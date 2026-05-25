"""
Test Procedure ID : TP-UC9-013
Objective         : Verify humidity data range rules at the lower boundary
                    limits (0% is accepted, while -1% is rejected)
Test Cases        : TC-UC9-017, TC-UC9-018
"""

import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:3000"
DEFAULT_WAIT = 10


class TestHumidityLowerBoundary:

    def test_humidity_lower_boundary_validation(self, driver, fill_weather_form):

        wait = WebDriverWait(driver, DEFAULT_WAIT)

        driver.get(BASE_URL + "/weather-data?no_auto_fetch=true")

        # ── Valid lower boundary (0) ─────────────────────────────────────
        test_date_1 = f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

        fill_weather_form(
            date=test_date_1,
            temperature="25",
            humidity="0",
            rainfall="12.5",
            location="Kuala Lumpur"
        )

        submit_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "submit-weather-btn"))
        )

        submit_btn.click()

        success_msg = wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(text(),'Weather record added successfully')]"
                )
            )
        )

        assert success_msg.is_displayed()

        print("TC-UC9-017 Humidity Lower Boundary Accepted (0%) - PASS")

        # ── Invalid lower boundary (-1) ──────────────────────────────────
        test_date_2 = f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

        fill_weather_form(
            date=test_date_2,
            temperature="25",
            humidity="-1",
            rainfall="12.5",
            location="Kuala Lumpur"
        )

        submit_btn.click()

        error_msg = wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(text(),'Humidity must be between')]"
                )
            )
        )

        assert error_msg.is_displayed()

        print("TC-UC9-018 Humidity Lower Boundary Rejected (-1%) - PASS")