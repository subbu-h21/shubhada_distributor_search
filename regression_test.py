#!/usr/bin/env python3
"""
PHARMASCRAPE Phase A/B Refactor - Regression Test Suite
Tests the new distributor schema with credentials, test-login endpoint, and expanded history schema
"""
import requests
import time
import sys
from typing import Dict, List, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://agent-preview-live.preview.emergentagent.com/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def log_section(name: str):
    print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.CYAN}[SECTION] {name}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")

def log_test(name: str):
    print(f"\n{Colors.BLUE}[TEST]{Colors.RESET} {name}")

def log_pass(msg: str):
    print(f"  {Colors.GREEN}✓{Colors.RESET} {msg}")

def log_fail(msg: str):
    print(f"  {Colors.RED}✗ FAIL{Colors.RESET} {msg}")

def log_info(msg: str):
    print(f"  {Colors.YELLOW}ℹ{Colors.RESET} {msg}")

# Test state
test_failures = []
test_passes = []
created_distributor_id = None
created_history_id = None

def assert_field_not_in_response(data: dict, field: str, context: str):
    """Critical assertion: field must NOT be in response"""
    if field in data:
        log_fail(f"SECURITY ISSUE: {field} found in {context}")
        test_failures.append(f"{context} - {field} exposed")
        return False
    log_pass(f"{field} correctly NOT in {context}")
    return True

def assert_field_equals(data: dict, field: str, expected: Any, context: str):
    """Assert field equals expected value"""
    if field not in data:
        log_fail(f"{field} missing in {context}")
        test_failures.append(f"{context} - {field} missing")
        return False
    if data[field] != expected:
        log_fail(f"{field} = {data[field]}, expected {expected} in {context}")
        test_failures.append(f"{context} - {field} mismatch")
        return False
    log_pass(f"{field} = {expected} in {context}")
    return True

def test_1_get_portals():
    """Priority 1: GET /api/portals — 5 seeded portals returned"""
    log_test("Priority 1: GET /api/portals - verify 5 seeded portals")
    try:
        resp = requests.get(f"{BASE_URL}/portals", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P1: GET /api/portals - wrong status")
            return
        
        portals = resp.json()
        
        if len(portals) != 5:
            log_fail(f"Got {len(portals)} portals, expected exactly 5")
            test_failures.append("P1: GET /api/portals - wrong count")
            return
        
        portal_names = [p["name"] for p in portals]
        expected = ["SUNSHOP", "CHETHANA", "VARDHAMAN", "MEDPLUS", "APOLLO"]
        
        if set(portal_names) != set(expected):
            log_fail(f"Portal names mismatch. Got: {portal_names}")
            test_failures.append("P1: GET /api/portals - wrong names")
            return
        
        log_pass(f"5 portals returned: {', '.join(portal_names)}")
        test_passes.append("P1: GET /api/portals")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P1: GET /api/portals - {e}")

def test_2_get_targets():
    """Priority 2: GET /api/targets — 6 seeded distributors, no encryptedPassword"""
    log_test("Priority 2: GET /api/targets - verify 6 distributors, no encryptedPassword")
    try:
        resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P2: GET /api/targets - wrong status")
            return None
        
        targets = resp.json()
        
        if len(targets) != 6:
            log_fail(f"Got {len(targets)} distributors, expected exactly 6")
            test_failures.append("P2: GET /api/targets - wrong count")
            return None
        
        # Critical: verify encryptedPassword is NOT in any response
        for i, target in enumerate(targets):
            if not assert_field_not_in_response(target, "encryptedPassword", f"distributor {i+1}"):
                return None
        
        # Verify new schema fields present
        required_fields = ["id", "name", "url", "portal", "portalType", "hasCredentials", "selected"]
        for target in targets:
            for field in required_fields:
                if field not in target:
                    log_fail(f"Missing field '{field}' in distributor")
                    test_failures.append(f"P2: GET /api/targets - missing {field}")
                    return None
        
        log_pass(f"6 distributors returned with correct schema")
        log_info(f"Distributors: {', '.join([t['name'] for t in targets])}")
        test_passes.append("P2: GET /api/targets")
        return targets
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P2: GET /api/targets - {e}")
        return None

def test_3_post_target_with_password():
    """Priority 3: POST /api/targets with password — hasCredentials=true, no encryptedPassword"""
    log_test("Priority 3: POST /api/targets with password")
    global created_distributor_id
    
    try:
        payload = {
            "name": "REGRESSION TEST DISTRIBUTOR",
            "url": "https://www.sunshop.co.in",
            "portal": "SUNSHOP",
            "portalType": "GENERIC",
            "username": "testuser123",
            "password": "testpass456",
            "selected": True
        }
        
        resp = requests.post(f"{BASE_URL}/targets", json=payload, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P3: POST /api/targets - wrong status")
            return None
        
        distributor = resp.json()
        created_distributor_id = distributor.get("id")
        
        # Critical: encryptedPassword must NOT be in response
        if not assert_field_not_in_response(distributor, "encryptedPassword", "POST response"):
            return None
        
        # hasCredentials must be true
        if not assert_field_equals(distributor, "hasCredentials", True, "POST response"):
            return None
        
        # username should be present
        if not assert_field_equals(distributor, "username", "testuser123", "POST response"):
            return None
        
        log_pass(f"Created distributor {created_distributor_id} with hasCredentials=true")
        test_passes.append("P3: POST /api/targets with password")
        return distributor
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P3: POST /api/targets - {e}")
        return None

def test_4_get_created_distributor():
    """Priority 4: GET created distributor via list — encryptedPassword still not in response"""
    log_test("Priority 4: GET created distributor via list")
    
    if not created_distributor_id:
        log_fail("No distributor ID from previous test")
        test_failures.append("P4: No distributor to test")
        return
    
    try:
        resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P4: GET /api/targets - wrong status")
            return
        
        targets = resp.json()
        created = None
        
        for target in targets:
            if target.get("id") == created_distributor_id:
                created = target
                break
        
        if not created:
            log_fail(f"Created distributor {created_distributor_id} not found in list")
            test_failures.append("P4: Distributor not in list")
            return
        
        # Critical: encryptedPassword must NOT be in response
        if not assert_field_not_in_response(created, "encryptedPassword", "GET list response"):
            return
        
        # hasCredentials should still be true
        if not assert_field_equals(created, "hasCredentials", True, "GET list response"):
            return
        
        log_pass(f"Distributor {created_distributor_id} retrieved correctly from list")
        test_passes.append("P4: GET created distributor")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P4: GET distributor - {e}")

def test_5_patch_with_password():
    """Priority 5: PATCH /api/targets/{id} with password — hasCredentials=true, no encryptedPassword"""
    log_test("Priority 5: PATCH /api/targets/{id} with new password")
    
    if not created_distributor_id:
        log_fail("No distributor ID from previous test")
        test_failures.append("P5: No distributor to test")
        return
    
    try:
        payload = {"password": "newpassword789"}
        
        resp = requests.patch(f"{BASE_URL}/targets/{created_distributor_id}", json=payload, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P5: PATCH password - wrong status")
            return
        
        distributor = resp.json()
        
        # Critical: encryptedPassword must NOT be in response
        if not assert_field_not_in_response(distributor, "encryptedPassword", "PATCH response"):
            return
        
        # hasCredentials must be true
        if not assert_field_equals(distributor, "hasCredentials", True, "PATCH response"):
            return
        
        log_pass(f"Password updated, hasCredentials=true, no encryptedPassword in response")
        test_passes.append("P5: PATCH with password")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P5: PATCH password - {e}")

def test_6_patch_toggle_selected():
    """Priority 6: PATCH /api/targets/{id} with selected toggle"""
    log_test("Priority 6: PATCH /api/targets/{id} toggle selected")
    
    if not created_distributor_id:
        log_fail("No distributor ID from previous test")
        test_failures.append("P6: No distributor to test")
        return
    
    try:
        # Toggle to false
        resp = requests.patch(f"{BASE_URL}/targets/{created_distributor_id}", json={"selected": False}, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P6: PATCH selected - wrong status")
            return
        
        distributor = resp.json()
        
        if not assert_field_equals(distributor, "selected", False, "PATCH response"):
            return
        
        # Toggle back to true
        resp = requests.patch(f"{BASE_URL}/targets/{created_distributor_id}", json={"selected": True}, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P6: PATCH selected back - wrong status")
            return
        
        distributor = resp.json()
        
        if not assert_field_equals(distributor, "selected", True, "PATCH response"):
            return
        
        log_pass("Selected toggle working correctly")
        test_passes.append("P6: PATCH toggle selected")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P6: PATCH selected - {e}")

def test_7_test_login_no_credentials():
    """Priority 7: POST /api/targets/{id}/test-login on distributor with NO credentials"""
    log_test("Priority 7: POST /api/targets/{id}/test-login - no credentials")
    
    try:
        # First, get a distributor without credentials (one of the seeded ones)
        resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        targets = resp.json()
        
        no_creds_target = None
        for target in targets:
            if not target.get("hasCredentials", False):
                no_creds_target = target
                break
        
        if not no_creds_target:
            log_fail("No distributor without credentials found")
            test_failures.append("P7: No distributor without credentials")
            return
        
        target_id = no_creds_target["id"]
        log_info(f"Testing with distributor: {no_creds_target['name']} (id: {target_id})")
        
        resp = requests.post(f"{BASE_URL}/targets/{target_id}/test-login", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P7: test-login - wrong status")
            return
        
        result = resp.json()
        
        # Should return ok=false
        if result.get("ok") != False:
            log_fail(f"Expected ok=false, got {result.get('ok')}")
            test_failures.append("P7: test-login - ok should be false")
            return
        
        # Detail should mention credentials not set
        detail = result.get("detail", "")
        if "credentials not set" not in detail.lower():
            log_fail(f"Detail should mention 'Credentials not set', got: {detail}")
            test_failures.append("P7: test-login - wrong detail message")
            return
        
        log_pass(f"test-login correctly returned ok=false with detail: '{detail}'")
        test_passes.append("P7: test-login no credentials")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P7: test-login - {e}")

def test_8_extract_no_credentials():
    """Priority 8: POST /api/extract with distributor that has no credentials"""
    log_test("Priority 8: POST /api/extract - distributor without credentials")
    global created_history_id
    
    try:
        # Get a distributor without credentials
        resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        targets = resp.json()
        
        no_creds_target = None
        for target in targets:
            if not target.get("hasCredentials", False):
                no_creds_target = target
                break
        
        if not no_creds_target:
            log_fail("No distributor without credentials found")
            test_failures.append("P8: No distributor without credentials")
            return
        
        target_id = no_creds_target["id"]
        log_info(f"Testing extraction with: {no_creds_target['name']} (id: {target_id})")
        
        start_time = time.time()
        
        payload = {
            "product": "PARACETAMOL 500MG",
            "target_ids": [target_id]
        }
        
        resp = requests.post(f"{BASE_URL}/extract", json=payload, timeout=30)
        
        elapsed = time.time() - start_time
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P8: extract - wrong status")
            return
        
        result = resp.json()
        created_history_id = result.get("id")
        
        # Should have results array
        if "results" not in result:
            log_fail("No results array in response")
            test_failures.append("P8: extract - no results")
            return
        
        results = result["results"]
        
        if len(results) != 1:
            log_fail(f"Expected 1 result, got {len(results)}")
            test_failures.append("P8: extract - wrong result count")
            return
        
        target_result = results[0]
        
        # Status should be LOGIN_FAILED
        if target_result.get("status") != "LOGIN_FAILED":
            log_fail(f"Expected status=LOGIN_FAILED, got {target_result.get('status')}")
            test_failures.append("P8: extract - wrong status")
            return
        
        # Detail should mention credentials not set
        detail = target_result.get("detail", "")
        if "credentials not set" not in detail.lower():
            log_fail(f"Detail should mention credentials not set, got: {detail}")
            test_failures.append("P8: extract - wrong detail")
            return
        
        # Duration should be quick (< 5s) because no browser launched
        if elapsed > 5:
            log_fail(f"Extraction took {elapsed:.1f}s, expected < 5s (no browser should launch)")
            test_failures.append("P8: extract - too slow")
        else:
            log_pass(f"Extraction completed quickly in {elapsed:.1f}s (no browser launched)")
        
        log_pass(f"Extraction returned LOGIN_FAILED with detail: '{detail}'")
        log_info(f"History entry ID: {created_history_id}")
        test_passes.append("P8: extract no credentials")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P8: extract - {e}")

def test_9_extract_empty_product():
    """Priority 9: POST /api/extract with empty product — expect 400"""
    log_test("Priority 9: POST /api/extract - empty product validation")
    
    try:
        # Get any target
        resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        targets = resp.json()
        
        if not targets:
            log_fail("No targets available")
            test_failures.append("P9: No targets")
            return
        
        target_id = targets[0]["id"]
        
        payload = {
            "product": "",
            "target_ids": [target_id]
        }
        
        resp = requests.post(f"{BASE_URL}/extract", json=payload, timeout=10)
        
        if resp.status_code != 400:
            log_fail(f"Status {resp.status_code}, expected 400")
            test_failures.append("P9: extract empty product - wrong status")
            return
        
        log_pass("Empty product correctly rejected with 400")
        test_passes.append("P9: extract empty product validation")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P9: extract empty product - {e}")

def test_10_extract_empty_targets():
    """Priority 10: POST /api/extract with empty target_ids — expect 400"""
    log_test("Priority 10: POST /api/extract - empty target_ids validation")
    
    try:
        payload = {
            "product": "PARACETAMOL 500MG",
            "target_ids": []
        }
        
        resp = requests.post(f"{BASE_URL}/extract", json=payload, timeout=10)
        
        if resp.status_code != 400:
            log_fail(f"Status {resp.status_code}, expected 400")
            test_failures.append("P10: extract empty targets - wrong status")
            return
        
        log_pass("Empty target_ids correctly rejected with 400")
        test_passes.append("P10: extract empty targets validation")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P10: extract empty targets - {e}")

def test_11_get_history():
    """Priority 11: GET /api/history — new schema with quantity, results[], etc."""
    log_test("Priority 11: GET /api/history - verify new schema")
    
    try:
        resp = requests.get(f"{BASE_URL}/history", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P11: GET history - wrong status")
            return
        
        history = resp.json()
        
        if not isinstance(history, list):
            log_fail("Response is not a list")
            test_failures.append("P11: GET history - not a list")
            return
        
        if len(history) == 0:
            log_fail("No history entries found")
            test_failures.append("P11: GET history - empty")
            return
        
        # Check newest entry (should be from test_8)
        newest = history[0]
        
        # Verify new schema fields
        new_fields = ["quantity", "notFound", "loginFailed", "results"]
        for field in new_fields:
            if field not in newest:
                log_fail(f"Missing new schema field: {field}")
                test_failures.append(f"P11: GET history - missing {field}")
                return
        
        # Verify results array has items with new schema
        if newest.get("results"):
            result_item = newest["results"][0]
            expected_result_fields = ["targetId", "targetName", "portal", "url", "product", "status"]
            for field in expected_result_fields:
                if field not in result_item:
                    log_fail(f"Missing result field: {field}")
                    test_failures.append(f"P11: GET history - missing result {field}")
                    return
        
        log_pass(f"History retrieved with new schema. Total entries: {len(history)}")
        log_info(f"Newest entry: product={newest.get('product')}, targetsRun={newest.get('targetsRun')}, loginFailed={newest.get('loginFailed')}")
        test_passes.append("P11: GET history new schema")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P11: GET history - {e}")

def test_12_get_history_detail():
    """Priority 12: GET /api/history/{id} — verify items[] populated"""
    log_test("Priority 12: GET /api/history/{id} - verify detail with items[]")
    
    if not created_history_id:
        log_fail("No history ID from previous test")
        test_failures.append("P12: No history ID")
        return
    
    try:
        resp = requests.get(f"{BASE_URL}/history/{created_history_id}", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P12: GET history detail - wrong status")
            return
        
        entry = resp.json()
        
        # Verify results array present
        if "results" not in entry:
            log_fail("No results array in detail")
            test_failures.append("P12: GET history detail - no results")
            return
        
        results = entry["results"]
        
        if len(results) == 0:
            log_fail("Results array is empty")
            test_failures.append("P12: GET history detail - empty results")
            return
        
        # For LOGIN_FAILED, items should be empty array
        result_item = results[0]
        if result_item.get("status") == "LOGIN_FAILED":
            if "items" in result_item:
                if result_item["items"] != []:
                    log_fail(f"LOGIN_FAILED should have empty items[], got {result_item['items']}")
                    test_failures.append("P12: GET history detail - items not empty for LOGIN_FAILED")
                    return
                log_pass("LOGIN_FAILED result has empty items[] as expected")
            else:
                log_pass("LOGIN_FAILED result (items field may not be present for LOGIN_FAILED)")
        
        log_pass(f"History detail retrieved with results array (length={len(results)})")
        test_passes.append("P12: GET history detail")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P12: GET history detail - {e}")

def test_13_get_screenshot_404():
    """Priority 13: GET /api/screenshots/nonexistent.png — expect 404"""
    log_test("Priority 13: GET /api/screenshots/{filename} - nonexistent file")
    
    try:
        resp = requests.get(f"{BASE_URL}/screenshots/nonexistent_file_12345.png", timeout=10)
        
        if resp.status_code != 404:
            log_fail(f"Status {resp.status_code}, expected 404")
            test_failures.append("P13: screenshot 404 - wrong status")
            return
        
        log_pass("Nonexistent screenshot correctly returns 404")
        test_passes.append("P13: screenshot 404")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P13: screenshot 404 - {e}")

def test_14_delete_target():
    """Priority 14: DELETE /api/targets/{id} — cleanup"""
    log_test("Priority 14: DELETE /api/targets/{id} - cleanup")
    
    if not created_distributor_id:
        log_fail("No distributor ID to delete")
        test_failures.append("P14: No distributor to delete")
        return
    
    try:
        resp = requests.delete(f"{BASE_URL}/targets/{created_distributor_id}", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P14: DELETE target - wrong status")
            return
        
        result = resp.json()
        
        if not result.get("ok"):
            log_fail("Delete did not return ok=true")
            test_failures.append("P14: DELETE target - not ok")
            return
        
        # Verify it's gone
        resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        targets = resp.json()
        
        for target in targets:
            if target.get("id") == created_distributor_id:
                log_fail("Distributor still exists after delete")
                test_failures.append("P14: DELETE target - still exists")
                return
        
        log_pass(f"Distributor {created_distributor_id} deleted successfully")
        test_passes.append("P14: DELETE target")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P14: DELETE target - {e}")

def test_15_delete_history():
    """Priority 15: DELETE /api/history/{id} — cleanup"""
    log_test("Priority 15: DELETE /api/history/{id} - cleanup")
    
    if not created_history_id:
        log_fail("No history ID to delete")
        test_failures.append("P15: No history to delete")
        return
    
    try:
        resp = requests.delete(f"{BASE_URL}/history/{created_history_id}", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P15: DELETE history - wrong status")
            return
        
        result = resp.json()
        
        if not result.get("ok"):
            log_fail("Delete did not return ok=true")
            test_failures.append("P15: DELETE history - not ok")
            return
        
        # Verify it's gone
        resp = requests.get(f"{BASE_URL}/history/{created_history_id}", timeout=10)
        
        if resp.status_code != 404:
            log_fail(f"History entry still accessible, status {resp.status_code}")
            test_failures.append("P15: DELETE history - still exists")
            return
        
        log_pass(f"History entry {created_history_id} deleted successfully")
        test_passes.append("P15: DELETE history")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P15: DELETE history - {e}")

def main():
    print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.CYAN}PHARMASCRAPE Phase A/B Refactor - Regression Test Suite{Colors.RESET}")
    print(f"{Colors.CYAN}Testing backend at: {BASE_URL}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
    
    # Run all priority tests in order
    log_section("SCHEMA & SECURITY TESTS")
    test_1_get_portals()
    test_2_get_targets()
    test_3_post_target_with_password()
    test_4_get_created_distributor()
    test_5_patch_with_password()
    test_6_patch_toggle_selected()
    
    log_section("NEW ENDPOINTS & CREDENTIALS TESTS")
    test_7_test_login_no_credentials()
    test_8_extract_no_credentials()
    
    log_section("VALIDATION TESTS")
    test_9_extract_empty_product()
    test_10_extract_empty_targets()
    
    log_section("HISTORY & SCREENSHOTS TESTS")
    test_11_get_history()
    test_12_get_history_detail()
    test_13_get_screenshot_404()
    
    log_section("CLEANUP TESTS")
    test_14_delete_target()
    test_15_delete_history()
    
    # Summary
    print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.CYAN}TEST SUMMARY{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
    
    total_tests = len(test_passes) + len(test_failures)
    
    if test_failures:
        print(f"\n{Colors.RED}FAILED TESTS ({len(test_failures)}):{Colors.RESET}")
        for failure in test_failures:
            print(f"  {Colors.RED}✗{Colors.RESET} {failure}")
    
    if test_passes:
        print(f"\n{Colors.GREEN}PASSED TESTS ({len(test_passes)}):{Colors.RESET}")
        for passed in test_passes:
            print(f"  {Colors.GREEN}✓{Colors.RESET} {passed}")
    
    print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
    if test_failures:
        print(f"{Colors.RED}REGRESSION TEST FAILED: {len(test_failures)}/{total_tests} tests failed{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*80}{Colors.RESET}\n")
        sys.exit(1)
    else:
        print(f"{Colors.GREEN}ALL REGRESSION TESTS PASSED: {len(test_passes)}/{total_tests} tests{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*80}{Colors.RESET}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
