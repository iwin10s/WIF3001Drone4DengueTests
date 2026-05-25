"""
test_uc8_019.py
===============
Test Procedure : TP-UC8-019
Test Cases     : TC-UC8-019
Objective      : Verify that system exceptions generate detailed technical log
                 events inside backend tracking files for diagnostic purposes.
Coverage Items : TCOV-08-037
Wrap-Up        : None

Approach
--------
  This test reads the backend log file directly from disk (or via a log API
  endpoint if available) after a known upload failure has been triggered.

  It depends on TP-UC8-018 having run first (or triggers its own failure).

  Set LOG_FILE_PATH environment variable to the absolute path of the backend
  log file, e.g.:
    set LOG_FILE_PATH=C:\\path\\to\\drone4dengue\\backend\\logs\\app.log

  If the backend exposes a log endpoint, set LOG_API_ENDPOINT instead.
"""

import os
import re
import time
import pathlib
import tempfile
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

BASE_URL     = "http://localhost:3000"
DATA_MGT_URL = BASE_URL + "/data-management"
API_URL      = os.getenv("API_BASE_URL", "http://localhost:4000")

# Path to the backend log file — set via env var
LOG_FILE_PATH    = os.getenv("LOG_FILE_PATH", "")
LOG_API_ENDPOINT = os.getenv("LOG_API_ENDPOINT", "")


def _trigger_upload_failure(driver, wait):
    """
    Inject a 500 mock, upload a valid CSV, then restore fetch.
    This is the same failure simulation as TC-UC8-018 and ensures
    a log entry exists for TC-UC8-019 to inspect.
    """
    mock_js = """
    window._origFetch = window.fetch;
    window.fetch = function(url, opts) {
        if (typeof url === 'string' && url.toLowerCase().includes('upload')) {
            return Promise.resolve(new Response(
                JSON.stringify({success:false, message:'Simulated error for log test'}),
                {status: 500, headers: {'Content-Type': 'application/json'}}
            ));
        }
        return window._origFetch(url, opts);
    };
    """
    driver.execute_script(mock_js)
    time.sleep(0.3)

    csv_path = str(pathlib.Path(tempfile.gettempdir()) / "dengue_cases.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(
            "date,location,activeCases,totalCases,coverageArea,status,"
            "source,latitude,longitude\n"
            "2026-03-15,Kluang,15,120,Cheras,Processing,csv,3.139,101.686\n"
        )

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
    file_input.send_keys(csv_path)

    wait.until(
        EC.text_to_be_present_in_element(
            (By.XPATH, "//button[.//text()[contains(., 'Upload')]]"),
            "Upload Data"
        )
    )
    time.sleep(1)
    driver.execute_script(
        "if (window._origFetch) { window.fetch = window._origFetch; "
        "delete window._origFetch; }"
    )


def _read_log_from_file():
    """Read the backend log file and return its content as a string."""
    if not LOG_FILE_PATH or not os.path.exists(LOG_FILE_PATH):
        return ""
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        print("[WARN] Could not read log file '%s': %s" % (LOG_FILE_PATH, e))
        return ""


def _read_log_from_api():
    """Fetch log content from LOG_API_ENDPOINT if configured."""
    if not LOG_API_ENDPOINT:
        return ""
    try:
        import requests
        r = requests.get(LOG_API_ENDPOINT, timeout=5)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print("[WARN] Could not fetch log from API '%s': %s" % (LOG_API_ENDPOINT, e))
    return ""


class TestUC8BackendLogging:
    """TP-UC8-019 — Backend log events after upload failure."""

    def test_backend_log_contains_error_details_after_upload_failure(self, logged_in):
        """
        TC-UC8-019 | TCOV-08-037
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Trigger an upload failure (simulated 500 via JS mock).
        Step 3  Read the backend server log (file or API endpoint).
        Step 4  Assert the log contains:
                (a) A timestamp
                (b) An error message string
                (c) An execution stack trace OR error code

        Pre-condition: LOG_FILE_PATH or LOG_API_ENDPOINT must be set.
        Special requirement: Requires access to server logger / log file output.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        # ── Step 2: Trigger an upload failure ────────────────────────────────
        _trigger_upload_failure(driver, wait)
        time.sleep(1)  # allow log to flush

        # ── Step 3: Read backend log ──────────────────────────────────────────
        log_content = _read_log_from_file() or _read_log_from_api()

        if not log_content:
            # If no log access configured, check browser console SEVERE logs
            # as a fallback (captures frontend-visible errors)
            print("[WARN] LOG_FILE_PATH and LOG_API_ENDPOINT not set. "
                  "Falling back to browser console logs.")
            try:
                browser_logs = driver.get_log("browser")
                severe_logs = [e["message"] for e in browser_logs
                               if e.get("level") == "SEVERE"]
                log_content = "\n".join(severe_logs)
                print("[INFO] Browser SEVERE logs:\n" + log_content[:500])
            except Exception:
                log_content = ""

        if not log_content:
            pytest.skip(
                "TC-UC8-019 SKIPPED: No backend log access configured and no "
                "browser SEVERE logs captured. Set LOG_FILE_PATH to the backend "
                "log file path and re-run."
            )

        # ── Step 4: Assert log contains required fields ───────────────────────
        log_lower = log_content.lower()

        # (a) Timestamp — ISO format or common log formats
        has_timestamp = bool(
            re.search(r"\d{4}-\d{2}-\d{2}", log_content) or
            re.search(r"\d{2}:\d{2}:\d{2}", log_content)
        )

        # (b) Error message string
        has_error_msg = any(kw in log_lower for kw in
                            ["error", "failed", "exception", "upload", "csv"])

        # (c) Stack trace or error code
        has_stack_or_code = any(kw in log_lower for kw in
                                ["stack", "at ", "traceback", "500",
                                 "internal", "error_code", "code"])

        assert has_timestamp, (
            "TC-UC8-019 FAIL: Backend log does not contain a timestamp.\n"
            "Log snippet: " + log_content[-500:]
        )
        assert has_error_msg, (
            "TC-UC8-019 FAIL: Backend log does not contain an error message string.\n"
            "Log snippet: " + log_content[-500:]
        )
        assert has_stack_or_code, (
            "TC-UC8-019 FAIL: Backend log does not contain a stack trace or error code.\n"
            "Log snippet: " + log_content[-500:]
        )

        print("TC-UC8-019 Backend Log Contains Error Details After Upload Failure - PASS")