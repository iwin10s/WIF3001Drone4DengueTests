"""
Test Procedure ID : TP-UC7-004
Objective         : Verify admin can create a new single user with valid details,
                    and that the system validates required fields, correct email
                    format, and email uniqueness.
Test Cases        : TC-UC7-004
Run               : pytest test_TP_UC7_004.py::TestTP_UC7_004 -v

PRECONDITIONS:
  - ali@gmail.com must NOT exist before running Step 1.
  - Step 4 (duplicate) depends on Step 1 having run first to create ali@gmail.com.
"""
from selenium.webdriver.common.by import By

from conftest import (
    USER_ALI_EMAIL,
    go_to_user_management, get_page_source, get_alert_text,
    open_add_user_modal, fill_add_user_form, submit_add_user_form,
)


class TestTP_UC7_004:
    """TP-UC7-004 — Create Single User: Valid, Empty Email, Invalid Format, Duplicate"""

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-004 Step 1
    # Input   : Email: ali@gmail.com | Role: User | Company: Health Tech Solutions
    # Expected: Account created; user appears in list with correct role and company;
    #           confirmation message displayed.
    # ──────────────────────────────────────────────────────────────────────────
    def test_create_valid_user(self, driver):
        try:
            go_to_user_management(driver)
            open_add_user_modal(driver)
            fill_add_user_form(driver, email=USER_ALI_EMAIL, role="User")
            submit_add_user_form(driver)

            alert = get_alert_text(driver)
            page  = get_page_source(driver)

            success = (
                (alert and (
                    "success" in alert.lower()
                    or "created" in alert.lower()
                    or "invited" in alert.lower()
                ))
                or "success"             in page
                or USER_ALI_EMAIL.lower() in page
            )
            assert success, "No confirmation that user ali@gmail.com was created."

            print("✅ TC-UC7-004 Step 1 | Create Valid User — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-004 Step 1 | Create Valid User — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-004 Step 2
    # Input   : Email: (empty) | Role: User | Action: Submit form
    # Expected: Submit button is disabled; form cannot be submitted.
    # ──────────────────────────────────────────────────────────────────────────
    def test_create_user_empty_email(self, driver):
        try:
            go_to_user_management(driver)
            open_add_user_modal(driver)
            fill_add_user_form(driver, email="", role="User")

            # ── Do NOT call submit_add_user_form — button is disabled when ────
            # ── email is empty. Instead, assert it is actually disabled.   ────
            submit_btn = driver.find_element(
                By.XPATH,
                "//button[contains(normalize-space(.), 'Create User')]"
            )

            is_disabled = (
                not submit_btn.is_enabled()                        # Selenium check
                or submit_btn.get_attribute("disabled") is not None  # HTML attribute
            )

            assert is_disabled, (
                "Submit button should be disabled when email is empty, but it is clickable."
            )

            print("✅ TC-UC7-004 Step 2 | Create User Empty Email — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-004 Step 2 | Create User Empty Email — FAIL ({e})")
            assert False
    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-004 Step 3
    # Input   : Email: userexample.com (missing @ symbol) | Role: User
    # Expected: Submission prevented; validation error for invalid email format.
    # ──────────────────────────────────────────────────────────────────────────
    def test_create_user_invalid_email_format(self, driver):
        try:
            go_to_user_management(driver)
            open_add_user_modal(driver)
            fill_add_user_form(driver, email="userexample.com", role="User")
            submit_add_user_form(driver)

            alert = get_alert_text(driver)
            page  = get_page_source(driver)

            validation_shown = (
                (alert and (
                    "invalid"     in alert.lower()
                    or "valid email" in alert.lower()
                ))
                or "invalid"      in page
                or "valid email"  in page
                or "email format" in page
            )
            assert validation_shown, "No validation error shown for invalid email format."

            print("✅ TC-UC7-004 Step 3 | Create User Invalid Email Format — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-004 Step 3 | Create User Invalid Email Format — FAIL ({e})")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-004 Step 4
    # Input   : Email: ali@gmail.com (already registered) | Role: User
    # Expected: Account creation prevented; error 'email already in use'.
    # NOTE    : Depends on Step 1 having run first to create ali@gmail.com.
    # ──────────────────────────────────────────────────────────────────────────
    def test_create_user_duplicate_email(self, driver):
        try:
            go_to_user_management(driver)
            open_add_user_modal(driver)
            fill_add_user_form(driver, email=USER_ALI_EMAIL, role="User")
            submit_add_user_form(driver)

            alert = get_alert_text(driver)
            page  = get_page_source(driver)

            blocked = (
                (alert and (
                    "already"    in alert.lower()
                    or "exists"    in alert.lower()
                    or "duplicate" in alert.lower()
                ))
                or "already registered" in page
                or "already in use"     in page
                or "duplicate"          in page
            )
            assert blocked, "No error shown for duplicate email ali@gmail.com."

            print("✅ TC-UC7-004 Step 4 | Create User Duplicate Email — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-004 Step 4 | Create User Duplicate Email — FAIL ({e})")
            assert False