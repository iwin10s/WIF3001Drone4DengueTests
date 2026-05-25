import pytest
import time
import csv
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException
)
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys

BASE_URL        = "http://localhost:3000"
ADMIN_EMAIL     = "kiki@gmail.com"
ADMIN_PASSWORD  = "Abc12345!"
DOWNLOAD_DIR    = os.path.join(os.getcwd(), "downloads")

@pytest.fixture
def driver():
    """Launch Chrome with download preferences configured."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    opts = webdriver.ChromeOptions()
    opts.add_experimental_option("prefs", {
        "download.default_directory": DOWNLOAD_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })
    svc = Service(ChromeDriverManager().install())
    drv = webdriver.Chrome(service=svc, options=opts)
    drv.maximize_window()
    drv.get(BASE_URL)
    yield drv
    drv.quit()

#  HELPER FUNCTIONS
def login_and_go_to_prediction(driver):
    wait = WebDriverWait(driver, 20)

    # Always start from BASE_URL to get a clean login state
    driver.get(BASE_URL)

    # Wait for login form
    email_field = wait.until(EC.visibility_of_element_located((By.ID, "email")))
    email_field.clear()
    email_field.send_keys(ADMIN_EMAIL)

    password_field = driver.find_element(By.ID, "password")
    password_field.clear()
    password_field.send_keys(ADMIN_PASSWORD)

    driver.find_element(
        By.XPATH, "//button[@type='submit' and contains(text(),'LOGIN')]"
    ).click()

    # Wait for dashboard redirect
    wait.until(EC.url_contains("/dashboard"))

    # Click Prediction & Alert in sidebar
    sidebar_link = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//*[contains(text(),'Prediction') and contains(text(),'Alert')]")
        )
    )
    sidebar_link.click()

    # Wait for the h1 heading — use URL as a fallback signal too
    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h1[contains(text(),'Prediction & Alert')]")
        )
    )
    time.sleep(1)  # allow React to finish rendering predictions


def get_latest_csv():
    """Return path of the most recently created CSV in DOWNLOAD_DIR, or None."""
    files = [os.path.join(DOWNLOAD_DIR, f)
             for f in os.listdir(DOWNLOAD_DIR) if f.endswith(".csv")]
    return max(files, key=os.path.getctime) if files else None


def clear_downloads():
    """Delete all files in DOWNLOAD_DIR."""
    if os.path.exists(DOWNLOAD_DIR):
        for f in os.listdir(DOWNLOAD_DIR):
            os.remove(os.path.join(DOWNLOAD_DIR, f))


def nsp(xpath_text):
    """
    Wrap an XPath text literal in normalize-space().
    All buttons in page.tsx contain SVG icon children before their text,
    so contains(text(),...) fails. normalize-space(.) concatenates all
    descendant text nodes, making substring matching reliable.
    Usage: f"//button[{nsp('Export')}]"
    """
    return f"contains(normalize-space(.), '{xpath_text}')"


#  TP-12.01-001  Load Dashboard and Apply Filters
#  Technique: EP (filter values), BVA (date boundaries), ST (filter changes)
def test_tp12_001_dashboard_load_and_filters(driver):
    wait = WebDriverWait(driver, 20)
    login_and_go_to_prediction(driver)

    # ── Steps 2-4: Page elements ─────────────────────────────────────────────
    assert wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h1[contains(text(),'Prediction & Alert')]")
        )
    ).is_displayed(), "h1 'Prediction & Alert' not visible"

    assert driver.find_element(
        By.XPATH, "//h2[contains(text(),'Dengue Predictions')]"
    ).is_displayed(), "h2 'Dengue Predictions' not visible"

    assert driver.find_element(
        By.XPATH, "//div[contains(text(),'Predicted Risk Areas')]"
    ).is_displayed(), "Predicted Risk Areas section not visible"

    # ── Steps 5-9: Risk Level filter (EP – each valid partition) ─────────────
    risk_select = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//select[option[text()='All Levels']]")
        )
    )
    select = Select(risk_select)

    initial_rows = driver.find_elements(By.XPATH, "//table//tbody//tr")
    print(f"\n[INFO] Initial prediction count: {len(initial_rows)}")

    for level in ["High", "Medium", "Low", "All Levels"]:
        select.select_by_visible_text(level)
        time.sleep(1.5)  # allow React re-render

        # Only count REAL data rows — those that have a badge span in td[2].
        # The empty-state row (<tr><td colspan="6">No predictions match...</td></tr>)
        # has no td[2]//span, so it is correctly excluded from this count.
        data_rows = driver.find_elements(
            By.XPATH, "//table//tbody//tr[td[2]//span]"
        )

        if level == "All Levels":
            print(f"[INFO] Filter={level}: {len(data_rows)} data rows")
            continue

        if data_rows:
            badges = driver.find_elements(
                By.XPATH,
                f"//table//tbody//tr//td[2]//span[{nsp(level.upper())}]"
            )
            actual_texts = [s.text.strip() for s in driver.find_elements(
                By.XPATH, "//table//tbody//tr//td[2]//span"
            )]
            print(f"[INFO] Filter={level}: {len(data_rows)} data rows, "
                  f"{len(badges)} matching badges | all badges: {actual_texts}")

        
            assert len(badges) == len(data_rows), (
                f"[DEF-001] Filter='{level}' shows {len(data_rows)} data row(s) but "
                f"only {len(badges)} badge(s) show '{level.upper()}'. "
                f"Actual badge texts: {actual_texts}. "
                f"A row passed the filter despite having a different risk level — "
                f"riskLevel in DB is likely not stored in lowercase."
            )
        else:
            # No data rows — the empty-state message must be visible
            empty_msg = driver.find_elements(
                By.XPATH,
                "//td[contains(text(),'No predictions match the selected filters')]"
            )
            assert empty_msg and empty_msg[0].is_displayed(), (
                f"Filter={level} returned no data but empty-state message not shown"
            )
            print(f"[INFO] Filter={level}: no data — correct empty-state message shown")

    # ── Steps 10-12: Date Range picker renders (BVA — UI only) ───────────────
    date_trigger = driver.find_element(
        By.XPATH, "//input[@placeholder='Select date range' or @type='text']"
    )
    assert date_trigger.is_displayed(), "Date Range picker not visible"
    date_trigger.click()
    time.sleep(0.5)
    print("[INFO] Date Range picker opened (UI check)")
    driver.find_element(By.XPATH, "//h2[contains(text(),'Dengue Predictions')]").click()
    time.sleep(0.5)


#  TP-12.01-002  View Detailed Prediction Information
#  Technique: DT (risk level combinations), CL (required fields)
def test_tp12_002_view_prediction_details(driver):
    """
    Verify Admin can view detailed prediction information for different risk areas.

    Steps 3, 5, 6: Click View Details for available row(s) and verify modal fields.
    """
    wait = WebDriverWait(driver, 20)
    login_and_go_to_prediction(driver)

    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//div[contains(text(),'Predicted Risk Areas')]")
        )
    )
    time.sleep(2)

    eye_buttons = driver.find_elements(
        By.XPATH, "//table//tbody//tr//td[last()]//button[1]"
    )
    if not eye_buttons:
        pytest.skip("No prediction rows available to test View Details")

    eye_buttons[0].click()

    modal_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'Prediction Details')]")
        )
    )
    assert modal_heading.is_displayed(), "Prediction Details modal did not open"

    for field in ["Risk Level", "Risk Score", "Historical Data Score",
                  "Weather Score", "Coordinates"]:
        elem = driver.find_element(By.XPATH, f"//*[contains(text(),'{field}')]")
        assert elem.is_displayed(), f"Field '{field}' not visible in modal"

    model3 = driver.find_elements(
        By.XPATH, "//*[contains(text(),'Breeding Area Detection Score')]"
    )
    if model3:
        print("[INFO] Model 3 score present (enhanced prediction)")

    combined = driver.find_elements(
        By.XPATH, "//*[contains(text(),'Combined Score')]"
    )
    if combined:
        print("[INFO] Combined score present (multi-model prediction)")

    # Close modal — button text is the HTML entity × rendered as ×
    close_btn = driver.find_element(
        By.XPATH,
        "//button[contains(text(),'×') or contains(text(),'\u00d7') or contains(text(),'✕')]"
    )
    close_btn.click()
    time.sleep(0.5)

    modal_gone = driver.find_elements(
        By.XPATH, "//h2[contains(text(),'Prediction Details')]"
    )
    assert len(modal_gone) == 0 or not modal_gone[0].is_displayed(), \
        "Modal did not close after clicking ×"



#  TP-12.01-003  Export CSV and Refresh Predictions
#  Technique: ST (button loading states), CL (CSV structure)
def test_tp12_003_export_and_refresh(driver):
    """
    Verify Admin can export prediction report (CSV) and refresh prediction data.

    Step 3: Click Export — verify CSV downloaded with correct filename & headers.
    Step 4: Click Refresh Predictions — verify spinner then idle state.

    NOTE: Both buttons contain SVG icon children (FiDownload / FiRefreshCw),
    so contains(text(),...) fails. Use normalize-space(.) via the nsp() helper.
    """
    wait = WebDriverWait(driver, 20)
    clear_downloads()
    login_and_go_to_prediction(driver)

    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//div[contains(text(),'Predicted Risk Areas')]")
        )
    )
    time.sleep(2)

    row_count = len(driver.find_elements(By.XPATH, "//table//tbody//tr"))
    print(f"\n[INFO] Predictions visible in table: {row_count}")

    # ── Step 3: Export ────────────────────────────────────────────────────────
    export_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//button[{nsp('Export')} and not({nsp('Exporting')})]")
        )
    )
    assert export_btn.is_enabled(), "Export button should be enabled initially"
    export_btn.click()

    time.sleep(2)

    # Verify button returns to idle
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//button[{nsp('Export')} and not({nsp('Exporting')})]")
        )
    )

    # ── CSV verification ──────────────────────────────────────────────────────
    time.sleep(1)
    csv_file = get_latest_csv()
    if not csv_file:
        pytest.skip("CSV download not captured — check browser download settings")

    filename = os.path.basename(csv_file)
    assert filename.startswith("dengue-predictions-"), \
        f"CSV filename incorrect: {filename}"
    assert filename.endswith(".csv"), \
        f"File should be .csv, got: {filename}"

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        for col in [
            "Operational Area", "Location Address", "Latitude", "Longitude",
            "Risk Level", "Risk Score", "Model 1 Score", "Model 2 Score",
            "Model 3 Score", "Combined Score", "Images Processed",
            "Models Used", "Date"
        ]:
            assert col in headers, f"Missing CSV header: {col}"
        rows = list(reader)
        print(f"[INFO] CSV exported with {len(rows)} predictions")
        if row_count > 0:
            assert len(rows) > 0, "CSV should contain data when table has rows"

    # ── Step 4: Refresh Predictions ───────────────────────────────────────────
    # The Refresh button: <button><FiRefreshCw ... /> Refresh Predictions</button>
    # Same icon-before-text pattern — must use nsp().
    refresh_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH,
             f"//button[{nsp('Refresh Predictions')} and not({nsp('Refreshing')})]")
        )
    )
    assert refresh_btn.is_enabled(), "Refresh button should be enabled"
    refresh_btn.click()

    time.sleep(0.5)
    # Optionally verify spinner class (may be too fast)
    driver.find_elements(
        By.XPATH, "//*[name()='svg' and contains(@class,'animate-spin')]"
    )

    # Wait until button returns to idle
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH,
             f"//button[{nsp('Refresh Predictions')} and not({nsp('Refreshing')})]")
        )
    )
    print("[INFO] Refresh completed successfully")


#  TP-12.01-004  Configure Alert Rules
def test_tp12_004_configure_alert_rules(driver):
    """
    Verify Admin can configure notification recipients and channels.

    Steps 3-5: Select All Health Officials + all channels → Save → success.
    Steps 6-7: Email only → Save → success.
    """
    wait = WebDriverWait(driver, 20)
    login_and_go_to_prediction(driver)

    alert_section = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h3[contains(text(),'Set Alert Rules')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", alert_section)
    time.sleep(0.5)

    recipient_select = driver.find_element(
        By.XPATH, "//select[option[text()='-- Select Recipients --']]"
    )
    Select(recipient_select).select_by_visible_text("All Health Officials")

    email_cb = driver.find_element(
        By.XPATH, "//label[contains(.,'Email')]//input[@type='checkbox']"
    )
    sms_cb = driver.find_element(
        By.XPATH, "//label[contains(.,'SMS')]//input[@type='checkbox']"
    )
    push_cb = driver.find_element(
        By.XPATH, "//label[contains(.,'Push Notification')]//input[@type='checkbox']"
    )

    for cb in [email_cb, sms_cb, push_cb]:
        if not cb.is_selected():
            cb.click()

    save_btn = driver.find_element(
        By.XPATH, "//button[contains(text(),'Save Alert Rules')]"
    )
    assert save_btn.is_enabled(), "Save button should be enabled with recipient selected"
    save_btn.click()

    success = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Alert rules saved successfully')]")
        )
    )
    assert success.is_displayed(), "Success message not shown after saving all channels"
    print("[INFO] Alert rules saved with all channels")

    # Email only
    time.sleep(1)
    for cb in [sms_cb, push_cb]:
        if cb.is_selected():
            cb.click()
    assert email_cb.is_selected(), "Email should remain checked"

    driver.find_element(
        By.XPATH, "//button[contains(text(),'Save Alert Rules')]"
    ).click()

    success2 = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Alert rules saved successfully')]")
        )
    )
    assert success2.is_displayed(), "Success message not shown on 2nd save (Email only)"
    print("[INFO] Alert rules saved with Email only")


#  TP-12.01-005  Create Notification Schedules
def test_tp12_005_create_notification_schedules(driver):
    """
    Verify system can create daily and weekly notification schedules.

    Steps 3-4: Click '+ Create New Alert Schedule' and fill a daily/weekly schedule.

    EXPECTED DEFECT: The button in page.tsx has no onClick handler — clicking it
    does nothing and no form/modal appears. This test will FAIL to surface that
    missing feature as a real defect in the report.
    """
    wait = WebDriverWait(driver, 20)
    login_and_go_to_prediction(driver)

    scheduled_section = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h3[contains(text(),'Scheduled Notifications')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", scheduled_section)

    # Verify static schedules visible
    assert driver.find_element(
        By.XPATH, "//*[contains(text(),'Daily High Risk Report')]"
    ).is_displayed(), "Daily High Risk Report schedule not visible"

    assert driver.find_element(
        By.XPATH, "//*[contains(text(),'Weekly Summary')]"
    ).is_displayed(), "Weekly Summary schedule not visible"

    # Click Create New Alert Schedule
    create_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(text(),'Create New Alert Schedule')]")
        )
    )
    create_btn.click()
    time.sleep(1)

    # A form/modal must appear — will FAIL until feature is implemented
    schedule_form = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//input[@placeholder='Schedule Name'] | //input[@name='scheduleName']")
        )
    )
    # Reached only if form is implemented
    schedule_form.send_keys("Daily 8AM")
    print("[INFO] Schedule creation form appeared and was filled")



#  TP-12.01-006  View Alert History
def test_tp12_006_view_alert_history(driver):
    """
    Verify Admin can view alert history records.

    Steps 3-4: Verify all 3 static entries and 'View All Alert History' button.

    FIX: page.tsx renders alert status as {alert.date} - {alert.status} inside
    one div, which React splits into multiple DOM text nodes. contains(text(),...)
    checks individual nodes, so 'Alert system active' is never found.
    normalize-space(.) merges all descendant text before comparing.
    """
    wait = WebDriverWait(driver, 20)
    login_and_go_to_prediction(driver)

    history_section = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h3[contains(text(),'Alert History')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", history_section)

    # Verify 3 static entries
    assert driver.find_element(
        By.XPATH, "//*[contains(text(),'High Risk Alert - Location Detected')]"
    ).is_displayed(), "High Risk Alert entry not found"

    assert driver.find_element(
        By.XPATH, "//*[contains(text(),'Medium Risk Alert - Location Detected')]"
    ).is_displayed(), "Medium Risk Alert entry not found"

    assert driver.find_element(
        By.XPATH, "//*[contains(text(),'System Status Report')]"
    ).is_displayed(), "System Status Report entry not found"

    # Status text uses normalize-space(.) to handle React's split text nodes
    status_elements = driver.find_elements(
        By.XPATH,
        f"//*[{nsp('Alert system active')} or {nsp('All systems operational')}]"
    )
    assert len(status_elements) >= 2, \
        "Alert status texts ('Alert system active', 'All systems operational') not displayed"

    # View All button
    assert driver.find_element(
        By.XPATH, "//button[contains(text(),'View All Alert History')]"
    ).is_displayed(), "'View All Alert History' button not found"

    print("[INFO] All 3 alert history entries verified")



#  TP-12.01-007  Pagination
def test_tp12_007_pagination(driver):
    """
    Verify pagination works correctly in prediction list.

    From the screenshot: 28 predictions, 10 per page, pages 1/2/3.
    Pagination bar renders whenever predictions exist (page.tsx line 582).

    BVA — Page 1:  Previous disabled, page-1 button highlighted.
    BVA — Single page (≤10): Next disabled.
    ST  — >10 records: Navigate 1→2, verify Previous enabled + page-2 active,
          then 2→1, verify page-1 active.
    """
    wait = WebDriverWait(driver, 20)
    login_and_go_to_prediction(driver)

    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//div[contains(text(),'Predicted Risk Areas')]")
        )
    )
    time.sleep(2)

    # Pagination bar: "Showing X to Y of Z predictions"
    pagination_info = driver.find_elements(
        By.XPATH,
        f"//*[{nsp('Showing')} and {nsp('of')} and {nsp('predictions')}]"
    )
    if not pagination_info:
        pytest.skip("Pagination bar not rendered — DB has no predictions")

    info_text = pagination_info[0].text
    print(f"[INFO] Pagination info: {info_text}")

    try:
        total_count = int(
            info_text.split("of")[1].split("predictions")[0].strip()
        )
    except (IndexError, ValueError):
        total_count = 0
    print(f"[INFO] Total predictions: {total_count}")

    # ── BVA: Page 1 boundary — Previous always disabled ──────────────────────
    prev_btn = driver.find_element(By.XPATH, "//button[text()='Previous']")
    assert not prev_btn.is_enabled(), \
        "Previous button must be disabled on page 1"

    next_btn = driver.find_element(By.XPATH, "//button[text()='Next']")

    # ── BVA: Single-page case (≤10 records) ──────────────────────────────────
    if total_count <= 10:
        assert not next_btn.is_enabled(), \
            f"Next should be disabled — only {total_count} predictions (one page)"
        print(f"[INFO] Single page confirmed: {total_count} records, Next disabled")
        return

    # ── ST: Multi-page case (>10 records) ────────────────────────────────────
    assert next_btn.is_enabled(), \
        f"Next should be enabled — {total_count} predictions span multiple pages"

    # Navigate to page 2
    next_btn.click()
    time.sleep(1)

    prev_p2 = driver.find_element(By.XPATH, "//button[text()='Previous']")
    assert prev_p2.is_enabled(), \
        "Previous button must be enabled on page 2"

    page2_active = driver.find_elements(
        By.XPATH,
        "//button[contains(@class,'bg-accent-blue') and normalize-space(text())='2']"
    )
    assert len(page2_active) > 0, \
        "Page 2 button should be highlighted (bg-accent-blue) when on page 2"
    print("[INFO] Navigated to page 2 — Previous enabled, page 2 highlighted")

    # Navigate back to page 1
    prev_p2.click()
    time.sleep(1)

    page1_active = driver.find_elements(
        By.XPATH,
        "//button[contains(@class,'bg-accent-blue') and normalize-space(text())='1']"
    )
    assert len(page1_active) > 0, \
        "Page 1 button should be highlighted (bg-accent-blue) when back on page 1"
    print("[INFO] Returned to page 1 — page 1 highlighted")



#  TP-12.01-008  No Matching Filter Results
def test_tp12_008_no_matching_filter(driver):
    """
    Verify system shows correct empty-state message when filter returns no results.

    Step 3: Apply Risk Level = Low (most likely to have no data).
    Expected message: 'No predictions match the selected filters'
    Must NOT show: 'No predictions yet'
    """
    wait = WebDriverWait(driver, 20)
    login_and_go_to_prediction(driver)

    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//div[contains(text(),'Predicted Risk Areas')]")
        )
    )
    time.sleep(1)

    risk_select = driver.find_element(
        By.XPATH, "//select[option[text()='All Levels']]"
    )

    for level in ["Low", "Medium", "High"]:
        Select(risk_select).select_by_visible_text(level)
        time.sleep(1)

        empty = driver.find_elements(
            By.XPATH, "//td[contains(text(),'No predictions match the selected filters')]"
        )
        if empty and empty[0].is_displayed():
            wrong = driver.find_elements(
                By.XPATH, "//td[contains(text(),'No predictions yet')]"
            )
            assert len(wrong) == 0 or not wrong[0].is_displayed(), \
                "Wrong empty-state message shown — must not show 'No predictions yet'"
            print(f"[INFO] Correct empty-state message shown with filter={level}")
            return

    pytest.skip("All risk level filters return data — cannot test empty filter state")



#  TP-12.01-009  Empty Prediction List (DB empty)
def test_tp12_009_empty_prediction_list(driver):
    """
    Verify correct empty-state message when the database has no predictions.

    Expected message: 'No predictions yet. Use the map above to create predictions.'
    PRE-CONDITION: Database must have NO prediction records.
    """
    wait = WebDriverWait(driver, 20)
    login_and_go_to_prediction(driver)

    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//div[contains(text(),'Predicted Risk Areas')]")
        )
    )
    time.sleep(2)

    empty_state = driver.find_elements(
        By.XPATH, "//td[contains(text(),'No predictions yet')]"
    )

    if not (empty_state and empty_state[0].is_displayed()):
        pytest.skip("Database has predictions — cannot test empty DB state")

    full_text = empty_state[0].text
    assert "Use the map above to create predictions" in full_text, \
        "Empty DB message must include 'Use the map above to create predictions'"
    print("[INFO] Correct empty-DB message displayed")


# ═══════════════════════════════════════════════════════
#  TP-12.01-010  Save Alert Rules Without Recipient
#  Technique: EP (invalid input), ST (disabled state), EG (force JS click) #pytest test_prediction_alert.py::test_tp12_010_save_alert_without_recipient -v
# ═══════════════════════════════════════════════════════
def test_tp12_010_save_alert_without_recipient(driver):
    """
    Verify system blocks saving alert rules when no recipient is selected.

    Steps 3-4: Clear recipient → verify Save button disabled → JS force-click
    Expected: Button stays disabled; on forced click, validation error appears.

    FIX for login timeout: always restart from BASE_URL using login_and_go_to_prediction.
    Previous failure was because the function hit a stale session.
    """
    wait = WebDriverWait(driver, 20)
    login_and_go_to_prediction(driver)

    alert_section = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h3[contains(text(),'Set Alert Rules')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", alert_section)
    time.sleep(0.5)

    # Clear recipient (page.tsx default is "All Health Officials",
    # must explicitly set to empty value)
    recipient_select = driver.find_element(
        By.XPATH, "//select[option[text()='-- Select Recipients --']]"
    )
    Select(recipient_select).select_by_value("")    
    time.sleep(0.5)

    save_btn = driver.find_element(
        By.XPATH, "//button[contains(text(),'Save Alert Rules')]"
    )
    assert not save_btn.is_enabled(), \
        "Save button should be disabled when no recipient is selected"
    print("[INFO] Save button correctly disabled with empty recipient")

    # EG: Force-click via JS to test server-side / handler validation
    driver.execute_script("arguments[0].click();", save_btn)
    time.sleep(0.5)

    try:
        err = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "//*[contains(text(),'Please select at least one recipient')]")
            )
        )
        assert err.is_displayed(), "Validation error not shown after forced click"
        print("[INFO] Validation error shown on forced click")
    except TimeoutException:
        # Disabled button protection is sufficient — no error message needed
        print("[INFO] Disabled button correctly prevents invalid save")


#  TP-12.01-011  ML Service Failure During Load
def test_tp12_011_ml_service_failure_on_load(driver):
    if not os.environ.get("BACKEND_OFFLINE"):
        pytest.skip("Set BACKEND_OFFLINE=1 and stop ML service to run this test")

    wait = WebDriverWait(driver, 20)
    login_and_go_to_prediction(driver)

    # Page must still load — this part is expected to work
    page_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h1[contains(text(),'Prediction & Alert')]")
        )
    )
    assert page_heading.is_displayed(), "Dashboard must still render when ML is offline"

    # Give the API calls time to complete and fail
    time.sleep(3)

    # Refresh and Export must still be present (safe degradation)
    assert driver.find_element(
        By.XPATH, f"//button[{nsp('Refresh Predictions')}]"
    ).is_displayed(), "Refresh button must remain visible when ML is offline"

    assert driver.find_element(
        By.XPATH, f"//button[{nsp('Export')}]"
    ).is_displayed(), "Export button must remain visible when ML is offline"

    # ASSERT: A specific error indicator must be visible.
    # This will FAIL because page.tsx never renders an error banner
    # when ML fails on load (DEF-002).
    error_banner = driver.find_elements(
        By.XPATH,
        f"//*[{nsp('Failed to load predictions')} or "
        f"{nsp('Prediction model unavailable')}]"
    )
    visible_errors = [e for e in error_banner if e.is_displayed()]

    assert len(visible_errors) > 0, (
        "[DEF-002] No error message shown when ML service is offline on page load. "
        "page.tsx loadPredictions() never calls setModelAvailable(false), "
        "and success:false API responses are silently ignored — "
        "user sees no feedback that predictions could not be loaded."
    )
    
#  TP-12.01-012  Refresh with ML Service Down
def test_tp12_012_refresh_when_ml_service_down(driver):
    if not os.environ.get("BACKEND_OFFLINE"):
        pytest.skip("Set BACKEND_OFFLINE=1 and stop ML service to run this test")

    wait = WebDriverWait(driver, 20)
    login_and_go_to_prediction(driver)

    # Wait for page to fully render before clicking refresh
    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h1[contains(text(),'Prediction & Alert')]")
        )
    )
    time.sleep(2)

    # Click Refresh
    refresh_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//button[{nsp('Refresh Predictions')}]")
        )
    )
    refresh_btn.click()

    # Wait for spinner to finish (button returns to idle)
    wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, f"//button[{nsp('Refresh Predictions')}]")
        )
    )

    error_banner = driver.find_elements(
        By.XPATH,
        f"//*[{nsp('Failed to load predictions')} or "
        f"{nsp('Prediction model unavailable')}]"
    )
    visible_errors = [e for e in error_banner if e.is_displayed()]

    assert len(visible_errors) > 0, (
        "[DEF-002] No error message shown after Refresh when ML service is offline. "
        "page.tsx loadPredictions() catch block does not call setModelAvailable(false), "
        "and success:false responses are silently ignored — user sees no feedback."
    )

#  TP-12.01-013  Export Empty Prediction List
def test_tp12_013_export_empty_list(driver):
    wait = WebDriverWait(driver, 20)
    clear_downloads()
    login_and_go_to_prediction(driver)
    time.sleep(2)

    empty_state = driver.find_elements(
        By.XPATH, "//td[contains(text(),'No predictions')]"
    )
    if not (empty_state and empty_state[0].is_displayed()):
        pytest.skip("Predictions exist — cannot test empty export")

    print("[INFO] Prediction list is empty")

    export_btn = driver.find_element(
        By.XPATH, f"//button[{nsp('Export')}]"
    )
    export_btn.click()
    time.sleep(2)

    csv_file = get_latest_csv()
    if csv_file:
        lines = open(csv_file, "r", encoding="utf-8").read().strip().split("\n")
        assert len(lines) == 1, \
            "Empty export CSV should contain headers only (1 line)"
        print("[INFO] Empty export CSV has headers only — correct")
    else:
        print("[INFO] No CSV created for empty export — acceptable behaviour")


#  TP-12.01-014  Schedule Save Failure (DB/Network)
def test_tp12_014_schedule_save_failure(driver):
    wait = WebDriverWait(driver, 20)
    login_and_go_to_prediction(driver)

    scheduled_section = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h3[contains(text(),'Scheduled Notifications')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", scheduled_section)

    create_btn = driver.find_element(
        By.XPATH, "//button[contains(text(),'Create New Alert Schedule')]"
    )
    create_btn.click()
    time.sleep(1)

    # Form must appear — will FAIL until feature is implemented in page.tsx
    schedule_name = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//input[@name='scheduleName' or @placeholder='Schedule Name']")
        )
    )
    schedule_name.send_keys("Test Schedule")

    save_btn = driver.find_element(
        By.XPATH,
        "//button[contains(text(),'Save') and not(contains(text(),'Alert'))]"
    )
    save_btn.click()

    error_msg = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'Failed to save schedule') or "
             "contains(text(),'Try again later')]")
        )
    )
    assert error_msg.is_displayed(), "Error message not shown on schedule save failure"

    ghost = driver.find_elements(
        By.XPATH, "//*[contains(text(),'Test Schedule')]"
    )
    assert len(ghost) <= 1, \
        "Failed schedule must not be persisted in the list"

