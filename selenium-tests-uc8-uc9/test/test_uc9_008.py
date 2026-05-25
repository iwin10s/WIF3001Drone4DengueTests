# """
# test_uc9_008.py

# Test Procedure : TP-UC9-008
# Test Cases     : TC-UC9-009
# Objective      : Verify that an error message is displayed when a database
#                  save fails due to mock server latency or connection errors
#                  (simulated via DevTools network throttling / offline mode).

# Confirmed from page.tsx line 452:
#   - Error message : "Failed to save weather record"
#                     (err.response?.data?.error || "Failed to save weather record")
#   - Alert selector: [class*='AlertDescription']

# NOTE: Selenium cannot directly trigger DevTools network conditions.
#       This test simulates a network drop by intercepting via Chrome DevTools
#       Protocol (CDP) using driver.execute_cdp_cmd() to set the network
#       offline before attempting to save, then restores it after.
# """

# import pytest
# import time
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.chrome.service import Service
# from selenium.webdriver.chrome.options import Options
# from webdriver_manager.chrome import ChromeDriverManager

# # ---------------------------------------------------------------------------
# # Constants
# # ---------------------------------------------------------------------------
# BASE_URL     = "http://localhost:3000"
# WEATHER_URL  = f"{BASE_URL}/weather-data"
# ADMIN_EMAIL  = "admin1@drone4dengue.com"
# ADMIN_PASS   = "adminpass1"
# DEFAULT_WAIT = 20

# # Confirmed from page.tsx line 452
# SAVE_ERROR_MSG = "Failed to save weather record"


# # ---------------------------------------------------------------------------
# # Helpers
# # ---------------------------------------------------------------------------

# def make_driver():
#     options = Options()
#     options.add_argument("--no-sandbox")
#     options.add_argument("--disable-dev-shm-usage")
#     driver = webdriver.Chrome(
#         service=Service(ChromeDriverManager().install()),
#         options=options,
#     )
#     driver.maximize_window()
#     return driver


# def login_and_go_to_weather(driver):
#     """Log in as Admin One with JWT + companyId gates, navigate to /weather-data."""
#     wait = WebDriverWait(driver, DEFAULT_WAIT)

#     driver.get(f"{BASE_URL}/")
#     wait.until(EC.visibility_of_element_located((By.ID, "email"))).send_keys(ADMIN_EMAIL)
#     driver.find_element(By.ID, "password").send_keys(ADMIN_PASS)
#     driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
#     wait.until(EC.url_contains("/dashboard"))
#     print(f"\n[Auth] Logged in as: {ADMIN_EMAIL} (Admin One)")

#     # Assert JWT token
#     token = driver.execute_script("return localStorage.getItem('token');")
#     assert token, (
#         f"JWT token not found in localStorage after login as {ADMIN_EMAIL}. "
#         "Admin MUST be authenticated before this test proceeds."
#     )
#     print("[Auth] JWT token present.")

#     # Assert companyId
#     company_val = driver.execute_script("""
#         return localStorage.getItem('companyId')
#             || localStorage.getItem('company_id')
#             || localStorage.getItem('user')
#             || localStorage.getItem('authUser');
#     """)
#     assert company_val, (
#         "companyId not found in localStorage after login. "
#         "companyId MUST exist in the auth context before test proceeds."
#     )
#     print(f"[Auth] companyId/user context confirmed: {str(company_val)[:80]}")

#     # Navigate to /weather-data
#     try:
#         sidebar = wait.until(
#             EC.element_to_be_clickable((By.XPATH, "//a[contains(@href,'/weather-data')]"))
#         )
#         sidebar.click()
#     except Exception:
#         driver.get(WEATHER_URL)

#     wait.until(
#         EC.visibility_of_element_located(
#             (By.XPATH, "//*[contains(text(),'Weather Data Management')]")
#         )
#     )
#     time.sleep(1)


# def set_network_offline(driver):
#     """Use Chrome DevTools Protocol to simulate network offline (500-equivalent)."""
#     driver.execute_cdp_cmd("Network.enable", {})
#     driver.execute_cdp_cmd("Network.emulateNetworkConditions", {
#         "offline": True,
#         "latency": 0,
#         "downloadThroughput": 0,
#         "uploadThroughput": 0,
#     })
#     print("[Network] Simulated network drop (offline mode).")


# def restore_network(driver):
#     """Restore normal network conditions via CDP."""
#     driver.execute_cdp_cmd("Network.emulateNetworkConditions", {
#         "offline": False,
#         "latency": 0,
#         "downloadThroughput": -1,
#         "uploadThroughput": -1,
#     })
#     print("[Network] Network restored to normal.")


# def get_alert_text(driver, timeout=DEFAULT_WAIT):
#     """Wait for AlertDescription and return its text."""
#     try:
#         el = WebDriverWait(driver, timeout).until(
#             EC.visibility_of_element_located(
#                 (By.CSS_SELECTOR, "[class*='AlertDescription']")
#             )
#         )
#         return el.text.strip()
#     except Exception:
#         pass
#     try:
#         el = WebDriverWait(driver, 5).until(
#             EC.visibility_of_element_located((By.CSS_SELECTOR, "[role='alert']"))
#         )
#         return el.text.strip()
#     except Exception:
#         return ""


# # ---------------------------------------------------------------------------
# # Fixture
# # ---------------------------------------------------------------------------

# @pytest.fixture(scope="function")
# def auth_driver():
#     driver = make_driver()
#     yield driver
#     # Wrap-up: always restore network on teardown
#     try:
#         restore_network(driver)
#     except Exception:
#         pass
#     driver.quit()


# # ---------------------------------------------------------------------------
# # TP-UC9-008
# # ---------------------------------------------------------------------------

# class TestTP_UC9_008:

#     # ── TC-UC9-009 : Save fails on network drop — error message shown ─────
#     def test_tc_uc9_009_save_fails_on_network_error(self, auth_driver):
#         """
#         TC-UC9-009

#         Step 1 : Log in as Admin One, verify JWT + companyId.
#         Step 2 : Navigate to http://localhost:3000/weather-data.
#         Step 3 : Click "Add New Record" to open the manual entry form.
#         Step 4 : Fill in valid weather record fields.
#         Step 5 : Simulate a network drop (CDP offline mode — equivalent to
#                  HTTP 500 / connection timeout).
#         Step 6 : Click "Add Record" to submit while network is offline.
#         Step 7 : Verify the system displays "Failed to save weather record".
#         Step 8 : Restore normal network connection settings (Wrap Up).
#         """
#         driver = auth_driver
#         wait   = WebDriverWait(driver, DEFAULT_WAIT)

#         # Step 1 & 2 : Login and navigate
#         login_and_go_to_weather(driver)

#         # Step 3 : Click "Add New Record" to open the inline form
#         add_btn = wait.until(
#             EC.element_to_be_clickable(
#                 (By.XPATH, "//button[contains(.,'Add New Record')]")
#             )
#         )
#         add_btn.click()

#         # Step 4 : Fill in valid form fields
#         # Confirmed IDs from page.tsx: date, temperature, humidity, rainfall,
#         # location, companyLocationId
#         wait.until(EC.visibility_of_element_located((By.ID, "date")))

#         driver.find_element(By.ID, "date").send_keys("2025-06-01")
#         driver.find_element(By.ID, "temperature").send_keys("28.5")
#         driver.find_element(By.ID, "humidity").send_keys("75")
#         driver.find_element(By.ID, "rainfall").send_keys("12.5")
#         driver.find_element(By.ID, "location").send_keys("Kuala Lumpur")

#         # Select first available operational area
#         from selenium.webdriver.support.ui import Select
#         try:
#             sel = Select(driver.find_element(By.ID, "companyLocationId"))
#             real_opts = [o for o in sel.options if o.get_attribute("value")]
#             assert len(real_opts) > 0, "No operational area options found."
#             sel.select_by_value(real_opts[0].get_attribute("value"))
#         except Exception as e:
#             raise AssertionError(f"Could not select operational area: {e}")

#         # Step 5 : Simulate network drop BEFORE clicking submit
#         set_network_offline(driver)

#         # Step 6 : Click "Add Record" submit button
#         submit_btn = wait.until(
#             EC.element_to_be_clickable(
#                 (By.XPATH, "//button[contains(.,'Add Record')]")
#             )
#         )
#         submit_btn.click()

#         # Step 7 : Verify error message is shown
#         alert_text = get_alert_text(driver, timeout=15)
#         assert SAVE_ERROR_MSG in alert_text, (
#             f"TC-UC9-009 FAILED: Expected '{SAVE_ERROR_MSG}'. "
#             f"Actual: '{alert_text}'"
#         )

#         # Step 8 (Wrap Up) : Restore network
#         restore_network(driver)

#         print("TC-UC9-009 Network Error Shows Failure Message - PASS")

"""
test_uc9_008.py

Test Procedure : TP-UC9-008
Test Cases     : TC-UC9-009
Objective      : Verify that an error message is displayed when a database
                 save fails due to mock server latency or connection errors
                 (simulated via DevTools network throttling / offline mode).

Confirmed from page.tsx line 452:
  - Error message : "Failed to save weather record"
                    (err.response?.data?.error || "Failed to save weather record")
  - Alert selector: [class*='AlertDescription']

NOTE: Selenium cannot directly trigger DevTools network conditions.
      This test simulates a network drop by intercepting via Chrome DevTools
      Protocol (CDP) using driver.execute_cdp_cmd() to set the network
      offline before attempting to save, then restores it after.
"""

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

# Confirmed from page.tsx line 452
SAVE_ERROR_MSG = "Failed to save weather record"


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
    time.sleep(1)


def set_network_offline(driver):
    """Use Chrome DevTools Protocol to simulate network offline (500-equivalent)."""
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd("Network.emulateNetworkConditions", {
        "offline": True,
        "latency": 0,
        "downloadThroughput": 0,
        "uploadThroughput": 0,
    })
    print("[Network] Simulated network drop (offline mode).")


def restore_network(driver):
    """Restore normal network conditions via CDP."""
    driver.execute_cdp_cmd("Network.emulateNetworkConditions", {
        "offline": False,
        "latency": 0,
        "downloadThroughput": -1,
        "uploadThroughput": -1,
    })
    print("[Network] Network restored to normal.")


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
    # Wrap-up: always restore network on teardown
    try:
        restore_network(driver)
    except Exception:
        pass
    driver.quit()


# ---------------------------------------------------------------------------
# TP-UC9-008
# ---------------------------------------------------------------------------

class TestTP_UC9_008:

    # ── TC-UC9-009 : Save fails on network drop — error message shown ─────
    def test_tc_uc9_009_save_fails_on_network_error(self, auth_driver):
        """
        TC-UC9-009

        Step 1 : Log in as Admin One, verify JWT + companyId.
        Step 2 : Navigate to http://localhost:3000/weather-data.
        Step 3 : Click "Add New Record" to open the manual entry form.
        Step 4 : Fill in valid weather record fields.
        Step 5 : Simulate a network drop (CDP offline mode — equivalent to
                 HTTP 500 / connection timeout).
        Step 6 : Click "Add Record" to submit while network is offline.
        Step 7 : Verify the system displays "Failed to save weather record".
        Step 8 : Restore normal network connection settings (Wrap Up).
        """
        driver = auth_driver
        wait   = WebDriverWait(driver, DEFAULT_WAIT)

        # Step 1 & 2 : Login and navigate
        login_and_go_to_weather(driver)

        # Step 3 : Click "Add New Record" via JS to bypass any overlay
        add_btn = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[contains(.,'Add New Record')]")
            )
        )
        driver.execute_script("arguments[0].click();", add_btn)

        # Poll until #date input is in DOM and has visible height
        # (framer-motion animates height 0->auto, so visibility check fires too early)
        def form_expanded(d):
            try:
                el = d.find_element(By.ID, "date")
                return d.execute_script(
                    "return arguments[0].offsetHeight > 0 "
                    "&& arguments[0].offsetParent !== null;", el
                )
            except Exception:
                return False

        WebDriverWait(driver, DEFAULT_WAIT).until(form_expanded)

        # Step 4 : Fill in valid form fields
        # Confirmed IDs from page.tsx: date, temperature, humidity, rainfall,
        # location, companyLocationId

        driver.find_element(By.ID, "date").send_keys("2025-06-01")
        driver.find_element(By.ID, "temperature").send_keys("28.5")
        driver.find_element(By.ID, "humidity").send_keys("75")
        driver.find_element(By.ID, "rainfall").send_keys("12.5")
        driver.find_element(By.ID, "location").send_keys("Kuala Lumpur")

        # Select first available operational area
        from selenium.webdriver.support.ui import Select
        try:
            sel = Select(driver.find_element(By.ID, "companyLocationId"))
            real_opts = [o for o in sel.options if o.get_attribute("value")]
            assert len(real_opts) > 0, "No operational area options found."
            sel.select_by_value(real_opts[0].get_attribute("value"))
        except Exception as e:
            raise AssertionError(f"Could not select operational area: {e}")

        # Step 5 : Simulate network drop BEFORE clicking submit
        set_network_offline(driver)

        # Step 6 : Click "Add Record" submit button
        submit_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(.,'Add Record')]")
            )
        )
        submit_btn.click()

        # Step 7 : Verify error message is shown
        alert_text = get_alert_text(driver, timeout=15)
        assert SAVE_ERROR_MSG in alert_text, (
            f"TC-UC9-009 FAILED: Expected '{SAVE_ERROR_MSG}'. "
            f"Actual: '{alert_text}'"
        )

        # Step 8 (Wrap Up) : Restore network
        restore_network(driver)

        print("TC-UC9-009 Network Error Shows Failure Message - PASS")