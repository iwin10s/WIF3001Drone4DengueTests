"""
Test Procedure ID : TP-UC7-003
Objective         : Verify admin can search users by name and email, filter by
                    role and status, and that the system correctly handles
                    searches that return no results.
Test Cases        : TC-UC7-003
Run               : pytest tests/test_uc7_003.py -v -s

PRECONDITIONS:
  - User with name 'Ali' and email ali@gmail.com must exist.
  - At least one Admin user must exist.
  - At least one Pending user must exist.
  - No user with name/email/username matching 'XYZ123' must exist.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select

from conftest import (
    USER_ALI_EMAIL,
    go_to_user_management, get_page_source,
    get_search_input, wait_clickable, wait_visible,
    clear_and_type,
)


class TestTP_UC7_003:
    """TP-UC7-003 — Search by Name/Email, Filter by Role/Status, No Results"""

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-003 Step 1
    # Input   : Search Query: Ali (search by name)
    # Expected: User record with name 'Ali' returned; no unrelated records shown.
    # ──────────────────────────────────────────────────────────────────────────
    def test_search_by_name(self, driver):
        try:
            go_to_user_management(driver)

            search = get_search_input(driver)
            clear_and_type(search, "Ali")
            search.send_keys(Keys.RETURN)
            time.sleep(2)

            page = get_page_source(driver)
            assert "ali" in page, "Search by name 'Ali' returned no results."

            print("✅ TC-UC7-003 Step 1 | Search by Name — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-003 Step 1 | Search by Name — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-003 Step 2
    # Input   : Search Query: ali@gmail.com (search by email)
    # Expected: User record with email ali@gmail.com returned with exact match.
    # ──────────────────────────────────────────────────────────────────────────
    def test_search_by_email(self, driver):
        try:
            go_to_user_management(driver)

            search = get_search_input(driver)
            clear_and_type(search, USER_ALI_EMAIL)
            search.send_keys(Keys.RETURN)
            time.sleep(2)

            page = get_page_source(driver)
            assert USER_ALI_EMAIL.lower() in page, (
                f"Search by email '{USER_ALI_EMAIL}' returned no results."
            )

            print("✅ TC-UC7-003 Step 2 | Search by Email — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-003 Step 2 | Search by Email — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-003 Step 3
    # Input   : Search Query: XYZ123 (non-existing user)
    # Expected: Empty results state or 'No users found' message; no error thrown.
    # ──────────────────────────────────────────────────────────────────────────
    def test_search_no_results(self, driver):
        try:
            go_to_user_management(driver)

            search = get_search_input(driver)
            clear_and_type(search, "XYZ123")
            search.send_keys(Keys.RETURN)
            time.sleep(2)

            page = get_page_source(driver)
            assert (
                "no user"   in page
                or "no result" in page
                or "not found" in page
                or "empty"     in page
                or "0 user"    in page
            ), "No empty-state message shown for non-existing user search 'XYZ123'."

            print("✅ TC-UC7-003 Step 3 | Search No Results — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-003 Step 3 | Search No Results — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-003 Step 4  –  Filter by Role = Admin
    # ──────────────────────────────────────────────────────────────────────────
    def test_filter_by_role_admin(self, driver):
        try:
            go_to_user_management(driver)

            header_bar = driver.find_element(
                By.CSS_SELECTOR, "div.bg-accent-blue.rounded-t-xl"
            )

            # Target the filter button via its unique div.relative wrapper
            # (avoids index-based lookup that hits the + Plus button instead)
            filter_btn = header_bar.find_element(
                By.CSS_SELECTOR, "div.relative > button"
            )
            filter_btn.click()
            time.sleep(1)

            # Popover renders inside div.relative
            popover = header_bar.find_element(
                By.CSS_SELECTOR, "div.relative div.absolute"
            )

            # Role label → its direct sibling <select>
            role_label = popover.find_element(
                By.XPATH, ".//label[normalize-space(.)='Role:']"
            )
            role_select = role_label.find_element(
                By.XPATH, "following-sibling::select"
            )
            Select(role_select).select_by_value("admin")
            time.sleep(1)

            popover.find_element(
                By.XPATH, ".//button[normalize-space(.)='Apply']"
            ).click()
            time.sleep(3)

            page = get_page_source(driver)
            assert "admin" in page, "Role filter 'Admin' produced no results."

            print("✅ TC-UC7-003 Step 4 | Filter by Role Admin — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-003 Step 4 | Filter by Role Admin — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-003 Step 5  –  Filter by Status = Pending
    # ──────────────────────────────────────────────────────────────────────────
    def test_filter_by_status_pending(self, driver):
        try:
            go_to_user_management(driver)

            header_bar = driver.find_element(
                By.CSS_SELECTOR, "div.bg-accent-blue.rounded-t-xl"
            )

            filter_btn = header_bar.find_element(
                By.CSS_SELECTOR, "div.relative > button"
            )
            filter_btn.click()
            time.sleep(1)

            popover = header_bar.find_element(
                By.CSS_SELECTOR, "div.relative div.absolute"
            )

            # Status label → its direct sibling <select>
            status_label = popover.find_element(
                By.XPATH, ".//label[normalize-space(.)='Status:']"
            )
            status_select = status_label.find_element(
                By.XPATH, "following-sibling::select"
            )
            # value="Pending" — capital P matches the HTML option attribute exactly
            Select(status_select).select_by_value("Pending")
            time.sleep(1)

            popover.find_element(
                By.XPATH, ".//button[normalize-space(.)='Apply']"
            ).click()
            time.sleep(3)

            page = get_page_source(driver)
            assert "pending" in page, "Status filter 'Pending' produced no results."

            print("✅ TC-UC7-003 Step 5 | Filter by Status Pending — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-003 Step 5 | Filter by Status Pending — FAIL ({e})")
            assert False