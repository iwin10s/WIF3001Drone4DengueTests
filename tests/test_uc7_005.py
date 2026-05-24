"""
Test Procedure ID : TP-UC7-005
Objective         : Verify admin can bulk-import multiple users successfully,
                    and that the system gracefully handles batches containing
                    duplicate or invalid email entries without aborting the import.
Test Cases        : TC-UC7-005
Run               : pytest tests/test_uc7_005.py -v -s

PRECONDITIONS:
  - abu@gmail.com, mary@drone4dengue.com, ken@yahoo.com must NOT exist.
  - ali@gmail.com must already be registered (used as duplicate in Step 2).
  - Admin account s@gmail.com must be logged in.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from conftest import (
    go_to_user_management, get_page_source, get_alert_text,
    wait_clickable, wait_visible,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def open_bulk_add_modal(driver):
    """Click the 'Bulk Add Users' button on the User Management page."""
    go_to_user_management(driver)
    time.sleep(2)

    # HTML: <button ...> <FiUserPlus /> Bulk Add Users </button>
    bulk_btn = wait_clickable(
        driver,
        By.XPATH,
        "//button[contains(normalize-space(.), 'Bulk Add Users')]",
        timeout=10,
    )
    bulk_btn.click()
    time.sleep(1)


def get_bulk_modal(driver):
    """Return the bulk modal container element."""
    return wait_visible(
        driver,
        By.XPATH,
        "//h2[normalize-space(.)='Bulk Add Users']/ancestor::div[contains(@class,'bg-white')]",
        timeout=10,
    )


def fill_bulk_row(driver, modal, row_index, email, role):
    """
    Fill one row in the bulk table.
    - row_index is 0-based.
    - role must be 'user' or 'admin' (lowercase — matches HTML option values).
    - Modal starts with 3 rows; click '+ Add Row' first if row_index >= 3.
    """
    # ── Add extra rows if needed ───────────────────────────────────────────
    rows = modal.find_elements(By.XPATH, ".//tbody/tr")
    while len(rows) <= row_index:
        add_row_btn = modal.find_element(
            By.XPATH,
            ".//button[contains(normalize-space(.), 'Add Row')]",
        )
        add_row_btn.click()
        time.sleep(0.5)
        rows = modal.find_elements(By.XPATH, ".//tbody/tr")

    target_row = rows[row_index]

    # ── Email input ────────────────────────────────────────────────────────
    # HTML: <input type="email" placeholder="user@example.com" ...>
    email_input = target_row.find_element(By.XPATH, ".//input[@type='email']")
    email_input.clear()
    email_input.send_keys(email)
    time.sleep(0.3)

    # ── Role select ────────────────────────────────────────────────────────
    # HTML: <select ...> <option value="user">...</option>
    #                    <option value="admin">...</option> </select>
    role_select = target_row.find_element(By.XPATH, ".//select")
    # Values are lowercase: "user" / "admin"
    Select(role_select).select_by_value(role.lower())
    time.sleep(0.3)


def submit_bulk_invite(driver, modal):
    """Click 'Invite All Users' / submit button inside the modal."""
    invite_btn = wait_clickable(
        driver,
        By.XPATH,
        ".//button[contains(normalize-space(.), 'Invite All') or "
        "contains(normalize-space(.), 'Invite') or "
        "contains(normalize-space(.), 'Submit')]",
        timeout=10,
        # search relative to modal if possible; fall back to driver
    )
    invite_btn.click()
    time.sleep(5)   # allow bulk processing + progress bar to finish


# ── Test Class ─────────────────────────────────────────────────────────────────

class TestTP_UC7_005:
    """TP-UC7-005 — Bulk Import: Valid, Duplicate Email, Invalid Format"""

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-005 Step 1
    # Input   : abu@gmail.com (user), mary@drone4dengue.com (admin),
    #           ken@yahoo.com (user)
    # Expected: All 3 users created; appear in user list with correct roles;
    #           green summary confirmation displayed.
    # ──────────────────────────────────────────────────────────────────────────
    def test_bulk_import_valid_users(self, driver):
        try:
            open_bulk_add_modal(driver)
            modal = get_bulk_modal(driver)

            users = [
                ("abu@gmail.com",         "user"),
                ("mary@drone4dengue.com", "admin"),
                ("ken@yahoo.com",         "user"),
            ]

            # Modal already has 3 default rows — fill them directly
            for i, (email, role) in enumerate(users):
                fill_bulk_row(driver, modal, i, email, role)

            submit_bulk_invite(driver, modal)

            page = get_page_source(driver)

            # The modal shows a green bulkSummaryMessage on success
            # HTML: <div class="bg-green-50 border border-green-200 ...">
            success = any(
                kw in page.lower()
                for kw in ("success", "invited", "created", "imported", "complete")
            ) or any(email.lower() in page.lower() for email, _ in users)

            assert success, (
                "No confirmation that bulk users were created."
            )

            print("✅ TC-UC7-005 Step 1 | Bulk Import Valid Users — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-005 Step 1 | Bulk Import Valid Users — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-005 Step 2
    # Input   : newuser@gmail.com, ali@gmail.com (duplicate), test@yahoo.com
    # Expected: System detects duplicate ali@gmail.com;
    #           red error shown; import blocked; no new users created.
    # ──────────────────────────────────────────────────────────────────────────
    def test_bulk_import_duplicate_email(self, driver):
        try:
            open_bulk_add_modal(driver)
            modal = get_bulk_modal(driver)

            users = [
                ("newuser@gmail.com", "user"),
                ("ali@gmail.com",     "user"),   # already registered → duplicate
                ("test@yahoo.com",    "user"),
            ]

            for i, (email, role) in enumerate(users):
                fill_bulk_row(driver, modal, i, email, role)

            submit_bulk_invite(driver, modal)

            page = get_page_source(driver)

            # HTML: <div class="bg-red-50 border border-red-200 text-red-700 ...">
            # or per-row errorMessage shown inside the table row
            blocked = any(
                kw in page.lower()
                for kw in (
                    "already", "duplicate", "registered",
                    "exists", "already registered",
                )
            )
            assert blocked, (
                "No duplicate-email error shown for ali@gmail.com in bulk import."
            )

            print("✅ TC-UC7-005 Step 2 | Bulk Import Duplicate Email — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-005 Step 2 | Bulk Import Duplicate Email — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-005 Step 3
    # Input   : valid@gmail.com, invalidemail (no domain), sample@yahoo.com
    # Expected: Inline validation shows 'Please enter a valid email address.'
    #           immediately under the invalid row; import cannot proceed.
    # ──────────────────────────────────────────────────────────────────────────
    def test_bulk_import_invalid_email_format(self, driver):
        try:
            open_bulk_add_modal(driver)
            modal = get_bulk_modal(driver)

            users = [
                ("valid@gmail.com",  "user"),
                ("invalidemail",     "user"),   # no domain — triggers inline error
                ("sample@yahoo.com", "user"),
            ]

            for i, (email, role) in enumerate(users):
                fill_bulk_row(driver, modal, i, email, role)

            # Inline validation fires on change — check BEFORE submit
            # HTML: <p class="mt-1 text-xs text-red-600">
            #         Please enter a valid email address.
            #       </p>
            page = get_page_source(driver)
            inline_error = "please enter a valid email address" in page.lower()

            # Also try submitting and check if blocked
            if not inline_error:
                try:
                    submit_bulk_invite(driver, modal)
                    page = get_page_source(driver)
                except Exception:
                    pass

            page = get_page_source(driver)
            validation_shown = (
                inline_error
                or "please enter a valid email" in page.lower()
                or "invalid" in page.lower()
                or "valid email" in page.lower()
            )
            assert validation_shown, (
                "No validation error shown for invalid email 'invalidemail'."
            )

            print("✅ TC-UC7-005 Step 3 | Bulk Import Invalid Format — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-005 Step 3 | Bulk Import Invalid Format — FAIL ({e})")
            assert False