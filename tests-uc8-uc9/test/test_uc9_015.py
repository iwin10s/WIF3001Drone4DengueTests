"""
Test Procedure ID : TP-UC9-015
Objective         : Verify rainfall data range rules at the minimum lower boundary
                    limits (0mm is accepted, while negative values like -0.1mm are rejected)
Test Cases        : TC-UC9-021, TC-UC9-022
"""

import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:3000"
DEFAULT_WAIT = 10


class TestRainfallLowerBoundary:

    def test_rainfall_lower_boundary_validation(self, driver, fill_weather_form):

        wait = WebDriverWait(driver, DEFAULT_WAIT)

        driver.get(BASE_URL + "/weather-data?no_auto_fetch=true")

        # ── Valid lower boundary (0) ──────────────────────────────────────
        test_date_1 = f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

        fill_weather_form(
            date=test_date_1,
            temperature="25",
            humidity="75",
            rainfall="0",
            location="Kuala Lumpur"
        )

        submit_btn = wait.until(
            EC.element_to_be_clickable((By.ID, "submit-weather-btn"))
        )

        submit_btn.click()

        # Confirm success notification
        success_msg = wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(text(),'Weather record added successfully')]"
                )
            )
        )

        assert success_msg.is_displayed()
        print("TC-UC9-021 Rainfall Lower Boundary Accepted (0mm) - PASS")

        # ── Invalid lower boundary (-0.1) ────────────────────────────────
        test_date_2 = f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

        # Re-open form for second test
        driver.find_element(By.ID, "add-new-record-btn").click()

        fill_weather_form(
            date=test_date_2,
            temperature="25",
            humidity="75",
            rainfall="-0.1",
            location="Kuala Lumpur"
        )

        submit_btn.click()

        # Confirm error notification
        error_msg = wait.until(
            EC.visibility_of_element_located(
                (
                    By.XPATH,
                    "//*[contains(text(),'Rainfall cannot be negative')]"
                )
            )
        )

        assert error_msg.is_displayed()
        print("TC-UC9-022 Rainfall Lower Boundary Rejected (-0.1mm) - PASS")