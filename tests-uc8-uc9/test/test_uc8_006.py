"""
test_uc8_006.py
===============
Test Procedure : TP-UC8-006
Test Cases     : TC-UC8-006
Objective      : Verify that system handles and rejects incomplete dengue data
                 with missing headers (CSV upload) and missing required fields
                 (direct API POST).
Coverage Items : TCOV-08-011, TCOV-08-012, TCOV-08-013

Frontend note
-------------
  No manual create form exists in page.tsx.
  TCOV-08-011/012 are tested via the Selenium CSV upload widget.
  TCOV-08-013 (empty required field) is tested via direct API POST since there
  is no frontend form to leave blank.

Wrap-Up        : None (rejected records are never inserted)
"""

import os
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

VALID_BASE = {
    "date":         "2026-05-21",
    "location":     "Seremban",
    "activeCases":  5,
    "totalCases":   20,
    "status":       "Processing",
    "source":       "manual",
    "coverageArea": "Seremban",
    "latitude":     2.7297,
    "longitude":    101.9381,
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


def _upload_csv_content(driver, wait, content, filename="dengue_incomplete.csv"):
    """Write content to a temp file and upload it via the Upload Data widget."""
    path = str(pathlib.Path(tempfile.gettempdir()) / filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

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
    file_input.send_keys(path)

    wait.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, "//button[.//text()[contains(., 'Upload')]]"),
            "Upload Data"
        )
    )
    time.sleep(0.5)


def _get_banner(driver):
    for css in ["div.text-red-700", "div.text-green-700", "div.text-gray-700"]:
        for e in driver.find_elements(By.CSS_SELECTOR, css):
            if e.is_displayed() and e.text.strip():
                return e.text.strip().lower()
    return ""


class TestUC8IncompleteData:
    """TP-UC8-006 — Incomplete/missing field rejection."""

    def test_csv_with_missing_headers_is_rejected(self, logged_in):
        """
        TC-UC8-006 | TCOV-08-011
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Upload a CSV file that contains only a data row (no headers).
        Step 3  Assert the system identifies the missing header block and
                returns a rejection banner.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        no_header_csv = "2026-03-15,Kluang,15,120,Cheras,Processing,csv,3.139,101.686\n"
        _upload_csv_content(driver, wait, no_header_csv)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        banner    = _get_banner(driver)
        combined  = page_text + " " + banner

        assert any(kw in combined for kw in
                   ["invalid", "header", "missing", "error", "failed",
                    "column", "schema", "format", "rejected"]), (
            "TC-UC8-006 FAIL (missing headers): System did not reject a CSV "
            "with no column headers.\nBanner: %s\nBody: %s" % (
                banner, page_text[:400])
        )
        print("TC-UC8-006 CSV With Missing Headers Rejected - PASS")

    def test_csv_with_empty_date_rows_is_rejected(self, logged_in):
        """
        TC-UC8-006 | TCOV-08-012
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Upload a CSV where two rows have an empty date field.
        Step 3  Assert the system isolates/drops the malformed lines and
                returns a parsing notification or error.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        empty_date_csv = (
            "date,location,activeCases,totalCases,coverageArea,status,source,latitude,longitude\n"
            ",Kluang,15,120,Cheras,Processing,csv,3.139,101.686\n"
            ",Petaling Jaya,5,40,PJ,Processing,csv,3.107,101.637\n"
        )
        _upload_csv_content(driver, wait, empty_date_csv)

        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        banner    = _get_banner(driver)
        combined  = page_text + " " + banner

        assert any(kw in combined for kw in
                   ["invalid", "error", "missing", "empty", "failed",
                    "skipped", "0 record", "malformed", "rejected"]), (
            "TC-UC8-006 FAIL (empty date rows): System did not handle/reject "
            "rows with empty date fields.\nBanner: %s\nBody: %s" % (
                banner, page_text[:400])
        )
        print("TC-UC8-006 CSV With Empty Date Rows Rejected - PASS")

    def test_api_post_with_empty_location_is_rejected(self, logged_in):
        """
        TC-UC8-006 | TCOV-08-013
        ─────────────────────────────────────────────────────────────────────
        Step 1  Build a payload with location = '' (empty string).
        Step 2  POST to /dengue-data directly via requests.
        Step 3  Assert the API returns 4xx — required field cannot be blank.

        Note: There is no frontend form to leave empty (page.tsx has no
        manual create form). Per the SRS, this validation is enforced at the
        backend API level and tested via direct POST.
        """
        driver = logged_in
        token, company_id = _get_auth(driver)

        payload = dict(VALID_BASE, location="")
        resp = requests.post(
            API_URL + "/dengue-data",
            json=payload,
            headers=_api_headers(token),
            timeout=10,
        )

        assert resp.status_code in range(400, 500), (
            "TC-UC8-006 FAIL (empty location via API): Expected 4xx for "
            "location='', got HTTP %d.\nResponse: %s" % (
                resp.status_code, resp.text[:300])
        )
        print("TC-UC8-006 API POST With Empty Location Rejected - PASS")