"""
conftest.py — Shared fixtures and helpers for UC-7 test procedures.
All test_TP_UC7_XXX.py files import from here automatically via pytest.
"""

import os
import time
import pytest

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

BASE_URL = "http://localhost:3000"

ADMIN_EMAIL    = "s@gmail.com"
ADMIN_PASSWORD = "denisetest1"

NON_ADMIN_EMAIL    = "normaluser@gmail.com"
NON_ADMIN_PASSWORD = "userpassword"

USER_ALI_EMAIL   = "ali@gmail.com"
USER_ALI_NAME    = "Ali"

USER_PENDING_EMAIL = "TestPending@gmail.com"
USER_PENDING_NAME  = "TestPending"

USER_DELETE_EMAIL  = "deleteuser@gmail.com"
USER_DELETE_NAME   = "deleteuser"

USER_UNKNOWN_EMAIL = "unknownuser@gmail.com"

USER_HEALTHTECH_USER_EMAIL  = "user@healthtech.com"
USER_HEALTHTECH_ADMIN_EMAIL = "admin@healthtech.com"

BULK_USERS_VALID = [
    {"email": "abu@gmail.com",         "role": "User"},
    {"email": "mary@drone4dengue.com", "role": "Admin"},
    {"email": "ken@yahoo.com",         "role": "User"},
]

from pathlib import Path
DOWNLOAD_DIR = str(Path.home() / "Downloads")

EXPECTED_CSV_COLUMNS = [
    "id", "userid", "name", "email", "username",
    "phone", "address", "role", "status",
    "organization", "companyid", "createdat", "updatedat",
]


# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def dismiss_alert(driver):
    try:
        driver.switch_to.alert.accept()
    except Exception:
        pass


def get_page_source(driver, timeout=15):
    """Return lowercased page source, dismissing any blocking JS alert first."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            return driver.page_source.lower()
        except Exception:
            dismiss_alert(driver)
            time.sleep(0.5)
    dismiss_alert(driver)
    try:
        return driver.page_source.lower()
    except Exception:
        return ""


def get_alert_text(driver, timeout=10):
    """If a JS alert is open, return its text and dismiss it; else return None."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            alert = driver.switch_to.alert
            txt   = alert.text
            alert.accept()
            return txt
        except Exception:
            time.sleep(0.3)
    return None


def wait_visible(driver, by, locator, timeout=20):
    """Wait until element is present in DOM and visible."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            el = driver.find_element(by, locator)
            if el.is_displayed():
                return el
        except Exception:
            pass
        time.sleep(0.5)
    raise TimeoutException(f"Element {locator!r} not visible after {timeout}s")


def wait_clickable(driver, by, locator, timeout=20):
    return WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((by, locator))
    )


def clear_and_type(element, text):
    element.clear()
    element.send_keys(text)


def go_to_user_management(driver):
    driver.get(BASE_URL + "/user-management")
    time.sleep(3)


def do_login(driver, email, password):
    wait = WebDriverWait(driver, 20)
    driver.get(BASE_URL)
    wait.until(EC.visibility_of_element_located((By.ID, "email")))
    driver.find_element(By.ID, "email").send_keys(email)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.XPATH, "//button[contains(.,'LOGIN')]").click()
    time.sleep(2)


def open_add_user_modal(driver):
    btn = wait_clickable(
        driver, By.XPATH,
        "//button[contains(.,'Add') or contains(.,'New User') or contains(.,'Invite')]"
    )
    btn.click()
    time.sleep(2)


def fill_add_user_form(driver, email="", role="User"):
    try:
        field = wait_visible(
            driver, By.XPATH,
            "//input[@type='email' or @name='email'"
            " or @placeholder[contains(.,'Email')] or @placeholder[contains(.,'email')]]"
        )
        clear_and_type(field, email)
    except Exception:
        pass
    try:
        sel = driver.find_element(
            By.XPATH, "//select[contains(@name,'role') or contains(@id,'role')]"
        )
        Select(sel).select_by_visible_text(role)
    except Exception:
        pass


def submit_add_user_form(driver):
    btn = wait_clickable(
        driver, By.XPATH,
        "//button[@type='submit' or contains(.,'Submit')"
        " or contains(.,'Create') or contains(.,'Save') or contains(.,'Invite')]"
    )
    btn.click()
    time.sleep(2)


def open_user_edit(driver, email):
    go_to_user_management(driver)
    time.sleep(2)
    btn = wait_clickable(
        driver, By.XPATH,
        f"//tr[contains(.,'{email}')]//button[@title='Edit' or contains(.,'Edit')]"
        f" | //div[contains(.,'{email}')]//button[@title='Edit' or contains(.,'Edit')]"
    )
    btn.click()
    time.sleep(2)


def change_user_role(driver, user_email, new_role):
    open_user_edit(driver, user_email)
    sel = wait_visible(
        driver, By.XPATH,
        "//select[contains(@name,'role') or contains(@id,'role')]"
    )
    Select(sel).select_by_visible_text(new_role)
    btn = wait_clickable(
        driver, By.XPATH,
        "//button[@type='submit' or contains(.,'Save') or contains(.,'Update')]"
    )
    btn.click()
    time.sleep(2)


def select_user_checkbox(driver, email):
    try:
        cb = driver.find_element(
            By.XPATH, f"//tr[contains(.,'{email}')]//input[@type='checkbox']"
        )
        if not cb.is_selected():
            cb.click()
        time.sleep(1)
    except Exception:
        pass


def click_delete_selected(driver):
    btn = wait_clickable(
        driver, By.XPATH,
        "//button[contains(.,'Delete Selected') or contains(.,'Delete') or @title='Delete']"
    )
    btn.click()
    time.sleep(2)


def get_search_input(driver):
    return wait_visible(
        driver, By.XPATH,
        "//input[@type='search'"
        " or @placeholder[contains(.,'Search')] or @placeholder[contains(.,'search')]]"
    )


def open_bulk_add(driver):
    btn = wait_clickable(
        driver, By.XPATH,
        "//button[contains(.,'Bulk') or contains(.,'Import')"
        " or contains(.,'Bulk Add') or contains(.,'Bulk Invite')]"
    )
    btn.click()
    time.sleep(2)


def fill_bulk_row(driver, index, email, role="User"):
    try:
        inputs = driver.find_elements(
            By.XPATH,
            "//input[@type='email'"
            " or @placeholder[contains(.,'Email')] or @placeholder[contains(.,'email')]]"
        )
        if index <= len(inputs):
            clear_and_type(inputs[index - 1], email)
        sels = driver.find_elements(
            By.XPATH,
            "//select[contains(@name,'role') or contains(@id,'role')"
            " or contains(@class,'role')]"
        )
        if index <= len(sels):
            Select(sels[index - 1]).select_by_visible_text(role)
    except Exception:
        pass


def click_invite_all(driver):
    btn = wait_clickable(
        driver, By.XPATH,
        "//button[contains(.,'Invite All')"
        " or contains(.,'Import All') or contains(.,'Create All')]"
    )
    btn.click()
    time.sleep(3)


# ══════════════════════════════════════════════════════════════════════════════
# PYTEST FIXTURES  (available to all test files in this folder)
# ══════════════════════════════════════════════════════════════════════════════

def _make_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_experimental_option("prefs", {
        "download.default_directory":   DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade":   True,
        "safebrowsing.enabled":         True,
    })
    return webdriver.Chrome(options=opts)


@pytest.fixture
def driver():
    """Admin-authenticated Chrome driver."""
    drv  = _make_driver()
    wait = WebDriverWait(drv, 20)
    drv.get(BASE_URL)
    wait.until(EC.visibility_of_element_located((By.ID, "email")))
    drv.find_element(By.ID, "email").send_keys(ADMIN_EMAIL)
    drv.find_element(By.ID, "password").send_keys(ADMIN_PASSWORD)
    drv.find_element(By.XPATH, "//button[contains(.,'LOGIN')]").click()
    wait.until(EC.url_contains("/dashboard"))
    yield drv
    drv.quit()


@pytest.fixture
def raw_driver():
    """Unauthenticated Chrome driver — for access-control tests."""
    drv = _make_driver()
    yield drv
    drv.quit()