"""
Test Procedure ID : TP-UC8-001
Objective         : Verify that the system allows the admin to access the Data Management
                    module when authenticated, and blocks unauthenticated access routes.
Test Cases        : TC-UC8-001
                    - TCOV-08-001 : Authenticated admin logs in and navigates to /data-management
                    - TCOV-08-002 : Unauthenticated user is blocked from /data-management
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

BASE_URL       = "http://localhost:3000"
LOGIN_URL      = BASE_URL
DATA_MGMT_URL  = f"{BASE_URL}/data-management"
ADMIN_EMAIL    = "admin1@drone4dengue.com"
ADMIN_PASSWORD = "adminpass1"
DEFAULT_WAIT   = 10


def make_driver(incognito=False):
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if incognito:
        options.add_argument("--incognito")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    driver.maximize_window()
    return driver


def login(driver, email, password):
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, DEFAULT_WAIT)
    wait.until(EC.visibility_of_element_located((By.ID, "email"))).send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/dashboard"))


@pytest.fixture(scope="function")
def auth_driver():
    driver = make_driver(incognito=False)
    yield driver
    driver.quit()


@pytest.fixture(scope="function")
def anon_driver():
    driver = make_driver(incognito=True)
    yield driver
    driver.quit()


def test_authenticated_admin_can_access_data_management(auth_driver):
    driver = auth_driver
    wait   = WebDriverWait(driver, DEFAULT_WAIT)

    # Step 1 & 2 : Login with admin1@drone4dengue.com / adminpass1
    login(driver, ADMIN_EMAIL, ADMIN_PASSWORD)

    # Step 3 : Click Data Management in sidebar
    sidebar_link = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//a[@href='/data-management']"))
    )
    sidebar_link.click()

    # Step 4 : Verify URL is /data-management
    wait.until(EC.url_contains("/data-management"))
    assert "/data-management" in driver.current_url

    # Step 5 : Verify page heading is visible
    heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Data Management')]")
        )
    )
    assert heading.is_displayed()
    print("TC-UC8-001 Authenticated Admin Access - PASS")


def test_unauthenticated_user_is_blocked_from_data_management(anon_driver):
    driver = anon_driver
    wait   = WebDriverWait(driver, DEFAULT_WAIT)

    # Step 1 : Navigate directly to /data-management without logging in
    driver.get(DATA_MGMT_URL)

    # Step 2 : Wait for auth guard to resolve
    time.sleep(3)

    current_url = driver.current_url

    # Step 3 : Check if redirected to login
    redirected = (
        "/data-management" not in current_url
        and (
            current_url.rstrip("/") == LOGIN_URL.rstrip("/")
            or "/login" in current_url
            or "/error" in current_url
            or "/401" in current_url
            or "/403" in current_url
            or "/unauthorized" in current_url
        )
    )

    if redirected:
        login_form = wait.until(EC.visibility_of_element_located((By.ID, "email")))
        assert login_form.is_displayed()
        print("TC-UC8-001 Unauthenticated Access Blocked - PASS")
        return

    # Check for inline login prompt
    login_prompt_visible = False
    try:
        login_prompt_visible = driver.find_element(By.ID, "email").is_displayed()
    except Exception:
        pass

    if login_prompt_visible:
        print("TC-UC8-001 Unauthenticated Access Blocked - PASS")

    assert login_prompt_visible, (
        "DEFECT — TCOV-08-002: "
        "Unauthenticated user can fully access /data-management. "
        "No redirect and no login prompt were shown. "
        f"Current URL: {current_url}. "
        "The route guard is not enforced for this protected page."
    )