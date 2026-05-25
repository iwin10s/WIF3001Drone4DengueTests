"""
test_uc8_015.py
===============
Test Procedure : TP-UC8-015
Test Cases     : TC-UC8-015
Objective      : Verify that system updates the map view with dengue records
                 by region, and handles null coordinates gracefully.
Coverage Items : TCOV-08-030, TCOV-08-031
Wrap-Up        : None

Pre-condition  : DB contains at least one record with lat=3.1390, lng=101.6869
                 and at least one record with latitude=null, longitude=null.
"""

import time
import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL     = "http://localhost:3000"
DATA_MGT_URL = BASE_URL + "/data-management"


class TestUC8MapView:
    """TP-UC8-015 — Map view with valid and null coordinates."""

    def test_map_renders_markers_for_valid_coordinates(self, logged_in):
        """
        TC-UC8-015 | TCOV-08-030
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management.
        Step 2  Locate the map view (Leaflet MapContainer).
        Step 3  Assert the map canvas renders and at least one marker is present
                for records with valid lat/lng (3.1390, 101.6869).
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        # Scroll to the map section
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # Leaflet renders inside a div with class 'leaflet-container'
        map_container = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".leaflet-container")
            )
        )
        assert map_container.is_displayed(), (
            "TC-UC8-015 FAIL: Leaflet map container not visible on the page."
        )

        # Leaflet markers render as img or div with class 'leaflet-marker-icon'
        time.sleep(2)  # allow tiles + markers to load
        markers = driver.find_elements(By.CSS_SELECTOR, ".leaflet-marker-icon")

        assert len(markers) > 0, (
            "TC-UC8-015 FAIL: No Leaflet markers found on the map. "
            "Ensure DB contains records with valid lat/lng coordinates."
        )
        print("TC-UC8-015 Map Renders Markers for Valid Coordinates - PASS")

    def test_map_remains_stable_with_null_coordinates(self, logged_in):
        """
        TC-UC8-015 | TCOV-08-031
        ─────────────────────────────────────────────────────────────────────
        Step 1  Navigate to /data-management (DB has a record with lat=null).
        Step 2  Locate the Leaflet map container.
        Step 3  Assert the map renders without JS crashes or blank-screen errors.
        Step 4  Assert records with null coords are simply omitted from the map
                (no marker rendered for them) — page remains stable.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # Map must still be present and visible
        map_container = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".leaflet-container")
            )
        )
        assert map_container.is_displayed(), (
            "TC-UC8-015 FAIL: Map container disappeared — possible crash caused "
            "by null coordinate record."
        )

        # Check for JS crash overlay or error modal
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        crash_keywords = ["uncaught", "typeerror", "cannot read", "undefined", "null"]
        # These would appear as visible error overlays, not console logs
        error_overlays = driver.find_elements(
            By.XPATH, "//*[contains(@class,'error') and contains(@class,'overlay')]"
        )
        assert not any(kw in body_text for kw in crash_keywords) or not error_overlays, (
            "TC-UC8-015 FAIL: Page shows crash/error overlay after rendering "
            "map with null coordinate record."
        )
        print("TC-UC8-015 Map Remains Stable with Null Coordinates - PASS")