"""
test_uc9_005.py

Test Procedure : TP-UC9-005
Test Case      : TC-UC9-006
Objective      : Verify that the system clears the table and displays
                 "No weather data" when no records match the selected filters
                 (location or date).
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

BASE_URL    = "http://localhost:3000"
WEATHER_URL = f"{BASE_URL}/weather-data"

# A date guaranteed to have no records in the test database
NO_DATA_DATE = "2025-01-01"


class TestTP_UC9_005:
    """TP-UC9-005 — Filters with no matching records show 'No Weather Data'."""

    # ------------------------------------------------------------------
    # TC-UC9-006
    # ------------------------------------------------------------------
    def test_tc_uc9_006_no_location_selected_shows_placeholder(self, logged_in):
        """
        TC-UC9-006 — Part A
        Input   : Set Operational Area filter to "Select a Location" (unselected).
        Expected: Table clears and shows "No weather data" placeholder.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        # ── Step 1: Confirm we are on the Weather Data page ──────────
        wait.until(EC.url_contains("/weather-data"))

        # ── Step 2: Locate the Operational Area / Location filter ─────
        # There are two locationSelect dropdowns; the filter one is in the
        # filter bar above the table (not in the CSV upload section).
        location_selects = driver.find_elements(By.ID, "locationSelect")
        # Pick the second one (index 1) which belongs to the table filter bar
        filter_select_el = location_selects[-1] if len(location_selects) > 1 else location_selects[0]
        filter_select = Select(filter_select_el)

        # ── Step 3: Choose the default "Select a Location" option ─────
        filter_select.select_by_index(0)   # index 0 is always the placeholder

        # ── Step 4: Verify "No Weather Data" placeholder is displayed ─
        placeholder = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                           "'abcdefghijklmnopqrstuvwxyz'),'no weather data')]")
            )
        )
        assert placeholder.is_displayed(), (
            "Expected 'No weather data' placeholder text to appear when "
            "no location is selected in the filter."
        )

        print("TC-UC9-006 No Location Selected Placeholder - PASS")

    def test_tc_uc9_006_non_existent_date_shows_placeholder(self, logged_in):
        """
        TC-UC9-006 — Part B
        Input   : Clear all filters, then set Date filter to 2025-01-01
                  (a date with no stored records).
        Expected: Table clears and shows "No weather data" placeholder.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        # ── Step 1: Reload page to reset all filter state ─────────────
        driver.get(WEATHER_URL)
        wait.until(EC.url_contains("/weather-data"))

        # ── Step 2: Locate the Date filter input ──────────────────────
        # There may be two dateFilter elements; pick the one in the filter bar.
        date_filters = driver.find_elements(By.ID, "dateFilter")
        filter_date_el = date_filters[-1] if len(date_filters) > 1 else date_filters[0]

        # ── Step 3: Enter a date that has no records ───────────────────
        filter_date_el.clear()
        filter_date_el.send_keys(NO_DATA_DATE)

        # ── Step 4: Trigger the filter (blur / Enter) ─────────────────
        from selenium.webdriver.common.keys import Keys
        filter_date_el.send_keys(Keys.TAB)

        # ── Step 5: Verify "No Weather Data" placeholder is displayed ─
        placeholder = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                           "'abcdefghijklmnopqrstuvwxyz'),'no weather data')]")
            )
        )
        assert placeholder.is_displayed(), (
            f"Expected 'No weather data' placeholder when filtering by date {NO_DATA_DATE}."
        )

        print("TC-UC9-006 Non-Existent Date Placeholder - PASS")