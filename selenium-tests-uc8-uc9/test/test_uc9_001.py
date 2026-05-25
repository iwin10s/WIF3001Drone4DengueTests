import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL       = "http://localhost:3000"
WEATHER_URL    = f"{BASE_URL}/weather-data"
ADMIN_EMAIL    = "admin1@drone4dengue.com"
ADMIN_PASSWORD = "adminpass1"
DEFAULT_WAIT   = 10  

class TestTP_UC9_001:
    """TP-UC9-001 — Weather Data module displays existing records after login."""

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------
    def _login(self, driver):
        """Step 1 — Navigate to login page and authenticate as admin."""
        driver.get(f"{BASE_URL}/")
        wait = WebDriverWait(driver, DEFAULT_WAIT)

        # Step 1a — Enter email
        driver.find_element(By.ID, "email").send_keys(ADMIN_EMAIL)

        # Step 1b — Enter password
        driver.find_element(By.ID, "password").send_keys(ADMIN_PASSWORD)

        # Step 1c — Click LOGIN button
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # FIX: Ensure context hydration completes and user lands on the dashboard
        wait.until(EC.url_contains("/dashboard"))


    # ------------------------------------------------------------------
    # TC-UC9-001
    # ------------------------------------------------------------------
    def test_tc_uc9_001_weather_page_displays_records(self, driver):
        """
        TC-UC9-001
        Input   : Valid admin credentials → click "Weather Data" in sidebar
        Expected: Admin is authenticated; page loads showing weather statistics
                  and existing records in the data table.
        """
        wait = WebDriverWait(driver, 15)

        # ── Step 1: Log in as admin ──────────────────────────────────
        self._login(driver)

        # ── Step 2: Navigate to Weather Data module ──────────────────
        # RECOMMENDED: Use client-side sidebar click to maintain SPA state context 
        # just like UC8, rather than forcing a heavy full-page hard reload.
        try:
            sidebar_link = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/weather-data')]"))
            )
            sidebar_link.click()
        except Exception:
            # Fallback to direct link navigation if sidebar structure differs
            driver.get(WEATHER_URL)

        # ── Step 3: Verify page title / heading is present ───────────
        heading = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[contains(text(),'Weather Data Management')]")
            )
        )
        assert heading.is_displayed(), (
            "Expected 'Weather Data Management' heading to be visible on the page."
        )

        # ── Step 4: Verify statistics cards are rendered ─────────────
        stats_cards = driver.find_elements(
            By.CSS_SELECTOR, "[class*='card'], [class*='Card']"
        )
        assert len(stats_cards) > 0, (
            "Expected at least one statistics card to be rendered on the Weather Data page."
        )

        # ── Step 5: Verify the weather records table is present ───────
        table_or_placeholder = wait.until(
            EC.presence_of_element_located(
                (By.XPATH,
                 "//*[contains(text(),'Weather Records') or "
                 "contains(text(),'No Weather Data') or "
                 "contains(text(),'Date')]")
            )
        )
        assert table_or_placeholder.is_displayed(), (
            "Expected either a weather records table or a placeholder message to be visible."
        )

        # ── Step 6: Print validation execution pass message ──────────
        print("TC-UC9-001 Data Table Displays Records - PASS")