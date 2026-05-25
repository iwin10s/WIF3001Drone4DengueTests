"""
test_uc8_004.py
===============
Test Procedure : TP-UC8-004
Test Cases     : TC-UC8-004
Objective      : Verify that admin can create a new dengue data record via
                 manual (direct API) input, and that the new record appears
                 in the Data Management data table.
Coverage Items : TCOV-08-006

Frontend note
-------------
  page.tsx contains no manual create form.  Per the SRS, manual record
  creation is performed by POSTing directly to the backend REST API:
    POST http://localhost:4000/dengue-data

  Auth requirements enforced here and in conftest.logged_in:
    - Admin MUST be authenticated (JWT in localStorage['token'])
    - companyId MUST exist (in localStorage['company']['id'])
    - Both are verified before any API call is made

Wrap-Up
-------
  The created record is deleted via DELETE /dengue-data after assertion.
"""

import os
import json
import time
import pytest
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

API_URL      = os.getenv("API_BASE_URL", "http://localhost:4000")
BASE_URL     = os.getenv("APP_BASE_URL", "http://localhost:3000")
DATA_MGT_URL = BASE_URL + "/data-management"


def _get_auth(driver):
    """
    Read token and companyId from the browser's localStorage.

    localStorage keys (written by React AuthContext after login):
      'token'   -> JWT string
      'company' -> JSON string: { "id": "<companyId>", "name": "...", ... }

    Asserts both exist — test fails immediately with a clear message if not.
    These checks mirror the UC-8 pre-conditions:
      Admin MUST be authenticated / JWT token MUST exist /
      companyId MUST exist in token.
    """
    token        = driver.execute_script("return localStorage.getItem('token');")
    company_json = driver.execute_script("return localStorage.getItem('company');")

    assert token, (
        "TC-UC8-004 PRE-CONDITION FAIL: Admin is not authenticated.\n"
        "localStorage['token'] is missing. Ensure login succeeded."
    )
    assert company_json, (
        "TC-UC8-004 PRE-CONDITION FAIL: companyId not found.\n"
        "localStorage['company'] is missing. Ensure AuthContext stores company after login."
    )

    company_id = json.loads(company_json).get("id", "")
    assert company_id, (
        "TC-UC8-004 PRE-CONDITION FAIL: 'company' JSON has no 'id' field.\n"
        "company value: %s" % company_json
    )

    return token, company_id


def _api_headers(token):
    return {
        "Authorization": "Bearer " + token,
        "Content-Type":  "application/json",
    }


def _delete_record(token, location="Batu Pahat", date="2026-05-21"):
    """Wrap-up: remove the test record from the DB."""
    try:
        resp = requests.delete(
            API_URL + "/dengue-data",
            params={"date": date, "location": location},
            headers=_api_headers(token),
            timeout=10,
        )
        if resp.status_code not in (200, 204, 404):
            print("[WARN] Wrap-up DELETE returned %d" % resp.status_code)
    except Exception as exc:
        print("[WARN] Wrap-up failed: %s" % exc)


class TestUC8ManualCreate:
    """TP-UC8-004 — Manual record creation via backend API."""

    def test_api_post_creates_record_visible_in_data_table(self, logged_in):
        """
        TC-UC8-004 | TCOV-08-006
        ─────────────────────────────────────────────────────────────────────
        Pre-conditions verified before test body:
          - Admin authenticated  (JWT token in localStorage['token'])
          - companyId present    (localStorage['company']['id'])

        Step 1  Navigate to /data-management (done by logged_in fixture).
        Step 2  Read JWT token and companyId from localStorage.
        Step 3  POST a new record to POST /dengue-data with the real token.
        Step 4  Assert the API returns HTTP 200 or 201.
        Step 5  Click 'Search Data' in the browser to refresh the table.
        Step 6  Assert 'Batu Pahat' row is visible in the data table.
        Step 7  Wrap-up: DELETE the created record.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        # ── Step 2: Read token and companyId — fails fast if missing ──────────
        token, company_id = _get_auth(driver)
        print("[INFO] Authenticated. companyId=%s" % company_id)

        # ── Step 3: POST new record directly to backend API ───────────────────
        new_record = {
            "date":         "2026-05-21",
            "location":     "Batu Pahat",
            "activeCases":  10,
            "totalCases":   30,
            "status":       "Active Cases",
            "source":       "manual",
            "coverageArea": "Batu Pahat",
            "latitude":     1.8572,
            "longitude":    102.9325,
            "companyId":    company_id,   # taken from localStorage — not hardcoded
        }

        resp = requests.post(
            API_URL + "/dengue-data",
            json=new_record,
            headers=_api_headers(token),
            timeout=10,
        )

        # ── Step 4: Assert API accepted the record ────────────────────────────
        assert resp.status_code in (200, 201), (
            "TC-UC8-004 FAIL: POST /dengue-data returned HTTP %d.\n"
            "Payload  : %s\n"
            "Response : %s" % (resp.status_code, new_record, resp.text[:400])
        )

        # ── Step 5: Refresh the frontend table ───────────────────────────────
        search_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[.//text()[contains(., 'Search Data')]]")
            )
        )
        search_btn.click()
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody")))
        time.sleep(1)

        # ── Step 6: Assert record visible in table ────────────────────────────
        table_text = " ".join(
            r.text for r in driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        )
        assert "Batu Pahat" in table_text, (
            "TC-UC8-004 FAIL: 'Batu Pahat' not visible in table after API POST.\n"
            "Table: " + table_text[:500]
        )

        # ── Step 7: Wrap-up ───────────────────────────────────────────────────
        _delete_record(token)

        print("TC-UC8-004 Manual API POST Creates Record Visible in Table - PASS")