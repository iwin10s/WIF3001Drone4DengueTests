# tests/editProfile/test_edit_profile_mobile.py
# TP-UC4-002, 007–008, 010–012 — Mobile App edit profile
#
# Navigation (matches manual testing):
#   Login → Dashboard → Profile tab → My Account → Edit Profile

import time

import conftest
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from tests.mobile_helpers import accept_medical_disclaimer_if_shown

MOBILE_EMAIL = "wingtenglei@gmail.com"
MOBILE_PASSWORD = "Drone4Dengue!"
EXPO_DEV_URL = conftest.EXPO_DEV_URL

VALID_NAME = "Adam bin Arbain"
VALID_USERNAME = "adamarbain2107"
VALID_ADDRESS = "Kuala Lumpur"


def _unique_test_phone():
    """Phone must be unique in DB (@unique); reuse a stable suffix per run."""
    suffix = int(time.time()) % 10_000_000
    return f"+6012{suffix:07d}"


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


def _set_input_text(driver, element, value):
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


def _hide_keyboard(driver):
    try:
        driver.hide_keyboard()
    except Exception:
        pass


def _login_mobile(driver, timeout=45):
    """Log in and land on the dashboard (home tab)."""
    wait = WebDriverWait(driver, timeout)
    accept_medical_disclaimer_if_shown(driver)
    _deep_link(driver, "/--/(auth)/login")
    accept_medical_disclaimer_if_shown(driver)
    wait.until(EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "loginScreen")))

    _set_input_text(
        driver, driver.find_element(AppiumBy.ACCESSIBILITY_ID, "email"), MOBILE_EMAIL
    )
    _set_input_text(
        driver,
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, "password"),
        MOBILE_PASSWORD,
    )
    _hide_keyboard(driver)
    _tap_element(driver, driver.find_element(AppiumBy.ACCESSIBILITY_ID, "loginButton"))

    try:
        wait.until(EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "homeTab")))
    except TimeoutException:
        wait.until(
            EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "dashboardScreen"))
        )
    wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "bottomNavBar"))
    )
    time.sleep(0.8)
    return wait


def _scroll_profile_list(driver, direction="up"):
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


def _scroll_edit_profile_form(driver, direction="up"):
    """Scroll the edit-profile ScrollView (address is below phone)."""
    size = driver.get_window_size()
    driver.execute_script(
        "mobile: swipe",
        {
            "direction": direction,
            "left": size["width"] // 2,
            "top": int(size["height"] * 0.45),
            "width": 1,
            "height": int(size["height"] * 0.35),
        },
    )
    time.sleep(0.35)


def _field_in_tappable_band(driver, element):
    """True when the field is not hidden under the keyboard or bottom nav."""
    try:
        loc = element.location
        y = loc["y"]
        h = driver.get_window_size()["height"]
        return int(h * 0.12) < y < int(h * 0.72)
    except Exception:
        return False


def _find_profile_field(driver, test_id, *, scroll_direction="up", scroll_first=False):
    """Locate a profile input and scroll until it is on screen."""
    if scroll_first:
        _scroll_edit_profile_form(driver, scroll_direction)

    for _ in range(6):
        for el in driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id):
            if _field_in_tappable_band(driver, el):
                return el
        _scroll_edit_profile_form(driver, scroll_direction)

    return WebDriverWait(driver, 12).until(
        EC.visibility_of_element_located((AppiumBy.ACCESSIBILITY_ID, test_id))
    )


def _commit_field_focus(driver):
    """Blur the active field so React Native onChangeText commits state."""
    _hide_keyboard(driver)
    try:
        header = driver.find_element(
            AppiumBy.IOS_PREDICATE,
            'label == "Edit Profile" OR name == "Edit Profile"',
        )
        _tap_element(driver, header)
    except Exception:
        pass
    time.sleep(0.25)


def _set_profile_field(driver, test_id, value, *, multiline=False, scroll_direction="up"):
    """Fill RN TextInputs; mobile:type updates React state on iOS (send_keys often does not)."""
    _hide_keyboard(driver)
    time.sleep(0.2)
    scroll_first = test_id in ("profileAddressInput", "profilePhoneInput")
    element = _find_profile_field(
        driver,
        test_id,
        scroll_direction=scroll_direction,
        scroll_first=scroll_first,
    )
    _tap_element(driver, element)
    time.sleep(0.35)
    try:
        driver.execute_script("mobile: clearText", {"element": element})
    except Exception:
        try:
            element.clear()
        except Exception:
            pass
    if value:
        try:
            driver.execute_script("mobile: type", {"element": element, "text": value})
        except Exception:
            try:
                element.send_keys(value)
            except Exception:
                element.set_value(value)
    else:
        try:
            element.send_keys("\b")
        except Exception:
            pass
    time.sleep(0.35)
    _commit_field_focus(driver)
    if multiline:
        _hide_keyboard(driver)


def _scroll_until_clickable(driver, test_id, *, scroll_direction="up", max_swipes=6):
    for _ in range(max_swipes):
        for el in driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id):
            try:
                if el.is_displayed() and el.is_enabled():
                    if _field_in_tappable_band(driver, el):
                        return el
            except Exception:
                continue
        _scroll_edit_profile_form(driver, scroll_direction)
    return WebDriverWait(driver, 12).until(
        EC.element_to_be_clickable((AppiumBy.ACCESSIBILITY_ID, test_id))
    )


def _read_profile_field(driver, test_id):
    return _element_text(
        driver.find_element(AppiumBy.ACCESSIBILITY_ID, test_id)
    ).strip()


def _tap_bottom_nav_profile(driver, wait, timeout=20):
    """Tap Profile on the bottom navigation bar (4th tab)."""
    nav_wait = WebDriverWait(driver, timeout)
    nav_wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "bottomNavBar"))
    )
    time.sleep(0.5)

    locators = (
        (AppiumBy.ACCESSIBILITY_ID, "profileTab"),
        (AppiumBy.ACCESSIBILITY_ID, "Profile"),
        (
            AppiumBy.IOS_PREDICATE,
            'type == "XCUIElementTypeButton" AND label == "Profile"',
        ),
        (
            AppiumBy.IOS_PREDICATE,
            'type == "XCUIElementTypeButton" AND name == "Profile"',
        ),
        (
            AppiumBy.IOS_PREDICATE,
            'label == "Profile" AND (type == "XCUIElementTypeButton" OR type == "XCUIElementTypeOther")',
        ),
    )
    for locator in locators:
        try:
            tab = nav_wait.until(EC.element_to_be_clickable(locator))
            _tap_element(driver, tab)
            return
        except TimeoutException:
            continue

    # Fallback: Profile is the rightmost of four bottom tabs
    size = driver.get_window_size()
    driver.execute_script(
        "mobile: tap",
        {"x": int(size["width"] * 0.88), "y": int(size["height"] * 0.93)},
    )


def _go_to_profile_screen(driver, wait, timeout=25):
    """Bottom nav Profile → Profile screen."""
    _tap_bottom_nav_profile(driver, wait, timeout=timeout)
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "profileScreen"))
    )


def _tap_my_account(driver, wait, timeout=20):
    """My Account row on Profile → Edit Profile screen."""
    nav_wait = WebDriverWait(driver, timeout)
    _scroll_profile_list(driver, "up")

    locators = (
        (AppiumBy.ACCESSIBILITY_ID, "myAccountLink"),
        (AppiumBy.ACCESSIBILITY_ID, "editProfileLink"),
        (AppiumBy.ACCESSIBILITY_ID, "My Account"),
        (
            AppiumBy.IOS_PREDICATE,
            'type == "XCUIElementTypeButton" AND label == "My Account"',
        ),
        (
            AppiumBy.IOS_PREDICATE,
            'label CONTAINS[c] "My Account"',
        ),
    )
    for locator in locators:
        try:
            row = nav_wait.until(EC.element_to_be_clickable(locator))
            _tap_element(driver, row)
            break
        except TimeoutException:
            continue
    else:
        raise TimeoutException("Could not find My Account on Profile screen")

    wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "editProfileScreen"))
    )


def _open_edit_profile(driver, timeout=25):
    """Login → Profile tab → My Account → Edit Profile (matches manual flow)."""
    wait = _login_mobile(driver, timeout=45)
    _go_to_profile_screen(driver, wait)
    _tap_my_account(driver, wait)
    return wait


def _fill_profile(driver, *, name=None, username=None, phone=None, address=None):
    if name is not None:
        _set_profile_field(driver, "profileFullNameInput", name)
    if username is not None:
        _set_profile_field(driver, "profileUsernameInput", username)
    if phone is not None:
        _set_profile_field(driver, "profilePhoneInput", phone, scroll_direction="up")
    if address is not None:
        _set_profile_field(
            driver, "profileAddressInput", address, multiline=True, scroll_direction="up"
        )


def _tap_save_changes(driver):
    _hide_keyboard(driver)
    _commit_field_focus(driver)
    save_btn = _scroll_until_clickable(driver, "profileSaveButton", scroll_direction="up")
    _tap_element(driver, save_btn)
    time.sleep(0.6)


def _tap_confirm_save(driver):
    confirm = _scroll_until_clickable(
        driver, "profileConfirmSaveButton", scroll_direction="up"
    )
    _tap_element(driver, confirm)
    time.sleep(0.5)


def _wait_for_confirm_modal(driver, timeout=10):
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "profileConfirmModal"))
    )


def _alert_message_text(driver):
    for test_id in ("profileAlertMessage",):
        for el in driver.find_elements(AppiumBy.ACCESSIBILITY_ID, test_id):
            text = _element_text(el).strip()
            if text:
                return text
    for pred in (
        'type == "XCUIElementTypeStaticText" AND label CONTAINS[c] "profile"',
        'type == "XCUIElementTypeStaticText" AND label CONTAINS[c] "required"',
        'type == "XCUIElementTypeStaticText" AND label CONTAINS[c] "Failed"',
    ):
        for el in driver.find_elements(AppiumBy.IOS_PREDICATE, pred):
            text = _element_text(el).strip()
            if text:
                return text
    return ""


def _wait_for_alert_message(driver, fragment, timeout=25):
    deadline = time.time() + timeout
    last_text = ""
    while time.time() < deadline:
        last_text = _alert_message_text(driver)
        if fragment.lower() in last_text.lower():
            return last_text
        if _page_contains(driver, fragment):
            return fragment
        if driver.find_elements(AppiumBy.ACCESSIBILITY_ID, "profileAlertOkButton"):
            if last_text:
                break
        time.sleep(0.35)
    raise TimeoutException(
        f"Alert message containing {fragment!r} not found"
        + (f" (last alert text: {last_text!r})" if last_text else "")
    )


def _confirm_modal_visible(driver):
    return bool(
        driver.find_elements(AppiumBy.ACCESSIBILITY_ID, "profileConfirmModal")
    )


# ── TP-UC4-002: Successful profile save (Mobile) ──────────────────────────────
def test_successful_profile_save_mobile(mobile_driver):
    wait = _open_edit_profile(mobile_driver)
    WebDriverWait(mobile_driver, 15).until(
        lambda d: _read_profile_field(d, "profileFullNameInput")
    )
    # Keep the account username; only change fields that are safe to overwrite in E2E.
    current_username = _read_profile_field(mobile_driver, "profileUsernameInput")

    test_phone = _unique_test_phone()
    _fill_profile(
        mobile_driver,
        name=VALID_NAME,
        username=current_username or VALID_USERNAME,
        phone=test_phone,
        address=VALID_ADDRESS,
    )
    _tap_save_changes(mobile_driver)
    _wait_for_confirm_modal(mobile_driver)
    _tap_confirm_save(mobile_driver)

    _wait_for_alert_message(mobile_driver, "Profile updated successfully!")
    _tap_element(
        mobile_driver,
        mobile_driver.find_element(AppiumBy.ACCESSIBILITY_ID, "profileAlertOkButton"),
    )

    wait.until(EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "profileScreen")))
    print("PASS: Mobile profile saved with confirmation and success modal (TP-UC4-002)")


# ── TP-UC4-007: Empty full name error ───────────────────────────────────────
def test_empty_full_name_mobile(mobile_driver):
    _open_edit_profile(mobile_driver)
    _fill_profile(mobile_driver, name="", username=VALID_USERNAME)
    _tap_save_changes(mobile_driver)

    _wait_for_alert_message(mobile_driver, "Full name is required")
    assert not _confirm_modal_visible(mobile_driver), (
        "FAIL: Confirmation modal appeared for empty full name"
    )
    print("PASS: Empty full name shows error modal, no confirm (TP-UC4-007)")


# ── TP-UC4-008: Empty username error ─────────────────────────────────────────
def test_empty_username_mobile(mobile_driver):
    _open_edit_profile(mobile_driver)
    _fill_profile(mobile_driver, name=VALID_NAME, username="")
    _tap_save_changes(mobile_driver)

    _wait_for_alert_message(mobile_driver, "Username is required")
    assert not _confirm_modal_visible(mobile_driver), (
        "FAIL: Confirmation modal appeared for empty username"
    )
    print("PASS: Empty username shows error modal, no confirm (TP-UC4-008)")


# ── TP-UC4-010: Cancel navigates back without saving ─────────────────────────
def test_cancel_navigates_back_mobile(mobile_driver):
    wait = _open_edit_profile(mobile_driver)
    original = _element_text(
        mobile_driver.find_element(AppiumBy.ACCESSIBILITY_ID, "profileFullNameInput")
    )

    _fill_profile(mobile_driver, name="Test Name")
    _tap_element(
        mobile_driver,
        mobile_driver.find_element(AppiumBy.ACCESSIBILITY_ID, "profileCancelButton"),
    )

    wait.until(EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "profileScreen")))

    _tap_my_account(mobile_driver, wait)

    name_now = _element_text(
        mobile_driver.find_element(AppiumBy.ACCESSIBILITY_ID, "profileFullNameInput")
    )
    assert name_now == original, (
        f"FAIL: Name changed after Cancel (was {original!r}, now {name_now!r})"
    )
    print("PASS: Cancel returns to profile without saving (TP-UC4-010)")


# ── TP-UC4-011: Confirmation modal before save ──────────────────────────────
def test_confirmation_modal_before_save_mobile(mobile_driver):
    _open_edit_profile(mobile_driver)
    _fill_profile(
        mobile_driver,
        name=VALID_NAME,
        username=VALID_USERNAME,
        phone=_unique_test_phone(),
    )
    _tap_save_changes(mobile_driver)

    WebDriverWait(mobile_driver, 10).until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "profileConfirmTitle"))
    )
    msg = mobile_driver.find_element(AppiumBy.ACCESSIBILITY_ID, "profileConfirmMessage")
    assert "update your profile" in _element_text(msg).lower()

    assert mobile_driver.find_elements(
        AppiumBy.ACCESSIBILITY_ID, "profileConfirmCancelButton"
    ), "FAIL: Confirm modal Cancel not visible"
    assert mobile_driver.find_elements(
        AppiumBy.ACCESSIBILITY_ID, "profileConfirmSaveButton"
    ), "FAIL: Confirm modal Confirm not visible"

    _tap_element(
        mobile_driver,
        mobile_driver.find_element(AppiumBy.ACCESSIBILITY_ID, "profileConfirmCancelButton"),
    )
    print("PASS: Confirmation modal shown with Cancel and Confirm (TP-UC4-011)")


# ── TP-UC4-012: Dismiss confirmation cancels save ───────────────────────────
def test_dismiss_confirmation_cancels_save_mobile(mobile_driver):
    wait = _open_edit_profile(mobile_driver)
    original = _element_text(
        mobile_driver.find_element(AppiumBy.ACCESSIBILITY_ID, "profileFullNameInput")
    )

    _fill_profile(
        mobile_driver,
        name=VALID_NAME,
        username=VALID_USERNAME,
        phone=_unique_test_phone(),
    )
    _tap_save_changes(mobile_driver)
    _wait_for_confirm_modal(mobile_driver)

    cancel = _scroll_until_clickable(
        mobile_driver, "profileConfirmCancelButton", scroll_direction="up"
    )
    _tap_element(mobile_driver, cancel)
    time.sleep(0.5)

    assert not _confirm_modal_visible(mobile_driver), "FAIL: Confirm modal still visible"
    wait.until(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "editProfileScreen"))
    )

    _tap_element(
        mobile_driver,
        mobile_driver.find_element(AppiumBy.ACCESSIBILITY_ID, "profileCancelButton"),
    )
    wait.until(EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "profileScreen")))
    _tap_my_account(mobile_driver, wait)

    name_now = _element_text(
        mobile_driver.find_element(AppiumBy.ACCESSIBILITY_ID, "profileFullNameInput")
    )
    assert name_now == original, "FAIL: Profile changed after dismissing confirmation"
    print("PASS: Dismissing confirm modal cancels save (TP-UC4-012)")
