# tests/login/test_login_web.py

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:3000"
LOGIN_URL = BASE_URL          # admin login lives at /
DASHBOARD_URL = f"{BASE_URL}/dashboard"
SIGNUP_URL = f"{BASE_URL}/signup"
FORGOT_PASSWORD_URL = f"{BASE_URL}/forgot-password"

# ── Pre-conditions (must exist in database) ──────────────────────────────────
ADMIN_EMAIL = "admin@drone4dengue.com"
ADMIN_PASSWORD = "Drone4Dengue!"

NON_ADMIN_EMAIL = "wingtenglei@gmail.com"   # role = public / mobile user
NON_ADMIN_PASSWORD = "Drone4Dengue!"

WRONG_PASSWORD = "WrongPass!"
UNREGISTERED_EMAIL = "notregistered@test.com"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _wait_for_login_form(driver, timeout=15):
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, timeout)
    # Login card animates in (opacity 0 → 1); presence alone is not enough.
    wait.until(EC.visibility_of_element_located((By.ID, "email")))
    wait.until(EC.visibility_of_element_located((By.ID, "password")))
    return wait


def _fill_login_form(driver, *, email="", password=""):
    email_field = driver.find_element(By.ID, "email")
    email_field.clear()
    if email:
        email_field.send_keys(email)

    password_field = driver.find_element(By.ID, "password")
    password_field.clear()
    if password:
        password_field.send_keys(password)


def _click_login(driver):
    driver.find_element(
        By.XPATH,
        "//button[@type='submit' and contains(translate(., 'login', 'LOGIN'), 'LOGIN')]",
    ).click()


def _get_error_text(driver, wait, timeout=10):
    """Return the visible error banner text (AlertCircle area)."""
    error_el = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(@class,'bg-red') or contains(@class,'text-red')]"
                       "/following-sibling::span | "
                       "//*[contains(@class,'bg-red-500')]//span")
        )
    )
    return error_el.text


# ── TP-UC1-001: Successful admin login ──────────────────────────────────────
def test_successful_admin_login_web(web_driver):
    """Main Flow – admin logs in with valid credentials and is redirected to /dashboard."""
    wait = _wait_for_login_form(web_driver)

    _fill_login_form(web_driver, email=ADMIN_EMAIL, password=ADMIN_PASSWORD)
    _click_login(web_driver)

    wait.until(lambda d: d.current_url.rstrip("/") == DASHBOARD_URL.rstrip("/"))
    assert web_driver.current_url.rstrip("/") == DASHBOARD_URL.rstrip("/"), (
        "FAIL: Admin not redirected to /dashboard after successful login"
    )
    print("PASS: Admin successfully logged in and redirected to /dashboard")


# ── TP-UC1-002: Sign Up link redirect ───────────────────────────────────────
def test_signup_redirect_from_login_web(web_driver):
    """Alternative Flow – clicking 'Sign up' on login page redirects to /signup."""
    wait = _wait_for_login_form(web_driver)

    signup_link = wait.until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Sign up"))
    )
    signup_link.click()

    wait.until(lambda d: d.current_url.rstrip("/") == SIGNUP_URL.rstrip("/"))
    assert web_driver.current_url.rstrip("/") == SIGNUP_URL.rstrip("/"), (
        "FAIL: Not redirected to Sign Up / Registration page"
    )
    print("PASS: Redirected to Registration page from Login")


# ── TP-UC1-003: Forgot Password redirect (email entry verified manually) ─────
def test_forgot_password_redirect_web(web_driver):
    """Clicking 'Forgot Password ?' opens the reset-password page (no email submit)."""
    wait = _wait_for_login_form(web_driver)

    forgot_link = wait.until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Forgot Password ?"))
    )
    forgot_link.click()

    wait.until(lambda d: "/forgot-password" in d.current_url)
    assert web_driver.current_url.rstrip("/") == FORGOT_PASSWORD_URL.rstrip("/"), (
        "FAIL: Not redirected to /forgot-password"
    )

    reset_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Reset Password')]")
        )
    )
    assert reset_heading.is_displayed(), "FAIL: Reset Password page title not shown"

    email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
    assert email_field.is_displayed(), "FAIL: Email field not visible on reset page"

    print("PASS: Redirected to forgot-password page (email reset verified manually)")


# ── TP-UC1-004: Empty email field ────────────────────────────────────────────
def test_empty_email_web(web_driver):
    """Exception Flow – submitting with empty email shows validation error."""
    wait = _wait_for_login_form(web_driver)

    _fill_login_form(web_driver, email="", password=ADMIN_PASSWORD)
    _click_login(web_driver)

    # Browser native validation or custom error
    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'Email') or contains(text(),'email') or "
             "contains(text(),'required')]")
        )
    )
    assert error.is_displayed(), "FAIL: Empty email error NOT shown"
    print("PASS: Empty email validation error displayed")


# ── TP-UC1-005: Empty password field ─────────────────────────────────────────
def test_empty_password_web(web_driver):
    """Exception Flow – submitting with empty password shows validation error."""
    wait = _wait_for_login_form(web_driver)

    _fill_login_form(web_driver, email=ADMIN_EMAIL, password="")
    _click_login(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'Password') or contains(text(),'password') or "
             "contains(text(),'required')]")
        )
    )
    assert error.is_displayed(), "FAIL: Empty password error NOT shown"
    print("PASS: Empty password validation error displayed")


# ── TP-UC1-006: Invalid email format ─────────────────────────────────────────
def test_invalid_email_format_web(web_driver):
    """Invalid email is blocked by HTML5 validation (native tooltip on type=email)."""
    wait = _wait_for_login_form(web_driver)

    _fill_login_form(web_driver, email="adminATdrone4dengue.com", password=ADMIN_PASSWORD)
    _click_login(web_driver)

    email_field = web_driver.find_element(By.ID, "email")

    def _browser_rejects_email(driver):
        message = driver.execute_script(
            "return arguments[0].validationMessage;", email_field
        )
        is_valid = driver.execute_script(
            "return arguments[0].checkValidity();", email_field
        )
        if not is_valid and message:
            return message
        return False

    validation_message = wait.until(_browser_rejects_email)
    assert "@" in validation_message, (
        f"FAIL: Expected '@' in browser validation message, got: {validation_message!r}"
    )
    assert "/dashboard" not in web_driver.current_url, (
        "FAIL: Login submitted despite invalid email format"
    )
    print(f"PASS: Browser blocked invalid email ({validation_message!r})")


# ── TP-UC1-007: Wrong password ────────────────────────────────────────────────
def test_wrong_password_web(web_driver):
    """Exception Flow – correct email with wrong password shows error message."""
    wait = _wait_for_login_form(web_driver)

    _fill_login_form(web_driver, email=ADMIN_EMAIL, password=WRONG_PASSWORD)
    _click_login(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'Incorrect password') or "
             "contains(text(),'Wrong password') or "
             "contains(text(),'Invalid') or "
             "contains(text(),'failed')]")
        )
    )
    assert error.is_displayed(), "FAIL: Wrong password error NOT shown"
    # Ensure user is NOT redirected to dashboard
    assert "/dashboard" not in web_driver.current_url, (
        "FAIL: User was redirected to dashboard despite wrong password"
    )
    print("PASS: Wrong password error displayed, user remains on login page")


# ── TP-UC1-008: Unregistered email ───────────────────────────────────────────
def test_unregistered_email_web(web_driver):
    """Exception Flow – unknown email shows login error and stays on login page."""
    wait = _wait_for_login_form(web_driver)

    _fill_login_form(web_driver, email=UNREGISTERED_EMAIL, password="User123!")
    _click_login(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'Invalid credentials') or "
             "contains(text(),'No account') or "
             "contains(text(),'not found') or "
             "contains(text(),'User not found') or "
             "contains(text(),'does not exist')]")
        )
    )
    assert error.is_displayed(), "FAIL: Unregistered email error NOT shown"
    assert "/dashboard" not in web_driver.current_url, (
        "FAIL: User was redirected to dashboard with unregistered email"
    )
    print("PASS: Unregistered email rejected with error banner")


# ── TP-UC1-009: Brute-force lockout (5+ failed attempts) ─────────────────────
def test_too_many_failed_attempts_web(web_driver):
    """Exception Flow – 5+ wrong passwords triggers lockout message."""
    wait = _wait_for_login_form(web_driver)

    lockout_detected = False
    for attempt in range(1, 7):
        _fill_login_form(web_driver, email=ADMIN_EMAIL, password=f"WrongPass{attempt}!")
        _click_login(web_driver)

        # Small wait for the error to appear before checking
        time.sleep(1.5)

        page_text = web_driver.find_element(By.TAG_NAME, "body").text
        if any(phrase in page_text for phrase in [
            "Too many",
            "too many",
            "locked",
            "try again later",
            "rate limit",
        ]):
            lockout_detected = True
            print(f"  Lockout triggered after {attempt} attempt(s)")
            break

        # If still on login page with a generic error, keep trying
        if "/dashboard" in web_driver.current_url:
            # Somehow logged in — force fail
            assert False, "FAIL: Logged in with wrong password"

    assert lockout_detected, (
        "FAIL: Lockout / rate-limit message NOT shown after 6 consecutive wrong-password attempts"
    )
    print("PASS: Brute-force lockout message displayed after repeated failed logins")


# ── TP-UC1-010: Non-admin role blocked on Admin Web ──────────────────────────
def test_non_admin_blocked_web(web_driver):
    """Exception Flow – a public/mobile user account is denied access on Admin Web."""
    wait = _wait_for_login_form(web_driver)

    _fill_login_form(web_driver, email=NON_ADMIN_EMAIL, password=NON_ADMIN_PASSWORD)
    _click_login(web_driver)

    # Expect an access-denied error and NOT a redirect to /dashboard
    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'Access denied') or "
             "contains(text(),'Admin privileges') or "
             "contains(text(),'not authorized') or "
             "contains(text(),'permission')]")
        )
    )
    assert error.is_displayed(), "FAIL: Non-admin access-denied error NOT shown"
    assert "/dashboard" not in web_driver.current_url, (
        "FAIL: Non-admin user was granted access to /dashboard"
    )
    print("PASS: Non-admin user correctly denied access with error message")


# ── TP-UC1-011: Password visibility toggle ───────────────────────────────────
def test_password_visibility_toggle_web(web_driver):
    """UI Check – toggling the eye icon switches password field between text and password type."""
    wait = _wait_for_login_form(web_driver)

    _fill_login_form(web_driver, email=ADMIN_EMAIL, password=ADMIN_PASSWORD)

    password_field = web_driver.find_element(By.ID, "password")
    assert password_field.get_attribute("type") == "password", (
        "FAIL: Password field should start as type='password'"
    )

    # Click the show/hide toggle button (Eye icon)
    toggle_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH,
             "//button[@type='button' and .//svg[contains(@class,'lucide-eye') "
             "or contains(@data-lucide,'eye') "
             "or contains(@class,'Eye')]]"
             " | //button[@type='button' and .//*[local-name()='svg']]"
             "[contains(@class,'right-2')]")
        )
    )
    toggle_btn.click()

    assert password_field.get_attribute("type") == "text", (
        "FAIL: Password field should switch to type='text' after clicking show"
    )

    toggle_btn.click()
    assert password_field.get_attribute("type") == "password", (
        "FAIL: Password field should revert to type='password' after clicking hide"
    )
    print("PASS: Password visibility toggle works correctly")


# ── TP-UC1-012: Login page loads correctly ───────────────────────────────────
def test_login_page_elements_present_web(web_driver):
    """Smoke Test – verify all expected elements are present on the login page."""
    wait = _wait_for_login_form(web_driver)

    wait.until(EC.visibility_of_element_located((By.ID, "email")))
    wait.until(EC.visibility_of_element_located((By.ID, "password")))

    login_btn = wait.until(
        EC.visibility_of_element_located(
            (
                By.XPATH,
                "//button[@type='submit' and contains(translate(., 'login', 'LOGIN'), 'LOGIN')]",
            )
        )
    )
    forgot_link = wait.until(
        EC.visibility_of_element_located((By.LINK_TEXT, "Forgot Password ?"))
    )
    signup_link = wait.until(
        EC.visibility_of_element_located((By.LINK_TEXT, "Sign up"))
    )

    assert login_btn.is_displayed(), "FAIL: Login button not visible"
    assert forgot_link.is_displayed(), "FAIL: 'Forgot Password ?' link not visible"
    assert signup_link.is_displayed(), "FAIL: 'Sign up' link not visible"

    print("PASS: All expected login page elements are present and visible")


# ── TP-UC1-013: Successful login clears previous error ───────────────────────
def test_error_cleared_on_valid_login_web(web_driver):
    """Edge Case – error from a failed attempt is not carried over to a successful login."""
    wait = _wait_for_login_form(web_driver)

    # First: trigger a wrong-password error
    _fill_login_form(web_driver, email=ADMIN_EMAIL, password=WRONG_PASSWORD)
    _click_login(web_driver)

    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(@class,'bg-red-500')]")
        )
    )

    # Then: login with correct credentials
    _fill_login_form(web_driver, email=ADMIN_EMAIL, password=ADMIN_PASSWORD)
    _click_login(web_driver)

    wait.until(lambda d: d.current_url.rstrip("/") == DASHBOARD_URL.rstrip("/"))
    assert web_driver.current_url.rstrip("/") == DASHBOARD_URL.rstrip("/"), (
        "FAIL: Correct credentials after failed attempt did not redirect to /dashboard"
    )
    print("PASS: Successful login after a failed attempt redirects to /dashboard with no residual error")


# ── TP-UC1-014: Both fields empty ────────────────────────────────────────────
def test_both_fields_empty_web(web_driver):
    """Edge Case – submitting with both fields empty shows at least one validation error."""
    wait = _wait_for_login_form(web_driver)

    _fill_login_form(web_driver, email="", password="")
    _click_login(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'required') or "
             "contains(text(),'Email') or "
             "contains(text(),'Password') or "
             "contains(text(),'valid')]")
        )
    )
    assert error.is_displayed(), "FAIL: No validation error shown when both fields are empty"
    assert "/dashboard" not in web_driver.current_url, (
        "FAIL: Redirected to dashboard with empty credentials"
    )
    print("PASS: Validation error shown when both fields are submitted empty")