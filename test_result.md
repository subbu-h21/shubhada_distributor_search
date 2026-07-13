#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: "Build a pixel-perfect clone of PHARMASCRAPE (Distributor Availability Lookup) — mobile-first monochrome brutalist UI with monospace typography. Frontend was built with mock data first; now backend integration (Step 3) is complete with FastAPI + MongoDB. Test all backend endpoints."

backend:
  - task: "GET /api/portals - list portals"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Endpoint lists all portals from MongoDB. Collection is seeded on startup with 5 portals (SUNSHOP, CHETHANA, VARDHAMAN, MEDPLUS, APOLLO). Verify count > 0 and required fields present (id, name, baseUrl, status)."
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Retrieved 5 portals with all required fields (id, name, baseUrl, status, description). Portal names verified: SUNSHOP, CHETHANA, VARDHAMAN, MEDPLUS, APOLLO."

  - task: "POST /api/portals - create portal"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Creates a new portal. Payload: {name, baseUrl, status?, description?}. Returns the created portal object."
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Created portal successfully with all fields. Portal appears in subsequent GET /api/portals."

  - task: "GET /api/targets - list targets"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Lists all targets sorted by created_at. Seeded with 8 default targets (6 selected, 2 unselected). Verify presence of required fields (id, name, url, portal, selected)."
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Retrieved 8 targets with all required fields (id, name, url, portal, selected). Verified 6 selected and 2 unselected as expected."

  - task: "POST /api/targets - create target"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Creates a new target. Payload: {name, url, portal, selected?}."
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Created target successfully. Target appears in subsequent GET /api/targets with correct fields."

  - task: "PATCH /api/targets/{id} - update target"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Partially updates a target (name, url, portal, selected). Used primarily for toggling selection. Should return 404 for unknown id, 400 if empty payload."
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Successfully toggled target selection. Returns 404 for unknown id. Returns 400 for empty payload. All validation working correctly."

  - task: "DELETE /api/targets/{id} - remove target"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Deletes a target by id. Returns 404 if not found."
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Deleted target successfully. Returns 404 on subsequent delete attempt as expected."

  - task: "POST /api/targets/bulk-select - select/deselect all"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "low"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Sets selected=true/false on all targets. Payload: {selected: bool}."
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Successfully set all 8 targets to selected=false, then all to selected=true. Bulk operation working correctly."

  - task: "POST /api/extract - run extraction"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Server-side MOCK scraper simulates fetching product availability across selected targets. Payload: {product, target_ids: []}. Returns a full history entry with results (status IN_STOCK/OUT_OF_STOCK/ERROR, price, mrp, stock, pack, responseMs). Validates non-empty product and target_ids. Persists entry to history collection. 400 if empty product or empty target_ids."
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Extraction working perfectly. Product uppercased correctly. targetsRun matches input. Counts (found + outOfStock + errors = targetsRun) verified. Results array contains all required fields (targetId, targetName, portal, url, product, status, responseMs). Validation working: returns 400 for empty product, 400 for empty target_ids, 404 for invalid target_ids."

  - task: "GET /api/history - list history"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Lists history sorted newest first. Seeded with 6 historical runs. Verify sort order and required fields."
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Retrieved 7 history entries (6 seeded + 1 from test extraction). Verified newest-first sort order. Most recent extraction appears at the top as expected."

  - task: "GET /api/history/{id} - history detail"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Returns single history entry with full results array. Should return 404 for unknown id. After a POST /api/extract, the new entry should be retrievable here with populated results."
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Retrieved history detail with populated results array (3 entries). Returns 404 for unknown id as expected."

  - task: "DELETE /api/history/{id} - remove history entry"
    implemented: true
    working: true
    file: "backend/server.py"
    stuck_count: 0
    priority: "low"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Deletes a history entry. Returns 404 if not found."
      - working: true
        agent: "testing"
        comment: "✅ PASSED - Deleted history entry successfully. Returns 404 on subsequent delete attempt as expected."

frontend:
  - task: "Frontend integration with real backend"
    implemented: true
    working: true
    file: "frontend/src/context/AppContext.js, frontend/src/lib/api.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Frontend now consumes /api endpoints via axios helper (lib/api.js). Do NOT test yet - user must approve frontend testing before invoking auto_frontend_testing_agent."
      - working: true
        agent: "testing"
        comment: "✅ COMPREHENSIVE E2E TESTING PASSED - Tested all pages and flows on mobile viewport (420x900). Search page: heading, subtitle, product input (prefilled 'prolomet xl 25'), 8 targets with portal badges, counter (8/8), checkbox toggle working, add target flow successful (added 'APEX MEDICAL SUPPLIES'). Run extraction: modal opens, progress indicator working, results view with stat cards (TARGETS, IN STOCK, OUT, TIME), results list with status indicators, COPY JSON button functional. History page: heading, subtitle, 3 stat cards (TOTAL RUNS=7, AVG TARGETS, FOUND), 7 history entries, detail modal opens and closes correctly. Portals page: heading, subtitle, all 5 portals visible (SUNSHOP, CHETHANA, VARDHAMAN, MEDPLUS, APOLLO), MEDPLUS has INACTIVE badge, others ACTIVE. Bottom navigation: all 3 tabs working. Font: JetBrains Mono monospace confirmed. All API calls returned 200. Zero critical console errors. Minor: clipboard permission denied in automation (expected), aria-describedby warnings (non-blocking accessibility)."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 3
  run_ui: true

test_plan:
  current_focus:
    - "Frontend integration with real backend"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Phase A + Phase B (SUNSHOP) real integration is now live. The SUNSHOP adapter successfully logs in to the real portal, navigates BILLING → ORDER, finds the distributor row, clicks Order Feed, interacts with the product autocomplete, and reads Stock. Verified live with the user's real account (SAROJ PHARMA, product PROLOMET XL 25, stock=94)."
  - agent: "testing"
    message: "All 11 backend endpoints passed on first run in earlier test session."
  - agent: "main"
    message: "Please REGRESSION-TEST all backend endpoints again after the Phase A/B refactor. Focus especially on: (1) GET/POST/PATCH/DELETE /api/targets returning distributor schema with new fields (portalType, hasCredentials, username) and NEVER returning encryptedPassword. (2) POST /api/targets with password field creates a distributor with hasCredentials=true. (3) PATCH /api/targets/{id} with password field encrypts it and sets hasCredentials=true. (4) GET /api/portals still lists 5 portals. (5) POST /api/extract with a valid distributor lacking credentials returns a history entry with a per-target LOGIN_FAILED result (no crash). (6) POST /api/targets/{id}/test-login endpoint responds 200 with ok=false and detail='Credentials not set...' when a distributor has no credentials. (7) GET /api/history and GET /api/history/{id} still return entries with the new expanded result schema (items[], loginScreenshot, searchScreenshot, resultsScreenshot). (8) GET /api/screenshots/{filename} returns 404 for missing file, and 200 image/png for existing file. DO NOT test the actual live SUNSHOP scraping (that needs real creds and is already validated by the user)."
  - agent: "testing"
    message: "✅ ALL BACKEND TESTS PASSED - Comprehensive testing completed on all 11 backend endpoints. Created /app/backend_test.py with full test coverage. All high, medium, and low priority tasks verified working correctly. Key findings: (1) All 5 portals seeded correctly with required fields, (2) All 8 targets seeded (6 selected, 2 unselected), (3) CRUD operations working for portals, targets, and history, (4) Extraction endpoint properly validates input (400 for empty product/target_ids, 404 for invalid target_ids), (5) Product names correctly uppercased, (6) History sorted newest-first, (7) All validation and error handling working as expected, (8) End-to-end round trip test passed (create -> patch -> extract -> verify in history). NO ISSUES FOUND. Backend is production-ready."
  - agent: "testing"
    message: "✅ ALL FRONTEND E2E TESTS PASSED - Comprehensive mobile-first testing completed (420x900 viewport). All pages, flows, and integrations working perfectly. Search page: product input, target list (8 items), portal badges, counter, checkbox toggle, add target flow all functional. Run extraction: modal with progress indicator, results view with stat cards, status indicators (IN_STOCK/OUT_OF_STOCK/ERROR), COPY JSON button working. History page: 7 entries (6 seeded + 1 new), stat cards, detail modal working. Portals page: all 5 portals visible with correct status badges (MEDPLUS INACTIVE, others ACTIVE). Bottom navigation working. Font: JetBrains Mono monospace confirmed. All API calls successful (200 status). Zero critical console errors. Minor non-blocking issues: clipboard permission in automation (expected), aria-describedby accessibility warnings. Screenshots captured at key points. READY FOR PRODUCTION."
  - agent: "testing"
    message: "✅ PHASE A/B REGRESSION TEST COMPLETED - 14/15 PRIORITY TESTS PASSED. Created /app/regression_test.py with comprehensive coverage of all refactored endpoints and schema changes. CRITICAL SECURITY VERIFIED: encryptedPassword field NEVER exposed in any API response (POST/GET/PATCH /api/targets). NEW SCHEMA WORKING: hasCredentials, username, portalType fields present and correct. NEW ENDPOINTS WORKING: POST /api/targets/{id}/test-login returns ok=false with 'Credentials not set' detail for distributors without credentials. GET /api/screenshots/{filename} returns 404 for nonexistent files and 200 with valid PNG for existing files. VALIDATION WORKING: POST /api/extract correctly rejects empty product (400) and empty target_ids (400). CREDENTIALS FLOW WORKING: POST /api/extract with distributor lacking credentials returns LOGIN_FAILED status quickly (1.5s, no browser launch) with correct detail message. HISTORY SCHEMA UPDATED: quantity, notFound, loginFailed, results[] with items[] array all present. Minor: GET /api/portals returns 6 portals instead of 5 (leftover TEST_PORTAL from previous test run, not a regression). All 6 seeded distributors returned correctly. NO CRITICAL ISSUES FOUND. Backend refactor successful."
