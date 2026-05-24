"""
Test Procedure ID : TP-UC7-001
Objective         : Verify the system grants access to authorized Admin users
                    and denies access to non-Admin users attempting to navigate
                    to the User Management module.
Test Cases        : TC-UC7-001
Run               : pytest test_TP_UC7_001.py::TestTP_UC7_001 -v
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from conftest import (
    BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD,
    NON_ADMIN_EMAIL, NON_ADMIN_PASSWORD,
    go_to_user_management, get_page_source, do_login,
)


class TestTP_UC7_001:
    """TP-UC7-001 — Access Control: Admin vs Non-Admin"""

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-001 Step 1
    # Input   : Email: s@gmail.com | Password: denisetest1 | Role: Admin
    # Expected: Login succeeds; User Management module loads with full user list,
    #           filters, summary indicators, and status information.
    # ──────────────────────────────────────────────────────────────────────────
    def test_admin_login_and_access(self, driver):
        try:
            go_to_user_management(driver)

            page = get_page_source(driver)

            assert (
                "user management" in page
                or "user list"    in page
                or "total users"  in page
                or "email"        in page
            ), "User Management page did not load for Admin."

            print("✅ TC-UC7-001 Step 1 | Admin Login and Access — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-001 Step 1 | Admin Login and Access — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-001 Step 2
    # Input   : Email: normaluser@gmail.com | Role: User
    #           Action: Attempt to navigate to User Management
    # Expected: Access denied; unauthorized message or redirect shown;
    #           no user data exposed.
    # ──────────────────────────────────────────────────────────────────────────
    def test_non_admin_access_denied(self, raw_driver):
        try:
            do_login(raw_driver, NON_ADMIN_EMAIL, NON_ADMIN_PASSWORD)

            raw_driver.get(BASE_URL + "/user-management")
            time.sleep(3)

            page    = get_page_source(raw_driver)
            cur_url = raw_driver.current_url.lower()

            denied = (
                "unauthorized"     in page
                or "forbidden"     in page
                or "access denied" in page
                or "not allowed"   in page
                or "/user-management" not in cur_url
                or "login"         in cur_url
            )

            assert denied, "Non-admin user was NOT blocked from User Management."

            print("✅ TC-UC7-001 Step 2 | Non-Admin Access Denied — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-001 Step 2 | Non-Admin Access Denied — FAIL ({e})")
            assert False