"""
test_uc8_017.py
===============
Test Procedure : TP-UC8-017
Test Cases     : TC-UC8-017
Objective      : Verify that system exports dengue data to a downloadable CSV
                 according to parameters, and catches missing variables safely.
Coverage Items : TCOV-08-033, TCOV-08-034

Confirmed from dengueDataController.js + manual testing:

  exportData (GET /dengue-data/export):
    - Params    : startDate, endDate, status, format (all OPTIONAL)
    - No params → exports ALL records (no 400, no error)
    - Returns   : 200 + Content-Disposition: attachment;
                  filename="dengue_data_export.csv"
    - Error     : 500 → "Failed to export data"

  NOTE: /dengue-data/export-report does NOT exist in the backend — returns 404.
  TCOV-08-034 is therefore re-scoped to verify that calling /dengue-data/export
  with NO filter parameters still returns 200 and a valid CSV with all records
  (i.e. missing/empty params are handled safely, not rejected).

Test strategy:
  TCOV-08-033 : GET /dengue-data/export with valid startDate + endDate + status
                → assert 200 + Content-Type text/csv + expected column headers
  TCOV-08-034 : GET /dengue-data/export with NO parameters
                → assert 200 + valid CSV returned (all records exported safely)
"""

import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL      = "http://localhost:3000"
API_BASE_URL  = "http://localhost:4000"
DATA_MGMT_URL = f"{BASE_URL}/data-management"

ADMIN_EMAIL  = "admin1@drone4dengue.com"
ADMIN_PASS   = "adminpass1"
DEFAULT_WAIT = 20

# Valid filter params for TCOV-08-033
EXPORT_START_DATE = "2025-01-01"
EXPORT_END_DATE   = "2025-01-31"
EXPORT_STATUS     = "Active Cases"

# Expected CSV column headers (confirmed from controller exportData fields)
EXPECTED_CSV_COLS = ["id", "location", "date", "activeCases", "totalCases", "status"]


# ---------------------------------------------------------------------------
# Helpers
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


def login_and_navigate(driver):
    """
    Full auth flow with hard gates:
      1. Submit login form
      2. Poll localStorage for JWT token (URL-agnostic — no /dashboard assumption)
      3. Assert JWT token MUST exist
      4. Assert companyId MUST exist
      5. Navigate directly to /data-management
      6. Wait for page heading
    """
    wait = WebDriverWait(driver, DEFAULT_WAIT)

    # Step 1 : Open login page and submit credentials
    driver.get(BASE_URL)
    wait.until(EC.visibility_of_element_located((By.ID, "email"))).send_keys(ADMIN_EMAIL)
    driver.find_element(By.ID, "password").send_keys(ADMIN_PASS)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Step 2 : Poll localStorage for token — URL-agnostic, no /dashboard assumption
    token = None
    deadline = time.time() + DEFAULT_WAIT
    while time.time() < deadline:
        token = driver.execute_script("return localStorage.getItem('token');")
        if token:
            break
        time.sleep(0.5)

    # Step 3 : Assert JWT token MUST exist
    assert token, (
        f"JWT token not found in localStorage after {DEFAULT_WAIT}s.\n"
        f"User: {ADMIN_EMAIL} | URL at timeout: {driver.current_url}\n"
        "Admin MUST be authenticated before this test proceeds."
    )

    # Step 4 : Assert companyId MUST exist
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

    # Step 5 : Navigate directly (token in localStorage → page loads authenticated)
    driver.get(DATA_MGMT_URL)

    # Step 6 : Wait for page heading
    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Data Management')]")
        )
    )


def api_fetch(driver, endpoint):
    """
    Execute GET request via browser fetch() using the JWT from localStorage.
    Returns dict: { status, body, contentType }.
    body is parsed JSON if Content-Type is application/json, otherwise raw text.
    """
    script = f"""
        const done = arguments[0];
        const token = localStorage.getItem('token');
        fetch('{API_BASE_URL}{endpoint}', {{
            headers: {{ 'Authorization': 'Bearer ' + token }}
        }})
        .then(async r => {{
            const contentType = r.headers.get('content-type') || '';
            let body;
            if (contentType.includes('application/json')) {{
                body = await r.json();
            }} else {{
                body = await r.text();
            }}
            done({{ status: r.status, body: body, contentType: contentType }});
        }})
        .catch(e => done({{ status: 0, body: e.toString(), contentType: '' }}));
    """
    return driver.execute_async_script(script)


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def auth_driver():
    driver = make_driver()
    yield driver
    driver.quit()


# ---------------------------------------------------------------------------
# TC-UC8-017 | TCOV-08-033
# Export with valid filter params returns 200 + CSV with correct headers
# ---------------------------------------------------------------------------

def test_export_with_valid_params_returns_csv(auth_driver):
    """
    TC-UC8-017 | TCOV-08-033

    Confirmed from dengueDataController.js exportData:
      - Endpoint : GET /dengue-data/export
      - Params   : startDate, endDate, status (all optional, filter the result)
      - Returns  : 200 + Content-Type: text/csv + CSV body with column headers

    Step 1 : Login as Admin One — JWT + companyId gates enforced.
    Step 2 : Navigate to /data-management.
    Step 3 : Click the Export button on the page UI.
    Step 4 : Also call GET /dengue-data/export with startDate + endDate + status
             via browser fetch() to verify the API response directly.
    Step 5 : Assert HTTP 200.
    Step 6 : Assert Content-Type contains 'csv'.
    Step 7 : Assert CSV body contains expected column headers.
    """
    driver = auth_driver
    wait   = WebDriverWait(driver, DEFAULT_WAIT)

    # ── Step 1 & 2 : Login and navigate ──────────────────────────────
    login_and_navigate(driver)

    # ── Step 3 : Click Export button on the page ──────────────────────
    # page.tsx onExport(): builds URL from current filters and triggers
    # a hidden <a> download click. We click the button to test the UI path.
    export_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[normalize-space()='Export']")
        )
    )
    export_btn.click()
    print("[Step 3] Clicked 'Export' button.")
    time.sleep(2)  # allow download trigger to fire

    # ── Step 4 : Call API directly with valid filter params ───────────
    # Verifies the endpoint response shape independently of the UI click.
    endpoint = (
        f"/dengue-data/export"
        f"?startDate={EXPORT_START_DATE}"
        f"&endDate={EXPORT_END_DATE}"
        f"&status={EXPORT_STATUS.replace(' ', '%20')}"
        f"&format=csv"
    )
    result       = api_fetch(driver, endpoint)
    status       = result.get("status")
    content_type = result.get("contentType", "")
    body         = result.get("body", "")
    print(f"[Step 4] API response — status={status}, "
          f"contentType='{content_type}', body[:80]='{str(body)[:80]}'")

    # ── Step 5 : Assert HTTP 200 ──────────────────────────────────────
    assert status == 200, (
        f"Expected HTTP 200 from /dengue-data/export with valid params.\n"
        f"Got: {status}\nBody: {str(body)[:300]}"
    )

    # ── Step 6 : Assert Content-Type is CSV ───────────────────────────
    assert "csv" in content_type.lower() or "text/" in content_type.lower(), (
        f"Expected text/csv Content-Type.\n"
        f"Got: '{content_type}'"
    )

    # ── Step 7 : Assert expected column headers present in CSV body ───
    for col in EXPECTED_CSV_COLS:
        assert col in body, (
            f"Expected column '{col}' in CSV response headers.\n"
            f"CSV preview: {str(body)[:300]}"
        )

    print("TC-UC8-017 TCOV-08-033 Export With Valid Params Returns CSV — PASS")


# ---------------------------------------------------------------------------
# TC-UC8-017 | TCOV-08-034
# Export with NO filter params returns 200 + all records (missing vars handled)
# ---------------------------------------------------------------------------

def test_export_without_params_returns_all_records(auth_driver):
    """
    TC-UC8-017 | TCOV-08-034

    Confirmed from dengueDataController.js exportData + manual testing:
      - Endpoint : GET /dengue-data/export (NO params)
      - All filter params (startDate, endDate, status) are optional
      - Missing/empty params are handled safely — no 400, no crash
      - System exports ALL records and returns 200 + valid CSV

    NOTE: /dengue-data/export-report does NOT exist (returns 404).
    This test re-scopes TCOV-08-034 to verify that the system safely
    handles the case where NO filter variables are provided — it must
    not crash or return an error, it must export all records.

    Step 1 : Login as Admin One — JWT + companyId gates enforced.
    Step 2 : Navigate to /data-management.
    Step 3 : Call GET /dengue-data/export with NO query parameters.
    Step 4 : Assert HTTP 200 — no error for missing optional params.
    Step 5 : Assert Content-Type contains 'csv'.
    Step 6 : Assert CSV body is non-empty (all records exported).
    Step 7 : Assert CSV body contains expected column headers.
    """
    driver = auth_driver

    # ── Step 1 & 2 : Login and navigate ──────────────────────────────
    login_and_navigate(driver)

    # ── Step 3 : Call /dengue-data/export with NO params ─────────────
    # No startDate, no endDate, no status, no format — all omitted.
    result       = api_fetch(driver, "/dengue-data/export")
    status       = result.get("status")
    content_type = result.get("contentType", "")
    body         = result.get("body", "")
    print(f"[Step 3] No-params export — status={status}, "
          f"contentType='{content_type}', body[:80]='{str(body)[:80]}'")

    # ── Step 4 : Assert HTTP 200 — missing params must NOT cause error ─
    assert status == 200, (
        f"Expected HTTP 200 when calling /dengue-data/export with no params.\n"
        f"Got: {status}\nBody: {str(body)[:300]}\n"
        "Missing optional filter params must be handled safely (export all records)."
    )

    # ── Step 5 : Assert Content-Type is CSV ───────────────────────────
    assert "csv" in content_type.lower() or "text/" in content_type.lower(), (
        f"Expected text/csv Content-Type for no-param export.\n"
        f"Got: '{content_type}'"
    )

    # ── Step 6 : Assert CSV body is non-empty ────────────────────────
    # When no filters are applied the system should return ALL records.
    assert body and len(body.strip()) > 0, (
        "CSV body is empty — expected all records to be exported "
        "when no filter params are provided."
    )

    # ── Step 7 : Assert expected column headers present ───────────────
    for col in EXPECTED_CSV_COLS:
        assert col in body, (
            f"Expected column '{col}' in CSV response headers.\n"
            f"CSV preview: {str(body)[:300]}"
        )

    print("TC-UC8-017 TCOV-08-034 Export Without Params Returns All Records Safely — PASS")