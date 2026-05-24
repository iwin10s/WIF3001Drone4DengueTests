# tests/editProfile/test_edit_profile_web.py
# TP-UC4-001, 003–006, 009 — Admin Web profile settings (Settings → Profile Settings)

import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
BASE_URL = "http://localhost:3000"
LOGIN_URL = BASE_URL
SETTINGS_URL = f"{BASE_URL}/settings"

ADMIN_EMAIL = "admin@drone4dengue.com"
ADMIN_PASSWORD = "Drone4Dengue!"

VALID_NAME = "Adam bin Arbain"
VALID_USERNAME = "adamarbain"
VALID_PHONE = "+60104587140"


def _wait_for_login_form(driver, timeout=15):
    driver.get(LOGIN_URL)
    wait = WebDriverWait(driver, timeout)
    wait.until(EC.visibility_of_element_located((By.ID, "email")))
    wait.until(EC.visibility_of_element_located((By.ID, "password")))
    return wait


def _login_as_admin(driver):
    wait = _wait_for_login_form(driver)
    email = driver.find_element(By.ID, "email")
    email.clear()
    email.send_keys(ADMIN_EMAIL)
    password = driver.find_element(By.ID, "password")
    password.clear()
    password.send_keys(ADMIN_PASSWORD)
    driver.find_element(
        By.XPATH,
        "//button[@type='submit' and contains(translate(., 'login', 'LOGIN'), 'LOGIN')]",
    ).click()
    WebDriverWait(driver, 20).until(lambda d: "/dashboard" in d.current_url)


def _open_profile_settings(driver, timeout=20):
    _login_as_admin(driver)
    driver.get(SETTINGS_URL)
    wait = WebDriverWait(driver, timeout)
    wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="profileSettingsSection"]'))
    )
    return wait


def _click_edit_profile(driver):
    btn = driver.find_element(By.CSS_SELECTOR, '[data-testid="profileEditButton"]')
    btn.click()
    time.sleep(0.3)


def _set_input_value(driver, test_id, value):
    """Set value on React controlled inputs (clear() alone does not update state)."""
    el = driver.find_element(By.CSS_SELECTOR, f'[data-testid="{test_id}"]')
    driver.execute_script(
        """
        const input = arguments[0];
        const val = arguments[1];
        const setter = Object.getOwnPropertyDescriptor(
          window.HTMLInputElement.prototype, 'value'
        ).set;
        setter.call(input, val);
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        el,
        value,
    )
    return el


def _click_save_profile(driver):
    driver.find_element(By.CSS_SELECTOR, '[data-testid="profileSaveButton"]').click()
    time.sleep(0.3)


def _is_in_edit_mode(driver):
    save = driver.find_elements(By.CSS_SELECTOR, '[data-testid="profileSaveButton"]')
    return bool(save)


# ── TP-UC4-001: Successful profile save (Admin Web) ─────────────────────────
def test_successful_profile_save_web(web_driver):
    wait = _open_profile_settings(web_driver)
    _click_edit_profile(web_driver)

    _set_input_value(web_driver, "profileNameInput", VALID_NAME)
    _set_input_value(web_driver, "profileUsernameInput", VALID_USERNAME)
    _set_input_value(web_driver, "profilePhoneInput", VALID_PHONE)
    _click_save_profile(web_driver)

    success = WebDriverWait(web_driver, 25).until(
        EC.visibility_of_element_located(
            (By.CSS_SELECTOR, '[data-testid="profileSuccessMessage"]')
        )
    )
    assert "Profile updated successfully!" in success.text
    assert not _is_in_edit_mode(web_driver), "FAIL: Still in edit mode after successful save"
    print("PASS: Admin profile saved with success message (TP-UC4-001)")


# ── TP-UC4-003: Email and Company disabled in edit mode ─────────────────────
def test_email_and_company_disabled_web(web_driver):
    _open_profile_settings(web_driver)
    _click_edit_profile(web_driver)

    email = web_driver.find_element(By.CSS_SELECTOR, '[data-testid="profileEmailInput"]')
    company = web_driver.find_element(By.CSS_SELECTOR, '[data-testid="profileCompanyInput"]')
    assert email.get_attribute("disabled") is not None, "FAIL: Email field should be disabled"
    assert company.get_attribute("disabled") is not None, "FAIL: Company field should be disabled"

    original_email = email.get_attribute("value") or ""
    original_company = company.get_attribute("value") or ""

    try:
        email.click()
        email.send_keys("hacker@evil.com")
    except Exception:
        pass
    try:
        company.click()
        company.send_keys("Evil Corp")
    except Exception:
        pass

    assert (email.get_attribute("value") or "") == original_email, (
        "FAIL: Email value changed while disabled"
    )
    assert (company.get_attribute("value") or "") == original_company, (
        "FAIL: Company value changed while disabled"
    )
    print("PASS: Email and Company fields remain disabled (TP-UC4-003)")


# ── TP-UC4-004: Empty name validation ───────────────────────────────────────
def test_empty_name_validation_web(web_driver):
    _open_profile_settings(web_driver)
    _click_edit_profile(web_driver)

    _set_input_value(web_driver, "profileNameInput", "")
    _set_input_value(web_driver, "profileUsernameInput", VALID_USERNAME)
    _set_input_value(web_driver, "profilePhoneInput", VALID_PHONE)
    _click_save_profile(web_driver)

    error = WebDriverWait(web_driver, 15).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="profileNameError"]'))
    )
    assert "Please fill out this field" in error.text
    assert _is_in_edit_mode(web_driver), "FAIL: Left edit mode despite validation error"
    print("PASS: Empty name shows field error and blocks save (TP-UC4-004)")


# ── TP-UC4-005: Empty username validation ────────────────────────────────────
def test_empty_username_validation_web(web_driver):
    _open_profile_settings(web_driver)
    _click_edit_profile(web_driver)

    _set_input_value(web_driver, "profileNameInput", VALID_NAME)
    _set_input_value(web_driver, "profileUsernameInput", "")
    _set_input_value(web_driver, "profilePhoneInput", VALID_PHONE)
    _click_save_profile(web_driver)

    error = WebDriverWait(web_driver, 15).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="profileUsernameError"]'))
    )
    assert "Please fill out this field" in error.text
    assert _is_in_edit_mode(web_driver), "FAIL: Left edit mode despite validation error"
    print("PASS: Empty username shows field error and blocks save (TP-UC4-005)")


# ── TP-UC4-006: Invalid phone format ────────────────────────────────────────
def test_invalid_phone_format_web(web_driver):
    _open_profile_settings(web_driver)
    _click_edit_profile(web_driver)

    _set_input_value(web_driver, "profileNameInput", VALID_NAME)
    _set_input_value(web_driver, "profileUsernameInput", VALID_USERNAME)
    _set_input_value(web_driver, "profilePhoneInput", "123ABC")
    _click_save_profile(web_driver)

    error = WebDriverWait(web_driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="profilePhoneError"]'))
    )
    assert "Invalid number format." in error.text
    assert _is_in_edit_mode(web_driver), "FAIL: Left edit mode despite phone validation error"
    print("PASS: Invalid phone shows format error and blocks save (TP-UC4-006)")


# ── TP-UC4-009: Cancel discards changes ─────────────────────────────────────
def test_cancel_discards_changes_web(web_driver):
    wait = _open_profile_settings(web_driver)
    original_name = wait.until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-testid="profileNameInput"]'))
    ).get_attribute("value")

    _click_edit_profile(web_driver)
    _set_input_value(web_driver, "profileNameInput", "Test Name")
    web_driver.find_element(By.CSS_SELECTOR, '[data-testid="profileEditButton"]').click()

    name_after = web_driver.find_element(By.CSS_SELECTOR, '[data-testid="profileNameInput"]')
    assert not _is_in_edit_mode(web_driver), "FAIL: Still in edit mode after Cancel"
    assert (name_after.get_attribute("value") or "") == (original_name or ""), (
        "FAIL: Name was not reverted after Cancel"
    )
    success = web_driver.find_elements(By.CSS_SELECTOR, '[data-testid="profileSuccessMessage"]')
    assert not success, "FAIL: Success message shown after Cancel"
    print("PASS: Cancel reverts name and exits edit mode (TP-UC4-009)")
