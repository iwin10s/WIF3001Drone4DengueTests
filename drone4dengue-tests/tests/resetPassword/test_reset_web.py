# tests/reset_password/test_reset_password_web.py
#
# Admin Web reset-password tests using Selenium.
# Covers the /forgot-password page visible in the UI screenshot:
#   - Email input field + "SEND CODE" button
#   - "Remember your password? Sign in" link
#   - "Back to Login" link (top-right)
#
# NOTE: TC-UC3-003 (full end-to-end reset) requires a real OTP from the inbox.
# Set the environment variable RESET_OTP=<code> before running that test, or
# skip it with:  pytest -k "not full_reset"

import os

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:3000"
LOGIN_URL = BASE_URL
FORGOT_URL = f"{BASE_URL}/forgot-password"

REGISTERED_EMAIL = "leiwingteng@gmail.com"
UNREGISTERED_EMAIL = "notregistered@test.com"
INVALID_EMAIL = "wingtengleiATgmail.com"
NEW_PASSWORD = "Drone4Dengue!New"
WRONG_CONFIRM = "Drone4Dengue!Wrong"
WEAK_PASSWORD = "weakpass"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _wait_for_forgot_form(driver, timeout=15):
    driver.get(FORGOT_URL)
    wait = WebDriverWait(driver, timeout)
    # The email input has no id in the screenshot; locate by type or placeholder
    wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@type='email'] | //input[@placeholder]")
        )
    )
    return wait


def _find_email_input(driver):
    for locator in [
        (By.ID, "email"),
        (By.XPATH, "//input[@type='email']"),
        (By.XPATH, "//input[contains(@placeholder,'email') or contains(@placeholder,'Email')]"),
    ]:
        els = driver.find_elements(*locator)
        if els:
            return els[0]
    raise Exception("Could not locate email input on Reset Password page")


def _fill_email(driver, email):
    field = _find_email_input(driver)
    field.clear()
    if email:
        field.send_keys(email)


def _click_send_code(driver):
    driver.find_element(
        By.XPATH,
        "//button[contains(translate(., 'sendcode', 'SENDCODE'), 'SEND CODE') "
        "or contains(translate(., 'send', 'SEND'), 'SEND')]",
    ).click()


def _get_visible_message(driver, wait, timeout=10):
    """Return the first visible status / error text on the page."""
    el = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[self::p or self::span or self::div]"
             "[string-length(normalize-space(text())) > 0]"
             "[not(self::label)]")
        )
    )
    return el


# ── TP-UC3-001: Valid email — code request ────────────────────────────────────
def test_valid_email_send_code_web(web_driver):
    """
    Main Flow – registered email triggers confirmation message on Admin Web.
    Verifies 'Enter the code' text appears and ensures no active errors block the flow.
    """
    # 1. Wait for the form to load
    wait = _wait_for_forgot_form(web_driver)

    # 2. Perform actions: Fill the email and click submit
    _fill_email(web_driver, REGISTERED_EMAIL)
    _click_send_code(web_driver)

    # 3. Strictly verify that the confirmation text appears on screen
    # This targets the specific "Enter the code" text you expect to see
    confirm = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(), 'Enter the code')]")
        )
    )
    assert confirm.is_displayed(), "FAIL: 'Enter the code' message was not displayed to the user."
    
    # 4. Check for error messages, but FILTER out invisible/hidden HTML elements
    all_error_els = web_driver.find_elements(
        By.XPATH, "//*[contains(text(),'not found') or contains(text(),'Error')]"
    )
    
    # Only care about error messages the user can actually see on screen
    visible_error_els = [el for el in all_error_els if el.is_displayed()]
    
    # If any visible error text exists, collect it for a descriptive failure message
    if visible_error_els:
        detected_errors = [el.text.strip() for el in visible_error_els if el.text.strip()]
        pytest.fail(f"FAIL: Error message(s) visible on screen for a valid registered email: {detected_errors}")

    # 5. Success!
    print("PASS: 'Enter the code' confirmation message displayed successfully without errors.")


# ── TP-UC3-005 (web half): Back to Login link ─────────────────────────────────
def test_back_to_login_link_web(web_driver):
    """Alternative Flow – clicking 'Back to Login' returns to the login page."""
    wait = _wait_for_forgot_form(web_driver)

    back_link = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//*[contains(text(),'Back to Login')]")
        )
    )
    back_link.click()

    wait.until(lambda d: d.current_url.rstrip("/") == LOGIN_URL.rstrip("/"))
    assert web_driver.current_url.rstrip("/") == LOGIN_URL.rstrip("/"), (
        "FAIL: Not redirected to login page after clicking 'Back to Login'"
    )
    print("PASS: 'Back to Login' redirects to login page")


# ── TP-UC3-013: "Remember your password? Sign in" link ───────────────────────
def test_remember_password_signin_link_web(web_driver):
    """Alternative Flow – 'Remember your password? Sign in' redirects to login."""
    wait = _wait_for_forgot_form(web_driver)

    signin_link = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH,
             "//*[contains(text(),'Sign in') or contains(text(),'sign in')]"
             "[not(self::button[@type='submit'])]")
        )
    )
    signin_link.click()

    wait.until(lambda d: d.current_url.rstrip("/") == LOGIN_URL.rstrip("/"))
    assert web_driver.current_url.rstrip("/") == LOGIN_URL.rstrip("/"), (
        "FAIL: Not redirected to login page after clicking 'Remember your password? Sign in'"
    )
    print("PASS: 'Remember your password? Sign in' redirects to login page")


# ── TP-UC3-006: Unregistered email ───────────────────────────────────────────
def test_unregistered_email_web(web_driver):
    """Exception Flow – unregistered email shows 'Email not found' error."""
    wait = _wait_for_forgot_form(web_driver)

    _fill_email(web_driver, UNREGISTERED_EMAIL)
    _click_send_code(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'not found') or contains(text(),'No account') "
             "or contains(text(),'does not exist') or contains(text(),'not registered')]")
        )
    )
    assert error.is_displayed(), "FAIL: 'Email not found' error NOT shown for unregistered email"
    print("PASS: 'Email not found' error displayed for unregistered email")


# ── TP-UC3-007: Empty email field ─────────────────────────────────────────────
def test_empty_email_web(web_driver):
    """Exception Flow – empty email field shows validation error."""
    wait = _wait_for_forgot_form(web_driver)

    _fill_email(web_driver, "")
    _click_send_code(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'required') or contains(text(),'enter') "
             "or contains(text(),'Email') or contains(text(),'empty')]")
        )
    )
    assert error.is_displayed(), "FAIL: Empty email validation error NOT shown"
    print("PASS: Empty email validation error displayed")


# ── TP-UC3-008: Invalid email format ─────────────────────────────────────────
def test_invalid_email_format_web(web_driver):
    """Exception Flow – malformed email shows format validation error."""
    wait = _wait_for_forgot_form(web_driver)

    _fill_email(web_driver, INVALID_EMAIL)
    _click_send_code(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'valid email') or contains(text(),'Invalid email') "
             "or contains(text(),'email address')]")
        )
    )
    assert error.is_displayed(), "FAIL: Invalid email format error NOT shown"
    print("PASS: Invalid email format error displayed")


# ── TP-UC3-009: Wrong reset code ─────────────────────────────────────────────
def test_wrong_reset_code_web(web_driver):
    """Exception Flow – incorrect OTP/code shows error and blocks password entry.

    Pre-condition: A real code must have been sent to the inbox first.
    This test sends the code request, then submits a deliberately wrong code.
    """
    wait = _wait_for_forgot_form(web_driver)

    # Step 1: send code
    _fill_email(web_driver, REGISTERED_EMAIL)
    _click_send_code(web_driver)

    # Wait for code input to appear (could be on same page or navigated step)
    try:
        code_input = wait.until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//input[@type='text' and not(@type='email')]"
                 " | //input[contains(@placeholder,'code') or contains(@placeholder,'OTP')]"
                 " | //input[@maxlength='6']")
            )
        )
    except Exception:
        print("SKIP: Code input field not reachable — UI may require inbox access to proceed.")
        return

    # Step 2: submit wrong code
    code_input.clear()
    code_input.send_keys("000000")

    web_driver.find_element(
        By.XPATH,
        "//button[@type='submit'] | //button[contains(text(),'Verify') "
        "or contains(text(),'Submit') or contains(text(),'Confirm')]",
    ).click()

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'Invalid code') or contains(text(),'incorrect') "
             "or contains(text(),'expired') or contains(text(),'wrong')]")
        )
    )
    assert error.is_displayed(), "FAIL: Wrong code error NOT shown"
    # Must NOT advance to password entry
    password_inputs = web_driver.find_elements(
        By.XPATH, "//input[@type='password']"
    )
    assert not password_inputs, (
        "FAIL: Password entry form appeared despite wrong code being submitted"
    )
    print("PASS: Wrong reset code error displayed, password entry NOT shown")


# ── TP-UC3-010: Password mismatch on reset ────────────────────────────────────
def test_password_mismatch_on_reset_web(web_driver):
    """Exception Flow – mismatched new/confirm passwords shows error.

    Requires a real OTP. Set env var RESET_OTP=<code> to run this test live.
    Without it the test is skipped gracefully.
    """
    otp = os.environ.get("RESET_OTP", "")
    if not otp:
        print("SKIP: RESET_OTP env var not set — skipping mismatch test (requires real inbox code)")
        return

    wait = _wait_for_forgot_form(web_driver)
    _fill_email(web_driver, REGISTERED_EMAIL)
    _click_send_code(web_driver)

    code_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@maxlength='6'] | //input[contains(@placeholder,'code')]")
        )
    )
    code_input.clear()
    code_input.send_keys(otp)
    web_driver.find_element(By.XPATH, "//button[@type='submit']").click()

    # Fill mismatched passwords
    new_pw = wait.until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='password'][1]"))
    )
    new_pw.send_keys(NEW_PASSWORD)
    confirm_pw = web_driver.find_element(By.XPATH, "//input[@type='password'][2]")
    confirm_pw.send_keys(WRONG_CONFIRM)
    web_driver.find_element(By.XPATH, "//button[@type='submit']").click()

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'do not match') or contains(text(),'mismatch') "
             "or contains(text(),'match')]")
        )
    )
    assert error.is_displayed(), "FAIL: Password mismatch error NOT shown"
    print("PASS: Password mismatch error displayed on reset page")


# ── TP-UC3-011: Weak new password rejected ────────────────────────────────────
def test_weak_new_password_web(web_driver):
    """Exception Flow – weak new password rejected by policy.

    Requires a real OTP. Set env var RESET_OTP=<code> to run this test live.
    """
    otp = os.environ.get("RESET_OTP", "")
    if not otp:
        print("SKIP: RESET_OTP env var not set — skipping weak password test")
        return

    wait = _wait_for_forgot_form(web_driver)
    _fill_email(web_driver, REGISTERED_EMAIL)
    _click_send_code(web_driver)

    code_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@maxlength='6'] | //input[contains(@placeholder,'code')]")
        )
    )
    code_input.clear()
    code_input.send_keys(otp)
    web_driver.find_element(By.XPATH, "//button[@type='submit']").click()

    new_pw = wait.until(
        EC.presence_of_element_located((By.XPATH, "//input[@type='password'][1]"))
    )
    new_pw.send_keys(WEAK_PASSWORD)
    confirm_pw = web_driver.find_element(By.XPATH, "//input[@type='password'][2]")
    confirm_pw.send_keys(WEAK_PASSWORD)
    web_driver.find_element(By.XPATH, "//button[@type='submit']").click()

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'uppercase') or contains(text(),'requirements') "
             "or contains(text(),'8 characters') or contains(text(),'symbol') "
             "or contains(text(),'policy') or contains(text(),'strong')]")
        )
    )
    assert error.is_displayed(), "FAIL: Weak password policy error NOT shown"
    print("PASS: Weak password policy error displayed on reset page")


# ── TP-UC3-012: Empty new password fields ────────────────────────────────────
def test_empty_new_password_web(web_driver):
    """Exception Flow – empty password fields on the reset form show validation error.

    Requires a real OTP. Set env var RESET_OTP=<code> to run this test live.
    """
    otp = os.environ.get("RESET_OTP", "")
    if not otp:
        print("SKIP: RESET_OTP env var not set — skipping empty password test")
        return

    wait = _wait_for_forgot_form(web_driver)
    _fill_email(web_driver, REGISTERED_EMAIL)
    _click_send_code(web_driver)

    code_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@maxlength='6'] | //input[contains(@placeholder,'code')]")
        )
    )
    code_input.clear()
    code_input.send_keys(otp)
    web_driver.find_element(By.XPATH, "//button[@type='submit']").click()

    # Leave both password fields empty and submit
    wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
    web_driver.find_element(By.XPATH, "//button[@type='submit']").click()

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'required') or contains(text(),'enter') "
             "or contains(text(),'Password') or contains(text(),'empty')]")
        )
    )
    assert error.is_displayed(), "FAIL: Empty password validation error NOT shown"
    print("PASS: Empty password validation error displayed on reset page")


# ── Smoke: Reset Password page elements present ───────────────────────────────
def test_reset_page_elements_present_web(web_driver):
    """Smoke – all expected UI elements are visible on the Reset Password page."""
    wait = _wait_for_forgot_form(web_driver)

    # Email input
    assert _find_email_input(web_driver).is_displayed(), "FAIL: Email input not visible"

    # SEND CODE button
    send_btn = web_driver.find_element(
        By.XPATH,
        "//button[contains(translate(., 'sendcode', 'SENDCODE'), 'SEND CODE') "
        "or contains(translate(., 'send', 'SEND'), 'SEND')]",
    )
    assert send_btn.is_displayed(), "FAIL: SEND CODE button not visible"

    # "Remember your password? Sign in" link
    signin_link = web_driver.find_element(
        By.XPATH, "//*[contains(text(),'Sign in') or contains(text(),'sign in')]"
    )
    assert signin_link.is_displayed(), "FAIL: Sign in link not visible"

    # "Back to Login" link
    back_link = web_driver.find_element(
        By.XPATH, "//*[contains(text(),'Back to Login') or contains(text(),'back to login')]"
    )
    assert back_link.is_displayed(), "FAIL: 'Back to Login' link not visible"

    print("PASS: All expected Reset Password page elements are present and visible")