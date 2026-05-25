"""
conftest.py — shared fixtures for Drone4Dengue Selenium test suite.

Provides:
  - driver   : a configured Chrome WebDriver instance (session-scoped)
  - logged_in: navigates to Data Management as an authenticated admin
"""

import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# ---------------------------------------------------------------------------
# Constants — override via environment variables if needed
# ---------------------------------------------------------------------------
BASE_URL    = os.getenv("APP_BASE_URL", "http://localhost:3000")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL",  "admin1@drone4dengue.com")
ADMIN_PASS  = os.getenv("ADMIN_PASS",   "adminpass1")
DATA_MGT_URL = f"{BASE_URL}/data-management"
WEATHER_URL  = f"{BASE_URL}/weather-data"

# ---------------------------------------------------------------------------
# Chrome driver fixture  (function-scoped so each test gets a clean browser)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def driver():
    """Spin up a headless Chrome session and tear it down after each test."""
    options = Options()
    options.add_argument("--headless")          # run without a display
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,900")

    # chromedriver must be on PATH (installed via npm chromedriver package)
    service = Service()
    drv = webdriver.Chrome(service=service, options=options)
    drv.implicitly_wait(10)  # seconds — applied globally to every find call

    yield drv

    drv.quit()


# ---------------------------------------------------------------------------
# Convenience fixture: authenticated browser already on Data Management page
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def logged_in(driver):
    """
    Log in as admin and navigate to /data-management.
    Returns the driver so tests can start interacting immediately.
    """
    from selenium.webdriver.common.by import By

    # Step 1 — open login page
    driver.get(f"{BASE_URL}/")

    # Step 2 — fill credentials
    driver.find_element(By.ID, "email").send_keys(ADMIN_EMAIL)
    driver.find_element(By.ID, "password").send_keys(ADMIN_PASS)

    # Step 3 — submit login form
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Step 4 — navigate to Weather Data
    driver.get(WEATHER_URL)

    return driver

"""
conftest.py — shared fixtures for Drone4Dengue Selenium test suite.

Provides:
  - driver     : configured Chrome WebDriver (function-scoped)
  - logged_in  : authenticated browser on /weather-data

Session-scoped preflight checks run once before any test:
  - Frontend reachable at localhost:3000
  - Backend  reachable at localhost:4000
  Both must be running or the entire session is aborted with a clear message.
"""

# import os
# import time
# import requests
# import pytest

# from selenium import webdriver
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC

# # ---------------------------------------------------------------------------
# # Constants — override via environment variables if needed
# # ---------------------------------------------------------------------------
# BASE_URL     = os.getenv("APP_BASE_URL",  "http://localhost:3000")
# API_URL      = os.getenv("API_BASE_URL",  "http://localhost:4000")
# ADMIN_EMAIL  = os.getenv("ADMIN_EMAIL",   "admin1@drone4dengue.com")
# ADMIN_PASS   = os.getenv("ADMIN_PASS",    "adminpass1")
# DATA_MGT_URL = BASE_URL + "/data-management"


# # ---------------------------------------------------------------------------
# # Session-scoped preflight — runs ONCE before the first test
# # Aborts the whole session immediately if either server is not up.
# # ---------------------------------------------------------------------------
# @pytest.fixture(scope="session", autouse=True)
# def require_servers():
#     """
#     Verify that both the Next.js frontend and the Express backend are
#     reachable before any test starts.

#     If either is down the session is aborted with an explicit error message
#     instead of every test failing with a confusing 'Upload failed' / 
#     'Failed to fetch' banner.

#     Start both servers before running pytest:
#         # Terminal 1 — frontend
#         npm run dev

#         # Terminal 2 — backend
#         npm run start   (or: node server.js / ts-node src/index.ts)

#         # Terminal 3 — tests
#         pytest test/
#     """
#     errors = []

#     # -- Check frontend --
#     try:
#         r = requests.get(BASE_URL, timeout=5)
#         # Any HTTP response (even a redirect) means the server is up
#     except requests.ConnectionError:
#         errors.append(
#             "Frontend NOT reachable at %s\n"
#             "  -> Start it with:  npm run dev" % BASE_URL
#         )

#     # -- Check backend --
#     try:
#         r = requests.get(API_URL, timeout=5)
#     except requests.ConnectionError:
#         errors.append(
#             "Backend NOT reachable at %s\n"
#             "  -> Start it with:  npm run start  (inside your backend folder)" % API_URL
#         )

#     if errors:
#         msg = "\n\n" + "=" * 60 + "\n"
#         msg += "PREFLIGHT FAILED — servers not running:\n\n"
#         msg += "\n\n".join(errors)
#         msg += "\n" + "=" * 60
#         pytest.exit(msg, returncode=3)


# # ---------------------------------------------------------------------------
# # Chrome WebDriver fixture (function-scoped — fresh browser per test)
# # ---------------------------------------------------------------------------
# @pytest.fixture(scope="function")
# def driver():
#     """Spin up a headless Chrome session; tear it down after each test."""
#     options = Options()
#     options.add_argument("--headless=new")
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     options.add_argument("--window-size=1440,900")
#     # Capture browser console logs
#     options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

#     drv = webdriver.Chrome(service=Service(), options=options)
#     drv.implicitly_wait(10)

#     yield drv

#     # -- Print any SEVERE console errors seen during the test --
#     try:
#         logs = drv.get_log("browser")
#         severe = [e for e in logs if e.get("level") == "SEVERE"]
#         if severe:
#             print("\n[BROWSER SEVERE LOGS]")
#             for e in severe:
#                 print("  ", e.get("message", "")[:200])
#     except Exception:
#         pass

#     drv.quit()


# # ---------------------------------------------------------------------------
# # logged_in fixture — authenticated browser already on /data-management
# # ---------------------------------------------------------------------------
# @pytest.fixture(scope="function")
# def logged_in(driver):
#     """
#     Log in as admin and navigate to /data-management.

#     Login flow (confirmed from page source):
#       - POST credentials via the login form (email + password inputs, submit button)
#       - After success the app redirects to /dashboard
#       - Token is stored in localStorage under the key 'token'
#       - We then navigate directly to /data-management

#     Returns the driver so tests can interact with the page immediately.
#     """
#     wait = WebDriverWait(driver, 15)

#     # Step 1 — open login page
#     driver.get(BASE_URL + "/")
#     time.sleep(1)

#     # Step 2 — fill credentials
#     driver.find_element(By.ID, "email").send_keys(ADMIN_EMAIL)
#     driver.find_element(By.ID, "password").send_keys(ADMIN_PASS)

#     # Step 3 — submit
#     driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

#     # Step 4 — wait for redirect to /dashboard (confirms login succeeded)
#     wait.until(EC.url_contains("/dashboard"))

#     # Step 5 — confirm token is in localStorage
#     token = driver.execute_script("return localStorage.getItem('token');")
#     assert token, (
#         "Login succeeded (redirected to /dashboard) but no 'token' found "
#         "in localStorage. Check AuthContext token storage key."
#     )

#     # Step 6 — navigate to Data Management
#     driver.get(DATA_MGT_URL)

#     # Step 7 — wait for the page heading to confirm the page loaded
#     wait.until(
#         EC.presence_of_element_located(
#             (By.XPATH, "//h1[contains(text(), 'Data Management')]")
#         )
#     )
#     # Extra pause for framer-motion stagger animations to settle
#     time.sleep(1.5)

#     return driver
