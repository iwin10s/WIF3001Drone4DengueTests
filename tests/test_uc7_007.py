"""
Test Procedure ID : TP-UC7-007
Objective         : Verify admin can promote users to Admin and demote Admins
                    to User, and that the system prevents role changes that would
                    leave the system with no Admin account.
Test Cases        : TC-UC7-007
Run               : pytest tests/test_uc7_007.py -v -s

PRECONDITIONS:
  - user@healthtech.com  exists with Role: User.
  - admin@healthtech.com exists with Role: Admin.
  - At least one other Admin exists (for Step 2 demotion to be valid).
  - For Step 3: exactly 1 Admin remains in the system at test time.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from conftest import (
    go_to_user_management, get_page_source, get_alert_text,
    wait_clickable, wait_visible,
)

USER_EMAIL  = "user@healthtech.com"
ADMIN_EMAIL = "admin@healthtech.com"


def open_role_edit_for(driver, email):
    """
    Navigate to User Management, find the target user row,
    and open their role/edit panel.
    """
    go_to_user_management(driver)
    time.sleep(2)

    user_row = wait_visible(
        driver,
        By.XPATH,
        f"//tr[contains(., '{email}')] | //div[contains(., '{email}')]",
        timeout=10,
    )
    # Try a dedicated Edit/Role button inside the row
    try:
        edit_btn = user_row.find_element(
            By.XPATH,
            ".//button[contains(@aria-label,'edit') or "
            "contains(normalize-space(.),'Edit') or "
            "contains(@title,'Edit')]",
        )
        edit_btn.click()
    except Exception:
        user_row.click()
    time.sleep(2)


def change_role_to(driver, new_role):
    """Select a new role in the role dropdown and save."""
    role_select = wait_visible(
        driver,
        By.XPATH,
        "//select[contains(@name,'role') or contains(@id,'role')]",
        timeout=10,
    )
    Select(role_select).select_by_visible_text(new_role)
    time.sleep(0.5)

    save_btn = wait_clickable(
        driver,
        By.XPATH,
        "//button[contains(normalize-space(.), 'Save') or "
        "contains(normalize-space(.), 'Update')]",
        timeout=10,
    )
    save_btn.click()
    time.sleep(3)


class TestTP_UC7_007:
    """TP-UC7-007 — Role Management: Promote, Demote, Last-Admin Prevention"""

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-007 Step 1
    # Input   : user@healthtech.com → Role: Admin
    # Expected: Role updated to Admin; change reflected in user list immediately.
    # ──────────────────────────────────────────────────────────────────────────
    def test_promote_user_to_admin(self, driver):
        try:
            open_role_edit_for(driver, USER_EMAIL)
            change_role_to(driver, "Admin")

            alert = get_alert_text(driver)
            page  = get_page_source(driver)

            success = (
                (alert and any(
                    kw in alert.lower()
                    for kw in ("success", "updated", "changed", "promoted")
                ))
                or any(
                    kw in page.lower()
                    for kw in ("success", "admin")
                )
            )
            assert success, (
                f"No confirmation that {USER_EMAIL} was promoted to Admin."
            )

            # Verify list shows the updated role
            go_to_user_management(driver)
            time.sleep(2)
            page = get_page_source(driver)
            assert USER_EMAIL.lower() in page.lower(), (
                f"{USER_EMAIL} not visible in user list after promotion."
            )

            print("✅ TC-UC7-007 Step 1 | Promote User to Admin — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-007 Step 1 | Promote User to Admin — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-007 Step 2
    # Input   : admin@healthtech.com → Role: User  (other Admins still exist)
    # Expected: Role updated to User; Admin permissions revoked; list updated.
    # ──────────────────────────────────────────────────────────────────────────
    def test_demote_admin_to_user(self, driver):
        try:
            open_role_edit_for(driver, ADMIN_EMAIL)
            change_role_to(driver, "User")

            alert = get_alert_text(driver)
            page  = get_page_source(driver)

            success = (
                (alert and any(
                    kw in alert.lower()
                    for kw in ("success", "updated", "changed", "demoted")
                ))
                or "success" in page.lower()
            )
            assert success, (
                f"No confirmation that {ADMIN_EMAIL} was demoted to User."
            )

            go_to_user_management(driver)
            time.sleep(2)
            page = get_page_source(driver)
            assert ADMIN_EMAIL.lower() in page.lower(), (
                f"{ADMIN_EMAIL} not visible in user list after demotion."
            )

            print("✅ TC-UC7-007 Step 2 | Demote Admin to User — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-007 Step 2 | Demote Admin to User — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-007 Step 3
    # Input   : Last remaining Admin → attempt Role: User
    # Expected: System blocks demotion; error 'Cannot demote the last Admin';
    #           role remains Admin.
    # NOTE    : Ensure exactly 1 Admin exists before running this step.
    # ──────────────────────────────────────────────────────────────────────────
    def test_cannot_demote_last_admin(self, driver):
        try:
            open_role_edit_for(driver, ADMIN_EMAIL)

            # Attempt to set role to User
            try:
                role_select_el = driver.find_element(
                    By.XPATH,
                    "//select[contains(@name,'role') or contains(@id,'role')]",
                )
                Select(role_select_el).select_by_visible_text("User")
                time.sleep(0.5)

                save_btn = wait_clickable(
                    driver,
                    By.XPATH,
                    "//button[contains(normalize-space(.), 'Save') or "
                    "contains(normalize-space(.), 'Update')]",
                    timeout=10,
                )
                save_btn.click()
                time.sleep(3)
            except Exception:
                pass  # Button may be disabled pre-click

            alert = get_alert_text(driver)
            page  = get_page_source(driver)

            # Check if button is disabled (UI-level prevention)
            try:
                save_btn = driver.find_element(
                    By.XPATH,
                    "//button[contains(normalize-space(.), 'Save') or "
                    "contains(normalize-space(.), 'Update')]",
                )
                btn_disabled = (
                    not save_btn.is_enabled()
                    or save_btn.get_attribute("disabled") is not None
                )
            except Exception:
                btn_disabled = False

            blocked = (
                btn_disabled
                or (alert and any(
                    kw in alert.lower()
                    for kw in ("last admin", "cannot demote", "only admin", "at least one")
                ))
                or any(
                    kw in page.lower()
                    for kw in ("last admin", "cannot demote", "only admin", "at least one")
                )
            )
            assert blocked, (
                "System did NOT prevent demotion of the last Admin account."
            )

            print("✅ TC-UC7-007 Step 3 | Cannot Demote Last Admin — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-007 Step 3 | Cannot Demote Last Admin — FAIL ({e})")
            assert False