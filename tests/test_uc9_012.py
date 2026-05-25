"""
Test Procedure ID : TP-UC9-012
Objective         : Verify temperature data range rules at the upper boundary
                    limits (60°C is accepted, while 61°C is rejected)
Test Cases        : TC-UC9-015, TC-UC9-016
"""

import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:3000"
DEFAULT_WAIT = 10


class TestTemperatureUpperBoundary:

    def test_temperature_upper_boundary_validation(self, driver, fill_weather_form):

        wait = WebDriverWait(driver, DEFAULT_WAIT)

        driver.get(BASE_URL + "/weather-data?no_auto_fetch=true")

        # ── Valid upper boundary (60) ────────────────────────────────────
        test_date_1 = f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

        fill_weather_form(
            date=test_date_1,
            temperature="60",
            humidity="75",
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

        print("TC-UC9-015 Temperature Upper Boundary Accepted (60°C) - PASS")


        # ── Invalid upper boundary (61) ──────────────────────────────────
        test_date_2 = f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

        fill_weather_form(
            date=test_date_2,
            temperature="61",
            humidity="75",
            rainfall="12.5",
            location="Kuala Lumpur"
        )

        submit_btn.click()

        error_msg = wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(text(),'Temperature must be between')]"
                )
            )
        )

        assert error_msg.is_displayed()

        print("TC-UC9-016 Temperature Upper Boundary Rejected (61°C) - PASS")