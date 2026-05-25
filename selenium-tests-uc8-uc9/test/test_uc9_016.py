"""
Test Procedure ID : TP-UC9-016
Objective         : Verify that an existing weather record can be removed from
                    the system successfully upon admin deletion confirmation.
Test Cases        : TC-UC9-025
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:3000"
WEATHER_URL = f"{BASE_URL}/weather-data"
DEFAULT_WAIT = 10


class TestDeleteWeatherRecord:
    """TP-UC9-016 — Weather record deleted successfully."""

    def test_tc_uc9_025_delete_record_successfully(self, driver):
        """
        TC-UC9-025
        Input   : Click Delete (trash) icon on a table row → confirm "OK".
        Expected: Toast "Weather record deleted successfully" and the row
                  vanishes from the table.
        """
        wait = WebDriverWait(driver, DEFAULT_WAIT)

        driver.get(WEATHER_URL + "?no_auto_fetch=true")

        # ── Step 1: Wait for at least one table row to be present ─────
        # Note: If table is empty, a record must be added first via test setup
        first_row = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "table tbody tr")
            )
        )
        
        # Capture unique cell text for verification
        cells = first_row.find_elements(By.TAG_NAME, "td")
        row_identifier = cells[0].text.strip() if cells else ""

        # ── Step 2: Click the Delete (trash) icon ───
        # Convention: row has 2 action buttons — index 0 = Edit, index 1 = Delete
        row_buttons = first_row.find_elements(By.TAG_NAME, "button")
        assert len(row_buttons) >= 2, (
            f"Expected at least 2 action buttons, found {len(row_buttons)}."
        )
        delete_btn = row_buttons[1]
        delete_btn.click()

        # ── Step 3: Handle browser confirm() dialog ────────
        alert = wait.until(EC.alert_is_present())
        alert.accept()

        # ── Step 4: Verify success message ────────────────────────────
        success_alert = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[class*='AlertDescription']")
            )
        )
        assert "Weather record deleted successfully" in success_alert.text

        # ── Step 5: Verify the row is no longer in the table ──────────
        time.sleep(1) # Allow DOM to refresh after delete
        rows_after = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        
        if row_identifier:
            remaining_texts = []
            for r in rows_after:
                tds = r.find_elements(By.TAG_NAME, "td")
                if tds:
                    remaining_texts.append(tds[0].text.strip())
            
            assert row_identifier not in remaining_texts, (
                f"Deleted row '{row_identifier}' still exists in the table."
            )

        print("TC-UC9-025 Weather Record Deleted Successfully - PASS")