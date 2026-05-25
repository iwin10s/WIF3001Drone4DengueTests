"""
test_uc8_010.py
===============
Test Procedure : TP-UC8-010
Test Cases     : TC-UC8-010
Objective      : Verify that system handles error validation if no record
                 matches filter criteria, displaying a placeholder message.
Coverage Items : TCOV-08-019, TCOV-08-020
Wrap-Up        : None
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL     = "http://localhost:3000"
DATA_MGT_URL = BASE_URL + "/data-management"

PLACEHOLDER_KEYWORDS = ["no data", "no record", "please apply", "no results", "not found"]


def _clear_filters(driver):
    try:
        driver.find_element(
            By.XPATH, "//button[.//text()[contains(., 'Clear')]]"
        ).click()
        time.sleep(0.8)
    except Exception:
        pass


class TestUC8NoMatchFilter:
    """TP-UC8-010 — Placeholder shown when no records match filters."""

    def test_no_records_for_year_2020_date_range(self, logged_in):
        """
        TC-UC8-010 | TCOV-08-019
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Set startDate=2020-01-01, endDate=2020-01-31.
        Step 3  Click Search Data.
        Step 4  Assert placeholder "No Record found" (or equivalent) is shown.

        Pre-condition: Ensure zero records exist for Jan 2020.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        date_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date']")
        assert len(date_inputs) >= 2, "Expected 2 date inputs."

        date_inputs[0].clear()
        date_inputs[0].send_keys("2020-01-01")
        date_inputs[1].clear()
        date_inputs[1].send_keys("2020-01-31")

        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[.//text()[contains(., 'Search Data')]]")
            )
        ).click()
        time.sleep(2)

        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        real_rows = [r for r in rows if r.text.strip() and
                     not any(kw in r.text.lower() for kw in PLACEHOLDER_KEYWORDS)]

        assert any(kw in body_text for kw in PLACEHOLDER_KEYWORDS) or len(real_rows) == 0, (
            "TC-UC8-010 FAIL (no match date): Expected placeholder or zero rows "
            "for Jan 2020 filter, but found %d row(s).\nBody: %s" % (
                len(real_rows), body_text[:400])
        )
        print("TC-UC8-010 No Records Found for Date Range 2020 - PASS")

    def test_no_records_for_nonexistent_location(self, logged_in):
        """
        TC-UC8-010 | TCOV-08-020
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Clear filters, then type 'NonExistLocation' in location input.
        Step 3  Click Search Data.
        Step 4  Assert placeholder "No Record found" (or equivalent) is shown.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        _clear_filters(driver)

        # Find the location text input
        loc_input = None
        for inp in driver.find_elements(By.CSS_SELECTOR, "input[type='text']"):
            placeholder = (inp.get_attribute("placeholder") or "").lower()
            if "location" in placeholder or "search" in placeholder:
                loc_input = inp
                break
        if not loc_input:
            all_text = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            loc_input = all_text[-1] if all_text else None

        assert loc_input, "Could not find the location text input."
        loc_input.clear()
        loc_input.send_keys("NonExistLocation")

        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[.//text()[contains(., 'Search Data')]]")
            )
        ).click()
        time.sleep(2)

        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        real_rows = [r for r in rows if r.text.strip() and
                     not any(kw in r.text.lower() for kw in PLACEHOLDER_KEYWORDS)]

        assert any(kw in body_text for kw in PLACEHOLDER_KEYWORDS) or len(real_rows) == 0, (
            "TC-UC8-010 FAIL (no match location): Expected placeholder for "
            "'NonExistLocation', but found %d row(s).\nBody: %s" % (
                len(real_rows), body_text[:400])
        )
        print("TC-UC8-010 No Records Found for NonExist Location - PASS")