"""
Test Procedure ID : TP-UC7-010
Objective         : Verify admin can export the complete user list as a CSV file
                    containing all required data fields and all user records.
Test Cases        : TC-UC7-011
Run               : pytest tests/test_uc7_010.py -v -s
"""

import os
import re
import csv
import glob
import time

from selenium.webdriver.common.by import By

from conftest import (
    DOWNLOAD_DIR, EXPECTED_CSV_COLUMNS,
    go_to_user_management, get_page_source,
    wait_clickable,
)

EXPECTED_FILENAME = "users.csv"

def enable_headless_downloads(driver):
    """
    Headless Chrome blocks downloads by default.
    Path MUST use os.path.abspath to ensure clean separators on Windows.
    """
    clean_path = os.path.abspath(DOWNLOAD_DIR)   # ← normalizes all slashes
    driver.execute_cdp_cmd(
        "Browser.setDownloadBehavior",
        {
            "behavior":     "allow",
            "downloadPath": clean_path,
        },
    )
    print(f"\n🔍 Download path set to: {clean_path}")  # confirm in output


def wait_for_download(filename, timeout=30):
    clean_dir = os.path.abspath(DOWNLOAD_DIR)    # ← same fix here
    target    = os.path.join(clean_dir, filename)
    deadline  = time.monotonic() + timeout
    while time.monotonic() < deadline:
        partials = glob.glob(os.path.join(clean_dir, "*.crdownload"))
        if os.path.exists(target) and not partials:
            return target
        time.sleep(1)
    return None


class TestTP_UC7_010:
    """TP-UC7-010 — Export User List as CSV"""

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-011 Step 1
    # Input   : Click Export to CSV button
    # Expected: users.csv downloaded to DOWNLOAD_DIR.
    # ──────────────────────────────────────────────────────────────────────────
    def test_export_csv_downloaded(self, driver):
        try:
            # Allow downloads in headless Chrome
            enable_headless_downloads(driver)

            go_to_user_management(driver)

            # Remove pre-existing file to avoid false positive
            old_file = os.path.join(DOWNLOAD_DIR, EXPECTED_FILENAME)
            if os.path.exists(old_file):
                os.remove(old_file)

            # HTML: <button title="Export to CSV"><FiArrowDown /></button>
            export_btn = wait_clickable(
                driver,
                By.XPATH,
                "//button[@title='Export to CSV']",
                timeout=10,
            )
            export_btn.click()
            time.sleep(2)

            csv_path = wait_for_download(EXPECTED_FILENAME, timeout=30)
            assert csv_path is not None, (
                f"'{EXPECTED_FILENAME}' was not found in '{DOWNLOAD_DIR}' "
                f"within 30 seconds."
            )

            print(f"✅ TC-UC7-011 Step 1 | CSV Downloaded to {csv_path} — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-011 Step 1 | CSV File Downloaded — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-011 Step 2
    # Input   : Open users.csv
    # Expected: Column headers present in correct order.
    # ──────────────────────────────────────────────────────────────────────────
    def test_export_csv_correct_columns(self, driver):
        try:
            csv_path = os.path.join(DOWNLOAD_DIR, EXPECTED_FILENAME)
            assert os.path.exists(csv_path), (
                f"'{EXPECTED_FILENAME}' not found in '{DOWNLOAD_DIR}' "
                f"— run test_export_csv_downloaded first."
            )

            with open(csv_path, newline="", encoding="utf-8") as f:
                reader  = csv.reader(f)
                headers = next(reader)

            # Normalise: strip whitespace, lowercase — matches EXPECTED_CSV_COLUMNS
            headers_normalised = [h.strip().lower() for h in headers]

            assert headers_normalised == EXPECTED_CSV_COLUMNS, (
                f"Column mismatch.\n"
                f"  Expected : {EXPECTED_CSV_COLUMNS}\n"
                f"  Got      : {headers_normalised}"
            )

            print("✅ TC-UC7-011 Step 2 | CSV Columns Correct — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-011 Step 2 | CSV Columns Correct — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-011 Step 3
    # Input   : Count CSV rows vs total shown in User Management UI
    # Expected: Counts match; file opens without error.
    # ──────────────────────────────────────────────────────────────────────────
    def test_export_csv_record_count_matches(self, driver):
        try:
            csv_path = os.path.join(DOWNLOAD_DIR, EXPECTED_FILENAME)
            assert os.path.exists(csv_path), (
                f"'{EXPECTED_FILENAME}' not found — run earlier steps first."
            )

            # ── Count data rows in CSV (excluding header) ─────────────────────
            with open(csv_path, newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))

            assert len(rows) >= 2, "CSV appears empty — header only, no data rows."
            csv_data_count = len(rows) - 1

            # ── Count table rows in the User Management UI ────────────────────
            go_to_user_management(driver)
            time.sleep(2)

            # Each user is a <tr> inside <tbody> — count them directly
            # This is more reliable than parsing a text badge
            user_rows = driver.find_elements(
                By.XPATH, "//tbody/tr"
            )
            ui_count = len(user_rows)

            assert ui_count > 0, "No user rows found in the UI table."

            assert csv_data_count == ui_count, (
                f"Count mismatch: CSV has {csv_data_count} rows, "
                f"UI table has {ui_count} rows.\n"
                f"Note: CSV exports ALL users; UI may paginate. "
                f"Check if pagination is active."
            )

            print(
                f"✅ TC-UC7-011 Step 3 | Record Count Matches "
                f"({csv_data_count} records) — PASS"
            )

        except Exception as e:
            print(f"❌ TC-UC7-011 Step 3 | CSV Record Count Matches — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-011 Step 4 — Cleanup
    # ──────────────────────────────────────────────────────────────────────────
    def test_cleanup_csv_file(self, driver):
        try:
            csv_path = os.path.join(DOWNLOAD_DIR, EXPECTED_FILENAME)
            if os.path.exists(csv_path):
                os.remove(csv_path)
                assert not os.path.exists(csv_path), "users.csv could not be deleted."

            print("✅ TC-UC7-011 Step 4 | Cleanup CSV File — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-011 Step 4 | Cleanup CSV File — FAIL ({e})")
            assert False