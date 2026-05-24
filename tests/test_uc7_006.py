"""
Test Procedure ID : TP-UC7-006
Objective         : Verify admin can update editable user profile fields;
                    that read-only fields (email, role, company) are protected;
                    that the user list reflects updates immediately; and that
                    update failures are handled gracefully.
Test Cases        : TC-UC7-006
Run               : pytest tests/test_uc7_006.py -v -s
"""

import time
from selenium.webdriver.common.by import By

from conftest import (
    go_to_user_management, get_page_source, get_alert_text,
    wait_clickable, wait_visible,
)

TARGET_EMAIL    = "ali@gmail.com"
UPDATED_NAME    = "Ali Abu"
UPDATED_PHONE   = "0181234567"
UPDATED_ADDRESS = "Kuala Lumpur"


def open_edit_modal(driver, email=TARGET_EMAIL):
    """
    Navigate to User Management and click the pencil/edit button
    on the row belonging to <email>.
    """
    go_to_user_management(driver)
    time.sleep(2)

    # Click the edit (pencil) button inside the target user's row
    # HTML: <button title="Edit"> or button with FiEdit2 icon inside the row
    edit_btn = wait_clickable(
        driver,
        By.XPATH,
        f"//tr[contains(., '{email}')]//button[@title='Edit' or @aria-label='Edit'] | "
        f"//tr[contains(., '{email}')]//button[last()-1]",   # fallback: 2nd-last button (edit before delete)
        timeout=10,
    )
    edit_btn.click()
    time.sleep(2)


def get_edit_modal(driver):
    """Return the edit modal container — identified by 'Update User' button."""
    return wait_visible(
        driver,
        By.XPATH,
        "//button[normalize-space(.)='Update User']/ancestor::div"
        "[contains(@class,'bg-white')]",
        timeout=10,
    )


class TestTP_UC7_006:
    """TP-UC7-006 — Edit User Profile"""

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-006 Step 1
    # Input   : Open ali@gmail.com edit modal
    # Expected: Email, Role, Company are rendered as <div> (not editable inputs).
    # ──────────────────────────────────────────────────────────────────────────
    def test_readonly_fields_are_protected(self, driver):
        try:
            open_edit_modal(driver)
            modal = get_edit_modal(driver)

            # ── Email, Role, Company are <div class="bg-gray-100 ..."> ────
            # They are NOT <input> elements — confirm no editable input exists
            # for these fields inside the modal.
            for field_placeholder in (
                "Enter full name",    # editable  — should EXIST as input
            ):
                modal.find_element(
                    By.XPATH,
                    f".//input[@placeholder='{field_placeholder}']",
                )  # just confirm editable fields are inputs

            # Confirm email is a div (read-only), not an input
            email_inputs = modal.find_elements(
                By.XPATH,
                ".//input[@type='email' or @placeholder[contains(.,'email')"
                " or contains(.,'Email')]]",
            )
            assert len(email_inputs) == 0, (
                "Email field is rendered as an <input> — it should be a read-only <div>."
            )

            # Confirm role is a div (read-only), not a select or input
            role_inputs = modal.find_elements(
                By.XPATH,
                ".//input[contains(@placeholder,'role') or contains(@placeholder,'Role')] | "
                ".//select[contains(@name,'role') or contains(@id,'role')]",
            )
            assert len(role_inputs) == 0, (
                "Role field is editable — it should be a read-only <div>."
            )

            # Confirm company is a div (read-only), not an input
            company_inputs = modal.find_elements(
                By.XPATH,
                ".//input[contains(@placeholder,'company') or contains(@placeholder,'Company')]",
            )
            assert len(company_inputs) == 0, (
                "Company field is editable — it should be a read-only <div>."
            )

            print("✅ TC-UC7-006 Step 1 | Read-Only Fields Protected — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-006 Step 1 | Read-Only Fields Protected — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-006 Step 2
    # Input   : Full Name → 'Ali Abu', Phone → '0181234567',
    #           Address → 'Kuala Lumpur'
    # Expected: Profile saved; new values visible; read-only fields unchanged.
    # ──────────────────────────────────────────────────────────────────────────
    def test_update_editable_fields(self, driver):
        try:
            open_edit_modal(driver)
            modal = get_edit_modal(driver)

            # ── Full Name ─────────────────────────────────────────────────
            # HTML: <input type="text" placeholder="Enter full name" ...>
            name_input = modal.find_element(
                By.XPATH, ".//input[@placeholder='Enter full name']"
            )
            name_input.clear()
            name_input.send_keys(UPDATED_NAME)

            # ── Phone ─────────────────────────────────────────────────────
            # HTML: <input type="tel" placeholder="Enter phone number" ...>
            phone_input = modal.find_element(
                By.XPATH, ".//input[@placeholder='Enter phone number']"
            )
            phone_input.clear()
            phone_input.send_keys(UPDATED_PHONE)

            # ── Address ───────────────────────────────────────────────────
            # HTML: <input type="text" placeholder="Enter address" ...>
            address_input = modal.find_element(
                By.XPATH, ".//input[@placeholder='Enter address']"
            )
            address_input.clear()
            address_input.send_keys(UPDATED_ADDRESS)

            # ── Click 'Update User' ───────────────────────────────────────
            # HTML: <button onClick={handleUpdateProfile}>Update User</button>
            update_btn = modal.find_element(
                By.XPATH, ".//button[normalize-space(.)='Update User']"
            )
            update_btn.click()
            time.sleep(3)   # wait for API call + modal close animation

            # ── Modal should close — verify via page source ───────────────
            page = get_page_source(driver)

            # Check success alert or updated name in list
            alert = get_alert_text(driver)
            success = (
                (alert and any(
                    kw in alert.lower()
                    for kw in ("success", "updated", "saved")
                ))
                or UPDATED_NAME.lower() in page
                or "success" in page
            )
            assert success, (
                f"No confirmation that profile was updated to '{UPDATED_NAME}'."
            )

            print("✅ TC-UC7-006 Step 2 | Update Editable Fields — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-006 Step 2 | Update Editable Fields — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-006 Step 3
    # Input   : Return to User Management list (no manual refresh)
    # Expected: List immediately shows 'Ali Abu'.
    # ──────────────────────────────────────────────────────────────────────────
    def test_user_list_reflects_update_immediately(self, driver):
        try:
            # Modal closes after save — user should already be on the list page
            # Navigate fresh to confirm no manual refresh needed
            go_to_user_management(driver)
            time.sleep(3)

            # get_page_source returns lowercased source
            page = get_page_source(driver)
            assert UPDATED_NAME.lower() in page, (
                f"User list does not show updated name '{UPDATED_NAME}' "
                f"after navigating back without manual refresh."
            )

            print("✅ TC-UC7-006 Step 3 | User List Reflects Update — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-006 Step 3 | User List Reflects Update — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-006 Step 4
    # Input   : Attempt update while server/DB is down
    # Expected: Graceful error message shown; data not corrupted.
    # NOTE    : Stop DB container manually before running this step.
    #           docker stop <db_container_name>
    # ──────────────────────────────────────────────────────────────────────────
    def test_update_fails_gracefully_on_server_error(self, driver):
        try:
            open_edit_modal(driver)
            modal = get_edit_modal(driver)

            # Make a small change to trigger save
            name_input = modal.find_element(
                By.XPATH, ".//input[@placeholder='Enter full name']"
            )
            name_input.clear()
            name_input.send_keys("Trigger Error")

            update_btn = modal.find_element(
                By.XPATH, ".//button[normalize-space(.)='Update User']"
            )
            update_btn.click()
            time.sleep(3)

            page = get_page_source(driver)
            error_shown = any(
                kw in page
                for kw in (
                    "error", "failed", "could not", "unable",
                    "something went wrong", "try again", "server",
                )
            )
            assert error_shown, (
                "No error message shown when update attempted during server downtime."
            )

            # Email must still be present — confirms no data corruption
            assert TARGET_EMAIL.lower() in page, (
                "Target user email missing after failed update — possible data corruption."
            )

            print("✅ TC-UC7-006 Step 4 | Graceful Error on Server Failure — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-006 Step 4 | Graceful Error on Server Failure — FAIL ({e})")
            assert False