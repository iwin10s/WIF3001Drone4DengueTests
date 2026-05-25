"""
test_uc8_018.py
===============
Test Procedure : TP-UC8-018
Test Cases     : TC-UC8-018
Objective      : Verify that system gracefully terminates workflows and handles
                 exceptions when transactional operations fail.
Coverage Items : TCOV-08-035, TCOV-08-036
Wrap-Up        : Restore normal server connectivity after each sub-test.

Controller behaviour (dengueDataController.js):
  uploadCSV  → on DB/parse failure: logger.error('[UPLOAD CSV ERROR]', ...)
               → sendInternalError(res, 'Failed to upload and import CSV', err)
  create     → on failure: res.status(400).json({ error: err.message })
               OR sendInternalError for unexpected errors

page.tsx upload error path:
  catch (e) → setUploadMsg(`✗ ${e.message || 'Upload failed. Please try again.'}`)
             → setUploadStatus('error')
  Rendered  → <div class="... text-red-700 bg-red-50 ...">✗ Upload failed...</div>

Simulation strategy:
  TC-018-1 (CSV DB failure):
    POST /dengue-data/upload with a malformed CSV that causes a Prisma
    parse/create error on every row. The controller catches it, calls
    sendInternalError → API returns 500. page.tsx throws and sets the
    error message. Selenium then reads the red feedback div.

  TC-018-2 (Simulated server 500 on upload):
    Intercept the POST /dengue-data/upload request using a fetch-override
    injected into the browser BEFORE the file input is triggered. The
    override forces a mocked 500 response for any upload POST, causing
    page.tsx's onFileChange error branch to fire and render the red
    feedback div. This approach:
      - Tests the page.tsx error path without requiring token extraction.
      - Is robust across auth-context implementations (no localStorage
        key dependency).
      - Matches the actual UI flow (file → upload endpoint → error shown).

    NOTE ON ORIGINAL DESIGN: The original TC-018-2 tried to POST directly
    to /dengue-data (create endpoint) via a raw browser fetch and read the
    token from localStorage. This failed because:
      (a) page.tsx has no manual create form — the UI only uses the upload
          endpoint, so that code path is never exercised by the frontend.
      (b) The AuthContext may validate and rewrite the token asynchronously
          after navigation, causing a 15s polling window to expire before
          the key stabilises.
    The rewritten approach uses the upload endpoint — the actual UI path —
    and avoids token extraction entirely.

Upload message locator (page.tsx):
  <div class="mt-3 p-3 rounded-lg text-sm font-medium text-red-700 bg-red-50 border border-red-200">
    ✗ <error message>
  </div>
"""

import os
import time
import tempfile
import csv
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL     = os.getenv("APP_BASE_URL", "http://localhost:3000")
API_URL      = os.getenv("API_URL",      "http://localhost:4000")
DATA_MGT_URL = f"{BASE_URL}/data-management"

# Matches the upload feedback div that page.tsx renders when uploadMsg is set.
# Stable structural classes present on both success and error states.
UPLOAD_MSG_XPATH = (
    "//div[contains(@class,'mt-3') and contains(@class,'p-3') "
    "and contains(@class,'rounded-lg') and contains(@class,'text-sm')]"
)

# Expected error text fragments (page.tsx: `✗ ${e.message || 'Upload failed. Please try again.'}`)
ERROR_KEYWORDS = [
    "upload failed",
    "please try again",
    "failed",
    "error",
    "✗",
]

# ---------------------------------------------------------------------------
# Fetch-override JS template
# Intercepts POST requests to a URL fragment and returns a mocked 500.
# Usage: _FETCH_OVERRIDE_JS.format(url_fragment=..., error_message=...)
# ---------------------------------------------------------------------------
_FETCH_OVERRIDE_JS = """
    window.__originalFetch = window.fetch;
    window.fetch = function(url, options) {{
        var method = (options && options.method || 'GET').toUpperCase();
        if (method === 'POST' &&
            typeof url === 'string' &&
            url.includes('{url_fragment}')) {{
            return Promise.resolve(
                new Response(
                    JSON.stringify({{
                        error: {{
                            message: '{error_message}'
                        }}
                    }}),
                    {{
                        status: 500,
                        headers: {{ 'Content-Type': 'application/json' }}
                    }}
                )
            );
        }}
        return window.__originalFetch.apply(this, arguments);
    }};
    window.__fetchIntercepted = true;
"""

_FETCH_RESTORE_JS = """
    if (window.__originalFetch) {
        window.fetch = window.__originalFetch;
        delete window.__originalFetch;
        delete window.__fetchIntercepted;
    }
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_auth_token(driver, timeout=15):
    """
    Poll for the auth token across all common storage locations.

    page.tsx reads: localStorage.getItem('token')
    This helper checks localStorage first (matching the app's own behaviour),
    then falls back to sessionStorage and common alternative key names so that
    it works even if the AuthContext implementation changes.

    Returns the token string, or raises AssertionError after timeout.
    """
    _STORAGE_CHECKS = """
        return (
            localStorage.getItem('token') ||
            localStorage.getItem('authToken') ||
            localStorage.getItem('accessToken') ||
            localStorage.getItem('jwt') ||
            sessionStorage.getItem('token') ||
            sessionStorage.getItem('authToken') ||
            sessionStorage.getItem('accessToken') ||
            null
        );
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        token = driver.execute_script(_STORAGE_CHECKS)
        if token:
            return token
        time.sleep(0.5)
    raise AssertionError(
        "TC-UC8-018 SETUP FAIL: Auth token not found in localStorage or "
        f"sessionStorage after {timeout}s. Checked keys: token, authToken, "
        "accessToken, jwt. Ensure the logged_in fixture has fully completed "
        "login and the AuthContext has written the token to client storage."
    )


def _create_malformed_csv():
    """
    Create a CSV whose rows will cause a Prisma DB write failure.
    Strategy: provide a date value that cannot be parsed (invalid ISO string)
    so that `new Date(row.date)` in uploadCSV produces Invalid Date,
    causing prisma.dengueData.create to throw a type error on every row.
    The outer try/catch in uploadCSV calls sendInternalError → HTTP 500.
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", prefix="dengue_fail_"
    )
    writer = csv.DictWriter(
        tmp,
        fieldnames=["date", "location", "activeCases", "totalCases",
                    "coverageArea", "status", "source", "latitude", "longitude"],
    )
    writer.writeheader()
    # Invalid date triggers Prisma validation error on every row
    writer.writerow({
        "date":         "NOT-A-DATE",
        "location":     "TestFailLocation",
        "activeCases":  "10",
        "totalCases":   "50",
        "coverageArea": "TestArea",
        "status":       "Processing",
        "source":       "csv",
        "latitude":     "3.1390",
        "longitude":    "101.6869",
    })
    tmp.close()
    return tmp.name


def _create_valid_csv():
    """
    Create a well-formed CSV with a valid date field.
    Used in TC-018-2 where the DB is never reached (fetch is intercepted).
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", prefix="dengue_valid_"
    )
    writer = csv.DictWriter(
        tmp,
        fieldnames=["date", "location", "activeCases", "totalCases",
                    "coverageArea", "status", "source", "latitude", "longitude"],
    )
    writer.writeheader()
    writer.writerow({
        "date":         "2026-05-01",
        "location":     "TestLocation",
        "activeCases":  "5",
        "totalCases":   "20",
        "coverageArea": "TestCoverage",
        "status":       "Active Cases",
        "source":       "csv",
        "latitude":     "3.1390",
        "longitude":    "101.6869",
    })
    tmp.close()
    return tmp.name


def _send_file_to_input(driver, csv_path):
    """Expose the hidden file input and inject the file path."""
    file_input = driver.find_element(
        By.CSS_SELECTOR, "input[type='file'][accept='.csv']"
    )
    driver.execute_script("arguments[0].style.display = 'block';", file_input)
    driver.execute_script("arguments[0].value = '';", file_input)
    file_input.send_keys(csv_path)


def _wait_for_upload_message(wait, timeout=20):
    """Wait for the upload feedback div to appear in the DOM."""
    return wait.until(
        EC.presence_of_element_located((By.XPATH, UPLOAD_MSG_XPATH))
    )


def _assert_error_message(msg_div, label):
    """
    Assert the upload feedback div signals an error — either via:
      - The text content containing known error keywords, OR
      - The CSS class containing 'text-red-700' (page.tsx error class)
    """
    msg_text  = msg_div.text.strip().lower()
    msg_class = msg_div.get_attribute("class") or ""

    is_error = (
        any(kw in msg_text for kw in ERROR_KEYWORDS)
        or "text-red-700" in msg_class
    )
    assert is_error, (
        f"{label} FAIL: Expected an error message in the upload feedback div.\n"
        f"  text='{msg_text}'\n  class='{msg_class}'"
    )


def _assert_page_stable(driver, label):
    """Assert the Data Management heading is still visible (no crash)."""
    heading = driver.find_element(
        By.XPATH, "//h1[contains(text(),'Data Management')]"
    )
    assert heading.is_displayed(), (
        f"{label} FAIL: Page crashed — 'Data Management' heading is gone."
    )


# ---------------------------------------------------------------------------
# TC-UC8-018-1: CSV upload during DB write failure shows error message
# ---------------------------------------------------------------------------
def test_csv_upload_db_failure_shows_error_message(logged_in):
    """
    TC-UC8-018 | TCOV-08-035
    ─────────────────────────────────────────────────────────────────────────
    Simulate a database transactional write failure during CSV upload by
    uploading a CSV whose date field is unparseable by Prisma.

    dengueDataController.js uploadCSV:
      - Each row: new Date('NOT-A-DATE') → Invalid Date → prisma.create throws
      - Outer catch: logger.error('[UPLOAD CSV ERROR]', ...) → sendInternalError
      - API responds 500 with { error: { message: '...' } }

    page.tsx onFileChange:
      - res.ok is false → throw new Error(result.error?.message || 'Upload failed')
      - catch (e): setUploadMsg(`✗ ${e.message}`) → setUploadStatus('error')
      - Renders: <div class="text-red-700 ...">✗ Upload failed...</div>

    Step 1  Navigate to /data-management.
    Step 2  Create a malformed CSV (invalid date field).
    Step 3  Send the file to the hidden file input to trigger upload.
    Step 4  Wait for the upload feedback div to appear.
    Step 5  Assert the div shows an error (red class or error text).
    Step 6  Assert the page remains stable (no crash / blank screen).
    """
    driver = logged_in
    wait   = WebDriverWait(driver, 20)

    # Step 1 — Navigate to Data Management page
    driver.get(DATA_MGT_URL)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    print("Step 1: Navigated to Data Management page")

    # Step 2 — Create a CSV that will cause a DB write failure
    csv_path = _create_malformed_csv()
    print(f"Step 2: Created malformed CSV at {csv_path}")

    # Step 3 — Send the file to trigger the upload
    _send_file_to_input(driver, csv_path)
    print("Step 3: Sent malformed CSV to the hidden file input")

    # Step 4 — Wait for the upload feedback div
    upload_msg_div = _wait_for_upload_message(wait)
    msg_text  = upload_msg_div.text.strip()
    msg_class = upload_msg_div.get_attribute("class") or ""
    print(f"Step 4: Upload feedback div appeared — text='{msg_text}', class='{msg_class}'")

    # Step 5 — Assert error state is shown
    _assert_error_message(
        upload_msg_div,
        "TC-UC8-018 CSV DB Failure"
    )
    print("Step 5: Error message confirmed — system did not silently succeed")

    # Step 6 — Assert page is still stable
    _assert_page_stable(driver, "TC-UC8-018 CSV DB Failure")
    print("Step 6: Page remains stable after DB failure")

    os.unlink(csv_path)
    print("TC-UC8-018 CSV Upload DB Failure Shows Error Message - PASS")


# ---------------------------------------------------------------------------
# TC-UC8-018-2: Simulated server 500 on upload shows error message in UI
# ---------------------------------------------------------------------------
def test_upload_simulated_server_error_shows_error_message(logged_in):
    """
    TC-UC8-018 | TCOV-08-036
    ─────────────────────────────────────────────────────────────────────────
    Simulate an unexpected internal server error (HTTP 500) during CSV upload
    by intercepting fetch() in the browser BEFORE the file input is triggered.

    WHY THIS APPROACH (vs original design):
      page.tsx has no manual create form — the only data-write path visible
      in the UI is the CSV upload (POST /dengue-data/upload). The original
      TC-018-2 tried to POST to /dengue-data (create endpoint) directly and
      read the auth token from localStorage. Both assumptions were incorrect:
        1. The create endpoint is not exercised by the frontend UI.
        2. localStorage.getItem('token') may be null during the 15s window
           if AuthContext validates the token asynchronously after navigation.

      The rewritten test intercepts POST /dengue-data/upload — the actual
      endpoint onFileChange calls — so it tests the real UI error path
      without any token extraction.

    Injection replaces window.fetch so that POST /dengue-data/upload
    returns a mocked 500 JSON response:
      { error: { message: 'Simulated server error. Please try again.' } }

    page.tsx onFileChange:
      - res.ok is false → const errorMsg = result.error?.message || 'Upload failed'
      - throw new Error(errorMsg)
      - catch (e): setUploadMsg(`✗ ${e.message}`) → setUploadStatus('error')
      - Renders: <div class="text-red-700 ...">✗ Simulated server error...</div>

    Step 1  Navigate to /data-management.
    Step 2  Inject fetch() override to intercept POST /dengue-data/upload → 500.
    Step 3  Create a valid CSV (the DB is never reached; only fetch is mocked).
    Step 4  Send the file to the hidden file input to trigger upload.
    Step 5  Wait for the upload feedback div to appear.
    Step 6  Assert the error message is displayed (red class or error text).
    Step 7  Assert the page remains stable (no crash / blank screen).
    Step 8  Restore fetch() to the original implementation (always runs).
    """
    driver = logged_in
    wait   = WebDriverWait(driver, 20)

    # Step 1 — Navigate to Data Management page
    driver.get(DATA_MGT_URL)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
    print("Step 1: Navigated to Data Management page")

    # Step 2 — Inject fetch() override BEFORE the upload is triggered.
    # Intercepts POST to any URL containing '/dengue-data/upload' and returns
    # a mocked 500 response matching the shape sendInternalError produces.
    # Using double-brace escaping because this string is NOT a .format() call —
    # the JS braces are literal.
    driver.execute_script(
        _FETCH_OVERRIDE_JS.format(
            url_fragment="/dengue-data/upload",
            error_message="Simulated server error. Please try again.",
        )
    )
    print("Step 2: fetch() override injected — POST /dengue-data/upload will return 500")

    csv_path = None
    try:
        # Step 3 — Create a valid CSV (the override means the server never sees it)
        csv_path = _create_valid_csv()
        print(f"Step 3: Created valid CSV at {csv_path}")

        # Step 4 — Send the file to the hidden file input to trigger onFileChange
        _send_file_to_input(driver, csv_path)
        print("Step 4: Sent valid CSV to the hidden file input (fetch is mocked → 500)")

        # Step 5 — Wait for the upload feedback div
        upload_msg_div = _wait_for_upload_message(wait)
        msg_text  = upload_msg_div.text.strip()
        msg_class = upload_msg_div.get_attribute("class") or ""
        print(f"Step 5: Upload feedback div appeared — text='{msg_text}', class='{msg_class}'")

        # Step 6 — Assert error state is shown
        _assert_error_message(
            upload_msg_div,
            "TC-UC8-018 Simulated 500"
        )
        print("Step 6: Error message confirmed — UI correctly handles server-level failure")

        # Step 7 — Assert page is still stable
        _assert_page_stable(driver, "TC-UC8-018 Simulated 500")
        print("Step 7: Page remains stable after simulated server error")

    finally:
        # Step 8 — Always restore the original fetch implementation
        driver.execute_script(_FETCH_RESTORE_JS)
        print("Step 8: fetch() restored to original implementation")
        if csv_path and os.path.exists(csv_path):
            os.unlink(csv_path)

    print("TC-UC8-018 Upload Simulated Server Error Shows Error Message - PASS")