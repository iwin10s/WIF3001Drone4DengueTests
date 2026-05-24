"""
Test Procedure ID : TP-UC7-009
Objective         : Verify admin can permanently delete a user account,
                    cancel a pending deletion without data loss, and that the
                    system prevents an admin from deleting their own account.
Test Cases        : TC-UC7-010
Run               : pytest test_TP_UC7_009.py::TestTP_UC7_009 -v -s

CONFIRMED FROM SOURCE:
  Row delete button — icon-only (<FiTrash2>), NO title/aria-label/text.
    className: "p-2 rounded-lg hover:bg-red-50 text-red-500 transition-colors"
    → Located by: contains(@class,'text-red-500')

  Edit button (different, must NOT match):
    className: "p-2 rounded-lg hover:bg-light-bg/50 text-accent-blue ..."
    → Uses text-accent-blue, so text-red-500 selector is unambiguous.

  Confirm dialog button texts:
    Single delete : confirmText="Delete",     cancelText="Cancel"
    Bulk delete   : confirmText="Delete All", cancelText="Cancel"

  Success feedback: React dialog ("User deleted successfully."), NOT JS alert.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from conftest import (
    ADMIN_EMAIL,
    go_to_user_management, get_page_source, get_alert_text,
    wait_clickable, wait_visible,
    get_search_input, clear_and_type,
)

DELETE_EMAIL = "deleteuser@gmail.com"

# ── Exact locators from source ────────────────────────────────────────────────

# Icon-only delete button — uniquely identified by text-red-500 class
_ROW_DELETE_BTN = "//button[contains(@class,'text-red-500')]"

# Scoped to a specific user row
def _row_delete_xpath(email):
    return (
        f"//tr[.//td[contains(normalize-space(.),'{email}')]]"
        f"//button[contains(@class,'text-red-500')]"
    )

# Confirmation dialog buttons (from confirmText/cancelText in source)
_DIALOG_DELETE = (By.XPATH,
    "//button[normalize-space(.)='Delete']"
    " | //button[normalize-space(.)='Delete All']"
)
_DIALOG_CANCEL = (By.XPATH, "//button[normalize-space(.)='Cancel']")

# React success dialog keywords (from setSuccessDialogMessage)
_SUCCESS_KEYWORDS = ("deleted successfully", "deleted", "success")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _search_user(driver, email):
    """Filter the table to one row by typing the email in the search box."""
    search = get_search_input(driver)
    clear_and_type(search, email)
    search.send_keys(Keys.RETURN)
    time.sleep(2)
    end = time.monotonic() + 10
    while time.monotonic() < end:
        if email.lower() in driver.page_source.lower():
            return
        time.sleep(0.5)
    raise TimeoutError(
        f"'{email}' did not appear in filtered results — check DB preconditions."
    )


def _open_delete_dialog(driver, email):
    """Navigate, search for the user, click their trash icon to open dialog."""
    go_to_user_management(driver)
    time.sleep(2)
    _search_user(driver, email)

    del_btn = wait_clickable(
        driver, By.XPATH, _row_delete_xpath(email), timeout=10
    )
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", del_btn)
    time.sleep(0.3)
    del_btn.click()
    time.sleep(1)


def _email_in_table(driver, email):
    """True only if email is inside <tbody> — not navbar/header/toast."""
    try:
        return len(driver.find_elements(
            By.XPATH,
            f"//tbody//td[contains(normalize-space(.), '{email}')]"
        )) > 0
    except Exception:
        return False


def _success_shown(driver):
    page = get_page_source(driver)   # already lowercased
    return any(kw in page for kw in _SUCCESS_KEYWORDS)


# ─────────────────────────────────────────────────────────────────────────────
# TEST CLASS
# ─────────────────────────────────────────────────────────────────────────────

class TestTP_UC7_009:
    """TP-UC7-009 — Delete: Cancel, Confirm, Self-Delete Prevention"""

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-010 Step 1
    # Input   : deleteuser@gmail.com → trash icon → Cancel
    # Expected: User account remains in list.
    # ──────────────────────────────────────────────────────────────────────────
    def test_cancel_deletion(self, driver):
        try:
            _open_delete_dialog(driver, DELETE_EMAIL)

            wait_clickable(driver, *_DIALOG_CANCEL, timeout=8).click()
            time.sleep(2)

            _search_user(driver, DELETE_EMAIL)

            assert _email_in_table(driver, DELETE_EMAIL), (
                f"'{DELETE_EMAIL}' disappeared from table after Cancel — "
                "deletion was NOT cancelled correctly."
            )

            print("✅ TC-UC7-010 Step 1 | Cancel Deletion — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-010 Step 1 | Cancel Deletion — FAIL\n    {e}")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-010 Step 2
    # Input   : deleteuser@gmail.com → trash icon → "Delete" (confirm)
    # Expected: "User deleted successfully." shown; user gone from table.
    # ──────────────────────────────────────────────────────────────────────────
    def test_confirm_deletion(self, driver):
        try:
            _open_delete_dialog(driver, DELETE_EMAIL)

            wait_clickable(driver, *_DIALOG_DELETE, timeout=8).click()
            time.sleep(4)   # wait for API + React re-render

            success = _success_shown(driver)
            if success:
                print("    ℹ️  Success dialog detected.")

            go_to_user_management(driver)
            time.sleep(2)

            still_in_table = False
            try:
                _search_user(driver, DELETE_EMAIL)
                still_in_table = _email_in_table(driver, DELETE_EMAIL)
            except TimeoutError:
                still_in_table = False   # not found in search = deleted ✓

            assert not still_in_table, (
                f"'{DELETE_EMAIL}' still appears in the table after confirmed deletion."
            )

            print("✅ TC-UC7-010 Step 2 | Confirm Deletion — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-010 Step 2 | Confirm Deletion — FAIL\n    {e}")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-010 Step 3
    # Input   : Attempt to delete s@gmail.com (logged-in admin)
    # Expected: System prevents self-deletion.
    #
    # ROOT CAUSE OF PREVIOUS FALSE PASS:
    #   The delete button is an icon-only button with class "text-red-500".
    #   Old XPath searched for title/aria-label/text → found 0 buttons →
    #   took "UI prevention" branch → always PASSED even when it shouldn't.
    #
    #   Fix: use contains(@class,'text-red-500') which matches the real button.
    #   Now the button IS found, deletion is actually attempted, and the test
    #   correctly FAILs if the system allows self-deletion (real bug).
    # ──────────────────────────────────────────────────────────────────────────
    def test_cannot_delete_own_account(self, driver):
        try:
            go_to_user_management(driver)
            time.sleep(2)
            _search_user(driver, ADMIN_EMAIL)

            # Find the trash icon button in the admin's own row
            own_del_btns = driver.find_elements(
                By.XPATH, _row_delete_xpath(ADMIN_EMAIL)
            )
            print(f"    ℹ️  Delete buttons found in own row: {len(own_del_btns)}")

            if len(own_del_btns) == 0:
                # UI fully prevents self-delete by hiding the button
                print("    ℹ️  Trash icon not rendered for own account — UI prevention confirmed.")
                print("✅ TC-UC7-010 Step 3 | Cannot Delete Own Account — PASS")
                return

            # Button exists — actually attempt the deletion
            print("    ℹ️  Trash icon found — attempting self-delete to verify block…")
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", own_del_btns[0]
            )
            time.sleep(0.3)
            own_del_btns[0].click()
            time.sleep(1)

            # Try clicking the confirm "Delete" button in the dialog
            try:
                wait_clickable(driver, *_DIALOG_DELETE, timeout=5).click()
                time.sleep(3)
            except Exception:
                print("    ℹ️  No confirm dialog appeared — blocked before dialog.")

            # Check for error message
            page = get_page_source(driver)
            error_shown = any(
                kw in page for kw in (
                    "cannot delete", "own account", "yourself",
                    "not allowed", "forbidden",
                )
            )

            # Re-navigate and check the TABLE (not the whole page)
            go_to_user_management(driver)
            time.sleep(2)
            _search_user(driver, ADMIN_EMAIL)
            admin_still_in_table = _email_in_table(driver, ADMIN_EMAIL)

            print(f"    ℹ️  Admin still in table : {admin_still_in_table}")
            print(f"    ℹ️  Error message shown  : {error_shown}")

            # REAL BUG: account was actually deleted
            if not admin_still_in_table:
                print(
                    "❌ TC-UC7-010 Step 3 | Cannot Delete Own Account — FAIL\n"
                    f"    REAL BUG: '{ADMIN_EMAIL}' was deleted from the system!\n"
                    "    The app does NOT prevent admin self-deletion — report this."
                )
                assert False, (
                    f"Self-deletion of '{ADMIN_EMAIL}' was NOT prevented by the system."
                )

            # Account still exists — blocked correctly
            print("✅ TC-UC7-010 Step 3 | Cannot Delete Own Account — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-010 Step 3 | Cannot Delete Own Account — FAIL\n    {e}")
            assert False