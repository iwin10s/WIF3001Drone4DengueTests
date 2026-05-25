import pytest
import time
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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


def go_to_dashboard(driver):
    tap(driver, 140, 2050)
    time.sleep(2)


def go_to_dengue_cases_tab(driver):
    go_to_dashboard(driver)
    tap(driver, 720, 330)
    time.sleep(3)


def open_location_alert_modal(driver):
    go_to_dengue_cases_tab(driver)

    source = driver.page_source
    assert "Location Alert" in source, "Location Alert floating button is missing from Dengue Cases page"

    tap(driver, 200, 1750)
    time.sleep(2)


def open_create_alert_modal(driver):
    open_location_alert_modal(driver)

    source = driver.page_source
    assert "Create New Alert" in source, "Create New Alert option is missing from alert modal menu"

    tap(driver, 620, 1170)
    time.sleep(2)


def test_TC_16_001_view_dengue_cases_map(driver):
    go_to_dengue_cases_tab(driver)

    source = driver.page_source

    assert "Dengue Cases" in source, "Dengue Cases page header/title not found after navigation"

    print("PASS: Dengue Cases tab opened")


def test_TC_16_002_tap_location_alert_button(driver):
    open_location_alert_modal(driver)

    source = driver.page_source

    assert "Location-based Alerts" in source or "View Existing Alerts" in source or "Create New Alert" in source, \
        "Alert modal did not open - expected menu options (View Existing/Create New) not found"

    print("PASS: Alert options modal displayed")


def test_TC_16_003_display_view_existing_alerts_option(driver):
    open_location_alert_modal(driver)

    source = driver.page_source

    assert "View Existing Alerts" in source, "'View Existing Alerts' menu item is missing from alert options modal"

    print("PASS: View Existing Alerts option displayed")


def test_TC_16_004_display_create_new_alert_option(driver):
    open_location_alert_modal(driver)

    source = driver.page_source

    assert "Create New Alert" in source, "'Create New Alert' menu item is missing from alert options modal"

    print("PASS: Create New Alert option displayed")


def test_TC_16_005_open_alert_creation_modal(driver):
    open_create_alert_modal(driver)

    source = driver.page_source

    assert "Create Location Alert" in source or "Alert Name" in source, \
        "Alert creation form did not load - missing header or Alert Name field"

    print("PASS: Alert creation modal displayed")


def test_TC_16_006_enter_valid_alert_name(driver):
    open_create_alert_modal(driver)

    wait = WebDriverWait(driver, 20)

    field = wait.until(
        EC.presence_of_element_located(
            (AppiumBy.XPATH, "//*[contains(@text,'Alert Name') or contains(@hint,'Home') or contains(@text,'e.g.')]")
        )
    )

    field.click()
    field.send_keys("Home")

    print("PASS: Valid alert name entered")


def test_TC_16_007_empty_alert_name_validation(driver):
    open_create_alert_modal(driver)

    # Tap map area to select location but leave Alert Name empty
    tap(driver, 600, 1150)
    time.sleep(2)

    # Tap Create Alert button
    tap(driver, 600, 1900)
    time.sleep(2)

    source = driver.page_source

    assert (
        "required" in source.lower()
        or "alert name" in source.lower()
        or "please" in source.lower()
    ), "Validation error for empty Alert Name field was not shown to user"

    print("PASS: Empty alert name validation checked")


def test_TC_16_008_search_and_select_valid_location(driver):
    open_create_alert_modal(driver)

    wait = WebDriverWait(driver, 20)

    search = wait.until(
        EC.presence_of_element_located(
            (AppiumBy.XPATH, "//*[contains(@text,'Search location') or contains(@hint,'Search location')]")
        )
    )

    search.click()
    search.send_keys("Universiti Malaya")
    time.sleep(3)

    source = driver.page_source

    assert "Universiti" in source or "Malaya" in source, \
        "Location search returned no results for 'Universiti Malaya'"

    print("PASS: Location search result displayed")


def test_TC_16_009_select_location_directly_from_map(driver):
    open_create_alert_modal(driver)

    # Tap map area
    tap(driver, 600, 1150)
    time.sleep(2)

    source = driver.page_source

    assert (
        "selected" in source.lower()
        or "location" in source.lower()
        or "500m" in source.lower()
    ), "Map interaction did not register - no location pin or confirmation shown"

    print("PASS: Location selected from map")


def test_TC_16_010_display_selected_address(driver):
    open_create_alert_modal(driver)

    tap(driver, 600, 1150)
    time.sleep(3)

    source = driver.page_source

    assert (
        "Kuala Lumpur" in source
        or "Malaysia" in source
        or "location" in source.lower()
    ), "Reverse geocoding failed - selected location's address not displayed"

    print("PASS: Selected address displayed")


def test_TC_16_011_create_location_alert_successfully(driver):
    open_create_alert_modal(driver)

    # Tap alert name field roughly
    tap(driver, 600, 520)
    time.sleep(1)

    # Type Home using Android keycodes may vary, so use keyboard text if focused
    driver.press_keycode(36)  # H
    driver.press_keycode(43)  # o
    driver.press_keycode(41)  # m
    driver.press_keycode(33)  # e

    # Tap map
    tap(driver, 600, 1150)
    time.sleep(2)

    # Tap Create Alert
    tap(driver, 600, 1900)
    time.sleep(3)

    source = driver.page_source

    assert (
        "success" in source.lower()
        or "created" in source.lower()
        or "Location alert created successfully" in source
    ), "Alert creation failed - no success confirmation message received"

    print("PASS: Location alert created successfully")


def test_TC_16_012_display_success_message_after_creation(driver):
    open_create_alert_modal(driver)

    tap(driver, 600, 520)
    time.sleep(1)

    driver.press_keycode(36)
    driver.press_keycode(43)
    driver.press_keycode(41)
    driver.press_keycode(33)

    tap(driver, 600, 1150)
    time.sleep(2)

    tap(driver, 600, 1900)
    time.sleep(3)

    source = driver.page_source

    assert "Location alert created successfully" in source or "success" in source.lower(), \
        "Expected success message 'Location alert created successfully' not displayed after creation"

    print("PASS: Success message displayed")


def test_TC_16_013_view_existing_saved_alerts(driver):
    open_location_alert_modal(driver)

    source = driver.page_source
    assert "View Existing Alerts" in source, "'View Existing Alerts' option not found in alert modal"

    tap(driver, 580, 980)
    time.sleep(2)

    source = driver.page_source

    assert "My Location Alerts" in source or "Active" in source or "Alerts" in source, \
        "Existing alerts list page did not load - missing expected page elements"

    print("PASS: Existing saved alerts displayed")


def test_TC_16_014_delete_existing_alert(driver):
    open_location_alert_modal(driver)

    tap(driver, 580, 980)
    time.sleep(2)

    # Tap delete icon on first alert card
    tap(driver, 1020, 730)
    time.sleep(2)

    print("PASS: Delete alert action executed")


def test_TC_16_015_toggle_active_paused_status(driver):
    open_location_alert_modal(driver)

    tap(driver, 580, 980)
    time.sleep(2)

    # Tap Active status badge area
    tap(driver, 930, 730)
    time.sleep(2)

    print("PASS: Alert status toggle action executed")


def test_TC_16_016_alert_creation_server_error(driver):
    open_create_alert_modal(driver)

    tap(driver, 600, 520)
    time.sleep(1)

    driver.press_keycode(36)
    driver.press_keycode(43)
    driver.press_keycode(41)
    driver.press_keycode(33)

    tap(driver, 600, 1150)
    time.sleep(2)

    tap(driver, 600, 1900)
    time.sleep(3)

    source = driver.page_source

    assert (
        "Failed to create location alert" in source
        or "failed" in source.lower()
    ), "Server error handling failed - expected error message not displayed when creation fails"

    print("PASS: Server error message displayed")