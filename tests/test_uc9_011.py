"""
Test Procedure ID : TP-UC9-011
Objective         : Verify temperature data range rules at the lower boundary
                    limits (-50°C is accepted, while -51°C is rejected)
Test Cases        : TC-UC9-013, TC-UC9-014
"""

import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = "http://localhost:3000"
DEFAULT_WAIT = 10


# ---------------------------------------------------------------------------
# TP-UC9-011
# Temperature lower boundary validation
# ---------------------------------------------------------------------------

class TestTemperatureLowerBoundary:

    def test_temperature_lower_boundary_validation(self, driver, fill_weather_form):

        wait = WebDriverWait(driver, DEFAULT_WAIT)

        # ── Step 1 : Open Weather Data page ──────────────────────────────
        driver.get(BASE_URL + "/weather-data?no_auto_fetch=true")

        # ── Step 2 : Submit valid lower boundary value (-50) ─────────────
        fill_weather_form(
            date="2000-01-01",
            temperature="-50",
            humidity="75",
            rainfall="12.5",
            location="Kuala Lumpur"
        )

        submit_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "submit-weather-btn"))
        )

        submit_btn.click()

        # ── Step 3 : Verify success message ──────────────────────────────
        success_msg = wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(text(),'Weather record added successfully')]"
                )
            )
        )

        assert success_msg.is_displayed(), (
            "Temperature = -50 should be accepted."
        )

        print("TC-UC9-013 Temperature Lower Boundary Accepted (-50°C) - PASS")

        # ── Step 4 : Submit invalid lower boundary value (-51) ───────────
        test_date_2 = f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

        fill_weather_form(
            date=test_date_2,
            temperature="-51",
            humidity="75",
            rainfall="12.5",
            location="Kuala Lumpur"
        )

        submit_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "submit-weather-btn"))
        )

        submit_btn.click()

        # ── Step 5 : Verify validation error message ─────────────────────
        error_msg = wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(text(),'Temperature must be between')]"
                )
            )
        )

        assert error_msg.is_displayed(), (
            "Temperature = -51 should be rejected."
        )

        print("TC-UC9-014 Temperature Lower Boundary Rejected (-51°C) - PASS")