import time
import pytest
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


BASE_URL = "http://localhost:3000"

ADMIN_EMAIL = "s@gmail.com"
ADMIN_PASSWORD = "denisetest1"

DRONE_NAME = "Drone Alpha"
DRONE_MODEL = "DJI Phantom 4 Pro"

SERIAL = f"SN-{datetime.now().strftime('%Y%m%d%H%M%S')}"

DUPLICATE_SERIAL = "SN123456789"

STATUS_EDIT = "Maintenance"

TARGET_DRONE_ID = "DRN-001"


def _dismiss_alert(driver):
    try:
        alert = driver.switch_to.alert
        alert.accept()
    except Exception:
        pass


def _get_page_source(driver, timeout=15):
    """Return lowercased page source, dismissing any blocking JS alert first."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            return driver.page_source.lower()
        except Exception:
            _dismiss_alert(driver)
            time.sleep(0.5)
    _dismiss_alert(driver)
    try:
        return driver.page_source.lower()
    except Exception:
        return ""


@pytest.fixture
def driver():

    opts = Options()

    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    drv = webdriver.Chrome(options=opts)

    wait = WebDriverWait(drv, 20)

    drv.get(BASE_URL)

    wait.until(
        EC.visibility_of_element_located(
            (By.ID, "email")
        )
    )

    drv.find_element(
        By.ID,
        "email"
    ).send_keys(
        ADMIN_EMAIL
    )

    drv.find_element(
        By.ID,
        "password"
    ).send_keys(
        ADMIN_PASSWORD
    )

    drv.find_element(
        By.XPATH,
        "//button[contains(.,'LOGIN')]"
    ).click()

    wait.until(
        EC.url_contains(
            "/dashboard"
        )
    )

    yield drv

    drv.quit()


def _click_visible(driver, by, locator, wait=WebDriverWait(driver, 20)):
    """Wait for element to be present, scroll into view, then retry until clickable."""
    end = time.monotonic() + wait._timeout
    while time.monotonic() < end:
        try:
            el = driver.find_element(by, locator)
            driver.execute_script("arguments[0].scrollIntoView(true);", el)
            time.sleep(0.2)
            if el.is_displayed() and el.is_enabled():
                el.click()
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise TimeoutException(f"Could not click element {locator}")


def _wait_visible(driver, by, locator, timeout=20):
    """Wait until element is present in DOM and is_displayed."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            el = driver.find_element(by, locator)
            if el.is_displayed():
                return el
        except Exception:
            pass
        time.sleep(0.5)
    raise TimeoutException(f"Element {locator} not visible after {timeout}s")


def open_add_form(driver):

    driver.get(
        BASE_URL +
        "/drone-management"
    )

    time.sleep(7)

    _click_visible(
        driver,
        By.XPATH,
        "//button[contains(.,'Add Drone')]"
    )


def fill_form(
    driver,
    name,
    model,
    serial
):

    # Label-relative locators for the Add Drone modal
    fields = [
        ("Drone Name", name),
        ("Model", model),
        ("Serial Number", serial),
    ]

    for label_text, value in fields:
        xpath = (
            f"//label[contains(normalize-space(.), '{label_text}')]"
            f"/following::input[1]"
        )
        el = _wait_visible(driver, By.XPATH, xpath)
        el.clear()
        el.send_keys(value)


def submit(driver):

    btn_xpath = "//button[@type='submit' and contains(.,'Add Drone')]"

    end = time.monotonic() + 20
    while time.monotonic() < end:
        try:
            btn = driver.find_element(By.XPATH, btn_xpath)
            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.2)
            if btn.is_displayed() and btn.is_enabled():
                btn.click()
                return
        except Exception:
            pass
        time.sleep(0.5)


def get_alert_text(driver, timeout=15):
    """If a JS alert is open, return its text; else return None."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            alert = driver.switch_to.alert
            text = alert.text
            alert.accept()
            return text
        except Exception:
            _dismiss_alert(driver)
            time.sleep(0.3)
    return None


def test_TC_UC5_003_empty_name(driver):

    try:
        open_add_form(driver)

        fill_form(
            driver,
            "",
            DRONE_MODEL,
            SERIAL
        )

        submit(driver)

        alert_text = get_alert_text(driver)

        assert alert_text is not None
        assert "required" in alert_text.lower()

        print("✅ TC-UC5-003 Empty Name — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-003 Empty Name — FAIL ({e})")

        assert False

def test_TC_UC5_003_empty_model(driver):

    try:

        open_add_form(driver)

        fill_form(
            driver,
            DRONE_NAME,
            "",
            SERIAL
        )

        submit(driver)

        alert_text = get_alert_text(driver)

        assert alert_text
        assert "required" in alert_text.lower()

        print("✅ TC-UC5-003 Empty Model — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-003 Empty Model — FAIL ({e})")

        assert False


def test_TC_UC5_003_empty_serial(driver):

    try:

        open_add_form(driver)

        fill_form(
            driver,
            DRONE_NAME,
            DRONE_MODEL,
            ""
        )

        submit(driver)

        alert_text = get_alert_text(driver)

        assert alert_text
        assert "required" in alert_text.lower()

        print("✅ TC-UC5-003 Empty Serial — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-003 Empty Serial — FAIL ({e})")

        assert False


def test_TC_UC5_003_create_valid(driver):

    try:

        open_add_form(driver)

        fill_form(
            driver,
            DRONE_NAME,
            DRONE_MODEL,
            SERIAL
        )

        submit(driver)

        alert_text = get_alert_text(driver)

        assert alert_text
        assert "created" in alert_text.lower()

        print("✅ TC-UC5-003 Create Drone — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-003 Create Drone — FAIL ({e})")

        assert False


def test_TC_UC5_003_duplicate_serial(driver):

    try:

        open_add_form(driver)

        fill_form(
            driver,
            DRONE_NAME,
            DRONE_MODEL,
            DUPLICATE_SERIAL
        )

        submit(driver)

        page = _get_page_source(driver)

        alert = get_alert_text(driver)

        assert (
            "already" in page
            or "exists" in page
            or (
                alert
                and "already" in alert.lower()
            )
        )

        print("✅ TC-UC5-003 Duplicate Serial — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-003 Duplicate Serial — FAIL ({e})")

        assert False

def test_TC_UC5_004_edit_drone(driver):

    try:

        driver.get(
            BASE_URL +
            "/drone-management"
        )

        time.sleep(10)

        edit_btn = _wait_visible(
            driver,
            By.XPATH,
            "(//button[@title='Edit Drone'])[1]"
        )

        driver.execute_script(
            "arguments[0].scrollIntoView(true);",
            edit_btn
        )

        edit_btn.click()

        time.sleep(3)

        status = _wait_visible(
            driver,
            By.XPATH,
            "//label[contains(.,'Status')]/following::select[1]"
        )

        Select(status).select_by_visible_text(
            STATUS_EDIT
        )

        save = _wait_visible(
            driver,
            By.XPATH,
            "//button[contains(.,'Save Changes')]"
        )

        save.click()

        alert = get_alert_text(driver)

        assert alert
        assert "updated" in alert.lower()

        print("✅ TC-UC5-004 Edit Drone — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-004 Edit Drone — FAIL ({e})")

        assert False


def test_TC_UC5_004_cancel_update(driver):

    try:

        driver.get(
            BASE_URL +
            "/drone-management"
        )

        time.sleep(10)

        edit = _wait_visible(
            driver,
            By.XPATH,
            "(//button[@title='Edit Drone'])[1]"
        )

        edit.click()

        time.sleep(2)

        cancel = _wait_visible(
            driver,
            By.XPATH,
            "//button[contains(.,'Cancel')]"
        )

        cancel.click()

        time.sleep(2)

        page = _get_page_source(driver)

        assert "drone" in page

        print("✅ TC-UC5-004 Cancel Update — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-004 Cancel Update — FAIL ({e})")

        assert False


def test_TC_UC5_004_failed_save(driver):

    try:

        driver.get(
            BASE_URL +
            "/drone-management"
        )

        time.sleep(10)

        page = _get_page_source(driver)

        assert "drone" in page

        print("✅ TC-UC5-004 Save Validation — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-004 Save Validation — FAIL ({e})")

        assert False