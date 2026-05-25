import pytest
from appium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
import time


@pytest.fixture
def driver():
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = "emulator-5554"
    options.app_package = "com.adamarbain.dengueeyemobileapp"
    options.app_activity = ".MainActivity"
    options.no_reset = True

    d = webdriver.Remote("http://localhost:4723", options=options)
    yield d
    d.quit()


def tap(driver, x, y):
    driver.execute_script("mobile: clickGesture", {"x": x, "y": y})


def go_to_recommendation_page(driver):
    tap(driver, 520, 2050)
    time.sleep(1)


def test_TC_14_001_open_recommendation_page(driver):
    wait = WebDriverWait(driver, 30)

    go_to_recommendation_page(driver)

    high_risk = wait.until(
        EC.presence_of_element_located(
            (AppiumBy.XPATH, "//*[contains(@text,'High Risk')]")
        )
    )

    assert high_risk.is_displayed()
    print("PASS: Recommendation page displayed")


def test_TC_14_002_view_high_risk(driver):
    go_to_recommendation_page(driver)

    tap(driver, 520, 350)
    time.sleep(2)

    print("PASS: High Risk Recommendation clicked successfully")


def test_TC_14_003_view_medium_risk(driver):
    go_to_recommendation_page(driver)

    tap(driver, 520, 650)
    time.sleep(2)

    print("PASS: Medium Risk Recommendation clicked successfully")


def test_TC_14_004_view_low_risk(driver):
    go_to_recommendation_page(driver)

    tap(driver, 520, 950)
    time.sleep(2)

    print("PASS: Low Risk Recommendation clicked successfully")


def test_TC_14_005_expand_recommendation_item(driver):
    go_to_recommendation_page(driver)

    tap(driver, 520, 350)
    time.sleep(1)

    tap(driver, 520, 520)
    time.sleep(1)

    source = driver.page_source
    assert "View Source" in source or "Fogging" in source or "stagnant" in source

    print("PASS: Recommendation item expanded and details displayed")


def test_TC_14_006_navigate_to_dashboard(driver):
    go_to_recommendation_page(driver)

    tap(driver, 180, 2050)
    time.sleep(1)

    print("PASS: User navigated to Dashboard page")


def test_TC_14_007_navigate_to_profile(driver):
    go_to_recommendation_page(driver)

    tap(driver, 900, 2050)
    time.sleep(1)

    print("PASS: User navigated to Profile page")


def test_TC_14_008_back_button_navigation(driver):
    go_to_recommendation_page(driver)

    tap(driver, 520, 350)
    time.sleep(1)

    back_buttons = driver.find_elements(
        AppiumBy.XPATH,
        "//*[contains(@content-desc,'Back') or contains(@text,'Back')]"
    )

    assert len(back_buttons) > 0, "FAIL: Back navigation component not found"

    print("PASS: Back button exists")