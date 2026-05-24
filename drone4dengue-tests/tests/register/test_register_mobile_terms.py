# tests/register/test_register_mobile_terms.py
#
# Mobile register: Terms & Conditions and Privacy Policy link navigation only.
# Requires Expo Go (or native build), Metro :8081, Appium :4723.

import os
import time
import uuid

import conftest
import pytest
import requests
from appium import webdriver as appium_driver
from appium.options.ios import XCUITestOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from tests.mobile_helpers import accept_medical_disclaimer_if_shown

VALID_PASSWORD = "Drone4Dengue!"
EXPO_DEV_URL = conftest.EXPO_DEV_URL
API_URL = os.environ.get("API_URL", "http://localhost:4000")
DUPLICATE_TEST_EMAIL = "wingtenglei@gmail.com"


@pytest.fixture(scope="module")
def mobile_driver():
    """One simulator session for the whole module (faster, matches manual testing flow)."""
    global MOBILE_BUNDLE_ID
    conftest.MOBILE_BUNDLE_ID = conftest._resolve_mobile_bundle_id()
    MOBILE_BUNDLE_ID = conftest.MOBILE_BUNDLE_ID

    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.device_name = conftest.MOBILE_DEVICE_NAME
    options.udid = conftest.MOBILE_UDID
    options.bundle_id = MOBILE_BUNDLE_ID
    options.automation_name = "XCUITest"
    options.new_command_timeout = 300

    app_path = os.environ.get("MOBILE_APP_PATH")
    if app_path:
        options.app = app_path

    driver = appium_driver.Remote("http://localhost:4723", options=options)
    driver.implicitly_wait(3)

    if MOBILE_BUNDLE_ID == conftest.EXPO_GO_BUNDLE_ID:
        conftest._launch_expo_project(driver, "/--/(auth)/login")
        time.sleep(2)

    accept_medical_disclaimer_if_shown(driver)
    yield driver
    driver.quit()


def _ensure_email_registered(email):
    """Create the email via API if it does not exist (409 is OK).

    Pre-condition note: wingtenglei@gmail.com must be seeded in the database
    before this test runs. This call is a best-effort safety net when the API
    is warm. If the API is unreachable the test is skipped so CI does not
    produce a false failure — seed the DB manually when running cold.
    """
    try:
        requests.post(
            f"{API_URL}/auth/register",
            json={"email": email, "password": VALID_PASSWORD, "companyId": "comp-999"},
            timeout=10,
        )
    except requests.RequestException as exc:
        pytest.skip(f"server-api not reachable at {API_URL}: {exc}")


def _bundle_id():
    bundle = conftest.MOBILE_BUNDLE_ID
    if not bundle:
        raise RuntimeError("mobile_driver session did not initialize MOBILE_BUNDLE_ID")
    return bundle


def _element_text(element):
    """iOS elements often expose copy via label/value instead of .text."""
    return (
        (element.text or "")
        or (element.get_attribute("value") or "")
        or (element.get_attribute("label") or "")
    )


def _page_contains(driver, fragment):
    """Fallback when error views are not exposed as separate accessibility nodes."""
    return fragment.lower() in driver.page_source.lower()


def _deep_link(driver, route_path):
    url = f"{EXPO_DEV_URL.rstrip('/')}{route_path}"
    driver.activate_app(_bundle_id())
    driver.execute_script(
        "mobile: deepLink",
        {"url": url, "bundleId": _bundle_id()},
    )
    time.sleep(2)


def _open_register_screen(driver, timeout=25):
    """Land on the register screen (deep link + fallback via login)."""
    wait = WebDriverWait(driver, timeout)

    accept_medical_disclaimer_if_shown(driver)
    _deep_link(driver, "/--/(auth)/register")
    accept_medical_disclaimer_if_shown(driver)

    try:
        wait.until(
            EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "registerScreen"))
        )
        return wait
    except TimeoutException:
        pass

    _deep_link(driver, "/--/(auth)/login")
    accept_medical_disclaimer_if_shown(driver)
    try:
        wait.until(
            EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "loginScreen"))
        )
        wait.until(
            EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, "signUpLink"))
        ).click()
        wait.until(
            EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "registerScreen"))
        )
        return wait
    except TimeoutException:
        # Last resort: placeholder-based locators (Expo Go without latest testIDs)
        wait.until(
            EC.presence_of_element_located(
                (AppiumBy.IOS_PREDICATE, 'placeholderValue == "Enter your email"')
            )
        )
        return wait


def _find_email_input(driver):
    try:
        return driver.find_element(AppiumBy.ACCESSIBILITY_ID, "email")
    except Exception:
        return driver.find_element(
            AppiumBy.IOS_PREDICATE, 'placeholderValue == "Enter your email"'
        )


def _find_password_input(driver):
    try:
        return driver.find_element(AppiumBy.ACCESSIBILITY_ID, "password")
    except Exception:
        return driver.find_element(
            AppiumBy.IOS_PREDICATE, 'placeholderValue == "Create a password"'
        )


def _find_confirm_password_input(driver):
    try:
        return driver.find_element(AppiumBy.ACCESSIBILITY_ID, "confirmPassword")
    except Exception:
        return driver.find_element(
            AppiumBy.IOS_PREDICATE, 'placeholderValue == "Confirm your password"'
        )


def _set_input_text(driver, element, value):
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
        return
    try:
        driver.execute_script(
            "mobile: type", {"element": element, "text": value}
        )
    except Exception:
        try:
            element.set_value(value)
        except Exception:
            element.send_keys(value)
    time.sleep(0.3)


def _is_toggle_on(element):
    """Read iOS Switch/checkbox state via value or selected attribute."""
    value = (element.get_attribute("value") or "").lower()
    if value in ("1", "true", "on", "checked", "yes"):
        return True
    selected = element.get_attribute("selected")
    return str(selected).lower() in ("true", "1")


def _terms_switch_on(driver):
    switches = driver.find_elements(
        AppiumBy.IOS_PREDICATE, 'type == "XCUIElementTypeSwitch"'
    )
    return switches and _is_toggle_on(switches[0])


def _accept_terms_toggle(driver):
    """Tap the T&C Switch (testID termsCheckbox) so onValueChange sets agree=true."""
    _scroll_register_form(driver, "up")
    toggle = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "termsCheckbox"))
    )
    if not _is_toggle_on(toggle):
        toggle.click()
        time.sleep(0.5)


def _fill_register_form(
    driver,
    *,
    email="wingtenglei@gmail.com",
    password=VALID_PASSWORD,
    confirm_password=None,
    accept_terms=True,
):
    if confirm_password is None:
        confirm_password = password

    _set_input_text(driver, _find_email_input(driver), email)
    _set_input_text(driver, _find_password_input(driver), password)
    _set_input_text(driver, _find_confirm_password_input(driver), confirm_password)

    if accept_terms:
        _accept_terms_toggle(driver)


def _hide_keyboard(driver):
    try:
        driver.hide_keyboard()
    except Exception:
        pass


def _scroll_register_form(driver, direction="up"):
    size = driver.get_window_size()
    driver.execute_script(
        "mobile: swipe",
        {
            "direction": direction,
            "left": size["width"] // 2,
            "top": int(size["height"] * 0.55),
            "width": 1,
            "height": int(size["height"] * 0.4),
        },
    )
    time.sleep(0.3)


def _tap_register(driver):
    _hide_keyboard(driver)
    _scroll_register_form(driver, "up")

    register_btn = None
    for test_id in ("registerButton", "createAccountButton"):
        els = driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id)
        if els:
            register_btn = els[0]
            break

    if register_btn is None:
        register_btn = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    AppiumBy.IOS_PREDICATE,
                    'type == "XCUIElementTypeButton" AND label CONTAINS[c] "Create Account"',
                )
            )
        )

    try:
        register_btn.click()
    except Exception:
        loc = register_btn.location
        sz = register_btn.size
        driver.execute_script(
            "mobile: tap",
            {
                "x": loc["x"] + sz["width"] // 2,
                "y": loc["y"] + sz["height"] // 2,
            },
        )
    time.sleep(0.8)


def _dismiss_success_alert_if_present(driver):
    try:
        driver.switch_to.alert.accept()
        time.sleep(0.5)
        return True
    except Exception:
        pass
    try:
        driver.find_element(
            AppiumBy.IOS_PREDICATE,
            'label == "OK" AND type == "XCUIElementTypeButton"',
        ).click()
        time.sleep(0.5)
        return True
    except Exception:
        return False


def _api_login_succeeded(email, password=VALID_PASSWORD):
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=5,
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def _wait_for_registration_success(driver, timeout=60, *, email=None):
    """Wait for login screen after register (alert + redirect, or API fallback)."""
    deadline = time.time() + timeout

    while time.time() < deadline:
        _dismiss_success_alert_if_present(driver)

        if driver.find_elements(
            AppiumBy.IOS_PREDICATE, 'placeholderValue == "Enter your password"'
        ):
            return
        if driver.find_elements(AppiumBy.ACCESSIBILITY_ID, "loginScreen"):
            return

        if email and _api_login_succeeded(email):
            _deep_link(driver, "/--/(auth)/login")
            accept_medical_disclaimer_if_shown(driver)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "loginScreen"))
            )
            return

        if _page_contains(driver, "enter your password") or _page_contains(
            driver, "registration successful"
        ):
            return

        for error_id in ("registerError", "registerErrorMessage", "emailFieldError"):
            for el in driver.find_elements(AppiumBy.ACCESSIBILITY_ID, error_id):
                text = _element_text(el)
                if text:
                    raise AssertionError(f"Registration failed on device: {text}")

        time.sleep(0.5)

    for error_id in ("registerError", "registerErrorMessage", "emailFieldError"):
        for el in driver.find_elements(AppiumBy.ACCESSIBILITY_ID, error_id):
            text = _element_text(el)
            if text:
                raise AssertionError(f"Registration failed on device: {text}")
    visible = []
    for el in driver.find_elements(
        AppiumBy.IOS_PREDICATE, 'type == "XCUIElementTypeStaticText"'
    ):
        text = _element_text(el).strip()
        if text:
            visible.append(text)
    raise TimeoutException(
        f"Registration did not complete. Visible messages: {visible[:12]}"
    )


def _assert_error_shown(error, message):
    if error is True:
        return
    assert error.is_displayed(), message


LEGAL_SCREEN_TEXT = ("terms and privacy policy", "terms and privacy")


def _assert_terms_legal_screen(driver, wait):
    """Both termsLink and privacyPolicyLink open /(auth)/terms (combined legal page)."""
    try:
        screen = wait.until(
            EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "termsScreen"))
        )
        assert screen.is_displayed(), "FAIL: termsScreen not visible"
    except TimeoutException:
        assert any(_page_contains(driver, text) for text in LEGAL_SCREEN_TEXT), (
            "FAIL: Not on Terms and Privacy Policy screen"
        )


def _return_to_register_screen(driver, wait, timeout=15):
    """Leave legal screen and land on register.

    Appium driver.back() often does not pop the Expo Router stack in Expo Go;
    prefer the in-app header back control, then deep-link if needed.
    """
    short = WebDriverWait(driver, 5)
    back_clicked = False
    for locator in (
        (AppiumBy.ACCESSIBILITY_ID, "termsBackButton"),
        (AppiumBy.ACCESSIBILITY_ID, "Back"),
        (
            AppiumBy.IOS_PREDICATE,
            'type == "XCUIElementTypeButton" AND label == "Back"',
        ),
    ):
        try:
            short.until(EC.element_to_be_clickable(locator)).click()
            back_clicked = True
            time.sleep(0.5)
            break
        except TimeoutException:
            continue

    if not back_clicked:
        try:
            driver.back()
            time.sleep(0.5)
        except Exception as exc:
            print(f"WARNING: driver.back() raised: {exc}")

    register_wait = WebDriverWait(driver, timeout)
    try:
        register_wait.until(
            EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "registerScreen"))
        )
        return
    except TimeoutException:
        pass

    try:
        register_wait.until(
            EC.presence_of_element_located(
                (AppiumBy.IOS_PREDICATE, 'placeholderValue == "Enter your email"')
            )
        )
        return
    except TimeoutException:
        pass

    print("WARNING: Register screen not found after back(); deep-linking to register.")
    _deep_link(driver, "/--/(auth)/register")
    accept_medical_disclaimer_if_shown(driver)
    wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "registerScreen"))
    )


def _wait_for_error(driver, test_id, text_fragment, timeout=20):
    wait = WebDriverWait(driver, timeout)
    fragments = [text_fragment] if isinstance(text_fragment, str) else list(text_fragment)

    _scroll_register_form(driver, "down")
    _scroll_register_form(driver, "up")

    if test_id:
        try:
            el = wait.until(
                EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, test_id))
            )
            if any(frag in _element_text(el).lower() for frag in fragments):
                return el
        except TimeoutException:
            pass

    for alt_id in ("registerError", "registerErrorMessage", "emailFieldError"):
        if alt_id == test_id:
            continue
        try:
            el = driver.find_element(AppiumBy.ACCESSIBILITY_ID, alt_id)
            if any(frag in _element_text(el).lower() for frag in fragments):
                return el
        except Exception:
            pass

    for frag in fragments:
        predicate = (
            f'type == "XCUIElementTypeStaticText" '
            f'AND label CONTAINS[c] "{frag}"'
        )
        try:
            return wait.until(
                EC.presence_of_element_located((AppiumBy.IOS_PREDICATE, predicate))
            )
        except TimeoutException:
            continue

    if any(_page_contains(driver, frag) for frag in fragments):
        return True

    visible = []
    for el in driver.find_elements(
        AppiumBy.IOS_PREDICATE, 'type == "XCUIElementTypeStaticText"'
    ):
        text = _element_text(el).strip()
        if text:
            visible.append(text)
    raise TimeoutException(
        f"Could not find error containing any of {fragments!r} (test_id={test_id!r}). "
        f"Visible: {visible[:10]}"
    )

# ── TP-UC2-003: Terms and Conditions redirect ─────────────────────────────────
def test_terms_redirect_mobile(mobile_driver):
    """Terms & Conditions link opens the legal screen; back returns to register."""
    wait = _open_register_screen(mobile_driver)
    _scroll_register_form(mobile_driver, "up")

    try:
        terms_link = wait.until(
            EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, "termsLink"))
        )
    except TimeoutException:
        terms_link = wait.until(
            EC.element_to_be_clickable(
                (
                    AppiumBy.IOS_PREDICATE,
                    'label CONTAINS[c] "Terms & Conditions" AND '
                    '(type == "XCUIElementTypeStaticText" OR type == "XCUIElementTypeLink")',
                )
            )
        )
    terms_link.click()

    _assert_terms_legal_screen(mobile_driver, wait)
    _return_to_register_screen(mobile_driver, wait)
    print("PASS: Terms & Conditions link opened legal screen and returned to Register")


# ── TP-UC2-013: Privacy Policy link redirect ──────────────────────────────────
def test_privacy_policy_redirect_mobile(mobile_driver):
    """Privacy Policy opens the same legal screen as Terms (combined page)."""
    wait = _open_register_screen(mobile_driver)
    _scroll_register_form(mobile_driver, "up")

    try:
        privacy_link = wait.until(
            EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, "privacyPolicyLink"))
        )
    except TimeoutException:
        privacy_link = wait.until(
            EC.element_to_be_clickable(
                (
                    AppiumBy.IOS_PREDICATE,
                    'label CONTAINS[c] "Privacy Policy" AND '
                    '(type == "XCUIElementTypeStaticText" OR type == "XCUIElementTypeLink")',
                )
            )
        )
    privacy_link.click()

    _assert_terms_legal_screen(mobile_driver, wait)
    _return_to_register_screen(mobile_driver, wait)
    print("PASS: Privacy Policy link opened legal screen and returned to Register")