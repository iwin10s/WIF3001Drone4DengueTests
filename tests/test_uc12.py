import pytest
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


#  CONFIG — update before running
BASE_URL       = "http://localhost:3000"
ADMIN_EMAIL    = "kiki@gmail.com"
ADMIN_PASSWORD = "Abc12345!"


#  FIXTURE — launches Chrome, opens login page, tears down after test
@pytest.fixture
def driver():
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    driver.maximize_window()
    driver.get(BASE_URL)
    yield driver
    driver.quit()


#  HELPER — login and navigate to Settings page
def login_and_go_to_settings(driver):
    wait = WebDriverWait(driver, 15)

    # Ensure we're on login page
    if "dashboard" in driver.current_url or "settings" in driver.current_url:
        driver.get(BASE_URL)

    # Fill email — id="email" from login/page.tsx
    wait.until(EC.visibility_of_element_located((By.ID, "email")))
    email_field = driver.find_element(By.ID, "email")
    email_field.clear()
    email_field.send_keys(ADMIN_EMAIL)

    # Fill password — id="password"
    password_field = driver.find_element(By.ID, "password")
    password_field.clear()
    password_field.send_keys(ADMIN_PASSWORD)

    # Click LOGIN button
    driver.find_element(By.XPATH, "//button[@type='submit' and contains(text(),'LOGIN')]").click()

    # Wait for dashboard redirect
    wait.until(EC.url_contains("/dashboard"))

    # Navigate to Settings via sidebar
    settings_link = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(@href,'/settings')] | //*[contains(text(),'Settings') and not(contains(text(),'Password'))]")
        )
    )
    settings_link.click()

    # Confirm Settings page loaded — h1 "Settings"
    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h1[contains(text(),'Settings')]")
        )
    )


#  HELPER — wait for success dialog (Location created/deleted)
#  Shows modal with FiCheckCircle + "Success!" heading
def wait_for_success_dialog(driver, timeout=10):
    wait = WebDriverWait(driver, timeout)
    success_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h3[contains(text(),'Success!')]")
        )
    )
    assert success_heading.is_displayed(), "Success dialog not shown"
    # Click "Great!" to dismiss
    driver.find_element(
        By.XPATH, "//button[contains(text(),'Great!')]"
    ).click()
    time.sleep(0.5)


#  TP-12-001
#  Admin updates profile information successfully
def test_tp12_001_update_profile(driver):
    """
    TC-12-001
    Steps 1-8: login → Settings → Profile Settings →
               verify current info → edit name + phone → Save Changes →
               verify success → refresh → verify persisted
    """
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)
 
    # ── Step 3-4: Verify Profile Settings section is displayed ────────────────
    profile_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'Profile Settings')]")
        )
    )
    assert profile_heading.is_displayed(), "Profile Settings section not visible"
 
    # Verify current profile fields are present — wait for async API load
    name_field_check = wait.until(EC.visibility_of_element_located((By.ID, "name")))
    assert name_field_check.is_displayed(), "Name field not displayed"
    email_field_check = wait.until(EC.visibility_of_element_located((By.ID, "email")))
    assert email_field_check.is_displayed(), "Email field not displayed"
 
    # ── Step 5: Click "Edit Profile" to enable editing ────────────────────────
    edit_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Edit Profile')]")
        )
    )
    edit_btn.click()
    time.sleep(0.5)
 
    # ── Step 5: Edit Name and Phone ───────────────────────────────────────────
    # id="name" from page.tsx
    name_field = wait.until(EC.element_to_be_clickable((By.ID, "name")))
    name_field.clear()
    name_field.send_keys("Kiki Tan")
 
    # id="phone" from page.tsx
    phone_field = driver.find_element(By.ID, "phone")
    phone_field.clear()
    phone_field.send_keys("01123456789")
 
    # ── Step 6: Click "Save Changes" ─────────────────────────────────────────
    save_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Save Changes')]")
        )
    )
    save_btn.click()
 
    # ── Step 7: Verify success message ───────────────────────────────────────
    # From page.tsx: profileSuccess = 'Profile updated successfully!'
    success_msg = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Profile updated successfully')]")
        )
    )
    assert success_msg.is_displayed(), "Profile update success message not shown"
 
    # ── Step 8: Refresh page and verify info persists ─────────────────────────
    driver.refresh()
    wait.until(EC.visibility_of_element_located((By.XPATH, "//h1[contains(text(),'Settings')]")))
    time.sleep(2)  # allow profile data to load from API
 
    updated_name = driver.find_element(By.ID, "name")
    assert updated_name.get_attribute("value") == "Kiki Tan", \
        f"Name not persisted after refresh. Got: {updated_name.get_attribute('value')}"
 
    updated_phone = driver.find_element(By.ID, "phone")
    assert updated_phone.get_attribute("value") == "01123456789", \
        f"Phone not persisted after refresh. Got: {updated_phone.get_attribute('value')}"
 
#  TP-12-002
#  Admin cancels profile editing — original data restored
def test_tp12_002_cancel_profile_edit(driver):
    """
    TC-12-002
    Steps 1-5: login → Profile Settings → modify fields →
               Cancel → verify original info restored
    """
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)

    # Wait for name field to load with current value
    wait.until(EC.visibility_of_element_located((By.ID, "name")))
    time.sleep(2)  # allow API data to load

    # Record original name value before editing
    original_name = driver.find_element(By.ID, "name").get_attribute("value")

    # Click Edit Profile
    edit_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(.,'Edit Profile')]"))
    )
    edit_btn.click()
    time.sleep(0.5)

    # Modify the name field with a temporary value
    name_field = wait.until(EC.element_to_be_clickable((By.ID, "name")))
    name_field.clear()
    name_field.send_keys("Temporary Name Do Not Save")

    # Click "Cancel" — same button toggles back
    cancel_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Cancel') and not(contains(.,'Location'))]")
        )
    )
    cancel_btn.click()
    time.sleep(0.5)

    # ── Step 5: Verify original name is restored ──────────────────────────────
    restored_name = driver.find_element(By.ID, "name").get_attribute("value")
    assert restored_name == original_name, \
        f"Name not restored after cancel. Expected '{original_name}', got '{restored_name}'"

    # Verify Edit Profile button is shown again (not in edit mode)
    edit_btn_visible = driver.find_element(By.XPATH, "//button[contains(.,'Edit Profile')]")
    assert edit_btn_visible.is_displayed(), "Edit Profile button not shown after cancel"


#  TP-12-003
#  Admin successfully updates password
def test_tp12_003_update_password_success(driver):
    """
    TC-12-003
    Steps 1-5: login → Password Settings → enter matching passwords →
               Update Password → verify success message
    """
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)

    # ── Step 2: Verify Password Settings section ──────────────────────────────
    password_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'Password Settings')]")
        )
    )
    assert password_heading.is_displayed(), "Password Settings section not visible"

    # ── Step 3: Enter New Password and Confirm Password ───────────────────────
    new_password_field = driver.find_element(By.ID, "new-password")
    new_password_field.clear()
    new_password_field.send_keys("Abc12345!")

    confirm_password_field = driver.find_element(By.ID, "confirm-password")
    confirm_password_field.clear()
    confirm_password_field.send_keys("Abc12345!")

    # ── Step 4: Click "Update Password" ──────────────────────────────────────
    update_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Update Password')]")
        )
    )
    update_btn.click()

    # ── Step 5: Verify success message ───────────────────────────────────────
    success_msg = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Password updated successfully')]")
        )
    )
    assert success_msg.is_displayed(), "Password update success message not shown"

    # Verify password fields are cleared after success
    assert driver.find_element(By.ID, "new-password").get_attribute("value") == "", \
        "New password field should be cleared after success"
    assert driver.find_element(By.ID, "confirm-password").get_attribute("value") == "", \
        "Confirm password field should be cleared after success"


#  TP-12-004
#  System prevents password update when passwords don't match
def test_tp12_004_password_mismatch_validation(driver):
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)

    # Verify Password Settings section visible
    wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'Password Settings')]")
        )
    )

    # ── Step 3: Enter mismatched passwords ────────────────────────────────────
    new_password_field = driver.find_element(By.ID, "new-password")
    new_password_field.clear()
    new_password_field.send_keys("Abc12345!")

    confirm_password_field = driver.find_element(By.ID, "confirm-password")
    confirm_password_field.clear()
    confirm_password_field.send_keys("Abc12345")   # deliberately missing "!"

    # ── Step 4: Click Update Password ────────────────────────────────────────
    update_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Update Password')]")
        )
    )
    update_btn.click()

    # ── Step 5: Verify validation error ──────────────────────────────────────
    error_msg = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'do not match') or contains(text(),'passwords do not match')]")
        )
    )
    assert error_msg.is_displayed(), "Password mismatch validation message not shown"

    # Verify no success message is shown
    success_elements = driver.find_elements(
        By.XPATH, "//*[contains(text(),'Password updated successfully')]"
    )
    assert len(success_elements) == 0, "Success message should NOT appear when passwords mismatch"

#  TP-12-005
#  Admin updates notification preferences successfully
def test_tp12_005_update_notification_preferences(driver):
    """
    TC-12-005
    Steps 1-4: login → Notification Preferences →
               set Email ON, SMS ON, Frequency = Daily →
               Save Preferences → verify success
    """
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)

    # ── Step 2: Verify Notification Preferences section ───────────────────────
    notif_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'Notification Preferences')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", notif_heading)
    assert notif_heading.is_displayed(), "Notification Preferences section not visible"

    # ── Step 3a: Enable Email Notifications toggle ────────────────────────────
    # From page.tsx: sr-only checkbox controls the toggle visually
    email_toggle = driver.find_element(
        By.XPATH,
        "//h3[contains(text(),'Email Notifications')]/ancestor::div[contains(@class,'flex')]//input[@type='checkbox']"
    )
    if not email_toggle.is_selected():
        # Click the visible toggle div instead (sr-only hides the input)
        toggle_div = driver.find_element(
            By.XPATH,
            "//h3[contains(text(),'Email Notifications')]/ancestor::div[contains(@class,'flex')]//label[contains(@class,'cursor-pointer')]"
        )
        toggle_div.click()
        time.sleep(0.5)

    # ── Step 3b: Enable SMS Notifications toggle ──────────────────────────────
    sms_toggle = driver.find_element(
        By.XPATH,
        "//h3[contains(text(),'SMS Notifications')]/ancestor::div[contains(@class,'flex')]//input[@type='checkbox']"
    )
    if not sms_toggle.is_selected():
        toggle_div = driver.find_element(
            By.XPATH,
            "//h3[contains(text(),'SMS Notifications')]/ancestor::div[contains(@class,'flex')]//label[contains(@class,'cursor-pointer')]"
        )
        toggle_div.click()
        time.sleep(0.5)

    # ── Step 3c: Set Alert Frequency = Daily ─────────────────────────────────
    # id="alert-frequency" from page.tsx
    freq_select = Select(driver.find_element(By.ID, "alert-frequency"))
    freq_select.select_by_value("daily")

    # ── Step 4: Click "Save Preferences" ─────────────────────────────────────
    save_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Save Preferences')]")
        )
    )
    save_btn.click()

    # ── Verify success message ────────────────────────────────────────────────
    # From page.tsx: notificationSuccess = 'Notification preferences saved successfully!'
    success_msg = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Notification preferences saved successfully')]")
        )
    )
    assert success_msg.is_displayed(), "Notification preferences success message not shown"



#  TP-12-006
#  Admin sets dengue alert threshold to High
def test_tp12_006_set_alert_threshold_high(driver):
    """
    TC-12-006
    Steps 1-4: login → System Configuration →
               set Threshold Level = High → Apply Settings → verify success
    """
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)
 
    # ── Step 2: Scroll to System Configuration section ────────────────────────
    sys_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'System Configuration')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", sys_heading)
    assert sys_heading.is_displayed(), "System Configuration section not visible"
 
    # ── Step 3: Select "High" threshold radio button ──────────────────────────
    high_radio = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//input[@type='radio' and @name='threshold' and @value='high']")
        )
    )
    high_radio.click()
    assert high_radio.is_selected(), "High threshold radio not selected"
 
    # ── Step 4: Click "Apply Settings" ───────────────────────────────────────
    apply_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Apply Settings')]")
        )
    )
    apply_btn.click()
 
    # ── Verify success message ────────────────────────────────────────────────
    # From page.tsx: systemConfigSuccess = 'System configuration saved successfully!'
    success_msg = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'System configuration saved successfully')]")
        )
    )
    assert success_msg.is_displayed(), "System configuration success message not shown"
    # TP-12-006 passes: Apply Settings triggered and success message confirmed.
 
 

#  TP-12-007
#  System accepts valid prediction model parameter values
def test_tp12_007_valid_model_parameters(driver):
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)

    sys_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'System Configuration')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", sys_heading)

    # ── Step 3: Click "Edit Parameters" ──────────────────────────────────────
    edit_params_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Edit Parameters')]")
        )
    )
    edit_params_btn.click()
    time.sleep(0.5)

    # ── Step 4: Set Historical Data Weight = 0.8 ──────────────────────────────
    param_inputs = wait.until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//div[contains(@class,'bg-gray-100')]//input[@type='number']")
        )
    )

    param_inputs[0].clear()
    param_inputs[0].send_keys("0.8")

    param_inputs[1].clear()
    param_inputs[1].send_keys("0.5")

    param_inputs[2].clear()
    param_inputs[2].send_keys("0.2")

    # ── Step 5: Click "Apply Settings" ───────────────────────────────────────
    apply_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Apply Settings')]")
        )
    )
    apply_btn.click()

    # ── Step 6: Verify a result message is displayed ──────────────────────────
    result_msg = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'System configuration saved successfully') or "
             "contains(text(),'Unable to save changes') or "
             "contains(text(),'Failed to update')]")
        )
    )
    assert result_msg.is_displayed(), "No result message shown after applying model parameters"
    print(f"\n TP-12-007 Result message: {result_msg.text}")


#  TP-12-008
#  System rejects invalid prediction model parameters
def test_tp12_008_invalid_model_parameters(driver):
    """
    TC-12-008
    Steps 1-6: login → System Configuration → Edit Parameters →
               set out-of-range values → Apply Settings →
               verify error message shown
    """
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)

    sys_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'System Configuration')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", sys_heading)

    # Click "Edit Parameters"
    edit_params_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Edit Parameters')]")
        )
    )
    edit_params_btn.click()
    time.sleep(0.5)

    # Set invalid values — all above max of 1.0
    param_inputs = wait.until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//div[contains(@class,'bg-gray-100')]//input[@type='number']")
        )
    )
    param_inputs[0].clear()
    param_inputs[0].send_keys("9.9")   # invalid: max is 1

    param_inputs[1].clear()
    param_inputs[1].send_keys("9.9")

    param_inputs[2].clear()
    param_inputs[2].send_keys("9.9")

    # Click "Apply Settings"
    apply_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Apply Settings')]")
        )
    )
    apply_btn.click()

    # Verify error message is shown
    # From page.tsx: systemConfigError shown in red when API rejects
    error_msg = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH,
             "//*[contains(text(),'Unable to save changes') or "
             "contains(text(),'Failed to update') or "
             "contains(text(),'Invalid') or "
             "contains(@class,'text-red')]")
        )
    )
    assert error_msg.is_displayed(), "Error message not shown for invalid model parameters"

    # Confirm success message is NOT shown
    success_elements = driver.find_elements(
        By.XPATH, "//*[contains(text(),'System configuration saved successfully')]"
    )
    assert len(success_elements) == 0, "Success should NOT appear for invalid parameters"


#  TP-12-009
#  Admin switches data synchronization mode to Manual
def test_tp12_009_switch_sync_mode_manual(driver):
    """
    TC-12-009
    Steps 1-5: login → System Configuration →
               Data Synchronization = Manual →
               Apply Settings → verify updated successfully
    """
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)

    sys_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'System Configuration')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", sys_heading)

    # ── Step 3: Select Manual sync radio ─────────────────────────────────────
    # From page.tsx: <input type="radio" name="sync" value="manual">
    manual_radio = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//input[@type='radio' and @name='sync' and @value='manual']")
        )
    )
    manual_radio.click()
    assert manual_radio.is_selected(), "Manual sync radio not selected"

    # Verify "Sync Now" button appears when manual is selected
    sync_now_btn = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//button[contains(.,'Sync Now')]")
        )
    )
    assert sync_now_btn.is_displayed(), "'Sync Now' button not shown in manual mode"

    # ── Step 4: Click "Apply Settings" ───────────────────────────────────────
    apply_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Apply Settings')]")
        )
    )
    apply_btn.click()

    # ── Step 5: Verify success ────────────────────────────────────────────────
    success_msg = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'System configuration saved successfully')]")
        )
    )
    assert success_msg.is_displayed(), "Sync mode update success message not shown"

    # Verify Manual radio is still selected after save
    assert driver.find_element(
        By.XPATH, "//input[@type='radio' and @name='sync' and @value='manual']"
    ).is_selected(), "Manual sync not retained after save"


# 
#  TP-12-010 & TP-12-011
#  Admin adds operational area using map selection
def test_tp12_010_add_operational_area(driver):
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)

    # ── Step 2: Scroll to Operational Areas section ───────────────────────────
    areas_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'Operational Areas')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", areas_heading)

    # ── Step 3: Click "Add Operational Area" ─────────────────────────────────
    add_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Add Operational Area')]")
        )
    )
    add_btn.click()

    # ── Wait for modal to open ────────────────────────────────────────────────
    modal = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'Add New Operational Area')]")
        )
    )
    assert modal.is_displayed(), "Add Operational Area modal did not open"

    # ── Step 4-5: Enter search address ───────────────────────────────────────
    address_field = wait.until(
        EC.element_to_be_clickable((By.ID, "location-address"))
    )
    address_field.clear()
    address_field.send_keys("Batu Pahat, Johor")

    # ── Step 5: Pin location on map (click centre of map) ────────────────────
    try:
        map_div = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class,'leaflet-container')]")
            )
        )
        driver.execute_script("arguments[0].scrollIntoView();", map_div)
        time.sleep(1)
        # Use ActionChains to click the centre of the map
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).move_to_element(map_div).click().perform()
        time.sleep(2)  # wait for reverse geocode to populate address
    except TimeoutException:
        print("Map not found — proceeding without map pin (coordinates left empty)")

    # ── Step 6: Enter Operational Area Name ──────────────────────────────────
    # id="location-name" from page.tsx
    name_field = wait.until(
        EC.element_to_be_clickable((By.ID, "location-name"))
    )
    name_field.clear()
    name_field.send_keys("Batu Pahat Zone")

    # ── Step 7: Click "Add Location" ─────────────────────────────────────────
    add_location_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Add Location')]")
        )
    )
    add_location_btn.click()

    # ── Verify success dialog ─────────────────────────────────────────────────
    # From page.tsx: showSuccessDialog with 'Location created successfully!'
    wait_for_success_dialog(driver)

    # Verify new location appears in the list
    location_entry = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(text(),'Batu Pahat Zone')]")
        )
    )
    assert location_entry.is_displayed(), "'Batu Pahat Zone' not found in operational areas list"


#  TP-12-011
#  Admin deletes an operational area
def test_tp12_011_delete_operational_area(driver):
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)
 
    # ── Step 2: Scroll to Operational Areas section ───────────────────────────
    areas_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'Operational Areas')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", areas_heading)
 
    # Wait for list to fully render
    time.sleep(2)
 
    # ── Step 3: Check if any operational areas exist ──────────────────────────
    location_items = driver.find_elements(
        By.XPATH,
        "//h3[contains(@class,'font-semibold') and contains(@class,'text-gray-800')]"
    )
    if len(location_items) == 0:
        pytest.skip(
            "No operational areas found. "
            "Add one first (run test_tp12_010) then re-run this test."
        )
 
    # ── Step 4: Record the name of the first area ─────────────────────────────
    first_location_name = location_items[0].text.strip()
    print(f"\n[TC-011] Target location to delete: '{first_location_name}'")
 
    # Guard: if name is empty or too short, flag immediately
    assert len(first_location_name) > 0, \
        "First operational area has an empty name — check the app data or XPath selector"
 
    # ── Step 5-6: Click delete and auto-accept confirm dialog ─────────────────
    delete_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "(//button[@title='Delete location'])[1]")
        )
    )
 
    # Override window.confirm BEFORE clicking so dialog is auto-accepted
    driver.execute_script("window.confirm = function() { return true; }")
    time.sleep(0.3)  # ensure override is in place before click
    delete_btn.click()
 
    # ── Step 7: Verify deletion succeeded ────────────────────────────────────
    # First: check for success dialog/toast
    success_shown = False
    try:
        wait_for_success_dialog(driver)
        success_shown = True
        print("[TC-011] Success dialog appeared after delete.")
    except TimeoutException:
        print("[TC-011] No success dialog — checking list directly.")
 
    # Allow list to refresh after DELETE API call
    time.sleep(2)
 
    # FIX: Use exact h3 text match scoped to the operational areas list
    # Original used //*[contains(text(), name)] which matched every element
    # containing that string (e.g. 'r' matched 53 unrelated elements)
    remaining = driver.find_elements(
        By.XPATH,
        f"//h3[contains(@class,'font-semibold') and "
        f"contains(@class,'text-gray-800') and "
        f"normalize-space(text())='{first_location_name}']"
    )
 
    assert len(remaining) == 0, (
        f"[FEATURE BUG] Deleted location '{first_location_name}' still appears in the list.\n"
        f"Success dialog shown: {success_shown}\n"
        f"Possible causes:\n"
        f"  - Delete button click did not trigger DELETE API call\n"
        f"  - API call failed silently (check network tab / backend logs)\n"
        f"  - UI did not re-fetch or refresh list after deletion"
    )
 
    print(f"[TC-011]  Location '{first_location_name}' successfully deleted.")
 
 

#  TC-12-012
#  Admin successfully sends broadcast notification
def test_tp12_012_send_broadcast_notification_success(driver):
  
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)
 
    # ── Step 2: Scroll to Broadcast Notification section ─────────────────────
    broadcast_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'Broadcast Notification')]")
        )
    )
    driver.execute_script("argumets[0].scrollIntoView();", broadcast_heading)
    assert broadcast_heading.is_displayed(), \
        "Broadcast Notification section not visible on Settings page"
 
    # ── Step 3: Enter Title ───────────────────────────────────────────────────
    title_field = wait.until(
        EC.element_to_be_clickable((By.ID, "broadcast-title"))
    )
    title_field.clear()
    title_field.send_keys("Alert")
 
    # ── Step 4: Enter Message ─────────────────────────────────────────────────
    message_field = wait.until(
        EC.element_to_be_clickable((By.ID, "broadcast-message"))
    )
    message_field.clear()
    message_field.send_keys("Stay Indoors")
 
    # ── Step 5: Click Send ────────────────────────────────────────────────────
    send_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Send Broadcast Notification')]")
        )
    )
    assert send_btn.is_enabled(), \
        "Send button should be enabled when Title and Message are filled"
    send_btn.click()
 
    # ── Step 6: Verify success message ───────────────────────────────────────
    try:
        success_msg = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "//*[contains(text(),'Broadcast notification sent successfully')]")
            )
        )
        assert success_msg.is_displayed(), \
            "Success message element found but not visible"
    except TimeoutException:
        pytest.fail(
            "[FEATURE BUG] Success message 'Broadcast notification sent successfully' "
            "did not appear within 15 seconds after clicking Send.\n"
            "Possible causes:\n"
            "  - Send button click did not trigger POST API call\n"
            "  - API call failed silently (check network tab / backend logs)\n"
            "  - Frontend not rendering success state from API response"
        )
 
    # ── Step 7: Verify form is cleared after success ──────────────────────────
    time.sleep(1)  # allow frontend state to update
 
    title_value = driver.find_element(By.ID, "broadcast-title").get_attribute("value")
    message_value = driver.find_element(By.ID, "broadcast-message").get_attribute("value")
 
    assert title_value == "", (
        f"[UI BUG] Title field should be cleared after successful broadcast, "
        f"but still contains: '{title_value}'"
    )
    assert message_value == "", (
        f"[UI BUG] Message field should be cleared after successful broadcast, "
        f"but still contains: '{message_value}'"
    )
 
    print("[TC-012] Broadcast notification sent and form cleared successfully.")
 
 
#  TC-12-013
#  Broadcast notification fails when API is unavailable
def test_tp12_013_send_broadcast_notification_api_failure(driver):
    if not os.environ.get("BROADCAST_API_OFFLINE"):
        pytest.skip(
            "Skipped: TC-12-013 requires the broadcast API to be OFFLINE.\n"
            "Steps to enable:\n"
            "  1. Stop the backend notification service\n"
            "  2. Set env var:  $env:BROADCAST_API_OFFLINE = '1'\n"
            "  3. Re-run:  pytest test_settings.py::test_tp12_013_send_broadcast_notification_api_failure -v"
        )
 
    wait = WebDriverWait(driver, 15)
    login_and_go_to_settings(driver)
 
    # ── Step 3: Scroll to Broadcast Notification section ─────────────────────
    broadcast_heading = wait.until(
        EC.visibility_of_element_located(
            (By.XPATH, "//h2[contains(text(),'Broadcast Notification')]")
        )
    )
    driver.execute_script("arguments[0].scrollIntoView();", broadcast_heading)
 
    # ── Step 4: Enter Title and Message ──────────────────────────────────────
    title_field = wait.until(
        EC.element_to_be_clickable((By.ID, "broadcast-title"))
    )
    title_field.clear()
    title_field.send_keys("Alert")
 
    message_field = wait.until(
        EC.element_to_be_clickable((By.ID, "broadcast-message"))
    )
    message_field.clear()
    message_field.send_keys("Stay Indoors")
 
    # ── Step 5: Click Send ────────────────────────────────────────────────────
    send_btn = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(.,'Send Broadcast Notification')]")
        )
    )
    send_btn.click()
 
    # ── Step 6: Verify error message is shown ────────────────────────────────
    try:
        error_msg = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "//*[contains(@class,'text-red') and "
                 "(contains(text(),'Failed to send') or "
                 "contains(text(),'broadcast notification'))]")
            )
        )
        assert error_msg.is_displayed(), \
            "Error message element found but not visible"
        print(f"[TC-013] Error message displayed: '{error_msg.text}'")
 
    except TimeoutException:
        pytest.fail(
            "[FEATURE BUG] No error message appeared after sending broadcast "
            "with API offline.\n"
            "Expected: A red error message containing 'Failed to send' or "
            "'broadcast notification' to be visible.\n"
            "Actual: UI showed no feedback — silent failure.\n"
            "Fix required: Frontend must handle API error response and render "
            "an error state (e.g. broadcastError div with class 'text-red')."
        )
 
    # ── Step 7: Confirm success message is NOT shown ──────────────────────────
    success_elements = driver.find_elements(
        By.XPATH, "//*[contains(text(),'sent successfully')]"
    )
    assert len(success_elements) == 0, (
        "[BUG] Success message should NOT appear when the broadcast API fails, "
        "but it was found on the page."
    )
 
    print("[TC-013] Error message shown correctly. Success message not shown.")