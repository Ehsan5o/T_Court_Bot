from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime, timedelta
import sys
import os

CALENDLY_URL = "https://calendly.com/tennis-court-/tennis-court-booking"

BOOKING_SCHEDULE = {
    "Monday 19:00": {"target_day": "Wednesday", "target_time": "7:00pm"},
    "Monday 20:00": {"target_day": "Wednesday", "target_time": "8:00pm"},
    "Thursday 16:00": {"target_day": "Saturday", "target_time": "4:00pm"},
    "Thursday 17:00": {"target_day": "Saturday", "target_time": "5:00pm"}
}

def calculate_target_date(run_time, target_day):
    today = datetime.now()
    days_ahead = (7 + ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"].index(target_day) - today.weekday()) % 7
    if days_ahead < 2:
        days_ahead += 7
    target_date = today + timedelta(days=days_ahead)
    return target_date.strftime("%Y-%m-%d")

def get_contact_details(run_time_key):
    # Use User 1 for 19:00 and 16:00 slots, User 2 for 20:00 and 17:00 slots
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
        raise ValueError(f"Unknown run time: {run_time_key}")

def book_tennis_court(run_time_key):
    if run_time_key not in BOOKING_SCHEDULE:
        print(f"Invalid run time: {run_time_key}")
        return
    
    target_info = BOOKING_SCHEDULE[run_time_key]
    target_day = target_info["target_day"]
    target_time = target_info["target_time"]

    # Get contact details for this run
    contact = get_contact_details(run_time_key)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        driver.get(CALENDLY_URL)
        time.sleep(2)

        target_date = calculate_target_date(run_time_key, target_day)
        date_elements = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "calendar-day"))
        )
        for date in date_elements:
            if target_date in date.get_attribute("data-date"):
                date.click()
                break
        else:
            raise Exception(f"Target date {target_date} not found")

        time_slots = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "time"))
        )
        for slot in time_slots:
            if target_time in slot.text.lower():
                slot.click()
                break
        else:
            raise Exception(f"Target time {target_time} not found")

        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Next')]"))
        )
        next_button.click()

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "full_name_input")))
        driver.find_element(By.ID, "full_name_input").send_keys(contact["full_name"])
        driver.find_element(By.ID, "email_input").send_keys(contact["email"])
        driver.find_element(By.ID, "1bT3Iu2abRAKqjda6jqLu").send_keys(contact["building_name"])
        driver.find_element(By.ID, "tCGwp8nKnr6eDQuqH1Z7F").send_keys(contact["unit_no"])
        driver.find_element(By.ID, "eMqYw4Nb4Cd2DDrjBwbbm").send_keys(contact["num_players"])
        driver.find_element(By.ID, "B-IUGCRB09hRLI1QXjzeI").send_keys(contact["phone_no"])

        confirm_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Schedule')]")
        confirm_button.click()

        time.sleep(2)
        print(f"Booked {target_day} {target_time} on {target_date} successfully with {contact['email']}")

    except Exception as e:
        print(f"Error booking {target_day} {target_time}: {e}")
        raise
    
    finally:
        driver.quit()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please provide run time (e.g., 'Monday 19:00')")
    else:
        run_time = " ".join(sys.argv[1:])
        book_tennis_court(run_time)
