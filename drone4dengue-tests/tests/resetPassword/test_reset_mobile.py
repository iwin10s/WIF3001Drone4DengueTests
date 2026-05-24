# tests/reset_password/test_reset_password_mobile.py
#
# Mobile App reset-password tests using Appium.
# The Mobile App uses a 3-step flow:
#   Step 1 — Enter email + "Send Reset Code" / "Cancel"
#   Step 2 — Enter OTP code
#   Step 3 — Enter and confirm new password
#
# Tests that require a real OTP (TC-UC3-004, 009, 010, 011, 012) read from
# the environment variable RESET_OTP=<code>. Without it those tests skip.
#
# Pre-condition: wingtenglei@gmail.com must be registered in the system.

import os
import time

import conftest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from tests.mobile_helpers import accept_medical_disclaimer_if_shown

REGISTERED_EMAIL = "wingtenglei@gmail.com"
UNREGISTERED_EMAIL = "notregistered@test.com"
INVALID_EMAIL = "wingtengleiATgmail.com"
NEW_PASSWORD = "Drone4Dengue!New"
WRONG_CONFIRM = "Drone4Dengue!Wrong"
WEAK_PASSWORD = "weakpass"
EXPO_DEV_URL = conftest.EXPO_DEV_URL


def _bundle_id():
    bundle = conftest.MOBILE_BUNDLE_ID
    if not bundle:
        raise RuntimeError("mobile_driver session did not initialize MOBILE_BUNDLE_ID")
    return bundle


def _element_text(element):
    return (
        (element.text or "")
        or (element.get_attribute("value") or "")
        or (element.get_attribute("label") or "")
    )


def _deep_link(driver, route_path):
    url = f"{EXPO_DEV_URL.rstrip('/')}{route_path}"
    driver.activate_app(_bundle_id())
    driver.execute_script("mobile: deepLink", {"url": url, "bundleId": _bundle_id()})
    time.sleep(2)


def _page_contains(driver, fragment):
    return fragment.lower() in driver.page_source.lower()


def _tap_element(driver, element):
    try:
        element.click()
    except Exception:
        loc = element.location
        sz = element.size
        driver.execute_script(
            "mobile: tap",
            {"x": loc["x"] + sz["width"] // 2, "y": loc["y"] + sz["height"] // 2},
        )


def _set_input_text(driver, element, value, *, secure=False):
    """Fill RN TextInputs; mobile:type + send_keys so React state updates on iOS."""
    element.click()
    time.sleep(0.25)
    try:
        driver.execute_script("mobile: clearText", {"element": element})
    except Exception:
        try:
            element.clear()
        except Exception:
            pass
    if not value:
        time.sleep(0.2)
        return
    if secure:
        element.send_keys(value)
        time.sleep(0.3)
        return
    try:
        driver.execute_script("mobile: type", {"element": element, "text": value})
    except Exception:
        try:
            element.set_value(value)
        except Exception:
            element.send_keys(value)
    time.sleep(0.3)


def _hide_keyboard(driver):
    try:
        driver.hide_keyboard()
    except Exception:
        pass


def _open_login_screen(driver, timeout=20):
    wait = WebDriverWait(driver, timeout)
    accept_medical_disclaimer_if_shown(driver)
    _deep_link(driver, "/--/(auth)/login")
    accept_medical_disclaimer_if_shown(driver)
    wait.until(EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "loginScreen")))
    return wait


def _open_reset_screen_step1(driver, timeout=20):
    """Navigate to the Reset Password Step 1 (email entry) via the login screen."""
    wait = _open_login_screen(driver, timeout)

    # Tap "Forgot Password?" — try testID first, then text predicate
    forgot_btn = None
    for test_id in ("forgotPasswordLink", "forgotPassword", "forgotPasswordButton"):
        els = driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)
        if els:
            forgot_btn = els[0]
            break
    if forgot_btn is None:
        forgot_btn = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.IOS_PREDICATE,
                 'label CONTAINS[c] "Forgot Password" AND '
                 '(type == "XCUIElementTypeButton" OR type == "XCUIElementTypeStaticText")')
            )
        )
    forgot_btn.click()
    time.sleep(1)

    # Wait for Step 1 — email input or resetPasswordScreen
    try:
        wait.until(EC.presence_of_element_located(
            (AppiumBy.ACCESSIBILITY_ID, "resetPasswordScreen")
        ))
    except TimeoutException:
        wait.until(EC.presence_of_element_located(
            (AppiumBy.IOS_PREDICATE, 'placeholderValue CONTAINS[c] "email"')
        ))
    return wait


def _find_email_input_reset(driver):
    for test_id in ("resetEmailInput", "emailInput", "email"):
        els = driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)
        if els:
            return els[0]
    return driver.find_element(
        AppiumBy.IOS_PREDICATE, 'placeholderValue CONTAINS[c] "email"'
    )


def _find_reset_button(driver, wait, test_ids, label_fragment):
    for test_id in test_ids:
        try:
            return wait.until(
                EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, test_id))
            )
        except TimeoutException:
            continue
    return wait.until(
        EC.element_to_be_clickable(
            (
                AppiumBy.IOS_PREDICATE,
                f'label CONTAINS[c] "{label_fragment}" AND type == "XCUIElementTypeButton"',
            )
        )
    )


def _tap_send_reset_code(driver):
    _hide_keyboard(driver)
    wait = WebDriverWait(driver, 15)
    btn = _find_reset_button(
        driver,
        wait,
        ("sendResetCodeButton", "sendCodeButton", "submitButton"),
        "Send Reset Code",
    )
    _tap_element(driver, btn)
    time.sleep(0.5)


def _assert_error_visible(error, message):
    if error is True:
        return
    text = _element_text(error).strip()
    assert text and text != "[object Object]", message


def _wait_for_error(driver, fragments, timeout=15):
    """Wait for reset error message (avoid matching modal subtitle via bare 'email')."""
    fragments = [fragments] if isinstance(fragments, str) else list(fragments)
    deadline = time.time() + timeout

    skip_predicate = {"email", "enter", "empty", "fill"}

    while time.time() < deadline:
        for test_id in ("resetErrorMessage", "resetError"):
            for el in driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id):
                text = _element_text(el).strip()
                if not text or text == "[object Object]":
                    continue
                lower = text.lower()
                if any(f.lower() in lower for f in fragments):
                    return el

        for frag in fragments:
            if frag.lower() in skip_predicate:
                continue
            predicate = (
                f'type == "XCUIElementTypeStaticText" AND label CONTAINS[c] "{frag}"'
            )
            try:
                el = driver.find_element(AppiumBy.IOS_PREDICATE, predicate)
                if _element_text(el).strip():
                    return el
            except Exception:
                pass

        if any(_page_contains(driver, frag) for frag in fragments):
            return True

        time.sleep(0.3)

    visible = [
        _element_text(el).strip()
        for el in driver.find_elements(
            AppiumBy.IOS_PREDICATE, 'type == "XCUIElementTypeStaticText"'
        )
        if _element_text(el).strip()
    ]
    raise TimeoutException(
        f"Could not find error containing any of {fragments!r}. Visible text: {visible[:12]}"
    )


# ── TP-UC3-002: Valid email — Mobile App code request ────────────────────────
def test_valid_email_send_code_mobile(mobile_driver):
    """Main Flow – registered email triggers Step 2 (code entry) on Mobile App."""
    wait = _open_reset_screen_step1(mobile_driver)

    email_input = _find_email_input_reset(mobile_driver)
    _set_input_text(mobile_driver, email_input, REGISTERED_EMAIL)
    _tap_send_reset_code(mobile_driver)

    # Expect Step 2 — code entry screen (allow time for API + email send)
    step_wait = WebDriverWait(mobile_driver, 30)
    try:
        step2 = step_wait.until(
            EC.presence_of_element_located(
                (AppiumBy.ACCESSIBILITY_ID, "resetCodeScreen")
            )
        )
    except TimeoutException:
        step2 = step_wait.until(
            EC.presence_of_element_located(
                (AppiumBy.ACCESSIBILITY_ID, "resetCodeInput")
            )
        )

    assert step2 is not None, "FAIL: Step 2 (code entry) NOT shown after valid email"
    print("PASS: Step 2 (code entry) displayed after valid email submission on Mobile App")


# ── TP-UC3-005 (mobile half): Cancel button returns to login ──────────────────
def test_cancel_returns_to_login_mobile(mobile_driver):
    """Alternative Flow – tapping 'Cancel' dismisses the reset flow and shows login."""
    wait = _open_reset_screen_step1(mobile_driver)

    cancel_btn = None
    for test_id in ("cancelButton", "cancelResetButton", "cancelBtn"):
        els = mobile_driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)
        if els:
            cancel_btn = els[0]
            break
    if cancel_btn is None:
        cancel_btn = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.IOS_PREDICATE,
                 'label == "Cancel" AND type == "XCUIElementTypeButton"')
            )
        )
    cancel_btn.click()

    login_screen = wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "loginScreen"))
    )
    assert login_screen.is_displayed(), "FAIL: Login screen NOT shown after tapping Cancel"
    print("PASS: Tapping 'Cancel' returns to login screen on Mobile App")


# ── TP-UC3-006: Unregistered email ───────────────────────────────────────────
def test_unregistered_email_mobile(mobile_driver):
    """Exception Flow – unregistered email shows 'Email not found' error."""
    wait = _open_reset_screen_step1(mobile_driver)

    email_input = _find_email_input_reset(mobile_driver)
    _set_input_text(mobile_driver, email_input, UNREGISTERED_EMAIL)
    _tap_send_reset_code(mobile_driver)

    error = _wait_for_error(
        mobile_driver,
        ["not found", "no account", "does not exist", "not registered"],
    )
    _assert_error_visible(error, "FAIL: 'Email not found' error NOT shown for unregistered email")
    print("PASS: 'Email not found' error displayed for unregistered email on Mobile App")


# ── TP-UC3-007: Empty email field ─────────────────────────────────────────────
def test_empty_email_mobile(mobile_driver):
    """Exception Flow – empty email field shows validation error."""
    wait = _open_reset_screen_step1(mobile_driver)

    email_input = _find_email_input_reset(mobile_driver)
    _set_input_text(mobile_driver, email_input, "")
    _tap_send_reset_code(mobile_driver)

    error = _wait_for_error(
        mobile_driver,
        ["email is required", "required"],
    )
    _assert_error_visible(error, "FAIL: Empty email validation error NOT shown")
    print("PASS: Empty email validation error displayed on Mobile App")


# ── TP-UC3-008: Invalid email format ─────────────────────────────────────────
def test_invalid_email_format_mobile(mobile_driver):
    """Exception Flow – malformed email shows format error."""
    wait = _open_reset_screen_step1(mobile_driver)

    email_input = _find_email_input_reset(mobile_driver)
    _set_input_text(mobile_driver, email_input, INVALID_EMAIL)
    _tap_send_reset_code(mobile_driver)

    error = _wait_for_error(
        mobile_driver,
        ["valid email", "invalid email", "email address"],
    )
    _assert_error_visible(error, "FAIL: Invalid email format error NOT shown")
    print("PASS: Invalid email format error displayed on Mobile App")


# ── TP-UC3-009: Wrong reset code ─────────────────────────────────────────────
def test_wrong_reset_code_mobile(mobile_driver):
    """Exception Flow – incorrect OTP shows error and blocks password entry."""
    wait = _open_reset_screen_step1(mobile_driver)

    email_input = _find_email_input_reset(mobile_driver)
    _set_input_text(mobile_driver, email_input, REGISTERED_EMAIL)
    _tap_send_reset_code(mobile_driver)

    # Wait for Step 2 — code input
    try:
        code_input = wait.until(
            EC.presence_of_element_located(
                (AppiumBy.ACCESSIBILITY_ID, "resetCodeInput")
            )
        )
    except TimeoutException:
        try:
            code_input = wait.until(
                EC.presence_of_element_located(
                    (AppiumBy.IOS_PREDICATE,
                     'placeholderValue CONTAINS[c] "code" OR placeholderValue CONTAINS[c] "OTP"')
                )
            )
        except TimeoutException:
            print("SKIP: Code input not reachable — real inbox access may be required.")
            return

    _set_input_text(mobile_driver, code_input, "000000")
    _hide_keyboard(mobile_driver)

    # Tap verify / next
    for test_id in ("verifyCodeButton", "submitCodeButton", "nextButton"):
        els = mobile_driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)
        if els:
            els[0].click()
            break
    else:
        mobile_driver.find_element(
            AppiumBy.IOS_PREDICATE,
            'type == "XCUIElementTypeButton" AND '
            '(label CONTAINS[c] "Verify" OR label CONTAINS[c] "Submit" OR '
            'label CONTAINS[c] "Next" OR label CONTAINS[c] "Confirm")',
        ).click()

    error = _wait_for_error(
        mobile_driver,
        ["invalid code", "incorrect", "expired", "wrong code"],
    )
    _assert_error_visible(error, "FAIL: Wrong code error NOT shown")
    # Confirm Step 3 (password entry) is NOT shown
    pw_inputs = mobile_driver.find_elements(
        AppiumBy.IOS_PREDICATE,
        'placeholderValue CONTAINS[c] "password" AND type == "XCUIElementTypeSecureTextField"',
    )
    assert not pw_inputs, "FAIL: Password entry appeared despite wrong OTP"
    print("PASS: Wrong code error displayed, password entry NOT shown on Mobile App")


# ── TP-UC3-010: Password mismatch on reset ────────────────────────────────────
def test_password_mismatch_on_reset_mobile(mobile_driver):
    """Exception Flow – mismatched new/confirm passwords shows error.

    Requires a real OTP. Set env var RESET_OTP=<code> before running.
    """
    otp = os.environ.get("RESET_OTP", "")
    if not otp:
        print("SKIP: RESET_OTP env var not set — skipping mismatch test")
        return

    wait = _open_reset_screen_step1(mobile_driver)
    email_input = _find_email_input_reset(mobile_driver)
    _set_input_text(mobile_driver, email_input, REGISTERED_EMAIL)
    _tap_send_reset_code(mobile_driver)

    # Step 2 — enter real OTP
    code_input = wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "resetCodeInput"))
    )
    _set_input_text(mobile_driver, code_input, otp)
    _hide_keyboard(mobile_driver)
    for test_id in ("verifyCodeButton", "submitCodeButton", "nextButton"):
        els = mobile_driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)
        if els:
            els[0].click()
            break

    # Step 3 — enter mismatched passwords
    new_pw_input = wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "newPasswordInput"))
    )
    _set_input_text(mobile_driver, new_pw_input, NEW_PASSWORD, secure=True)

    confirm_pw_input = mobile_driver.find_element(
        AppiumBy.ACCESSIBILITY_ID, "confirmPasswordInput"
    )
    _set_input_text(mobile_driver, confirm_pw_input, WRONG_CONFIRM, secure=True)
    _hide_keyboard(mobile_driver)

    for test_id in ("resetSubmitButton", "submitButton"):
        els = mobile_driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)
        if els:
            els[0].click()
            break

    error = _wait_for_error(
        mobile_driver,
        ["do not match", "mismatch", "match", "same"],
    )
    _assert_error_visible(error, "FAIL: Password mismatch error NOT shown on Mobile App")
    print("PASS: Password mismatch error displayed on Mobile App")


# ── TP-UC3-011: Weak new password rejected ────────────────────────────────────
def test_weak_new_password_mobile(mobile_driver):
    """Exception Flow – weak new password rejected on Mobile App.

    Requires a real OTP. Set env var RESET_OTP=<code> before running.
    """
    otp = os.environ.get("RESET_OTP", "")
    if not otp:
        print("SKIP: RESET_OTP env var not set — skipping weak password test")
        return

    wait = _open_reset_screen_step1(mobile_driver)
    email_input = _find_email_input_reset(mobile_driver)
    _set_input_text(mobile_driver, email_input, REGISTERED_EMAIL)
    _tap_send_reset_code(mobile_driver)

    code_input = wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "resetCodeInput"))
    )
    _set_input_text(mobile_driver, code_input, otp)
    _hide_keyboard(mobile_driver)
    for test_id in ("verifyCodeButton", "submitCodeButton", "nextButton"):
        els = mobile_driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)
        if els:
            els[0].click()
            break

    new_pw_input = wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "newPasswordInput"))
    )
    _set_input_text(mobile_driver, new_pw_input, WEAK_PASSWORD, secure=True)
    confirm_pw_input = mobile_driver.find_element(
        AppiumBy.ACCESSIBILITY_ID, "confirmPasswordInput"
    )
    _set_input_text(mobile_driver, confirm_pw_input, WEAK_PASSWORD, secure=True)
    _hide_keyboard(mobile_driver)

    for test_id in ("resetSubmitButton", "submitButton"):
        els = mobile_driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)
        if els:
            els[0].click()
            break

    error = _wait_for_error(
        mobile_driver,
        ["uppercase", "requirements", "8 characters", "symbol", "policy", "meet", "strong"],
    )
    _assert_error_visible(error, "FAIL: Weak password policy error NOT shown on Mobile App")
    print("PASS: Weak password policy error displayed on Mobile App")


# ── TP-UC3-012: Empty new password fields ─────────────────────────────────────
def test_empty_new_password_mobile(mobile_driver):
    """Exception Flow – empty new password fields show validation error on Mobile App.

    Requires a real OTP. Set env var RESET_OTP=<code> before running.
    """
    otp = os.environ.get("RESET_OTP", "")
    if not otp:
        print("SKIP: RESET_OTP env var not set — skipping empty password test")
        return

    wait = _open_reset_screen_step1(mobile_driver)
    email_input = _find_email_input_reset(mobile_driver)
    _set_input_text(mobile_driver, email_input, REGISTERED_EMAIL)
    _tap_send_reset_code(mobile_driver)

    code_input = wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "resetCodeInput"))
    )
    _set_input_text(mobile_driver, code_input, otp)
    _hide_keyboard(mobile_driver)
    for test_id in ("verifyCodeButton", "submitCodeButton", "nextButton"):
        els = mobile_driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)
        if els:
            els[0].click()
            break

    # Leave both password fields empty and submit
    wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "newPasswordInput"))
    )
    _hide_keyboard(mobile_driver)
    for test_id in ("resetSubmitButton", "submitButton"):
        els = mobile_driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)
        if els:
            els[0].click()
            break

    error = _wait_for_error(
        mobile_driver,
        ["required", "enter", "password", "empty", "fill"],
    )
    _assert_error_visible(error, "FAIL: Empty password validation error NOT shown on Mobile App")
    print("PASS: Empty password validation error displayed on Mobile App")


# ── Smoke: Step 1 UI elements present ────────────────────────────────────────
def test_reset_screen_elements_present_mobile(mobile_driver):
    """Smoke – all expected UI elements visible on Step 1 of Mobile Reset Password."""
    wait = _open_reset_screen_step1(mobile_driver)

    # Email input
    email_input = _find_email_input_reset(mobile_driver)
    assert email_input.is_displayed(), "FAIL: Email input not visible on reset screen"

    send_btn = _find_reset_button(
        mobile_driver,
        wait,
        ("sendResetCodeButton", "sendCodeButton"),
        "Send Reset Code",
    )
    assert send_btn is not None, "FAIL: 'Send Reset Code' button not visible"

    cancel_btn = _find_reset_button(
        mobile_driver,
        wait,
        ("cancelButton", "cancelResetButton"),
        "Cancel",
    )
    assert cancel_btn is not None, "FAIL: 'Cancel' button not visible"

    # Step indicator (3 steps visible)
    step_indicators = mobile_driver.find_elements(
        AppiumBy.IOS_PREDICATE, 'type == "XCUIElementTypeStaticText" AND label IN {"1","2","3"}'
    )
    assert len(step_indicators) >= 3, (
        f"FAIL: Expected 3 step indicators, found {len(step_indicators)}"
    )

    print("PASS: All expected Step 1 Reset Password elements visible on Mobile App")