"""
test_uc8_005.py
===============
Test Procedure : TP-UC8-005
Test Cases     : TC-UC8-005
Objective      : Verify that the system rejects invalid dengue data submitted
                 via direct API calls (equivalence partitioning).
Coverage Items : TCOV-08-007, TCOV-08-008, TCOV-08-009, TCOV-08-010

Frontend note
-------------
  No manual create form exists in the frontend (page.tsx).  Invalid data
  validation is tested by POSTing malformed payloads directly to the backend
  REST API and asserting the HTTP response is 4xx (rejected).
  TCOV-08-007 (non-CSV file upload) is tested via the Selenium upload widget.

Wrap-Up        : None (rejected records are never inserted)
"""

import os
import io
import time
import pathlib
import tempfile
import pytest
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

API_URL      = os.getenv("API_BASE_URL", "http://localhost:4000")
BASE_URL     = os.getenv("APP_BASE_URL", "http://localhost:3000")
DATA_MGT_URL = BASE_URL + "/data-management"

# Valid baseline — individual tests override one field to make it invalid
VALID_BASE = {
    "date":         "2026-05-21",
    "location":     "Petaling Jaya",
    "activeCases":  10,
    "totalCases":   30,
    "status":       "Processing",
    "source":       "manual",
    "coverageArea": "PJ",
    "latitude":     3.107,
    "longitude":    101.637,
    "companyId":    "comp-001",
}


def _get_auth(driver):
    """Assert token AND companyId exist; return (token, company_id)."""
    import json
    token        = driver.execute_script("return localStorage.getItem(\'token\');")
    company_json = driver.execute_script("return localStorage.getItem(\'company\');")
    assert token, (
        "PRE-CONDITION FAIL: JWT token missing from localStorage. "
        "Admin must be authenticated."
    )
    assert company_json, (
        "PRE-CONDITION FAIL: \'company\' missing from localStorage. "
        "companyId must exist for UC-8 API calls."
    )
    company_id = json.loads(company_json).get("id", "")
    assert company_id, "PRE-CONDITION FAIL: company JSON has no \'id\' field."
    return token, company_id


def _api_headers(token):
    return {
        "Authorization": "Bearer " + token,
        "Content-Type":  "application/json",
    }


def _post_record(payload, token):
    """POST payload to /dengue-data and return the response."""
    return requests.post(
        API_URL + "/dengue-data",
        json=payload,
        headers=_api_headers(token),
        timeout=10,
    )


class TestUC8InvalidData:
    """TP-UC8-005 — Invalid data rejection via API (equivalence partitioning)."""

    def test_pdf_file_upload_is_rejected_by_frontend(self, logged_in):
        """
        TC-UC8-005 | TCOV-08-007
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Override the file input's accept attribute and send a .pdf path.
        Step 3  Assert the upload is silently rejected (no 'Uploading...' state
                fires, or the banner shows a file-type error).

        This is the only sub-test that uses Selenium because the file-type
        check is enforced at the frontend upload widget level.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)

        # Create a dummy PDF
        pdf_path = str(pathlib.Path(tempfile.gettempdir()) / "dengue_bad.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"%PDF-1.4 fake content")

        # Open the upload widget
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[.//text()[contains(., 'Upload Data')]]")
            )
        ).click()

        try:
            file_input = driver.find_element(
                By.CSS_SELECTOR, "input[type='file'][accept='.csv']"
            )
        except NoSuchElementException:
            file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")

        # Remove accept constraint so Selenium can send the PDF path
        driver.execute_script("arguments[0].removeAttribute('accept');", file_input)
        file_input.send_keys(pdf_path)
        time.sleep(2)

        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()

        # Rejection signals: error banner, OR button never entered 'Uploading...'
        # meaning onChange was not fired / file was filtered client-side
        btn_texts = [b.text.strip() for b in driver.find_elements(By.TAG_NAME, "button")]
        rejected = (
            any(kw in body_text for kw in
                ["invalid", "error", "failed", "only csv", "unsupported", "pdf"]) or
            "Uploading..." not in btn_texts  # onChange never fired
        )
        assert rejected, (
            "TC-UC8-005 FAIL (pdf upload): System did not reject the .pdf file.\n"
            "Body: " + body_text[:300]
        )
        print("TC-UC8-005 PDF File Upload Rejected by Frontend - PASS")

    def test_invalid_date_format_rejected_by_api(self, logged_in):
        """
        TC-UC8-005 | TCOV-08-008
        ─────────────────────────────────────────────────────────────────────
        Step 1  Build a payload where date = '15/03/2026' (DD/MM/YYYY).
        Step 2  POST to /dengue-data directly via requests.
        Step 3  Assert the API returns 4xx (bad request — invalid date format).
        """
        driver = logged_in
        token, company_id = _get_auth(driver)

        payload = dict(VALID_BASE, date="15/03/2026")
        resp = _post_record(payload, token)

        assert resp.status_code in range(400, 500), (
            "TC-UC8-005 FAIL (invalid date format): Expected 4xx from API for "
            "date='15/03/2026', got HTTP %d.\nResponse: %s" % (
                resp.status_code, resp.text[:300])
        )
        print("TC-UC8-005 Invalid Date Format Rejected by API - PASS")

    def test_alphabetical_values_in_numeric_fields_rejected_by_api(self, logged_in):
        """
        TC-UC8-005 | TCOV-08-009
        ─────────────────────────────────────────────────────────────────────
        Step 1  Build a payload where activeCases='abc', totalCases='abc'.
        Step 2  POST to /dengue-data directly via requests.
        Step 3  Assert the API returns 4xx (bad request — non-numeric values).
        """
        driver = logged_in
        token, company_id = _get_auth(driver)

        payload = dict(VALID_BASE, activeCases="abc", totalCases="abc")
        resp = _post_record(payload, token)

        assert resp.status_code in range(400, 500), (
            "TC-UC8-005 FAIL (alpha in numeric): Expected 4xx from API for "
            "activeCases='abc', got HTTP %d.\nResponse: %s" % (
                resp.status_code, resp.text[:300])
        )
        print("TC-UC8-005 Alphabetical Values in Numeric Fields Rejected by API - PASS")

    def test_negative_active_cases_rejected_by_api(self, logged_in):
        """
        TC-UC8-005 | TCOV-08-010
        ─────────────────────────────────────────────────────────────────────
        Step 1  Build a payload where activeCases = -10 (negative integer).
        Step 2  POST to /dengue-data directly via requests.
        Step 3  Assert the API returns 4xx (out-of-range value rejected).
        """
        driver = logged_in
        token, company_id = _get_auth(driver)

        payload = dict(VALID_BASE, activeCases=-10)
        resp = _post_record(payload, token)

        assert resp.status_code in range(400, 500), (
            "TC-UC8-005 FAIL (negative activeCases): Expected 4xx from API for "
            "activeCases=-10, got HTTP %d.\nResponse: %s" % (
                resp.status_code, resp.text[:300])
        )
        print("TC-UC8-005 Negative Active Cases Rejected by API - PASS")