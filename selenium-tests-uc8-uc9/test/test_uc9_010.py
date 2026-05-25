"""
test_uc9_010.py

Test Procedure : TP-UC9-010
Test Case      : TC-UC9-012
Objective      : Verify that the system rejects non-numeric words or text
                 strings typed into the temperature, humidity, and rainfall
                 form fields.
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

BASE_URL    = "http://localhost:3000"
WEATHER_URL = f"{BASE_URL}/weather-data"


class TestTP_UC9_010:
    """TP-UC9-010 — Non-numeric values are rejected for numeric fields."""

    def _open_form(self, driver, wait):
        """Click 'Add New Record' and wait for the form."""
        driver.get(WEATHER_URL)
        wait.until(EC.url_contains("/weather-data"))
        add_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='Add New Record']")
            )
        )
        add_btn.click()
        wait.until(EC.visibility_of_element_located((By.ID, "date")))

    def test_tc_uc9_012_non_numeric_values_rejected(self, logged_in):
        """
        TC-UC9-012
        Input   : temperature="hot", humidity="Humid weather", rainfall="heavy rain"
                  (all other fields valid)
        Expected: System blocks submission and displays a validation error
                  asking for numeric values; record is NOT added.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        # ── Step 1: Navigate to Weather Data page and open form ───────
        self._open_form(driver, wait)

        # ── Step 2: Fill in a valid date ───────────────────────────────
        driver.find_element(By.ID, "date").send_keys("2025-06-15")

        # ── Step 3: Enter non-numeric text in Temperature ─────────────
        driver.find_element(By.ID, "temperature").send_keys("hot")

        # ── Step 4: Enter non-numeric text in Humidity ────────────────
        driver.find_element(By.ID, "humidity").send_keys("Humid weather")

        # ── Step 5: Enter non-numeric text in Rainfall ────────────────
        driver.find_element(By.ID, "rainfall").send_keys("heavy rain")

        # ── Step 6: Fill valid location and operational area ──────────
        driver.find_element(By.ID, "location").send_keys("Kuala Lumpur")

        op_area_select = Select(driver.find_element(By.ID, "companyLocationId"))
        options = [o for o in op_area_select.options if o.get_attribute("value")]
        if options:
            op_area_select.select_by_index(1)

        # ── Step 7: Click "Add Record" ────────────────────────────────
        driver.find_element(
            By.XPATH, "//button[normalize-space()='Add Record']"
        ).click()

        # ── Step 8: Verify validation error is shown ──────────────────
        error_alert = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[class*='AlertDescription']")
            )
        )
        assert "Weather record added successfully" not in error_alert.text, (
            "Record was added despite non-numeric values — expected rejection."
        )
        # The error message should indicate a validation failure
        assert error_alert.text.strip() != "", (
            "Expected a validation error message, but the alert was empty."
        )

        print("TC-UC9-012 Non-Numeric Input Validation - PASS")