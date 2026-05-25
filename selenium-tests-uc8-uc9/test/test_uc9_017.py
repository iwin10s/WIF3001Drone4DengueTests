"""
test_uc9_017.py

Test Procedure : TP-UC9-017
Test Case      : TC-UC9-026
Objective      : Verify that the current weather data records table can be
                 exported as a downloadable CSV file named
                 weather-data-yyyy-mm-dd.csv containing the correct columns.

Prerequisites  : Weather records must exist in the database.
                 The browser's download directory must be accessible at
                 DOWNLOAD_DIR (defaults to ~/Downloads).
"""

import os
import re
import sys
import time
import glob
import pytest
from selenium.webdriver.common.by import By

# Resolve WEATHER_URL from conftest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from conftest import WEATHER_URL
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL     = "http://localhost:3000"
WEATHER_URL  = f"{BASE_URL}/weather-data"

# Override via env var if the CI download folder is elsewhere
DOWNLOAD_DIR = os.getenv(
    "SELENIUM_DOWNLOAD_DIR",
    os.path.join(os.path.expanduser("~"), "Downloads")
)

EXPECTED_COLUMNS = {"Date", "Temperature", "Humidity", "Rainfall", "Location"}
FILENAME_PATTERN = re.compile(r"^weather-data-\d{4}-\d{2}-\d{2}\.csv$")


class TestTP_UC9_017:
    """TP-UC9-017 — Export Data button downloads a correctly named CSV."""

    def test_tc_uc9_026_export_data_downloads_csv(self, logged_in):
        """
        TC-UC9-026
        Input   : Click "Export Data" button on the Weather Data page.
        Expected: A file matching weather-data-yyyy-mm-dd.csv is downloaded
                  and contains columns: Date, Temperature, Humidity, Rainfall, Location.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        # ── Step 1: Confirm we are on the Weather Data page ──────────
        wait.until(EC.url_contains("/weather-data"))

        # ── Step 2: Note existing CSV files in the download directory ──
        existing_csvs = set(
            glob.glob(os.path.join(DOWNLOAD_DIR, "weather-data-*.csv"))
        )

        # ── Step 3: Click the "Export Data" button ────────────────────
        export_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='Export Data']")
            )
        )
        export_btn.click()

        # ── Step 4: Wait for a new CSV to appear in the download folder ─
        deadline = time.time() + 15   # 15-second timeout
        new_csv  = None
        while time.time() < deadline:
            current_csvs = set(
                glob.glob(os.path.join(DOWNLOAD_DIR, "weather-data-*.csv"))
            )
            new_files = current_csvs - existing_csvs
            if new_files:
                new_csv = list(new_files)[0]
                break
            time.sleep(0.5)

        assert new_csv is not None, (
            "No new weather-data CSV file appeared in the download directory "
            f"({DOWNLOAD_DIR}) within 15 seconds after clicking Export Data."
        )

        # ── Step 5: Verify the filename matches the expected pattern ───
        filename = os.path.basename(new_csv)
        assert FILENAME_PATTERN.match(filename), (
            f"Downloaded filename '{filename}' does not match "
            f"the expected pattern 'weather-data-yyyy-mm-dd.csv'."
        )

        # ── Step 6: Open the file and verify column headers ───────────
        with open(new_csv, "r", encoding="utf-8") as f:
            header_line = f.readline().strip()

        actual_columns = {col.strip() for col in header_line.split(",")}
        missing = EXPECTED_COLUMNS - actual_columns
        assert not missing, (
            f"The exported CSV is missing these columns: {missing}. "
            f"Actual columns found: {actual_columns}"
        )

        print("TC-UC9-026 Export Data Downloads Valid CSV File - PASS")