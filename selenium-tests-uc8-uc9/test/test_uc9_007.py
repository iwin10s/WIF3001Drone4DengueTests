"""
test_uc9_007.py

Test Procedure : TP-UC9-007
Test Cases     : TC-UC9-008, TC-UC9-010, TC-UC9-024
Objective      : Verify that the system rejects invalid file formats,
                 incomplete CSV layouts with missing columns, or files
                 containing out-of-range data.

Confirmed from page.tsx line 486:
  - Error alert text : "Failed to process CSV file. Please check the format."
                       "Failed to process CSV file. Please check the data."
  - Alert selector   : [class*='AlertDescription']

Fixture files required in test/fixtures/:
  - weather_valid.pdf   (invalid format — not a CSV)
  - weather_missing.csv  (missing temperature column)
  - invalid_data.csv     (temperature = 100, out of range)
"""

import os
import pytest
import time
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

FIXTURES_DIR    = os.path.join(os.path.dirname(__file__), "fixtures")
INVALID_FORMAT  = os.path.join(FIXTURES_DIR, "weather_valid.pdf")
MISSING_COL_CSV = os.path.join(FIXTURES_DIR, "weather_missing.csv")
INVALID_DATA_CSV = os.path.join(FIXTURES_DIR, "invalid_data.csv")

FORMAT_ERROR_MSG = "Failed to process CSV file. Please check the format."
DATA_ERROR_MSG   = "Failed to process CSV file. Please check the data."


def abs_path(path):
    return os.path.abspath(path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    driver.maximize_window()
    return driver


def login_and_go_to_weather(driver):
    """Log in as Admin One with JWT + companyId gates, navigate to /weather-data."""
    wait = WebDriverWait(driver, DEFAULT_WAIT)

    driver.get(f"{BASE_URL}/")
    wait.until(EC.visibility_of_element_located((By.ID, "email"))).send_keys(ADMIN_EMAIL)
    driver.find_element(By.ID, "password").send_keys(ADMIN_PASS)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))
    print(f"\n[Auth] Logged in as: {ADMIN_EMAIL} (Admin One)")

    # Assert JWT token
    token = driver.execute_script("return localStorage.getItem('token');")
    assert token, (
        f"JWT token not found in localStorage after login as {ADMIN_EMAIL}. "
        "Admin MUST be authenticated before this test proceeds."
    )
    print("[Auth] JWT token present.")

    # Assert companyId
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

    # Navigate directly to /weather-data
    driver.get(WEATHER_URL)
    wait.until(EC.url_contains("/weather-data"))
    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Weather Data Management')]")
        )
    )
    wait.until(EC.presence_of_element_located((By.ID, "csvFile")))
    time.sleep(1)


def upload_file(driver, filepath):
    """
    Attach any file to #csvFile and click Upload CSV.
    Note: The input has accept='.csv' but we bypass this for invalid format tests
    by sending the file path directly via send_keys.
    """
    wait = WebDriverWait(driver, DEFAULT_WAIT)
    csv_input = wait.until(EC.presence_of_element_located((By.ID, "csvFile")))
    csv_input.send_keys(abs_path(filepath))
    time.sleep(1)

    upload_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[@type='submit' and contains(.,'Upload CSV')]")
        )
    )
    upload_btn.click()


def get_alert_text(driver, timeout=DEFAULT_WAIT):
    """Wait for AlertDescription and return its text."""
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.CSS_SELECTOR, "[class*='AlertDescription']")
            )
        )
        return el.text.strip()
    except Exception:
        pass
    try:
        el = WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "[role='alert']"))
        )
        return el.text.strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def auth_driver():
    driver = make_driver()
    yield driver
    driver.quit()


# ---------------------------------------------------------------------------
# TP-UC9-007
# ---------------------------------------------------------------------------

class TestTP_UC9_007:

    # ── TC-UC9-008 : Invalid file format (.pdf) is rejected ─────────────
    def test_tc_uc9_008_invalid_file_format(self, auth_driver):
        """
        TC-UC9-008

        Step 1 : Log in as Admin One, verify JWT + companyId.
        Step 2 : Navigate to http://localhost:3000/weather-data.
        Step 3 : In 'Upload CSV Data', select weather_valid.pdf
                 (invalid file format — not a CSV).
        Step 4 : Click "Upload CSV".
        Step 5 : Verify the system displays:
                 "Failed to process CSV file. Please check the format."
        """
        driver = auth_driver
        wait   = WebDriverWait(driver, DEFAULT_WAIT)

        assert os.path.isfile(INVALID_FORMAT), (
            f"Fixture not found: {INVALID_FORMAT}"
        )

        # Step 1 & 2 : Login and navigate
        login_and_go_to_weather(driver)

        # Step 3 & 4 : Upload invalid format file
        upload_file(driver, INVALID_FORMAT)

        # Step 5 : Verify error message
        alert_text = get_alert_text(driver)
        assert FORMAT_ERROR_MSG in alert_text, (
            f"TC-UC9-008 FAILED: Expected '{FORMAT_ERROR_MSG}'. "
            f"Actual: '{alert_text}'"
        )

        print("TC-UC9-008 Invalid File Format Rejected - PASS")

    # ── TC-UC9-010 : CSV with missing temperature column is rejected ──────
    def test_tc_uc9_010_missing_column_csv(self, auth_driver):
        """
        TC-UC9-010

        Step 1 : Log in as Admin One, verify JWT + companyId.
        Step 2 : Navigate to http://localhost:3000/weather-data.
        Step 3 : In 'Upload CSV Data', select weather_missing.csv
                 (contains date, humidity, rainfall, location but NO temperature).
        Step 4 : Click "Upload CSV".
        Step 5 : Verify the system displays:
                 "Failed to process CSV file. Please check the format."
        """
        driver = auth_driver
        wait   = WebDriverWait(driver, DEFAULT_WAIT)

        assert os.path.isfile(MISSING_COL_CSV), (
            f"Fixture not found: {MISSING_COL_CSV}"
        )

        # Step 1 & 2 : Login and navigate
        login_and_go_to_weather(driver)

        # Step 3 & 4 : Upload missing-column CSV
        upload_file(driver, MISSING_COL_CSV)

        # Step 5 : Verify error message
        alert_text = get_alert_text(driver)
        assert FORMAT_ERROR_MSG in alert_text, (
            f"TC-UC9-010 FAILED: Expected '{FORMAT_ERROR_MSG}'. "
            f"Actual: '{alert_text}'"
        )

        print("TC-UC9-010 Missing Column CSV Rejected - PASS")

    # ── TC-UC9-024 : CSV with out-of-range data is rejected ───────────────
    def test_tc_uc9_024_out_of_range_data_csv(self, auth_driver):
        """
        TC-UC9-024

        Step 1 : Log in as Admin One, verify JWT + companyId.
        Step 2 : Navigate to http://localhost:3000/weather-data.
        Step 3 : In 'Upload CSV Data', select invalid_data.csv
                 (contains a row where temperature = 100, out of valid range).
        Step 4 : Click "Upload CSV".
        Step 5 : Verify the system displays:
                 "Failed to process CSV file. Please check the data."
        """
        driver = auth_driver
        wait   = WebDriverWait(driver, DEFAULT_WAIT)

        assert os.path.isfile(INVALID_DATA_CSV), (
            f"Fixture not found: {INVALID_DATA_CSV}"
        )

        # Step 1 & 2 : Login and navigate
        login_and_go_to_weather(driver)

        # Step 3 & 4 : Upload out-of-range data CSV
        upload_file(driver, INVALID_DATA_CSV)

        # Step 5 : Verify error message
        alert_text = get_alert_text(driver)
        assert DATA_ERROR_MSG in alert_text, (
            f"TC-UC9-024 FAILED: Expected '{DATA_ERROR_MSG}'. "
            f"Actual: '{alert_text}'"
        )

        print("TC-UC9-024 Out-of-Range Data CSV Rejected - PASS")