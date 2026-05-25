"""
test_uc8_003.py — TP-UC8-003: Valid CSV Import & Duplicate Detection

Test Cases Executed: TC-UC8-003
Objective: Verify the system accepts valid structural bulk imports via CSV schema,
           updates the data table correctly, and flags duplicate operations.

Upload message rendering (from page.tsx):
  - Container : <div class="mt-3 p-3 rounded-lg text-sm font-medium {status_class}">
  - Success   : class includes 'text-green-700'  | text starts with '✓ Successfully imported: N record(s)'
  - Error     : class includes 'text-red-700'    | text starts with '✗ <error message>'
  - The div only exists in the DOM when uploadMsg state is non-null.
"""

import os
import time
import pytest
import tempfile
import csv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL     = os.getenv("APP_BASE_URL", "http://localhost:3000")
DATA_MGT_URL = f"{BASE_URL}/data-management"

# XPath that matches the upload feedback div regardless of status colour.
# Targets the fixed container classes that are always present when uploadMsg != null.
UPLOAD_MSG_XPATH = (
    "//div[contains(@class,'mt-3') and contains(@class,'p-3') "
    "and contains(@class,'rounded-lg') and contains(@class,'text-sm')]"
)


# ---------------------------------------------------------------------------
# Helper: create a temporary valid CSV file for upload
# ---------------------------------------------------------------------------
def create_valid_csv():
    """
    Creates a temporary dengue_cases.csv matching the controller's exact field
    mapping (dengueDataController.js lines 247-257):
      Required : date, location
      Optional : activeCases, totalCases, coverageArea, status, source,
                 latitude, longitude
      Valid status values (from controller): 'Active Cases', 'Hotspot'
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", prefix="dengue_cases_"
    )
    writer = csv.DictWriter(
        tmp,
        fieldnames=[
            "date",         # new Date(row.date)          — required
            "location",     # row.location                — required
            "activeCases",  # parseInt(row.activeCases)   — defaults 0
            "totalCases",   # parseInt(row.totalCases)    — defaults 0
            "coverageArea", # row.coverageArea || ''      — optional
            "status",       # row.status || 'Processing'  — optional
            "source",       # row.source || 'csv'         — optional
            "latitude",     # parseFloat(row.latitude)    — optional
            "longitude",    # parseFloat(row.longitude)   — optional
        ],
    )
    writer.writeheader()
    writer.writerow({
        "date":         "2026-03-15",
        "location":     "Kluang",
        "activeCases":  "15",
        "totalCases":   "120",
        "coverageArea": "Johor",
        "status":       "Active Cases",   # valid enum value from controller
        "source":       "csv",
        "latitude":     "1.9670",         # Kluang, Johor coordinates
        "longitude":    "103.3244",
    })
    tmp.close()
    return tmp.name


def _send_file_to_input(driver, csv_path):
    """
    Make the hidden file input visible and inject the file path.
    page.tsx: <input type="file" accept=".csv" ref={fileInputRef} style={{display:'none'}} />
    """
    file_input = driver.find_element(
        By.CSS_SELECTOR, "input[type='file'][accept='.csv']"
    )
    driver.execute_script("arguments[0].style.display = 'block';", file_input)
    # Reset value so onChange fires even if the same file is used again
    driver.execute_script("arguments[0].value = '';", file_input)
    file_input.send_keys(csv_path)


def _wait_for_upload_message(wait):
    """
    Wait for the upload feedback div to appear in the DOM.
    Matches on stable container classes: mt-3 p-3 rounded-lg text-sm
    (page.tsx always renders these regardless of success/error state).
    """
    return wait.until(
        EC.presence_of_element_located((By.XPATH, UPLOAD_MSG_XPATH))
    )


# ---------------------------------------------------------------------------
# TC-UC8-003 — Sub-test 1: Valid CSV upload appears in data table
# ---------------------------------------------------------------------------
def test_valid_csv_upload_appears_in_table(logged_in):
    """
    TC-UC8-003 (first import):
    Upload a valid dengue_cases.csv and verify the new record
    appears in the data table without a manual page refresh.
    """
    driver = logged_in
    wait   = WebDriverWait(driver, 15)

    # Step 1 — Navigate to the Data Management page
    driver.get(DATA_MGT_URL)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

    # Step 2 — Create a valid CSV file on disk
    csv_path = create_valid_csv()
    print(f"Step 2: Created temporary CSV file at {csv_path}")

    # Step 3 — Send the CSV path to the hidden file input
    _send_file_to_input(driver, csv_path)
    print("Step 3: Sent CSV file path to the hidden file input")

    # Step 4 — Wait for the upload feedback div to appear
    # page.tsx success text: "✓ Successfully imported: N record(s)"
    # page.tsx success class: "text-green-700 bg-green-50 border border-green-200"
    upload_msg_div = _wait_for_upload_message(wait)
    msg_text  = upload_msg_div.text.strip()
    msg_class = upload_msg_div.get_attribute("class") or ""

    # Step 5 — Assert the message indicates a successful import
    is_success = (
        "successfully imported" in msg_text.lower()
        or "✓" in msg_text
        or "text-green-700" in msg_class
    )
    assert is_success, (
        f"TC-UC8-003 FAIL: Expected a success upload message. "
        f"Got text='{msg_text}', class='{msg_class}'"
    )
    
    # Step 6 — Apply date filter so the table fetches and renders results
    # page.tsx only shows records after 'Search Data' is clicked
    start_input = driver.find_element(By.XPATH, "(//input[@type='date'])[1]")
    start_input.send_keys("2026-03-01")
    end_input   = driver.find_element(By.XPATH, "(//input[@type='date'])[2]")
    end_input.send_keys("2026-03-31")

    # Step 7 — Click Search Data to load the table
    driver.find_element(
        By.XPATH, "//button[contains(text(),'Search Data')]"
    ).click()


    # Step 8 — Wait for the imported 'Kluang' row to appear in the table
    # Location is rendered in td:nth-child(2) as row.displayName || row.location
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//table//tbody//tr//td[contains(text(),'Kluang')]")
        )
    )

    # Step 9 — Double-check by scanning all row texts
    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    assert any("Kluang" in r.text for r in rows), \
        "TC-UC8-003 FAIL: 'Kluang' not found in any table row after import."

    os.unlink(csv_path)
    print("TC-UC8-003 (First Import) Valid CSV upload reflected in table - PASS")


# ---------------------------------------------------------------------------
# TC-UC8-003 — Sub-test 2: Duplicate CSV upload is rejected
# ---------------------------------------------------------------------------
def test_duplicate_csv_upload_is_rejected(logged_in):
    """
    TC-UC8-003 (duplicate import):
    Upload the same CSV file a second time and verify the system
    rejects the duplicate rows and maintains data integrity.
    Depends on: test_valid_csv_upload_appears_in_table having run first.
    """
    driver = logged_in
    wait   = WebDriverWait(driver, 15)

    # Step 1 — Navigate to the Data Management page
    driver.get(DATA_MGT_URL)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    # Step 2 — Re-create the same CSV (identical data = duplicate)
    csv_path = create_valid_csv()
    print(f"Step 2: Re-created the same CSV file at {csv_path}")

    # Step 3 — Send the duplicate file to the hidden file input
    _send_file_to_input(driver, csv_path)
    print("Step 3: Sent duplicate CSV file path to the file input")

    # Step 4 — Wait for the upload feedback div
    # Duplicate outcome can be:
    #   - Error  : class 'text-red-700', text starts with '✗'
    #   - Partial: class 'text-green-700', text '✓ Successfully imported: 0 records (N errors encountered)'
    upload_msg_div = _wait_for_upload_message(wait)
    msg_text  = upload_msg_div.text.strip()
    msg_class = upload_msg_div.get_attribute("class") or ""

    # Step 5 — Verify the system flagged/rejected the duplicate
    msg_lower = msg_text.lower()
    is_duplicate_rejected = (
        "✗"          in msg_text          # explicit error prefix
        or "text-red-700" in msg_class    # error colour class
        or "0 record" in msg_lower        # 0 new records imported
        or "duplicate" in msg_lower
        or "already"   in msg_lower
        or "failed"    in msg_lower
        or "error"     in msg_lower
    )
    assert is_duplicate_rejected, (
        f"TC-UC8-003 FAIL: Expected duplicate rejection but got: "
        f"text='{msg_text}', class='{msg_class}'"
    )
    print("Duplicate upload correctly flagged/rejected by the system")

    os.unlink(csv_path)
    print("TC-UC8-003 Duplicate Upload Rejected - PASS")