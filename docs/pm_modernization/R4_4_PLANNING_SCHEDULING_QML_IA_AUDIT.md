# R4.4 Planning / Scheduling — QML + Information Architecture Audit

**Read-only audit. No QML, Python, or navigation changes were made while producing
this report. No files were moved or deleted. Nothing was committed.**

Scope: exact current-state inventory of the Scheduling/Planning workspace's QML
structure and information architecture, plus a repository-evidence-backed
recommendation on how to reorganize it. This document does not implement
anything — it is the input to a future, separately-authorized implementation
pass.

---

## 1. Executive Summary

The Planning/Scheduling workspace is **not** a single monolithic page — it
already has 8 internal tabs (a custom chip-`Flow` + `StackLayout`, not
`TabBar`) plus a 9th, parallel full-page "Activity Details" drill-down with 8
of its *own* internal sections. The crowding complaint is real, but its causes
are almost entirely **information-architecture defects, not missing tab
structure**:

1. **Page-level chrome is too heavy and never changes.** A KPI strip, two
   loading overlays, two message banners, a 5-control action bar, and the
   8-tab strip all render *above* the `StackLayout` on every single tab —
   roughly six "always visible" chrome blocks compete with whatever the
   active tab actually wants to show.
2. **The same six health facts are computed once for the KPI strip and then
   recomputed with the identical formula a second time for the Diagnostics
   tab's summary table** — near-total duplication that adds screen weight
   without adding information.
3. **The full-page "Activity Details" drill-down duplicates 5 of its 8
   sections verbatim** (Calendars, Baselines, Resources, Activity Feed, and
   partially Overview) against content the corresponding top-level tab
   already shows — a genuine Level-2/Level-3 boundary violation.
4. **"Refresh" is wired independently in 6 places and "Run CPM" in 4 places**,
   all calling the exact same two controller methods with no tab-scoping —
   redundant toolbar action, not redundant functionality.
5. **The Gantt/timeline lane is non-interactive and structurally wins a fixed
   horizontal fight against the activity table** (`SplitView` gives it more
   default width *and* `fillWidth: true`), showing the same rows a second
   time with almost no informational value-add (no selection, no
   highlighting, a permanently-fake baseline outline).
6. **Two "Constraint Violations" surfaces in the same panel measure different
   things** (a deadline-lateness count vs. a real constraint-overrun table) —
   a naming collision, not a duplication, but equally confusing.
7. One genuinely well-executed area exists as a model to build on: **Resource
   Leveling is already a single, clean, self-contained tab** with no legacy
   controls left over from before this session's R4.4B–W.1 work — it does not
   need to move, split, or be promoted to its own navigation destination.

The recommended path (§28) is **not** a new PM navigation item and **not** a
retreat to one giant scrolling page. It is a **consolidation pass on the
internal tab structure that already exists**: turn the always-visible chrome
into a proper "Overview" landing tab, delete the duplicated Diagnostics
summary table and the 5 duplicated Detail-page sections, de-emphasize (not
relocate) the two periodic/administrative tabs (Baselines, Calendars), and
leave Resource Leveling exactly where it is.

---

## 2. Current Route / Navigation

Routing is two-layered, verified from source (not from prior modernization
docs):

- **Shell route layer** (`src/ui_qml/modules/project_management/routes.py`,
  `build_project_management_routes()`): only **one** route has
  `appears_in_navigation=True` — `project_management.workspace` ("Project
  Management" / group "Workspaces"), loading
  `qml/workspace/ProjectManagementWorkspace.qml`. Ten more routes (one per PM
  sub-workspace key) are registered with `appears_in_navigation=False` as
  deep-link/compatibility aliases, including **`project_management.scheduling`**
  → `qml/workspace/compatibility/SchedulingRoute.qml`.
- **In-page workspace navigation layer**
  (`PMWorkspaceNavigationController`, exposed as `pmCatalog.pmNavigation`)
  drives the sidebar *inside* the single canonical shell page.
  `navigationItems` includes:

  ```
  { "id": "scheduling", "label": "Planning", "group": "Work", "icon": "calendar" }
  ```

- **Exact user-facing label: "Planning"** — not "Scheduling", not "Schedule".
  This label lives only in the navigation-controller data; every other layer
  (the compatibility route's descriptor title `"Scheduling"`, the
  `workspaceKey` `"scheduling"`, every class/file name, the presenter/view-model
  module names) says "Scheduling". **This is a real naming inconsistency**:
  anyone searching code or docs for "Planning" will find almost nothing;
  anyone reading the sidebar has no reason to search for "Scheduling."
- **Nav group**: "Work" (alongside "Projects", "Tasks").
- **Icon**: `"calendar"`.
- **Root QML**: `src/ui_qml/modules/project_management/qml/workspaces/scheduling/SchedulingWorkspacePage.qml`
  (457 lines), reached only via a hard-coded `key → file` entry in the
  canonical shell's `Repeater`/`Loader` — **there is no direct top-level shell
  route to Scheduling**; you always land on it through the one canonical PM
  shell.
- **Controller**: `ProjectManagementSchedulingWorkspaceController`
  (`controllers/scheduling/scheduling_workspace_controller.py`), exposed as
  `pmCatalog.schedulingWorkspace`.
- **Presenter**: `ProjectSchedulingWorkspacePresenter`
  (`presenters/scheduling/scheduling_workspace_presenter.py`).
- **Compatibility alias**: exactly one — `project_management.scheduling`,
  bridging via `SchedulingRoute.qml`, which loads the *same* canonical shell
  and forces the `scheduling` destination selected. No other legacy alias
  exists.
- **`SchedulingWorkspace.qml`** (the 5-line `SchedulingWorkspacePage {}`
  wrapper) is **test-only** — its sole reference anywhere in the repository is
  an architecture-guardrail test asserting the file's text; it is never
  loaded by the canonical shell or any route. This is a repeated pattern
  across all 10 PM workspaces, not unique to Scheduling.

---

## 3. Exact QML File Tree

```
SchedulingWorkspacePage.qml  [ROOT PAGE] [LIVE]
 ├─ SchedulingWorkspaceState.qml            [non-visual state/logic] [LIVE]
 ├─ LazyObjectLoader → dialogs/SchedulingDialogHost.qml   [DIALOG] [CONDITIONALLY LIVE]
 │    └─ AppWidgets.EntityDialog "createBaselineDialog"  (shared)
 ├─ components/SchedulingActionBar.qml       [TOOLBAR] [LIVE]  (page-level instance)
 ├─ (inline tab strip: Flow + Repeater(state.panelTabs), not a separate file)
 ├─ StackLayout  — 8 panels, all mounted simultaneously, one visible at a time
 │   ├─ panels/SchedulingActivityTimelinePanel.qml   [TAB/PAGE] [LIVE]
 │   │    ├─ components/SchedulingPanelFrame.qml     [LIVE]
 │   │    ├─ AppWidgets.TableToolbar (shared)
 │   │    ├─ SplitView
 │   │    │    ├─ AppWidgets.DataTable (shared)                — activity/schedule grid
 │   │    │    ├─ AppWidgets.TablePaginationBar (shared)
 │   │    │    ├─ AppControls.CenteredDialog "activityFilterPopup"  [DIALOG] [CONDITIONALLY LIVE]
 │   │    │    └─ panels/SchedulingTimelinePanel.qml  [TIMELINE/GANTT] [LIVE]
 │   │    │         └─ ListView + Repeater(8 gridlines) — hand-rolled Gantt lane
 │   │    └─ components/SchedulingActionBar.qml  [LIVE] (independent instance: Refresh/Run CPM)
 │   ├─ panels/SchedulingDiagnosticsPanel.qml   [PANEL, table-heavy] [LIVE]
 │   │    ├─ SchedulingPanelFrame + SchedulingActionBar [LIVE]
 │   │    └─ AppWidgets.DataTable x2 (diagnostics summary, constraint violations)
 │   ├─ panels/SchedulingResourcesPanel.qml     [PANEL] [LIVE]
 │   │    └─ SchedulingPanelFrame + SchedulingActionBar + DataTable x1
 │   ├─ panels/SchedulingResourceLevelingPanel.qml  [PANEL + INSPECTOR + DIALOG] [LIVE]
 │   │    ├─ SchedulingPanelFrame + SchedulingActionBar
 │   │    ├─ AppWidgets.InlineMessage x1 (+ Repeater of per-conflict messages)
 │   │    ├─ AppWidgets.DataTable x1 (proposed moves)
 │   │    ├─ AppWidgets.InspectorPanel  [INSPECTOR]
 │   │    └─ AppControls.ConfirmationDialog "applyConfirmDialog"  [DIALOG] [CONDITIONALLY LIVE]
 │   ├─ panels/SchedulingBaselinesPanel.qml     [PANEL, heaviest] [LIVE]
 │   │    ├─ SchedulingPanelFrame + SchedulingActionBar (5 actions + 2 combos + checkbox)
 │   │    └─ AppWidgets.DataTable x3 (compare, register, variance)
 │   ├─ panels/SchedulingDelaysPanel.qml        [PANEL] [LIVE]
 │   │    └─ SchedulingPanelFrame + SchedulingActionBar + DataTable x1
 │   ├─ panels/SchedulingCalendarsPanel.qml     [PANEL] [LIVE]
 │   │    └─ SchedulingPanelFrame + SchedulingActionBar + calculator card + DataTable x2
 │   └─ panels/SchedulingActivityFeedPanel.qml  [PANEL] [LIVE]
 │        └─ SchedulingPanelFrame + SchedulingActionBar + AppWidgets.ActivityFeed
 └─ Loader (active: state.detailOpen) — mutually exclusive with the block above
      └─ AppWidgets.SectionDetailPage (shared)  [SECTION HOST]
           ├─ AppWidgets.ContextualActionToolbar (shared)
           ├─ SectionScopedInlineMessage x2 (shared)
           └─ panels/SchedulingDetailPanel.qml  [INSPECTOR / 8-SECTION DETAIL] [LIVE, 529 LOC]
                └─ 8x AppWidgets.LazySectionLoader  [each CONDITIONALLY LIVE]
                     _sec0 Overview        → field cards (task facts)
                     _sec1 Dependencies    → DataTable (read-only mirror of Task Detail)
                     _sec2 Constraints     → DataTable (constraint_type/deadline/actual locks)
                     _sec3 Calendars       → DataTable x2   ── duplicates Calendars tab verbatim
                     _sec4 Baselines       → DataTable x2   ── duplicates Baselines tab verbatim
                     _sec5 Resources       → DataTable x1   ── duplicates Resources tab verbatim
                     _sec6 Activity Feed   → ActivityFeed   ── duplicates Activity Feed tab verbatim
                     _sec7 Change Impact   → 3 metric tiles + DataTable

── Test-only / not reachable from production render path ──
SchedulingWorkspace.qml  [LEGACY/ALIAS WRAPPER] [TEST-ONLY]
```

**Liveness note:** the `StackLayout` keeps all 8 tab panels resident
(instantiated) at all times — "inactive" tabs are hidden, not destroyed — so
none of the 8 are "conditionally live" in the lazy sense; only the dialogs,
the filter popup, and the 8 Detail-page sections use real lazy loaders
(`LazyObjectLoader`/`LazySectionLoader`).

---

## 4. QML Complexity / LOC

| File | LOC | Layout containers | Tables/Lists | Dialogs | Signal handlers | Controller calls | Business logic in-file? |
|---|---|---|---|---|---|---|---|
| `SchedulingWorkspacePage.qml` | **457** | 1 ColumnLayout, 1 StackLayout, 1 Flow | 1 Repeater (tab strip) | 0 direct (1 via lazy loader) | ~14 | ~22 | **Yes** — 18 default-model fallback shapes hardcoded |
| `SchedulingWorkspaceState.qml` | 130 | 0 (non-visual) | 0 | 0 | 3 | 4 | **Yes** — column-state merge algorithm, 13-column base schema |
| `panels/SchedulingActivityTimelinePanel.qml` | 245 | 1 ColumnLayout + SplitView | 1 DataTable, 1 Gantt panel | 1 | ~8 | ~10 | Yes — column-state helper functions |
| `panels/SchedulingTimelinePanel.qml` | 234 | 1 ColumnLayout, 2 RowLayout | 1 ListView + Repeater(8) | 0 | 0 | 0 | **Yes** — date-window-to-pixel Gantt math |
| `panels/SchedulingDiagnosticsPanel.qml` | 106 | 1 ColumnLayout | 2 DataTable | 0 | 3 | 4 | No |
| `panels/SchedulingResourcesPanel.qml` | 80 | 1 ColumnLayout | 1 DataTable | 0 | 3 | 3 | No |
| `panels/SchedulingResourceLevelingPanel.qml` | 181 | 1 ColumnLayout + 3 inline + 3 RowLayout | 1 DataTable + 1 Repeater | 1 | 3 | 2 | Yes — selected-move lookup |
| `panels/SchedulingBaselinesPanel.qml` | 215 | 1 ColumnLayout | 3 DataTable | 0 | ~8 | 9 | **Yes** — authorization-gated action-list computation |
| `panels/SchedulingDelaysPanel.qml` | 93 | 1 ColumnLayout | 1 DataTable | 0 | 3 | 3 | Minor — row-lookup on activation |
| `panels/SchedulingCalendarsPanel.qml` | 271 | 1 ColumnLayout + 2 RowLayout + 2 inline | 2 DataTable + 1 Repeater | 0 | ~6 | 4 | Yes — checked-days filter |
| `panels/SchedulingActivityFeedPanel.qml` | 82 | 1 ColumnLayout | 1 ActivityFeed | 0 | 2 | 1 | Yes — client-side search filter |
| `panels/SchedulingDetailPanel.qml` | **529 ⚠ &gt;500** | 4 nested ColumnLayout (per-section) | 8 DataTable + 1 ActivityFeed + 2 Repeater | 0 | 0 own | 1 | **Yes** — 8-way section-height switch |
| `components/SchedulingActionBar.qml` | 57 | 2 RowLayout | 1 Repeater | 0 | 1 | 0 | No |
| `components/SchedulingPanelFrame.qml` | 127 | 3 (Column/Row mix) | 1 Repeater | 0 | 2 | 0 | No |
| `dialogs/SchedulingDialogHost.qml` | 74 | 0 | 0 | 1 | 2 | 1 | Yes — result/error branching |

**Files over threshold:** `SchedulingDetailPanel.qml` (529, &gt;500) and
`SchedulingWorkspacePage.qml` (457, &gt;300). No file exceeds 800 LOC. These two
are exactly the files this audit's recommendation (§28, §36) reduces —
`SchedulingDetailPanel.qml` by deleting 5 duplicated sections, and
`SchedulingWorkspacePage.qml` by moving its always-visible chrome into a
proper Overview tab.

**Cross-cutting complexity finding:** real business logic (Gantt bar
positioning math, authorization-gated action lists, column-state merge
algorithms, 8-way section-height switches) is embedded directly in QML files
rather than delegated to the Python presenter/controller layer in at least 4
places. This raises unit-testability and duplication risk independent of the
crowding question, and is flagged for future attention but is **not** part of
this audit's IA recommendation (would require behavior changes, out of scope
here).

---

## 5. Current Visual Hierarchy

```
Planning (sidebar label) / SchedulingWorkspacePage.qml
────────────────────────────────────────────────────────────
[always visible, identical on every tab, rendered above the StackLayout]

  KPI strip                 8 tiles: Activities / Critical / Delayed /
                             Open ends / Infeasible / Baselines / Calendar /
                             Overloads
  Loading overlay           "Loading scheduling data..." (conditional)
  Busy overlay              "Applying planning changes..." (conditional)
  Error banner               (conditional)
  Success banner             (conditional)
  Action bar                [Refresh] [Run CPM]  Project▾ Baseline▾ Calendar▾
  Tab strip (8 chips)       [Activity & Timeline][Diagnostics][Resources]
                            [Resource Leveling][Baselines][Delays]
                            [Calendars][Activity Feed]

[exactly one of the following, per active tab — StackLayout]

  ┌ Activity & Timeline ─────────────────────────────────────┐
  │ [Search] [Filter] [Customize]                            │
  │ ┌─────────────────────────┬──────────────────────────┐   │
  │ │ Activity table (13 cols,│ Gantt lane (non-interactive,│ │
  │ │ 10 visible by default)  │ wider by default, fillWidth)│ │
  │ └─────────────────────────┴──────────────────────────┘   │
  └────────────────────────────────────────────────────────────┘

  ┌ Diagnostics ───────────────────────────────────────────────┐
  │ [Refresh Diagnostics] [Run CPM]                             │
  │ Diagnostics summary table (6 rows — ~duplicates KPI strip)  │
  │ "Constraint Violations" table (real overruns — name collides│
  │  with the summary row of the same name above it)            │
  └───────────────────────────────────────────────────────────────┘

  ┌ Resources ─────────────┐  ┌ Resource Leveling ───────────────┐
  │ [Refresh][Run CPM]      │  │ [Preview]                        │
  │ Resource loading table  │  │ before/after metrics + conflicts │
  └──────────────────────────┘  │ moves table + inspector          │
                                 │ [Apply Leveling Plan] (confirm)  │
                                 └───────────────────────────────────┘

  ┌ Baselines (heaviest tab) ──────────────────────────────────┐
  │ [Save][Submit][Approve][Reject][Archive]  A▾ B▾ ☐Unchanged  │
  │ Compare table / Register table / Approval-Time Variance     │
  └────────────────────────────────────────────────────────────┘

  ┌ Delays ─────┐  ┌ Calendars ──────────────┐  ┌ Activity Feed ─┐
  │ delayed tbl │  │ working-week + calc card │  │ feed list       │
  └─────────────┘  │ summary tbl + holiday tbl│  └─────────────────┘
                    └────────────────────────────┘

[mutually exclusive full-screen replacement, not an overlay]

  Activity Details (opened by row-activation; hides everything above)
    Back  |  Overview / Dependencies / Constraints / Calendars /
             Baselines / Resources / Activity Feed / Change Impact
    (5 of these 8 sections duplicate a top-level tab's table verbatim)
```

**What competes for first-screen attention:** the KPI strip, both banners'
conditional space, the action bar, and the 8-tab strip are ALL present before
a single byte of tab-specific content renders — on the default landing tab
("Activity & Timeline"), the user additionally gets a toolbar, a 10-column
table, and a competing Gantt lane, all above the fold at typical desktop
heights (quantified in §18).

---

## 6. Current Sections

The full 26-row section inventory (purpose / file / data source / user
question / editable / scope / always-visible / collapsible / lazy /
height) was produced in detail during evidence-gathering and is
condensed here to the sections material to the IA decision; the complete
table is preserved in the underlying research transcript if needed for
implementation follow-up.

| Section | Purpose | Always visible? | Editable? | Notably duplicated? |
|---|---|---|---|---|
| KPI strip | Health at a glance (8 metrics) | **Yes, every tab** | No | Yes — vs. Diagnostics summary table |
| Action bar | Project/Baseline/Calendar scope + Refresh/Run CPM | **Yes, every tab** | Yes (selectors) | Yes — Refresh/Run CPM re-declared in 4 other panels |
| Activity table + Gantt | Primary schedule grid + timeline | Tab-gated | Read-only (+ filter/sort) | Gantt duplicates table's rows visually |
| Diagnostics summary table | 6-row health recap | Tab-gated | No | **Yes — recomputes KPI strip's own formulas** |
| Constraint Violations table | Real constraint-type overruns | Tab-gated | No | Name collides with the row above it, not a true duplicate |
| Resources table | Per-resource allocation pressure | Tab-gated | No | Duplicated in Detail §Resources |
| Resource Leveling (Preview/Apply/moves/inspector) | Leveling decision workflow | Tab-gated, and data itself is lazy (only after "Preview") | Yes (mutating) | **No duplication found — clean** |
| Baselines (3 tables + 5 actions) | Governance: freeze/approve/compare | Tab-gated | Yes | Compare+Register duplicated in Detail §Baselines |
| Delays table | Late-activity detail | Tab-gated | No | Overlaps Activity table + KPI "Delayed" |
| Calendars (2 tables + calculator) | Calendar definition (read-only) + ad hoc day-count tool | Tab-gated | Calculator only | Duplicated in Detail §Calendars |
| Activity Feed | Narrative event log | Tab-gated | No | Duplicated in Detail §Activity Feed (minus search) |
| Detail page, 8 sections | Per-activity drill-down | Full-screen, mutually exclusive with tabs | Read-only (except Change Impact trigger) | 5 of 8 sections duplicate a tab verbatim |

---

## 7. Current Actions

| Action | Real call | Duplicated? |
|---|---|---|
| "Refresh" | `workspaceController.refresh()` | **6 independent instances** (root, Diagnostics, Resources, Delays, Calendars, Activity Feed) — every one reloads the *entire* workspace, not the local tab |
| "Run CPM" | `workspaceController.recalculateSchedule()` | **4 independent instances** (root, Diagnostics, Resources, Delays) |
| Project/Baseline/Calendar selectors | `selectProject`/`selectBaseline`/`selectCalendar` | Calendar selector also re-declared inside the Calendars tab |
| Filter/Apply/Clear (Activity table) | `setStatusFilter`/`setShowCriticalOnly`/`setShowDelayedOnly`/`clearFilters` | No |
| Customize columns | `saveTableColumnState` | 6 independent instances, one per table, each scoped correctly to its own table |
| "Preview" | `previewResourceLeveling()` | No — real, load-bearing mutation |
| "Apply Leveling Plan" (confirm-gated) | `applyResourceLeveling()` | No |
| Save/Submit/Approve/Reject/Archive (Baselines) | `createBaseline`/`submitBaseline`/`approveBaseline`/`rejectBaseline`/`deleteBaseline` | "Archive" label calls `deleteBaseline` — **label/intent mismatch worth fixing independently of IA** |
| "Calculate Days" | `calculateWorkingDays` | No |
| "Run Impact Analysis" | `computeScheduleImpact({})` | Conceptually duplicates Task Detail's own, differently-wired schedule-impact preview (`TasksScheduleImpactSection.qml`) — a cross-workspace consistency risk, not an IA placement problem |

**Flagged toolbar mixing:** page-wide, expensive, schedule-mutating actions
("Refresh", "Run CPM") sit in the *identical, visually undifferentiated*
`SchedulingActionBar` component that also hosts tab-local, low-stakes actions
(search, customize) in Diagnostics/Resources/Delays/Calendars — a user has no
visual cue that clicking "Refresh Diagnostics" reloads the whole workspace,
not just that table.

---

## 8. Current Tabs / Navigation

**Direct answer: Scheduling already has 8 internal tabs — it is not one giant
page.** The tab strip is a hand-rolled `Flow`+`Repeater` of chip buttons (not
`TabBar`/`ButtonGroup`/`SwipeView`), driving a `StackLayout` by positional
index. Order (verbatim, `SchedulingWorkspaceState.qml:24-33`):

1. `activity_timeline` — "Activity & Timeline" (default)
2. `diagnostics` — "Diagnostics"
3. `resources` — "Resources"
4. `resource_leveling` — "Resource Leveling"
5. `baselines` — "Baselines"
6. `delays` — "Delays"
7. `calendars` — "Calendars"
8. `activity_feed` — "Activity Feed"

Each chip supports an optional numeric badge (`modelData.count`) that no
current tab actually populates — dead affordance, not dead code path.

**One internal sub-navigation exists beneath a tab**: the Activity & Timeline
tab's `SplitView` (table pane + Gantt pane) is itself a form of internal
layout-level navigation that a reader could easily miss when scanning for
"tabs."

**The real problem is tab *content density and duplication*, not the
existence of tabs**: several tabs stack 2–3 unrelated tables in one scrolling
column with only cosmetic connections (e.g., Baselines' three tables share one
search box that likely doesn't even filter all three), and a *parallel*,
non-tab surface (the Detail page) re-presents 5 of the 8 tabs' content a
second time.

---

## 9. Current Inspector

Exactly **one** true `AppWidgets.InspectorPanel` exists in the whole
Scheduling tree: the Resource Leveling tab's move inspector.

- **Opens on:** row selection in the leveling-moves table (`visible:
  root._selectedMove !== null`).
- **Shows:** task name/status header + 8 fields (WBS, Old Start, New Start,
  Shift, Resources, Reason, Float before→after, Deadline warning).
- **Width:** fixed, `Theme.AppTheme.inspectorWidth` (theme-driven constant,
  not resizable, no `SplitView` handle).
- **Closes via:** the panel's own "×", which clears the table's row
  selection (one-way derived visibility, no independent open/closed flag).
- **Survives tab changes:** yes, incidentally — because `StackLayout` keeps
  all 8 panels resident, leaving and returning to the Resource Leveling tab
  preserves the selection and thus the inspector state.
- **Overlaps Task Detail?** Minimally — most fields (WBS, dates, float) are
  basic task facts Task Detail would show too, but the leveling-specific
  facts (shift, reason, deadline warning, before/after comparison) are
  genuinely unique to this workflow.

The **Detail page** (`SchedulingDetailPanel.qml`) is a *different* pattern —
a full-page takeover (`AppWidgets.SectionDetailPage`), not a side/inspector
panel, with zero `InspectorPanel`/`SplitView` usage inside it. It is best
understood as a second, parallel "Level 3" surface with its own 8-way
internal section switcher, not an inspector in the same sense as Resource
Leveling's.

**Verdict on inspector density contributing to crowding:** the single real
inspector is well-scoped and not a crowding contributor. The Detail page,
however, *is* a contributor — not through visual density in the moment (it
replaces the whole screen), but through **duplication debt**: 5 of its 8
sections exist only because building a fresh mini-page per activity was
easier than teaching the existing tabs to filter to a selection, which is
exactly backwards from a maintainable IA.

---

## 10. Current Tables

Every table in the workspace (11 across the 8 tabs, plus 8 more inside the
Detail page, plus one inside a Change-Impact section) is `AppWidgets.DataTable`
bound to a controller-backed `DynamicTableModel` — **no client-side-only
`rows:` arrays anywhere in this workspace**, which is a genuine architectural
strength worth preserving through any redesign.

Duplication clusters confirmed by direct column/model comparison:

| Duplicated table | Tab location | Detail-page location |
|---|---|---|
| Calendar Summary + Holiday | Calendars tab | `_sec3` (byte-for-byte identical columns/model) |
| Baseline Compare + Register | Baselines tab | `_sec4` (near-identical, one cosmetic column-key difference) |
| Resource loading | Resources tab | `_sec5` (identical) |
| Activity Feed | Activity Feed tab | `_sec6` (identical, minus search) |

Not duplicated: the Approval-Time Variance table (Baselines tab only),
Dependencies and Constraints tables (Detail page only, no tab equivalent),
Change Impact table (Detail page only).

**Column customization/persistence** exists only for the Activity table
(`activityTableId`, real persisted column order/visibility). Every other
table's "Customize" button is session-only (no persistence), and the
Constraint Violations table in Diagnostics has **no toolbar at all** — no
search, no customize — an inconsistency, not a deliberate simplification.

**Task-level fact fragmentation:** `taskName`/dates/`status`/`critical` recur
independently across the Activity table, Delays table, Diagnostics'
violations table, and the Baseline Compare table — five separate renderings
of "which activity, what dates, what status" with zero cross-highlighting
between them.

---

## 11. Current KPIs

Eight KPI tiles, always visible, computed once in
`presenters/scheduling/overview_builder.py`:

| Label | Classification |
|---|---|
| Activities | ESSENTIAL |
| Critical | ESSENTIAL |
| Delayed | USEFUL — but duplicated verbatim by the Diagnostics tab |
| Open ends | USEFUL — but its ONLY other appearance is the same count a second time in Diagnostics; no drill path to see *which* activities |
| Infeasible | ESSENTIAL — R4.4's own constraint-aware infeasibility signal |
| Baselines | SECONDARY — a raw count with no immediate decision it supports on this screen |
| Calendar | SECONDARY / MISPLACED — "8h, 2 holiday(s)" is calendar trivia, not a planning-health fact peers to "Critical"/"Infeasible" |
| Overloads | USEFUL — duplicated verbatim by Diagnostics |

Additionally, **3 different bespoke "stat card" implementations** exist with
no shared component: the `KpiStrip` pills, the Resource Leveling panel's
plain-`Text` before/after row, and the Change Impact section's hand-rolled
`Rectangle` tiles. None share styling/sizing logic.

**KPI/Diagnostics duplication is the single largest, cheapest-to-fix crowding
contributor in the whole workspace** — 5 of 6 Diagnostics summary rows
(Critical Path Length, Open Ends, Infeasible, Delayed, Resource Conflicts) are
the identical number computed a second time; only "Constraint Violations"
(itself confusingly named, see §13) adds anything the KPI strip doesn't
already say.

No KPI/removal is recommended by this audit — that is an implementation
decision (§39, deferred). This section only classifies.

---

## 12. Current Dependencies UI

**No project-wide dependency table, graph, or diagnostic exists anywhere in
Scheduling.** The one project-wide dependency fetch that occurs
(`list_project_dependencies`) is used *only* as an internal input to the
"Open Ends" KPI/Diagnostics count — it is never rendered as rows.

The **only** rendered dependency content is the Detail page's Dependencies
section (`_sec1`): a read-only table (Related Activity / Type / Lag /
Direction / Status / Network Note) explicitly labeled *"Read-only predecessor
and successor visibility from the current schedule network"* — no CRUD, no
add/edit/remove action anywhere in Scheduling. Task Detail's own Dependencies
section already owns CRUD elsewhere in the app.

**Conclusion:** this is a reasonable, intentional split (Scheduling = context
view; Task Detail = CRUD), not duplication of *editing* capability — but it
does duplicate the *display* of the same relationships, and it is only
reachable by drilling into an individual activity, with no project-wide
"which activities have broken dependency chains" view at all (a real gap
underneath the "Open Ends" KPI, which only ever shows a count).

---

## 13. Current Constraints UI

**Confirmed: the old synthetic "Deadline = Finish No Later Than" mislabeling
is gone.** No occurrence of that string exists anywhere in the current
QML/presenter tree; `formatters.py`'s `constraint_label_for_activity()`
implements an explicit precedence (actual-end lock → actual-start lock → real
constraint type → Deadline → planned-start anchor → Open) with a defensive
comment specifically warning against re-introducing the conflation.

Constraint facts are distributed across four surfaces, each with a distinct
role:

1. **Diagnostics tab** — a "Constraint Violations" *summary row* (actually a
   deadline-lateness count) and a separately-fetched "Constraint Violations"
   *table* (the real constraint-type overrun feed) — **same label, two
   different metrics, in the same panel.** This is the audit's clearest
   single naming-collision defect.
2. **Detail page, Constraints section** — the only place a planner sees the
   raw constraint value/date for one activity, correctly disambiguated by
   type (real constraint / Deadline / Actual Start Lock / Actual Finish
   Lock).
3. **Detail page, Overview section** — a condensed one-line constraint
   summary label next to the raw deadline date (a legitimate "quick glance vs.
   full table" pairing, one tab apart from #2 in the same Detail page).
4. **Activity table's "Constraint" column** — per-row, workspace-wide, but
   **hidden by default**.

**Also found (unprompted but directly relevant):** the Detail page's Overview
status label (`detail_builder.py`) checks only `is_critical`, never
`is_infeasible` — unlike every other criticality-reporting surface in the
workspace, which uses the canonical Infeasible-&gt;Critical-&gt;Normal precedence.
An activity that is infeasible-but-not-critical will show as merely
"Normal"/its raw status in the Detail header while its own row in the
Activity table (and the KPI strip) correctly says "Infeasible." This is a
correctness bug, not an IA placement question, but it directly affects
whether the audit's recommended "what stays in the Inspector" fact set (§31)
can be trusted as-is.

**Conclusion:** no dedicated Constraints tab exists, and the evidence does not
support creating one — the four current surfaces serve genuinely different
scopes (aggregate violations vs. per-activity full detail vs. quick-glance vs.
workspace-wide column). The naming collision and the infeasibility-check bug
are the real defects, not the absence of a tab.

---

## 14. Current Resource Leveling UI

**Confirmed: exactly one leveling UI surface exists, and it is fully
consolidated.** `panels/SchedulingResourceLevelingPanel.qml` (181 LOC) —
Preview button → before/after conflict-count + finish-date-shift summary →
unresolved-conflict warning banners → moves table + inspector → confirm-gated
Apply button. No stray "Auto Level"/"Manual Level" button, dialog, or menu
item exists anywhere else in the workspace; a repository-wide search for
those terms in UI code returns zero hits outside this one panel (the only
other matches are backend function names, not UI).

| Control | Classification |
|---|---|
| "Preview" button | **KEEP** — correctly isolated, no auto-run on page load |
| Before/after metrics + unresolved-conflict banners | **KEEP** |
| Moves table + inspector | **KEEP** |
| "Apply Leveling Plan" (confirm-gated) | **KEEP** |

This tab is the model the rest of the workspace should be brought toward, not
a component needing rework.

---

## 15. Current Diagnostics UI

Diagnostics facts are computed in `overview_builder.py` (for the KPI strip)
and then **independently recomputed with the identical formula** in
`diagnostics_builder.py` for 5 of its 6 summary rows (Critical Path Length,
Open Ends, Infeasible Activities, Delayed Activities, Resource Conflicts).
Only the 6th row's *label* ("Constraint Violations") and the panel's second,
separately-fetched real violations table add anything beyond the KPI strip —
and that row's actual formula measures deadline-lateness, not constraint
violations, colliding in name with the table beneath it.

The same underlying facts can appear in up to **four** places at once
(KPI tile → Diagnostics summary row → a dedicated detail tab such as Delays
or Resources → a per-activity Detail-page section) — each additional
appearance beyond the KPI tile and the dedicated detail tab adds screen
weight without adding a distinct purpose.

**Recommendation input for §26:** Diagnostics should remain a single tab
(not fragment further), but should drop its redundant summary rows (already
covered by the always-visible/Overview-tab KPIs) and keep only the
genuinely-distinct real constraint-violation feed, retitled to avoid the
collision.

---

## 16. Current Baseline UI

Baseline content exists in **four** places: the dedicated Baselines tab (3
tables, the most actions of any panel — Save/Submit/Approve/Reject/Archive,
plus 2 comparison selectors and a checkbox), the Detail page's read-only
Baselines section (an explicit duplicate — its own empty-state text tells the
user to go use "the Baselines panel" instead), the single "Save Baseline"
dialog, and a standalone baseline `ComboBox` on the root action bar (a fourth,
independent baseline-selection control separate from the tab's own A/B
comparison selectors).

**Classification: core scheduling-governance functionality, not a secondary
or occasional add-on** — by action count and table real estate it is the
single heaviest tab in the workspace. But it is a **periodic governance
workflow** (freeze → approve → compare), not a daily-use view, and it
currently competes for equal-weight tab-bar real estate with daily-use tabs
like Activity & Timeline and Resources. It does not need to leave the
workspace, but it should not visually compete at the same priority level as
day-to-day schedule work (§28, §36).

---

## 17. Current Gantt / Timeline

**Location:** `panels/SchedulingTimelinePanel.qml` (234 LOC), embedded as the
right-hand pane of a horizontal `SplitView` inside the Activity & Timeline
tab — not its own tab.

**Screen share:** the `SplitView` gives the Gantt pane a *larger* default
width (760px preferred) than the activity table (560px preferred) and marks
only the Gantt pane `fillWidth: true`, so it also absorbs all extra
horizontal space. Both panes have a 420px floor (SplitView minimum), meaning
this one tab alone needs at least ~840px of usable width before either pane
even reaches its floor.

**Controls around it:** none of its own — it inherits the same
search/filter/customize toolbar and pagination as the activity table above
the split, and shows exactly the same page of rows.

**Selection it drives:** **none.** There is no `MouseArea`, no click handler,
no selection signal anywhere in the file. Selecting a row in the adjacent
table does not highlight or scroll to the corresponding bar; there is no
`selectedActivityId` binding into this component at all. Its "baseline ghost
outline" is permanently hardcoded `true` for every row — not wired to real
baseline data.

**Competition with other panels:** it visually restates the same rows the
table already shows (title, a colored bar, a status label — 3 data points vs.
the table's up to 13 columns) with no cross-navigation value, while consuming
the majority of the horizontal split by default.

**R4.4 vs. R4.5 boundary respected by this audit:** this section documents
placement and screen-share facts only. It does **not** propose Gantt
interaction polish, deep timeline responsiveness, or any Gantt-specific
adaptive behavior — those are R4.5's explicit charter. What R4.4 *can*
legitimately decide, as pure IA/placement (not Gantt engineering), is (a)
whether the Gantt pane's default width/fill behavior should stop out-competing
the table by default, and (b) whether it stays paired with the table at all
versus moving behind a view toggle — both addressed in §28/§36 as placement
decisions, leaving the actual chart rendering/interaction untouched for R4.5.

---

## 18. Responsive Structural Analysis

**No window rendering or screenshot capture was performed.** This environment
has no interactive display/screenshot tooling wired into this audit, and per
the audit's own instruction, no pixel-perfect claim is made. What follows is
a structural sizing analysis derived from the actual QML layout constants
found in the files above (`Layout.preferredHeight`/`preferredWidth`,
`SplitView` minimums, `AppWidgets` default sizing) — real constants, not
assumptions.

Approximate chrome heights (from AppTheme margin/spacing constants and
explicit `LoadingOverlay`/`InlineMessage`/`KpiStrip`/`SchedulingActionBar`
component defaults, all `compact`/single-row where used here):

| Chrome element | Approx. height |
|---|---|
| App shell header/nav (outside Scheduling, shared) | ~56–64px |
| KPI strip | ~88–100px (card height + margins) |
| Loading/busy overlay (each, when shown) | ~40px compact |
| Error/success banner (each, when shown) | ~40px |
| Action bar (Refresh/Run CPM + 3 combos) | ~56px |
| Tab strip (`Flow` of chips, wraps at narrow widths) | ~48px single row, up to ~96px if wrapped to 2 rows |
| **Subtotal, always-visible chrome (no banners active)** | **~250–320px** before any tab content renders |

At the five target sizes, remaining vertical space for the active tab's own
content (window height minus shell chrome minus the ~250–320px Scheduling
chrome above, ignoring OS window decoration):

| Target | Window height | Est. remaining content height |
|---|---|---|
| 1024×640 | 640 | **~260–330px** — a single `preferredHeight: 320`+ table (several tabs specify exactly this) already exceeds or consumes nearly all remaining space before scrolling |
| 1280×720 | 720 | ~340–410px |
| 1366×768 | 768 | ~390–460px |
| 1440×900 | 900 | ~520–590px |
| 1920×1080 | 1080 | ~700–770px |

Horizontally, the Activity & Timeline tab's `SplitView` alone requires ~840px
of floor width (420+420) before either pane is even at its minimum — at
1024px width, after the app shell's own sidebar (typically 200–260px in this
codebase's shared nav components) and the Scheduling `AppWidgets.InspectorPanel`
width constant (used elsewhere, not on this tab, but relevant to the same
theme budget), there is very little margin left, meaning the Gantt pane in
particular is a likely candidate to be squeezed to its 420px floor at
1024×640 — at which point it shows only a handful of pixels of chart per row
label, undermining its own purpose.

**Conclusion:** at 1024×640, the always-visible chrome plus a single tab's
own hard-coded `preferredHeight` tables already consume the entire viewport
before scrolling, on every single tab — this is a structural, layout-constant
fact, not a subjective impression, and it holds even before considering the
Detail page's 8 sections (several with `implicitHeight: 480/520`) stacked
inside a page that itself replaces the whole screen.

---

## 19. Crowding Root Causes

| Category | Evidence |
|---|---|
| **TOO MANY ALWAYS-VISIBLE PANELS** | KPI strip + 2 overlays + 2 banners + action bar + tab strip all render above the `StackLayout` on every tab (§5, §18) |
| **TOO MANY TOOLBAR ACTIONS** | "Refresh" x6, "Run CPM" x4, all wired to the same two methods with no tab-scoping (§7) |
| **DUPLICATED INFORMATION** | KPI strip vs. Diagnostics summary rows (5 of 6); Detail page vs. 5 of 8 top-level tabs (§10, §15, §16) |
| **POOR HIERARCHY** | "Constraint Violations" naming collision (§13); "Planning" vs. "Scheduling" label split (§2); "Archive" button calling `deleteBaseline` (§7) |
| **TOO MUCH VERTICAL CHROME** | ~250–320px of always-visible chrome before any tab content, confirmed via layout constants (§18) |
| **TOO MANY SUMMARY CARDS** | 8 KPI tiles + 3 independently-implemented ad hoc stat-card patterns with no shared component (§11) |
| **INSPECTOR + MAIN CONTENT COMPETITION** | Not the Resource Leveling inspector (well-scoped) — but the Gantt pane vs. the activity table, which is the same competition dynamic without the word "inspector" attached (§17) |
| **DIAGNOSTICS SHOWN TOO EARLY** | Not literally — Diagnostics is tab #2, not the landing tab — but its *aggregate facts* (Infeasible/Critical/Overloads counts) are unavoidably first-screen via the always-visible KPI strip, which is appropriate for a health-at-a-glance job (§11) and is **not** classified as a defect here |
| **LEVELING MIXED WITH ANALYSIS** | **Not found** — Resource Leveling is cleanly isolated (§14), a positive counter-example |
| **BASELINE MIXED WITH DAILY SCHEDULING** | Confirmed — the heaviest tab (3 tables, 5 actions, periodic-governance cadence) sits at equal tab-bar weight next to daily-use tabs (§16) |
| **GANTT COMPETING WITH TABLES** | Confirmed — wider default width, `fillWidth: true`, zero interactivity, same rows as the adjacent table (§17) |
| **FIXED HEIGHTS / WIDTHS** | Nearly every table specifies a hard `Layout.preferredHeight` (200–700px range); `SplitView` panes have hard 420px minimums (§10, §17, §18) |
| **RESPONSIVE COLLAPSE FAILURE** | Structurally likely at 1024×640 per §18's sizing analysis; not confirmed via rendered screenshots (none available) |

---

## 20. User Jobs

| Job | Currently served by |
|---|---|
| A. Understand schedule health | KPI strip (always visible) + Diagnostics tab (largely redundant) |
| B. Inspect the task schedule | Activity & Timeline tab's table |
| C. Critical path / float | Activity table columns + KPI "Critical" tile |
| D. Inspect dependencies | Detail page only (no tab) |
| E. Inspect scheduling constraints | Diagnostics violations table + Detail page Constraints section (read-only; editing is Task Editor's job, confirmed out of Scheduling entirely) |
| F. Resource overloads | Resources tab + KPI "Overloads" |
| G. Preview/apply leveling | Resource Leveling tab (clean) |
| H. Schedule diagnostics investigation | Diagnostics tab |
| I. Compare baseline/current | Baselines tab |
| J. Work with Gantt/timeline | Embedded pane inside job B's tab |

**Jobs that naturally belong together:** A/B/C/H (understanding and
inspecting the *live* schedule) are one coherent cluster; D/E are read-only
*context* about a selected activity, not project-wide content — they belong
in an Inspector/Detail context attached to B, not as their own tabs; J is a
*view mode* of B (a way of looking at the same rows), not an independent job,
and should not be treated as competing tab-bar content.

**Jobs that should NOT compete on one screen:** **I (baseline governance) vs.
A/B/C/H (daily schedule work)** — different cadence and different mental
mode (periodic freeze/approve vs. continuous monitoring). **F/G (resource
capacity + leveling) already correctly avoid competing** with A/B/C — this
separation exists today and should be preserved, not because leveling needs
more isolation, but because it's a working example of the boundary the rest
of the workspace should adopt.

---

## 21. Navigation-Level Analysis

| Level | Current reality |
|---|---|
| **Level 1 — PM module nav** | "Work" group: Projects / Tasks / **Planning** (label; underlying key `scheduling`) |
| **Level 2 — Planning workspace nav** | The 8-tab strip |
| **Level 3 — contextual detail** | The Resource Leveling `InspectorPanel` (correctly scoped) **and** the Detail page's 8 sections (incorrectly re-presenting Level 2 content) |

**The Level-2/Level-3 boundary is currently violated**: 5 of the Detail page's
8 "Level 3" sections are not contextual detail about the selected activity at
all — they are unfiltered re-renders of Level-2 tab content (the same
project-wide Baseline/Resource/Calendar/Activity-Feed tables), just reached
through a different door. A true Level 3 surface should show facts that are
*about the selected item specifically*; four of these five sections show
exactly what the corresponding Level-2 tab already shows to everyone,
unfiltered by the selection at all.

---

## 22. Option A — Single Workspace (retreat to one page + collapsible sections)

**Evaluation, not recommendation.**

- **Pros:** simpler mental model in the abstract; no route/tab state to
  manage; a single scroll position.
- **Cons:** the workspace has *already* moved past this — collapsing 8 tabs'
  worth of tables/forms into one scrolling page with collapsible sections
  would concentrate exactly the content the existing `StackLayout` currently
  keeps apart, worsening (not fixing) the "too many always-visible panels"
  cause, since a collapsed section still occupies a strip and multiple
  sections can be expanded simultaneously by design. It also actively harms
  §32/§35's lazy-loading goals: expensive data (leveling proposals, baseline
  comparisons, diagnostics) would need to load speculatively rather than on
  tab activation, or the "collapsed" state would need its own lazy-load logic
  reinventing what `StackLayout`'s tab-activation model already gives for
  free.
- **Responsive implications:** worse — a single long scroll at 1024×640
  means every section's `preferredHeight` stacks additively rather than being
  time-sliced by tab selection.
- **Discoverability:** arguably worse, not better — a title on a collapsed
  header is a weaker affordance than a labeled tab, and the current tab
  labels (§8) are already clear.
- **Implementation cost:** low to convert, but high in regression risk (every
  panel's height/scroll assumptions would need rework) for no net crowding
  benefit.
- **Future scalability:** poor — adding a 9th planning concern would mean
  adding yet another collapsible section to an ever-longer scroll, rather than
  a 9th tab.

**Not recommended.** No credible evidence supports it; every root cause found
in §19 is orthogonal to "does this use tabs or collapsible sections," and the
one difference that does matter (all-sections-visible-at-once potential)
points against it.

---

## 23. Option B — One Route + Internal Subnav

**Evaluation.**

- **Pros:** formalizes and *fixes* what already exists rather than inventing
  something new — the underlying `StackLayout` + tab-selection pattern is
  proven and already ships; consolidating from 8 loosely-related tabs to a
  smaller, purpose-grouped set (e.g., Overview / Schedule / Resource Leveling
  / Diagnostics, with Baselines/Calendars visually de-emphasized rather than
  removed) directly addresses the KPI/Diagnostics duplication (§15), the
  Detail-page duplication (§10, §21), and the toolbar redundancy (§7) without
  inventing new infrastructure.
- **Cons:** still requires real consolidation work (merging Diagnostics'
  redundant rows, trimming the Detail page from 8 sections to 3–4,
  re-homing the KPI strip/action bar into a proper Overview tab) — this is
  implementation effort, not a free relabeling.
- **Route complexity:** none added — still exactly one shell route
  (`project_management.scheduling`) and one root QML page; only the *internal*
  tab set and Detail-page section set change.
- **State preservation:** straightforward — `SchedulingWorkspaceState.qml`
  already centralizes `activePanelId`/`panelTabs`; consolidating tabs is a
  data-shape change to that one file plus deleting the panels that get
  merged/removed, not a new state-management pattern.
- **Controller reuse:** high — the controller already exposes per-tab
  properties/table-models 1:1 with today's panels; consolidation mostly means
  *not* building new controller surface, and deleting the now-unused
  Detail-page-specific bindings for the 5 duplicated sections.
- **Responsive behavior:** improves directly — fewer always-visible chrome
  blocks (§18) and fewer competing panels per tab.
- **Future R4.5 interaction:** clean — R4.5's Gantt work would attach to
  whichever tab hosts the Activity table (renamed "Schedule" in the
  recommended IA, §28) without needing any navigation-level change here.

**This is the strong, evidence-backed option.**

---

## 24. Option C — Additional PM Nav Item

**Evaluation against the directive's own criteria.**

| Criterion | Scheduling/Planning as a whole | Resource Leveling specifically |
|---|---|---|
| Distinct user job | Yes (already true today, hence its own nav entry) | Yes, but already served by one focused tab |
| Frequency | Daily/continuous | Occasional/triggered (a planner runs it when overloads appear, not continuously) |
| Independent content volume | High (justifies the existing entry) | Low-to-moderate — one panel's worth |
| Independent state | Already isolated within the workspace's own controller properties | Already isolated (`levelingProposal`/`levelingMoveRows`), no cross-workspace state needed |
| Permission model | Standard PM permissions | Same permission model as the rest of Scheduling — no separate capability gate found |
| URL/deep-link value | Already has one (`project_management.scheduling`) | No evidence of an independent deep-link need (no support ticket / bookmark use case found in the code or tests) |
| Narrow-screen usability | One more top-level item to fit in the sidebar | Adding a *second* top-level item for what is one tab today would increase sidebar clutter, working against the audit's own crowding goal at a different layer |
| Future growth | Real (R4.5 Gantt, more diagnostics) | Bounded — the feature's own scope (Preview → Apply) is complete per R4.4M–W.1; no roadmap evidence of it growing into a multi-page destination |
| Duplication risk | N/A | Splitting it out risks re-fragmenting the exact Resources/Leveling relationship that today's single-workspace tab set keeps coherent (leveling needs the same resource-load data Resources already shows) |

**Conclusion: no new PM Level-1 navigation item is justified by current
evidence — neither a generic "Planning" split nor a "Resource Leveling"/
"Workload Management" promotion.** The existing single "Planning" entry
already has the job frequency, content volume, and independent state to
justify its current standing; Resource Leveling does not meet enough of the
criteria to justify fragmenting out on its own.

---

## 25. Resource Leveling Placement (evaluated in depth)

Directly answering §24's question: **no, Resource Leveling is not
substantial enough to warrant a dedicated *external* page or PM nav item.**
It is exactly substantial enough to warrant the dedicated *internal* tab it
already has — one focused workflow (conflicts → preview → proposal → apply),
self-contained, already performance-hardened (R4.4W.1: sub-2-second Preview
even at 5,000 tasks), with no legacy leftover controls. The evidence in §14
and §24 both point the same way: **keep it exactly where it is.**

---

## 26. Diagnostics Placement

Should stay a single tab, not fragment into its own page, and not consolidate
*upward* into the KPI strip either (the KPI strip's job is glanceable
aggregate counts; Diagnostics' job is a browsable list of *why*). What should
change is **internal**, not placement: drop the 5 redundant summary rows that
merely restate KPI-strip counts, keep and retitle the real constraint-overrun
table to resolve the naming collision (§13, §15), and consider folding in the
one genuine gap found (§12: no view of *which* activities have open
dependency ends, only a count) as new, non-duplicative content for this tab
rather than a new page.

---

## 27. Three Target IA Alternatives

### Option 1 — Conservative (in-place cleanup, same route, same tab mechanism)

```
Planning (unchanged route/label)
└── one workspace, tab count 8 → 7
    ├── Overview        [NEW] — KPI strip + action bar content moves here
    ├── Schedule         (renamed from "Activity & Timeline"; Delays folded in
                          as a status filter, not a separate tab)
    ├── Resources
    ├── Resource Leveling (unchanged)
    ├── Baselines         (unchanged content, visually de-emphasized position)
    ├── Diagnostics       (deduplicated against Overview's KPIs)
    └── Calendars         (unchanged)
Detail drill-down: trimmed from 8 sections to 4
    (Overview, Dependencies, Constraints, Change Impact — the 4 that are NOT
     verbatim duplicates of a top-level tab)
```

- **Pros:** lowest migration risk — no new subnav mechanism, reuses the
  exact `StackLayout`/tab-chip pattern already proven; every change is either
  a merge, a delete, or a data-shape edit to the existing state file.
  Directly fixes root causes §19's "always-visible chrome," "duplicated
  information," and the Detail-page boundary violation (§21).
- **Cons:** does not address the tab-strip's own crowding at the visual
  level (still 7 roughly-equal-weight chips) or give Baselines/Calendars a
  visually distinct "secondary" treatment beyond ordering.

### Option 2 — Strong Separation (internal Planning navigation restructure)

```
Planning
├── Overview       — landing tab: health KPIs + top diagnostic/critical items
├── Schedule        — Activity table + Gantt (Delays folded in as a filter;
                       Dependencies/Constraints reachable via a per-row
                       Inspector, not the full-page Detail drill-down)
├── Resource Leveling  — unchanged
└── Diagnostics     — consolidated violations/conflicts/infeasibility list

  [secondary/administrative group, visually distinct from the primary 4]
  Baselines · Calendars
```

- **Pros:** the primary/secondary visual split directly matches the
  cadence mismatch found in §16/§20 (daily work vs. periodic governance);
  reduces the *primary* tab count to 4, a much shallower first-screen
  decision for the common case.
- **Cons:** introduces one new structural concept (a "secondary" tier within
  Level 2) that does not exist today — more design work than Option 1, though
  still no new route and no new PM nav item. Requires deciding exactly how
  "secondary" tabs are surfaced (a visually distinct tab-strip segment? a
  small overflow/"More" affordance? — an open question for implementation,
  not resolved by this audit, see §44 uncertain decisions).

### Option 3 — Separate PM Navigation (rejected direction, presented for completeness)

```
Work
├── Projects
├── Tasks
└── Planning          (Schedule + Diagnostics only)

Workload Management [NEW L1 nav item]
└── Resources + Resource Leveling
```

- **Pros:** theoretically clean separation of "schedule analysis" from
  "resource capacity work."
- **Cons:** fails §24's own evidence-based criteria — Resource Leveling's
  frequency, independent-content volume, and growth trajectory do not
  justify a new top-level destination; splitting Resources away from
  Schedule also severs the natural adjacency between "who's overloaded" and
  "what's critical," which today live one tab-click apart; adds sidebar
  clutter at exactly the kind of narrow-screen cost this audit is trying to
  reduce elsewhere.

**Not recommended** — included only because the directive requires evaluating
it explicitly (§24).

---

## AMENDMENT — Product Decisions (supersedes parts of §22–§45 below)

**Status: target-IA decision, documentation-only update. No QML/Python was
implemented or changed. No re-audit was performed** — §1–§21 (evidence) and
§22–§27 (options evaluation) stand as originally written and are the
accepted current-state evidence base. What follows revises the
*recommendation* sections (§28, §29, §31, §32, §39, §40, §41, §43, §44, §45)
to reflect eight product decisions made after reviewing the audit:

1. **Gantt is first-class within Planning**, not a "Schedule" tab with an
   embedded timeline pane. `Planning → Gantt` owns the activity/WBS grid
   *and* the timeline as one integrated schedule-working surface — R4.4
   establishes its correct location and screen ownership; R4.5 remains
   responsible for deep Gantt interaction/adaptive work.
2. **Final primary Planning navigation:** Overview · Gantt · Resource
   Leveling · Diagnostics. **Secondary:** Baselines · Calendars. No new PM
   Level-1 route.
3. **Global Planning context stays minimal and persistent** across the
   primary pages (selected Project, Refresh, Recalculate/Run CPM) — it does
   **not** all move into Overview, and the old heavy page chrome is not
   restored. Baseline comparison controls belong to Baselines/Gantt where
   applicable; calendar-specific controls belong to Calendars; tab-local
   actions stay tab-local.
4. **Resources content merges into Resource Leveling** (Current Resource
   Load + Current Conflicts + Preview + Proposal + Apply, one workflow) —
   no separate primary Resources page, since no independent content was
   found that doesn't naturally belong to that workflow.
5. **Activity detail is resolved via Gantt row/bar selection → a
   contextual `InspectorPanel`** (dates/duration/float,
   Infeasible/Critical/Flexible status, constraint summary, dependency
   summary, resource-load summary, schedule-impact summary where
   appropriate, "Open Task") — never a recreation of Task Detail, and never
   a home for project-wide Calendars/Baselines/Resources/Activity-Feed
   content.
6. Target QML tree converges toward the shape in the amended §40.
7. Every cleanup the original audit already recommended is still performed
   (KPI/Diagnostics dedup, Refresh/Run CPM dedup, Delays→Gantt filter merge,
   constraint-diagnostics naming fix, `is_infeasible` correctness fix,
   Archive/delete label fix, duplicated Detail-section removal, genuine lazy
   loading, responsive cleanup) — only *where things live* changes.
8. **Navigation rule:** maximum PM navigation + Planning navigation +
   contextual inspector — three levels, no more. Gantt view controls (Critical
   Path, Dependency Lines, Baseline overlay, Zoom, Timescale) are view
   controls/overlays *within* the Gantt page, not a fourth navigation level.

**Activity Feed placement — closed by the FINAL PRODUCT DECISIONS section
below (decision 1):** confirmed as a secondary destination, alongside
Baselines and Calendars. It is project-level historical/narrative context,
not a Diagnostics concern, and is not restored inside selected-activity
detail.

---

## 28. Recommended IA (amended)

**Recommendation: Option 2 (Strong Separation via internal Planning
navigation), refined by the product decisions above.** Option 1's specific
fixes (dedup, bug fixes, label fixes) are still fully absorbed; Option 3
remains rejected per §24's evidence — nothing in the amendment reopens that
question.

Specific answers (superseding the equivalent bullets in the original §28):

- **Is another PM nav item needed?** No (§24, reaffirmed by decision 2).
- **Is internal Planning navigation needed?** Yes — four primary
  destinations (Overview, Gantt, Resource Leveling, Diagnostics) plus two
  secondary (Baselines, Calendars), still built on the existing tab-strip
  mechanism, not a new navigation layer (decision 2, decision 8).
- **Where does Resource Leveling belong?** Its own primary tab, now
  additionally owning the Resources tab's former content as "Current
  Resource Load," alongside Current Conflicts, Preview, Proposal, and Apply
  — one continuous capacity-decision workflow rather than two tabs a planner
  had to move between (decision 4).
- **Where does Diagnostics belong?** Unchanged from the original
  recommendation — its own primary tab, deduplicated against Overview's
  KPIs, naming collision resolved (§26).
- **Where does Dependencies belong?** Unchanged in *scope* (per-activity,
  read-only, no CRUD, CRUD stays in Task Detail) but changed in *surface*:
  it is now content inside the Gantt tab's contextual `InspectorPanel`
  (decision 5), not a trimmed full-page Detail section.
- **Where does Constraints belong?** Same treatment as Dependencies — the
  per-activity summary moves into the Gantt Inspector; the aggregate
  violations table stays in Diagnostics (§13, §26). No dedicated tab.
- **Where do Baselines belong?** Secondary tier, alongside Calendars,
  unchanged from the original recommendation (§16, §20) — but baseline
  *comparison/overlay* controls that make sense while looking at the
  schedule (e.g. a "show baseline" overlay) may additionally surface as a
  Gantt view control (decision 3), without moving baseline governance itself
  out of the secondary Baselines tab.
- **Where does the Gantt belong?** It **is** the primary "Schedule" surface
  now, not a pane embedded inside one — the activity/WBS grid and the
  timeline are one integrated tab, always shown together (decision 1). Its
  own view options (Critical Path, Dependency Lines, Baseline overlay, Zoom,
  Timescale) are in-page view controls, never a separate navigation level
  (decision 8). The grid/timeline default-sizing fix from the original audit
  (stop the timeline out-competing the grid, §17) still applies within this
  single integrated tab.
- **What stays in the Inspector?** Per decision 5: dates/duration, float,
  Infeasible/Critical/Flexible status (the canonical precedence — this is
  where the original audit's `is_infeasible` correctness bug, §13, gets
  fixed at the source, since the Inspector must not ship the same defect),
  a constraint summary, a dependency summary, a resource-load summary, a
  schedule-impact summary where appropriate, and "Open Task." **Not**: full
  Task editing, full dependency CRUD, full constraint editing, or any
  project-wide Calendars/Baselines/Resources/Activity-Feed content — the
  last of these is a new, explicit exclusion the original audit's "trimmed
  Detail page" plan had not fully committed to (it still kept a full-page
  container that *could* regrow duplicate sections; a true Inspector cannot).
- **What moves out of the initial screen?** The full KPI strip and
  needs-attention content still move to the new Overview tab (unchanged from
  the original recommendation), but the *minimal* Project/Refresh/Run-CPM
  controls now persist across all four primary tabs rather than living only
  on Overview (decision 3) — this is the one respect in which the amended
  recommendation keeps *more* global chrome than the original §28 proposed,
  deliberately, per product's explicit instruction not to over-concentrate
  every control into one tab.

---

## 29. Default Planning Landing Page (amended)

```
Planning → Overview   (default tab)

Persistent Planning context header (present on Overview/Gantt/Resource
Leveling/Diagnostics alike — decision 3, NOT Overview-exclusive)
  Project ▾   [Refresh]   [Run CPM]

Overview tab's own content, below the persistent header
  KPI strip: Activities · Critical · Delayed · Open ends · Infeasible ·
  Overloads   (Baselines/Calendar trivia tiles demoted or folded into
  supporting text, consistent with §11's SECONDARY/MISPLACED findings)

  "What needs attention" list (critical/infeasible/overloaded items the
  KPIs are counting) — content this audit does not fully specify;
  flagged as an implementation decision, not invented here

Then navigate to:
  Gantt · Resource Leveling · Diagnostics       (primary tier)
  Baselines · Calendars · Activity Feed          (secondary tier, confirmed
                                                   — FINAL PRODUCT DECISIONS
                                                   decision 1)
```

Note the change from the original §29: the Baseline/Calendar *selectors*
that used to sit in the always-visible action bar are **not** relocated to
Overview — per decision 3 they move to the Baselines and Calendars tabs
respectively, where they are actually used. Only Project/Refresh/Run CPM
persist globally.

---

## 30. Resource Leveling Location

The R4.4 Preview → Apply workflow should continue to live at **Planning →
Resource Leveling** (its own primary tab), not as a permanent global toolbar
button. A small **global entry point should NOT be added** — the evidence in
§14/§25 shows no current gap this would fill (there is no legacy "Auto
Level" button anywhere to replace, and the workflow is explicitly meant to be
deliberate, not a one-click ambient action per R4.4W.1's own performance
findings and §36 below).

---

## 31. Toolbar Ownership / Global Planning Context (amended)

Per decision 3, this is no longer "everything lives in one global bar, or
everything moves to Overview" — it is a minimal *persistent* header plus
strictly tab-local action bars:

| Belongs in | Actions |
|---|---|
| **Persistent Planning context header** (present on all 4 primary tabs: Overview, Gantt, Resource Leveling, Diagnostics) | Project selector, "Refresh", "Run CPM" — nothing else |
| **Gantt tab** | Search, Filter (incl. the merged Delays "late" filter), Customize columns, plus Gantt view controls (Critical Path, Dependency Lines, Baseline overlay, Zoom, Timescale — view controls, not navigation, per decision 8) |
| **Resource Leveling tab** | "Preview", "Apply Leveling Plan", plus whatever action(s) the merged Current-Resource-Load content needs (decision 4) |
| **Diagnostics tab** | Search only |
| **Baselines tab** (secondary) | Save/Submit/Approve/Reject/Archive (rename "Archive" to match its real `delete` semantics, or vice versa — implementation decision), A/B selectors, Include-unchanged checkbox, Baseline selector (moved here from the old global action bar, decision 3) |
| **Calendars tab** (secondary) | Calendar selector (moved here from the old global action bar, decision 3), working-day calculator |
| **Gantt Inspector** | "Open Task" only |

The persistent header owns exactly the three genuinely cross-tab,
project-wide operations (select project, refresh, recalculate) — nothing
tab-local is duplicated there, and nothing that used to be tab-local (search,
filter, customize, baseline/calendar selection) moves into it either. This
directly reverses today's 6x/4x Refresh/Run-CPM duplication (§7) without
re-creating a new "everything dump" in a different tab.

---

## 32. Selected-Task Inspector Ownership (amended)

**Trigger:** selecting a row in the Gantt tab's activity/WBS grid **or**
selecting a bar in its timeline — both open the *same* contextual
`AppWidgets.InspectorPanel` (decision 5). Wiring bar-selection to drive this
(today it has none, §17) is basic selection plumbing needed to establish
*which activity* the Inspector shows — it is not the deep Gantt interaction
work (drag-to-reschedule, zoom/timescale rendering, resize handles) that
stays R4.5's responsibility under the unchanged R4.4/R4.5 boundary (§37).

**Contents (per decision 5):**
- dates / duration
- float
- status, using the canonical Infeasible → Critical → Flexible precedence
  (fixing, at the source, the original audit's §13 finding that the old
  Detail page's Overview header skipped the infeasibility check — the new
  Inspector must not inherit that bug)
- constraint summary (one line, same `constraint_label_for_activity()`
  formatter already used elsewhere — no new formatting logic)
- dependency summary (count/short list, not the full CRUD table)
- resource-load summary for the selected activity
- schedule-impact summary, where appropriate (see migration note below)
- "Open Task" action into Task Detail

**Explicitly excluded:** full Task editing, full dependency CRUD, full
constraint editing (unchanged from the original recommendation — none of
these exist in Scheduling today either), **and, newly explicit under this
amendment: no project-wide Calendars/Baselines/Resources/Activity-Feed
content of any kind.** The original audit's "trimmed Detail page" plan kept
a full-page, multi-section container that *could* regrow such sections over
time; a true `InspectorPanel` structurally cannot, which is one reason this
migration path was chosen (see below).

**Migration determination for `SchedulingDetailPanel.qml`
(`SectionDetailPage`/`ContextualActionToolbar`/`LazySectionLoader`
scaffold):** the smallest maintainable path is to **replace** it, not adapt
it in place. The target Inspector's content is a *flat* list of ~8 facts —
structurally identical to what the Resource Leveling tab's `InspectorPanel`
already renders today via its `sections:` array (§9) — whereas
`SchedulingDetailPanel.qml`'s multi-section, `LazySectionLoader`-per-section,
full-page-takeover machinery exists to serve a *different* shape (independent
tabbed sub-pages, several of them full tables). Building the new Inspector
as a second instantiation of the same shared `AppWidgets.InspectorPanel`
component already proven in Resource Leveling is less code than trimming and
maintaining the existing multi-section scaffold going forward, and it
removes the exact container that made the original 5-section duplication
possible in the first place. Concretely:
- **Delete** `SchedulingDetailPanel.qml`, and the `SectionDetailPage` /
  `ContextualActionToolbar` / `SectionScopedInlineMessage` / `Loader` wiring
  in `SchedulingWorkspacePage.qml` that hosts it (`state.detailOpen`, the
  full-screen takeover pattern).
- **Add** one `AppWidgets.InspectorPanel` instance directly inside the Gantt
  tab, using the existing `sections:`/`showSecondaryAction`/
  `secondaryActionLabel`/`secondaryActionRequested` API (the same API
  Resource Leveling's Inspector already uses for its own facts and could use
  for "Open Task") — no new shared-component work required.
- The "schedule-impact summary" fact is the one piece of content that, in
  the old Detail page, required an explicit "Run Impact Analysis" button
  click (`computeScheduleImpact({})`) rather than being an always-available
  fact. Whether the Inspector shows it lazily behind a small trigger
  (consistent with keeping the Inspector fast to open) or the presenter
  layer is asked to make a cheaper summary available immediately is an
  implementation decision this document does not resolve — flagged again in
  the uncertain-decisions list (§ end of document).

---

## 33. Check Existing Shared Nav Components

No existing shared "workspace-local tab rail" component was found reused
elsewhere that Scheduling should have adopted instead of hand-rolling its own
`Flow`+`Repeater` chip strip — the pattern in `SchedulingWorkspacePage.qml`
lines 214-294 is bespoke to this file. The PM shell's own sidebar
(`Components.PmWorkspaceNavigation`) is a *different* pattern (Level 1, not
Level 2) and not directly reusable as-is for an internal tab rail. **This
audit did not find a ready-made "primary/secondary tab" shared component** —
building the primary/secondary tier distinction recommended in §28 will
either need a small, genuinely reusable addition to the shared component
library (preferred, since other PM workspaces likely have the same daily-vs-
periodic tab problem) or, at minimum, should not become a second bespoke,
Scheduling-only control if a shared one can be justified. This is flagged as
an implementation-time decision, not resolved here.

---

## 34. Controller / Presenter Implications

Not implemented here; identified only.

- **Global to Planning:** selected project/baseline/calendar, `isLoading`/
  `isBusy`/error/feedback messages — already global on the controller today.
- **Schedule-only:** activity table rows/sort/filter/pagination, Gantt/timeline
  data — already scoped via distinct controller properties.
- **Resource-Leveling-only:** `levelingProposal`/`levelingMoveRows` — already
  cleanly isolated (R4.4Q+ work); no change needed.
- **Diagnostics-only:** diagnostics/violations table models — already
  distinct; the KPI-duplicate rows can be dropped from
  `diagnostics_builder.py` without touching `overview_builder.py`.
- **What can lazy-load:** Resource Leveling data already does (only after
  "Preview" — confirmed, §14/§36); Baseline comparison/variance data already
  loads only on row selection (`loadVarianceRecordsForBaseline`) — good
  precedent to extend to Diagnostics' own detail fetches if any are found to
  be eager in a future pass.
- **What should clear on project switch:** all of the above except possibly
  cached column-customization state (already project-independent, correctly
  so).

---

## 35. Lazy-Loading Opportunities

| Data | Current behavior | Target |
|---|---|---|
| Resource leveling proposal | **Already lazy** — only computed on "Preview" click | Keep as-is; this is the model example |
| Baseline variance records | **Already lazy** — only on register-row selection | Keep as-is |
| Diagnostics/violations tables | Eager on tab activation (all 8 tabs mount together via `StackLayout`, so "on tab activation" is effectively "on page load" today) | Candidate for genuine lazy mount if the primary/secondary tier split (§27 Option 2) is implemented with real `Loader`-gated secondary tabs, rather than `StackLayout` keeping all 7-8 siblings resident |
| Baseline compare/register tables | Same as above | Same candidate |
| Dependency/Constraint per-activity data | Already fetched only when an activity is selected/detail opened | Keep as-is |

The single biggest structural lazy-loading opportunity is that **`StackLayout`
currently keeps all 8 panels resident regardless of which tab is active** —
none of today's "eager" data is eager because someone chose it to be; it's
eager because the container that would gate it (a `Loader` per tab) isn't
used. This is worth flagging for implementation even though it is a bigger
change than pure IA reshuffling.

---

## 36. Performance Implications

R4.4W.1 found leveling Preview can be expensive at large project sizes before
its fix (111s at 5,000 tasks on a synthetic worst case) and fast after it
(sub-2s on real DB-backed data at the same scale). The current IA already
gets the *load-timing* half of this right — Preview is an explicit user
action, never triggered by opening the Resource Leveling tab, let alone by
opening Planning itself. **No IA change is needed to preserve this
property**; the recommendation in §28/§30 explicitly keeps Preview as a
deliberate click, and nothing proposed here (Overview tab, tab consolidation,
Detail-page trimming) introduces any new eager computation of a leveling
proposal. This section exists to confirm the constraint was checked, not to
report a new finding.

---

## 37. R4.4 / R4.5 Boundary

R4.4 (this audit and its owning phase) owns: Planning/Scheduling IA, the
general tab/chrome responsive structure, the Resource Leveling workflow
(already delivered), diagnostics content correctness (the naming collision
and duplication fixes recommended here), and truthful tables/panels. R4.5
owns: Gantt-specific adaptive behavior, deep timeline responsiveness, and
Gantt interaction polish. This audit's Gantt findings (§17) are placement/
screen-share facts only (does it compete with the table for width, is it
interactive) — no redesign of the chart itself, its date-window math, or its
rendering is proposed or implied. Any decision to add Gantt interactivity
(row-selection cross-highlighting, click-to-open-detail from a bar) is
explicitly deferred to R4.5.

---

## 38. R4.4 / R5 Boundary

R4.4 owns project-specific resource leveling (delivered, R4.4B–W.1). R5 owns
broader Workload Management / operational resource UX. Per §24's evidence-
based rejection of Option 3, this audit does **not** recommend moving
Resource Leveling into a "Workload Management" destination merely because it
involves resources — the feature is project-scoped (it operates on one
project's tasks/resources at a time, driven by the Planning workspace's
already-selected project) and has no evidence of an operational,
cross-project use case that would justify reclassifying it as R5 territory.

---

## 39. Exact Keep / Move / Merge / Remove Matrix (amended)

| Component / section | Current location | Target location | Decision | Reason |
|---|---|---|---|---|
| KPI strip | Always-visible page chrome | Overview tab (new) | **MOVE** | Removes always-visible chrome from every other tab (§18, §19) — unchanged from the original plan |
| Action bar — Project selector, Refresh, Run CPM | Always-visible page chrome | Persistent minimal header on all 4 primary tabs | **MOVE, narrowed scope** | Decision 3: these three stay global; nothing else does |
| Action bar — Baseline selector | Always-visible page chrome | Baselines tab (secondary) | **MOVE** | Decision 3: baseline controls belong to Baselines |
| Action bar — Calendar selector | Always-visible page chrome | Calendars tab (secondary) | **MOVE** | Decision 3: calendar controls belong to Calendars |
| "Refresh" (Diagnostics/Resources/Delays/Calendars/Activity Feed instances) | 5 duplicate panel-local buttons | — | **REMOVE** (keep only the persistent-header instance) | Identical call, no tab-scoping, pure duplication (§7) |
| "Run CPM" (Diagnostics/Resources/Delays instances) | 3 duplicate panel-local buttons | — | **REMOVE** (keep only the persistent-header instance) | Same as above |
| Diagnostics summary table (5 of 6 rows) | Diagnostics tab | — | **REMOVE** | Recomputes KPI-strip formulas verbatim (§15) |
| "Constraint Violations" table (real overruns) | Diagnostics tab | Diagnostics tab | **RENAME** (to resolve the naming collision) | Same panel as the row being removed shared its exact label (§13) |
| Delays tab | Own top-level tab | Filter/state within the Gantt tab | **MERGE** | It is a filtered view of the same activity data the Gantt tab now owns (§20); target renamed from "Schedule" to "Gantt" per decision 1 |
| Activity & Timeline tab (grid + embedded timeline pane) | Own top-level tab, timeline as a sub-pane | **Gantt** — one integrated primary tab owning both the grid and the timeline | **RENAME + RE-SCOPE** (not a plain rename — timeline is elevated from "embedded pane" to co-equal content of a first-class tab) | Decision 1: Gantt is first-class, not split from a "Schedule" page |
| Gantt/timeline pane sizing | `SplitView`, wider + `fillWidth` vs. the grid | Same integrated Gantt tab, non-dominant sizing | **KEEP**, resize only | IA/placement fix only — no R4.5 work performed here (§17, §37); still applies inside the now-unified Gantt tab |
| **Resources tab (entire panel)** | Own top-level tab | Resource Leveling tab, as "Current Resource Load" | **MERGE** | Decision 4: no independent content justifies a separate primary page; the workflow is naturally continuous with Preview/Proposal/Apply |
| Detail page §Calendars | Full-page duplicate of Calendars tab | — | **REMOVE** | Byte-for-byte duplicate (§10, §21) — unchanged |
| Detail page §Baselines | Full-page duplicate of Baselines tab | — | **REMOVE** | Near-identical duplicate; its own empty-state text already tells users to use the tab instead (§16) — unchanged |
| Detail page §Resources | Full-page duplicate of the (now-merged) Resources content | — | **REMOVE** | Identical model/columns (§10) — unchanged, and doubly redundant once Resources merges into Resource Leveling |
| Detail page §Activity Feed | Full-page duplicate of Activity Feed tab | — | **REMOVE** | Identical model (§10) — unchanged |
| Detail page §Overview | Full-page, task facts | **Gantt tab's contextual `InspectorPanel`** | **REPLACE** (content migrates; container does not) | Decision 5: superseded — no longer "keep as a trimmed Detail page," see §32's migration determination |
| Detail page §Dependencies | Full-page, read-only mirror | **Gantt tab's contextual `InspectorPanel`** (dependency summary only, not the full table) | **REPLACE** | Decision 5 |
| Detail page §Constraints | Full-page, per-activity constraint list | **Gantt tab's contextual `InspectorPanel`** (one-line summary) | **REPLACE** | Decision 5 |
| Detail page §Change Impact | Full-page, "Run Impact Analysis" | **Gantt tab's contextual `InspectorPanel`** ("schedule-impact summary where appropriate") | **REPLACE** | Decision 5; exact triggering mechanism (lazy button vs. always-available summary) is an open implementation question, §32 |
| `SchedulingDetailPanel.qml` / `SectionDetailPage` full-page container | Own file/pattern | — | **REMOVE** (superseded by the new `InspectorPanel` instance) | §32's migration determination: replacing, not trimming, is the smaller maintainable path |
| Baselines tab | Primary-tier tab | Secondary-tier tab | **MOVE** (visual tier, not physical relocation) | Periodic-governance cadence vs. daily tabs (§16, §20) — unchanged |
| Calendars tab | Primary-tier tab | Secondary-tier tab | **MOVE** (visual tier) | Same rationale; also read-only/administrative in nature (§16) — unchanged |
| **Activity Feed tab** | Primary-tier tab (implicit, original 8-tab list) | Secondary tier | **MOVE** (confirmed) | FINAL PRODUCT DECISIONS decision 1: confirmed secondary destination — project-level historical/narrative context, not a Diagnostics concern |
| "Archive" baseline action | Baselines tab | Baselines tab | **RENAME** (label or underlying call, TBD at implementation) | Calls `deleteBaseline` — label/intent mismatch (§7) — unchanged |
| Resource Leveling tab | Own top-level tab | Unchanged as a tab, **expanded content** (absorbs Resources) | **KEEP + MERGE-TARGET** | Clean, isolated, performance-hardened; now also the model example and the Resources merge destination (§14, §25, decision 4) |
| Resource Leveling `InspectorPanel` | Inside its own tab | Unchanged | **KEEP** | Well-scoped, no crowding contribution (§9); same shared component reused for the new Gantt inspector (§32) |
| `SchedulingWorkspace.qml` | Test-only wrapper | Unchanged | **DEFER** | Out of this audit's scope; cross-cutting cleanup across all 10 PM workspaces, not Scheduling-specific |
| Detail-page "Change Impact" vs. Task Detail's own schedule-impact preview | Two independently-built features | Unchanged (impact summary now lives in the Gantt Inspector instead, but the cross-workspace duplication question is untouched) | **DEFER** | Cross-workspace consistency question, not an IA placement question within Scheduling alone (§16 cross-cutting note) |

---

## 40. Proposed QML Tree (amended — for the recommended IA, not created)

```
SchedulingWorkspacePage.qml                       [unchanged root, same route]
├── SchedulingWorkspaceState.qml                   [panelTabs data reshaped:
│                                                     8 tabs → 4 primary + 2-3
│                                                     secondary, tier flag added]
├── components/SchedulingPlanningContextHeader.qml [NEW, small — Project
│                                                     selector + Refresh +
│                                                     Run CPM only; present on
│                                                     all 4 primary tabs
│                                                     (decision 3). Replaces
│                                                     components/
│                                                     SchedulingActionBar.qml's
│                                                     role as page-level chrome
│                                                     — SchedulingActionBar.qml
│                                                     itself is kept for
│                                                     tab-local action rows
│                                                     (Baselines, Calendars,
│                                                     Diagnostics search, etc.),
│                                                     not renamed gratuitously]
├── StackLayout  (primary tier)
│   ├── panels/SchedulingOverviewPanel.qml          [NEW — KPI strip +
│   │                                                 needs-attention list;
│   │                                                 new default landing tab]
│   ├── panels/SchedulingGanttPanel.qml             [RENAMED + RE-SCOPED from
│   │    │                                            SchedulingActivityTimeline
│   │    │                                            Panel.qml — decision 1:
│   │    │                                            grid + timeline as one
│   │    │                                            integrated surface, not
│   │    │                                            a "Schedule" tab with an
│   │    │                                            embedded pane. Delays'
│   │    │                                            content folds in here as
│   │    │                                            a filter.]
│   │    ├── panels/SchedulingTimelinePanel.qml      [unchanged file, resized
│   │    │                                            per §17/§19's finding;
│   │    │                                            gains view-control
│   │    │                                            toggles for Critical
│   │    │                                            Path / Dependency Lines /
│   │    │                                            Baseline overlay / Zoom /
│   │    │                                            Timescale — view
│   │    │                                            controls, not navigation
│   │    │                                            (decision 8)]
│   │    └── AppWidgets.InspectorPanel               [NEW instantiation here
│   │                                                 (shared component,
│   │                                                 already proven in
│   │                                                 Resource Leveling) —
│   │                                                 opens on grid-row OR
│   │                                                 Gantt-bar selection;
│   │                                                 replaces
│   │                                                 SchedulingDetailPanel.qml
│   │                                                 entirely (decision 5,
│   │                                                 §32)]
│   ├── panels/SchedulingResourceLevelingPanel.qml  [ADAPTED — gains a
│   │                                                 "Current Resource Load"
│   │                                                 section absorbing
│   │                                                 SchedulingResourcesPanel's
│   │                                                 former content, ahead of
│   │                                                 Current Conflicts /
│   │                                                 Preview / Proposal /
│   │                                                 Apply (decision 4)]
│   └── panels/SchedulingDiagnosticsPanel.qml       [redundant rows removed;
│                                                     naming collision fixed —
│                                                     unchanged file identity]
├── (secondary tier — surfaced via a new shared "More ▾" affordance,
│    App/Widgets/NavOverflowMenu.qml, per FINAL PRODUCT DECISIONS decision 2;
│    not a second persistent tab row)
│   ├── panels/SchedulingBaselinesPanel.qml         [unchanged content; gains
│   │                                                 the Baseline selector
│   │                                                 moved from the old
│   │                                                 global action bar]
│   ├── panels/SchedulingCalendarsPanel.qml         [unchanged content; gains
│   │                                                 the Calendar selector
│   │                                                 moved from the old
│   │                                                 global action bar]
│   └── panels/SchedulingActivityFeedPanel.qml      [unchanged content;
│                                                     placement confirmed
│                                                     secondary tier, FINAL
│                                                     PRODUCT DECISIONS
│                                                     decision 1]
└── dialogs/SchedulingDialogHost.qml                [unchanged]

── Removed entirely (not merely hidden) ──
panels/SchedulingResourcesPanel.qml   [content merges into Resource Leveling
                                        per decision 4; whether it becomes a
                                        reusable sub-component or is absorbed
                                        directly is an implementation detail]
panels/SchedulingDelaysPanel.qml      [content becomes a Gantt-tab filter;
                                        file deleted]
panels/SchedulingDetailPanel.qml      [replaced by the InspectorPanel
                                        instantiated directly in the Gantt
                                        tab; SectionDetailPage/
                                        ContextualActionToolbar/
                                        SectionScopedInlineMessage usage in
                                        SchedulingWorkspacePage.qml removed
                                        accordingly — decision 5, §32]

── Unchanged, no action ──
SchedulingWorkspace.qml   [still test-only, deferred per §39]
```

No files are created by this audit. This tree is the target shape for a
future, separately-authorized implementation pass. File-naming choice
(`SchedulingActivityTimelinePanel.qml` → `SchedulingGanttPanel.qml`) follows
the repository's own established convention of naming a panel file after its
tab's label (matching `SchedulingResourceLevelingPanel.qml` for "Resource
Leveling," `SchedulingDiagnosticsPanel.qml` for "Diagnostics," etc.) — this is
not a gratuitous rename, it is the same convention every other panel already
follows, now applied because the tab's own identity changed (decision 1).

---

## 41. Migration Sequence (amended, recommended, not executed)

1. Fix the two correctness bugs independently of any IA move (Detail-page
   Overview's missing `is_infeasible` check, §13 — fix it at the shared
   formatter source, since the new Inspector must not inherit it; the
   "Archive"/`deleteBaseline` label mismatch, §7) — zero IA risk, ship first.
2. Introduce `SchedulingPlanningContextHeader.qml` (Project selector,
   Refresh, Run CPM only) alongside the existing action bar, without yet
   removing anything, to verify it's behaviorally equivalent for those three
   controls before the next step.
3. Introduce `SchedulingOverviewPanel.qml` (KPI strip + needs-attention
   content) as a new tab, without yet removing the KPI strip from the
   page-level chrome.
4. Remove the KPI strip and the old always-visible action bar from
   `SchedulingWorkspacePage.qml`'s chrome once both replacements (steps 2–3)
   are confirmed equivalent; redistribute the Baseline selector to
   `SchedulingBaselinesPanel.qml` and the Calendar selector to
   `SchedulingCalendarsPanel.qml` (decision 3) rather than dropping them.
5. Remove the 5 duplicate "Refresh"/redundant "Run CPM" instances from
   Diagnostics/Resources/Delays/Calendars/Activity Feed, relying on the one
   persistent-header instance.
6. Remove the 5 redundant Diagnostics summary rows; rename/retitle the real
   Constraint Violations table to resolve the naming collision.
7. Rename/re-scope `SchedulingActivityTimelinePanel.qml` →
   `SchedulingGanttPanel.qml` (decision 1); update `panelTabs`' label from
   "Activity & Timeline" to "Gantt."
8. Fold the Delays tab's content into the Gantt tab as a filter option;
   remove the Delays tab entry from `panelTabs` and delete
   `SchedulingDelaysPanel.qml`.
9. Merge `SchedulingResourcesPanel.qml`'s content into
   `SchedulingResourceLevelingPanel.qml` as a new "Current Resource Load"
   section (decision 4); remove the Resources tab entry from `panelTabs` and
   delete `SchedulingResourcesPanel.qml` (or reduce it to a sub-component if
   its content is extracted for reuse rather than copied — implementation
   detail).
10. Build the new contextual `AppWidgets.InspectorPanel` inside the Gantt
    tab (dates/duration/float/status/constraint summary/dependency summary/
    resource-load summary/schedule-impact summary/"Open Task"), wiring it to
    both grid-row selection (already exists) and Gantt-bar selection (new —
    basic selection plumbing, not deep R4.5 interaction work, per §32).
11. Delete `SchedulingDetailPanel.qml` and the `SectionDetailPage`/
    `ContextualActionToolbar`/`SectionScopedInlineMessage`/`Loader` wiring
    in `SchedulingWorkspacePage.qml` that hosted it, once step 10's Inspector
    is confirmed to carry every fact still needed (decision 5, §32, §39).
12. Add Gantt view-control toggles (Critical Path, Dependency Lines,
    Baseline overlay, Zoom, Timescale) as in-page view controls, not new
    navigation (decision 8) — scope only as much as needed to not block
    the Inspector work; deeper rendering/interaction for these overlays may
    be deferred to R4.5 if it requires chart engineering beyond simple
    show/hide toggles (flag at implementation time).
13. Introduce the primary/secondary tab-tier visual treatment (mechanism
    still open, §33/§44) and move Baselines/Calendars — and, pending product
    confirmation, Activity Feed — into the secondary tier.
14. Adjust the Gantt tab's grid/timeline default proportions so the timeline
    no longer default-dominates (placement only — no R4.5 interaction work).
15. Re-run the full QML offscreen-load test and the Scheduling-specific test
    suite (§42) after each step, not just at the end.

Behavioral changes (the two bug fixes in step 1) are deliberately sequenced
separately from pure moves, per the directive's own instruction not to mix
them.

---

## 42. Test Impact

Tests that would need updates if the recommended IA above is implemented
(none modified by this audit):

| Category | Expected impact |
|---|---|
| Route tests | None — no route/shell change |
| Offscreen QML load (`test_qml_offscreen_loading.py`) | Must keep passing at every migration step; will exercise the new `SchedulingOverviewPanel.qml` once it exists |
| Component contracts | New/updated contract tests for `SchedulingOverviewPanel.qml`; existing panel contract tests for Diagnostics (row count changes), Delays (file removed/merged), Baselines/Calendars (tier change, if it affects visibility bindings) |
| Controller bindings | `scheduling_workspace_controller.py`/`scheduling_property_updates.py` tests for any property removed (e.g. if Delays-specific properties are folded into Schedule's filter state) |
| Navigation | `SchedulingWorkspaceState.qml`'s `panelTabs`/`panelIndex()` tests need updating for the new tab count/order; any test asserting the current 8-tab list verbatim will need its expected list updated |
| Selection | Detail-page section-index tests need updating for the trimmed 4-section list |
| Inspector | Resource Leveling inspector tests unaffected (no change) |
| Responsive | Any existing responsive/sizing test would need re-baselining against the new (smaller) always-visible chrome height |
| Resource leveling | Unaffected — no change to this tab |
| Diagnostics | Tests asserting the 6-row summary table's exact row count/labels need updating for the 5-row removal |

No tests were modified as part of producing this audit.

---

## 43. 1280×720 Mockup (amended — hierarchy only, no visual decoration)

```
┌ Planning ──────────────────────────────────────────────────────────────┐
│ [Overview] [Gantt] [Resource Leveling] [Diagnostics]      ▸ More ▾      │  ← primary tier
│                                                    (Baselines, Calendars,│
│                                                     Activity Feed*)      │
├──────────────────────────────────────────────────────────────────────────┤
│ Persistent Planning context header (present on all 4 primary tabs):    │
│   Project▾    [Refresh]  [Run CPM]                                     │
├──────────────────────────────────────────────────────────────────────────┤
│ Overview tab (default landing):                                        │
│   ┌────────┬────────┬────────┬────────┬────────┬────────┐              │
│   │Activit.│Critical│Delayed │OpenEnds│Infeasi.│Overload│              │
│   └────────┴────────┴────────┴────────┴────────┴────────┘              │
│   [ what needs attention — critical/infeasible/overloaded items ]      │
└──────────────────────────────────────────────────────────────────────────┘

┌ Gantt tab (first-class — grid + timeline as ONE integrated surface) ────┐
│ [Search] [Filter incl. "Delayed only"] [Customize] [Critical Path▢]    │
│ [Dependency Lines▢] [Baseline▢] [Zoom] [Timescale▾]  ← view controls,   │
│                                                          not navigation │
│ ┌──────────────────────────────────┬───────────────────────────────┐   │
│ │ Activity/WBS grid (13 cols)       │ Timeline (resized, no longer   │   │
│ │                                    │ default-wider than the grid)  │   │
│ └──────────────────────────────────┴───────────────────────────────┘   │
│   [grid row OR timeline bar selection → Inspector: dates/duration/     │
│    float, Infeasible/Critical/Flexible status, constraint summary,     │
│    dependency summary, resource-load summary, schedule-impact summary, │
│    Open Task]                                                          │
└────────────────────────────────────────────────────────────────────────┘

┌ Resource Leveling tab (now owns Current Resource Load too) ────────────┐
│ Current Resource Load table                                             │
│ Current Conflicts · [Preview]   before/after · finish-date shift       │
│ ┌───────────────────────┬───────────────────────────────┐              │
│ │ Proposed-moves table   │ Inspector (unchanged)         │              │
│ └───────────────────────┴───────────────────────────────┘              │
│                                          [Apply Leveling Plan] (confirm)│
└──────────────────────────────────────────────────────────────────────────┘

┌ Diagnostics tab ─────────────────────────────────────────────────────────┐
│ [Search]                                                                  │
│  Constraint &amp; Schedule Violations table (renamed, deduplicated)          │
└────────────────────────────────────────────────────────────────────────────┘
```
`*` Activity Feed's tier placement is confirmed secondary (FINAL PRODUCT
DECISIONS decision 1).

---

## 44. 1024×640 Mockup (amended)

```
┌ Planning ─────────────────────────────────────────┐
│ [Overview][Gantt][Res.Leveling][Diag.] ▸ More      │  ← wraps to 1 row if
├─────────────────────────────────────────────────────┤    labels shortened
│ Project▾  [Refresh][RunCPM]   (persistent header)  │
├─────────────────────────────────────────────────────┤
│ Overview:                                          │
│  ┌─────┬─────┬─────┬─────┬─────┬─────┐            │
│  │Act. │Crit.│Delay│Open │Infe.│Over.│            │
│  └─────┴─────┴─────┴─────┴─────┴─────┘            │
│  [ needs-attention list, scrollable ]              │
└─────────────────────────────────────────────────────┘

┌ Gantt tab (narrow width, below compactContentBreakpoint=1024) ─────┐
│ [Search][Filter][Customize]  [Grid|Timeline] view-mode toggle       │
│ (Split option hidden below the breakpoint — FINAL PRODUCT DECISIONS │
│ decision 4). Only ONE of Grid or Timeline consumes the primary      │
│ content width at a time; no vertical stacking of both.              │
└──────────────────────────────────────────────────────────────────────┘

┌ Resource Leveling tab (narrow width) ──────────────┐
│ Current Resource Load (stacked above conflicts)     │
│ [Preview]   before/after metrics (stacked, not row) │
│ Proposed-moves table (full width)                    │
└────────────────────────────────────────────────────────┘

(Gantt-tab InspectorPanel, below the breakpoint: hosted inside
App/Widgets/SlideOverPanel.qml as a scrimmed slide-in-from-right overlay
instead of a fixed side slot — FINAL PRODUCT DECISIONS decision 5. Above the
breakpoint it renders exactly as Resource Leveling's InspectorPanel does
today, a fixed-width side panel.)
```

At 1024×640, the Gantt tab's grid/timeline split, the Resource Leveling
tab's moves-table/inspector split, and the new Gantt-tab InspectorPanel all
need a real responsive fallback — this is now locked (not an open question)
by FINAL PRODUCT DECISIONS decisions 4 and 5: a Grid/Timeline view-mode
toggle for the Gantt tab, and a `SlideOverPanel`-hosted Inspector below the
shared `compactContentBreakpoint`.

---

## 45. Final Decisions (amended)

1. **Is the current Scheduling workspace objectively overcrowded from its
   QML structure?** Yes — confirmed via layout constants (§18), not
   subjective impression: always-visible chrome alone consumes ~250–320px
   before any tab content, which is a large fraction of a 640px-tall window.
   (Unchanged.)
2. **What exactly causes the crowding?** Always-visible page-level chrome,
   KPI/Diagnostics duplication, Detail-page duplication of 5 of 8 tabs,
   6x/4x toolbar-action duplication, and a non-interactive Gantt pane that
   out-competes its own table for width (§19). (Unchanged.)
3. **Is the problem visual styling or information architecture?**
   **Information architecture.** (Unchanged.)
4. **Should we add another Level-1 PM navigation item?** **No** (§24,
   reaffirmed by decision 2 — unchanged).
5. **Should Planning have internal navigation?** **Yes** — now four primary
   destinations (Overview, Gantt, Resource Leveling, Diagnostics) plus two
   secondary (Baselines, Calendars) — a consolidation and re-weighting of
   the existing tab strip, not a new navigation layer (decision 2).
6. **Should Resource Leveling get its own Planning page?** It already has
   one; **it now also absorbs the former Resources tab's content**
   ("Current Resource Load") rather than that content living separately
   (§25, decision 4).
7. **Should Diagnostics get its own Planning page?** It already has one;
   content should be deduplicated, not further separated (§26 — unchanged).
8. **Should Dependencies get its own page or remain Schedule/Task-Detail
   driven?** **Remain Gantt/Task-Detail driven** — per-activity, read-only
   context now surfaces in the Gantt tab's contextual `InspectorPanel`
   rather than a trimmed full-page Detail section; CRUD still stays
   exclusively in Task Detail (§12, §28, decision 5).
9. **Should Constraints get its own page or primarily live in Task edit +
   diagnostics?** **Primarily live in Diagnostics (violations) + the Gantt
   Inspector (per-activity summary)** — no dedicated tab; Task Editor
   remains the only place constraints are *edited* (§13, §28, decision 5).
10. **Where should Baselines live?** Stay a tab, secondary tier — unchanged
    (§16, §28).
11. **Where should the Gantt live?** **It is now the primary "Gantt" tab
    itself** — the activity/WBS grid and timeline are one integrated
    surface, not a pane embedded in a separate "Schedule" tab (decision 1).
    The grid/timeline sizing fix (stop the timeline out-competing the grid)
    still applies within this one tab; deeper interactivity remains R4.5's
    (§17, §37).
12. **Which current sections should disappear from the default landing
    screen?** The KPI strip still moves to the new Overview tab; Baselines,
    Calendars, and Activity Feed (confirmed, FINAL PRODUCT DECISIONS
    decision 1) move to the secondary tier — but the Project/Refresh/Run-CPM
    controls now persist across all
    four primary tabs rather than being Overview-exclusive (§28, §29,
    decision 3 — this is the one respect in which the amended answer differs
    from the original).
13. **Which content should lazy-load?** Resource Leveling and baseline
    variance already do; the structural opportunity remains making the
    secondary tier genuinely `Loader`-gated rather than always resident
    (§35 — unchanged).
14. **Which current actions should leave the global toolbar?** The
    persistent header keeps only Project/Refresh/Run CPM; the Baseline and
    Calendar selectors leave it for their respective tabs (decision 3); the
    5–6 duplicate tab-local re-declarations of Refresh/Run CPM still leave
    entirely (§7, §31).
15. **What is the exact recommended QML structure?** See the amended §40.

---

## FINAL PRODUCT DECISIONS (second amendment — locks all remaining IA
questions; implementation begins after this point)

**Status: documentation-only update, same as the first amendment. No
QML/Python was changed producing this section; no re-audit was performed.**
Ten remaining decisions are locked below, closing every item the first
amendment had left open except genuinely technical ones (exact breakpoint
pixel values, which line-for-line existing component to instantiate) —
those are implementation detail, not IA uncertainty, and are called out as
such at the end of this section.

1. **Activity Feed** is a confirmed secondary destination. Final secondary
   list: **Baselines, Calendars, Activity Feed.** It is not restored inside
   selected-activity detail (it was already excluded from the Inspector's
   fact list, §32) — it is project-level historical/narrative context, not
   a Diagnostics concern.
2. **Secondary navigation mechanism: one compact "More ▾" affordance**, not
   a second persistent tab row. Research confirms no dedicated
   overflow/nav-menu component exists yet, but the pieces to build the
   smallest reusable one already do: `App/Widgets/AnchoredPopup.qml` (a
   positioned `Popup` shell with `anchorItem`/`placement`/`clampToParent`)
   is the same primitive `ContextBar.qml`'s tenant/organization switcher and
   `PortfolioGovernanceToolbar.qml`'s compact-mode overflow already use for
   exactly this "button opens a small list of destinations" shape. The
   target implementation is a new **shared** component (not
   Scheduling-local) — e.g. `App/Widgets/NavOverflowMenu.qml` — composed
   from `AnchoredPopup` plus row delegates modeled on `ContextBar.qml`'s
   `ContextChip` pattern, with one addition neither existing usage has: an
   `isActive`/current-selection highlight per row, so opening the menu while
   on "Baselines" visibly shows "Baselines" as current. This satisfies the
   instruction to prefer an existing primitive and, where one is
   insufficient (no existing component has active-item highlighting),
   extend the smallest reusable shared piece rather than inventing a
   Scheduling-only control.
3. **Final primary navigation, reaffirmed:** Overview · Gantt · Resource
   Leveling · Diagnostics. **Final secondary, reaffirmed:** Baselines ·
   Calendars · Activity Feed. No new PM Level-1 navigation item.
4. **Gantt responsive model, locked:** at sufficiently wide widths, Grid |
   Timeline remain split side-by-side (unchanged from the first amendment).
   At compact widths (reusing the app's own existing
   `Theme.AppTheme.compactContentBreakpoint` = 1024, the same constant
   `PortfolioGovernanceToolbar.qml` already keys off of — no new breakpoint
   invented), the Gantt tab does **not** vertically stack the full grid and
   timeline. Instead it exposes a **view-mode control** — "Grid | Timeline"
   — where only one consumes the primary content width at a time; a "Split"
   option remains available whenever width permits it. This is a view mode,
   not a navigation level (decision 9 below), and it is placement/behavior
   only — no R4.5 chart-interaction work.
5. **Gantt Inspector responsiveness, locked.** `InspectorPanel.qml` itself
   has **zero** existing responsive/compact/overlay support (confirmed by
   direct read: it is an always-fixed-width, `Theme.AppTheme.inspectorWidth`
   `Rectangle`, no breakpoint or modal-mode property of any kind) — so there
   is nothing to "reuse from InspectorPanel" directly. What the app *does*
   already have, and what this decision reuses rather than invents, is (a)
   the same `compactContentBreakpoint` constant from decision 4, and (b) an
   existing shared, currently-unused-for-this-purpose modal primitive,
   `App/Widgets/SlideOverPanel.qml` (a scrimmed, animated slide-in-from-right
   panel). Locked behavior: at width ≥ the breakpoint, the Gantt Inspector
   renders exactly as Resource Leveling's already does today (a fixed-width
   side panel). Below the breakpoint, the same `InspectorPanel` instance is
   hosted inside `SlideOverPanel` instead of a side `Layout.preferredWidth`
   slot — the Gantt grid/timeline never permanently loses width to a fixed
   inspector at narrow sizes. This is the smallest reusable responsive
   behavior consistent with the rest of the app (the same breakpoint,
   composed with an existing shared modal primitive), not a
   Scheduling-only inspector framework.
6. **Schedule Impact inside the Inspector, locked.** Never automatic on
   selection change. Immediately shown, cheap, already-authoritative facts:
   dates, duration, float, Infeasible/Critical/Flexible status, constraint
   summary, dependency summary, resource-load summary. Schedule Impact
   itself starts in a `"Not analyzed"` state with an explicit **"Analyze
   Impact"** trigger; only on click does the real backend path run.
   **Reuse determination:** the Scheduling workspace already has one working,
   backend-authoritative chain for this
   (`workspaceController.computeScheduleImpact({})` →
   `run_compute_schedule_impact` → `ScheduleChangeImpactService.analyse()`
   via two real CPM passes, confirmed with no client-side math duplication
   anywhere in that path) — but its DTO
   (`SchedulingChangeImpactDto`: `affectedCount`, `maxProjectFinishShiftDays`,
   `requiresApproval`, `newlyCriticalCount`, `noLongerCriticalCount`,
   `affectedTasks[]`) does not carry the downstream-exposure/
   critical-path-change/conflict fields this decision's summary explicitly
   asks for. Task Detail's own Schedule Impact feature
   (`TasksScheduleImpactSection.qml`/`schedule_impact_builder.py`) is backed
   by the **same core `ScheduleChangeImpactService`**, just through a richer
   sibling DTO (`TaskScheduleImpactOverviewDesktopDto`/
   `ScheduleImpactReportDto`) that already carries exactly those fields. The
   Inspector's "Analyze Impact" trigger should call through to **that
   richer, already-existing serialization** rather than the narrower one the
   old `SchedulingDetailPanel.qml` used — this is wiring a new caller onto
   an existing, authoritative core service and its existing richer DTO, not
   writing new schedule-impact math anywhere, QML or Python. Invalidate a
   selected task's cached impact result whenever the relevant schedule/
   project state changes (new selection, Apply Leveling, Run CPM, baseline
   change) — do not let a stale impact silently persist across a
   recalculation.
7. **Resource content, reaffirmed:** merges into Planning → Resource
   Leveling (Current Resource Load, alongside Current Conflicts / Preview /
   Proposal / Apply). No separate primary Resources destination; R5
   continues to own broader cross-project Workload Management (unchanged
   from the first amendment).
8. **Activity Detail, reaffirmed:** `SchedulingDetailPanel.qml`'s full-page,
   8-section architecture is retired outright, not trimmed. Gantt row/bar
   selection uses the shared `InspectorPanel` (per decision 5's
   responsiveness treatment). None of Overview/Dependencies/Constraints/
   Calendars/Baselines/Resources/Activity-Feed/Change-Impact get rebuilt as
   a second mini-application inside the Inspector — only the fact set in
   decision 6 plus "Open Task." Task Detail remains authoritative for full
   editing/CRUD.
9. **Navigation depth rule, reaffirmed:** PM navigation + Planning
   navigation + contextual Inspector — three levels, no more. The Gantt
   view controls named in decision 4 (Grid/Timeline/Split), plus Zoom,
   Timescale, Critical Path, Dependency Lines, and Baseline overlay, are all
   view controls, never navigation.
10. **This section supersedes the first amendment's "uncertain decisions"
    list.** Every item that list raised is now closed: Activity Feed
    placement (decision 1), the secondary-tier mechanism (decision 2), the
    compact Gantt structural model (decision 4), Gantt Inspector
    responsiveness (decision 5), and the Schedule Impact loading policy
    (decision 6) are all locked above.

**Genuinely remaining technical uncertainties (implementation detail, not
IA questions):**
- Exact pixel/behavior details of `NavOverflowMenu.qml`'s active-item
  highlight styling (decision 2) — a visual-styling choice, not a
  placement question.
- Exact breakpoint value(s) if `compactContentBreakpoint` (1024) proves not
  to be the right threshold once the Gantt tab's real minimum grid/timeline
  widths are measured against it in practice (decision 4/5) — tune, don't
  redesign.
- Whether `SchedulingResourcesPanel.qml`'s content becomes a reusable
  sub-component or is copied directly into
  `SchedulingResourceLevelingPanel.qml` (§39/§40, decision 7) — an
  implementation-time code-organization choice with no user-facing effect
  either way.
- The Task Detail vs. Scheduling schedule-impact DTO consolidation
  (§39 cross-cutting note) — decision 6 resolves *which* existing DTO the
  new Inspector trigger calls, but whether the two call sites should
  eventually share one QML component as well as one backend service remains
  a cross-workspace question beyond this audit's Scheduling-only scope.
