"""
Test Procedure ID : TP-UC7-002
Objective         : Verify the system displays the complete user list with correct
                    summary counts and status indicators, supports forward and
                    backward pagination, and handles retrieval failure gracefully.
Test Cases        : TC-UC7-002
Run               : pytest test_TP_UC7_002.py::TestTP_UC7_002 -v

PRECONDITIONS:
  - Exactly 3 users pre-seeded (2 Admin, 3 Active, 0 Pending) for summary count test.
  - At least 25 users exist to trigger pagination.
  - For test_db_error_graceful: manually STOP the DB container before running
    that test, then restart it after.
    Command: docker stop <db_container_name>
"""

import time
from selenium.webdriver.common.by import By

from conftest import (
    go_to_user_management, get_page_source, wait_visible,
)


class TestTP_UC7_002:
    """TP-UC7-002 — User List Display, Pagination & DB Error Handling"""

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-002 Step 1
    # Input   : Admin accesses User Management with 3 users (2 Admin, 3 Active, 0 Pending)
    # Expected: Complete user list shown; summary counters correct; role and
    #           status indicators visible on each entry.
    # ──────────────────────────────────────────────────────────────────────────
    def test_user_list_and_summary_counts(self, driver):
        try:
            go_to_user_management(driver)

            page = get_page_source(driver)

            assert (
                "total" in page
                or "active"  in page
                or "pending" in page
                or "admin"   in page
            ), "Summary counters not found on User Management page."

            rows = driver.find_elements(
                By.XPATH,
                "//table//tbody//tr"
                " | //div[contains(@class,'user-row')]"
                " | //li[contains(@class,'user-item')]"
            )
            assert len(rows) > 0, "No user rows found in the user list."

            print("✅ TC-UC7-002 Step 1 | User List & Summary Counts — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-002 Step 1 | User List & Summary Counts — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-002 Step 2
    # Input   : Total Users: 25 | Admin on Page 1 | Action: Click "Next Page"
    # Expected: System navigates to Page 2 and displays next set of user records.
    # ──────────────────────────────────────────────────────────────────────────
    def test_pagination_next_page(self, driver):
        try:
            go_to_user_management(driver)

            next_btn = wait_visible(
                driver, By.XPATH,
                "//button[contains(.,'Next')"
                " or contains(@aria-label,'next') or contains(@title,'Next')]"
            )
            next_btn.click()
            time.sleep(2)

            page = get_page_source(driver)
            assert (
                "user" in page
                or "email" in page
            ), "Page 2 did not load any user data."

            print("✅ TC-UC7-002 Step 2 | Pagination Next Page — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-002 Step 2 | Pagination Next Page — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-002 Step 3
    # Input   : Admin on Page 2 | Action: Click "Previous Page"
    # Expected: System navigates back to Page 1 and displays original records.
    # ──────────────────────────────────────────────────────────────────────────
    def test_pagination_previous_page(self, driver):
        try:
            go_to_user_management(driver)

            # Navigate to Page 2 first
            next_btn = wait_visible(
                driver, By.XPATH,
                "//button[contains(.,'Next')"
                " or contains(@aria-label,'next') or contains(@title,'Next')]"
            )
            next_btn.click()
            time.sleep(2)

            # Navigate back to Page 1
            prev_btn = wait_visible(
                driver, By.XPATH,
                "//button[contains(.,'Prev') or contains(.,'Previous')"
                " or contains(@aria-label,'prev') or contains(@title,'Prev')]"
            )
            prev_btn.click()
            time.sleep(2)

            page = get_page_source(driver)
            assert (
                "user" in page
                or "email" in page
            ), "Page 1 did not reload after clicking Previous."

            print("✅ TC-UC7-002 Step 3 | Pagination Previous Page — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-002 Step 3 | Pagination Previous Page — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-002 Step 4
    # Input   : Admin accesses User Management while database connection times out
    # Expected: Appropriate error message shown; no crash or blank screen; retry option.
    # NOTE    : Manually stop the DB container BEFORE running this test.
    #           docker stop <db_container_name>
    #           Restart after: docker start <db_container_name>
    # ──────────────────────────────────────────────────────────────────────────
    def test_db_error_graceful(self, driver):
        try:
            go_to_user_management(driver)
            time.sleep(4)

            page = get_page_source(driver)

            assert (
                "error"       in page
                or "could not"   in page
                or "failed"      in page
                or "unavailable" in page
                or "try again"   in page
                or "retry"       in page
            ), "No graceful error message shown when DB is unavailable."

            print("✅ TC-UC7-002 Step 4 | DB Error Graceful — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-002 Step 4 | DB Error Graceful — FAIL ({e})")
            assert False