# tests/register/test_register_web.py

import uuid

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "http://localhost:3000"
SIGNUP_URL = f"{BASE_URL}/signup"
LOGIN_URL = BASE_URL  # admin login lives at /


def _wait_for_signup_form(driver, timeout=15):
    driver.get(SIGNUP_URL)
    wait = WebDriverWait(driver, timeout)
    wait.until(EC.presence_of_element_located((By.ID, "email")))
    return wait


def _fill_signup_form(
    driver,
    *,
    name="wing teng",
    username="wingteng",
    email="wingtenglei@gmail.com",
    password="Drone4Dengue!",
    confirm_password=None,
    phone="+60123456789",
    company=None,
    accept_terms=True,
):
    if confirm_password is None:
        confirm_password = password

    driver.find_element(By.ID, "name").clear()
    driver.find_element(By.ID, "name").send_keys(name)
    driver.find_element(By.ID, "username").clear()
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "email").clear()
    driver.find_element(By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "password").clear()
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "confirmPassword").clear()
    driver.find_element(By.ID, "confirmPassword").send_keys(confirm_password)
    driver.find_element(By.ID, "phone").clear()
    driver.find_element(By.ID, "phone").send_keys(phone)

    if company:
        Select(driver.find_element(By.ID, "company")).select_by_visible_text(company)

    if accept_terms:
        driver.find_element(
            By.CSS_SELECTOR, 'button[aria-label="Accept Terms and Privacy Policy"]'
        ).click()


def _click_sign_up(driver):
    driver.find_element(
        By.XPATH, "//button[@type='submit' and contains(translate(., 'signup', 'SIGNUP'), 'SIGN UP')]"
    ).click()


# ── TP-UC2-001: Successful registration with different companies ──────────────
def test_successful_register_all_companies_web(web_driver):
    companies = [
        "Drone4Dengue Main",
        "HealthTech Solutions",
        "Public Mobile User",
        "Urban Health Monitoring",
    ]

    for company in companies:
        suffix = uuid.uuid4().hex[:8]
        wait = _wait_for_signup_form(web_driver)

        numeric_phone = f"+601{int(uuid.uuid4().hex[:8], 16) % 100000000:08d}"
        _fill_signup_form(
            web_driver,
            email=f"register.{suffix}@example.com",
            username=f"user{suffix}",
            phone=numeric_phone,
            company=company,
        )
        _click_sign_up(web_driver)

        wait.until(lambda d: d.current_url.rstrip("/") == LOGIN_URL.rstrip("/"))
        assert web_driver.current_url.rstrip("/") == LOGIN_URL.rstrip("/"), (
            f"FAIL: Not redirected to login page for company: {company}"
        )
        print(f"PASS: Registration successful for company: {company}")


# ── TP-UC2-002: Log In redirect from Register page ───────────────────────────
def test_login_redirect_from_register_web(web_driver):
    wait = _wait_for_signup_form(web_driver)

    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Login"))).click()

    wait.until(lambda d: d.current_url.rstrip("/") == LOGIN_URL.rstrip("/"))
    assert web_driver.current_url.rstrip("/") == LOGIN_URL.rstrip("/"), (
        "FAIL: Not redirected to Login page"
    )
    print("PASS: Redirected to Login page from Sign Up")


# ── TP-UC2-003: Terms and Conditions redirect ─────────────────────────────────
def test_terms_redirect_web(web_driver):
    wait = _wait_for_signup_form(web_driver)

    terms_link = wait.until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Terms and Privacy Policy"))
    )
    terms_link.click()

    wait.until(lambda d: len(d.window_handles) > 1)
    web_driver.switch_to.window(web_driver.window_handles[-1])
    wait.until(EC.url_contains("/terms"))
    assert "/terms" in web_driver.current_url, "FAIL: Not redirected to T&C page"
    print("PASS: Redirected to Terms and Conditions page")


# ── TP-UC2-004: Duplicate email ───────────────────────────────────────────────
def test_duplicate_email_web(web_driver):
    wait = _wait_for_signup_form(web_driver)

    # Pre-condition: wingtenglei@gmail.com must already exist in the database
    _fill_signup_form(
        web_driver,
        email="wingtenglei@gmail.com",
        phone="+60111111111",
        company="Urban Health Monitoring",
    )
    _click_sign_up(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'already registered')]")
        )
    )
    assert error.is_displayed(), "FAIL: Duplicate email error NOT shown"
    print("PASS: Duplicate email error displayed")


# ── TP-UC2-005: Empty Full Name ───────────────────────────────────────────────
def test_empty_fullname_web(web_driver):
    wait = _wait_for_signup_form(web_driver)

    _fill_signup_form(
        web_driver,
        name="",
        email="newuser_empty_name@example.com",
        accept_terms=True,
    )
    _click_sign_up(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'enter a name') or contains(text(),'Full Name')]")
        )
    )
    assert error.is_displayed(), "FAIL: Full Name error NOT shown"
    print("PASS: Full Name required error displayed")


# ── TP-UC2-006: Empty Email ───────────────────────────────────────────────────
def test_empty_email_web(web_driver):
    wait = _wait_for_signup_form(web_driver)

    _fill_signup_form(
        web_driver,
        email="",
        accept_terms=True,
    )
    _click_sign_up(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'valid email') or contains(text(),'Email')]")
        )
    )
    assert error.is_displayed(), "FAIL: Email error NOT shown"
    print("PASS: Email required error displayed")


# ── TP-UC2-007: Empty Password ────────────────────────────────────────────────
def test_empty_password_web(web_driver):
    wait = _wait_for_signup_form(web_driver)

    _fill_signup_form(
        web_driver,
        password="",
        confirm_password="",
        accept_terms=True,
    )
    _click_sign_up(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Password')]")
        )
    )
    assert error.is_displayed(), "FAIL: Password error NOT shown"
    print("PASS: Password required error displayed")


# ── TP-UC2-008: Password mismatch ────────────────────────────────────────────
def test_password_mismatch_web(web_driver):
    wait = _wait_for_signup_form(web_driver)

    _fill_signup_form(
        web_driver,
        confirm_password="dronedengue4!!",
        accept_terms=True,
    )
    _click_sign_up(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'do not match') or contains(text(),'mismatch')]")
        )
    )
    assert error.is_displayed(), "FAIL: Password mismatch error NOT shown"
    print("PASS: Password mismatch error displayed")


# ── TP-UC2-009: Invalid email format ─────────────────────────────────────────
def test_invalid_email_format_web(web_driver):
    wait = _wait_for_signup_form(web_driver)

    _fill_signup_form(
        web_driver,
        email="wingtengleiATgmail.com",
        accept_terms=True,
    )
    _click_sign_up(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'valid email')]")
        )
    )
    assert error.is_displayed(), "FAIL: Invalid email format error NOT shown"
    print("PASS: Invalid email format error displayed")


# ── TP-UC2-010: T&C unchecked ────────────────────────────────────────────────
def test_terms_unchecked_web(web_driver):
    wait = _wait_for_signup_form(web_driver)

    _fill_signup_form(web_driver, accept_terms=False)
    _click_sign_up(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Terms') or contains(text(),'Privacy Policy')]")
        )
    )
    assert error.is_displayed(), "FAIL: T&C error NOT shown"
    print("PASS: T&C agreement error displayed")


# ── TP-UC2-011: Invalid phone number ─────────────────────────────────────────
def test_invalid_phone_web(web_driver):
    wait = _wait_for_signup_form(web_driver)

    _fill_signup_form(
        web_driver,
        email="invalid_phone_test@example.com",
        phone="123ABC",
        accept_terms=True,
    )
    _click_sign_up(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'valid phone') or contains(text(),'phone number')]")
        )
    )
    assert error.is_displayed(), "FAIL: Invalid phone error NOT shown"
    print("PASS: Invalid phone number error displayed")


# ── TP-UC2-012: Existing phone number ────────────────────────────────────────
def test_existing_phone_web(web_driver):
    wait = _wait_for_signup_form(web_driver)

    # Pre-condition: 01159924260 must already be registered in the database
    _fill_signup_form(
        web_driver,
        email="duplicate_phone_only@example.com",
        phone="01159924260",
        company="Urban Health Monitoring",
        accept_terms=True,
    )
    _click_sign_up(web_driver)

    error = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Phone number already registered')]")
        )
    )
    assert error.is_displayed(), "FAIL: Existing phone number error NOT shown"
    print("PASS: Existing phone number error displayed")
