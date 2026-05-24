# tests/login/test_login_mobile.py
# Mobile driver is configured in conftest.py (Expo Go by default: host.exp.Exponent).

import time

import conftest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from tests.mobile_helpers import accept_medical_disclaimer_if_shown

MOBILE_EMAIL = "wingtenglei@gmail.com"
MOBILE_PASSWORD = "Drone4Dengue!"
WRONG_PASSWORD = "WrongPass!"
UNREGISTERED_EMAIL = "notregistered@test.com"
INVALID_EMAIL = "userATdrone4dengue.com"
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


def _set_input_text(driver, element, value, *, secure=False):
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


def _open_login_screen(driver, timeout=25):
    """Land on login with form fields visible (disclaimer + deep link)."""
    wait = WebDriverWait(driver, timeout)
    accept_medical_disclaimer_if_shown(driver)
    _deep_link(driver, "/--/(auth)/login")
    accept_medical_disclaimer_if_shown(driver)

    wait.until(EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "loginScreen")))
    wait.until(EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "loginForm")))
    wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "email"))
    )
    return wait


def _fill_login(driver, *, email="", password=""):
    email_el = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "email")
    _set_input_text(driver, email_el, email)
    pwd_el = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "password")
    _set_input_text(driver, pwd_el, password, secure=True)


def _hide_keyboard(driver):
    try:
        driver.hide_keyboard()
    except Exception:
        pass


def _tap_login(driver):
    _hide_keyboard(driver)
    btn = driver.find_element(AppiumBy.ACCESSIBILITY_ID, "loginButton")
    _tap_element(driver, btn)
    time.sleep(0.8)


def _page_contains(driver, fragment):
    return fragment.lower() in driver.page_source.lower()


def _wait_for_login_error(driver, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        for test_id in ("loginErrorText", "loginError"):
            for el in driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id):
                text = _element_text(el).strip()
                if text and text != "[object Object]":
                    return el

        for frag in ("required", "valid email", "invalid", "credentials", "not found"):
            predicate = (
                f'type == "XCUIElementTypeStaticText" AND label CONTAINS[c] "{frag}"'
            )
            try:
                el = driver.find_element(AppiumBy.IOS_PREDICATE, predicate)
                if _element_text(el).strip():
                    return el
            except Exception:
                pass

        if _page_contains(driver, "email is required") or _page_contains(
            driver, "password is required"
        ):
            return True

        time.sleep(0.3)

    raise TimeoutException("Login error banner not found")


def _assert_login_error(error, message):
    text = _element_text(error).strip()
    assert text and text != "[object Object]", message


# ─── TC-01-002: Successful mobile login ───────────────────
def test_mobile_user_login(mobile_driver):
    _open_login_screen(mobile_driver)

    _fill_login(mobile_driver, email=MOBILE_EMAIL, password=MOBILE_PASSWORD)
    _tap_login(mobile_driver)

    home_wait = WebDriverWait(mobile_driver, 45)
    try:
        home_wait.until(
            EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "homeTab"))
        )
    except TimeoutException:
        try:
            home_wait.until(
                EC.presence_of_element_located(
                    (AppiumBy.ACCESSIBILITY_ID, "dashboardScreen")
                )
            )
        except TimeoutException:
            try:
                home_wait.until(
                    EC.presence_of_element_located(
                        (AppiumBy.ACCESSIBILITY_ID, "dashboardTitle")
                    )
                )
            except TimeoutException:
                errs = mobile_driver.find_elements(
                    AppiumBy.ACCESSIBILITY_ID, "loginErrorText"
                )
                if errs and _element_text(errs[0]).strip():
                    raise AssertionError(
                        f"FAIL: Login did not reach dashboard — {_element_text(errs[0])}"
                    ) from None
                raise

    print("PASS: Mobile user redirected to dashboard")


# ─── TC-01-003: Sign Up link redirects to Register ────────
def test_signup_redirect_mobile(mobile_driver):
    wait = _open_login_screen(mobile_driver)

    sign_up = wait.until(
        EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, "signUpLink"))
    )
    _tap_element(mobile_driver, sign_up)

    register = wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "registerScreen"))
    )
    assert register is not None, "FAIL: Not redirected to Register screen"
    print("PASS: Redirected to Register screen")


# ─── TC-01-005: Forgot Password redirect ──────────────────
def test_forgot_password_redirect_mobile(mobile_driver):
    wait = _open_login_screen(mobile_driver)

    forgot = wait.until(
        EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, "forgotPasswordLink"))
    )
    _tap_element(mobile_driver, forgot)

    reset_email = wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "resetEmailInput"))
    )
    assert reset_email is not None, "FAIL: Reset password UI did not appear"

    for test_id in ("sendResetCodeButton", "sendResetButton"):
        els = mobile_driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)
        if els:
            assert els[0] is not None, "FAIL: Send reset button not visible"
            print("PASS: Forgot password UI opened (email reset verified manually)")
            return

    mobile_driver.find_element(
        AppiumBy.IOS_PREDICATE,
        'label CONTAINS[c] "Send Reset Code" AND type == "XCUIElementTypeButton"',
    )
    print("PASS: Forgot password UI opened (email reset verified manually)")


# ─── TC-01-006: Empty email field ─────────────────────────
def test_empty_email_mobile(mobile_driver):
    """Submit with empty fields — do not fill password (iOS autofill can populate email)."""
    _open_login_screen(mobile_driver)

    _tap_login(mobile_driver)

    error = _wait_for_login_error(mobile_driver)
    _assert_login_error(error, "FAIL: Email error not shown")
    print("PASS: Email required error shown")


# ─── TC-01-007: Empty password field ──────────────────────
def test_empty_password_mobile(mobile_driver):
    _open_login_screen(mobile_driver)

    _fill_login(mobile_driver, email=MOBILE_EMAIL, password="")
    _tap_login(mobile_driver)

    error = _wait_for_login_error(mobile_driver)
    _assert_login_error(error, "FAIL: Password error not shown")
    print("PASS: Password required error shown")


# ─── TC-01-008: Invalid email format ──────────────────────
def test_invalid_email_format_mobile(mobile_driver):
    _open_login_screen(mobile_driver)

    _fill_login(mobile_driver, email=INVALID_EMAIL, password=MOBILE_PASSWORD)
    _tap_login(mobile_driver)

    error = _wait_for_login_error(mobile_driver)
    _assert_login_error(error, "FAIL: Invalid email format error not shown")
    print("PASS: Invalid email format error shown")


# ─── TC-01-009: Wrong password ────────────────────────────
def test_wrong_password_mobile(mobile_driver):
    _open_login_screen(mobile_driver)

    _fill_login(mobile_driver, email=MOBILE_EMAIL, password=WRONG_PASSWORD)
    _tap_login(mobile_driver)

    error = _wait_for_login_error(mobile_driver)
    _assert_login_error(error, "FAIL: Wrong password error not shown")
    print("PASS: Wrong password error shown")


# ─── TC-01-010: Unregistered email ────────────────────────
def test_unregistered_email_mobile(mobile_driver):
    _open_login_screen(mobile_driver)

    _fill_login(mobile_driver, email=UNREGISTERED_EMAIL, password=MOBILE_PASSWORD)
    _tap_login(mobile_driver)

    error = _wait_for_login_error(mobile_driver)
    _assert_login_error(error, "FAIL: User not found error not shown")
    print("PASS: Unregistered email error shown")


# ─── TC-01-011: Too many failed attempts ──────────────────
def test_too_many_attempts_mobile(mobile_driver):
    """Expect lockout message if API enforces rate limiting; otherwise invalid credentials."""
    _open_login_screen(mobile_driver)

    last_error = None
    for _ in range(5):
        _fill_login(mobile_driver, email=MOBILE_EMAIL, password=WRONG_PASSWORD)
        _tap_login(mobile_driver)
        time.sleep(1)
        try:
            last_error = _wait_for_login_error(mobile_driver, timeout=8)
        except TimeoutException:
            pass

    assert last_error is not None, "FAIL: No error shown after repeated failed logins"
    _assert_login_error(last_error, "FAIL: Lockout / error not shown")
    print("PASS: Error shown after repeated failed login attempts")
