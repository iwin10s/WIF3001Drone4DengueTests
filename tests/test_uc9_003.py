"""
test_uc9_003.py

Test Procedure : TP-UC9-003
Test Case      : TC-UC9-003
Objective      : Verify that valid weather data entered manually through
                 the form input is stored successfully and displayed in the table.
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

BASE_URL       = "http://localhost:3000"
WEATHER_URL    = f"{BASE_URL}/weather-data"
ADMIN_EMAIL    = "admin1@drone4dengue.com"
ADMIN_PASSWORD = "adminpass1"
DEFAULT_WAIT   = 10  


# Valid form values as specified in the test procedure
VALID_DATE        = "2025-05-21"
VALID_TEMPERATURE = "-28.5"
VALID_HUMIDITY    = "75"
VALID_RAINFALL    = "12.5"
VALID_LOCATION    = "Kuala Lumpur"
VALID_OP_AREA     = "Kuala Lumpur Central"   # partial match used in select search


class TestTP_UC9_003:
    """TP-UC9-003 — Manual form input creates a weather record successfully."""

    def test_tc_uc9_003_add_record_manually(self, logged_in):
        """
        TC-UC9-003
        Input   : date=2025-05-21, temperature=-28.5, humidity=75,
                  rainfall=12.5, location=Kuala Lumpur,
                  operational area=Kuala Lumpur Central - Kuala Lumpur City Center, Malaysia
        Expected: Success message "Weather record added successfully" and the
                  new record is visible in the Weather Records table.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        # ── Step 1: Confirm we are on the Weather Data page ──────────
        wait.until(EC.url_contains("/weather-data"))

        # ── Step 2: Click "Add New Record" button ─────────────────────
        add_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[normalize-space()='Add New Record']")
            )
        )
        add_btn.click()

        # ── Step 3: Wait for the inline add form to appear ────────────
        date_input = wait.until(
            EC.visibility_of_element_located((By.ID, "date"))
        )

        # ── Step 4: Fill in Date ───────────────────────────────────────
        date_input.clear()
        date_input.send_keys(VALID_DATE)

        # ── Step 5: Fill in Temperature ───────────────────────────────
        temp_input = driver.find_element(By.ID, "temperature")
        temp_input.clear()
        temp_input.send_keys(VALID_TEMPERATURE)

        # ── Step 6: Fill in Humidity ───────────────────────────────────
        humidity_input = driver.find_element(By.ID, "humidity")
        humidity_input.clear()
        humidity_input.send_keys(VALID_HUMIDITY)

        # ── Step 7: Fill in Rainfall ───────────────────────────────────
        rainfall_input = driver.find_element(By.ID, "rainfall")
        rainfall_input.clear()
        rainfall_input.send_keys(VALID_RAINFALL)

        # ── Step 8: Fill in Location ───────────────────────────────────
        location_input = driver.find_element(By.ID, "location")
        location_input.clear()
        location_input.send_keys(VALID_LOCATION)

        # ── Step 9: Select Operational Area dropdown ──────────────────
        op_area_select = Select(driver.find_element(By.ID, "companyLocationId"))
        # Find the option containing "Kuala Lumpur Central"
        selected = False
        for option in op_area_select.options:
            if VALID_OP_AREA.lower() in option.text.lower():
                op_area_select.select_by_visible_text(option.text)
                selected = True
                break
        assert selected, (
            f"Could not find Operational Area option containing '{VALID_OP_AREA}'."
        )

        # ── Step 10: Click "Add Record" button ────────────────────────
        add_record_btn = driver.find_element(
            By.XPATH, "//button[normalize-space()='Add Record']"
        )
        add_record_btn.click()

        # ── Step 11: Verify success alert message ─────────────────────
        success_alert = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[class*='AlertDescription']")
            )
        )
        assert "Weather record added successfully" in success_alert.text, (
            f"Expected success message, got: '{success_alert.text}'"
        )

        # ── Step 12: Verify the new record appears in the table ───────
        # The table should now contain a row with the location we entered.
        table_content = wait.until(
            EC.presence_of_element_located(
                (By.XPATH,
                 f"//table//td[contains(text(),'{VALID_LOCATION}')] | "
                 f"//*[contains(@class,'row')]//*[contains(text(),'{VALID_LOCATION}')]")
            )
        )
        assert table_content.is_displayed(), (
            f"Expected the new record with location '{VALID_LOCATION}' to appear in the table."
        )

        print("TC-UC9-003 Manual Form Input Creates Weather Record Successfully - PASS")