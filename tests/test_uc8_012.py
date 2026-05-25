"""
test_uc8_012.py
===============
Test Procedure : TP-UC8-012
Test Cases     : TC-UC8-012
Objective      : Verify that system allows admin to filter dengue data records
                 by Cases Type (Hotspot, Active Cases, All Types).
Coverage Items : TCOV-08-024, TCOV-08-025
Wrap-Up        : None
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

BASE_URL     = "http://localhost:3000"
DATA_MGT_URL = BASE_URL + "/data-management"


def _select_cases_type_and_search(driver, wait, case_type: str):
    """
    Select a value from the Cases Type dropdown, then click Search Data.
    case_type: "", "Hotspot", or "Active Cases"
    """
    status_dropdown = wait.until(
        EC.presence_of_element_located(
            (By.XPATH,
             "//select[option[contains(text(),'Hotspot')] "
             "and option[contains(text(),'Active Cases')]]")
        )
    )
    Select(status_dropdown).select_by_visible_text(case_type if case_type else "All Types")
    driver.find_element(
        By.XPATH, "//button[contains(text(),'Search Data')]"
    ).click()
    time.sleep(2)


def _get_type_column_values(driver):
    """
    Return a list of text values from the Type/Status column in the table body.
    The Type column is the 5th <td> per the table header order:
    Date | Location | Active/Total Cases | Cumulative Duration | Type | State | Actions
    """
    cells = driver.find_elements(By.CSS_SELECTOR, "table tbody tr td:nth-child(5)")
    return [c.text.strip() for c in cells if c.text.strip()]


class TestUC8CasesTypeFilter:
    """TP-UC8-012 — Cases Type filter on the Data Management table."""

    def test_filter_by_hotspot_shows_only_hotspot_rows(self, logged_in):
        """
        TC-UC8-012 | TCOV-08-024
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Open the Cases Type dropdown and select 'Hotspot'.
        Step 3  Click Search Data.
        Step 4  Observe the Type column — every visible row must show 'Hotspot'.
        Pre-requisite: At least one record with status='Hotspot' exists in DB.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        # Step 1 — Navigate to Data Management page
        driver.get(DATA_MGT_URL)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        # Step 2 & 3 — Select 'Hotspot' from Cases Type dropdown and search
        _select_cases_type_and_search(driver, wait, "Hotspot")
        print("Step 2-3: Selected 'Hotspot' from Cases Type filter and clicked Search Data")

        # Step 4 — Collect Type column values and assert all are 'Hotspot'
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
        type_values = _get_type_column_values(driver)

        assert len(type_values) > 0, (
            "TC-UC8-012 FAIL: No rows returned after filtering by 'Hotspot'. "
            "Ensure the database has at least one Hotspot record."
        )

        non_hotspot = [v for v in type_values if v != "Hotspot"]
        assert len(non_hotspot) == 0, (
            "TC-UC8-012 FAIL: Table contains rows with type other than 'Hotspot' "
            "after filtering. Unexpected values: %s" % non_hotspot
        )

        print("TC-UC8-012 Filter by Hotspot Shows Only Hotspot Rows - PASS")

    def test_filter_by_active_cases_shows_only_active_rows(self, logged_in):
        """
        TC-UC8-012 | TCOV-08-025
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Open the Cases Type dropdown and select 'Active Cases'.
        Step 3  Click Search Data.
        Step 4  Observe the Type column — every visible row must show 'Active Cases'.
        Pre-requisite: At least one record with status='Active Cases' exists in DB.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        # Step 1 — Navigate to Data Management page
        driver.get(DATA_MGT_URL)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        # Step 2 & 3 — Select 'Active Cases' from Cases Type dropdown and search
        _select_cases_type_and_search(driver, wait, "Active Cases")
        print("Step 2-3: Selected 'Active Cases' from Cases Type filter and clicked Search Data")

        # Step 4 — Collect Type column values and assert all are 'Active Cases'
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
        type_values = _get_type_column_values(driver)

        assert len(type_values) > 0, (
            "TC-UC8-012 FAIL: No rows returned after filtering by 'Active Cases'. "
            "Ensure the database has at least one Active Cases record."
        )

        non_active = [v for v in type_values if v != "Active Cases"]
        assert len(non_active) == 0, (
            "TC-UC8-012 FAIL: Table contains rows with type other than 'Active Cases' "
            "after filtering. Unexpected values: %s" % non_active
        )

        print("TC-UC8-012 Filter by Active Cases Shows Only Active Cases Rows - PASS")

    def test_filter_all_types_shows_mixed_rows(self, logged_in):
        """
        TC-UC8-012 | TCOV-08-024 + TCOV-08-025 (reset check)
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Open the Cases Type dropdown and select 'All Types'.
        Step 3  Click Search Data.
        Step 4  Observe the Type column — rows of more than one type must appear,
                confirming the filter has been cleared and all records are shown.
        Pre-requisite: Database has records of at least two different statuses.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        # Step 1 — Navigate to Data Management page
        driver.get(DATA_MGT_URL)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        # Step 2 & 3 — Select 'All Types' (empty value) and search
        _select_cases_type_and_search(driver, wait, "")
        print("Step 2-3: Selected 'All Types' from Cases Type filter and clicked Search Data")

        # Step 4 — Collect Type column values and assert multiple types appear
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
        type_values = _get_type_column_values(driver)

        assert len(type_values) > 0, (
            "TC-UC8-012 FAIL: No rows returned when 'All Types' is selected."
        )

        unique_types = set(type_values)
        assert len(unique_types) > 1, (
            "TC-UC8-012 FAIL: Expected records of multiple types when 'All Types' is "
            "selected, but only found: %s. Ensure DB has both Hotspot and Active Cases records."
            % unique_types
        )

        print("TC-UC8-012 All Types Filter Shows Mixed Record Types - PASS")