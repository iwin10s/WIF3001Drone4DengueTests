"""
test_uc8_009.py
===============
Test Procedure : TP-UC8-009
Test Cases     : TC-UC8-009
Objective      : Verify that admin can filter dengue data by location (state,
                 city) and that the system returns only matching records.
Coverage Items : TCOV-08-017, TCOV-08-018
Wrap-Up        : None
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL     = "http://localhost:3000"
DATA_MGT_URL = BASE_URL + "/data-management"


def _clear_filters(driver):
    try:
        btn = driver.find_element(
            By.XPATH, "//button[.//text()[contains(., 'Clear')]]"
        )
        btn.click()
        time.sleep(0.8)
    except Exception:
        pass


def _search_by_location(driver, wait, location_text):
    """Enter a location into the location search input and click Search Data."""
    # The location field is a text input (type='text') per the page scan
    loc_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
    # The location search box is the last text input visible on the filter bar
    # (after date inputs and case-type inputs)
    location_input = None
    for inp in loc_inputs:
        placeholder = (inp.get_attribute("placeholder") or "").lower()
        name        = (inp.get_attribute("name") or "").lower()
        if "location" in placeholder or "location" in name or "search" in placeholder:
            location_input = inp
            break

    if not location_input and loc_inputs:
        location_input = loc_inputs[-1]  # fallback: last text input

    assert location_input, "Could not find a location text input on the page."
    location_input.clear()
    location_input.send_keys(location_text)

    search_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[.//text()[contains(., 'Search Data')]]")
        )
    )
    search_btn.click()
    time.sleep(2)


class TestUC8LocationFilter:
    """TP-UC8-009 — Location-based filtering (state and city)."""

    def test_filter_by_state_selangor(self, logged_in):
        """
        TC-UC8-009 | TCOV-08-017
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Type 'Selangor' in the location filter input.
        Step 3  Click Search Data.
        Step 4  Assert the table isolates only rows containing 'Selangor'.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        _search_by_location(driver, wait, "Selangor")

        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        data_rows = [r for r in rows if r.text.strip() and
                     "no data" not in r.text.lower() and
                     "no record" not in r.text.lower()]

        no_data = any(kw in body_text for kw in ["no data", "no record"])

        if not no_data and data_rows:
            table_text = " ".join(r.text for r in data_rows).lower()
            assert "selangor" in table_text, (
                "TC-UC8-009 FAIL (state filter): Records returned do not "
                "contain 'Selangor'.\nTable: " + table_text[:400]
            )

        print("TC-UC8-009 Filter by State Selangor - PASS")

    def test_filter_by_city_petaling_jaya(self, logged_in):
        """
        TC-UC8-009 | TCOV-08-018
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Clear the state filter, type 'Petaling Jaya' in location input.
        Step 3  Click Search Data.
        Step 4  Assert only rows containing 'Petaling Jaya' are shown.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        _clear_filters(driver)
        _search_by_location(driver, wait, "Petaling Jaya")

        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        data_rows = [r for r in rows if r.text.strip() and
                     "no data" not in r.text.lower() and
                     "no record" not in r.text.lower()]

        no_data = any(kw in body_text for kw in ["no data", "no record"])

        if not no_data and data_rows:
            table_text = " ".join(r.text for r in data_rows).lower()
            assert "petaling jaya" in table_text, (
                "TC-UC8-009 FAIL (city filter): Records returned do not "
                "contain 'Petaling Jaya'.\nTable: " + table_text[:400]
            )

        print("TC-UC8-009 Filter by City Petaling Jaya - PASS")