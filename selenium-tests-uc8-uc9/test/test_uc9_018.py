import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC


BASE_URL    = "http://localhost:3000"
WEATHER_URL = f"{BASE_URL}/weather-data"


FILTER_DATE     = "2026-04-01"
FILTER_LOCATION = "Batu Pahat"   # partial text used to match the dropdown option




class TestTP_UC9_018:
    """TP-UC9-018 — Date and location filters show only matching records."""


    def _get_filter_elements(self, driver):
        """
        Return (date_filter_el, location_select_el) for the table filter bar.
        There may be multiple elements with the same ID (one in the upload
        section, one in the filter bar).  We take the last occurrence.
        """
        date_els    = driver.find_elements(By.ID, "dateFilter")
        loc_els     = driver.find_elements(By.ID, "locationSelect")
        return date_els[-1], loc_els[-1]


    def _get_visible_row_count(self, driver):
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        return len([r for r in rows if r.is_displayed()])


    def _clear_date_filter(self, driver):
        date_els = driver.find_elements(By.ID, "dateFilter")
        el = date_els[-1]
        el.clear()
        el.send_keys(Keys.TAB)


    def test_tc_uc9_027_filter_by_date(self, logged_in):
        """
        TC-UC9-027 — Part A
        Input   : Date filter = 2026-04-01
        Expected: Only records for 2026-04-01 remain visible in the table.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)


        # ── Step 1: Confirm we are on the Weather Data page ──────────
        wait.until(EC.url_contains("/weather-data"))


        # ── Step 2: Apply the Date filter ─────────────────────────────
        date_el, _ = self._get_filter_elements(driver)
        date_el.clear()
        date_el.send_keys(FILTER_DATE)
        date_el.send_keys(Keys.TAB)   # trigger onChange


        # ── Step 3: Allow the table to re-render ──────────────────────
        import time; time.sleep(1)


        # ── Step 4: Verify all visible rows contain the filtered date ─
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        assert rows, "No table rows found after applying date filter."


        for row in rows:
            row_text = row.text
            assert FILTER_DATE in row_text or "No weather data" in driver.page_source, (
                f"Row does not match filter date '{FILTER_DATE}': '{row_text}'"
            )


        print("TC-UC9-027A Filter by Date - PASS")




    def test_tc_uc9_027_filter_by_location(self, logged_in):
        """
        TC-UC9-027 — Part B
        Input   : Location filter = Batu Pahat - Jalan Rahmat, Batu Pahat, Johor
        Expected: Only records for that operational area are shown.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)


        # ── Step 1: Reload to reset all filters ───────────────────────
        driver.get(WEATHER_URL)
        wait.until(EC.url_contains("/weather-data"))


        # ── Step 2: Select the Batu Pahat location from the filter dropdown
        _, loc_el = self._get_filter_elements(driver)
        loc_select = Select(loc_el)


        # Find the option containing "Batu Pahat"
        selected = False
        for option in loc_select.options:
            if FILTER_LOCATION.lower() in option.text.lower():
                loc_select.select_by_visible_text(option.text)
                selected = True
                break
        assert selected, (
            f"Could not find '{FILTER_LOCATION}' in the location filter dropdown."
        )


        # ── Step 3: Allow table to re-render ──────────────────────────
        import time; time.sleep(1)


        # ── Step 4: Verify all visible rows belong to Batu Pahat ──────
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        assert rows, "No table rows found after applying location filter."


        for row in rows:
            row_text = row.text
            assert FILTER_LOCATION in row_text or "No weather data" in driver.page_source, (
                f"Row does not match filter location '{FILTER_LOCATION}': '{row_text}'"
            )


        print("TC-UC9-027B Filter by Location - PASS")


    def test_tc_uc9_027_filter_by_date_and_location_combined(self, logged_in):
        """
        TC-UC9-027 — Part C
        Input   : Date = 2026-04-01 AND Location = Batu Pahat
        Expected: Only records matching both criteria are shown simultaneously.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 15)


        # ── Step 1: Reload to reset all filters ───────────────────────
        driver.get(WEATHER_URL)
        wait.until(EC.url_contains("/weather-data"))


        # ── Step 2: Apply Date filter ──────────────────────────────────
        date_el, loc_el = self._get_filter_elements(driver)
        date_el.clear()
        date_el.send_keys(FILTER_DATE)
        date_el.send_keys(Keys.TAB)


        # ── Step 3: Apply Location filter ─────────────────────────────
        loc_select = Select(loc_el)
        for option in loc_select.options:
            if FILTER_LOCATION.lower() in option.text.lower():
                loc_select.select_by_visible_text(option.text)
                break


        # ── Step 4: Allow table to re-render ──────────────────────────
        import time; time.sleep(1)


        # ── Step 5: Verify all visible rows match BOTH criteria ────────
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        for row in rows:
            row_text = row.text
            matches_date     = FILTER_DATE     in row_text
            matches_location = FILTER_LOCATION in row_text
            both_match       = matches_date and matches_location
            no_data          = "No weather data" in driver.page_source


            assert both_match or no_data, (
                f"Row does not match both filters "
                f"(date='{FILTER_DATE}', location='{FILTER_LOCATION}'): '{row_text}'"
            )


            print("TC-UC9-027C Filter by Date + Location Combined - PASS")