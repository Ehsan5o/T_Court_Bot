from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
from datetime import datetime, timedelta
import sys
import os

CALENDLY_URL = os.environ.get("CALENDLY_URL")

# Test-specific booking schedule for Friday 14:00 GST
BOOKING_SCHEDULE = {
    "Friday 14:00": {"target_day": "Friday", "target_time": "14:00"}  # Temporary test: Friday 14:00 GST
}

def get_contact_details(run_time_key):
    if run_time_key == "Friday 14:00":  # Use User 1 for this test
        return {
            "full_name": os.environ.get("FULL_NAME_1"),
            "email": os.environ.get("EMAIL_1"),
            "building_name": os.environ.get("BUILDING_NAME_1"),
            "unit_no": os.environ.get("UNIT_NO_1"),
            "num_players": os.environ.get("NUM_PLAYERS_1"),
            "phone_no": os.environ.get("PHONE_NO_1")
        }
    else:
        raise ValueError(f"Unknown run_time_key for test: {run_time_key}")

def normalize_run_time(run_time_key):
    """Normalize the run time to the nearest scheduled time in BOOKING_SCHEDULE."""
    run_day, run_time_str = run_time_key.split()
    run_hour, run_minute = map(int, run_time_str.split(":"))

    # For test, only normalize to "Friday 14:00"
    scheduled_times = {"Friday": ["14:00"]}
    if run_day not in scheduled_times:
        raise ValueError(f"Invalid run day for test: {run_day}")

    closest_time = None
    min_diff = float('inf')
    for scheduled_time in scheduled_times[run_day]:
        scheduled_hour = int(scheduled_time.split(":")[0])
        diff = abs(run_hour * 60 + run_minute - scheduled_hour * 60)
        if diff < min_diff:
            min_diff = diff
            closest_time = scheduled_time

    if min_diff <= 60:
        normalized_run_time = f"{run_day} {closest_time}"
        print(f"Normalized run time from {run_time_key} to {normalized_run_time}")
        return normalized_run_time
    else:
        raise ValueError(f"Run time {run_time_key} is too far from scheduled test time")

def book_tennis_court(run_time_key):
    # Normalize the run time to handle delays
    try:
        run_time_key = normalize_run_time(run_time_key)
    except ValueError as e:
        print(f"Error: {e}")
        return

    if run_time_key not in BOOKING_SCHEDULE:
        print(f"Invalid run time: {run_time_key}")
        return
    
    target_info = BOOKING_SCHEDULE[run_time_key]
    target_day = target_info["target_day"]  # e.g., "Friday"
    target_time = target_info["target_time"]  # e.g., "14:00"

    # Parse the normalized run time to determine current time in GST (UTC+4)
    run_day, run_time_str = run_time_key.split()
    run_hour = int(run_time_str.split(":")[0])
    now = datetime.now()
    run_time = now.replace(hour=run_hour, minute=0, second=0, microsecond=0)
    if run_time < now:
        run_time += timedelta(days=1)  # If run time has passed today, use tomorrow

    # Adjust to GST (UTC+4) if not already
    run_time = run_time + timedelta(hours=4)  # Convert to GST

    # Calculate target booking date/time (same day for Friday test)
    target_datetime = run_time
    while target_datetime.weekday() != 4:  # 4 is Friday
        target_datetime += timedelta(days=1)
    target_date = target_datetime.strftime("%Y-%m-%d")
    target_weekday = target_datetime.strftime("%A")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # Debug: Print the CALENDLY_URL to verify its value
        print(f"Attempting to navigate to CALENDLY_URL: {CALENDLY_URL}")
        if not CALENDLY_URL or not CALENDLY_URL.startswith(('http://', 'https://')):
            raise ValueError("CALENDLY_URL is empty or invalid. Please set a valid URL (e.g., https://calendly.com/tennis-court-/tennis-court-booking)")

        driver.get(CALENDLY_URL)
        time.sleep(2)

        # Find all bookable (blue) dates using <button> with aria-label
        date_elements = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "button"))
        )
        selected_date = None
        for date in date_elements:
            aria_label = date.get_attribute("aria-label")
            if aria_label and "Times available" in aria_label:
                date_str = date.get_attribute("data-date")
                if date_str:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    if (date_obj.date() == target_datetime.date() and 
                        date_obj.strftime("%A") == target_day):
                        selected_date = date_str
                        driver.execute_script("arguments[0].click();", date)
                        print(f"Selected date: {selected_date} (from {aria_label})")
                        break
        if not selected_date:
            raise Exception(f"No bookable {target_day} found on {target_date}")

        # Select the target time (using buttons with specific class and no disabled)
        time_slots = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.XPATH, "//button[@role='button' and contains(@class, 'uvkj3lh') and not(contains(@class, 'disabled'))]"))
        )
        for slot in time_slots:
            slot_text = slot.text.strip().lower()
            # Handle both 24-hour and 12-hour formats
            if target_time in slot_text or (f"{target_time}:00" in slot_text):  # e.g., "14:00"
                slot.click()
                print(f"Selected time: {slot_text}")
                break
            # Handle "2:00pm" for 14:00
            elif f"{int(target_time) - 12}:00pm" in slot_text and int(target_time) > 12:
                slot.click()
                print(f"Selected time: {slot_text}")
                break
        else:
            raise Exception(f"Target time {target_time}:00 not found on {selected_date}")

        # Click "Next" after selecting time slot
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Next' and contains(@class, 'uvkj3lh yb_MD7H42L8SUzygjrlfk iHJCjB0EZtLFS2z0H')]"))
        )
        next_button.click()
        print("Clicked Next after time selection")

        # Fill form and submit
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "full_name_input")))
        contact = get_contact_details(run_time_key)
        driver.find_element(By.ID, "full_name_input").send_keys(contact["full_name"])
        driver.find_element(By.ID, "email_input").send_keys(contact["email"])
        driver.find_element(By.ID, "1bT3Iu2abRAKqjda6jqLu").send_keys(contact["building_name"])
        driver.find_element(By.ID, "tCGwp8nKnr6eDQuqH1Z7F").send_keys(contact["unit_no"])
        driver.find_element(By.ID, "eMqYw4Nb4Cd2DDrjBwbbm").send_keys(contact["num_players"])
        driver.find_element(By.ID, "B-IUGCRB09hRLI1QXjzeI").send_keys(contact["phone_no"])

        confirm_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Schedule')]")
        confirm_button.click()

        time.sleep(2)
        print(f"Booked {target_day} {target_time}:00 on {selected_date} successfully with {contact['email']}")

    except Exception as e:
        print(f"Error booking {target_day} {target_time}:00: {e}")
        raise
    
    finally:
        driver.quit()

if __name__ == "__main__":
    # Hardcode the run time for the test since it's manual
    run_time = "Friday 14:00"
    print(f"Current time: {run_time}")
    book_tennis_court(run_time)
