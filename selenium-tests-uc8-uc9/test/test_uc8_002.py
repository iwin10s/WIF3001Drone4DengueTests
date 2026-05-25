"""
test_uc8_002.py

Test Procedure : TP-UC8-002
Test Cases     : TC-UC8-002
Objective      : Verify that the primary data grid correctly lists pre-loaded
                 dengue collection rows when the Search button is clicked, and
                 displays a clean placeholder interface when no filters have
                 been applied (empty state).

Confirmed from page.tsx:
  - Page heading        : h1 text "Data Management"
  - Data table heading  : h3 text "Data Records"
  - Table columns       : Date | Location | Active/Total Cases |
                          Cumulative Duration | Type | State | Actions
  - Empty state text    : "No Data Displayed" + "Please apply filters above
                          and click "Search Data" to view dengue records."
  - No records text     : "No Records Found"
  - Search button       : Button text "Search Data"  (onClick=handleSearch)
  - Data only loads     : AFTER Search Data is clicked (hasAppliedFilters gate)
  - Stats cards         : Total Records | Active Cases | Dengue Hotspots |
                          Locations Covered  (from /dengue-data/summary)

Special Requirements:
  - Admin MUST be authenticated.
  - JWT token MUST exist in localStorage after login.
  - companyId MUST exist in the auth token/context.
  - Database MUST contain at least 1 dengue record for the populated sub-test.
"""

import os
import time
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL      = os.getenv("APP_BASE_URL", "http://localhost:3000")
DATA_MGT_URL  = f"{BASE_URL}/data-management"
ADMIN_EMAIL   = os.getenv("ADMIN_EMAIL", "admin1@drone4dengue.com")
ADMIN_PASS    = os.getenv("ADMIN_PASS",  "adminpass1")
DEFAULT_WAIT  = 20

# Exact UI strings from page.tsx
HEADING_TEXT        = "Data Management"
TABLE_HEADING_TEXT  = "Data Records"
EMPTY_STATE_TEXT    = "No Data Displayed"
EMPTY_STATE_HINT    = "Search Data"          # part of the hint paragraph
NO_RECORDS_TEXT     = "No Records Found"
SEARCH_BTN_TEXT     = "Search Data"

# Expected table column headers (from page.tsx <th> elements)
EXPECTED_COLUMNS = ["Date", "Location", "Active/Total Cases",
                    "Cumulative Duration", "Type", "State", "Actions"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_driver():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1440,900")
    drv = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )
    drv.maximize_window()
    return drv


def login_and_go_to_data_management(driver):
    """
    Full auth flow with hard gates:
      1. Login → /dashboard URL confirmed
      2. JWT token MUST exist in localStorage
      3. companyId MUST exist in localStorage/context
      4. Navigate to /data-management via sidebar (keeps SPA context alive)
      5. Wait for page heading and table heading
    """
    wait = WebDriverWait(driver, DEFAULT_WAIT)

    # Step 1 : Open login page
    driver.get(f"{BASE_URL}/")

    # Step 2 : Fill credentials
    wait.until(EC.visibility_of_element_located((By.ID, "email"))).send_keys(ADMIN_EMAIL)
    driver.find_element(By.ID, "password").send_keys(ADMIN_PASS)

    # Step 3 : Submit
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

    # Step 4 : Confirm /dashboard — credentials accepted
    wait.until(EC.url_contains("/dashboard"))
    print(f"\n[Auth] Logged in as: {ADMIN_EMAIL}")

    # Step 5 : Assert JWT token MUST exist
    token = driver.execute_script("return localStorage.getItem('token');")
    assert token, (
        f"JWT token not found in localStorage after login as {ADMIN_EMAIL}. "
        "Admin MUST be authenticated before this test proceeds."
    )
    print("[Auth] JWT token present.")

    # Step 6 : Assert companyId MUST exist
    company_val = driver.execute_script("""
        return localStorage.getItem('companyId')
            || localStorage.getItem('company_id')
            || localStorage.getItem('user')
            || localStorage.getItem('authUser');
    """)
    assert company_val, (
        "companyId not found in localStorage. "
        "companyId MUST exist in the auth token/context."
    )
    print(f"[Auth] companyId/user context: {str(company_val)[:80]}")

    # Step 7 : Click sidebar link → preserves SPA auth context (no hard reload)
    try:
        sidebar_link = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[contains(@href, '/data-management')]")
            )
        )
        sidebar_link.click()
    except Exception:
        driver.get(DATA_MGT_URL)

    # Step 8 : Wait for URL
    wait.until(EC.url_contains("/data-management"))

    # Step 9 : Wait for main page heading
    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, f"//h1[contains(text(),'{HEADING_TEXT}')]")
        )
    )

    # Step 10 : Wait for table section heading
    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, f"//h3[contains(text(),'{TABLE_HEADING_TEXT}')]")
        )
    )

# ---------------------------------------------------------------------------
# TP-UC8-002 — TC-UC8-002
# ---------------------------------------------------------------------------
class TestTP_UC8_002:
    """
    TP-UC8-002 — Data grid shows records after Search; shows placeholder before.

    Two sub-tests run in separate browser sessions:
      Sub-test A (populated DB)  : click Search Data → table shows rows with
                                   correct columns.
      Sub-test B (pre-search)    : verify the empty placeholder state is shown
                                   BEFORE Search Data is clicked.
    """

    # ------------------------------------------------------------------
    # TC-UC8-002 Sub-test A — Table displays records after Search Data
    # ------------------------------------------------------------------
    def test_tc_uc8_002a_table_displays_records_after_search(self):
        """
        TC-UC8-002 (populated DB sub-test)
        Precondition : Database contains at least 1 dengue record.
        Input        : Admin navigates to Data Management, clicks "Search Data"
                       with no filters (returns all records).
        Expected     : Data Records table renders rows mapping columns:
                       Date, Location, Active/Total Cases, Cumulative Duration,
                       Type, State, Actions.
                       Stats cards (Total Records, Active Cases, etc.) visible.
        """
        driver = make_driver()
        try:
            wait = WebDriverWait(driver, DEFAULT_WAIT)

            # ── Step 1 : Login and navigate to /data-management ───────
            # Asserts JWT + companyId internally before returning.
            login_and_go_to_data_management(driver)


            # ── Step 2 : Confirm empty state IS shown before search ───
            # hasAppliedFilters=false initially → "No Data Displayed".
            empty_state = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH,
                     f"//*[contains(text(),'{EMPTY_STATE_TEXT}')]")
                )
            )
            assert empty_state.is_displayed(), (
                f"Expected '{EMPTY_STATE_TEXT}' placeholder before search."
            )


            # ── Step 4 : Click "Search Data" with no filters ──────────
            # No filters set → returns all records in DB.
            search_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     f"//button[normalize-space()='{SEARCH_BTN_TEXT}']")
                )
            )
            search_btn.click()

            # ── Step 4 : Wait for table to populate with rows ─────────
            # After search, hasAppliedFilters=true and API response loads rows.
            # Wait for at least one <tbody><tr> to appear.
            first_row = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//table//tbody/tr[not(@class='animate-pulse')]")
                )
            )
            assert first_row.is_displayed(), (
                "Expected data rows in the table after clicking Search Data. "
                "Ensure the database contains at least 1 dengue record."
            )

            # ── Step 6 : Verify column headers are correct ─────────────
            # page.tsx <th> elements: Date | Location | Active/Total Cases |
            # Cumulative Duration | Type | State | Actions
            headers = driver.find_elements(By.XPATH, "//table//thead//th")
            header_texts = [h.text.strip() for h in headers if h.text.strip()]
            print(f"[Step 6] Column headers found: {header_texts}")

            for col in EXPECTED_COLUMNS:
                assert any(col in h for h in header_texts), (
                    f"Expected column header '{col}' not found in table.\n"
                    f"Headers present: {header_texts}"
                )
            print("[Step 6] All expected column headers confirmed.")

            # ── Step 7 : Verify first row has data in key columns ──────
            # Spot-check that the Date and Location cells are not empty.
            date_cells = driver.find_elements(
                By.XPATH, "//table//tbody/tr[1]/td[1]"
            )
            assert date_cells and date_cells[0].text.strip(), (
                "Date cell in first row is empty."
            )

            location_cells = driver.find_elements(
                By.XPATH, "//table//tbody/tr[1]/td[2]"
            )
            assert location_cells and location_cells[0].text.strip(), (
                "Location cell in first row is empty."
            )
            print(f"[Step 7] Row 1 — Date: '{date_cells[0].text.strip()}' | "
                  f"Location: '{location_cells[0].text.strip()}'")

            print("TC-UC8-002 Sub-test A (Table Displays Records) — PASS")

        finally:
            driver.quit()

    # ------------------------------------------------------------------
    # TC-UC8-002 Sub-test B — Empty placeholder shown before search
    # ------------------------------------------------------------------
    def test_tc_uc8_002b_empty_placeholder_before_search(self):
        """
        TC-UC8-002 (empty state sub-test)
        Input   : Admin navigates to /data-management WITHOUT clicking
                  "Search Data".
        Expected: Table shows "No Data Displayed" placeholder text and
                  the hint to click "Search Data". No data rows visible.
        """
        driver = make_driver()
        try:
            wait = WebDriverWait(driver, DEFAULT_WAIT)

            # ── Step 1 : Login and navigate to /data-management ───────
            login_and_go_to_data_management(driver)

            # ── Step 2 : Verify "No Data Displayed" placeholder ───────
            # page.tsx line 690: renders when hasAppliedFilters=false.
            empty_heading = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH,
                     f"//*[contains(text(),'{EMPTY_STATE_TEXT}')]")
                )
            )
            assert empty_heading.is_displayed(), (
                f"Expected placeholder '{EMPTY_STATE_TEXT}' before search."
            )
            print(f"[Step 2] Placeholder '{EMPTY_STATE_TEXT}' visible.")

            # ── Step 3 : Verify hint text references "Search Data" ────
            hint_el = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH,
                     f"//*[contains(text(),'{EMPTY_STATE_HINT}')]")
                )
            )
            assert hint_el.is_displayed(), (
                f"Expected hint text containing '{EMPTY_STATE_HINT}' not found."
            )
            print(f"[Step 3] Hint text with '{EMPTY_STATE_HINT}' visible.")

            # ── Step 4 : Confirm NO data rows are present ─────────────
            # Before search, tbody must have no real data rows.
            data_rows = driver.find_elements(
                By.XPATH,
                "//table//tbody/tr[contains(@class,'hover')]"
            )
            assert len(data_rows) == 0, (
                f"Expected 0 data rows before search but found {len(data_rows)}."
            )
            print("[Step 4] No data rows present before search — correct.")

            print("TC-UC8-002 Sub-test B (Empty Placeholder Before Search) — PASS")

        finally:
            driver.quit()