from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime, timedelta
import sys
import os

CALENDLY_URL = os.environ.get("CALENDLY_URL")

BOOKING_SCHEDULE = {
    "Monday 19:00": {"target_day": "Wednesday", "target_time": "06:00"},  # Updated to match "06:00"
    "Monday 20:00": {"target_day": "Wednesday", "target_time": "12:00"},  # Updated for 12:00 (adjust if 8:00pm)
    "Thursday 16:00": {"target_day": "Saturday", "target_time": "12:00"},  # Updated for 12:00 (adjust for 4:00pm)
    "Thursday 17:00": {"target_day": "Saturday", "target_time": "13:00"}   # Updated for 13:00 (adjust for 5:00pm)
}

def get_contact_details(run_time_key):
    if run_time_key in ["Monday 19:00", "Thursday 16:00"]:
        return {
            "full_name": os.environ.get("FULL_NAME_1"),
            "email": os.environ.get("EMAIL_1"),
            "building_name": os.environ.get("BUILDING_NAME_1"),
            "unit_no": os.environ.get("UNIT_NO_1"),
            "num_players": os.environ.get("NUM_PLAYERS_1"),
            "phone_no": os.environ.get("PHONE_NO_1")
        }
    elif run_time_key in ["Monday 20:00", "Thursday 17:00"]:
        return {
            "full_name": os.environ.get("FULL_NAME_2"),
            "email": os.environ.get("EMAIL_2"),
            "building_name": os.environ.get("BUILDING_NAME_2"),
            "unit_no": os.environ.get("UNIT_NO_2"),
            "num_players": os.environ.get("NUM_PLAYERS_2"),
            "phone_no": os.environ.get("PHONE_NO_2")
        }
    else:
        raise ValueError(f"Unknown run_time_key: {run_time_key}")

def book_tennis_court(run_time_key):
    if run_time_key not in BOOKING_SCHEDULE:
        print(f"Invalid run time: {run_time_key}")
        return
    
    target_info = BOOKING_SCHEDULE[run_time_key]
    target_day = target_info["target_day"]  # e.g., "Wednesday"
    target_time = target_info["target_time"]  # e.g., "06:00"

    # Parse run time to determine current time in GST (UTC+4)
    run_day, run_time_str = run_time_key.split()
    run_hour = int(run_time_str.split(":")[0])
    now = datetime.now()
    run_time = now.replace(hour=run_hour, minute=0, second=0, microsecond=0)
    if run_time < now:
        run_time += timedelta(days=1)  # If run time has passed today, use tomorrow

    # Adjust to GST (UTC+4) if not already
    run_time = run_time + timedelta(hours=4)  # Convert to GST

    # Calculate target booking date/time (48 hours later on Wednesday or Saturday)
    if target_day == "Wednesday":
        # Find the next Wednesday 48 hours from Monday's run time
        target_datetime = run_time + timedelta(hours=48)
        while target_datetime.weekday() != 2:  # 2 is Wednesday (0=Monday, 6=Sunday)
            target_datetime += timedelta(days=1)
    elif target_day == "Saturday":
        # Find the next Saturday 48 hours from Thursday's run time
        target_datetime = run_time + timedelta(hours=48)
        while target_datetime.weekday() != 5:  # 5 is Saturday
            target_datetime += timedelta(days=1)
    target_date = target_datetime.strftime("%Y-%m-%d")
    target_weekday = target_datetime.strftime("%A")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
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
                    # Check if this date matches the target date (exactly 48 hours from run time)
                    expected_date = target_datetime - timedelta(hours=48)
                    if (date_obj.date() == expected_date.date() and 
                        date_obj.strftime("%A") == target_day):
                        selected_date = date_str
                        driver.execute_script("arguments[0].click();", date)  # Use JS to click in case of disabled
                        print(f"Selected date: {selected_date} (from {aria_label})")
                        break
        if not selected_date:
            raise Exception(f"No bookable {target_day} found exactly 48 hours from {run_time.strftime('%Y-%m-%d %H:%M')} GST")

        # Select the target time (using buttons with specific class and no disabled)
        time_slots = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.XPATH, "//button[@role='button' and contains(@class, 'uvkj3lh') and not(contains(@class, 'disabled'))]"))
        )
        for slot in time_slots:
            slot_text = slot.text.strip().lower()
            if target_time in slot_text:  # e.g., "06:00" or "7:00pm"
                slot.click()
                print(f"Selected time: {slot_text}")
                break
        else:
            raise Exception(f"Target time {target_time} not found on {selected_date}")

        # Click "Next" after selecting time slot
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Next' and contains(@class, 'uvkj3lh yb_MD7H42L8SUzygjrlfk iHJCjB0EZtLFS2z0H')]"))
        )
        next_button.click()
        print("Clicked Next after time selection")

        # Fill form and submit
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "full_name_input")))
        contact = get_contact_details(run_time
