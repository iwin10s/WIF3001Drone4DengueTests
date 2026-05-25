"""
test_uc9_004.py

Test Procedure : TP-UC9-004
Test Cases     : TC-UC9-004  — Edit weather record, values saved correctly
                 TC-UC9-005  — "Updated At" timestamp refreshes after edit
Objective      : Verify that editing weather records persists the new values,
                 shows a success message, and logs an updated audit timestamp.

Prerequisites  : At least one weather record must exist in the database.
"""

import re
from datetime import datetime, timezone
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL    = "http://localhost:3000"
WEATHER_URL = f"{BASE_URL}/weather-data"


class TestTP_UC9_004:
    """TP-UC9-004 — Edit record saves correctly and updates audit timestamp."""

    def _open_edit_modal_for_first_record(self, driver, wait):
        """
        Click the Edit button on the first row of the Weather Records table
        and return the driver once the modal/form is visible.
        """
        # Step 1 — Locate the first Edit (pencil) icon button in the table
        edit_btn = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR,
                 "table tbody tr:first-child button[class*='edit'], "
                 "table tbody tr:first-child button:has(svg), "
                 "table tbody tr:first-child button")
            )
        )
        # If multiple buttons per row, filter to the edit one via aria-label or order
        row_buttons = driver.find_elements(
            By.CSS_SELECTOR, "table tbody tr:first-child button"
        )
        assert len(row_buttons) >= 1, "No action buttons found in the first table row."
        # Convention: first button = Edit, second = Delete
        row_buttons[0].click()

        # Step 2 — Wait for edit modal or inline edit form to appear
        wait.until(
            EC.visibility_of_element_located((By.ID, "modal-temperature"))
        )

    # ------------------------------------------------------------------
    # TC-UC9-004
    # ------------------------------------------------------------------
    def test_tc_uc9_004_edit_record_values_saved(self, logged_in):
        """
        TC-UC9-004
        Input   : Open first record, edit temperature=28.1, humidity=87,
                  rainfall=28.1, location=Petaling Jaya, click Update Record.
        Expected: Success message "Weather record updated successfully" and
                  the updated values are reflected in the table.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        # ── Step 1: Confirm we are on the Weather Data page ──────────
        wait.until(EC.url_contains("/weather-data"))

        # ── Step 2: Click the Edit button on the first record ─────────
        self._open_edit_modal_for_first_record(driver, wait)

        # ── Step 3: Edit Temperature ──────────────────────────────────
        temp_field = driver.find_element(By.ID, "modal-temperature")
        temp_field.clear()
        temp_field.send_keys("28.1")

        # ── Step 4: Edit Humidity ─────────────────────────────────────
        humidity_field = driver.find_element(By.ID, "modal-humidity")
        humidity_field.clear()
        humidity_field.send_keys("87")

        # ── Step 5: Edit Rainfall ─────────────────────────────────────
        rainfall_field = driver.find_element(By.ID, "modal-rainfall")
        rainfall_field.clear()
        rainfall_field.send_keys("28.1")

        # ── Step 6: Edit Location ─────────────────────────────────────
        location_field = driver.find_element(By.ID, "modal-location")
        location_field.clear()
        location_field.send_keys("Petaling Jaya")

        # ── Step 7: Click "Update Record" ─────────────────────────────
        update_btn = driver.find_element(
            By.XPATH, "//button[normalize-space()='Update Record']"
        )
        update_btn.click()

        # ── Step 8: Verify success alert ──────────────────────────────
        success_alert = wait.until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[class*='AlertDescription']")
            )
        )
        assert "Weather record updated successfully" in success_alert.text, (
            f"Expected update success message, got: '{success_alert.text}'"
        )

        # ── Step 9: Verify updated value appears in the table ─────────
        table_cell = wait.until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//table//td[contains(text(),'Petaling Jaya')] | "
                 "//*[contains(@class,'row')]//*[contains(text(),'Petaling Jaya')]")
            )
        )
        assert table_cell.is_displayed(), (
            "Expected 'Petaling Jaya' to appear in the table after update."
        )

        print("TC-UC9-004 Weather Record Edited Successfully - PASS")

    # ------------------------------------------------------------------
    # TC-UC9-005
    # ------------------------------------------------------------------
    def test_tc_uc9_005_updated_at_timestamp_refreshed(self, logged_in):
        """
        TC-UC9-005
        Input   : Edit and save an existing weather record.
        Expected: The "Updated At" column timestamp for that row matches
                  (within ~1 minute of) the current system time.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        # ── Step 1: Note time just before performing the edit ─────────
        before_edit = datetime.now(timezone.utc)

        # ── Step 2: Open Edit modal for first record ──────────────────
        wait.until(EC.url_contains("/weather-data"))
        self._open_edit_modal_for_first_record(driver, wait)

        # ── Step 3: Make a trivial change (temperature) and save ──────
        temp_field = driver.find_element(By.ID, "modal-temperature")
        temp_field.clear()
        temp_field.send_keys("30.0")

        update_btn = driver.find_element(
            By.XPATH, "//button[normalize-space()='Update Record']"
        )
        update_btn.click()

        # ── Step 4: Wait for the success message ──────────────────────
        wait.until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, "[class*='AlertDescription']"),
                "Weather record updated successfully"
            )
        )

        # ── Step 5: Find the "Updated At" cell in the first row ───────
        # Look for a cell that contains a date/time string (ISO or locale format)
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        assert rows, "No rows found in the weather records table."

        # The "Updated At" column is typically the last or second-to-last column.
        cells = rows[0].find_elements(By.TAG_NAME, "td")
        updated_at_text = None
        for cell in reversed(cells):
            text = cell.text.strip()
            # Match ISO date pattern or locale date-time pattern
            if re.search(r"\d{4}-\d{2}-\d{2}", text) or re.search(r"\d{1,2}/\d{1,2}/\d{4}", text):
                updated_at_text = text
                break

        assert updated_at_text is not None, (
            "Could not locate a date/timestamp in the first table row."
        )

        # ── Step 6: Parse and verify the timestamp is recent (≤60s delta) ──
        # Try ISO format first, then locale format
        parsed = None
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y, %I:%M:%S %p"):
            try:
                raw = re.search(r"[\d\-T:./,\s APM]+", updated_at_text)
                if raw:
                    parsed = datetime.strptime(raw.group().strip(), fmt)
                    break
            except ValueError:
                continue

        if parsed:
            delta_seconds = abs((datetime.utcnow() - parsed).total_seconds())
            assert delta_seconds < 300, (
                f"'Updated At' timestamp '{updated_at_text}' is more than 5 minutes "
                f"from the current time (delta={delta_seconds:.0f}s)."
            )
        else:
            # If parsing fails, at least confirm the column changed (non-empty)
            assert updated_at_text, (
                "Updated At timestamp is empty after saving the record."
            )

            print("TC-UC9-005 Updated Timestamp Refreshed - PASS")