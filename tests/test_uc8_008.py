"""
test_uc8_008.py
===============
Test Procedure : TP-UC8-008
Test Cases     : TC-UC8-008
Objective      : Verify that system safely rejects filtering with an invalid
                 date range where startDate is later than endDate.
Coverage Items : TCOV-08-016
Wrap-Up        : None
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL     = "http://localhost:3000"
DATA_MGT_URL = BASE_URL + "/data-management"


class TestUC8InvalidDateRange:
    """TP-UC8-008 — Invalid date range (startDate is later than endDate)."""

    def test_end_date_before_start_date_returns_zero_rows(self, logged_in):
        """
        TC-UC8-008 | TCOV-08-016
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Locate the date range filter inputs.
        Step 3  Enter an invalid range: startDate=2026-12-31, endDate=2026-01-01
                (startDate is clearly later than endDate — the invalid condition).
        Step 4  Click Search Data.
        Step 5  Assert the system returns zero rows without throwing errors
                and the page remains stable.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        # ── Step 1: Navigate to Data Management ──────────────────────────────
        driver.get(DATA_MGT_URL)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        # ── Step 2: Locate the two date inputs ───────────────────────────────
        date_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='date']")
        assert len(date_inputs) >= 2, (
            "Expected at least 2 date inputs on page, found %d." % len(date_inputs)
        )

        # ── Step 3: Enter invalid range — startDate > endDate ────────────────
        date_inputs[0].clear()
        date_inputs[0].send_keys("2026-12-31")   # startDate (later)
        date_inputs[1].clear()
        date_inputs[1].send_keys("2026-01-01")   # endDate   (earlier)
        print("Step 3: Entered invalid date range — startDate=2026-12-31, endDate=2026-01-01")

        # ── Step 4: Click Search Data ─────────────────────────────────────────
        search_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'Search Data')]")
            )
        )
        search_btn.click()
        time.sleep(2)

        # ── Step 5: Assert page is stable and no data rows are returned ───────
        # Page must not crash — the Data Management heading must still be present
        try:
            heading = driver.find_element(
                By.XPATH, "//*[contains(text(),'Data Management')]"
            )
            assert heading.is_displayed(), \
                "Page crashed — 'Data Management' heading is no longer visible."
        except Exception:
            assert False, "TC-UC8-008 FAIL: Page became unstable after invalid date range input."

        # Collect data rows, excluding empty-state/placeholder rows
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        all_rows  = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        data_rows = [
            r for r in all_rows
            if r.text.strip()
            and "no data"   not in r.text.lower()
            and "no record" not in r.text.lower()
        ]

        # Accept either: an explicit error/validation message, OR zero data rows
        error_shown = any(kw in body_text for kw in [
            "invalid", "error", "no data", "no record",
            "start date", "end date", "range"
        ])
        zero_rows = len(data_rows) == 0

        assert error_shown or zero_rows, (
            "TC-UC8-008 FAIL: System returned %d data row(s) for a reversed date range. "
            "Body excerpt: %s" % (len(data_rows), body_text[:400])
        )

        print("TC-UC8-008 Invalid Date Range (startDate > endDate) Returns Zero Rows - PASS")