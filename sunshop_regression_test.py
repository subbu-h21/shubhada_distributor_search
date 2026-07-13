#!/usr/bin/env python3
"""
PHARMASCRAPE Sunshop Adapter Regression Test
Tests backend API endpoints after sunshop.py _search_product() rewrite
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
    """Priority 1: GET /api/portals — 5 seeded portals, CHETHANA baseUrl verification"""
    log_test("Priority 1: GET /api/portals - verify 5 seeded portals")
    try:
        resp = requests.get(f"{BASE_URL}/portals", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P1: GET /api/portals - wrong status")
            return
        
        portals = resp.json()
        
        # Filter out any test portals that might have been created
        portals = [p for p in portals if p["name"] in ["SUNSHOP", "CHETHANA", "VARDHAMAN", "MEDPLUS", "APOLLO"]]
        
        if len(portals) != 5:
            log_fail(f"Got {len(portals)} seeded portals, expected exactly 5")
            test_failures.append("P1: GET /api/portals - wrong count")
            return
        
        portal_names = [p["name"] for p in portals]
        expected = ["SUNSHOP", "CHETHANA", "VARDHAMAN", "MEDPLUS", "APOLLO"]
        
        if set(portal_names) != set(expected):
            log_fail(f"Portal names mismatch. Got: {portal_names}")
            test_failures.append("P1: GET /api/portals - wrong names")
            return
        
        # Verify CHETHANA baseUrl
        chethana = next((p for p in portals if p["name"] == "CHETHANA"), None)
        if not chethana:
            log_fail("CHETHANA portal not found")
            test_failures.append("P1: CHETHANA not found")
            return
        
        expected_url = "http://www.chethanapharma.in"
        if chethana["baseUrl"] != expected_url:
            log_fail(f"CHETHANA baseUrl = {chethana['baseUrl']}, expected {expected_url}")
            test_failures.append("P1: CHETHANA baseUrl incorrect")
            return
        
        log_pass(f"5 portals returned: {', '.join(portal_names)}")
        log_pass(f"CHETHANA baseUrl verified: {expected_url}")
        test_passes.append("P1: GET /api/portals")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P1: GET /api/portals - {e}")

def test_2_get_targets():
    """Priority 2: GET /api/targets — 6 distributors with portalType + hasCredentials, no encryptedPassword"""
    log_test("Priority 2: GET /api/targets - verify 6 distributors")
    try:
        resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P2: GET /api/targets - wrong status")
            return None
        
        targets = resp.json()
        
        # Filter out any test distributors
        seeded_targets = [t for t in targets if not t["name"].startswith("REGRESSION")]
        
        if len(seeded_targets) < 6:
            log_fail(f"Got {len(seeded_targets)} seeded distributors, expected at least 6")
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
                    log_fail(f"Missing field '{field}' in distributor {target.get('name', 'unknown')}")
                    test_failures.append(f"P2: GET /api/targets - missing {field}")
                    return None
        
        log_pass(f"{len(targets)} distributors returned with correct schema")
        log_info(f"Seeded distributors: {', '.join([t['name'] for t in seeded_targets[:6]])}")
        test_passes.append("P2: GET /api/targets")
        return targets
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P2: GET /api/targets - {e}")
        return None

def test_3_post_target_with_credentials():
    """Priority 3: POST /api/targets with credentials — hasCredentials=true, no encryptedPassword"""
    log_test("Priority 3: POST /api/targets with credentials")
    global created_distributor_id
    
    try:
        payload = {
            "name": "REGRESSION_TEST",
            "url": "https://example.com",
            "portal": "SUNSHOP",
            "portalType": "SUNSHOP",
            "username": "u",
            "password": "p",
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
        if not assert_field_equals(distributor, "username", "u", "POST response"):
            return None
        
        log_pass(f"Created distributor {created_distributor_id} with hasCredentials=true")
        test_passes.append("P3: POST /api/targets with credentials")
        return distributor
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P3: POST /api/targets - {e}")
        return None

def test_4_patch_with_password():
    """Priority 4: PATCH /api/targets/{id} with password — hasCredentials=true, no encryptedPassword"""
    log_test("Priority 4: PATCH /api/targets/{id} with new password")
    
    if not created_distributor_id:
        log_fail("No distributor ID from previous test")
        test_failures.append("P4: No distributor to test")
        return
    
    try:
        payload = {"password": "newpw"}
        
        resp = requests.patch(f"{BASE_URL}/targets/{created_distributor_id}", json=payload, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P4: PATCH password - wrong status")
            return
        
        distributor = resp.json()
        
        # Critical: encryptedPassword must NOT be in response
        if not assert_field_not_in_response(distributor, "encryptedPassword", "PATCH response"):
            return
        
        # hasCredentials must be true
        if not assert_field_equals(distributor, "hasCredentials", True, "PATCH response"):
            return
        
        log_pass(f"Password updated, hasCredentials=true, no encryptedPassword in response")
        test_passes.append("P4: PATCH with password")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P4: PATCH password - {e}")

def test_5_patch_toggle_selected():
    """Priority 5: PATCH /api/targets/{id} with selected toggle"""
    log_test("Priority 5: PATCH /api/targets/{id} toggle selected")
    
    if not created_distributor_id:
        log_fail("No distributor ID from previous test")
        test_failures.append("P5: No distributor to test")
        return
    
    try:
        # Toggle to false
        resp = requests.patch(f"{BASE_URL}/targets/{created_distributor_id}", json={"selected": False}, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P5: PATCH selected - wrong status")
            return
        
        distributor = resp.json()
        
        if not assert_field_equals(distributor, "selected", False, "PATCH response"):
            return
        
        log_pass("Selected toggle working correctly")
        test_passes.append("P5: PATCH toggle selected")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P5: PATCH selected - {e}")

def test_6_test_login_no_credentials():
    """Priority 6: POST /api/targets/{id}/test-login on distributor with NO credentials"""
    log_test("Priority 6: POST /api/targets/{id}/test-login - no credentials")
    
    try:
        # Get a distributor without credentials (one of the seeded ones)
        resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        targets = resp.json()
        
        no_creds_target = None
        for target in targets:
            if not target.get("hasCredentials", False) and not target["name"].startswith("REGRESSION"):
                no_creds_target = target
                break
        
        if not no_creds_target:
            log_fail("No distributor without credentials found")
            test_failures.append("P6: No distributor without credentials")
            return
        
        target_id = no_creds_target["id"]
        log_info(f"Testing with distributor: {no_creds_target['name']} (id: {target_id})")
        
        resp = requests.post(f"{BASE_URL}/targets/{target_id}/test-login", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P6: test-login - wrong status")
            return
        
        result = resp.json()
        
        # Should return ok=false
        if result.get("ok") != False:
            log_fail(f"Expected ok=false, got {result.get('ok')}")
            test_failures.append("P6: test-login - ok should be false")
            return
        
        # Detail should mention credentials not set
        detail = result.get("detail", "")
        if "credentials not set" not in detail.lower():
            log_fail(f"Detail should mention 'Credentials not set', got: {detail}")
            test_failures.append("P6: test-login - wrong detail message")
            return
        
        log_pass(f"test-login correctly returned ok=false with detail: '{detail}'")
        test_passes.append("P6: test-login no credentials")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P6: test-login - {e}")

def test_7_extract_no_credentials():
    """Priority 7: POST /api/extract with distributor lacking credentials — quick response < 5s"""
    log_test("Priority 7: POST /api/extract - distributor without credentials")
    global created_history_id
    
    try:
        # Get a distributor without credentials
        resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        targets = resp.json()
        
        no_creds_target = None
        for target in targets:
            if not target.get("hasCredentials", False) and not target["name"].startswith("REGRESSION"):
                no_creds_target = target
                break
        
        if not no_creds_target:
            log_fail("No distributor without credentials found")
            test_failures.append("P7: No distributor without credentials")
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
            test_failures.append("P7: extract - wrong status")
            return
        
        result = resp.json()
        created_history_id = result.get("id")
        
        # Should have results array
        if "results" not in result:
            log_fail("No results array in response")
            test_failures.append("P7: extract - no results")
            return
        
        results = result["results"]
        
        if len(results) != 1:
            log_fail(f"Expected 1 result, got {len(results)}")
            test_failures.append("P7: extract - wrong result count")
            return
        
        target_result = results[0]
        
        # Status should be LOGIN_FAILED
        if target_result.get("status") != "LOGIN_FAILED":
            log_fail(f"Expected status=LOGIN_FAILED, got {target_result.get('status')}")
            test_failures.append("P7: extract - wrong status")
            return
        
        # Duration should be quick (< 5s) because no browser launched
        if elapsed > 5:
            log_fail(f"Extraction took {elapsed:.1f}s, expected < 5s (no browser should launch)")
            test_failures.append("P7: extract - too slow")
        else:
            log_pass(f"Extraction completed quickly in {elapsed:.1f}s (no browser launched)")
        
        log_pass(f"Extraction returned LOGIN_FAILED status")
        log_info(f"History entry ID: {created_history_id}")
        test_passes.append("P7: extract no credentials")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P7: extract - {e}")

def test_8_extract_empty_product():
    """Priority 8: POST /api/extract with empty product — expect 400"""
    log_test("Priority 8: POST /api/extract - empty product validation")
    
    try:
        # Get any target
        resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        targets = resp.json()
        
        if not targets:
            log_fail("No targets available")
            test_failures.append("P8: No targets")
            return
        
        target_id = targets[0]["id"]
        
        payload = {
            "product": "",
            "target_ids": [target_id]
        }
        
        resp = requests.post(f"{BASE_URL}/extract", json=payload, timeout=10)
        
        if resp.status_code != 400:
            log_fail(f"Status {resp.status_code}, expected 400")
            test_failures.append("P8: extract empty product - wrong status")
            return
        
        log_pass("Empty product correctly rejected with 400")
        test_passes.append("P8: extract empty product validation")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P8: extract empty product - {e}")

def test_9_extract_empty_targets():
    """Priority 9: POST /api/extract with empty target_ids — expect 400"""
    log_test("Priority 9: POST /api/extract - empty target_ids validation")
    
    try:
        payload = {
            "product": "PARACETAMOL 500MG",
            "target_ids": []
        }
        
        resp = requests.post(f"{BASE_URL}/extract", json=payload, timeout=10)
        
        if resp.status_code != 400:
            log_fail(f"Status {resp.status_code}, expected 400")
            test_failures.append("P9: extract empty targets - wrong status")
            return
        
        log_pass("Empty target_ids correctly rejected with 400")
        test_passes.append("P9: extract empty targets validation")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P9: extract empty targets - {e}")

def test_10_get_history():
    """Priority 10: GET /api/history — sorted newest first, schema includes quantity, results[], screenshots"""
    log_test("Priority 10: GET /api/history - verify schema and sort order")
    
    try:
        resp = requests.get(f"{BASE_URL}/history", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P10: GET history - wrong status")
            return
        
        history = resp.json()
        
        if not isinstance(history, list):
            log_fail("Response is not a list")
            test_failures.append("P10: GET history - not a list")
            return
        
        if len(history) == 0:
            log_fail("No history entries found")
            test_failures.append("P10: GET history - empty")
            return
        
        # Verify newest first sort order
        if len(history) > 1:
            for i in range(len(history) - 1):
                current_time = history[i].get("timestamp", "")
                next_time = history[i + 1].get("timestamp", "")
                if current_time < next_time:
                    log_fail(f"History not sorted newest first: entry {i} timestamp {current_time} < entry {i+1} timestamp {next_time}")
                    test_failures.append("P10: GET history - wrong sort order")
                    return
        
        # Check schema fields
        newest = history[0]
        required_fields = ["quantity", "results"]
        for field in required_fields:
            if field not in newest:
                log_fail(f"Missing schema field: {field}")
                test_failures.append(f"P10: GET history - missing {field}")
                return
        
        # Verify results array has correct schema
        if newest.get("results"):
            result_item = newest["results"][0]
            expected_result_fields = ["targetId", "targetName", "portal", "url", "product", "status"]
            for field in expected_result_fields:
                if field not in result_item:
                    log_fail(f"Missing result field: {field}")
                    test_failures.append(f"P10: GET history - missing result {field}")
                    return
        
        log_pass(f"History retrieved with correct schema. Total entries: {len(history)}")
        log_pass("History sorted newest first")
        log_info(f"Newest entry: product={newest.get('product')}, targetsRun={newest.get('targetsRun')}")
        test_passes.append("P10: GET history")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P10: GET history - {e}")

def test_11_get_history_detail():
    """Priority 11: GET /api/history/{id} — verify items[] preserved"""
    log_test("Priority 11: GET /api/history/{id} - verify detail with items[]")
    
    if not created_history_id:
        log_fail("No history ID from previous test")
        test_failures.append("P11: No history ID")
        return
    
    try:
        resp = requests.get(f"{BASE_URL}/history/{created_history_id}", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P11: GET history detail - wrong status")
            return
        
        entry = resp.json()
        
        # Verify results array present
        if "results" not in entry:
            log_fail("No results array in detail")
            test_failures.append("P11: GET history detail - no results")
            return
        
        results = entry["results"]
        
        if len(results) == 0:
            log_fail("Results array is empty")
            test_failures.append("P11: GET history detail - empty results")
            return
        
        log_pass(f"History detail retrieved with results array (length={len(results)})")
        test_passes.append("P11: GET history detail")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P11: GET history detail - {e}")

def test_12_get_screenshot_404():
    """Priority 12: GET /api/screenshots/nonexistent.png — expect 404"""
    log_test("Priority 12: GET /api/screenshots/{filename} - nonexistent file")
    
    try:
        resp = requests.get(f"{BASE_URL}/screenshots/nonexistent.png", timeout=10)
        
        if resp.status_code != 404:
            log_fail(f"Status {resp.status_code}, expected 404")
            test_failures.append("P12: screenshot 404 - wrong status")
            return
        
        log_pass("Nonexistent screenshot correctly returns 404")
        test_passes.append("P12: screenshot 404")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P12: screenshot 404 - {e}")

def test_13_delete_target():
    """Priority 13: DELETE /api/targets/{id} — expect 200 then 404 on repeat"""
    log_test("Priority 13: DELETE /api/targets/{id} - cleanup")
    
    if not created_distributor_id:
        log_fail("No distributor ID to delete")
        test_failures.append("P13: No distributor to delete")
        return
    
    try:
        resp = requests.delete(f"{BASE_URL}/targets/{created_distributor_id}", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P13: DELETE target - wrong status")
            return
        
        result = resp.json()
        
        if not result.get("ok"):
            log_fail("Delete did not return ok=true")
            test_failures.append("P13: DELETE target - not ok")
            return
        
        # Try to delete again - should get 404
        resp = requests.delete(f"{BASE_URL}/targets/{created_distributor_id}", timeout=10)
        
        if resp.status_code != 404:
            log_fail(f"Second delete returned {resp.status_code}, expected 404")
            test_failures.append("P13: DELETE target - should be 404 on repeat")
            return
        
        log_pass(f"Distributor {created_distributor_id} deleted successfully")
        log_pass("Repeat delete correctly returns 404")
        test_passes.append("P13: DELETE target")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P13: DELETE target - {e}")

def test_14_delete_history():
    """Priority 14: DELETE /api/history/{id} — expect 200 then 404 on repeat"""
    log_test("Priority 14: DELETE /api/history/{id} - cleanup")
    
    if not created_history_id:
        log_fail("No history ID to delete")
        test_failures.append("P14: No history to delete")
        return
    
    try:
        resp = requests.delete(f"{BASE_URL}/history/{created_history_id}", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Status {resp.status_code}, expected 200")
            test_failures.append("P14: DELETE history - wrong status")
            return
        
        result = resp.json()
        
        if not result.get("ok"):
            log_fail("Delete did not return ok=true")
            test_failures.append("P14: DELETE history - not ok")
            return
        
        # Try to get it again - should get 404
        resp = requests.get(f"{BASE_URL}/history/{created_history_id}", timeout=10)
        
        if resp.status_code != 404:
            log_fail(f"History entry still accessible, status {resp.status_code}")
            test_failures.append("P14: DELETE history - still exists")
            return
        
        log_pass(f"History entry {created_history_id} deleted successfully")
        log_pass("Repeat access correctly returns 404")
        test_passes.append("P14: DELETE history")
        
    except Exception as e:
        log_fail(f"Exception: {e}")
        test_failures.append(f"P14: DELETE history - {e}")

def main():
    print(f"\n{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.CYAN}PHARMASCRAPE Sunshop Adapter Regression Test Suite{Colors.RESET}")
    print(f"{Colors.CYAN}Testing backend at: {BASE_URL}{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.YELLOW}NOTE: sunshop.py _search_product() was rewritten with smarter autocomplete{Colors.RESET}")
    print(f"{Colors.YELLOW}      This is INTERNAL to the adapter - no API contract changed{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*80}{Colors.RESET}")
    
    # Run all priority tests in order
    log_section("PORTALS & TARGETS SCHEMA TESTS")
    test_1_get_portals()
    test_2_get_targets()
    
    log_section("CREDENTIALS & SECURITY TESTS")
    test_3_post_target_with_credentials()
    test_4_patch_with_password()
    test_5_patch_toggle_selected()
    
    log_section("CREDENTIALS VALIDATION TESTS")
    test_6_test_login_no_credentials()
    test_7_extract_no_credentials()
    
    log_section("INPUT VALIDATION TESTS")
    test_8_extract_empty_product()
    test_9_extract_empty_targets()
    
    log_section("HISTORY & SCREENSHOTS TESTS")
    test_10_get_history()
    test_11_get_history_detail()
    test_12_get_screenshot_404()
    
    log_section("CLEANUP TESTS")
    test_13_delete_target()
    test_14_delete_history()
    
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
