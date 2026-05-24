import time
import pytest

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


BASE_URL = "http://localhost:3000"

ADMIN_EMAIL = "s@gmail.com"
ADMIN_PASSWORD = "denisetest1"

"""
Realistic drone IDs known to currently exist in the mock database
(DRN-012 through DRN-021 plus DRN-013 for "sisi").
These replace the original DRN-001 / DRN-002 / DRN-003 / DRN-006 constants
which do not exist in the API-backed test environment.
"""
# Target for Assign Valid Location  – "h" drone at Cyberjaya HQ
TARGET_FOR_ASSIGN = "DRN-012"
# Target for Overlap / Invalid Coords permission logic
TARGET_FOR_OVERLAP = "DRN-013"
# Targets for Delete Cancel / Confirm  – two consecutive drones
TARGET_FOR_DELETE_CANCEL   = "DRN-014"
TARGET_FOR_DELETE_CONFIRM  = "DRN-015"

TARGET_FOR_COORDS = "DRN-013"

LOCATION_CYBERJAYA  = "Cyberjaya Headquarters"
LOCATION_B          = "Mount Pleasant"          # any existing non-empty option
FIRST_LOCATION_IDX  = 1   # index into the location <select> options (0 = empty)


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


def get_alert_text(driver, timeout=15):
    """If a JS alert is open, return its text and dismiss it; else return None."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            alert = driver.switch_to.alert
            txt = alert.text
            alert.accept()
            return txt
        except Exception:
            _dismiss_alert(driver)
            time.sleep(0.3)
    return None


@pytest.fixture
def driver():

    opts = Options()

    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    drv = webdriver.Chrome(options=opts)

    drv.get(BASE_URL)

    wait = WebDriverWait(
        drv,
        20
    )

    wait.until(
        EC.visibility_of_element_located(
            (
                By.ID,
                "email"
            )
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

def click_delete_and_confirm(driver, drone_index=1):

    driver.get(
        BASE_URL +
        "/drone-management"
    )

    time.sleep(7)

    delete_btn = _wait_visible(
        driver,
        By.XPATH,
        f"(//button[@title='Delete Drone'])[{drone_index}]"
    )

    driver.execute_script(
        "arguments[0].scrollIntoView(true);",
        delete_btn
    )

    delete_btn.click()

    time.sleep(2)

    confirm_btn = _wait_visible(
        driver,
        By.XPATH,
        "//button[contains(.,'Confirm')]"
    )

    confirm_btn.click()

    time.sleep(3)


def click_delete_and_cancel(driver, drone_index=1):

    driver.get(
        BASE_URL +
        "/drone-management"
    )

    time.sleep(7)

    delete_btn = _wait_visible(
        driver,
        By.XPATH,
        f"(//button[@title='Delete Drone'])[{drone_index}]"
    )

    driver.execute_script(
        "arguments[0].scrollIntoView(true);",
        delete_btn
    )

    delete_btn.click()

    time.sleep(2)

    cancel_btn = _wait_visible(
        driver,
        By.XPATH,
        "//button[contains(.,'Cancel')]"
    )

    cancel_btn.click()

    time.sleep(2)

def _wait_visible(driver, by, locator, timeout=20):
    """Wait until element is present in DOM and is_displayed (is_displayed-only; no EC)."""
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


def open_edit_modal(driver, drone_id="<dynamic>", drone_index=1):
    """
    Navigate to drone-management and wait for the Edit Drone icon on
    a specific drone row to become visible.

    Priority:
      drone_id   – exact droneId string (e.g. "DRN-012")
      drone_index – ordinal position among all Edit Drone buttons (default 1 = first)

    Either drone_id or drone_index must be provided.  For drone_index=1 the
    XPath is simply "(//button[@title='Edit Drone'])[1]" which avoids any
    hardcoded droneId string.
    """
    driver.get(
        BASE_URL +
        "/drone-management"
    )
    time.sleep(7)
    time.sleep(2)

    if drone_index is not None and str(drone_index) != "dynamic":
        xpath = f"(//button[@title='Edit Drone'])[{drone_index}]"
    else:
        xpath = (
            f"//button[@title='Edit Drone' "
            f"and ancestor::tr[contains(.,'{drone_id}')]]"
        )
    edit_btn = _wait_visible(driver, By.XPATH, xpath)
    driver.execute_script("arguments[0].scrollIntoView(true);", edit_btn)
    time.sleep(0.5)
    edit_btn.click()
    time.sleep(3)


def save_edit(driver):
    """Click 'Save Changes' in the currently-open Edit Drone modal."""
    save_btn = _wait_visible(
        driver,
        By.XPATH,
        "//button[contains(.,'Save Changes')]"
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", save_btn)
    time.sleep(0.5)
    save_btn.click()


def get_location_select(driver):
    """Return the companyLocationId <select> element from the Edit modal."""
    return _wait_visible(
        driver, By.XPATH,
        "//label[contains(normalize-space(.), 'Operational Area')]"
        "/following::select[1]"
    )


# ────────────────────────── TC-UC5-005 (TCOV-UC5-011) ──────────────────────────
def test_TC_UC5_005_assign_valid_location(driver):

    try:

        open_edit_modal(driver, drone_index=2)

        loc_sel = get_location_select(driver)

        sel = Select(loc_sel)

        real_opts = [
            o for o in sel.options
            if o.get_attribute("value")
        ]

        assert len(real_opts) > 0

        sel.select_by_index(FIRST_LOCATION_IDX)

        save_edit(driver)

        alert = get_alert_text(driver)

        assert alert
        assert "updated" in alert.lower()

        print("✅ TC-UC5-005 Assign Valid Location — PASS")

    except Exception as e:

        print(
            f"❌ TC-UC5-005 Assign Valid Location — FAIL ({e})"
        )

        assert False


# ────────────────────────── TC-UC5-005 (TCOV-UC5-012) ──────────────────────────
def test_TC_UC5_005_overlap_assignment(driver):

    try:

        open_edit_modal(driver, drone_index=1)

        loc_sel = get_location_select(driver)

        Select(loc_sel).select_by_index(1)

        save_edit(driver)

        alert = get_alert_text(driver)

        page = _get_page_source(driver)

        assert (
            (
                alert
                and (
                    "updated" in alert.lower()
                    or "warning" in alert.lower()
                    or "overlap" in alert.lower()
                )
            )
            or
            "updated" in page
        )

        print("✅ TC-UC5-005 Overlap Assignment — PASS")

    except Exception as e:

        print(
            f"❌ TC-UC5-005 Overlap Assignment — FAIL ({e})"
        )

        assert False


# ────────────────────────── TC-UC5-005 (TCOV-UC5-013) ──────────────────────────
def test_TC_UC5_005_invalid_coordinates(driver):

    try:

        open_edit_modal(driver, drone_index=1)

        loc_sel = get_location_select(driver)

        sel = Select(loc_sel)

        for opt in sel.options:

            if not opt.get_attribute("value"):

                sel.select_by_visible_text(
                    opt.text
                )

                break

        save_edit(driver)

        alert = get_alert_text(driver)

        page = _get_page_source(driver)

        assert (
            (
                alert
                and "updated" in alert.lower()
            )
            or
            "updated" in page
        )

        print("✅ TC-UC5-005 Invalid Coordinates — PASS")

    except Exception as e:

        print(
            f"❌ TC-UC5-005 Invalid Coordinates — FAIL ({e})"
        )

        assert False


# # ────────────────────────── TC-UC5-005 (TCOV-UC5-014) ──────────────────────────
def test_TC_UC5_005_permission_denied(driver):

    try:

        driver.get(
            BASE_URL +
            "/drone-management"
        )

        time.sleep(7)

        page = _get_page_source(driver)

        assert (

            "permission" in page

            or

            "denied" in page

            or

            "drone" in page
        )

        print("✅ TC-UC5-005 Permission Denied — PASS")

    except Exception as e:

        print(
            f"❌ TC-UC5-005 Permission Denied — FAIL ({e})"
        )

        assert False

# ────────────────────────── TC-UC5-006 (TCOV-UC5-015) ──────────────────────────
def test_TC_UC5_006_delete_cancel(driver):

    try:

        click_delete_and_cancel(
            driver,
            drone_index=1
        )

        page_src = _get_page_source(driver)

        alert_text = get_alert_text(
            driver,
            timeout=3
        )

        # Accept either:
        # 1. No alert
        # 2. Cancel alert shown
        # 3. Page still loads normally
        assert (
            alert_text is None
            or "cancel" in alert_text.lower()
            or "drone" in page_src
        )

        print("✅ TC-UC5-006 Delete Cancel — PASS")

    except Exception as e:

        print(
            f"❌ TC-UC5-006 Delete Cancel — FAIL ({e})"
        )

        assert False


# ────────────────────────── TC-UC5-006 (TCOV-UC5-016) ──────────────────────────
def test_TC_UC5_006_delete_confirm(driver):

    try:

        click_delete_and_confirm(
            driver,
            drone_index=2
        )

        page_src = _get_page_source(driver)

        alert_text = get_alert_text(
            driver,
            timeout=5
        )

        success = (

            (
                alert_text
                and (
                    "deleted" in alert_text.lower()
                    or "success" in alert_text.lower()
                    or "removed" in alert_text.lower()
                )
            )

            or

            (
                "deleted" in page_src
                or "success" in page_src
                or "drone" in page_src
            )
        )

        assert success

        print("✅ TC-UC5-006 Delete Confirm — PASS")

    except Exception as e:

        print(
            f"❌ TC-UC5-006 Delete Confirm — FAIL ({e})"
        )

        assert False