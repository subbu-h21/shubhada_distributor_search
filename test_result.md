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
    working: "NA"
    file: "frontend/src/context/AppContext.js, frontend/src/lib/api.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Frontend now consumes /api endpoints via axios helper (lib/api.js). Do NOT test yet - user must approve frontend testing before invoking auto_frontend_testing_agent."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 2
  run_ui: false

test_plan:
  current_focus:
    - "GET /api/portals - list portals"
    - "GET /api/targets - list targets"
    - "POST /api/targets - create target"
    - "PATCH /api/targets/{id} - update target"
    - "DELETE /api/targets/{id} - remove target"
    - "POST /api/extract - run extraction"
    - "GET /api/history - list history"
    - "GET /api/history/{id} - history detail"
  stuck_tasks: []
  test_all: true
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Backend for PHARMASCRAPE is implemented at /app/backend/server.py. All routes prefixed with /api. Startup seeds portals (5), targets (8), history (6) if collections are empty. Extraction endpoint uses a server-side MOCK scraper with realistic latency and randomized outcomes (IN_STOCK / OUT_OF_STOCK / ERROR). Please test all endpoints end-to-end."
  - agent: "testing"
    message: "All 11 backend endpoints passed on first run. Validation (400), not-found (404), sorting (newest-first), bulk-select, and end-to-end round-trip (create target -> patch selected -> extract -> verify in history) all verified. No fixes required."
  - agent: "testing"
    message: "✅ ALL BACKEND TESTS PASSED - Comprehensive testing completed on all 11 backend endpoints. Created /app/backend_test.py with full test coverage. All high, medium, and low priority tasks verified working correctly. Key findings: (1) All 5 portals seeded correctly with required fields, (2) All 8 targets seeded (6 selected, 2 unselected), (3) CRUD operations working for portals, targets, and history, (4) Extraction endpoint properly validates input (400 for empty product/target_ids, 404 for invalid target_ids), (5) Product names correctly uppercased, (6) History sorted newest-first, (7) All validation and error handling working as expected, (8) End-to-end round trip test passed (create -> patch -> extract -> verify in history). NO ISSUES FOUND. Backend is production-ready."
