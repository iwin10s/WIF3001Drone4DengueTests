"""
test_uc8_016.py
===============
Test Procedure : TP-UC8-016
Test Cases     : TC-UC8-016
Objective      : Verify that system displays granular dengue record information
                 correctly for each record when admin views the details.
Coverage Items : TCOV-08-032
Wrap-Up        : None
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL     = "http://localhost:3000"
DATA_MGT_URL = BASE_URL + "/data-management"

# Granular field labels rendered inside DetailsModal (page.tsx uppercase labels)
# The modal renders these as: <label class="text-sm font-semibold text-gray-500 uppercase">
EXPECTED_LABEL_TEXTS = [
    "Date",
    "Location",
    "State",
    "Status/Type",
    "Active Cases",
    "Total Cases",
]


class TestUC8DetailModal:
    """TP-UC8-016 — Detail modal view for a dengue record."""

    def test_eye_icon_opens_detail_modal_with_all_parameters(self, logged_in):
        """
        TC-UC8-016 | TCOV-08-032
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Apply Search Data to load records into the table.
        Step 3  Click the 'View' button (eye-icon, title='View Details') on
                the first data row.
        Step 4  Assert the 'Record Details' overlay modal opens.
        Step 5  Assert the modal contains all expected granular field labels.
        Step 6  Close the modal via the Close button.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        # ── Step 1: Navigate to Data Management ──────────────────────────────
        driver.get(DATA_MGT_URL)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        # ── Step 2: Load records via Search Data ─────────────────────────────
        search_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(),'Search Data')]")
            )
        )
        search_btn.click()
        time.sleep(2)

        # Confirm at least one data row exists before proceeding
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        assert rows, (
            "TC-UC8-016 FAIL: No records in the table. "
            "Populate the database before running this test."
        )

        # ── Step 3: Click the 'View' button (title='View Details') on row 1 ──
        # page.tsx renders:
        #   <button title="View Details">
        #     <FiEye size={16} /> View
        #   </button>
        first_row = rows[0]
        view_btn = first_row.find_element(
            By.XPATH,
            ".//button[@title='View Details' or contains(text(),'View')]"
        )
        view_btn.click()

        # ── Step 4: Assert 'Record Details' overlay modal opens ───────────────
        # page.tsx modal root:
        #   <div class="fixed inset-0 bg-black bg-opacity-50 ... z-50 ...">
        #     <h2 ...>Record Details</h2>
        modal_heading = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//h2[contains(text(),'Record Details')]")
            )
        )
        assert modal_heading.is_displayed(), (
            "TC-UC8-016 FAIL: 'Record Details' modal heading is not visible "
            "after clicking View."
        )

        # Grab the modal container via the fixed overlay div
        modal = driver.find_element(
            By.XPATH,
            "//div[contains(@class,'fixed') and contains(@class,'inset-0') "
            "and contains(@class,'z-50')]"
        )

        # ── Step 5: Assert all granular field labels appear in the modal ──────
        # page.tsx renders each field as:
        #   <label class="text-sm font-semibold text-gray-500 uppercase tracking-wide">
        #     Date / Location / State / Status/Type / Active Cases / Total Cases
        #   </label>
        modal_text = modal.text  # preserve original case for label matching
        missing_fields = [
            label for label in EXPECTED_LABEL_TEXTS
            if label.upper() not in modal_text.upper()
        ]
        assert not missing_fields, (
            "TC-UC8-016 FAIL: The following field labels are missing from the "
            "modal: %s\nModal text excerpt: %s" % (missing_fields, modal_text[:600])
        )


        # ── Step 6: Close the modal via the 'Close' button in the footer ──────
        # page.tsx footer renders:
        #   <Button onClick={onClose}>Close</Button>
        close_btn = modal.find_element(
            By.XPATH, ".//button[contains(text(),'Close')]"
        )
        close_btn.click()
        time.sleep(1)

        # Confirm modal is gone
        modal_still_visible = driver.find_elements(
            By.XPATH, "//h2[contains(text(),'Record Details')]"
        )
        assert not modal_still_visible or not modal_still_visible[0].is_displayed(), (
            "TC-UC8-016 FAIL: Modal did not close after clicking the Close button."
        )

        print("TC-UC8-016 Eye Icon Opens Detail Modal With All Parameters - PASS")