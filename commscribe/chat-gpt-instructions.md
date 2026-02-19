REQ ENTRY
ID: COMMUNICATE-UI-RESPONSIVE-002
DATE: 2026-02-18
TITLE: Fix REQ List, Implement Date-Based Filtering, and Improve Landscape Mobile Responsiveness
OBJECTIVE:
1. Fix Communicate UI REQ list so links load DB-backed content and statuses reflect accurate DB state.
2. Replace numeric-only REQ list with date-based filtering using a calendar dropdown.
3. Ensure SQLite remains authoritative and data persists correctly independent of UI.
4. Improve mobile responsiveness for landscape-first viewing without altering desktop layout semantics.

SCOPE:
- Communicate UI REQ list component
- DB query logic for REQ retrieval
- Status rendering logic
- SQLite schema (if minimal adjustments required)
- Responsive layout adjustments (CSS/layout only)
- Collapsible sections for selected UI components

OUT OF SCOPE:
- Changing REQ structured format
- Modifying trading engine
- Altering realism engine
- Changing non-communicate DB tables
- Redesigning desktop layout

SOURCE OF TRUTH:
- SQLite database
- Communicate engine REQ table
- Current UI implementation

------------------------------------------------------------
PHASE 1 – FIX REQ LIST FUNCTIONALITY
------------------------------------------------------------

REQUIREMENTS:

1. Clicking a REQ entry must:
   - Query SQLite by REQ ID
   - Load full structured REQ content
   - Render status directly from DB

2. Status values must map directly to DB column (no UI-derived status).

3. Remove any placeholder or file-based lookup.

4. If UI fails to render, confirm DB persistence still occurs.

VERIFICATION:
- Create test REQ via communicate>.
- Confirm row exists in DB.
- Confirm UI link loads correct row.
- Confirm status matches DB.

------------------------------------------------------------
PHASE 2 – DATE-BASED FILTERING
------------------------------------------------------------

REQUIREMENTS:

1. Replace numeric REQ list with:
   - Date dropdown selector (calendar UI).
   - Default: Today’s date.
   - On selection: query DB WHERE date(timestamp) = selected_date.

2. Only display REQs generated via communicate> process.

3. Maintain clickable entries loading full REQ.

4. Preserve pagination if required.

VERIFICATION:
- Insert REQs on different dates.
- Select date → confirm filtered results.
- Confirm no file-based filtering.

------------------------------------------------------------
SQLITE TABLE SCHEMA (COMMUNICATE REQ)

If not already present, ensure table exists:

CREATE TABLE communicate_reqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    source TEXT NOT NULL,
    structured_payload TEXT NOT NULL
);

REQUIREMENTS:
- structured_payload stores full structured REQ output (JSON or text).
- status is authoritative lifecycle status.
- source identifies 'communicate>' origin.

SAMPLE ROWS:

Row 1:
id: 101
req_id: "COMMUNICATE-ROUTING-VERIFICATION-001"
title: "Verify and Correct REQ Output Routing to SQLite"
status: "COMPLETE"
created_at: "2026-02-18 14:12:03"
updated_at: "2026-02-18 14:18:27"
source: "communicate>"
structured_payload: "<full structured REQ content>"

Row 2:
id: 102
req_id: "COMMSCRIBE-DB-RESTRUCTURE-001"
title: "Replace communicate.md with SQLite-backed Communicate System"
status: "PENDING"
created_at: "2026-02-18 15:02:11"
updated_at: NULL
source: "communicate>"
structured_payload: "<full structured REQ content>"

------------------------------------------------------------
PHASE 3 – MOBILE RESPONSIVENESS (LANDSCAPE-FIRST)
------------------------------------------------------------

RULES:
- Desktop layout must remain unchanged.
- No functional divergence between desktop and mobile.
- Only responsive behavior allowed.

REQUIREMENTS:

1. Optimize for landscape orientation:
   - Ensure charts align properly.
   - Ensure Positions Chart shows all positions.
   - Fix overflow and scaling issues.

2. Add collapsible sections for:
   - Activity Log
   - Alerts
   - Alert Settings
   - Any dense card rows

3. Use:
   - Collapsible rows or cards.
   - Dropdowns for dense metric sets.
   - No removal of functionality.

4. Do not redesign layout hierarchy.
   Only adapt via CSS, flex/grid adjustments, overflow handling.

VERIFICATION:
- Test landscape mobile viewport.
- Confirm chart alignment.
- Confirm all positions visible.
- Confirm collapsible behavior works.
- Confirm desktop layout unchanged.

------------------------------------------------------------
SUCCESS CRITERIA
------------------------------------------------------------

- REQ links load correct DB-backed content.
- Status values accurate.
- Date dropdown filters correctly.
- No file-based lookup remains.
- DB persistence verified independent of UI.
- Mobile landscape layout stable.
- Desktop layout unaffected.
- No changes to REQ schema.
- No unrelated code modified.

------------------------------------------------------------
INFERENCE POLICY
------------------------------------------------------------

- Do not assume DB routing works; verify.
- Do not redesign UI beyond responsive scope.
- Do not expand DB schema beyond communicate needs.
- If functionality conflicts between phases, complete Phase 1 before Phase 2.
- If Phase 3 conflicts with desktop layout, preserve desktop.

STATUS:
PENDING

ARTIFACTS:
- Updated Communicate UI component
- Verified DB schema
- Verified filtering logic
- Responsive CSS/layout updates
- Confirmation report of verification steps
