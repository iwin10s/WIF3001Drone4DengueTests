# conftest.py

import os
import re
import subprocess
import time

import pytest
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from appium import webdriver as appium_driver
from appium.options.ios import XCUITestOptions
from supabase import create_client

from tests.mobile_helpers import accept_medical_disclaimer_if_shown

# ── Mobile test configuration ────────────────────────────────────────────────
EXPO_DEV_URL = os.environ.get("EXPO_DEV_URL", "exp://127.0.0.1:8081")
MOBILE_UDID = os.environ.get("MOBILE_UDID", "B644F668-6C96-4E85-A88D-39862BF6B8AE")
MOBILE_DEVICE_NAME = os.environ.get("MOBILE_DEVICE_NAME", "iPhone 17")
NATIVE_BUNDLE_ID = "com.adamarbain.dengueeyemobileapp"
EXPO_GO_BUNDLE_ID = "host.exp.Exponent"

# Resolved at session start (see _resolve_mobile_bundle_id).
MOBILE_BUNDLE_ID = None

# ── Supabase credentials ─────────────────────────────────────────────────────
SUPABASE_URL = "https://ozahoqpfmxejowtttjgn.supabase.co"
SUPABASE_SERVICE_KEY = "sb_secret_LXNrfyjpNm4OWa9MEnWutg_1LuqDG_w"

TEST_EMAILS = [
    "wingtenglei@gmail.com",
    "23004953@siswa.um.edu.my",
    "existing@gmail.com",
]


def _simulator_installed_bundle_ids(udid):
    result = subprocess.run(
        ["xcrun", "simctl", "listapps", udid],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return set()

    # simctl prints plist-style dictionaries, not JSON
    return set(re.findall(r'^\s+"([^"]+)"\s*=\s*\{', result.stdout, re.MULTILINE))


def _resolve_mobile_bundle_id():
    """
    Pick an app that is actually installed on the simulator.
    Honors MOBILE_BUNDLE_ID when set and installed; otherwise prefers native
    build, then Expo Go.
    """
    installed = _simulator_installed_bundle_ids(MOBILE_UDID)
    if not installed:
        pytest.skip(
            f"No apps found on simulator {MOBILE_UDID}. Boot a simulator first."
        )

    requested = os.environ.get("MOBILE_BUNDLE_ID")
    candidates = []
    if requested:
        candidates.append(requested)
    candidates.extend([NATIVE_BUNDLE_ID, EXPO_GO_BUNDLE_ID])

    for bundle_id in candidates:
        if bundle_id in installed:
            print(f"[mobile] Using bundle id: {bundle_id}")
            return bundle_id

    pytest.skip(
        "No supported app installed. Install Expo Go on the simulator or run "
        "`cd client-mobile && npx expo run:ios`. "
        f"MOBILE_BUNDLE_ID={requested!r} was not found."
    )


def _launch_expo_project(driver, route_path="/--/(auth)/login"):
    """Open the DengueEye JS bundle inside Expo Go via deep link."""
    base = EXPO_DEV_URL.rstrip("/")
    url = f"{base}{route_path}"
    driver.execute_script(
        "mobile: deepLink",
        {"url": url, "bundleId": MOBILE_BUNDLE_ID},
    )
    time.sleep(4)


@pytest.fixture(scope="session")
def supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


@pytest.fixture(autouse=True)
def cleanup_test_accounts(supabase_client):
    yield

    for email in TEST_EMAILS:
        try:
            response = supabase_client.auth.admin.list_users()
            for user in response:
                if user.email == email:
                    supabase_client.auth.admin.delete_user(user.id)
                    print(f"Cleaned up: {email}")
        except Exception as e:
            print(f"Cleanup skipped for {email}: {e}")


@pytest.fixture
def web_driver():
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.fixture
def mobile_driver():
    global MOBILE_BUNDLE_ID
    MOBILE_BUNDLE_ID = _resolve_mobile_bundle_id()

    options = XCUITestOptions()
    options.platform_name = "iOS"
    options.device_name = MOBILE_DEVICE_NAME
    options.udid = MOBILE_UDID
    options.bundle_id = MOBILE_BUNDLE_ID
    options.automation_name = "XCUITest"
    options.new_command_timeout = 300

    app_path = os.environ.get("MOBILE_APP_PATH")
    if app_path:
        options.app = app_path

    driver = appium_driver.Remote("http://localhost:4723", options=options)
    driver.implicitly_wait(3)

    if MOBILE_BUNDLE_ID == EXPO_GO_BUNDLE_ID:
        _launch_expo_project(driver, "/--/(auth)/login")
        # Give Metro a moment to serve the latest JS bundle after code changes.
        time.sleep(2)

    accept_medical_disclaimer_if_shown(driver)

    yield driver
    driver.quit()
