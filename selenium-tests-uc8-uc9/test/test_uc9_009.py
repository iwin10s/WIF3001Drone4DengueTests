"""
test_uc9_009.py

Test Procedure : TP-UC9-009
Test Case      : TC-UC9-011
Objective      : Verify that the form system rejects empty required inputs
                 (date, temperature, humidity, rainfall, location, operational area)
                 during manual form submissions.
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

BASE_URL    = "http://localhost:3000"
WEATHER_URL = f"{BASE_URL}/weather-data"

# A full set of valid values used as the "baseline" for each sub-test
VALID = {
    "date":        "2025-06-01",
    "temperature": "28.5",
    "humidity":    "75",
    "rainfall":    "12.5",
    "location":    "Kuala Lumpur",
}


class TestTP_UC9_009:
    """TP-UC9-009 — Empty required fields are each individually rejected."""

    def _open_form(self, driver, wait):
        """Click 'Add New Record' and wait for the form to appear."""
        driver.get(WEATHER_URL)
        wait.until(EC.url_contains("/weather-data"))
        add_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='Add New Record']")
            )
        )
        add_btn.click()
        wait.until(EC.visibility_of_element_located((By.ID, "date")))

    def _fill_all_except(self, driver, skip_field, op_area_index=1):
        """Fill all valid values except the one named in skip_field."""
        fields = {
            "date":        ("date",        VALID["date"]),
            "temperature": ("temperature", VALID["temperature"]),
            "humidity":    ("humidity",    VALID["humidity"]),
            "rainfall":    ("rainfall",    VALID["rainfall"]),
            "location":    ("location",    VALID["location"]),
        }
        for key, (field_id, value) in fields.items():
            el = driver.find_element(By.ID, field_id)
            el.clear()
            if key != skip_field:
                el.send_keys(value)

        # Operational Area dropdown
        select_el = Select(driver.find_element(By.ID, "companyLocationId"))
        if skip_field != "operationalArea":
            options = [o for o in select_el.options if o.get_attribute("value")]
            if options:
                select_el.select_by_index(op_area_index)
        # else: leave at default placeholder (index 0)

    def _submit_and_get_message(self, driver, wait):
        """Click 'Add Record' and return the alert description text."""
        driver.find_element(
            By.XPATH, "//button[normalize-space()='Add Record']"
        ).click()
        alert_el = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[class*='AlertDescription']")
            )
        )
        return alert_el.text

    def _assert_rejected(self, message, field_label):
        assert "All fields are required" in message or message.strip() != "", (
            f"Expected validation rejection for empty '{field_label}', got: '{message}'"
        )
        assert "Weather record added successfully" not in message, (
            f"Record was added even with empty '{field_label}' field — should be rejected."
        )

    # ── TC-UC9-011 sub-cases ─────────────────────────────────────────

    def test_tc_uc9_011_empty_date_rejected(self, logged_in):
        """Step: Leave Date empty, fill all other fields — expect rejection."""
        driver = logged_in
        wait   = WebDriverWait(driver, 15)
        self._open_form(driver, wait)
        self._fill_all_except(driver, skip_field="date")
        msg = self._submit_and_get_message(driver, wait)
        self._assert_rejected(msg, "date")
        print("TC-UC9-011 Empty Date Validation - PASS")

    def test_tc_uc9_011_empty_temperature_rejected(self, logged_in):
        """Step: Leave Temperature empty, fill all other fields — expect rejection."""
        driver = logged_in
        wait   = WebDriverWait(driver, 15)
        self._open_form(driver, wait)
        self._fill_all_except(driver, skip_field="temperature")
        msg = self._submit_and_get_message(driver, wait)
        self._assert_rejected(msg, "temperature")
        print("TC-UC9-011 Empty Temperature Validation - PASS")

    def test_tc_uc9_011_empty_humidity_rejected(self, logged_in):
        """Step: Leave Humidity empty, fill all other fields — expect rejection."""
        driver = logged_in
        wait   = WebDriverWait(driver, 15)
        self._open_form(driver, wait)
        self._fill_all_except(driver, skip_field="humidity")
        msg = self._submit_and_get_message(driver, wait)
        self._assert_rejected(msg, "humidity")
        print("TC-UC9-011 Empty Humidity Validation - PASS")

    def test_tc_uc9_011_empty_rainfall_rejected(self, logged_in):
        """Step: Leave Rainfall empty, fill all other fields — expect rejection."""
        driver = logged_in
        wait   = WebDriverWait(driver, 15)
        self._open_form(driver, wait)
        self._fill_all_except(driver, skip_field="rainfall")
        msg = self._submit_and_get_message(driver, wait)
        self._assert_rejected(msg, "rainfall")
        print("TC-UC9-011 Empty Rainfall Validation - PASS")

    def test_tc_uc9_011_empty_location_rejected(self, logged_in):
        """Step: Leave Location empty, fill all other fields — expect rejection."""
        driver = logged_in
        wait   = WebDriverWait(driver, 15)
        self._open_form(driver, wait)
        self._fill_all_except(driver, skip_field="location")
        msg = self._submit_and_get_message(driver, wait)
        self._assert_rejected(msg, "location")
        print("TC-UC9-011 Empty Location Validation - PASS")

    def test_tc_uc9_011_empty_operational_area_rejected(self, logged_in):
        """Step: Leave Operational Area unselected, fill all other fields — expect rejection."""
        driver = logged_in
        wait   = WebDriverWait(driver, 15)
        self._open_form(driver, wait)
        self._fill_all_except(driver, skip_field="operationalArea")
        msg = self._submit_and_get_message(driver, wait)
        self._assert_rejected(msg, "operationalArea")
        print("TC-UC9-011 Empty Operational Area Validation - PASS")

        