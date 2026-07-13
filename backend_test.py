#!/usr/bin/env python3
"""
Comprehensive backend API tests for PHARMASCRAPE
Tests all endpoints with happy paths, validation, and error cases
"""
import requests
import time
import sys
from typing import Dict, List, Any

# Backend URL from frontend/.env
BASE_URL = "https://agent-preview-live.preview.emergentagent.com/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def log_test(name: str):
    print(f"\n{Colors.BLUE}[TEST]{Colors.RESET} {name}")

def log_pass(msg: str):
    print(f"  {Colors.GREEN}✓{Colors.RESET} {msg}")

def log_fail(msg: str):
    print(f"  {Colors.RED}✗{Colors.RESET} {msg}")

def log_info(msg: str):
    print(f"  {Colors.YELLOW}ℹ{Colors.RESET} {msg}")

# Global state for tracking created resources
created_portal_id = None
created_target_id = None
created_history_id = None
test_failures = []

def test_get_portals():
    """Test GET /api/portals - verify list returned with all seeded portals"""
    log_test("GET /api/portals - list portals")
    try:
        resp = requests.get(f"{BASE_URL}/portals", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            test_failures.append("GET /api/portals - wrong status code")
            return None
        
        portals = resp.json()
        
        if not isinstance(portals, list):
            log_fail("Response is not a list")
            test_failures.append("GET /api/portals - not a list")
            return None
        
        if len(portals) < 5:
            log_fail(f"Expected at least 5 seeded portals, got {len(portals)}")
            test_failures.append("GET /api/portals - insufficient portals")
            return None
        
        # Verify required fields
        required_fields = ["id", "name", "baseUrl", "status"]
        for portal in portals:
            for field in required_fields:
                if field not in portal:
                    log_fail(f"Portal missing required field: {field}")
                    test_failures.append(f"GET /api/portals - missing {field}")
                    return None
        
        # Verify expected portal names
        portal_names = [p["name"] for p in portals]
        expected_names = ["SUNSHOP", "CHETHANA", "VARDHAMAN", "MEDPLUS", "APOLLO"]
        for name in expected_names:
            if name not in portal_names:
                log_fail(f"Expected portal '{name}' not found")
                test_failures.append(f"GET /api/portals - missing {name}")
        
        log_pass(f"Retrieved {len(portals)} portals with all required fields")
        log_info(f"Portal names: {', '.join(portal_names)}")
        return portals
        
    except Exception as e:
        log_fail(f"Exception: {str(e)}")
        test_failures.append(f"GET /api/portals - exception: {str(e)}")
        return None

def test_post_portals():
    """Test POST /api/portals - create a new portal"""
    log_test("POST /api/portals - create portal")
    global created_portal_id
    
    try:
        payload = {
            "name": "TEST_PORTAL",
            "baseUrl": "https://test-portal.example.com",
            "status": "ACTIVE",
            "description": "Test portal created by automated tests"
        }
        
        resp = requests.post(f"{BASE_URL}/portals", json=payload, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            test_failures.append("POST /api/portals - wrong status code")
            return None
        
        portal = resp.json()
        
        if "id" not in portal:
            log_fail("Created portal missing 'id' field")
            test_failures.append("POST /api/portals - missing id")
            return None
        
        created_portal_id = portal["id"]
        
        # Verify it appears in list
        list_resp = requests.get(f"{BASE_URL}/portals", timeout=10)
        portals = list_resp.json()
        portal_ids = [p["id"] for p in portals]
        
        if created_portal_id not in portal_ids:
            log_fail("Created portal not found in subsequent GET")
            test_failures.append("POST /api/portals - not in list")
            return None
        
        log_pass(f"Created portal with id: {created_portal_id}")
        log_pass("Portal appears in subsequent GET /api/portals")
        return portal
        
    except Exception as e:
        log_fail(f"Exception: {str(e)}")
        test_failures.append(f"POST /api/portals - exception: {str(e)}")
        return None

def test_get_targets():
    """Test GET /api/targets - verify 8 seeded targets"""
    log_test("GET /api/targets - list targets")
    try:
        resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            test_failures.append("GET /api/targets - wrong status code")
            return None
        
        targets = resp.json()
        
        if not isinstance(targets, list):
            log_fail("Response is not a list")
            test_failures.append("GET /api/targets - not a list")
            return None
        
        if len(targets) < 8:
            log_fail(f"Expected at least 8 seeded targets, got {len(targets)}")
            test_failures.append("GET /api/targets - insufficient targets")
            return None
        
        # Verify required fields
        required_fields = ["id", "name", "url", "portal", "selected"]
        for target in targets:
            for field in required_fields:
                if field not in target:
                    log_fail(f"Target missing required field: {field}")
                    test_failures.append(f"GET /api/targets - missing {field}")
                    return None
        
        # Count selected vs unselected
        selected_count = sum(1 for t in targets if t["selected"])
        unselected_count = len(targets) - selected_count
        
        log_pass(f"Retrieved {len(targets)} targets with all required fields")
        log_info(f"Selected: {selected_count}, Unselected: {unselected_count}")
        return targets
        
    except Exception as e:
        log_fail(f"Exception: {str(e)}")
        test_failures.append(f"GET /api/targets - exception: {str(e)}")
        return None

def test_post_targets():
    """Test POST /api/targets - create a new target"""
    log_test("POST /api/targets - create target")
    global created_target_id
    
    try:
        payload = {
            "name": "TEST_TARGET",
            "url": "https://test-target.example.com/products",
            "portal": "SUNSHOP",
            "selected": True
        }
        
        resp = requests.post(f"{BASE_URL}/targets", json=payload, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            test_failures.append("POST /api/targets - wrong status code")
            return None
        
        target = resp.json()
        
        if "id" not in target:
            log_fail("Created target missing 'id' field")
            test_failures.append("POST /api/targets - missing id")
            return None
        
        created_target_id = target["id"]
        
        # Verify it appears in list
        list_resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        targets = list_resp.json()
        target_ids = [t["id"] for t in targets]
        
        if created_target_id not in target_ids:
            log_fail("Created target not found in subsequent GET")
            test_failures.append("POST /api/targets - not in list")
            return None
        
        log_pass(f"Created target with id: {created_target_id}")
        log_pass("Target appears in subsequent GET /api/targets")
        return target
        
    except Exception as e:
        log_fail(f"Exception: {str(e)}")
        test_failures.append(f"POST /api/targets - exception: {str(e)}")
        return None

def test_patch_targets(target_id: str):
    """Test PATCH /api/targets/{id} - update target"""
    log_test(f"PATCH /api/targets/{target_id} - update target")
    
    try:
        # First, get current state
        list_resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        targets = list_resp.json()
        target = next((t for t in targets if t["id"] == target_id), None)
        
        if not target:
            log_fail(f"Target {target_id} not found")
            test_failures.append("PATCH /api/targets - target not found")
            return False
        
        original_selected = target["selected"]
        new_selected = not original_selected
        
        # Toggle selected
        payload = {"selected": new_selected}
        resp = requests.patch(f"{BASE_URL}/targets/{target_id}", json=payload, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            test_failures.append("PATCH /api/targets - wrong status code")
            return False
        
        updated = resp.json()
        
        if updated["selected"] != new_selected:
            log_fail(f"Expected selected={new_selected}, got {updated['selected']}")
            test_failures.append("PATCH /api/targets - selection not updated")
            return False
        
        log_pass(f"Toggled selected from {original_selected} to {new_selected}")
        
        # Test 404 for unknown id
        resp_404 = requests.patch(f"{BASE_URL}/targets/unknown-id-12345", json=payload, timeout=10)
        if resp_404.status_code != 404:
            log_fail(f"Expected 404 for unknown id, got {resp_404.status_code}")
            test_failures.append("PATCH /api/targets - missing 404 for unknown id")
        else:
            log_pass("Returns 404 for unknown target id")
        
        # Test 400 for empty body
        resp_400 = requests.patch(f"{BASE_URL}/targets/{target_id}", json={}, timeout=10)
        if resp_400.status_code != 400:
            log_fail(f"Expected 400 for empty body, got {resp_400.status_code}")
            test_failures.append("PATCH /api/targets - missing 400 for empty body")
        else:
            log_pass("Returns 400 for empty update payload")
        
        return True
        
    except Exception as e:
        log_fail(f"Exception: {str(e)}")
        test_failures.append(f"PATCH /api/targets - exception: {str(e)}")
        return False

def test_delete_targets(target_id: str):
    """Test DELETE /api/targets/{id} - delete target"""
    log_test(f"DELETE /api/targets/{target_id} - delete target")
    
    try:
        resp = requests.delete(f"{BASE_URL}/targets/{target_id}", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            test_failures.append("DELETE /api/targets - wrong status code")
            return False
        
        log_pass(f"Deleted target {target_id}")
        
        # Verify 404 on subsequent delete
        resp_404 = requests.delete(f"{BASE_URL}/targets/{target_id}", timeout=10)
        if resp_404.status_code != 404:
            log_fail(f"Expected 404 on re-delete, got {resp_404.status_code}")
            test_failures.append("DELETE /api/targets - missing 404 on re-delete")
            return False
        
        log_pass("Returns 404 on subsequent delete attempt")
        return True
        
    except Exception as e:
        log_fail(f"Exception: {str(e)}")
        test_failures.append(f"DELETE /api/targets - exception: {str(e)}")
        return False

def test_bulk_select():
    """Test POST /api/targets/bulk-select - select/deselect all"""
    log_test("POST /api/targets/bulk-select - bulk select/deselect")
    
    try:
        # Set all to false
        payload = {"selected": False}
        resp = requests.post(f"{BASE_URL}/targets/bulk-select", json=payload, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            test_failures.append("POST /api/targets/bulk-select - wrong status code")
            return False
        
        # Verify all are false
        list_resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        targets = list_resp.json()
        all_false = all(not t["selected"] for t in targets)
        
        if not all_false:
            log_fail("Not all targets set to selected=false")
            test_failures.append("POST /api/targets/bulk-select - bulk false failed")
            return False
        
        log_pass(f"Set all {len(targets)} targets to selected=false")
        
        # Set all to true
        payload = {"selected": True}
        resp = requests.post(f"{BASE_URL}/targets/bulk-select", json=payload, timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            test_failures.append("POST /api/targets/bulk-select - wrong status code (true)")
            return False
        
        # Verify all are true
        list_resp = requests.get(f"{BASE_URL}/targets", timeout=10)
        targets = list_resp.json()
        all_true = all(t["selected"] for t in targets)
        
        if not all_true:
            log_fail("Not all targets set to selected=true")
            test_failures.append("POST /api/targets/bulk-select - bulk true failed")
            return False
        
        log_pass(f"Set all {len(targets)} targets to selected=true")
        return True
        
    except Exception as e:
        log_fail(f"Exception: {str(e)}")
        test_failures.append(f"POST /api/targets/bulk-select - exception: {str(e)}")
        return False

def test_extract(target_ids: List[str]):
    """Test POST /api/extract - run extraction"""
    log_test("POST /api/extract - run extraction")
    global created_history_id
    
    try:
        payload = {
            "product": "Paracetamol 500mg",
            "target_ids": target_ids[:3]  # Use first 3 targets
        }
        
        resp = requests.post(f"{BASE_URL}/extract", json=payload, timeout=30)
        
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            test_failures.append("POST /api/extract - wrong status code")
            return None
        
        entry = resp.json()
        
        # Verify required fields
        required_fields = ["id", "product", "duration", "targetsRun", "found", "outOfStock", "errors", "results"]
        for field in required_fields:
            if field not in entry:
                log_fail(f"Response missing required field: {field}")
                test_failures.append(f"POST /api/extract - missing {field}")
                return None
        
        # Verify product is uppercased
        if entry["product"] != payload["product"].upper():
            log_fail(f"Expected product '{payload['product'].upper()}', got '{entry['product']}'")
            test_failures.append("POST /api/extract - product not uppercased")
        else:
            log_pass(f"Product uppercased: {entry['product']}")
        
        # Verify targetsRun matches
        if entry["targetsRun"] != len(payload["target_ids"]):
            log_fail(f"Expected targetsRun={len(payload['target_ids'])}, got {entry['targetsRun']}")
            test_failures.append("POST /api/extract - targetsRun mismatch")
        else:
            log_pass(f"targetsRun = {entry['targetsRun']}")
        
        # Verify found + outOfStock + errors == targetsRun
        total = entry["found"] + entry["outOfStock"] + entry["errors"]
        if total != entry["targetsRun"]:
            log_fail(f"found({entry['found']}) + outOfStock({entry['outOfStock']}) + errors({entry['errors']}) != targetsRun({entry['targetsRun']})")
            test_failures.append("POST /api/extract - count mismatch")
        else:
            log_pass(f"Counts match: found={entry['found']}, outOfStock={entry['outOfStock']}, errors={entry['errors']}")
        
        # Verify results array
        if not isinstance(entry["results"], list):
            log_fail("results is not a list")
            test_failures.append("POST /api/extract - results not a list")
        elif len(entry["results"]) != entry["targetsRun"]:
            log_fail(f"results array length ({len(entry['results'])}) != targetsRun ({entry['targetsRun']})")
            test_failures.append("POST /api/extract - results length mismatch")
        else:
            log_pass(f"results array contains {len(entry['results'])} entries")
            
            # Verify result fields
            result_fields = ["targetId", "targetName", "portal", "url", "product", "status", "responseMs"]
            for result in entry["results"]:
                for field in result_fields:
                    if field not in result:
                        log_fail(f"Result missing field: {field}")
                        test_failures.append(f"POST /api/extract - result missing {field}")
                        break
        
        created_history_id = entry["id"]
        log_pass(f"Extraction completed with id: {created_history_id}")
        
        # Test validation: empty product
        resp_empty_product = requests.post(f"{BASE_URL}/extract", json={"product": "", "target_ids": target_ids[:1]}, timeout=10)
        if resp_empty_product.status_code != 400:
            log_fail(f"Expected 400 for empty product, got {resp_empty_product.status_code}")
            test_failures.append("POST /api/extract - missing 400 for empty product")
        else:
            log_pass("Returns 400 for empty product")
        
        # Test validation: empty target_ids
        resp_empty_targets = requests.post(f"{BASE_URL}/extract", json={"product": "Test", "target_ids": []}, timeout=10)
        if resp_empty_targets.status_code != 400:
            log_fail(f"Expected 400 for empty target_ids, got {resp_empty_targets.status_code}")
            test_failures.append("POST /api/extract - missing 400 for empty target_ids")
        else:
            log_pass("Returns 400 for empty target_ids")
        
        # Test validation: invalid target_ids
        resp_invalid = requests.post(f"{BASE_URL}/extract", json={"product": "Test", "target_ids": ["invalid-id-12345"]}, timeout=10)
        if resp_invalid.status_code not in [404, 200]:
            log_fail(f"Expected 404 or 200 for invalid target_ids, got {resp_invalid.status_code}")
            test_failures.append("POST /api/extract - unexpected status for invalid target_ids")
        else:
            if resp_invalid.status_code == 404:
                log_pass("Returns 404 for invalid target_ids")
            else:
                # If 200, should have empty results
                invalid_entry = resp_invalid.json()
                if invalid_entry.get("targetsRun", 0) == 0:
                    log_pass("Returns empty result for invalid target_ids")
                else:
                    log_fail("Invalid target_ids should result in 404 or empty results")
                    test_failures.append("POST /api/extract - invalid target_ids not handled properly")
        
        return entry
        
    except Exception as e:
        log_fail(f"Exception: {str(e)}")
        test_failures.append(f"POST /api/extract - exception: {str(e)}")
        return None

def test_get_history():
    """Test GET /api/history - list history"""
    log_test("GET /api/history - list history")
    
    try:
        resp = requests.get(f"{BASE_URL}/history", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            test_failures.append("GET /api/history - wrong status code")
            return None
        
        history = resp.json()
        
        if not isinstance(history, list):
            log_fail("Response is not a list")
            test_failures.append("GET /api/history - not a list")
            return None
        
        if len(history) < 6:
            log_fail(f"Expected at least 6 seeded history entries, got {len(history)}")
            test_failures.append("GET /api/history - insufficient entries")
            return None
        
        # Verify newest-first sort (timestamps should be descending)
        timestamps = [entry.get("timestamp") for entry in history if "timestamp" in entry]
        if len(timestamps) > 1:
            is_sorted = all(timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1))
            if not is_sorted:
                log_fail("History not sorted newest-first")
                test_failures.append("GET /api/history - not sorted correctly")
            else:
                log_pass("History sorted newest-first")
        
        # Verify the extraction we just created is at the top
        if created_history_id:
            if history[0]["id"] == created_history_id:
                log_pass(f"Most recent extraction ({created_history_id}) is at the top")
            else:
                log_fail(f"Expected most recent extraction at top, got {history[0]['id']}")
                test_failures.append("GET /api/history - newest entry not at top")
        
        log_pass(f"Retrieved {len(history)} history entries")
        return history
        
    except Exception as e:
        log_fail(f"Exception: {str(e)}")
        test_failures.append(f"GET /api/history - exception: {str(e)}")
        return None

def test_get_history_detail(entry_id: str):
    """Test GET /api/history/{id} - history detail"""
    log_test(f"GET /api/history/{entry_id} - history detail")
    
    try:
        resp = requests.get(f"{BASE_URL}/history/{entry_id}", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            test_failures.append("GET /api/history/{id} - wrong status code")
            return None
        
        entry = resp.json()
        
        # Verify results array is populated
        if "results" not in entry:
            log_fail("Response missing 'results' field")
            test_failures.append("GET /api/history/{id} - missing results")
            return None
        
        if not isinstance(entry["results"], list):
            log_fail("results is not a list")
            test_failures.append("GET /api/history/{id} - results not a list")
            return None
        
        if len(entry["results"]) > 0:
            log_pass(f"results array contains {len(entry['results'])} entries")
        else:
            log_info("results array is empty (may be seeded entry)")
        
        # Test 404 for unknown id
        resp_404 = requests.get(f"{BASE_URL}/history/unknown-id-12345", timeout=10)
        if resp_404.status_code != 404:
            log_fail(f"Expected 404 for unknown id, got {resp_404.status_code}")
            test_failures.append("GET /api/history/{id} - missing 404 for unknown id")
        else:
            log_pass("Returns 404 for unknown history id")
        
        return entry
        
    except Exception as e:
        log_fail(f"Exception: {str(e)}")
        test_failures.append(f"GET /api/history/{{id}} - exception: {str(e)}")
        return None

def test_delete_history(entry_id: str):
    """Test DELETE /api/history/{id} - delete history entry"""
    log_test(f"DELETE /api/history/{entry_id} - delete history entry")
    
    try:
        resp = requests.delete(f"{BASE_URL}/history/{entry_id}", timeout=10)
        
        if resp.status_code != 200:
            log_fail(f"Expected 200, got {resp.status_code}")
            test_failures.append("DELETE /api/history - wrong status code")
            return False
        
        log_pass(f"Deleted history entry {entry_id}")
        
        # Verify 404 on subsequent delete
        resp_404 = requests.delete(f"{BASE_URL}/history/{entry_id}", timeout=10)
        if resp_404.status_code != 404:
            log_fail(f"Expected 404 on re-delete, got {resp_404.status_code}")
            test_failures.append("DELETE /api/history - missing 404 on re-delete")
            return False
        
        log_pass("Returns 404 on subsequent delete attempt")
        return True
        
    except Exception as e:
        log_fail(f"Exception: {str(e)}")
        test_failures.append(f"DELETE /api/history - exception: {str(e)}")
        return False

def test_end_to_end():
    """End-to-end round trip test"""
    log_test("END-TO-END: create target -> patch -> extract -> verify in history")
    
    try:
        # 1. Create a new target
        payload = {
            "name": "E2E_TEST_TARGET",
            "url": "https://e2e-test.example.com",
            "portal": "APOLLO",
            "selected": False
        }
        resp = requests.post(f"{BASE_URL}/targets", json=payload, timeout=10)
        if resp.status_code != 200:
            log_fail(f"Failed to create target: {resp.status_code}")
            test_failures.append("E2E - target creation failed")
            return False
        
        e2e_target = resp.json()
        e2e_target_id = e2e_target["id"]
        log_pass(f"Created E2E target: {e2e_target_id}")
        
        # 2. Patch selected=true
        resp = requests.patch(f"{BASE_URL}/targets/{e2e_target_id}", json={"selected": True}, timeout=10)
        if resp.status_code != 200:
            log_fail(f"Failed to patch target: {resp.status_code}")
            test_failures.append("E2E - target patch failed")
            return False
        log_pass("Patched target to selected=true")
        
        # 3. Run extraction with this target
        resp = requests.post(f"{BASE_URL}/extract", json={"product": "E2E Test Product", "target_ids": [e2e_target_id]}, timeout=30)
        if resp.status_code != 200:
            log_fail(f"Failed to run extraction: {resp.status_code}")
            test_failures.append("E2E - extraction failed")
            return False
        
        e2e_entry = resp.json()
        e2e_entry_id = e2e_entry["id"]
        log_pass(f"Ran extraction: {e2e_entry_id}")
        
        # 4. Get history detail and verify target appears in results
        resp = requests.get(f"{BASE_URL}/history/{e2e_entry_id}", timeout=10)
        if resp.status_code != 200:
            log_fail(f"Failed to get history detail: {resp.status_code}")
            test_failures.append("E2E - history detail failed")
            return False
        
        detail = resp.json()
        if "results" not in detail or not isinstance(detail["results"], list):
            log_fail("History detail missing results array")
            test_failures.append("E2E - missing results")
            return False
        
        target_found = any(r["targetId"] == e2e_target_id for r in detail["results"])
        if not target_found:
            log_fail(f"Target {e2e_target_id} not found in extraction results")
            test_failures.append("E2E - target not in results")
            return False
        
        log_pass(f"Target {e2e_target_id} found in extraction results")
        log_pass("END-TO-END test completed successfully")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/targets/{e2e_target_id}", timeout=10)
        requests.delete(f"{BASE_URL}/history/{e2e_entry_id}", timeout=10)
        
        return True
        
    except Exception as e:
        log_fail(f"Exception: {str(e)}")
        test_failures.append(f"E2E - exception: {str(e)}")
        return False

def main():
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}PHARMASCRAPE Backend API Tests{Colors.RESET}")
    print(f"{Colors.BLUE}Base URL: {BASE_URL}{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    # Test in priority order: high -> medium -> low
    
    # HIGH PRIORITY
    portals = test_get_portals()
    targets = test_get_targets()
    test_post_targets()
    
    if created_target_id:
        test_patch_targets(created_target_id)
    
    if targets:
        target_ids = [t["id"] for t in targets]
        extraction = test_extract(target_ids)
    
    test_get_history()
    
    # MEDIUM PRIORITY
    test_post_portals()
    
    if created_history_id:
        test_get_history_detail(created_history_id)
    
    if created_target_id:
        test_delete_targets(created_target_id)
    
    # LOW PRIORITY
    test_bulk_select()
    
    if created_history_id:
        test_delete_history(created_history_id)
    
    # END-TO-END
    test_end_to_end()
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}TEST SUMMARY{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    if test_failures:
        print(f"{Colors.RED}FAILED: {len(test_failures)} test(s) failed{Colors.RESET}\n")
        for failure in test_failures:
            print(f"  {Colors.RED}✗{Colors.RESET} {failure}")
        print()
        sys.exit(1)
    else:
        print(f"{Colors.GREEN}SUCCESS: All tests passed!{Colors.RESET}\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
