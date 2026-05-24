import time
import pytest

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options


BASE_URL = "http://localhost:3000"

ADMIN_EMAIL = "s@gmail.com"
ADMIN_PASSWORD = "denisetest1"

SEARCH_NAME = "Drone Alpha"
SEARCH_MODEL = "DJI Phantom 4 Pro"
SEARCH_AREA = "Klang Valley"
INVALID_SEARCH = "zzz-no-drone"

FILTER_STATUS = "Maintenance"

@pytest.fixture
def driver():

    opts = Options()

    # COMMENT THIS AFTER DEBUGGING
    # opts.add_argument("--headless=new")

    opts.add_argument("--window-size=1920,1080")

    drv = webdriver.Chrome(
        options=opts
    )

    drv.maximize_window()

    wait = WebDriverWait(
        drv,
        30
    )

    drv.get(BASE_URL)

    email = wait.until(
        EC.element_to_be_clickable(
            (
                By.ID,
                "email"
            )
        )
    )

    password = drv.find_element(
        By.ID,
        "password"
    )

    email.send_keys(
        ADMIN_EMAIL
    )

    password.send_keys(
        ADMIN_PASSWORD
    )

    drv.find_element(
        By.XPATH,
        "//button[contains(.,'LOGIN')]"
    ).click()

    time.sleep(5)

    yield drv

    drv.quit()


def open_drone_management(driver):

    driver.get(
        BASE_URL + "/drone-management"
    )

    WebDriverWait(
        driver,
        30
    ).until(
        EC.presence_of_element_located(
            (
                By.TAG_NAME,
                "body"
            )
        )
    )

    time.sleep(5)


def search(driver, keyword):

    wait = WebDriverWait(
        driver,
        30
    )

    search_box = wait.until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//input[@placeholder='Search drones...']"
            )
        )
    )

    driver.execute_script(
        "arguments[0].scrollIntoView(true);",
        search_box
    )

    driver.execute_script(
        "arguments[0].click();",
        search_box
    )

    time.sleep(1)

    search_box.send_keys(
        Keys.CONTROL,
        "a"
    )

    search_box.send_keys(
        Keys.BACKSPACE
    )

    search_box.send_keys(
        keyword
    )

    time.sleep(3)


def test_TC_UC5_001_page_load(driver):
    try:

        open_drone_management(driver)

        assert "Drone" in driver.page_source

        print("✅ TC-UC5-001 Page Load — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-001 Page Load — FAIL ({e})")

        assert False


def test_TC_UC5_002_search_name(driver):

    try:

        open_drone_management(driver)

        search(driver, SEARCH_NAME)

        assert SEARCH_NAME in driver.page_source

        print("✅ TC-UC5-002 Search Name — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-002 Search Name — FAIL ({e})")

        assert False


def test_TC_UC5_002_search_model(driver):

    try:

        open_drone_management(driver)

        search(driver, SEARCH_MODEL)

        assert SEARCH_MODEL in driver.page_source

        print("✅ TC-UC5-002 Search Model — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-002 Search Model — FAIL ({e})")

        assert False


def test_TC_UC5_002_search_area(driver):

    try:

        open_drone_management(driver)

        search(driver, SEARCH_AREA)

        assert SEARCH_AREA in driver.page_source

        print("✅ TC-UC5-002 Search Area — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-002 Search Area — FAIL ({e})")

        assert False


def test_TC_UC5_002_search_no_result(driver):
    try:

        open_drone_management(driver)

        search(driver, INVALID_SEARCH)

        assert (
            "No drones found" in driver.page_source
            or
            "No records" in driver.page_source
        )

        print("✅ TC-UC5-002 Invalid Search — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-002 Invalid Search — FAIL ({e})")

        assert False

def test_TC_UC5_002_filter_status(driver):

    try:

        open_drone_management(driver)

        dropdown = driver.find_element(
            By.TAG_NAME,
            "select"
        )

        dropdown.send_keys(
            FILTER_STATUS
        )

        time.sleep(3)

        print("✅ TC-UC5-002 Filter Status — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-002 Filter Status — FAIL ({e})")

        assert False


def test_TC_UC5_002_pagination(driver):

    try:

        open_drone_management(driver)

        wait = WebDriverWait(
            driver,
            20
        )

        next_btn = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(., 'Next')]"
                )
            )
        )

        assert next_btn.is_enabled()

        next_btn.click()

        time.sleep(2)

        previous_btn = wait.until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(., 'Previous')]"
                )
            )
        )

        assert previous_btn.is_enabled()

        previous_btn.click()

        time.sleep(2)

        print("✅ TC-UC5-002 Pagination — PASS")

    except Exception as e:

        print(f"❌ TC-UC5-002 Pagination — FAIL ({e})")

        assert False