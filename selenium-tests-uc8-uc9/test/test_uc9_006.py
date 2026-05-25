"""
test_uc9_006.py

Test Procedure : TP-UC9-006
Test Case      : TC-UC9-007
Objective      : Verify that CSV file processing is rejected when Operational
                 Area is not selected from the dropdown menu.
"""

import os
import sys
import pytest

# Resolve fixture paths via conftest so they work on any OS/machine
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from conftest import FIXTURES_DIR, WEATHER_URL
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL    = "http://localhost:3000"
WEATHER_URL = f"{BASE_URL}/weather-data"

VALID_CSV = os.path.join(FIXTURES_DIR, "weather_valid.csv")


class TestTP_UC9_006:
    """TP-UC9-006 — Upload rejected without Operational Area selection."""

    def test_tc_uc9_007_upload_rejected_no_operational_area(self, logged_in):
        """
        TC-UC9-007
        Input   : Select weather_valid.csv; leave Operational Area on default
                  "Select a location"; click Upload CSV.
        Expected: Error alert "Please select a company location" is shown
                  and the CSV is NOT processed.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        # ── Step 1: Confirm we are on the Weather Data page ──────────
        wait.until(EC.url_contains("/weather-data"))

        # ── Step 2: Attach the CSV file to the file input ─────────────
        file_input = wait.until(
            EC.presence_of_element_located((By.ID, "csvFile"))
        )
        file_input.send_keys(VALID_CSV)

        # ── Step 3: Do NOT change the Operational Area dropdown ───────
        # (Leave it at the default "Select a location" placeholder — index 0)

        # ── Step 4: Click "Upload CSV" ────────────────────────────────
        upload_btn = driver.find_element(
            By.XPATH, "//button[normalize-space()='Upload CSV']"
        )
        upload_btn.click()

        # ── Step 5: Verify error message is shown ─────────────────────
        error_alert = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[class*='AlertDescription']")
            )
        )
        assert "Please select a company location" in error_alert.text, (
            f"Expected 'Please select a company location' error, got: '{error_alert.text}'"
        )

        print("TC-UC9-007 Upload Rejected Without Operational Area - PASS")