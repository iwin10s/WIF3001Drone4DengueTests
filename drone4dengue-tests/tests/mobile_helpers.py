# Shared helpers for Appium mobile tests (iOS / Expo Go).

import time

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def accept_medical_disclaimer_if_shown(driver, timeout=20):
    """
    Scroll through the medical disclaimer and tap I Understand & Accept when shown.
    No-op if the user already accepted it in a previous session.
    """
    wait = WebDriverWait(driver, 6)
    try:
        wait.until(
            EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "disclaimerModal"))
        )
    except TimeoutException:
        try:
            wait.until(
                EC.presence_of_element_located(
                    (
                        AppiumBy.IOS_PREDICATE,
                        'label == "Medical Disclaimer"',
                    )
                )
            )
        except TimeoutException:
            return

    _scroll_disclaimer_to_bottom(driver)
    _tap_disclaimer_accept(driver, timeout)

    WebDriverWait(driver, timeout).until_not(
        EC.presence_of_element_located(
            (AppiumBy.IOS_PREDICATE, 'label == "Medical Disclaimer"')
        )
    )


def _scroll_disclaimer_to_bottom(driver):
    """Scroll the disclaimer until the accept button is enabled."""
    accept_wait = WebDriverWait(driver, 20)

    for _ in range(15):
        try:
            button = driver.find_element(
                AppiumBy.ACCESSIBILITY_ID, "disclaimerAcceptButton"
            )
            if button.is_enabled():
                return
        except Exception:
            pass

        try:
            scroll = driver.find_element(
                AppiumBy.ACCESSIBILITY_ID, "disclaimerScroll"
            )
            driver.execute_script(
                "mobile: scroll",
                {"element": scroll, "direction": "down"},
            )
        except Exception:
            size = driver.get_window_size()
            driver.execute_script(
                "mobile: swipe",
                {
                    "direction": "up",
                    "left": size["width"] // 2,
                    "top": int(size["height"] * 0.65),
                    "width": 1,
                    "height": int(size["height"] * 0.3),
                },
            )
        time.sleep(0.35)

    # Fallback: tap by visible label once scroll threshold may have passed
    try:
        driver.find_element(
            AppiumBy.IOS_PREDICATE,
            'label == "I Understand & Accept" AND type == "XCUIElementTypeButton"',
        )
        return
    except Exception:
        pass

    accept_wait.until(
        lambda d: d.find_element(
            AppiumBy.ACCESSIBILITY_ID, "disclaimerAcceptButton"
        ).is_enabled()
    )


def _tap_disclaimer_accept(driver, timeout=12):
    wait = WebDriverWait(driver, timeout)
    try:
        accept_btn = wait.until(
            EC.element_to_be_clickable(
                (AppiumBy.ACCESSIBILITY_ID, "disclaimerAcceptButton")
            )
        )
        accept_btn.click()
    except TimeoutException:
        wait.until(
            EC.element_to_be_clickable(
                (
                    AppiumBy.IOS_PREDICATE,
                    'label == "I Understand & Accept" AND type == "XCUIElementTypeButton"',
                )
            )
        ).click()

    WebDriverWait(driver, timeout).until_not(
        EC.presence_of_element_located((AppiumBy.ACCESSIBILITY_ID, "disclaimerModal"))
    )
