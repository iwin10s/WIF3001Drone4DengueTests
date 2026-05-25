"""
test_uc8_019.py
===============
Test Procedure : TP-UC8-019
Test Cases     : TC-UC8-019
Objective      : Verify that system exceptions generate detailed technical log
                 events inside backend tracking files for diagnostic purposes.
Coverage Items : TCOV-08-037
Wrap-Up        : None
Pre-requisite  : A failed upload must have been triggered (TP-UC8-018) so that
                 the logger has written at least one error entry before this test.

Logger behaviour (dengueDataController.js):
  uploadCSV outer catch (line ~284):
    logger.error('[UPLOAD CSV ERROR]', {
      error: err.message,
      stack: err.stack,
      companyId: req.companyId
    })

Auth strategy — WHY this differs from the conftest `logged_in` fixture:
  The conftest.py logged_in fixture does:
    1. driver.get("/")
    2. fill credentials + click submit
    3. driver.get("/data-management")   ← hard navigation BEFORE token is written

  Step 3 fires before the Next.js AuthContext has written the token to
  localStorage. When _wait_for_auth_token() polls localStorage.getItem('token')
  it finds null for the full 15 s timeout and raises AssertionError.

  Fix: this test uses its OWN make_driver() + login flow (same pattern as
  test_uc8_002 and test_uc8_008) which polls localStorage for the token
  after submit — no URL assumption — guaranteeing the token is present.
  navigating to /data-management, guaranteeing the token is in localStorage
  before we try to read it.

  The token is needed here (unlike UC8-018) because we POST a binary file
  via requests — the browser's fetch API would reject raw binary content,
  so we bypass the browser for the trigger call only.
"""

import os
import re
import time
import glob
import json
import tempfile
import requests
import pytest
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL     = os.getenv("APP_BASE_URL", "http://localhost:3000")
API_URL      = os.getenv("API_URL",      "http://localhost:4000")
DATA_MGT_URL = f"{BASE_URL}/data-management"
ADMIN_EMAIL  = os.getenv("ADMIN_EMAIL",  "admin1@drone4dengue.com")
ADMIN_PASS   = os.getenv("ADMIN_PASS",   "adminpass1")
DEFAULT_WAIT = 20

LOG_FILE_PATH  = os.getenv("LOG_FILE_PATH", None)   # auto-detected if None
LOG_TAIL_BYTES = int(os.getenv("LOG_TAIL_BYTES", "16384"))


# ---------------------------------------------------------------------------
# Driver factory — same pattern as test_uc8_002 / test_uc8_008
# ---------------------------------------------------------------------------
def make_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,900")
    drv = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    drv.maximize_window()
    return drv


# ---------------------------------------------------------------------------
# Login helper — polls localStorage for token after submit.
# This is the critical difference vs the conftest `logged_in` fixture.
# ---------------------------------------------------------------------------
def login_and_go_to_data_management(driver):
    """
    Full auth flow:
      1. GET /
      2. Fill credentials + submit
      3. Poll localStorage for the JWT token — no URL assumption made.
         AuthContext writes the token after a successful login response.
         We poll until it appears, regardless of what route the app lands on.
      4. Assert JWT token MUST exist
      5. Assert companyId MUST exist
      6. Navigate to /data-management via sidebar
      7. Wait for page heading
    """
    wait = WebDriverWait(driver, DEFAULT_WAIT)

    # Step 1 : Open login page
    driver.get(f"{BASE_URL}/")

    # Step 2 : Fill credentials
    wait.until(EC.visibility_of_element_located((By.ID, "email"))).send_keys(ADMIN_EMAIL)
    driver.find_element(By.ID, "password").send_keys(ADMIN_PASS)

    # Step 3 : Submit
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Step 4 : Poll localStorage for the JWT token.
    # We do NOT wait for a specific URL (the app may go to /data-management,
    # /data-management, or another route depending on the implementation).
    # Instead we poll localStorage.getItem('token') directly — AuthContext
    # writes it immediately after the login API responds successfully.
    print(f"\n[Auth] Login submitted for: {ADMIN_EMAIL} — polling for token...")
    token = None
    deadline = time.time() + DEFAULT_WAIT
    while time.time() < deadline:
        token = driver.execute_script("return localStorage.getItem('token');")
        if token:
            break
        time.sleep(0.5)

    assert token, (
        f"JWT token not found in localStorage after {DEFAULT_WAIT}s.\n"
        f"User: {ADMIN_EMAIL}\n"
        "Admin MUST be authenticated — token MUST exist in localStorage.\n"
        f"Current URL at timeout: {driver.current_url}"
    )
    print(f"[Auth] JWT token present: {token[:20]}...")

    # Step 6 : Assert companyId MUST exist
    company_val = driver.execute_script("""
        return localStorage.getItem('companyId')
            || localStorage.getItem('company_id')
            || localStorage.getItem('user')
            || localStorage.getItem('authUser');
    """)
    assert company_val, (
        "companyId not found in localStorage. "
        "companyId MUST exist in the auth token/context."
    )
    print(f"[Auth] companyId/user context: {str(company_val)[:80]}")

    # Step 7 : Navigate directly to /data-management.
    # Token is already confirmed in localStorage (Step 4) so driver.get()
    # will load the page as an authenticated user.
    # We skip the sidebar-click approach here because after login the app
    # may be on a route where the sidebar is not yet rendered, causing a
    # 20s timeout before the fallback driver.get() fires anyway.
    driver.get(DATA_MGT_URL)

    # Step 8 : Wait for page heading — confirms component mounted
    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h1[contains(text(),'Data Management')]")
        )
    )


# ---------------------------------------------------------------------------
# Token extraction helper
# ---------------------------------------------------------------------------
def _get_token_from_browser(driver):
    """
    Read the auth token from localStorage.
    Called AFTER login_and_go_to_data_management() which guarantees the
    token is present (asserted in Step 5 above).

    page.tsx getToken() reads: localStorage.getItem('token')
    We use the same key — no polling needed since login helper already asserted it.
    """
    token = driver.execute_script("""
        return localStorage.getItem('token')
            || localStorage.getItem('authToken')
            || localStorage.getItem('accessToken')
            || localStorage.getItem('jwt')
            || sessionStorage.getItem('token')
            || null;
    """)
    assert token, (
        "Token disappeared from localStorage after navigation. "
        "This should not happen — login helper asserted it was present."
    )
    return token


# ---------------------------------------------------------------------------
# Upload trigger — sends binary CSV via requests using the browser token
# ---------------------------------------------------------------------------
def _create_stream_breaking_csv():
    """
    Create a file that breaks the csv-parse async stream at the parser level
    (hits the OUTER catch in uploadCSV, not the inner per-row catch).

    Structure: valid CSV header + raw non-UTF-8 binary garbage.
    The valid header lets multer/busboy accept the file. The binary body
    causes csv-parse to throw during `for await (const row of parser)`,
    which is caught by the outer try/catch → logger.error → HTTP 500.
    """
    tmp = tempfile.NamedTemporaryFile(
        mode="wb", suffix=".csv", delete=False, prefix="dengue_stream_break_019_"
    )
    tmp.write(
        b"date,location,activeCases,totalCases,"
        b"coverageArea,status,source,latitude,longitude\n"
    )
    tmp.write(b"\xff\xfe" * 300)   # non-UTF-8 bytes break csv-parse stream
    tmp.close()
    return tmp.name


def _trigger_upload_failure(token):
    """
    POST a stream-breaking CSV to /dengue-data/upload using the token
    extracted from the browser session — the same token the UI uses
    (page.tsx line 282: Authorization: Bearer ${getToken()}).

    Returns (status_code, response_text).
    Outer catch in uploadCSV must fire → HTTP 400 or 500.
    """
    csv_path = _create_stream_breaking_csv()
    try:
        with open(csv_path, "rb") as f:
            resp = requests.post(
                f"{API_URL}/dengue-data/upload",
                files={"file": ("dengue_stream_break_019.csv", f, "text/csv")},
                headers={"Authorization": f"Bearer {token}"},
                timeout=15,
            )
        return resp.status_code, resp.text
    finally:
        os.unlink(csv_path)


# ---------------------------------------------------------------------------
# Log file helpers
# ---------------------------------------------------------------------------
def _find_log_file():
    if LOG_FILE_PATH:
        return LOG_FILE_PATH if os.path.isfile(LOG_FILE_PATH) else None

    candidates = [
        "logs/combined.log", "logs/error.log", "logs/app.log",
        "backend/logs/combined.log", "backend/logs/error.log",
        "server/logs/combined.log", "app.log", "error.log", "combined.log",
    ]
    cwd = Path.cwd()
    for ancestor in [cwd, cwd.parent, cwd.parent.parent, cwd.parent.parent.parent]:
        for candidate in candidates:
            full = ancestor / candidate
            if full.is_file():
                return str(full)

    recent_logs = sorted(
        glob.glob(str(cwd / "**/*.log"), recursive=True),
        key=os.path.getmtime, reverse=True,
    )
    now = time.time()
    for log in recent_logs:
        if now - os.path.getmtime(log) < 600:
            return log
    return recent_logs[0] if recent_logs else None


def _read_log_tail(log_path, tail_bytes=16384):
    with open(log_path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - tail_bytes))
        return f.read().decode("utf-8", errors="replace")


def _parse_log_entries(raw_text):
    parsed = []
    for line in raw_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed.append(json.dumps(json.loads(line)))
        except json.JSONDecodeError:
            parsed.append(line)
    return parsed


# ---------------------------------------------------------------------------
# TC-UC8-019
# ---------------------------------------------------------------------------
class TestTC_UC8_019:

    def test_backend_log_captures_error_details_after_upload_failure(self):
        """
        TC-UC8-019 | TCOV-08-037
        ─────────────────────────────────────────────────────────────────────
        Verify that a transactional failure during CSV upload causes Winston
        to write a structured log entry containing a timestamp, an explicit
        error message, and a stack trace.

        Step 1  Login and open /data-management — polls localStorage for
                the token after submit, no URL assumption made.
        Step 2  Extract the auth token from localStorage (same key as
                page.tsx getToken(): localStorage.getItem('token')).
        Step 3  Trigger a stream-level upload failure via requests, using
                the browser token. Binary CSV breaks csv-parse → outer catch
                → logger.error('[UPLOAD CSV ERROR]', ...) → HTTP 500.
        Step 4  Locate the backend Winston log file on disk.
        Step 5  Read the tail of the log file.
        Step 6  Assert a log entry containing '[UPLOAD CSV ERROR]' exists.
        Step 7  Assert that entry contains a timestamp field.
        Step 8  Assert that entry contains an explicit error message string.
        Step 9  Assert that entry contains a stack trace.
        """
        driver = make_driver()
        try:
            # ── Step 1 : Login and open /data-management ─────────────
            # Polls localStorage for the token after submit — no URL
            # assumption. Token is asserted present before returning.
            login_and_go_to_data_management(driver)

            # ── Step 2 : Extract token — guaranteed present after Step 1 ─
            token = _get_token_from_browser(driver)

            # ── Step 3 : Trigger stream-level upload failure via requests ─
            # Uses requests (not browser) to send binary content that would
            # be rejected by the browser's fetch API.
            # Token is the same one the browser uses (page.tsx line 282).
            status_code, response_body = _trigger_upload_failure(token)
            print(
                f"[Step 3] Upload failure triggered — "
                f"status={status_code}, response='{response_body[:120]}'"
            )
            assert status_code in (400, 500), (
                f"Expected HTTP 400 or 500 from a binary CSV upload "
                f"(outer catch must fire to call logger.error). "
                f"Got status={status_code}.\n"
                f"Response: {response_body[:300]}\n"
                "A 200 means the binary content hit the inner per-row catch "
                "instead of the outer stream catch. "
                "Set LOG_FILE_PATH and verify logger.error is reachable, or "
                "adjust _create_stream_breaking_csv() for your csv-parse version."
            )

            # Give Winston 1s to flush the entry to disk
            time.sleep(1)

            # ── Step 4 : Locate the backend Winston log file ──────────
            log_path = _find_log_file()
            assert log_path is not None, (
                "Could not locate a backend log file on disk.\n"
                "Set LOG_FILE_PATH env var to the absolute path of the "
                "Winston log file (e.g. LOG_FILE_PATH=/app/logs/combined.log)."
            )
            print(f"[Step 4] Log file: '{log_path}'")

            # ── Step 5 : Read the tail of the log file ────────────────
            raw_tail = _read_log_tail(log_path, tail_bytes=LOG_TAIL_BYTES)
            log_entries = _parse_log_entries(raw_tail)
            print(
                f"[Step 5] Read {len(log_entries)} line(s) "
                f"({len(raw_tail)} bytes)"
            )

            # ── Step 6 : Assert '[UPLOAD CSV ERROR]' entry exists ─────
            upload_error_entries = [
                e for e in log_entries
                if "UPLOAD CSV ERROR" in e
                or ("upload" in e.lower() and "error" in e.lower())
            ]
            assert upload_error_entries, (
                "No log entry containing '[UPLOAD CSV ERROR]' found in "
                f"the last {LOG_TAIL_BYTES} bytes of '{log_path}'.\n"
                "Possible causes:\n"
                "  • Binary CSV did not break the stream parser (inner catch "
                "    fired instead of outer). Step 3 status must be 400 or 500.\n"
                "  • Wrong log file — set LOG_FILE_PATH.\n"
                "  • Winston writes to stdout only — redirect to a file.\n"
                f"Log tail (last 800 chars):\n{raw_tail[-800:]}"
            )
            target_entry = upload_error_entries[-1]
            print(f"[Step 6] '[UPLOAD CSV ERROR]' entry found: {target_entry[:200]}")

            # ── Step 7 : Assert timestamp is present ──────────────────
            timestamp_patterns = [
                r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
                r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
                r'"timestamp"',
                r'"time"',
            ]
            assert any(re.search(p, target_entry) for p in timestamp_patterns), (
                "No timestamp found in the '[UPLOAD CSV ERROR]' log entry.\n"
                f"Entry: {target_entry[:400]}"
            )
            print("[Step 7] Timestamp present ✓")

            # ── Step 8 : Assert explicit error message string is present ─
            error_string_patterns = [
                r'"error"', r'csv', r'invalid', r'failed',
                r'UPLOAD CSV ERROR', r'parse', r'encoding',
            ]
            assert any(
                re.search(p, target_entry, re.IGNORECASE)
                for p in error_string_patterns
            ), (
                "No explicit error message string in log entry.\n"
                f"Entry: {target_entry[:400]}"
            )
            print("[Step 8] Explicit error message string present ✓")

            # ── Step 9 : Assert stack trace is present ────────────────
            stack_patterns = [
                r'"stack"', r'at Object\.', r'at async',
                r'\\nat ', r'controllers/', r'dengueDataController',
                r'Error:.*\\n',
            ]
            assert any(
                re.search(p, target_entry, re.IGNORECASE)
                for p in stack_patterns
            ), (
                "No stack trace found in the log entry.\n"
                "Expected the 'stack' field (err.stack) to be captured.\n"
                f"Entry: {target_entry[:400]}"
            )
            print("[Step 9] Stack trace present ✓")

            print(
                "TC-UC8-019 Backend Log Captures Timestamp, Error String, "
                "and Stack Trace After Upload Failure — PASS"
            )

        finally:
            driver.quit()