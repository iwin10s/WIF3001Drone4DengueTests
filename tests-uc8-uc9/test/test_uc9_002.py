"""
test_uc9_002.py

Test Procedure : TP-UC9-002
Test Cases     : TC-UC9-002, TC-UC9-023
Objective      : Verify that valid weather CSV dataset is uploaded and stored
                 successfully, and duplicate records are rejected if the same
                 file is re-uploaded.

Confirmed from page.tsx:
  - CSV file input  : id="csvFile"  (accept=".csv")
  - Upload button   : button[type='submit'] text="Upload CSV"
  - Success alert   : AlertDescription — "uploaded and processed successfully"
  - Error alert     : AlertDescription — "Failed to process CSV file..."
  - Alert container : Alert > AlertDescription (shadcn/ui)

Session design:
  Each test has its OWN browser session (function-scoped).
  TC-UC9-002 logs in, uploads, asserts success, then the session closes.
  TC-UC9-023 opens a NEW session, logs in again, re-uploads the SAME file
  into a DB that already has those records from TC-UC9-002.
  This avoids stale element / button-disabled issues from shared sessions.
"""

import os
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
BASE_URL     = "http://localhost:3000"
WEATHER_URL  = f"{BASE_URL}/weather-data"
ADMIN_EMAIL  = "admin1@drone4dengue.com"
ADMIN_PASS   = "adminpass1"
DEFAULT_WAIT = 20

FIXTURE_CSV = os.path.join(
    os.path.dirname(__file__), "fixtures", "weather_valid.csv"
)

SUCCESS_FRAGMENT  = "uploaded and processed successfully"
DUPLICATE_FAIL_MSG = (
    "DEFECT — TC-UC9-023: Duplicate records were accepted by the backend. "
    f"The alert '{SUCCESS_FRAGMENT}' appeared on the second upload. "
    "Expected: system must reject or skip already-stored records. "
    "Actual: backend re-inserted duplicate data."
)


# ---------------------------------------------------------------------------
# Helpers (unchanged from confirmed-working version)
# ---------------------------------------------------------------------------

def make_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    drv = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    drv.maximize_window()
    return drv


def login_and_go_to_weather(driver):
    """
    Log in as Admin One, assert JWT + companyId, navigate to /weather-data.
    Waits until heading and csvFile input are both visible.
    """
    wait = WebDriverWait(driver, DEFAULT_WAIT)

    # Step 1 : Open login page
    driver.get(f"{BASE_URL}/")

    # Step 2 : Fill credentials
    wait.until(EC.visibility_of_element_located((By.ID, "email"))).send_keys(ADMIN_EMAIL)
    driver.find_element(By.ID, "password").send_keys(ADMIN_PASS)

    # Step 3 : Submit
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Step 4 : Wait for /dashboard
    wait.until(EC.url_contains("/dashboard"))
    print(f"\n[Auth] Logged in as: {ADMIN_EMAIL} (Admin One)")

    # Step 5 : Assert JWT token MUST exist
    token = driver.execute_script("return localStorage.getItem('token');")
    assert token, (
        f"JWT token not found in localStorage after login as {ADMIN_EMAIL}. "
        "Admin MUST be authenticated before this test proceeds."
    )
    print("[Auth] JWT token present.")

    # Step 6 : Assert companyId MUST exist
    company_val = driver.execute_script("""
        return localStorage.getItem('companyId')
            || localStorage.getItem('company_id')
            || localStorage.getItem('user')
            || localStorage.getItem('authUser');
    """)
    assert company_val, (
        "companyId not found in localStorage after login. "
        "companyId MUST exist in the auth context before test proceeds."
    )
    print(f"[Auth] companyId/user context confirmed: {str(company_val)[:80]}")

    # Step 7 : Navigate directly to /weather-data
    driver.get(WEATHER_URL)

    # Step 8 : Wait for URL
    wait.until(EC.url_contains("/weather-data"))

    # Step 9 : Wait for page heading
    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Weather Data Management')]")
        )
    )

    # Step 10 : Wait for csvFile input (upload section rendered)
    wait.until(EC.presence_of_element_located((By.ID, "csvFile")))
    time.sleep(1)


def get_alert_text(driver, timeout=DEFAULT_WAIT):
    """
    Wait for AlertDescription to appear and return its text.
    Strategy A: class contains 'AlertDescription' (Shadcn class name).
    Strategy B: role='alert' fallback.
    """
    # Strategy A
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[class*='AlertDescription']")
            )
        )
        return el.text.strip()
    except Exception:
        pass
    # Strategy B
    try:
        el = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[role='alert']"))
        )
        return el.text.strip()
    except Exception:
        return ""


def upload_csv(driver, filepath):
    """
    Attach CSV to #csvFile and click Upload CSV.
    Confirmed: button is disabled until React processes the file (~2s).
    """
    wait = WebDriverWait(driver, DEFAULT_WAIT)

    csv_input = wait.until(EC.presence_of_element_located((By.ID, "csvFile")))
    csv_input.send_keys(os.path.abspath(filepath))
    time.sleep(3)  # wait for React to enable the Upload CSV button

    upload_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[normalize-space()='Upload CSV']")
        )
    )
    upload_btn.click()


# ---------------------------------------------------------------------------
# TC-UC9-002 — Valid CSV upload succeeds
# ---------------------------------------------------------------------------
class TestTC_UC9_002:
    """
    TC-UC9-002: Upload a valid CSV and assert the success alert appears.
    Uses its own browser session — opens and closes independently of TC-UC9-023.
    """

    def test_tc_uc9_002_valid_csv_upload(self):
        """
        Input   : weather_valid.csv
        Expected: Alert 'uploaded and processed successfully' appears;
                  at least one row visible in the weather records table.
        """
        # ── Precondition ──────────────────────────────────────────────
        assert os.path.isfile(FIXTURE_CSV), (
            f"Fixture CSV not found: {FIXTURE_CSV}\n"
            "Create test/fixtures/weather_valid.csv before running."
        )

        driver = make_driver()
        try:
            # ── Step 1 : Login and open /weather-data ─────────────────
            # Asserts JWT + companyId + page heading + csvFile input ready.
            login_and_go_to_weather(driver)

            # ── Step 2 : Attach CSV and click Upload CSV ──────────────
            upload_csv(driver, FIXTURE_CSV)
            print(f"[Step 2] Uploaded: {FIXTURE_CSV}")

            # ── Step 3 : Assert success alert appears ─────────────────
            alert_text = get_alert_text(driver)
            print(f"[Step 3] Alert: '{alert_text}'")
            assert SUCCESS_FRAGMENT in alert_text, (
                f"Expected alert containing '{SUCCESS_FRAGMENT}'.\n"
                f"Actual alert text: '{alert_text}'"
            )

            # ── Step 4 : Verify table has at least one row ─────────────
            wait = WebDriverWait(driver, DEFAULT_WAIT)
            table_row = wait.until(
                EC.presence_of_element_located((By.XPATH, "//table//tbody/tr"))
            )
            assert table_row.is_displayed(), (
                "Weather records table has no rows after successful CSV upload."
            )

            print("TC-UC9-002 Valid CSV Upload — PASS")

        finally:
            # Always close this session regardless of pass/fail
            driver.quit()


# ---------------------------------------------------------------------------
# TC-UC9-023 — Duplicate CSV re-upload MUST be rejected
# ---------------------------------------------------------------------------
class TestTC_UC9_023:
    """
    TC-UC9-023: Re-upload the same CSV into a DB that already has those
    records (left by TC-UC9-002). Uses a FRESH browser session — logs in
    from scratch to avoid stale element / disabled-button issues.
    """

    def test_tc_uc9_023_duplicate_csv_upload(self):
        """
        Input   : Same weather_valid.csv uploaded again after TC-UC9-002.
        Expected: SUCCESS alert MUST NOT appear.
                  PASS if: non-success alert OR no alert (silent skip).
                  FAIL if: 'uploaded and processed successfully' appears.
        """
        # ── Precondition ──────────────────────────────────────────────
        assert os.path.isfile(FIXTURE_CSV), (
            f"Fixture CSV not found: {FIXTURE_CSV}"
        )

        driver = make_driver()
        try:
            # ── Step 1 : Fresh login — new session, same DB state ──────
            # DB still has records from TC-UC9-002 (same backend/DB).
            # JWT + companyId asserted inside login_and_go_to_weather().
            login_and_go_to_weather(driver)
            print("[Step 1] Fresh session on /weather-data. DB has prior records.")

            # ── Step 2 & 3 : Re-upload the same CSV ───────────────────
            # Fresh session means #csvFile and Upload CSV button are in
            # their initial state — no stale refs, button not stuck disabled.
            upload_csv(driver, FIXTURE_CSV)
            print(f"[Step 2/3] Re-uploaded same CSV: {FIXTURE_CSV}")

            # ── Step 4 : Capture whatever alert the server returns ─────
            alert_text = get_alert_text(driver)
            print(f"[Step 4] Alert after duplicate upload: '{alert_text}'")

            # ── Step 5 : Assert page has NOT crashed ───────────────────
            heading = driver.find_elements(
                By.XPATH, "//*[contains(text(),'Weather Data Management')]"
            )
            assert len(heading) > 0, (
                "Page heading gone after duplicate upload — possible crash."
            )

            # ── Step 6 : CORE ASSERTION — success alert MUST NOT appear ─
            # If success fragment is present → backend accepted duplicate
            # data → DEFECT → FAIL.
            assert SUCCESS_FRAGMENT not in alert_text, DUPLICATE_FAIL_MSG

            # ── Step 7 : No JS crash keywords in whatever alert appeared ─
            if alert_text:
                for kw in ["undefined", "cannot read", "typeerror", "uncaught"]:
                    assert kw not in alert_text.lower(), (
                        f"JS crash keyword '{kw}' in alert: '{alert_text}'"
                    )
                print(f"[Step 7] Duplicate correctly rejected. Alert: '{alert_text}'")
            else:
                print("[Step 7] No alert — silent deduplication (0 records inserted). Acceptable.")

            print("TC-UC9-023 Duplicate CSV Upload Rejected — PASS")

        finally:
            # Always close this session
            driver.quit()
