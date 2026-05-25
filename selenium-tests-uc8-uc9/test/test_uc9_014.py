"""
Test Procedure ID : TP-UC9-014
Objective         : Verify humidity data range rules at the upper boundary
                    limits (100% is accepted, while 101% is rejected)
Test Cases        : TC-UC9-019, TC-UC9-020
"""

import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:3000"
DEFAULT_WAIT = 10


class TestHumidityUpperBoundary:

    def test_humidity_upper_boundary_validation(self, driver, fill_weather_form):

        wait = WebDriverWait(driver, DEFAULT_WAIT)

        driver.get(BASE_URL + "/weather-data?no_auto_fetch=true")

        # ── Valid upper boundary (100) ───────────────────────────────────
        test_date_1 = f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

        fill_weather_form(
            date=test_date_1,
            temperature="25",
            humidity="100",
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

        print("TC-UC9-019 Humidity Upper Boundary Accepted (100%) - PASS")

        # ── Invalid upper boundary (101) ─────────────────────────────────
        test_date_2 = f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

        fill_weather_form(
            date=test_date_2,
            temperature="25",
            humidity="101",
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

        print("TC-UC9-020 Humidity Upper Boundary Rejected (101%) - PASS")