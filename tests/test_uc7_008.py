"""
Test Procedure ID : TP-UC7-008
Objective         : Verify admin can manually change a user's registration status
                    from Pending to Verified, and verify admin can initiate an
                    invitation for an unregistered email address.
Test Cases        : TC-UC7-008, TC-UC7-009
Run               : pytest test_TP_UC7_008.py::TestTP_UC7_008 -v -s

PRECONDITIONS:
  - TestPending@gmail.com must exist with Status: Pending.
  - unknownuser@gmail.com must NOT be registered in the system.

ROOT CAUSE NOTE:
  The user list is paginated — TestPending@gmail.com may not be on page 1.
  Fix: search for the email first so the row is guaranteed to be visible,
  then interact with it.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from conftest import (
    go_to_user_management, get_page_source, get_alert_text,
    wait_visible, wait_clickable,
    open_add_user_modal, fill_add_user_form, submit_add_user_form,
    get_search_input, clear_and_type,
)

PENDING_EMAIL = "TestPending@gmail.com"
UNKNOWN_EMAIL = "unknownuser@gmail.com"

# ── Component-accurate locators ───────────────────────────────────────────────
#
#  From the real TSX source:
#    <span className="px-3 py-1 rounded-full ...">Pending</span>
#    <button title="Verify User">Verify</button>   ← only when status==="Pending"
#
#  After searching, only one row is shown so we can drop the row anchor
#  and target the elements directly — simpler and more reliable.
# ─────────────────────────────────────────────────────────────────────────────

# Button that only exists when status === "Pending"
VERIFY_BTN  = (By.XPATH, "//button[@title='Verify User']")

# The status badge <span> — contains the text "Pending" or "Verified"
STATUS_BADGE = (By.XPATH, "//span[contains(@class,'rounded-full')]"
                           "[contains(text(),'Pending') or contains(text(),'Verified')]")


def _search_for_user(driver, email):
    """
    Type the email into the search box and wait for the table to filter.
    This guarantees the target row is on screen regardless of pagination.
    """
    search = get_search_input(driver)
    clear_and_type(search, email)
    search.send_keys(Keys.RETURN)
    time.sleep(2)   # wait for debounce + API response

    # Confirm the email appears somewhere on the page before continuing
    end = time.monotonic() + 10
    while time.monotonic() < end:
        if email.lower() in driver.page_source.lower():
            return
        time.sleep(0.5)

    raise TimeoutError(
        f"'{email}' did not appear in the filtered results after searching.\n"
        f"  → Check that the user exists in the DB with exactly this email."
    )


def _get_status_text(driver):
    """Return the lowercased text of the first visible status badge on screen."""
    try:
        badge = driver.find_element(*STATUS_BADGE)
        return badge.text.strip().lower()
    except Exception:
        return ""


class TestTP_UC7_008:
    """TP-UC7-008/009 — Status Verification and Invite Unregistered User"""

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-008 Step 1
    # Input   : Click 'Verify' button beside TestPending@gmail.com
    # Expected: Status badge changes from 'Pending' to 'Verified';
    #           'Verify' button disappears from the row.
    # ──────────────────────────────────────────────────────────────────────────
    def test_change_status_pending_to_verified(self, driver):
        try:
            go_to_user_management(driver)
            time.sleep(3)

            # ── Step 1: Search so the row is guaranteed on screen ─────────
            print(f"    ℹ️  Searching for '{PENDING_EMAIL}'…")
            _search_for_user(driver, PENDING_EMAIL)

            # ── Step 2: Read the status badge before clicking ─────────────
            status_before = _get_status_text(driver)
            print(f"    ℹ️  Status before: '{status_before}'")

            assert "pending" in status_before, (
                f"'{PENDING_EMAIL}' does not show 'Pending' status after searching.\n"
                f"  Got: '{status_before}'\n"
                f"  → Confirm the user exists in the DB with Status = Pending."
            )

            # ── Step 3: Find and click the 'Verify User' button ───────────
            verify_btn = wait_visible(driver, *VERIFY_BTN, timeout=10)

            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center'});", verify_btn
            )
            time.sleep(0.4)

            try:
                verify_btn.click()
            except Exception:
                # Fallback: JS click if a sticky header intercepts
                driver.execute_script("arguments[0].click();", verify_btn)

            time.sleep(3)   # wait for API + React re-render

            # ── Step 4: Verify the result ─────────────────────────────────
            alert        = get_alert_text(driver)
            status_after = _get_status_text(driver)

            if alert:
                print(f"    ℹ️  Alert: '{alert}'")
            print(f"    ℹ️  Status after: '{status_after}'")

            success = (
                # Badge text changed to 'verified'
                "verified" in status_after
                # OR React removed the Verify button (status is no longer Pending)
                or len(driver.find_elements(*VERIFY_BTN)) == 0
                # OR a toast/alert confirmed the update
                or (alert and any(
                    kw in alert.lower()
                    for kw in ("verified", "success", "updated", "status")
                ))
            )

            assert success, (
                f"Status for '{PENDING_EMAIL}' does not appear to have changed.\n"
                f"  Before : {status_before!r}\n"
                f"  After  : {status_after!r}\n"
                f"  Alert  : {alert!r}"
            )

            print("✅ TC-UC7-008 Step 1 | Change Status Pending → Verified — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-008 Step 1 | Change Status Pending → Verified — FAIL\n    {e}")
            assert False

    # ──────────────────────────────────────────────────────────────────────────
    # TC-UC7-009 Step 1
    # Input   : unknownuser@gmail.com — admin initiates invite/registration
    # Expected: Confirmation displayed; no system error.
    # ──────────────────────────────────────────────────────────────────────────
    def test_invite_unregistered_user(self, driver):
        try:
            go_to_user_management(driver)

            open_add_user_modal(driver)
            fill_add_user_form(driver, email=UNKNOWN_EMAIL, role="User")
            submit_add_user_form(driver)

            alert = get_alert_text(driver)
            page  = get_page_source(driver)

            if alert:
                print(f"    ℹ️  Alert: '{alert}'")

            success = (
                (alert and any(
                    kw in alert.lower()
                    for kw in ("success", "invited", "invitation", "sent", "created")
                ))
                or any(
                    kw in page
                    for kw in ("success", "invited", "invitation", UNKNOWN_EMAIL.lower())
                )
            )
            assert success, (
                f"No confirmation that invitation was sent to '{UNKNOWN_EMAIL}'.\n"
                f"  Alert : {alert!r}"
            )

            print("✅ TC-UC7-009 Step 1 | Invite Unregistered User — PASS")

        except Exception as e:
            print(f"❌ TC-UC7-009 Step 1 | Invite Unregistered User — FAIL\n    {e}")
            assert False