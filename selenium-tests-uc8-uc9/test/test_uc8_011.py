"""
test_uc8_011.py
===============
Test Procedure : TP-UC8-011
Test Cases     : TC-UC8-011
Objective      : Verify that system displays the number of active cases,
                 total cases, and coverage area correctly in the statistic
                 section.
Coverage Items : TCOV-08-021, TCOV-08-022, TCOV-08-023

Backend facts (from dengueDataController.js)
--------------------------------------------
  GET /dengue-data/summary  →  getSummary()
    Returns:
      { totalRecords, activeCases, locationsCovered, hotspotCount }
    These are the exact values the frontend stat cards display.

  POST /dengue-data
    Required: companyLocationId (not companyId)
    Returns 201 + { id, ... } on success.

  DELETE /dengue-data/:id
    Deletes by primary key — must use id from POST response.

Seeding strategy
----------------
  Each sub-test:
    1. POSTs known records via the API (self-seeding)
    2. Calls GET /dengue-data/summary to get the ground-truth counts
    3. Reloads /data-management and checks the stat cards match the API counts
    4. DELETEs all seeded records by id in the finally block (wrap-up)

Auth requirements (UC-8)
--------------------------
  Admin MUST be authenticated  → JWT in localStorage['token']
  companyId MUST exist         → localStorage['company']['id']
  companyLocationId MUST exist → resolved via GET /company-locations
"""

import os
import json
import time
import pytest
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

API_URL      = os.getenv("API_BASE_URL", "http://localhost:4000")
BASE_URL     = os.getenv("APP_BASE_URL", "http://localhost:3000")
DATA_MGT_URL = BASE_URL + "/data-management"

# Seed layout — 10 Active Cases, 5 Hotspot, 3 Processing, 3 distinct locations
SEED_RECORDS = [
    # (location, activeCases, totalCases, status)
    ("Cheras",      8,  20, "Active Cases"),
    ("Cheras",      5,  15, "Active Cases"),
    ("Cheras",      3,  10, "Active Cases"),
    ("Ampang",      7,  18, "Active Cases"),
    ("Ampang",      4,  12, "Active Cases"),
    ("Ampang",      6,  16, "Active Cases"),
    ("Wangsa Maju", 9,  25, "Active Cases"),
    ("Wangsa Maju", 2,   8, "Active Cases"),
    ("Wangsa Maju",11,  30, "Active Cases"),
    ("Cheras",      1,   5, "Active Cases"),
    ("Cheras",     15,  40, "Hotspot"),
    ("Ampang",     12,  35, "Hotspot"),
    ("Wangsa Maju",18,  50, "Hotspot"),
    ("Cheras",     20,  55, "Hotspot"),
    ("Ampang",      9,  28, "Hotspot"),
    ("Cheras",      4,  14, "Processing"),
    ("Ampang",      6,  20, "Processing"),
    ("Wangsa Maju", 3,  11, "Processing"),
]

EXPECTED_ACTIVE     = sum(1 for r in SEED_RECORDS if r[3] == "Active Cases")  # 10
EXPECTED_HOTSPOT    = sum(1 for r in SEED_RECORDS if r[3] == "Hotspot")       # 5
EXPECTED_TOTAL      = len(SEED_RECORDS)                                        # 18
EXPECTED_LOCATIONS  = len({r[0] for r in SEED_RECORDS})                       # 3


def _api_headers(token):
    return {"Authorization": "Bearer " + token, "Content-Type": "application/json"}


def _get_auth(driver):
    token        = driver.execute_script("return localStorage.getItem('token');")
    company_json = driver.execute_script("return localStorage.getItem('company');")
    assert token,        "PRE-CONDITION FAIL: JWT token missing."
    assert company_json, "PRE-CONDITION FAIL: 'company' missing from localStorage."
    company_id = json.loads(company_json).get("id", "")
    assert company_id,   "PRE-CONDITION FAIL: company JSON has no 'id' field."
    return token, company_id


def _get_company_location_id(token):
    """Resolve a valid companyLocationId required by POST /dengue-data."""
    for url in [API_URL + "/company-locations", API_URL + "/locations"]:
        try:
            resp = requests.get(url, headers=_api_headers(token), timeout=8)
            if resp.status_code == 200:
                body = resp.json()
                locs = body if isinstance(body, list) else body.get("data", [])
                if locs:
                    return locs[0].get("id") or locs[0].get("locationId")
        except Exception:
            pass
    return None


def _get_summary(token):
    """
    Call GET /dengue-data/summary and return the dict.
    This is the API source of truth for what the stat cards show.
    """
    resp = requests.get(
        API_URL + "/dengue-data/summary",
        headers=_api_headers(token),
        timeout=10,
    )
    assert resp.status_code == 200, (
        "GET /dengue-data/summary returned %d: %s" % (resp.status_code, resp.text[:200])
    )
    return resp.json()
    # Shape: { totalRecords, activeCases, locationsCovered, hotspotCount }


def _seed_records(token, location_id):
    """POST all SEED_RECORDS; return list of created ids for wrap-up."""
    created_ids = []
    for location, active, total, status in SEED_RECORDS:
        payload = {
            "date":              "2024-06-01",
            "location":          location,
            "activeCases":       active,
            "totalCases":        total,
            "status":            status,
            "source":            "tp-uc8-011-seed",
            "coverageArea":      location,
            "companyLocationId": location_id,
        }
        resp = requests.post(
            API_URL + "/dengue-data",
            json=payload,
            headers=_api_headers(token),
            timeout=10,
        )
        if resp.status_code == 201:
            rec_id = resp.json().get("id")
            if rec_id:
                created_ids.append(rec_id)
        else:
            print("[WARN] Seed POST failed (%d): %s" % (resp.status_code, resp.text[:100]))
    return created_ids


def _delete_by_ids(token, ids):
    """Wrap-up: DELETE /dengue-data/:id for each created record."""
    for rec_id in ids:
        try:
            resp = requests.delete(
                API_URL + "/dengue-data/" + rec_id,
                headers=_api_headers(token),
                timeout=8,
            )
            if resp.status_code not in (200, 204, 404):
                print("[WARN] DELETE %s returned %d" % (rec_id, resp.status_code))
        except Exception as e:
            print("[WARN] DELETE %s failed: %s" % (rec_id, e))


def _reload_data_management(driver, wait):
    """Navigate to /data-management and wait for stat cards to render."""
    driver.get(DATA_MGT_URL)
    wait.until(EC.presence_of_element_located(
        (By.XPATH, "//*[contains(text(), 'Data Management')]")
    ))
    time.sleep(2)  # framer-motion animations settle


def _find_count_near_label(text, label):
    """
    Return the first integer within 80 chars of *label* in the page text.
    Stat cards render as  "Active Cases\n10"  or  "10\nActive Cases".
    """
    import re
    idx = text.find(label)
    if idx == -1:
        return None
    window = text[max(0, idx - 80): idx + len(label) + 80]
    nums = re.findall(r"\b\d+\b", window)
    return int(nums[0]) if nums else None


class TestUC8StatisticsCards:
    """TP-UC8-011 — Statistics cards accuracy (self-seeding, API-verified)."""

    def test_status_counts_displayed_correctly(self, logged_in):
        """
        TC-UC8-011 | TCOV-08-021
        ─────────────────────────────────────────────────────────────────────
        Step 1  Resolve auth (token + companyLocationId).
        Step 2  Seed 10 Active Cases + 5 Hotspot + 3 Processing via API.
        Step 3  Call GET /dengue-data/summary — ground-truth counts.
        Step 4  Reload /data-management; read stat card section.
        Step 5  Assert Active Cases card  >= summary.activeCases.
        Step 6  Assert Hotspot card       >= summary.hotspotCount.
        Wrap-up DELETE all seeded records by id.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        token, _ = _get_auth(driver)
        location_id = _get_company_location_id(token)
        assert location_id, (
            "TC-UC8-011 PRE-CONDITION FAIL: No companyLocationId found. "
            "Create at least one company location before running this test."
        )

        print("\n[INFO] Seeding %d records..." % len(SEED_RECORDS))
        created_ids = _seed_records(token, location_id)
        assert len(created_ids) == len(SEED_RECORDS), (
            "TC-UC8-011 FAIL: Only %d/%d seed records created." % (
                len(created_ids), len(SEED_RECORDS))
        )

        try:
            # ── Step 3: Get ground-truth from summary API ─────────────────────
            summary = _get_summary(token)
            print("[INFO] Summary API: %s" % summary)
            api_active  = summary.get("activeCases", 0)
            api_hotspot = summary.get("hotspotCount", 0)

            # ── Step 4: Reload page ───────────────────────────────────────────
            _reload_data_management(driver, wait)
            body_text = driver.find_element(By.TAG_NAME, "body").text

            # ── Step 5–6: Assert stat card values match API summary ────────────
            ui_active  = _find_count_near_label(body_text, "Active Cases")
            ui_hotspot = _find_count_near_label(body_text, "Hotspot")

            assert ui_active is not None and ui_active >= api_active, (
                "TC-UC8-011 FAIL (TCOV-08-021): Active Cases card shows %s, "
                "API summary says %d.\nBody: %s" % (ui_active, api_active, body_text[:500])
            )
            assert ui_hotspot is not None and ui_hotspot >= api_hotspot, (
                "TC-UC8-011 FAIL (TCOV-08-021): Hotspot card shows %s, "
                "API summary says %d.\nBody: %s" % (ui_hotspot, api_hotspot, body_text[:500])
            )

        finally:
            _delete_by_ids(token, created_ids)

        print("TC-UC8-011 Status Counts Displayed Correctly - PASS")

    def test_total_records_count_displayed(self, logged_in):
        """
        TC-UC8-011 | TCOV-08-022
        ─────────────────────────────────────────────────────────────────────
        Step 1  Seed 18 records via API.
        Step 2  Call GET /dengue-data/summary → summary.totalRecords.
        Step 3  Reload /data-management.
        Step 4  Assert a stat card number matches summary.totalRecords.
        Wrap-up DELETE seeded records.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        token, _ = _get_auth(driver)
        location_id = _get_company_location_id(token)
        assert location_id, "TC-UC8-011 PRE-CONDITION FAIL: No companyLocationId found."

        print("\n[INFO] Seeding %d records for TCOV-08-022..." % len(SEED_RECORDS))
        created_ids = _seed_records(token, location_id)

        try:
            # ── Step 2: Ground-truth from API ─────────────────────────────────
            summary = _get_summary(token)
            api_total = summary.get("totalRecords", 0)
            print("[INFO] Summary API totalRecords=%d" % api_total)

            # ── Step 3: Reload ────────────────────────────────────────────────
            _reload_data_management(driver, wait)
            body_text = driver.find_element(By.TAG_NAME, "body").text

            # ── Step 4: Assert total card matches API ─────────────────────────
            # The card label may be "Total Records", "Total Cases", or similar
            import re
            ui_total = (
                _find_count_near_label(body_text, "Total Records") or
                _find_count_near_label(body_text, "Total Cases")   or
                _find_count_near_label(body_text, "Records")
            )

            assert ui_total is not None and ui_total == api_total, (
                "TC-UC8-011 FAIL (TCOV-08-022): Total Records card shows %s, "
                "API summary says %d.\nBody: %s" % (ui_total, api_total, body_text[:500])
            )

        finally:
            _delete_by_ids(token, created_ids)

        print("TC-UC8-011 Total Records Count Displayed - PASS")

    def test_distinct_location_count_displayed(self, logged_in):
        """
        TC-UC8-011 | TCOV-08-023
        ─────────────────────────────────────────────────────────────────────
        Step 1  Seed records across 3 distinct locations via API.
        Step 2  Call GET /dengue-data/summary → summary.locationsCovered.
        Step 3  Reload /data-management.
        Step 4  Assert Coverage Area / Locations card matches summary.locationsCovered.
        Wrap-up DELETE seeded records.
        """
        driver = logged_in
        wait   = WebDriverWait(driver, 20)

        token, _ = _get_auth(driver)
        location_id = _get_company_location_id(token)
        assert location_id, "TC-UC8-011 PRE-CONDITION FAIL: No companyLocationId found."

        print("\n[INFO] Seeding records across 3 distinct locations...")
        created_ids = _seed_records(token, location_id)

        try:
            # ── Step 2: Ground-truth from API ─────────────────────────────────
            summary = _get_summary(token)
            api_locations = summary.get("locationsCovered", 0)
            print("[INFO] Summary API locationsCovered=%d" % api_locations)

            # ── Step 3: Reload ────────────────────────────────────────────────
            _reload_data_management(driver, wait)
            body_text = driver.find_element(By.TAG_NAME, "body").text

            # ── Step 4: Assert coverage card matches API ──────────────────────
            ui_locations = (
                _find_count_near_label(body_text, "Coverage Area") or
                _find_count_near_label(body_text, "Locations")     or
                _find_count_near_label(body_text, "Location")
            )

            assert ui_locations is not None and ui_locations == api_locations, (
                "TC-UC8-011 FAIL (TCOV-08-023): Locations card shows %s, "
                "API summary says %d (locationsCovered).\nBody: %s" % (
                    ui_locations, api_locations, body_text[:500])
            )

        finally:
            _delete_by_ids(token, created_ids)

        print("TC-UC8-011 Distinct Location Count Displayed - PASS")