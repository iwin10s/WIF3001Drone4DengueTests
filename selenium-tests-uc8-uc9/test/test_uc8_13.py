"""
test_uc8_013.py
===============
Test Procedure : TP-UC8-013
Test Cases     : TC-UC8-013
Objective      : Verify that system updates the edited data in the database
                 and updates the data table after data changes.
Coverage Items : TCOV-08-027
Wrap-Up        : None

Implementation note:
    page.tsx has NO edit button or edit form in the UI — the Actions column
    renders only a single read-only 'View Details' button per row, and the
    DetailsModal is display-only (spans, no inputs).

    Edit is therefore exercised via the REST API directly:
      PATCH /dengue-data/:id  { activeCases: 100 }

    Token retrieval:
      page.tsx reads localStorage.getItem('token').
      The logged_in fixture submits the login form; AuthContext then writes
      the token to localStorage asynchronously. We poll localStorage with a
      WebDriverWait until the token is present before making any API calls.
"""

import time
import requests
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL     = "http://localhost:3000"
API_URL      = "http://localhost:4000"
DATA_MGT_URL = BASE_URL + "/data-management"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_auth_token(driver, timeout=15):
    """
    Poll localStorage every 500 ms until the 'token' key is populated.
    AuthContext writes the token asynchronously after the login form
    submits, so a bare execute_script call immediately after login returns None.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        token = driver.execute_script("return localStorage.getItem('token');")
        if token:
            return token
        time.sleep(0.5)
    raise AssertionError(
        "TC-UC8-013 SETUP FAIL: 'token' not found in localStorage after "
        f"{timeout}s. Ensure the app's AuthContext stores the JWT under the "
        "key 'token' and that the logged_in fixture has fully completed login."
    )


def _load_records_via_search(driver, wait):
    """Click 'Search Data' and wait for at least one table row to appear."""
    search_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'Search Data')]")
        )
    )
    search_btn.click()
    wait.until(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "table tbody tr")
    ))
    time.sleep(1)


def _get_first_record(driver, token):
    """
    Fetch the first record from the API using the auth token.
    Returns (id, original_activeCases).
    """
    resp = requests.get(
        f"{API_URL}/dengue-data?page=1&limit=1",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert resp.status_code == 200, (
        f"TC-UC8-013 SETUP FAIL: Could not fetch records from API. "
        f"Status: {resp.status_code}, Body: {resp.text[:200]}"
    )
    data = resp.json().get("data", [])
    assert data, (
        "TC-UC8-013 SETUP FAIL: API returned zero records. "
        "Populate the database before running this test."
    )
    return data[0]["id"], data[0].get("activeCases")


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestUC8EditRecord:
    """TP-UC8-013 — Edit existing record via API and verify table update."""

    def test_edit_active_cases_updates_data_table(self, logged_in):
        """
        TC-UC8-013 | TCOV-08-027
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Wait for the auth token to be written to localStorage by
                AuthContext (polled until present, max 15 s).
        Step 3  Click 'Search Data' to load the record list.
        Step 4  Fetch the first record's id and current activeCases from API.
        Step 5  PATCH /dengue-data/:id with { activeCases: 100 }.
        Step 6  Assert API returns 200/201/204.
        Step 7  Re-trigger 'Search Data' so the table refreshes.
        Step 8  Assert '100' appears in the Active/Total Cases column
                (td:nth-child(3)) without a manual page reload.
        Step 9  Teardown — restore the original activeCases value.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        # ── Step 1: Navigate to Data Management ──────────────────────────────
        driver.get(DATA_MGT_URL)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        # ── Step 2: Wait for the JWT to land in localStorage ─────────────────
        # AuthContext writes localStorage['token'] asynchronously after login.
        # Polling avoids a race condition where execute_script runs before
        # the token is stored.
        token = _wait_for_auth_token(driver, timeout=15)

        # ── Step 3: Load records via Search Data ─────────────────────────────
        _load_records_via_search(driver, wait)

        # ── Step 4: Fetch first record id from API ────────────────────────────
        record_id, original_active_cases = _get_first_record(driver, token)

        # ── Step 5: PATCH activeCases = 100 via REST API ──────────────────────
        patch_resp = requests.patch(
            f"{API_URL}/dengue-data/{record_id}",
            json={"activeCases": 100},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            timeout=10,
        )

        # ── Step 6: Assert API accepted the update ────────────────────────────
        assert patch_resp.status_code in (200, 201, 204), (
            f"TC-UC8-013 FAIL: API rejected the edit. "
            f"Status: {patch_resp.status_code}, Body: {patch_resp.text[:300]}"
        )
        print("API accepted edit — activeCases updated to 100")

        # ── Step 7: Re-trigger Search Data to refresh the table ──────────────
        _load_records_via_search(driver, wait)

        # ── Step 8: Assert '100' appears in Active/Total Cases column ─────────
        # Table column order (page.tsx thead):
        # 1:Date | 2:Location | 3:Active/Total Cases | 4:Cumulative Duration
        # | 5:Type | 6:State | 7:Actions
        # The activeCases value is rendered inside td:nth-child(3) as a <span>
        active_case_cells = driver.find_elements(
            By.CSS_SELECTOR, "table tbody tr td:nth-child(3)"
        )
        cell_values = [c.text.strip() for c in active_case_cells]

        assert any("100" in v for v in cell_values), (
            "TC-UC8-013 FAIL: Updated activeCases=100 not visible in the "
            "Active/Total Cases column after re-loading the table.\n"
            f"Column values found: {cell_values}"
        )

        # ── Step 9: Teardown — restore the original activeCases value ─────────
        if original_active_cases is not None:
            restore_resp = requests.patch(
                f"{API_URL}/dengue-data/{record_id}",
                json={"activeCases": original_active_cases},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                },
                timeout=10,
            )

        print("TC-UC8-013 Edit Active Cases Updates Data Table - PASS")