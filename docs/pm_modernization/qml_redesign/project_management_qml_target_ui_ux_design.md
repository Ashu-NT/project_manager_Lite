# Project Management Target UI/UX Design

Status: R0.1 approved; behavior-preserving R0.5 complete; R1 (query integrity and truthful controls) complete; R2 (PM navigation and project context) complete; visual/product redesign (R3-R8) not started  
Depends on: `project_management_qml_existing_state_audit.md`  
Target: maintainable enterprise desktop PM, designed responsively for available logical window width/height rather than any fixed resolution (revised from the original flat "1024x768 minimum" -- see section 11). Operational floor: 1024x640. Primary acceptance sizes: 1280x720, 1366x768, 1440x900, 1920x1080. Navigation/chrome collapses before business content becomes unusable.

## 1. Design outcome

The target PM experience should feel like one project-delivery product rather than ten unrelated shell destinations. It should preserve the real capabilities already present, remove controls that do not perform their label, and introduce a consistent hierarchy:

```text
Portfolio context -> project context -> work item context
```

The target does not require a new backend source of truth. QML consumes disposable read models, sends commands through existing desktop APIs, and receives authoritative results/events. Search, filtering, sorting, and pagination move to server/read-query contracts wherever a collection can exceed a complete selected-entity boundary.

## 2. Target information architecture

### 2.1 Approved PM-local destinations

| Destination | Current capabilities grouped | Scope |
|---|---|---|
| Overview | Dashboard | global or active project |
| Portfolio | Portfolio | global/organization |
| Work | Projects, Tasks, Scheduling | global catalog plus project execution |
| Workload Management | Resources, Timesheets | organization/global plus active project |
| Finance | Financials | active project required |
| Governance | Register, Collaboration | global or active project |

The route target is one canonical Project Management module/workspace route. Inside that route, PM-local navigation presents the six approved destinations, with secondary navigation inside Work, Workload Management, and Governance. The six destinations must not become six unrelated global application-drawer entries unless implementation proves the shell cannot host a unified PM module route.

Note (R2): the group formerly named "People & Time" is "Workload Management" (internal destination id `workload`). It covers project resource allocation/utilization and Timesheets; "People & Time" read as too HR-specific given PM resources can include equipment, not only staff. Resources' and Timesheets' own capability packages, controllers, and legacy route IDs are unchanged by this rename.

The ten existing route IDs remain only as migration and deep-link compatibility routes. While they exist, each resolves into the canonical PM workspace with the corresponding PM-local destination selected. They are removed only after callers, saved links, tests, and shell dependencies migrate. R0.5 preserves their current behavior; canonical-route implementation belongs to R2.

```text
Project Management
|-- Overview
|-- Portfolio
|-- Work
|   |-- Projects
|   |-- Tasks
|   `-- Planning
|-- Workload Management
|   |-- Resources
|   |-- My Time
|   `-- Review Queue
|-- Finance
`-- Governance
    |-- Register
    `-- Collaboration
```

"Planning" is the user-facing label for the existing Scheduling capability. "Finance" is the UI label while the existing `financials` route/package contract remains unchanged during migration.

### 2.2 Scope rules

| Capability | All projects | Active project | Behavior |
|---|---:|---:|---|
| Overview | yes | yes | organization summary or selected-project dashboard |
| Portfolio | yes | optional | portfolio is global; project selection is drill-through, not a filter by default |
| Projects | yes | selected row | global catalog; opening/pinning can set active project |
| Tasks | yes | yes | cross-project list or selected-project list |
| Planning | no | required | prompt for project before loading schedule |
| Resources | yes | optional | global pool or project allocation context |
| My Time | role/user scoped | optional | current user's assignments and period |
| Review Queue | yes | optional | permission-scoped queue with real query filters |
| Finance | no | required | no financial state without explicit project |
| Register | yes | yes | global governance or project register |
| Collaboration | yes | yes | query-scoped inbox/activity |

## 3. Project context contract

A persistent active-project context is recommended, but it is a controller/API dependency rather than a QML variable.

### 3.1 Required contract

Introduce a PM-scoped context object owned by `ProjectManagementWorkspaceCatalog` with:

- `activeProjectId`, `activeProjectLabel`, and `hasActiveProject`.
- project options scoped to the active tenant and organization.
- `selectProject(id)`, `clearProject()`, and `openProject(id, sourceRoute)` commands.
- a change signal consumed by project-aware controllers.
- reset on tenant/organization/session change.
- rejection of stale or inaccessible IDs during revalidation.
- explicit workspace policy: `required`, `optional`, or `not-applicable`.
- route state containing entity IDs, not copied DTOs.

Controllers remain responsible for their own query filters. A context change requests a refresh but does not silently discard unsaved dialog input. Dialogs with dirty state must ask whether to discard before accepting a context switch.

### 3.2 Pinning rule

- Opening a project detail does not silently change all workspaces on single-click selection.
- "Set active" or project activation pins the project.
- Planning and Finance require a pin or explicit selector choice.
- Tasks, Resources, Register, Collaboration, and Overview support "All projects" where their query contracts do.
- Portfolio selection does not change active context until the user chooses Open Project or Set Active.

### 3.3 Context bar

The PM context bar is below the application header and above workspace content:

```text
+------------------------------------------------------------------+
| Project Management  | Project: [All projects / Plant Upgrade v] |
| Scope status        | Open project | Clear | context validation  |
+------------------------------------------------------------------+
```

At compact width it becomes a single project selector plus an overflow menu. It must not duplicate the page title or section navigation.

## 4. Navigation model

Navigation has three explicit levels:

1. Application navigation: one canonical Project Management module/workspace route.
2. Workspace navigation: Projects/Tasks/Planning, Resources/My Time/Review Queue, or Register/Collaboration.
3. Detail navigation: inspector sections or full-detail section rail.

Rules:

- The shell owns entry into the canonical Project Management route.
- The PM workspace shell owns the six PM-local destinations, their secondary selection, and active project display.
- A detail page owns section selection.
- Back returns to the exact list query, page, selection, and scroll state.
- Canonical deep links are `(project_management_route, destination, entity_id, optional_section)` and never serialized view models. The ten compatibility route IDs translate into this shape during migration.
- Breadcrumbs appear only on full detail: `Projects / PRJ-104 / Schedule` or `Tasks / TSK-208 / Time`.
- The fixed section rail remains on wide detail pages; under 1180 available content width it becomes a compact section dropdown/drawer.

## 5. Target page patterns

### 5.1 Enterprise catalog pattern

Use for Projects, Tasks, Resources, and Register.

- Single click selects one row.
- On content width at least 1180, selection opens a read-only inspector without navigation.
- On compact widths, selection only highlights the row.
- Double-click, Enter, or Open opens full detail.
- Checkboxes select bulk scope and suppress the inspector.
- Primary Create remains in the list toolbar.
- Selection-specific actions appear in the contextual/bulk bar, with overflow after two visible actions.
- Table query state is represented by search, filter chips, server sort, page, and page size.
- Empty state distinguishes "no records" from "no query matches."

Inspector candidates and scope:

| Entity | Inspector content | Full detail still required |
|---|---|---|
| Project | status, owner, dates, health, next milestone, key totals | resources, schedule, tasks, finance, activity |
| Task | status, progress, assignees, dates, blockers, quick progress | dependencies, time, collaboration, schedule impact |
| Resource | availability, role, department/site, current allocation | capacity calendar, assignments, skills, cost rates |
| Register entry | severity/status/owner/due date, response summary | impact, links, response history, activity |

### 5.2 Console pattern

Use for Planning, Finance, Portfolio, and Overview. These are not forced into inspectors.

- Sticky scope/action bar.
- Purpose-specific tabs or grouped section navigation.
- One primary work surface at a time.
- Query-backed tables inside panels where collections can grow.
- No fixed multi-workflow bottom panel.
- Commands open bounded dialogs or dedicated command drawers; complex analysis stays on the page.

### 5.3 Queue pattern

Use for Collaboration Inbox/Approvals and Timesheet Review Queue.

- Server query owns search, filters, sort, and page.
- Saved views store query definitions, not row snapshots.
- Single selection reveals context actions and optional inspector.
- Approval/rejection reasons use purpose-built dialogs where required.
- Optimistic visual changes occur only if mutation contracts support conflict recovery; otherwise show busy, result, then refresh.

## 6. Target wireframes

### 6.1 PM Overview

```text
+--------------------------------------------------------------------------+
| PM context: [All projects v]                  Updated 10:42  [Refresh]   |
+--------------------------------------------------------------------------+
| Overview                                                                |
| [Portfolio health] [Delivery] [Capacity] [Cost] [Timesheets]            |
+------------------------------------+-------------------------------------+
| Delivery trend                     | Attention required                  |
| real chart                         | delayed tasks / risks / approvals   |
+------------------------------------+-------------------------------------+
| Operational tabs: Delays | Risks | Capacity | Cost | Approvals           |
| Search [........]  Filters [2]                    Columns | Export         |
| query-backed table                                      1-25 of N        |
+--------------------------------------------------------------------------+
```

At project scope, metrics and operational tabs use the selected project. At all-project scope, every displayed metric must come from an organization-scoped query, not a sum of the first page.

### 6.2 Portfolio

```text
+--------------------------------------------------------------------------+
| Portfolio | Scenario [Current v] Compare [None v]       [New Scenario]   |
+--------------------------------------------------------------------------+
| [Value] [Risk] [Capacity] [Budget exposure] [Delivery confidence]       |
+--------------------------------------------------------------------------+
| Executive | Heatmap | Intake | Scenarios | Capacity | Dependencies       |
+--------------------------------------------------------------------------+
| active tab work surface                                                  |
| Search / real filters / server sort / page                               |
|                                                                          |
| selected row -> decision inspector at wide width                         |
+--------------------------------------------------------------------------+
```

Intake, templates, scenarios, and dependencies become full tabs or focused drawers, not children of a 268-pixel bottom panel. Rebalance is absent until backed by a real command.

### 6.3 Projects list, wide

```text
+--------------------------------------------------------------------------+
| Work: Projects | Tasks | Planning                         [New Project]   |
| Search [........] Status [All] Site [All]  More filters  Columns Export  |
+------------------------------------------------+-------------------------+
| Projects table                                 | Project inspector       |
| [ ] Code Name Status Owner Site Start End       | PRJ-104 Plant Upgrade  |
| [x] ...                                         | Active | On track       |
|                                                 | owner / dates / health  |
|                                      1-25 of N  | [Open] [Set active]     |
+------------------------------------------------+-------------------------+
```

At compact width the inspector is removed and the table takes the full width.

### 6.4 Project detail

```text
+--------------------------------------------------------------------------+
| Projects / PRJ-104 / Overview                      Edit  Status  More v   |
| Plant Upgrade | Active | PM: A. Smith | 01 Mar - 30 Nov                  |
+----------------------+---------------------------------------------------+
| Overview             | fixed section message/action area                 |
| Delivery             | active section                                    |
|   Schedule           |                                                   |
|   Tasks              |                                                   |
| People               |                                                   |
|   Resources          |                                                   |
| Commercial           |                                                   |
|   Finance            |                                                   |
| Governance           |                                                   |
+----------------------+---------------------------------------------------+
```

At compact width, the left rail is a "Section: Overview" dropdown. Inventory/procurement links remain capability-gated external module navigation.

### 6.5 Tasks

```text
+--------------------------------------------------------------------------+
| Work: Projects | Tasks | Planning                         [New Task]      |
| Project [All v] Search [...] Status [...] Assignee [...] More filters    |
| Active chips: Delayed x | My tasks x                         Save view    |
+------------------------------------------------+-------------------------+
| query-backed task table                         | Task inspector          |
| WBS Code Task Project Status Assignees Dates    | TSK-208 Cable Pull      |
|                                                 | progress / blockers     |
|                                      1-50 of N  | Update progress | Open  |
+------------------------------------------------+-------------------------+
```

No board is promised by this design because no authoritative board ordering/query contract was proven. A board can be a later product capability, not a QML-only rearrangement of one page.

### 6.6 Planning

```text
+--------------------------------------------------------------------------+
| Planning | Project [Plant Upgrade v] Baseline [Current v] Calendar [...] |
| [Run CPM] [Save Baseline] [More v]                                       |
+--------------------------------------------------------------------------+
| Timeline | Diagnostics | Resources | Baselines | Delays | Calendars      |
+--------------------------------------------------------------------------+
| Search/filter bar                                                        |
| activity table                         | synchronized timeline canvas     |
| server page                            | critical path and milestones     |
+--------------------------------------------------------------------------+
```

The detail view opens as a right inspector at wide width for quick activity review and as full detail for dependency/calendar/baseline edits.

### 6.7 Workload Management

```text
+--------------------------------------------------------------------------+
| Workload Management: Resources | My Time | Review Queue                  |
+--------------------------------------------------------------------------+
| My Time: Period [05-11 Aug v] Project [All v]      [Add Time Entry]      |
| assignment/week grid or entry table backed by complete period query      |
| totals: regular | overtime | billable | remaining                        |
| [Save Draft] [Submit Period]                                             |
+--------------------------------------------------------------------------+
```

```text
+--------------------------------------------------------------------------+
| Review Queue | Search [...] Status [...] Project [...] Period [...]      |
| query-backed review table                                      1-25 of N |
| selected: [Approve] [Reject...] [Open] [More v]                         |
+--------------------------------------------------------------------------+
```

My Time reuses existing entry command semantics but gets a dedicated controller/query projection. Review Queue filters must be added to `list_review_queue_page`; until then unsupported controls stay hidden.

Default selection is capability-driven: users with personal time-entry capability enter My Time; reviewer-only users may enter Review Queue. A user with both capabilities defaults to My Time and can switch locally to Review Queue.

### 6.8 Resources

```text
+--------------------------------------------------------------------------+
| Resources | Project [All v] Search [...] Type [...] Dept [...] Site [...]|
| [New Resource]                                                           |
+------------------------------------------------+-------------------------+
| resource table                                  | availability inspector  |
| code/name/type/role/dept/site/load               | next 14/30 days         |
|                                      1-25 of N  | assignments | Open      |
+------------------------------------------------+-------------------------+
```

Department/site filters are a backend query dependency.

### 6.9 Finance overview

```text
+--------------------------------------------------------------------------+
| Finance | Project: Plant Upgrade | EUR                Refresh | Export v  |
| Approved Budget | Forecast | Actual | Commitments | Margin projection     |
+----------------------+---------------------------------------------------+
| Overview             | variance narrative and trend                      |
| Planning             | budget / planned cost / forecast                  |
| Cost Control         | actuals / commitments / changes                   |
| Commercial           | billing evidence / profitability                  |
| Configuration        | profile / cost codes / rate cards                 |
| Reports & Activity   |                                                   |
+----------------------+---------------------------------------------------+
```

### 6.10 Billing preparation

```text
+--------------------------------------------------------------------------+
| Commercial / Billing Preparation                    [New Preparation]    |
| PM prepares evidence. Accounting owns invoice and receivable truth.      |
+--------------------------------------------------------------------------+
| Billing profile [Draft/Active]                    [Configure] [Activate]  |
| Schedule lines                                 [Add Milestone/Line]       |
| Preparations table: period, basis, amount, readiness, status              |
| selected preparation -> sources/evidence inspector                        |
| [Add Fixed] [Add Approved Time] [Add Cost Plus] [Mark Ready] [Submit]    |
+--------------------------------------------------------------------------+
```

Every button maps to an existing finance command. "Create invoice", "mark paid", tax, and ledger posting controls are prohibited in PM.

### 6.11 Governance

```text
+--------------------------------------------------------------------------+
| Governance: Register | Collaboration                                    |
| Project [All v] | query-specific filters                                |
+--------------------------------------------------------------------------+
| Register: server list + inspector + full detail                          |
| Collaboration: Inbox | Mentions | Approvals | Activity                   |
|                server list + context actions + detail                    |
+--------------------------------------------------------------------------+
```

## 7. Target toolbar and action policy

### 7.1 Toolbars

- Page toolbar: create, export, and query controls that apply to the complete page.
- Context toolbar: selected-record actions only.
- Detail header: back/breadcrumb, identity, lifecycle state, and at most two primary actions plus More.
- Section toolbar: create/action for the active detail section only.
- Bulk bar: appears after checkbox selection, bottom-center in one horizontal row; it does not move table layout.

The responsive context toolbar shows at most two full buttons. Remaining actions move to a keyboard-accessible More menu. Destructive actions are separated and styled as danger.

### 7.2 Command behavior

- Create/edit dialogs validate locally for shape and through command models for domain constraints.
- Busy state disables repeat submission.
- Success closes the dialog only after authoritative command success.
- Validation/conflict/permission errors stay inside the originating dialog or fixed detail message.
- Delete/archive uses confirmation only when the command is immediately destructive.
- Purpose-built lifecycle dialogs are themselves confirmation and should not launch a second generic confirmation.
- Approve may be direct only when no reason or impact acknowledgement is required.
- Reject, reverse, decline, and reopen require reason dialogs where the backend accepts or mandates a reason.
- Permission-denied states disable or hide actions with an explanatory tooltip; service authorization remains mandatory.

## 8. Query, filter, sort, and pagination policy

### 8.1 Required server behavior

Every scalable list query accepts:

```text
scope + search + filters + sort_key + sort_direction + page + page_size
```

It returns items, page, page size, total count, normalized query state, and a stable ordering with ID tie-breaker. Export uses the same query definition but streams all authorized results independently of the visible page.

### 8.2 Capability matrix

| Workspace | Backend search now | Backend filters now | Backend page now | Required dependency |
|---|---:|---:|---:|---|
| Projects | yes | status | yes | server sort; site/owner/org filters |
| Tasks | yes | status/project | yes | server sort; assignee/date/priority filters |
| Planning activity | yes | status/critical/delayed | yes | server sort |
| Resources | yes | active/category | yes | server sort; department/site/project filters |
| Register | yes | project/type/status/severity | yes | server sort |
| Timesheet Review | no | status | yes | search, project, period, assignee, server sort |
| Collaboration | authoritative Inbox/Mentions pages | explicit query context | SQL page/total | Platform-owned Approvals; bounded recent Activity and current Presence |
| Portfolio heatmap | partial | scenario/intake status | page state | formalize server search/sort and totals |
| Dashboard operational | search/page controller path | tab/view dependent | controller path | prove query-global totals and server sort |
| Finance collections | selected readers | project/lifecycle dependent | mixed | remove fixed 50 caps; page actuals/commitments |

### 8.3 Client filtering is allowed only when

- the API contract declares the collection complete;
- it is bounded by one selected entity/project/period;
- the UI labels it as in-view filtering when appropriate; and
- no total/count implies unseen records are included.

## 9. Finance interaction design

The Finance intent hierarchy and phased command rollout are approved. Project Finance owns commercial and managerial project-finance workflows; Accounting remains authoritative for statutory records, invoices, receivables, payments, tax, and ledger truth.

Finance sections should be reorganized by user intent, not backend table name:

| Group | Sections | Interaction |
|---|---|---|
| Overview | KPIs, profitability, variance, cash flow | read/decision support |
| Planning | budget versions/lines, planned costs, forecast | governed commands and comparisons |
| Cost Control | actuals, commitments, changes | canonical lifecycle and drill-through |
| Commercial | billing profile/schedule/preparations | evidence preparation commands |
| Configuration | financial profile, cost codes, rate cards | permission-gated configuration |
| Reports & Activity | canonical exports, audit/activity | read/export |

Command implementation order follows risk: configuration, budget/planning, cost control, commercial. Accounting-owned records remain external read outcomes or links. Snapshot/read-model components may cache for display but must be disposable, versioned, and rebuilt from authoritative services.

## 10. Design-system target

### 10.1 Reuse unchanged

- `AppTheme`, `AppIcon`/semantic icon registry.
- shared text fields, combo boxes, date fields, labels, buttons, status chips.
- `WorkspaceFrame`, `EntityDialog`, `ConfirmationDialog`.
- `InlineMessage`, `SectionScopedInlineMessage`, `LoadingOverlay`, `EmptyState`.
- `KpiStrip`, `SectionHeading`, `SectionCard`, `ActivityFeed`.

### 10.2 Extend shared primitives

- `DataTable`: explicit `sortingMode: client|server|none`, emit-only server sort
  intent, authoritative controller state binding, and fail-closed invalid modes.
- `ContextualActionToolbar`: overflow action menu, compact icon/text rules, keyboard semantics.
- `SectionDetailPage`: compact section selector below a content-width threshold.
- `InspectorPanel`: responsive optional inspector with focus return and close behavior.
- `PermissionState`: unavailable/denied/hidden presentation with reason.
- dialog width use: compact, standard, and wide tokens clamped to available width.

These extensions belong in `src/ui_qml/shared` only if Platform, Inventory, or Maintenance can use the same semantics. PM must not push project-specific behavior into generic components.

### 10.3 PM-specific primitives

- `ProjectContextBar`: active-project scope and validation.
- `PmWorkspaceNav`: grouped secondary PM destination navigation.
- `PmCatalogWorkspace`: query toolbar + table + responsive inspector + pagination composition.
- `PmDetailHeader`: breadcrumb, entity identity, status, compact actions.
- `PlanningWorkspaceShell`: selectors + planning tabs + synchronized timeline surface.
- `FinanceSectionShell`: finance ownership notice, lifecycle state, query collection, and command slot.

PM-specific primitives consume shared controls but stay in the PM module.

## 11. Responsive behavior

**Governing rule (applies to every PM page, not only new R3+ work): do not
design for a fixed desktop resolution. Design responsively for available
logical window width and height.** No PM page may assume a specific pixel
size for the application window or for its own content area. Treat every
dimension below as whole-application *logical* pixels (post-DPI-scaling),
not physical display resolution -- a 1024-logical-pixel-wide window is the
target regardless of the physical monitor's pixel density.

Use available content width and height after global application chrome
*and* PM-local navigation are deducted -- never window width, and never an
assumed constant. Do not assume the PM content area itself is 1024px wide
(or any other fixed number): the shell drawer and PM secondary nav both
consume real space first, and that space itself changes as chrome
collapses at narrower sizes.

### Required acceptance sizes (whole-application logical pixels)

| Size | Role |
|---|---|
| 1024 x 640 | Minimum supported compact window |
| 1280 x 720 | Primary small-laptop target |
| 1366 x 768 | Standard laptop |
| 1440 x 900 | Normal desktop/laptop |
| 1920 x 1080 | Large desktop |

1024x640 is a floor, not a design target: the application must remain
*operational* there (usable for primary workflows, not merely
non-crashing), while 1280x720 through 1920x1080 are where full layout
fidelity is expected with no compromises. This supersedes the original flat
"1024x768 minimum."

At constrained widths, in priority order:

1. collapse/hide navigation chrome first (shell drawer, then PM secondary
   nav) -- both to icon-only or fully hidden before any business content is
   touched;
2. preserve the business workspace (tables, forms, KPIs, charts) -- it
   degrades only after chrome has nothing left to give back;
3. move actions into toolbar overflow where appropriate rather than
   clipping or hiding them outright;
4. avoid fixed-width layouts anywhere in PM QML -- prefer
   `Layout.fillWidth`/anchors/flow layouts over literal pixel widths that
   can't shrink;
5. dialogs must fit the available window (clamp to available width/height,
   never exceed it, never assume a fixed dialog size fits);
6. vertical scrolling is acceptable when content genuinely exceeds
   available height -- this is a legitimate degradation, not a defect;
7. primary actions must always remain reachable, even if that means via
   overflow rather than a direct button.

If chrome is already fully collapsed and content still cannot fit at
1024x640, that is a page-level defect to fix on that page, not a reason to
lower the floor or to design that page around a fixed size.

### Content-width tiers

These tiers describe layout behavior as a function of *actual measured
content width* (after chrome deduction) -- they are not a substitute for
testing at the acceptance sizes above, since the same acceptance size can
land in different tiers depending on how much chrome is currently expanded.

| Content width | Target behavior |
|---:|---|
| below 760 | compact toolbars; no inspector; section rail becomes selector; nonessential table columns hidden through presets |
| 760-1179 | full list/table; no persistent inspector; two visible context actions plus More |
| 1180-1519 | optional 320-pixel inspector; fixed section rail; two-column dashboards |
| 1520+ | 360-pixel inspector and wider analytics grids; never stretch form text excessively |

### Acceptance criteria

At 1024x640 (chrome may be fully collapsed to satisfy these):

- no horizontal clipping of required actions;
- no dialog exceeds available width/height;
- table always retains identity and status columns;
- project and section context remain visible (a collapsed/icon-only
  representation counts as visible; content hidden entirely does not);
- all actions are reachable through overflow;
- scroll ownership is unambiguous, with no nested full-page flickables;
- vertical scrolling within a page is acceptable where content exceeds
  available height.

**Table scroll is two-axis, not a substitute for `hideBelow`.** The shared
`DataTable.qml` widget's underlying `TableView`s already expose both a
vertical `ScrollBar` (`policy: ScrollBar.AsNeeded`) and a dedicated
horizontal `ScrollBar` (`_hScrollBar`), so every table built on `DataTable`
-- Projects, Tasks, Portfolio, and every Platform catalog page -- can
already be scrolled in both directions natively, with no per-page wiring
required. This is a *complementary* mechanism, not an alternative to
`hideBelow`: `hideBelow` decides which columns are worth showing at all at
a given width (identity/status always stay), while horizontal scroll is
what lets a user reach a column that's still visible-but-off-screen (or a
table that simply has more columns than any width comfortably fits). Do
not treat "the table scrolls horizontally" as a reason to skip adding
`hideBelow` to a column set -- a table that never hides anything and relies
purely on horizontal scroll fails the acceptance criterion above ("table
always retains identity and status columns" implies those two stay
in-view without scrolling; everything else may require either hiding or
scrolling, and hiding is the better default for genuinely secondary data).

At 1280x720 and every larger acceptance size, additionally: the fixed
section rail, inspector, and two-column layouts described above are
available uncompromised (not merely reachable via overflow/collapse).

## 12. Theme, density, and accessibility

- Continue token-only colors; no PM-local color palette.
- Replace numeric dialog widths with width-tier tokens and available-width clamps.
- Use compact density for tables/toolbars and comfortable density for forms without hard-coded compensation.
- Every custom interactive item gets `Accessible.role`, `Accessible.name`, focus behavior, Enter/Space handling, and visible focus.
- Use shared tabs instead of `Rectangle` + `MouseArea` tab implementations.
- Icon-only controls require tooltips and accessible names.
- Announce loading completion, mutation success, and errors through the shared semantic message layer where supported.
- Focus returns to the invoking control after a popup/dialog closes and to the selected row after detail Back.
- Minimum hit target follows the shared density token; compact does not mean inaccessible.

## 13. State, refresh, and performance policy

- Controllers own query state; QML renders and emits intent.
- Project context owns only shared scope, not workspace filters.
- Presenters build immutable/disposable view models.
- Domain events invalidate the smallest affected reader instead of refreshing all PM workspaces.
- Detail sections load lazily and cache only within entity/version scope.
- Switching selection cancels or ignores stale detail responses.
- Dashboard and Portfolio readers should batch aggregate queries and expose timing metrics already used by the codebase.
- Avoid QML re-filter/rebuild loops for large models; update Python table models in bounded batches.
- No background thread/timer is introduced solely for Tasks or another page. Use the platform's common async/refresh contract if future I/O leaves the UI thread.

## 14. Phased implementation roadmap

### R0 - Audit

Objective: reconstruct current state and approve constraints.  
Gate: the three QML redesign documents are reviewed.  
Status: complete.

### R0.1 - Product and contract decisions

Objective: record approval of the six PM-local destinations, canonical module route, explicit active-project pinning, capability-based Timesheets default, removal of Rebalance, Finance hierarchy/boundary, deny-safe R1 scope, and limited R0.5 map.  
Excludes: production or visual changes.  
Gate: complete. The three redesign documents contain the reconciled decisions.

### R0.5 - Behavior-preserving repository preparation

Objective: execute only 18 dialog moves, four capability widget moves, eight precise private Python renames, the task presenter utility split, the characterized internal `TasksTimeEntriesSection` split, and guarded dead-QML verification.  
Dependencies: clean PM tests and QML load baseline.  
Excludes: QML-facing facade restructuring, visual redesign, canonical-route implementation, or any route behavior change.  
Gate: behavior and screenshots unchanged; all current routes/dialogs load; exactly two empty Python and up to 15 net empty `qmldir` baseline artifacts are removed; dead QML is removed only after its separate proof gate.
Status: complete on 2026-08-14. All 23 guarded candidates were proven dead and removed; the ten route IDs and all target product decisions remain unchanged. Automated route/dialog/offscreen, task-time, shared primitive, adapter/pagination/event, architecture, and performance gates show no attributable regression. At the R0.5 closure point, R1 had started and R1.2 was complete.

### R1 - Query integrity, truthful controls, and deny-safe capability presentation

Objective: remove no-ops, add explicit table sorting modes, implement server sort contracts, replace Collaboration/Timesheet partial queries, and replace fail-open capability presentation with deny-safe, capability-complete UI state.  
Affected: shared DataTable, Projects, Tasks, Scheduling, Resources, Register, Timesheets, Collaboration, Portfolio, Dashboard, Finance collection readers.  
Gate: no PM control implies unsupported behavior; query tests prove totals and stable ordering; permission lookup absence/failure never advertises an unauthorized action.
Status: complete on 2026-08-14. R1.2 sorting ownership, R1.3 server-sort infrastructure,
R1.4 Projects/Tasks/Scheduling/Resources/Register sorting, and R1.5 Timesheet
Review are closed. R1.6 is closed: Inbox and Mentions are authoritative pages;
Activity is explicitly bounded recent collaboration; Approvals reuse the Platform
owner without PM paging/search claims; Presence is a complete TTL-scoped current
set; duplicate Team Updates and all snapshot/placeholder paths are removed.
R1.7 is closed: Portfolio aggregate truth is independent of UI paging; Dashboard
complete and bounded datasets expose truthful controls; Finance Actuals and
Commitments use authoritative SQL pages/totals/sorting; financial calculation
remains Decimal-exact; and Rebalance remains absent. R1.7 performance evidence
records Dashboard at 89 SQL statements and Portfolio at 68 statements in the
single-project fixture. R1.8 is closed: the existing six PM capability facts
are wired to the authoritative session engine with canonical permission codes;
missing engine/session/principal/tenant/organization and evaluation failures
all map to false; QML and row-action fallbacks are deny-safe; and assignment
policy failures are blocking. Backend enforcement and entity lifecycle facts
remain authoritative. R1.11 is closed and R1 is complete; R2 has not started.

R1.7 does not implement any target visual architecture in this document. It
only establishes trustworthy query/control foundations for later Overview,
Portfolio, and Finance work. Accounting ownership remains unchanged: PM owns
managerial project-finance projections, never statutory ledger, payment,
invoice, tax, journal, or reconciliation truth.

R1.8 introduces no visual redesign or broad RBAC framework. Its structured
presentation state is limited to `unknown`, `unavailable`, `ready`, and `error`
on the existing PM capability controller. Permission booleans remain compatible,
but only a known allowed decision can expose `true`. Tenant/organization and
runtime-session refresh paths recompute the facts. Page-level generic failures
remain errors because PM does not yet expose a structured page-denial contract;
the UI does not infer denial from message text.

### R2 - PM navigation and project context

Objective: introduce the canonical Project Management module/workspace route, six PM-local destinations, compatibility-route translation, and the authoritative explicitly pinned PM project-context contract.  
Dependencies: tenant/org reset semantics and route/deep-link contract.  
Gate: context switches are explicit, authorized, persistent, reset correctly, and do not lose dirty forms; the ten old IDs resolve as compatibility deep links rather than unrelated drawer workspaces.
Status: complete. See section 20 for the R2.0 scaffolding-discovery and integration record.

### R3 - Overview and Portfolio

Objective: build the new analytics shell and replace Portfolio's fixed bottom panel with focused tabs/work surfaces.  
Excludes: unbacked rebalance.  
Gate: global/project totals are query-correct and performance stays within agreed budgets.

### R4 - Work

Objective: add the responsive catalog/inspector pattern to Projects and Tasks and the target Planning console.  
Dependencies: inspector and action-overflow primitives.  
Gate: list state survives full detail/back; 1024 and keyboard paths pass.

### R5 - Workload Management

Objective: update Resources and split Timesheets into My Time and Review Queue.  
Dependencies: review query filters and a dedicated current-user period projection.  
Gate: entry CRUD, submission, review, rejection, lock, and correction paths are fully backed and permission-aware.

### R6 - Finance

Objective: reorganize finance by intent and expose approved canonical commands in controlled increments.  
Sequence: overview/configuration -> budget/planning -> cost control -> billing evidence -> reports.  
Gate: command/audit/concurrency tests pass; no Accounting-owned truth is created in PM.

### R7 - Governance and Collaboration

Objective: apply responsive list/inspector patterns to Register and query-backed queue patterns to Collaboration.  
Dependencies: R1 collaboration readers.  
Gate: saved views store queries, all filters are real, approval actions handle conflicts.

### R8 - Accessibility, density, cleanup, and regression

Objective: complete keyboard semantics, focus, compact layouts, dark mode, density, remove migration compatibility, and perform final dead-code cleanup.  
Gate: the canonical route, remaining compatibility routes, QML engine, dialogs, controllers, architecture, PM workflows, and visual acceptance checks pass, including the revised responsive floor (section 11): operational at 1024x640 with chrome collapsed as needed, full layout fidelity at 1280x720+.

## 15. Non-goals and prohibited shortcuts

- No QML-only persistent active-project variable.
- No six unrelated global PM drawer entries unless a documented shell constraint makes the canonical module route impossible.
- No client-side search/filter/sort over DB pages or capped global snapshots.
- No new task board without authoritative ordering/query behavior.
- No fake Portfolio rebalance.
- No Collaboration settings popup without a settings contract.
- No Finance local ledger, invoice, receivable, payment, or tax truth.
- No direct PM import of Inventory, Procurement, Accounting, or other module packages.
- No simultaneous repository move and visual redesign.
- No permanent compatibility wrappers or legacy directories after migration.

## 16. Target acceptance summary

The target is complete when one canonical PM module route provides the six approved PM-local destinations, compatibility routes are retired after dependency migration, users move from portfolio to project to task without implicit context changes, every visible control is real, scalable lists use authoritative queries, permission presentation is deny-safe, Timesheets defaults by capability while supporting capture and review, Finance exposes approved PM-owned commands without crossing Accounting boundaries, and the workspace remains keyboard-accessible and operational at 1024x640 (chrome collapsed as needed) with full layout fidelity at 1280x720 and larger (see section 11).

## 17. R1.9 closure note

R1.9 is closed on 2026-08-14 without beginning the target visual redesign.
Unsupported Dashboard, Portfolio, Scheduling, Timesheet, and Register export
controls and their presentation-only adapters were retired. The Finance
Purchase Orders future placeholder was removed from the active rail. Portfolio
Compare now presents the existing authoritative evaluation/comparison models;
selected-project Evaluate controls that ignored their selection were removed.
Scheduling comparison remains selector-driven and no longer advertises a
refresh-only Compare action.

The removed export and integration surfaces remain product work for R3-R7 and
must return only with real query/export/integration contracts. Existing real
file/report exports remain. Ten compatibility routes and R1.8 deny-safe action
presentation remain intact. At the R1.9 closure point, R1.10 and R2 had not
started.

The user committed the R1.9 source and focused test during verification; Codex
did not issue a commit. The closure-document update remains separate.

## 18. R1.10 closure note

R1.10 is closed on 2026-08-14 without implementing any target visual
architecture. Existing controllers remain the UI query-state owners and typed
queries/readers remain the execution authority. Search, supported filters,
scope, and sort reset page 1; page navigation and refresh preserve the remaining
query state; accepted server page, page size, filter, and sort state is reflected
back to presentation.

Projects, Tasks, and Resources exports are all-matching-results operations that
batch through their current authorized query and preserve its filters and sort.
Finance Excel/PDF is an explicitly bounded report with complete canonical
control totals and a disclosed 500-row source-detail bound. Scheduling,
Register, Timesheet Review, Collaboration, Portfolio, and Dashboard expose no
export after R1.9. No generic current-page export or selected-row export exists.

Final-page normalization now covers the scalable PM readers and Finance pages,
including refresh after result-count reduction. One interaction dispatches one
normal refresh; the only conditional second read corrects a page proven invalid
by the authoritative total. Query execution is synchronous, so no stale-response
mechanism is warranted. Tenant, organization, principal, project, and entity
visibility enforcement remains in the same service/reader paths used by the
visible lists.

Focused R1.10 and affected architecture verification is green. No full PM suite
was run per user direction. This stage introduces no `PMWorkspace`, route,
context bar, navigation, inspector, My Time, Finance IA, or visual redesign.
At the R1.10 closure point, R1.11 and R2 had not started, and Codex did not
create a commit.

## 19. R1.11 and final R1 closure

R1.11 closes R1 on 2026-08-14 without implementing any target visual design.
R1.1-R1.10 were reconciled against source and prior evidence: none is incomplete.
Future desired filters, My Time, notification delivery, Finance expansion,
canonical navigation/context, inspectors, and all responsive visual work remain
documented R2-R8 product scope rather than partial R1 behavior.

The focused closure matrix proves DataTable client/server/none behavior and
non-PM compatibility; authoritative Projects, Tasks, Scheduling, Resources,
Register, Timesheet, Collaboration, Portfolio, Dashboard, and Finance query
semantics; deny-safe capability presentation; truthful actions/exports; tenant
and organization isolation; PM QML loading; and unchanged compatibility routes.
It records 358 passing invocations across staged batches and reruns. The full
repository suite was intentionally **NOT RUN** under the approved 30-minute test
constraint, and a separate full PM suite was replaced by the union of focused
R1 risk groups.

One R1-attributable architecture regression was found and corrected: the
Scheduling presentation sorter no longer imports a core read contract. Its
allowlist, invalid-key fallback, missing-date ordering, complete-collection sort,
and stable activity-ID tie-break are unchanged. The remaining stale Platform
admin-directory assertion is unrelated/pre-existing and remains outside PM.

Dashboard/Portfolio performance gates pass at the reference 89/68 SQL statement
observations. Collaboration purpose-query measurement gates also pass. Static
closure searches are clean, all ten existing PM route IDs load, and
`project_management.workspace` was not introduced. `QMLLINT - UNAVAILABLE` in
`pmenv`. Zero R1-attributable regression remains, R2 has not started, and Codex
did not commit.

**R1 - QUERY INTEGRITY & TRUTHFUL CONTROLS: COMPLETE.**

Correction (section 20): "R2 has not started" and "`project_management.workspace`
was not introduced" were accurate at this R1.11 closure point and are left
as-written above as the historical record. Uncommitted R2 scaffolding was
added in a later commit before this closure document was next revisited; see
section 20 for the corrected R2.0/R2 status.

## 20. R2.0 scaffolding discovery and R2 closure

Commit `04717f3a` ("update all") added `navigation.py`
(`PM_CANONICAL_ROUTE_ID`, the ten-workspace intent map,
`compatibility_route_intent()`) and two controllers,
`PMProjectContextController` and `PMWorkspaceNavigationController`, before
any of the R2 work recorded below began. At discovery that scaffolding was
committed but inert: not exported from `controllers/common/__init__.py`,
not constructed by `ProjectManagementWorkspaceCatalog`, not referenced by
any QML, and not covered by any test -- so `@QmlElement`'s import-time
registration meant neither controller was even live in the QML type system.
Classification: **R2.0 scaffolding -- pre-existing, complete as authored.
R2 integration -- implemented in this phase, reusing rather than
duplicating it.**

R2 is closed. Completed:

- `PMProjectContextController` and `PMWorkspaceNavigationController` are
  catalog-owned (`ProjectManagementWorkspaceCatalog.pmProjectContext` /
  `.pmNavigation`), exported from `controllers/common/__init__.py`, and
  proven live through the normal QML bootstrap path (not an incidental
  import).
- `PMProjectContextController` is wired to the real Projects desktop API.
  `ProjectManagementProjectsDesktopApi.get_project(project_id)` did not
  exist before this phase even though the scaffolding's `_read_project()`
  already assumed it did; it was added as a thin wrapper over the existing
  `ProjectService.get_project()` used elsewhere in the same file.
- A `ProjectContextPolicy` enum (`required`/`optional`/`not_applicable`)
  was added to `navigation.py`'s `PMWorkspaceIntent` -- destination
  metadata, not `PMProjectContextController` -- per the approved table in
  section 2.1's "Workload Management" group (renamed from "People & Time"
  during R2; see below) and section 9. `PMWorkspaceNavigationController`
  exposes the current destination's policy; the catalog composes it with
  `hasActiveProject` into one `projectContextRequirementSatisfied` boolean
  so QML never re-derives the REQUIRED/OPTIONAL/NOT_APPLICABLE logic
  itself.
- The canonical shell (`qml/workspace/ProjectManagementWorkspacePage.qml`)
  hosts all ten existing R1-correct capability pages unchanged, loaded
  dynamically by `Loader.source` URL rather than a static QML `import`:
  this codebase's architecture guardrails forbid parent-relative QML
  imports, and each capability's own `qmldir` `module` name does not match
  its physical folder path, so neither a relative import nor the declared
  dotted-module import resolves cross-folder. A dynamic `Loader.source`
  needs neither.
- The ten existing route ids resolve into that shell via
  `compatibility_route_intent()`/`applyRoute()` through small per-route
  bridge components under `qml/workspace/compatibility/` -- "compatibility
  route" is this document's own established term; there is no installed
  client base, so the bridges exist for internal deep-link continuity
  while callers/tests migrate, not an external back-compat contract.
- Explicit pinning (`selectProject()`), non-pinning navigation/browsing
  (`openProject()`, route selection), lazy per-destination loading (a
  destination's controller is constructed only once it is first both
  selected and context-satisfied, then stays mounted rather than being
  torn down and reconstructed on revisit -- see below), and
  tenant/organization/reauthentication context revalidation
  (`refreshProjects()` on the catalog's existing `refreshCapabilities()`/
  `refreshAllWorkspaces()` hooks) are implemented and characterized with
  tests at both the controller and QML level.
- The PM secondary nav reuses the shared `App.Widgets.GroupedNavigationRail`
  (the same component `PlatformNavigation.qml` uses) with
  `autoCollapseAtNarrowWidth: true` and `showRailToggle: true`, rather than
  a bespoke rail, so responsive collapse and manual collapse both come from
  an already-proven shared primitive.
- The "Workload Management" IA rename: the group formerly named "People &
  Time" (Resources, Timesheets) is "Workload Management" (internal
  destination id `workload`) because PM resources can include equipment,
  not only staff, making "People & Time" read as too HR-specific. Resources
  and Timesheets keep their own capability packages, controllers, and
  route ids unchanged.
- No per-destination visibility capability contract exists in
  `PMCapabilityController` (its six facts are fine-grained command
  permissions, not workspace-level read visibility), so R2 does not filter
  the six navigation groups by capability -- inventing that mapping now
  would fabricate a product decision with no backing contract. All ten
  destinations remain visible, matching pre-R2 behavior.
- A teardown/recreate hazard in the shared `SectionDetailPage` (a pending
  `Qt.callLater()` reparent firing after its context is destroyed) was
  discovered by the canonical shell's destination-switching and avoided by
  never tearing a visited destination back down, rather than by patching
  the shared widget as a side effect of R2.

Deliberately not done, matching the approved R2 scope: no visual redesign
of any of the ten capability pages and no `PMCapabilityController`
capability expansion.

1024x768 result: **FUNCTIONALLY VERIFIED / PIXEL-LEVEL VISUAL VERIFICATION
DEFERRED.** The shell's responsive behavior at that width -- the PM
secondary nav auto-collapsing via the shared `GroupedNavigationRail`'s
`autoCollapseAtNarrowWidth`, and the project-context bar's row becoming
horizontally scrollable rather than clipping -- was verified structurally
(the bindings and thresholds are in place and exercised by tests). Rendered
pixel/screenshot verification was not performed because this environment
has no screenshot/render-capture tooling, not because the behavior is
unverified or broken. This is a scoped deferral, not an R2 regression --
R2's own gate did not require pixel evidence, matching the same standard
R0.5's closure already used ("no screenshot pixel-comparison gate was
available, so closure does not claim pixel-diff evidence").

R3-R8 visual/product work, My Time, desired unsupported filters,
notification delivery, and Finance expansion remain deferred, unchanged
from the R1.11 closure above.

## 21. R3.1 characterization and R3.3 Portfolio scalable query architecture

R3.1 characterized current Overview/Dashboard and Portfolio behavior before
any redesign work started. Findings, classified per the mandated framework
(UX REDESIGN DEBT / PERFORMANCE DEFECT / R1 CORRECTNESS GAP / FUTURE
FEATURE):

- **PERFORMANCE DEFECT, fixed in R3.7**:
  `DashboardPortfolioMixin.get_portfolio_data()` looped over every accessible
  project and, per project, called `get_project_kpis()` (which re-ran CPM
  scheduling internally), `get_resource_load_summary()`, and
  `_build_upcoming_tasks()` -- the last of which re-fetched the *entire*
  resource table and issued one `list_assignments_for_task()` call per task
  (an N+1 inside the N+1). Fixed by replicating the batching
  `DashboardService.get_dashboard_data()` already used for a single
  project: fetch each project's tasks/CPM schedule/assignments once, fetch
  the resource table once for the whole portfolio, and pass all of it into
  `get_project_kpis(schedule=...)` / `_build_upcoming_tasks(tasks=...,
  assignments_by_task=..., resources_by_id=...)` via their existing
  optional overrides. No new abstractions; no change to either helper's
  default (no-override) behavior, so every other call site is unaffected.
  Regression-proven by asserting fixed call counts independent of project
  count (`test_dashboard_portfolio_workspace_performance_measurement.py`).
- **Not an R1 correctness gap**: Portfolio's `list_templates()`,
  `list_intake_items()`, `list_scenarios()`, `list_heatmap()`, and
  `list_dependencies()` were traced into their underlying
  `PortfolioService` query mixins and confirmed to return the full
  accessible-scoped result set with no hidden cap -- the totals shown are
  the true totals, so today's client-side pagination over them is a
  scalability characteristic, not a truthfulness violation (matches R1.7's
  "Portfolio aggregate truth is independent of UI paging").
- **6 of 7 candidate-dead Portfolio section files confirmed dead** with
  fresh evidence (zero references anywhere in `src/ui_qml`, not
  instantiated by the live `PortfolioWorkspacePage.qml` or
  `PortfolioBottomPanel.qml`) and deleted in R3.2:
  `PortfolioIntakeSection.qml`, `PortfolioScenariosSection.qml`,
  `PortfolioDependenciesSection.qml`, `PortfolioTemplatesSection.qml`,
  `PortfolioToolbarSection.qml`, `PortfolioExecutiveSection.qml`.
  `PortfolioSummaryCard.qml` was found to still be live (used by
  `PortfolioGovernanceToolbar.qml`) and was kept -- a correction to the
  earlier recon's claim.

### Scalability gate inserted before the Portfolio visual redesign

Before building the new Portfolio tabs/workspaces (R3.4+), the product
requirement that Portfolio collections may grow to ~10,000+ rows required
settling the query architecture first, so the new UI is built on the real
contract from day one rather than retrofitted later.

**Classification of the five Portfolio collections** (by product/domain
semantics, not current row count):

| Collection | Classification | Product invariant |
|---|---|---|
| Scoring templates | BOUNDED_COMPLETE | A scoring-rubric configuration catalog an organization defines rarely (governance artifact, not a per-event record) -- the same character as rate cards elsewhere in this codebase. The complete authorized set is intentionally loaded. |
| Scenarios | BOUNDED_COMPLETE | Manually-authored what-if planning constructs created deliberately per planning cycle by PMO staff, not generated per business transaction. The complete authorized set is intentionally loaded. |
| Intake | SCALABLE | Every candidate/proposed project idea across the organization's lifetime, including rejected/historical ones -- no natural ceiling. |
| Heatmap | SCALABLE | One row per accessible project -- directly 1:1 with the project count the product must support at 10,000+. |
| Dependencies | SCALABLE | Cross-project dependency edges; grows at least as fast as project count. |

**Authoritative server-side pagination** was added for the three SCALABLE
collections, following this codebase's existing `ReadSort` /
`stable_order_by` / offset-`PaginatedResult` pattern (the same one
`TaskService.query_workspace_page()` and the Projects/Register catalog
readers already use):

- `PortfolioService.list_intake_items_page(...)` --
  `SqlAlchemyPortfolioIntakeRepository.list_page()` does the SQL
  scope/search/status filter, `ORDER BY` on an allowlisted column with an
  `id` tie-breaker, and `LIMIT`/`OFFSET`.
- `PortfolioService.list_portfolio_heatmap_page(...)` -- project
  selection (scope/search/status/sort/page) happens in SQL via the shared
  `ProjectCatalogReader` (the same reader the Projects workspace already
  uses) *before* any per-project pressure computation runs; heatmap facts
  (`_heatmap_reader.read_facts()`) are then fetched, and pressure computed,
  only for the page's projects -- never the full accessible scope.
- `PortfolioService.list_project_dependencies_page(...)` --
  `SqlAlchemyPortfolioProjectDependencyRepository.list_page()` paginates
  and searches dependency edges in SQL (joined to predecessor/successor
  project name for search and display, so no second unbounded project
  fetch is needed); pressure is then computed only for the small set of
  projects actually referenced on that page.

**Computed pressure is never a paginated sort key.** `pressure_score` /
`pressure_label` are derived per project from CPM scheduling, cost
variance, and resource utilization -- there is no way to `ORDER BY` them
in SQL without computing them for every accessible project first, which
would defeat the purpose of paginating at all. The rule applied
throughout: *authoritative paginated browse != bounded analytical
ranking*.

- On the paginated Heatmap/Dependencies browse, only genuinely
  SQL-authoritative columns (project name, status, dependency type,
  created/updated timestamps) are sortable. Requesting an unsupported key
  (e.g. `pressureScore`) falls back to the default via `ReadSort.normalize`'s
  existing allowlist behavior -- it does not error and does not silently
  re-sort the returned page in Python.
- A separate, explicitly bounded analytical projection,
  `PortfolioService.list_top_at_risk_projects()` (`collection_semantics =
  bounded/top_n`), ranks pressure across the *complete* authorized project
  scope and truncates to `TOP_AT_RISK_PROJECTS_LIMIT` (8 -- matching this
  codebase's existing watchlist convention used by the Dashboard's own
  `critical_watchlist`/`milestone_health` top_n tables, not an invented
  number). It is never derived from a paginated page, and changing the
  paginated browse's `page_size` cannot change its result
  (test-proven in `test_pm_r3_portfolio_scalable_queries.py`).
- No Dependencies Top-N was added -- product semantics do not currently
  call for a global dependency-pressure ranking distinct from the Heatmap
  one, and R3.3's instruction was explicit not to add one merely for
  symmetry.
- **No materialized pressure infrastructure was added in R3**: no
  `pressure_score` column, cache, scheduled recomputation, materialized
  view, or event-driven invalidation. If pressure becomes a first-class
  sortable/filterable/alertable/reportable metric, persisting/caching it is
  the future option to revisit then -- not before.

Desktop-API/presenter/controller wiring for these three query methods is
deferred to R3.4 (the Portfolio IA tabs phase) rather than retrofitted into
the current `PortfolioBottomPanel.qml`/`HeatmapTableController` (which
already does client-side pagination over a fully materialized list and
will be replaced, not extended, by R3.4) -- wiring the old UI to the new
contract now would itself be the "temporary client-pagination logic that
will be deleted a few stages later" the gate explicitly warned against.

R3.3 exit gate: all five collections classified; every SCALABLE collection
uses server pagination; no scalable page downloads the full collection for
client pagination; filtering/sorting happen before pagination; total_count
is authoritative; stable `id` tie-breakers are used throughout; aggregates
(Dashboard/Portfolio KPIs) remain computed from their own existing,
untouched authoritative paths, independent of any page size; tenant/org/
project scope is enforced identically to every other Portfolio query; a
focused ~10,000-row scale test exists (against Intake, the simplest
single-table SCALABLE collection to seed at scale -- it exercises the same
`stable_order_by`/`LIMIT`/`OFFSET` mechanism Heatmap's project-selection
layer reuses via the shared `ProjectCatalogReader`); the full
Portfolio+Dashboard regression batch (105 tests) plus the 12 new R3.3
tests pass. **R3.3 -- PORTFOLIO SCALABLE COLLECTION QUERIES: COMPLETE.**

## 22. R3.5 closure: Portfolio six-area IA tabs

The fixed 268px `PortfolioBottomPanel.qml` (five inline tabs: Funding/
Risks/Capacity/Governance/Activity) and the always-visible
`PortfolioGovernanceToolbar.qml` scenario toolbar are retired. Portfolio's
list page is now six equal-weight tabs (`qml/workspaces/portfolio/tabs/`,
driven by `AppWidgets.DetailTabBar` + `StackLayout`, backed by
`ProjectManagementPortfolioWorkspaceController.activeTab`/`setActiveTab()`):

- **Executive** -- KPI strip, the bounded `list_top_at_risk_projects()`
  ranking, and the Recent Actions feed (folded in per product decision --
  no 7th/8th tab).
- **Heatmap** -- the server-paginated browse
  (`list_portfolio_heatmap_page()`); row-activate still opens the existing
  per-project `PortfolioDetailPanel` drill-down unchanged.
- **Intake** -- server-paginated browse (`list_intake_items_page()`) with
  the existing status filter and approve/review/reject actions.
- **Scenarios** -- the relocated `PortfolioGovernanceToolbar` (scenario
  select/evaluate/compare, no longer persistent chrome above all tabs) plus
  a Scenario Library list and Scoring Templates management (folded in per
  product decision).
- **Capacity** -- unchanged capacity pool report.
- **Dependencies** -- server-paginated browse
  (`list_project_dependencies_page()`) with remove-dependency.

Deliberately not built in this phase (pre-existing gap, not introduced
here): there was no QML dialog for creating templates/scenarios/
dependencies/intake items before R3.4 either -- `createTemplate()`/
`createScenario()`/`createDependency()`/`createIntakeItem()` exist on the
controller but have no dialog UI wired to them. Recorded as a deferred gap
rather than built as a rushed addition to a tab-restructuring phase.

Verified through real QML loads (not source-contract checks alone): the
canonical shell's Portfolio compatibility route loads with the six-tab IA,
every tab is reachable via `setActiveTab()` without error, and each
paginated tab's page state is live after load
(`test_pm_r3_4_portfolio_ia_tabs.py`). Targeted regression: 90 Portfolio
tests green.

**Unplanned same-session fix**: a direct product report that the R2
project-context bar looked unprofessional on Portfolio led to the bar
being hidden entirely for `NOT_APPLICABLE`-policy destinations (Portfolio,
Projects) rather than always rendered regardless of relevance -- it still
renders for `OPTIONAL`/`REQUIRED` destinations (Dashboard, Scheduling,
Financials, etc.), so Scheduling/Financials' explicit-pinning requirement
is preserved. A visual restyle of the bar itself (chip-style project
label, hiding the empty results dropdown until a search returns matches)
was tried and then reverted back to the original styling per direct
instruction -- only the visibility gating is kept. No pinning/search/clear
behavior changed. Verified via a real QML load asserting the bar's
`visible` property across Dashboard (shown), Portfolio (hidden), and
Scheduling (shown).

**R3.4 -- PORTFOLIO IA TABS: COMPLETE.**

## 23. R3.6 closure: Portfolio interaction redesign

Compare already used R1's authoritative `compare_scenarios()`/
`evaluate_scenario()` unchanged -- no gap there. Browsing/selection safety
(opening the Heatmap drill-down, selecting a row, switching tabs) was
verified to never call `selectProject()` on its own, preserving R2.10's
explicit-pinning-only rule.

The one real interaction gap: there was no way to pin a project from
Portfolio into the shared R2 project context, so a user who found a
project via Portfolio's Heatmap had no path into Scheduling/Financials
(both `REQUIRED` project context) with that project already active. Added
an explicit **Set Active Project** / **Clear Active Project** action to
`PortfolioDetailPanel.qml`'s overview section (visible only when viewing a
project's drill-down, calling straight through to the same
`PMProjectContextController.selectProject()`/`clearProject()` the shared
context bar uses), plus an "Active project" chip when the viewed project
is already the pinned one. This is a deliberate, explicit action taken
after viewing a project's detail -- never automatic on row-select/open.

**R3.5 -- PORTFOLIO INTERACTION REDESIGN: COMPLETE.**

## 24. R3.3B -- Overview Scalable Queries

Inserted, matching Portfolio's own R3.3 gate, before the Overview visual
redesign (still not started -- see section 6.1's wireframe). A
characterization pass (real-file evidence, no code changes) found today's
seven Dashboard operational collections are fetched once per load/refresh
into `_raw_operational_tables`, then every search keystroke, page turn, and
tab switch re-slices that materialized list in pure Python
(`dashboard_operational_table_mixin.py`) with no sort at all
(`DashboardOperationalPanel.qml` uses `sortingMode: "none"`). Totals are not
lied about (this is a scalability/query-ownership gap, not a false-results
defect), but it fails the server-side standard section 8.1 requires, and
three of the seven collections materialize an **unbounded, org-wide** list
every refresh in portfolio (all-projects) mode.

**Classification of the seven operational collections**, by domain/product
semantics rather than current implementation or row count:

| Collection | Scope | Classification | Reason |
|---|---|---|---|
| Delayed Tasks | Project + portfolio | **SCALABLE** | Overdue-task volume scales with task count, not inherently bounded -- a program with poor schedule health could have hundreds/thousands of late tasks. |
| High Risks | Project only | **COMPLETE_SMALL** | Bounded to one project's own risk register (small by nature); no portfolio-wide equivalent exists today -- Register capability owns full cross-project risk browsing. |
| Projects at Risk | Portfolio | **BOUNDED_TOP_N** | An attention/triage list for a landing page, not "browse all projects" (Projects capability owns that). Requires full-scope computation for a correct ranking, but the *output* is explicitly bounded. |
| Budget Variances | Project | **COMPLETE_SMALL** | Bounded to one project's own cost-source categories (a small, fixed set). |
| Budget Variances | Portfolio | **BOUNDED_TOP_N** | Same reasoning as Projects at Risk -- an attention list, not a Financials-style full browse. |
| Resource Overloads | Project | **COMPLETE_SMALL** | Bounded to one project's assigned resources. |
| Resource Overloads | Portfolio | **BOUNDED_TOP_N** | Attention list of the most-overloaded resources, not a full resource browse (Resources capability owns that). |
| Pending Approvals | Both | **EXTERNAL_AUTHORITATIVE / BOUNDED_RECENT** | Platform-owned (`ApprovalService.list_pending(project_id=, limit=)` is already limit-bounded); PM must never build a duplicate approval reader. |
| Milestones | Both | **BOUNDED_TOP_N** | An upcoming-checkpoint watchlist; milestones are computed per-project via CPM and are inherently sparse (a handful per project), not a bulk-data concept. |

Only **Delayed Tasks** is genuinely SCALABLE. The other six were already
either correctly bounded/labeled (High Risks, project-scope Budget
Variances/Resource Overloads, Pending Approvals, Milestones) or fixed in
this phase (Projects at Risk, portfolio-scope Budget Variances/Resource
Overloads -- capped to a top-20 attention list with
`collection_semantics="top_n"`, `supports_search/pagination=False`, and an
honest "(Top 20)" title, in `operational_table_builder.py`). No SQL/query
changes were needed for those six -- capping a Python list is sufficient
once a collection is correctly classified as bounded-by-product-definition
rather than complete.

**Delayed Tasks fix -- reuse, not duplicate.** Tasks' own workspace query
already has an authoritative `schedule="overdue"` SQL filter
(`TaskWorkspaceReader.read_page()`, used by the Tasks capability's own
page) and already treats `project_id=None` as "all accessible projects."
`ProjectManagementDashboardDesktopApi.list_delayed_tasks_page()` calls
straight through to `TaskService.query_workspace_page(schedule="overdue",
...)` -- no new reader, no new SQL, no duplicate PM-Dashboard-owned query
authority. `ProjectDashboardOperationalTableDescriptor` gained optional
`page`/`page_size`/`total_count`/`sort_key`/`sort_direction`/`search_text`
fields (defaulted so the other six tables are unaffected).

**Derived-metric rule preserved**: none of the top_n tables' derived
values (risk score, cost variance, utilization) are exposed as sortable
columns on a paginated browse -- they don't need to be, since none of the
six became a paginated browse; they are bounded lists, not paginated ones.

**KPI/N+1 independence verified**: `DashboardPortfolioMixin.get_portfolio_data()`
(the object R3.7 already fixed) was not touched by this phase, and a test
directly proves calling `list_delayed_tasks_page()` at any page/page_size
does not change `get_portfolio_data()`'s KPI or project-total output.

**No materialized/persisted metrics were added.** Risk score, cost
variance, and utilization remain computed in Python from existing
authoritative reads, exactly as before.

Verified: a focused ~10,000-row scale test for Delayed Tasks (the one
SCALABLE collection) proves page 400 costs the same query count as page 1
and only the requested page is ever materialized; page reachability,
search-before-pagination, non-overdue exclusion, and all-projects scope
are also test-proven (`test_pm_r3_overview_scalable_queries.py`, 6 tests).
Targeted Dashboard/Portfolio regression (29 tests) and the operational
table builder's existing tests (16 tests) remain green.

**R3 -- OVERVIEW SCALABLE QUERIES: COMPLETE.**

**Delayed Tasks wired live into the existing "Delays" tab** (the one
concrete piece of UI work this phase justified doing immediately, since
the query capability now exists and end-to-end proof requires exercising
it through the real controller, not just the desktop API):
`DashboardOperationalTableMixin` now routes search/page/pageSize/tab-select
for `delayed_tasks` to `ProjectDashboardWorkspacePresenter.
list_delayed_tasks_page()` (a live backend call) instead of the shared
"re-slice an already-fetched list" path every other operational tab still
correctly uses. The tab still appears inside today's `DashboardOperational
Panel.qml`/`operationalTable*` QML properties unchanged -- no QML files
were touched, only the controller/presenter/desktop-API layers -- so this
is wiring, not the visual redesign itself. One known, accepted, minor gap:
the tab bar's row-count badge still reflects the eager snapshot's old
curated-watchlist count until the tab is actually opened (cosmetic only;
the tab's own total once viewed is always the live, authoritative count).
Verified through a real QML load of the Dashboard route exercising
search/page/pageSize on the live controller
(`test_pm_r3_overview_delayed_tasks_live_tab.py`).

**Context bar responsive fix + "Dashboard" -> "Overview" rename** (both
concrete, evidence-backed, low-risk): `DashboardSelectionBar.qml` now
collapses Baseline/Period/View into an overflow popup below
`Theme.AppTheme.compactContentBreakpoint` (1024, the existing shared
token), keeping only the single Project selector and Refresh always
visible -- matching section 3.3's compact-width contract. The overflow
combos reuse the same `syncingSelection`-guarded sync pattern the inline
combos already use (a real architecture guardrail test caught the first,
naive `currentIndex:` binding attempt and was the right call). The
user-visible "Dashboard" label is now "Overview" everywhere it was
authoritative (`workspaces.py`'s `ProjectManagementWorkspaceDescriptor`,
the PM nav item label, and every UI-layer fallback default) -- `route_id`/
class/file names intentionally remain `dashboard`/`Dashboard*` internally,
matching how this rename was scoped (user-visible label only, not an
internal identifier migration). Also fixed, while in this file: the
"Finance" nav item referenced an unregistered `icon: "finance"` --
corrected to the already-registered `"financials"` icon key.

The remaining Overview visual redesign (responsive KPI strip, delivery
trend + Attention Required pairing reusing already-real bounded data
instead of today's two-charts-side-by-side layout, replacing the other
operational tabs' still-curated content only if a real classification
calls for it, and a freshness indicator only if a real timestamp contract
is added) has not started.

**Update:** the KPI strip (shared `App.Widgets.KpiStrip`, used well beyond
Overview) and the delivery-trend/Attention-Required pairing were completed
in a later pass -- see section 26. The freshness indicator remains
deferred; no real timestamp contract exists yet.

## 25. R3.7 closure: Responsive Overview + Portfolio

Audited both surfaces against section 11's content-width tiers and
priority-collapse order (real-file evidence via a dedicated read-only
sweep, not assumed). Overview already had substantial width-keyed logic
(`DashboardSelectionBar`/`DashboardChartsSection`/etc.); Portfolio had
**none** -- a grep for any width-based breakpoint anywhere under
`qml/workspaces/portfolio/` returned zero hits before this pass.

Fixed, in priority order:

- **`PortfolioGovernanceToolbar.qml`** (Executive tab): the Base/vs
  comparison combos (320px of unyielding fixed width) collapse into a
  "Compare setup" overflow popup below `compactContentBreakpoint`, keeping
  Scenario + the primary Compare action always visible and reachable --
  this was the one gap classified as `blocks-1024x640-floor` (no headroom
  left before the primary action would clip).
- **`DetailTabBar.qml`** (shared; Portfolio's 6-tab bar and any other tab
  strip using it): wrapped in a `Flickable` so tabs scroll horizontally
  instead of silently overflowing past the container below the width they
  need -- there's no narrower "selector" fallback for a fixed tab count, so
  scroll is the correct degradation per rule 6.
- **`AnchoredPopup.qml`** (shared, 24+ consumers app-wide): `reposition()`
  already clamped X/Y so a popup stays on-screen, but never clamped the
  popup's own width/height -- a popup wider than the viewport (e.g. a fixed
  `width: 280` filter popup in a narrow window) still overflowed regardless
  of position. Added `clampSize()`, called alongside `reposition()`, that
  shrinks width/height down to what actually fits, once -- a pure
  correction, not a loop. Fixes rule 5 for every consumer at once.
- **Portfolio `DataTable` columns** (`PortfolioWorkspaceState.qml`):
  `DataTable.qml` already supports a per-column `hideBelow` (pixel) key
  (R7.4) but Portfolio's own column definitions never set it. Added
  `hideBelow: 760` to every non-identity, non-status column across
  heatmap/funding/risk tables, matching the acceptance criteria that a
  table must always retain its identity and status columns below 760.
- **`DashboardOverviewSections.qml`**: the "Recent Activity" inspector
  panel split at an unrelated `width >= 1360` threshold and used a fixed
  360px regardless. Realigned to section 11's actual tiers: two-column
  split from 1180+, 320px panel through 1519, 360px at 1520+.

**Also fixed, discovered while diagnosing a live user report during this
pass (not itself a responsive-design item, but directly blocked
verification of the above):** Overview could get stuck permanently
pre-load -- blank KPI strip, blank Scope/Baseline/Period/View selectors,
the raw pre-load placeholder subtitle, no error banner, and zero
`_refresh_dashboard()` log lines ever, confirmed against the real app's own
log file across two separate live launches. Root cause: Overview is the
default landing tab inside the PM canonical shell, so its capability
`Loader` activates earlier than any other capability's -- often before the
shell has finished assigning `pmCatalog` onto the outer shell page. The
shell's `Loader.onLoaded` handler did a plain `item.pmCatalog =
root.pmCatalog` snapshot assignment, which captures whatever `root.
pmCatalog` happens to be at that instant and never updates again; if that
instant was before `pmCatalog` landed, the Dashboard page's own `pmCatalog`
stayed null forever, and its `ensureLoaded()` never found a non-null
`workspaceController`. Fixed by replacing the snapshot with a live `Qt.
binding()` in `ProjectManagementWorkspacePage.qml`'s Loader, plus a
defensive `Qt.callLater(root.ensureLoaded)` retry in
`DashboardWorkspacePage.qml` itself. Regression test
`test_pm_workspace_dashboard_late_catalog_binding.py` reproduces the exact
race (loads the shell page with `pmCatalog` deliberately unset, then
assigns it only after the page completes) and fails without the fix,
passes with it.

Verified via the full targeted Portfolio/Dashboard/Overview PM test batch
(127 tests) plus the QML architecture guardrails -- all green. One
pre-existing, unrelated failure
(`test_platform_control_workspace_refreshes_on_control_events`) was
confirmed via `git stash` to fail identically with none of this phase's
changes applied -- not touched by this work.

**R3.6 -- RESPONSIVE OVERVIEW + PORTFOLIO: COMPLETE.**

## 26. R3.4 closure: Overview visual redesign

Closes the two substantive items left open at the end of section 24 (the
freshness indicator stays deferred -- no real timestamp contract exists).

**Delivery-trend + Attention Required pairing:** replaced the second chart
in both the bar-mode and line-mode chart layouts (previously a "Cost
Pressure"/"Cost Trend" `DashboardChartCard`) with a new
`DashboardAttentionPanel.qml`, fed by the top 2 rows each from the
already-real, already-bounded `delayed_tasks`/`high_risks`/
`pending_approvals` operational tables -- no new backend query, no
fabricated content. `DashboardOperationalTableMixin._build_attention_items()`
normalizes each table's differently-shaped rows into one common
`{category, title, subtitle, statusLabel, routeId, state}` shape via a
small per-category field-mapping table, exposed as the controller's new
`attentionItems` property.

**KPI strip responsive wrap -- attempted, reverted.** `App.Widgets.KpiStrip`
is shared well beyond Overview (30+ consumers across PM, Maintenance,
Inventory, and Platform). Its `RowLayout` divides available width equally
across all metric cells with no floor, so a strip with many metrics can
squeeze into illegible cells at the compact end of the acceptance range --
that gap is real and still open. A first attempt wrapped the row in a
`Flickable` with a per-cell minimum width, falling back to horizontal
scroll below that threshold instead of continuing to shrink. All automated
tests passed (no test exercises this widget's actual pixel rendering), but
real usage surfaced a live rendering regression on at least two pages
(Projects, Resources): a single-metric strip rendered as squashed,
overlapping text instead of the normal centered value/label. The exact
mechanism wasn't conclusively isolated in this environment (an offscreen
QQuickView render didn't reproduce the app's real font/theme setup closely
enough to confirm it directly), so rather than keep guessing against a
live regression, the change was reverted to the known-good pre-Flickable
version (git commit `ce275fb2`, confirmed via history to predate this
attempt). **Do not reintroduce this exact Flickable-wrap approach without
first getting a faithful visual reproduction** (a real windowed capture,
not an offscreen grab) to verify the fix before considering it done --
passing structural tests alone did not catch this. The underlying
illegible-cells-at-narrow-width gap remains open for a future, more
carefully verified attempt.

Verified via 3 new attention-panel tests (incl. a real QML-engine load) and
the full targeted Dashboard/Portfolio batch plus architecture guardrails
(all still green after the revert).

**Concise operational-tab labels**: the design doc's own R3.4 example
("Use concise labels such as: Delays / Risks / Cost / Workload / Approvals
/ Milestones") had not actually been applied -- the tab strip was reusing
each table's full descriptive `title` verbatim (`"Recent Pending Approvals
(Up to 120)"`, `"Milestone Watchlist (Next 8)"` as literal tab-button
text). Fixed with a small `id -> concise label` lookup in
`build_operational_tabs()`, leaving each table's own descriptive `title`
untouched for the panel header once a tab is open -- the tab button and
the panel header are different UI elements with different jobs, so they
now carry different text instead of the same overlong string.

**OVERVIEW VISUAL REDESIGN: COMPLETE** (freshness indicator explicitly
excluded, pending a real timestamp contract).

## 27. R3.8 verification and R3.9 closure

**R3.8 -- performance/scalability verification.** Re-checked every R3.8
bullet against what R3.4-R3.7 actually added:

- Dashboard N+1 fix (R3.3's `DashboardPortfolioMixin.get_portfolio_data()`
  batching): untouched by any R3.4-R3.7 change; its regression test
  (`test_dashboard_portfolio_workspace_performance_measurement.py`) still
  passes with the same bounded call-count assertions.
- Portfolio/Overview scalable collections: no new query paths were added
  by the visual/interaction/responsive work -- R3.4-R3.7 only changed QML
  layout, controller-side tab labeling, and popup/column presentation, not
  any reader/query code.
- **New in R3.4 -- the Attention Required panel and KPI strip**: both are
  pure transformations of data the controller already fetched.
  `_build_attention_items()` reads only `self._raw_operational_tables` (a
  plain list of already-serialized dicts) -- no repository, service, or
  presenter call anywhere in its body. `KpiStrip.qml`'s responsive wrap is
  a pure QML layout change with no data-layer involvement at all. Neither
  introduces a new query, let alone an N+1.
- KPI/N+1 independence (R3.3B's own gate) re-confirmed: nothing in
  R3.4-R3.7 touches `list_delayed_tasks_page()` or the KPI/health-card
  computation path.

No R3.8 gap found. **R3.8 -- PERFORMANCE/SCALABILITY VERIFICATION:
COMPLETE.**

**R3.9 -- targeted regression + closure.** Targeted batches run across
this work (never the ~30-minute full suite): the full Dashboard/Portfolio/
Overview PM test directory (127+ tests), the QML architecture guardrails,
and a stash-verified check that one unrelated pre-existing failure
(`test_platform_control_workspace_refreshes_on_control_events`) is not
attributable to any R3 change. All three modernization docs
(`project_management_qml_target_ui_ux_design.md`,
`project_management_qml_existing_state_audit.md`,
`project_management_ui_repository_restructure_plan.md`) are now updated
and in sync -- the latter two had been left saying "R3.4-R3.8 remain not
started" since R3.3 closed, which was stale.

**R3.9 -- TARGETED REGRESSION + CLOSURE: COMPLETE.**

**R3 -- OVERVIEW + PORTFOLIO: COMPLETE.**

####################################################################
# R4 -- WORK
####################################################################

## 28. R4.1 characterization: Projects, Tasks, Planning

Three parallel read-only recon passes (no code changes), same discipline
as R3.1: real call chains traced end to end, every control checked for
truthfulness, every finding classified as UX REDESIGN DEBT / PERFORMANCE
DEFECT / R1 CORRECTNESS GAP / FUTURE FEATURE.

### Projects

Call chain (`ProjectsWorkspacePage.qml` -> `projects_workspace_controller.py`
-> `ProjectProjectsWorkspacePresenter` -> `list_project_page` ->
`query_catalog_page` -> `SqlAlchemyProjectCatalogReader`) is fully
authoritative R1: server search/status-filter/sort/page/export, no gap.
Findings:

- **No inspector step exists** -- only flat catalog table and a full-screen
  detail page (`onRowActivated` jumps straight from row to full detail).
  This is the R4.2 target gap itself (catalog -> inspector -> full detail),
  not a defect in what exists today.
- **No "Set Active Project" action anywhere in Projects** -- confirmed via
  grep, `PMProjectContextController.selectProject()` is never called from
  this workspace. Opening correctly does not implicitly pin (matches the
  explicit-pinning rule), but the explicit affordance the R4.2 target
  requires simply doesn't exist yet.
- Filter surface is thin: only a Status combobox, despite `siteOptions`
  already being loaded into the controller unused (**FUTURE FEATURE**).
- `ProjectsColumnConfig.js` has no `hideBelow` on any of its 9 columns, and
  `TableToolbar` (6 actions: create/filter/customize/refresh/import/export)
  has no overflow -- **UX REDESIGN DEBT**, same category R3.7 found in
  Portfolio.
- Dialogs (`ProjectEditorDialog` 560px, `ProjectStatusDialog` 420px,
  `ProjectsImportDialog` 680px) are fixed-width with no clamp -- traced to
  the shared `EntityDialog`/`CenteredDialog` base, which only clamps
  height, never width. **Systemic, not Projects-specific.**
- All workflow actions (create/edit/status/delete, bulk delete/status,
  CSV/XLSX import, export, resource assign) are real, no dead controls.

### Tasks

Call chain uses the **full breadth** of `TaskService.query_workspace_page`
(search/status/priority/schedule/sort/page all genuinely wired) -- same
authoritative method Dashboard's Delayed Tasks tab already reuses. No
query-truthfulness gap found. Findings:

- **WBS data flows through but is never rendered as a tree**: `wbsCode`,
  `parentTaskId`, `hierarchyDepth`, `isSummary`, `childCount` all reach the
  presenter, and a move/reparent dialog exists, but the main table has no
  expand/collapse/indentation -- hierarchy indent only appears as literal
  spaces in one dialog's combo text. **UX REDESIGN DEBT** -- no real WBS
  outline view exists despite the data being there.
- Assignments, dependencies, progress, time/effort, collaboration,
  lifecycle -- all present and substantive via a real lazy-loaded
  multi-section detail inspector (not a flat CRUD table).
- "Select all" only selects the current page, not all filter-matching rows
  across pages -- a labeling clarity issue, not a defect.
- 9 dialogs, all fixed-pixel widths, no responsive clamp (same systemic
  `EntityDialog` gap as Projects). `TasksColumnConfig.js` has no
  `hideBelow` on any column (**UX REDESIGN DEBT**).
- Bulk selection + undo/redo (25-deep stack) confirmed still intact, not
  regressed. One latent risk: the bulk-property-change handler only
  branches on `propertyId === "status"` -- any other bulk property would
  silently no-op if ever wired up (worth checking in R4.3, not urgent now).

### Planning (current "Scheduling")

Nav already labels this "Planning" while the internal route/class names
stay `scheduling` -- matches the plan's "don't mechanically rename
internal packages" instruction. Call chain fetches the complete calculated
project schedule every refresh (VCC, justified -- CPM/baseline/calendar
math needs the whole graph), filters, **then sorts, then pages** -- the
previously-flagged PCC ("sort after page-slice") is confirmed **already
fixed**; only the VCC performance characteristic remains, and only matters
at large scale (full recalculation on every search keystroke). Findings:

- CPM (critical path/float), baseline compare/variance, and calendar-aware
  dates are all present and reasonably complete.
- **Constraints are an R1 correctness gap candidate**: the engine models
  the full PMI constraint set (`MUST_START_ON`, `FINISH_NO_LATER_THAN`,
  etc.) but the Constraints panel only ever synthesizes generic
  "Planned Start / Deadline / Actual Lock" rows from raw dates -- real
  constraint types/violations are never surfaced or editable in QML. Engine
  capability outstrips the UI.
- **Dependency create/edit/delete has no QML entry point at all**, despite
  full backend command support (`createDependency`/`updateDependency`/
  `deleteDependency`) -- **FUTURE FEATURE gap to close in R4.4** if
  dependency editing belongs in Planning.
- Only one dialog exists (Save Baseline, fixed 420px, same systemic gap).
- The project/baseline/calendar selector action bar is a fixed-width
  `RowLayout` with no overflow at narrow widths (**UX REDESIGN DEBT**,
  same category as R3.7); the activity table has no `hideBelow` either.
- `SchedulingTimelinePanel.qml` is a **hand-rolled Gantt-lane canvas**, not
  a table -- column-hiding won't apply to it; R4.5 will need a distinct
  adaptive strategy (zoom/scroll windowing) for this one panel, matching
  the plan's own anticipation that Planning "may require specialized
  adaptive console behavior."
- A `SplitView` pane has a hard `minimumWidth: 420` that will clip on
  narrow shells -- concrete R4.5 target.

### Cross-cutting pattern across all three

The exact same two responsive gaps recur in Projects, Tasks, and Planning
independently: missing `hideBelow` column config, and toolbars/action bars
with no overflow at narrow widths -- the identical category R3.7 already
fixed for Portfolio. Dialog-width clamping is a single shared-base-widget
fix (`EntityDialog`/`CenteredDialog`), not three separate fixes.

**R4.1 -- CHARACTERIZE CURRENT WORK UX: COMPLETE.**

## 29. R4.2 closure: Projects redesign

Built exactly the two gaps R4.1 found: a catalog -> inspector -> full
detail step (previously a direct catalog -> full-detail jump with nothing
in between), and an explicit Set/Clear Active Project action (previously
absent anywhere in Projects).

**Inspector.** `ProjectsWorkspacePage.qml`'s list area is now a
`RowLayout` (was a plain `Item`) holding `ProjectsListPage` alongside a
new `AppWidgets.InspectorPanel` -- the same shared widget Platform's
Sites/Organizations/Users/etc. pages already use, so this follows an
established pattern rather than inventing a new one. Single-click/select
(`onRowSelected` -> `selectProject()`) now shows the inspector; it does
**not** trigger any additional fetch -- the inspector is built purely from
the already-loaded catalog row's own `state` fields (one label per fact:
Client, Site, Start, Finish, Approved Budget, Contact, rather than several
facts mashed into one combined string), the same fields the table's
columns already display. Only double-click/row-activation still triggers
`activateProject()`'s heavier `build_project_detail_state()` fetch and
opens the full detail page -- unchanged from before. The inspector is
visible only at `compactContentBreakpoint`+ (below that, no inspector, per
section 11's compact-tier rule), and closes by clearing the selection.

**Explicit Set/Clear Active Project.** The inspector's secondary action
toggles between "Set Active Project" / "Clear Active Project" based on
whether the selected row is already `pmProjectContext.activeProjectId`,
calling `PMProjectContextController.selectProject()`/`clearProject()`
directly -- the same shared context bar and Portfolio's R3.6 action use.
Opening/selecting a row still never pins by itself; only this explicit
action does, matching the global project-context rule.

Verified with 3 new real QML-engine tests (real created project, no
mocks): selecting a row populates the inspector without opening full
detail; Set/Clear Active Project correctly toggles
`pmProjectContext.activeProjectId` and the inspector's own active-state
read; row activation still opens full detail as before. Full targeted
sweep (canonical shell/compatibility routes, architecture guardrails, R4.2
tests) -- 35 tests, all green.

Two incidental fixes made in passing:
- `ProjectsListPage.qml`'s root `Item` had a leftover `anchors.fill:
  parent` that started conflicting once its outer usage added
  `Layout.fillWidth`/`Layout.fillHeight` for the new `RowLayout` --
  removed (Qt warns "anchors on an item managed by a layout... undefined
  behavior" for exactly this).
- Design-doc section 11 gained a note that `DataTable`'s `TableView`
  already scrolls both horizontally and vertically natively (a real,
  already-existing capability that wasn't written down anywhere) --
  complementary to `hideBelow`, not a substitute for it.

**R4.2 -- PROJECTS REDESIGN: COMPLETE.**

## 30. KPI strip regression during R4.2 verification

While testing R4.2 live, a real rendering regression surfaced on multiple
pages (Projects, Resources): the shared `KpiStrip` widget's earlier
"responsive wrap" attempt (section 26) rendered a single-metric strip as
squashed, overlapping text instead of a normal centered value/label. See
section 26's updated note -- reverted to the known-good pre-Flickable
version (git commit `ce275fb2`); the underlying illegible-cells-at-narrow-
width gap remains open for a future, more carefully (visually) verified
attempt. Confirmed fixed by the user after an app restart.

## 31. R4.2 deep verification pass (Projects, against a full checklist)

The initial R4.2 closure (section 29) built the inspector and Set/Clear
Active Project action but did not verify the surrounding dialog/detail
machinery it now surfaces more prominently. A full checklist pass across
list, detail, Create/Edit dialogs, date picker, selectors, active-project
semantics, lifecycle actions, navigation, responsive UX, QML wiring, and
performance found two real, previously-undetected bugs -- both fixed and
regression-tested:

**Selection silently reassigned across pagination (real bug, fixed).**
`resolve_selected_project_id()` fell back to `filtered_projects[0].id`
whenever the requested id wasn't present in the *current page's* items --
meaning selecting a project on page 1, then turning to page 2, silently
swapped the selection to an unrelated project the user never clicked. This
was always latent but harmless before R4.2 (nothing rendered the
selection); the new inspector makes it a real, visible correctness bug.
Fixed: selection now clears (returns `""`) rather than substituting a
different project, in both the "not on this page" and "no id given" cases
-- selection changes only through an explicit `selectProject()` call, matching
the same explicit-action rule that governs active-project pinning.
Regression-tested (`test_pm_r4_2_selection_survives_pagination.py`, 4
cases, previously zero test coverage existed for this function at all).

**Opening detail scaled with total project count (real performance gap,
fixed).** `activateProject()` -> `build_project_detail_state()` called
`desktop_api.list_projects()` (fetch + serialize every project in the
tenant) just to find one by id, when `get_project(id)` -- a real
single-row repository lookup with its own per-project permission check --
already existed and simply wasn't being used. Fixed by switching to it;
opening one project's detail is now O(1) against project count, and
correctly re-applies per-project authorization instead of relying on the
coarser list-level check. Covered by the existing R4.2 inspector tests
(`test_row_activation_still_opens_full_detail`), re-run and green after
the change.

**Verified with real evidence (code-traced, not assumed):**
- Date picker (`DateField.qml`): real calendar popup (month/day/year
  combos + Today/Clear/Apply), already clamps its own popup to
  `popupBoundaryItem`'s bounds -- no change needed.
- Date round-trip: `format_date()`/`optional_date()` operate on plain
  `datetime.date` via `.isoformat()`/`date.fromisoformat()` -- no
  `datetime`/timezone conversion anywhere in the path, so no day-shift
  risk. Empty date strings parse to `None` cleanly; malformed strings
  raise a clear validation error the dialog surfaces without closing.
- End-before-start validation: enforced at the domain model level
  (`Project._validate_date_range()`, `PROJECT_DATE_RANGE_INVALID`) --
  authoritative regardless of entry point, not just a UI-side check.
- Edit dialog field population: every field `ProjectEditorDialog.
  populateFromProject()` reads (`name`, `clientName`, `clientContact`,
  `startDate`, `endDate`, `siteId`, `status`, `description`) is present in
  `build_project_state()`'s output -- confirmed the same function backs
  both the catalog row (feeding the new inspector) and the full detail
  view, so passing either into `openEditDialog()` populates correctly.
- Save flow: `run_mutation()` sets busy before the operation and disables
  the primary button while busy (real duplicate-submission guard, not
  cosmetic); failure sets `errorMessage` and keeps the dialog open;
  success closes it and triggers `_request_domain_refresh()`, which
  re-fetches both the catalog list and the selected project's detail --
  confirms "successful edit refreshes both list and detail."
- Detail page sections: all 10 (Overview/Schedule/Tasks/Resources/
  Financials/Risks/Documents/Activity/Material Demand/Procurement) are
  real lazy-loaded components with real data bindings, not placeholder
  shells.
- Dialog width responsiveness (section 29's `CenteredDialog` fix):
  re-verified reactive to the overlay resizing after the fact, not just
  at open time -- a first version only reacted to `widthChanged`/
  `aboutToShow` and missed the overlay's own width settling after
  construction; rebuilt around a proper property-binding dependency
  (`availableDialogWidth`) so it's correct regardless of timing. 2 new
  regression tests, one confirming the clamp when oversized, one
  confirming untouched behavior when the dialog already fits.
- Client/Client Contact are plain text fields, not selectors, in Projects
  today (matches current scope -- not a gap introduced by R4.2). Site is
  a real dropdown submitting a stable id. No Calendar or Project-Manager/
  owner selector exists in Projects -- those concepts belong to Planning
  (R4.4), not this capability.

**Confirmed pre-existing, unrelated to any R4.2 change:** re-ran the full
architecture guardrail suite (a stash-diff check, not assumption) --
6 failures reproduce identically with every R4.1/R4.2 change fully
stashed out (two `FileNotFoundError`s from stale test paths, a legacy RBAC
env-var check, a large-module growth budget, a 1200-line test-file limit,
and one pre-existing parent-relative QML import in Portfolio's
`ScenariosTab.qml`). None touch anything R4.2 changed.

**Not verified in this pass (needs a real windowed check, not assumed --
the KpiStrip incident is the standing reminder why):** exact pixel
behavior at each of the five acceptance sizes; a full manual walkthrough
of Projects -> Tasks/Planning/Finance cross-navigation deep-links;
`qmllint` (not installed in this environment, as already noted repeatedly
in this doc).

**R4.2 -- PROJECTS REDESIGN, DEEP VERIFICATION: COMPLETE** (two real bugs
found and fixed; visual/cross-navigation items above remain open pending a
live check).

## 32. DateField popup redesign (shared, all 20 consumers app-wide)

The date-picker's month/day/year row (`App.Controls.DateField`) packed all
three into a single 3-column `GridLayout` with `Layout.minimumWidth: 0` on
the month combo. When the popup was clamped to a narrow boundary (e.g. a
date field inside a compact-width dialog), the month combo -- needing room
for "September"/"November", not just "May" -- got squeezed down to
whatever a third of the narrow popup left it, clipping the text.

Redesigned: month is now a full-width row on its own; day and year (both
short, fixed-width values -- 2 and 4 digits) form a two-column row below.
This no longer depends on the popup being wide enough for three combos
side by side, so it doesn't clip regardless of how narrow the field/dialog
around it is. The Today/Clear/Apply button row also gained real minimum
widths (was `Layout.minimumWidth: 0` on all three) so button labels can't
clip either. The popup's own minimum-width floor was raised from 180 to
240 to match what the redesigned content actually needs.

This is a shared widget used by 20 real consumers across PM, Platform, and
Inventory (Task/Project/Register/Financials/Calendar/Purchase-Order
dialogs among them) -- all of them only ever use the field's public API
(`text`, `placeholderText`, `dateSelected`, `popupBoundaryItem`), never
reach into its internal month/day/year structure, so this was a contained,
internal-only layout change with no API surface change. Verified with a
new real QML-engine test asserting the month/day/year combos render at
their real (non-clipped) widths at a realistically narrow (260px) boundary
-- plus the existing DateField registration test and the full R4.2 test
batch, all green.

## 33. DataTable redesign: margins, header/row alignment, header checkbox,
column resize, sort icon

Five issues reported live against Projects, all in the shared `DataTable`
widget (used across PM, Platform, Maintenance, and Inventory -- every list
page in the app):

1. **Header text cramped/clipped on the left.** Header and row cells both
   used `Theme.AppTheme.spacingSm` for their left margin -- widened to
   `spacingMd` (and the matching right margin to `spacingSm`) on both
   header and row cells (text, status chip, progress bar) so they're
   consistent with each other and less cramped against the edge.
2. **Row entries not aligned with their column header.** `_colWidth()`
   could return a fractional pixel width; the header positions cells in a
   plain `Row` (full floating-point accumulation) while the data area is a
   real `TableView` (its own internal column-position accounting) -- each
   side rounding/snapping that fraction independently drifted a pixel or
   two further apart with every column to the right. Fixed by rounding
   `_colWidth()`'s result once, so both sides consume the same integer.
3. **Header "select all" checkbox didn't work and wasn't centered.** It
   used `AppControls.CheckBox` -- a real `QQC2.CheckBox` Control with its
   own internal indicator/contentItem/click layout -- while the working
   per-row checkboxes are a plain `Rectangle`+`Text`+`MouseArea` with no
   Control involved at all. Replaced the header checkbox with the exact
   same hand-rolled pattern the row checkboxes already use, rather than
   keep fighting the Control's internal state machinery.
4. **No way to resize a column.** Added a drag handle on each column's
   right edge (a 9px hit target centered on the existing 1px divider).
   Dragging shows a live guide line (not a continuous width recompute --
   that would mean a full table-model rebuild per pixel of mouse
   movement) and commits the new width once, on release, via the same
   `preferredWidth` override key `_columnBaseWidth()` already reads, then
   `columnsStateChanged()` so it persists the same way column visibility/
   order already do. **Explicitly clarified during this work:** resizing
   one column must not shrink any other column to compensate -- the table
   already scrolls horizontally, so growing a column should grow the
   table's total content width instead. The first commit through this
   path now freezes every *other* column's currently-rendered width as
   its own explicit `preferredWidth` at the same moment (captured before
   the drag's own width lands), not just the dragged column -- otherwise
   growing one column reduces `_extraFlexSpace`, which every flex-based
   column's share is computed from, so every other column would visibly
   narrow as a side effect of resizing something else.
5. **Sort indicator looked bad.** Replaced the 7px unicode "▲"/"▼" glyphs
   with real `chevron_up`/`chevron_down` icons from the existing icon font
   (`AppIcons.AppIcon`) -- crisp and theme-consistent instead of tiny,
   inconsistently-rendered text glyphs.

**One real bug found and fixed while building the resize handle itself:**
its `MouseArea` sat *underneath* the pre-existing sort `MouseArea` (which
fills the whole header cell and is declared after it) -- without an
explicit `z`, later-declared siblings paint on top and steal input, so
every press meant for the resize handle was being swallowed by the sort
click handler instead. Fixed with `z: 1` on the resize handle.

Verified with 4 new real `QTest`-based mouse-simulation tests (real press/
move/release drag sequences, not just structural checks): the header
checkbox click-toggles-all and click-toggles-off-when-already-all-
selected; column resize commits exactly once on release (not per
intermediate move); resizing one column leaves every other column's width
unchanged. Full regression: 57 targeted DataTable/R4.2/guardrail tests
plus the 125-test Portfolio/Dashboard/Overview batch, all green -- this
widget backs list pages across the entire app, not just Projects.

**R4.2 DataTable redesign: COMPLETE.**

## 34. Unplanned maintenance interlude: shell project-context bar and Views
removal (R4.3 paused for user-driven fixes)

Two direct product requests, out of R-phase sequence, executed before
resuming R4.3 (Tasks redesign) at the user's explicit request ("make R4.3
continue after fixes... it can be put on pause" -- there are more fixes
coming before returning to R4.3).

**1. Shell-level `ProjectContextBar` and `PMProjectContextController`
removed entirely.** Live report: the top search+project-dropdown bar was
visible on some workspaces and hidden on others (`NOT_APPLICABLE` policy
destinations), causing a UI flicker as the user navigated between them.
Investigation (before deleting anything) confirmed the two REQUIRED-policy
destinations that were the bar's original reason to exist -- Scheduling and
Financials -- already maintain their own fully independent in-page project
selectors and never actually read from `pmProjectContext`, so the shared
shell-level state had no real functional effect beyond the bar itself, the
REQUIRED-policy gate, and the Set/Clear Active Project buttons on
Portfolio/Projects. Per explicit user decision ("Remove everything"),
deleted:
- `ProjectContextBar.qml`, `ProjectContextRequiredState.qml` (and their
  `qmldir` entries).
- `PMProjectContextController` (`pm_project_context_controller.py`) and its
  exposure (`pmProjectContext`, `projectContextRequirementSatisfied`,
  `projectContextRequirementChanged`) from
  `ProjectManagementWorkspaceCatalog`.
- The `ProjectContextPolicy` enum and `project_context_policy` field from
  `navigation.py` (and the `projectContextPolicy` property from
  `PMWorkspaceNavigationController`) -- nothing else consumed this axis
  once the shell-level gate was gone.
- The "Set Active Project"/"Clear Active Project" secondary action from
  Portfolio's `PortfolioDetailPanel.qml` (R3.6 addition) and from Projects'
  inspector (`ProjectsWorkspacePage.qml`, R4.2 addition).
- All now-inapplicable tests (whole files where the test was entirely about
  this feature; individual tests removed elsewhere). 48 targeted tests
  green after removal.

**2. "Views" (saved-views) feature removed from the 5 pages that enabled
it**, per direct request ("delete all qml, controller/presenter codes
related to it"):
- **Tasks**: real saved-views subsystem (`TaskSavedViewService`,
  `task_saved_view_actions.py`, `ProjectManagementTaskViewStore`,
  `TasksSavedViewsPopup.qml`, `taskViewOptions`/`selectedTaskViewName`/
  `selectTaskView`/`saveCurrentTaskView`/`applySelectedTaskView`/
  `deleteSelectedTaskView` on the workspace controller) deleted wholesale.
- **Timesheets**: investigation found its "Views" button was *not* a
  saved-views feature at all -- it was the only UI control for the review
  queue's status filter (Submitted/Approved/Rejected), mislabeled behind
  the Views affordance, with no other access point (the separate Filter
  popup only covers Project/Resource/Period range). Flagged to the user
  rather than silently deleting working functionality; decision was to
  fold the status combo into the existing `TimesheetsFilterPopup.qml`
  (no backend change needed -- `queueStatusOptions`/`selectedQueueStatus`/
  `setQueueStatus` already existed on the controller) and remove the
  `TimesheetsViewsPopup.qml`/Views button as pure UI dead weight.
- **Collaboration, Dashboard (`DashboardOperationalPanel`), Scheduling
  (`SchedulingActivityTimelinePanel`)**: `showViews` was already `false` on
  all three with no popup/backend ever built -- just removed the dead
  `showViews: false` flag.
- `TableToolbar.qml`'s shared `showViews`/`viewsClicked`/`viewsButtonItem`
  properties were left untouched -- confirmed still genuinely used by
  Platform's `ControlWorkspacePage.qml` and 5 Inventory/Procurement list
  pages.

**Status: both removals COMPLETE**, targeted regression green.

**3. Two live DataTable bug reports fixed in the same interlude:**
- **Inspector didn't close on outside click.** `_emptySpaceCatcher` (built
  earlier this session to clear selection on a blank-space click) used
  `anchors.fill: parent` -- but a Flickable's default `data` property
  silently reparents plain children like this into its `contentItem`,
  whose size is the scrollable CONTENT size, not the viewport, and which
  scrolls with `contentY`. With few rows, `contentHeight` is far smaller
  than the visible viewport, so the catcher was confined to a thin strip
  near the top; the rest of the visibly-empty viewport below it received
  no click handling at all. Fixed by explicitly overriding
  `parent: _mainView` and sizing to `_mainView.width`/`height`, so the
  catcher always spans the real viewport regardless of row count and
  stays put under scrolling. Verified real row-click passthrough still
  works (a naive fix could make the now-viewport-sized catcher swallow
  row clicks instead of falling through to them).
- **Row lines didn't reach the viewport edge after shrinking a column.**
  Row background/divider are drawn per-cell in the `_mainView` delegate;
  the actual last column (index `length-1`) never gets a resize handle of
  its own, but flex:0 columns' `_colWidth()` always returns their own
  fixed width regardless of `_hasManualColumnWidths` -- so shrinking an
  earlier (draggable) column doesn't grow the last column to compensate,
  and total content width can drop below the viewport width, leaving a
  blank untreated strip after the last column. Fixed by adding a root-level
  `_rowFillWidthFor()` function the last-column cell's background/divider
  call to extend their width to the current viewport edge (via
  `_mainView.contentX + _mainView.width`) instead of stopping at their own
  column width. Both fixes verified with real `QTest` mouse-simulation
  tests (not source-contract checks) plus the full targeted R4.2/DataTable
  suite, all green.

R4.3 (Tasks redesign) remains paused pending further user-directed fixes;
resume from here when instructed.

## 35. R4.2 reopened: deep data/filter/detail-IA verification and fix pass

R4.2 was reopened at explicit user request ("do not assume R4.2 is correct
because the redesign is visually complete") for a field-by-field DataTable
audit, a professional multi-filter upgrade, and a full Project Detail IA
audit. R4.3 (Tasks) was **not** touched. Not committed as part of this
phase.

### DataTable column audit and fixes

Traced every column DB → reader → DTO → controller → QML. Findings and
fixes:

- **`approved_budget` INNER JOIN to `ProjectFinancialProfileORM` could
  silently drop rows.** `filtered_total`/summary counts are computed
  without that join, but the paged row-fetch used an INNER join to it for
  currency code -- any project missing a finance profile would vanish from
  the page while still being counted in the total (count says N, rows
  returned < N). Changed to LEFT OUTER JOIN.
- **`approved_budget` SQL `coalesce(SUM(...), 0)` defeated the "Not set" vs
  "$0 approved" distinction** in `format_budget()` -- a project with zero
  approved budget lines was indistinguishable from one with a genuine
  $0.00 approval. Removed the SQL-side coalesce; `None` now passes through
  correctly.
- **`clientName` was free text only, disconnected from `client_party_id`.**
  The FK existed on domain/ORM/DTO already but was never joined or
  resolved. Added a LEFT OUTER JOIN to `PartyORM`
  (`COALESCE(party.party_name, project.client_name, "")`) and a new
  `client_label` field (authoritative *display* value) kept separate from
  `client_name` (the raw, still-freely-editable dialog field) -- so the
  edit dialog never round-trips a resolved party name back into free text.
  Column key renamed `clientName` → `clientLabel`; sort key
  `clientName` → `clientLabel` (server-sort allowlist and reader
  `sort_expressions` updated together).
- **Date columns rendered raw ISO strings** (`2026-05-01`) instead of a
  human format. `format_date_label()` now uses `%d %b %Y` (matches the
  format already used elsewhere in PM, e.g. Register's `due_date_label`).
- **Real repository bug found and fixed while verifying the above with a
  real DB round-trip test**: `SqlAlchemyProjectRepository.update()`'s
  column-value dict omitted `site_id`, `department_id`, `client_party_id`,
  and `manager_user_id` entirely -- meaning **no update to any of these
  four fields was ever persisted**, regardless of what the domain object
  carried, silently reverting them on every `update_project()` call. This
  was latent and undetected because nothing previously round-tripped these
  fields through an update path in a test. Fixed by adding all four to the
  update statement's value dict. `organization_id` deliberately left out
  of this fix (it doubles as a `WHERE` scope filter in the same statement;
  changing it correctly would require a separate, more careful operation
  and is outside this audit's scope).

Column disposition: all 9 pre-existing columns **KEEP** (none removed);
`clientName` → `clientLabel` (**FIX DATA MAPPING** + **RENAME**),
`approvedBudgetLabel` (**FIX DATA MAPPING**, join + null handling),
`startDateLabel`/`endDateLabel` (**FIX FORMAT**). No column was backed by a
fake/hardcoded value; `clientContact` remains correctly `HIDE BY DEFAULT`.

### Filter architecture: Site, Department, Project Manager, date ranges

Previous state: exactly one filter (Status), no typed filter object, and no
`clearFilters()`. Domain-real fields available but unfiltered: `site_id`
(already joined for the column), `manager_user_id` (FK to `users`, unused),
`client_party_id` (FK to `parties`, now resolved for display). No
`department_id` existed on `Project` at all -- **added as a real column**
(domain field + ORM column + `q7r8s9t0u1v2` migration), matching Site's
existing pattern, per explicit user direction to build it as a real field
rather than skip the filter or fake it.

New server-side, composable filters, all pushed to SQL `WHERE` before
`LIMIT`/`OFFSET` (verified with a real DB test asserting the full
intersection of Site + Department + Manager + start-date-range returns
exactly the one matching project, and that a date range excluding an
out-of-range project actually excludes it):

- **Site** (`site_id`, equality on already-`site_id`-scoped column).
- **Department** (`department_id`, equality; new column, no join needed).
- **Project Manager** (`manager_user_id`, equality on existing FK column).
- **Start date range** / **End date range** (`>=`/`<=` predicates).

Threaded through every layer with named, typed parameters (no
untyped/loose dict): `SqlAlchemyProjectCatalogReader.read_page()` →
`ProjectCatalogReader` protocol → `ProjectQueryMixin.query_catalog_page()`
→ `ProjectManagementProjectsDesktopApi.list_project_page()` (string
`"all"` sentinel / ISO date strings at the desktop-API boundary, matching
the existing `status="all"` convention) → `build_workspace_state()` →
`ProjectProjectsWorkspacePresenter` → `ProjectManagementProjectsWorkspaceController`
(new properties `selectedSiteFilter`, `selectedDepartmentFilter`,
`selectedManagerFilter`, `startDateFrom/To`, `endDateFrom/To`, `siteOptions`
(pre-existing) + new `departmentOptions`, `managerOptions`). Export
(`list_export_records()`) threads the identical filter set through the
same `build_workspace_state()` call, so exported rows always match the
visible filtered query with zero extra wiring. A new `clearFilters()`
resets every filter (search, status, site, department, manager, both date
ranges) and refreshes once.

Option sources follow the existing site-picker convention exactly (inject
a `Platform*DesktopApi`, call `list_*`, map `DesktopApiResult.data` to
`{value, label}`): `PlatformDepartmentDesktopApi.list_departments()`
(already existed, just not wired into Projects) and
`PlatformUserDesktopApi.list_users()` (new wiring) via
`build_department_options()` / `build_manager_options()` on the presenter,
injected in `context.py` from the existing `platform_department` /
`platform_user` registry entries. Tenant/organization scoping is
unaffected -- new filters are appended to the same `filtered` predicate
list the existing scope filters seed, never around it.

### Filter UX

`ProjectsFilterPopup.qml` rebuilt as a single modal surface (Status, Site,
Department, Project Manager, Start/End date ranges) in a responsive
2-column `GridLayout`, all fields staged as drafts and committed together
by one **Apply** (the existing R4.2 draft/Apply/Clear/Close pattern, now
covering seven fields instead of one). `ProjectsListPage.qml` gained a
concise active-filter-chip row beneath the toolbar (`Status: Active ×`,
`Site: Hamburg ×`, ...) with per-chip clear, so applied filters stay
visible without permanently consuming toolbar width. Toolbar itself is
unchanged (Search / Filters / Customize / Refresh / Import / Export).

### Project Detail information architecture: consolidation

Full section-by-section audit (purpose / data source / wiring status /
duplication / recommendation) found the same pattern the R4.1
characterization had already flagged for other capabilities: sections that
looked equally "real" from the tab list were, underneath, a mix of fully
wired, decoratively stubbed, and backend-real-but-UI-disconnected. Ten
sections reduced to five:

| Section | Disposition | Why |
|---|---|---|
| Overview | **KEPT, extended** | Merged in Schedule's two fields (100% duplicate of Overview's own Start/Finish); added Site and Department rows (both now real, previously shown nowhere in Detail despite being real editable fields) |
| Schedule | **REMOVED** | Every field it showed (Start Date, Finish Date) was already shown identically in Overview |
| Tasks | **KEPT unchanged** | Real, fully-wired data (`list_tasks`, unbounded but naturally bounded to one project's task count); a genuine "Open in Tasks" navigation link was investigated and deliberately *not* added -- see below |
| Resources | **KEPT unchanged** | Real, fully-wired data plus project-scoped assign/edit/remove mutations that exist only here, not duplicated by any dedicated workspace |
| Financials | **REMOVED** | Its two real fields (Approved Budget, Currency) were already shown identically in Overview; the rest of the section was a static "open Financials workspace" message with no unique data |
| Risks | **FIXED — was dead-backend-real, UI-disconnected** | `risks_builder.py` already queried the real Register (`list_entries(project_id, entry_type="RISK")`) and populated `controller.projectRisks`, but the QML section never read it, showing a static "open Register" message instead. Rewired to a real bounded `RecordListCard` bound to `projectRisksModel.items` |
| Documents | **REMOVED** | Stub backend (`items=()` hardcoded) and unbound UI; no real document capability exists anywhere in this app for projects |
| Activity | **FIXED — was fully fake, now fully real** | Previously: stub backend (`items=()`) fetched into a property (`projectActivity`) the QML never read, AND the QML separately read a key (`state.activityItems`) the real detail projection never populated -- two independent dead paths that happened to both resolve to an always-empty feed. Rewired end-to-end onto the existing, already-real `ActivityService`/`PlatformActivityDesktopApi.list_recent(entity_type="project", entity_id=..., limit=50)` (the same real audit-log CQRS read already used by Inventory/Procurement's per-entity activity feeds) -- no new backend needed, just real wiring. A small keyword-based status classifier (success/warning/danger) was written locally in `activity_builder.py` rather than imported from Inventory's private serializer, since PM must not import Inventory/Procurement packages directly |
| Material Demand | **REMOVED** | Capability-gated (`inventory.reservations.create`) but zero backend wiring regardless of capability; pure placeholder text |
| Procurement | **REMOVED** | Capability-gated (`procurement.purchase_orders.read`) but zero backend wiring regardless of capability; pure placeholder text |

Final IA: **Overview, Tasks, Resources, Risks, Activity** — five sections,
all fully real, none placeholder, none duplicating another section's data.

**Cross-workspace "Open in Tasks/Register" navigation was investigated and
deliberately not built.** Tracing the only existing precedent
(`TasksWorkspaceState.navigateToRoute()` / `openTaskReservationsRoute()`,
which calls `shellModel.selectRoute(...)`) found that `shellModel` is
**never actually assigned** on any capability page loaded through the
canonical shell: `ProjectManagementWorkspacePage.qml`'s per-destination
`Loader.onLoaded` binds only `pmCatalog` to the loaded page, never
`shellModel`, so `TasksWorkspacePage`'s own `shellModel` property -- and
therefore its route-navigation functions -- are provably dead when loaded
through the canonical shell (the `if (root.shellModel && ...)` guard
never passes). Grepping the entire `workspaces/` tree found no other
capability page or section that successfully performs cross-workspace
navigation this way. Building a second, equally-dead "Open in Tasks"
button on top of the same broken mechanism would not satisfy the "detail
actions are real and wired" gate; the Tasks and Risks sections were
therefore designed as bounded real-data displays without a fabricated
navigation action. This dead `shellModel` wiring is a genuine finding
worth fixing in its own right, but is out of scope here since it lives in
`TasksWorkspacePage`/`ProjectManagementWorkspacePage.qml`, and R4.3 (Tasks)
must not be touched by this reopened R4.2 pass.

### Detail header, Create/Edit consistency, performance

- Detail header (title + status only) vs. Overview's first row: unchanged,
  pre-existing single-field (status) overlap judged too minor to warrant
  restructuring, consistent with the original R4.2 closure's finding.
- `ProjectEditorDialog.qml` gained a **Department** selector, populated from
  the same `departmentOptions` controller property the filter popup uses
  (one option source, not two) -- mirrors the existing Site selector
  exactly, including the same pre-existing quirk (no "unassigned" option
  in `build_site_options()`/`build_department_options()`, so a brand-new
  project's selector defaults to index 0 -- i.e. the first real site or
  department -- rather than "none"). Documented here as a known systemic
  quirk shared by both pickers, not newly introduced, and not fixed in
  this pass (fixing it would change Site's already-established behavior
  app-wide, which is out of scope for a Department addition).
  Dialog widened 560px → 680px and its `GridLayout` gained a 3-column tier
  at width > 640 so the added field grows the dialog wider, not taller
  (verified: edit-mode row count is unchanged at 4 rows; create-mode gains
  no extra row either, versus a 2-column layout which would have added a
  5th row).
- Detail-load performance: confirmed no new N+1. The real DB SQL-statement
  budget test (`test_workspace_page_query_budgets_are_constant`) asserts
  `query_catalog_page()` costs exactly 4 SQL statements regardless of which
  filters are set; verified unchanged after adding the `PartyORM` join,
  the `department_id` predicate, and three more equality/range predicates
  (joins and additional `WHERE` terms are folded into the same existing
  statements, not new round trips). Lazy detail sections (Tasks/Resources/
  Risks/Activity) each fire exactly one query on first open, same as
  before; Activity's new real query follows the identical one-call
  lazy-load pattern already used by the other three.

### Testing added

- Real DB tests (`test_workspace_database_pagination.py`): Site + Department
  + Manager + start-date-range composition returns the exact intersection;
  Department alone and date-range-alone tested independently to prove each
  predicate is actually applied, not merely accepted; `department_id`
  round-trips through `create_project`/`update_project`/`get_project`
  (this is the test that caught the repository `update()` bug above); SQL
  statement budget unchanged.
- Presenter unit tests (`test_projects_workspace_presenter.py`): full
  `TestBuildProjectActivityState` class replacing the old dead-stub
  `TestBuildProjectDocumentsState` (field mapping, status classification
  for create/delete-style actions, empty-project-id short-circuit with no
  API call, no-`activity_api` fallback).
- Existing QML offscreen-loading, route, and dialog tests re-run green
  after every structural QML change (section deletions, `qmldir` update,
  `ProjectsDetailPanel.qml` rewrite).
- Architecture guardrail suite re-run; the 6 pre-existing failures
  (`ScenariosTab.qml` parent-relative import, stale Platform-admin
  directory assertion, module-size budgets, legacy-ORM import check)
  reproduce byte-for-byte identically with all R4.2-reopened changes fully
  stashed out -- confirmed unrelated, none newly introduced.

### Deferred / unsupported (explicitly out of scope)

- Client picker as a selector (party-linked, not free text) in
  `ProjectEditorDialog.qml` -- `client_label` now resolves and *displays*
  the linked party name authoritatively when `client_party_id` is set, but
  no UI exists to *set* `client_party_id` via a picker; the dialog still
  only offers the free-text `clientName`/`clientContact` fields.
- Fixing the Site/Department "defaults to first option, not none" dialog
  quirk (see above) -- pre-existing, shared by both pickers, not
  introduced or worsened here.
- Fixing `TasksWorkspacePage`'s dead `shellModel` cross-workspace
  navigation -- real finding, out of scope because R4.3 (Tasks) must not
  be touched in this pass.
- Project type/category, calendar, progress/health/risk-state filters or
  columns -- none of these fields exist anywhere in the `Project` domain
  model; adding any would require new domain/schema work with no existing
  product decision backing it, matching this design's own "do not invent
  capabilities that don't exist" rule.
- Detail-page pixel-level responsive verification at all five acceptance
  sizes (1024x640 through 1920x1080) -- structural/binding correctness
  verified (2-/3-column `GridLayout` reflow thresholds, `RecordListCard`'s
  existing responsive text elision), but no rendered screenshot capture
  tooling exists in this environment (same standing deferral already
  recorded for R2/R3).

**R4.2 REOPENED — DATA/FILTER/DETAIL-IA VERIFICATION: COMPLETE.** R4.3
(Tasks) was not modified. Not committed.

## 36. R4.2 follow-up: Activity actor/diff tracking, and two reusable patterns for later phases

Follow-up to §35's Activity section, triggered by "all crud operation are
tracked as well right??". Not committed.

### Activity coverage and actor identity

- Confirmed (not assumed) that all four Project mutations
  (`create_project`/`update_project`/`set_status`/`delete_project`) and all
  four Project Resource mutations (`add_to_project`/`update`/`set_active`/
  `delete`) already called `record_activity()`; what was missing was
  **field-level diffs and human-readable messages**, not the calls
  themselves. Added `_diff_project_fields()` /
  `_diff_project_resource_fields()` (before/after `SimpleNamespace`
  snapshots diffed against the recorded field list) so every entry's
  `details_json.changes` carries `{field: {from, to}}`, plus a
  `message=` on every call.
- Actor identity resolution now prefers the linked **Employee**'s
  `full_name` over the `User`'s `display_name`/`username`
  (`_build_actor_lookup()` in `activity_builder.py`) — most `User` rows in
  this app correspond to an `Employee` via `Employee.user_id`, and the
  employee record carries the real recorded name. Reusable for any other
  workspace's activity feed that wants a human name rather than a login
  handle.
- The Activity section issues **two** `activity_api.list_recent()` calls
  (`entity_type="project"` then `entity_type="project_resource",
  workspace_id=<project_id>`), merged and re-sorted by timestamp — not one
  broad `workspace_id=`-only query, because Task activity also records
  under the same `workspace_id` convention and would otherwise leak
  out-of-scope Task entries into a Project's feed. Any later phase adding
  another child-entity's activity to a parent feed should follow this
  "narrow per-`entity_type` call, merge client-side" shape rather than
  widening the `workspace_id` filter.

### Reusable pattern: `RecordListCard` real bug fix (affects every section using it)

`ProjectManagement.Widgets.RecordListCard`'s row delegate set a plain
`height: rowContent.implicitHeight` binding on an `Item` inside a
`ColumnLayout`. `ColumnLayout` sizes children from `Layout.preferredHeight`
or `implicitHeight`, not the plain `height` property, so every row
collapsed to height 0 and rows rendered stacked on top of each other
(reported by the user as overlapping "Administrator" / "project.update" /
timestamp text in the Activity feed). Fixed by changing the delegate to
set `implicitHeight` instead of `height`, and anchoring `rowContent` to
`parent.top` so its top margin actually applies. This widget is shared by
`ProjectsActivitySection.qml`, `ProjectsRisksSection.qml`, and Register's
`RegisterUrgentSection.qml` — the fix applies to all three automatically.
**Any future phase (R4.3 or otherwise) adopting `RecordListCard` does not
need to re-fix this**, but should be aware plain `height:` bindings on
`Layout`-managed delegate items are the general trap to avoid.

### Reusable pattern: client-side search-filter bar over a `RecordListCard`

`ProjectsActivitySection.qml` now has an `App.Controls.SearchField` above
its `RecordListCard`, filtering the already-loaded (≤50 entries) items
client-side by `title` (the actor name) via a `_filteredItems` computed
property — no new backend query, since the full page is already in memory
and small. Shape, for reuse by any other section presenting a small bounded
list (Activity, Risks, or a future R4.3 Task-detail list):

```qml
property string _searchQuery: ""
readonly property var _filteredItems: {
    const query = root._searchQuery.trim().toLowerCase()
    const items = root.someModel.items || []
    if (query.length === 0) return items
    return items.filter(item => String(item.title || "").toLowerCase().includes(query))
}
// ...
AppControls.SearchField {
    placeholderText: "Search by name..."
    onTextEdited: (text) => { root._searchQuery = text }
}
PMWidgets.RecordListCard { items: root._filteredItems /* ... */ }
```

This is deliberately **not** the same mechanism as §35's server-side
multi-filter architecture (Site/Department/Manager/date-range on the main
DataTable) — that one exists because the underlying dataset is paginated
and server-authoritative, so filtering must happen in SQL. A detail-panel
list fetched once and capped at a small limit should stay a simple
client-side filter; only reach for a server-side filter object (§35's
pattern) when the list is itself paginated or unbounded. R4.3 should pick
whichever of the two matches what it's filtering, not default to one.

### Testing added

- `test_projects_workspace_presenter.py`: `activity_api.list_recent` mock
  converted from a fixed `return_value` to a `side_effect` branching on
  `entity_type`, matching the two-call query; new tests for actor
  resolution (Employee-preferred) and field-diff formatting (id→name
  resolution for site/department/manager).
- Ad hoc QML-offscreen verification (not committed as a permanent test):
  confirmed `RecordListCard.implicitHeight` grows by a real per-row amount
  (~69px/row) rather than collapsing to ~0 per added row, and that
  `ProjectsActivitySection.qml` loads with no binding errors and its
  `_filteredItems` correctly narrows/excludes by search text.

**R4.2 FOLLOW-UP (ACTIVITY TRACKING + LIST-SEARCH PATTERN): COMPLETE.**
Not committed.

## 37. R4.2 follow-up: currency dropdown, searchable ComboBox, Project/Client name filters

Three more user-driven fixes to the Projects workspace, layered onto §35/§36.

- **Currency field is now a dropdown, not free text.** `ProjectEditorDialog.qml`'s
  "Financial currency" field was `AppControls.TextField` with a placeholder
  hint; it's now `AppControls.ComboBox` sourced from
  `projects_workspace_controller.py`'s new `currencyOptions` property (165
  codes, read directly from the backend's own `ISO_4217_MINOR_UNITS` --
  the same table `resolve_currency_code()` already validates against, filtered
  to codes with a real minor-unit definition). Defaults to **XAF** via a new
  `defaultCurrencyCode` property when no value is set yet; an existing
  project's stored currency still resolves to its own position in the list.
- **`RecordListCard` row-overlap bug, found via user screenshot.** Its
  delegate set a plain `height:` binding inside a `ColumnLayout`; `ColumnLayout`
  only respects `implicitHeight`/`Layout.preferredHeight`, so every row
  collapsed to ~0 height and rows rendered stacked on top of each other
  (reported as "Activity" rows superimposing "Administrator" / "project.update"
  / the timestamp). Fixed by switching to `implicitHeight` and anchoring the
  row content to `parent.top` so its top margin actually applies. Shared
  widget -- also fixes the identical latent bug in Risks and Register's
  Urgent section.
- **Client-side search added to the Activity section.** A small
  `AppControls.SearchField` above `RecordListCard`, filtering the
  already-loaded (<=50) items by actor name -- see §36 for the pattern
  writeup distinguishing this from server-side filtering.
- **`App.Controls.ComboBox` is now a reusable searchable dropdown.** Any
  option list longer than 8 entries (`searchThreshold`, overridable per
  instance) automatically gets an in-popup search box that live-filters by
  label; short lists (Status) are unaffected. Selecting a filtered result
  still resolves to the option's *original* unfiltered index and fires
  `activated(index)` with that index, so every existing caller's
  `onActivated` handler (there are ~15 across the app) works unchanged --
  no caller needed to change. Also fixed: opening a popup whose current
  selection sits far down a long list (e.g. XAF near the end of an
  alphabetical currency list) used to visibly glide/scroll down to it
  (`ListView`'s default `highlightMoveVelocity`); `highlightMoveDuration: 0`
  on the full-list `ListView` makes it land there instantly instead.
- **Project Name / Client Name filters added to `ProjectsFilterPopup.qml`.**
  Two new independent, AND-composable server-side filters (not folded into
  the existing combined `search_text` OR-box), threaded through the full
  stack: reader (`func.lower(name/client_name).like(...)`, deliberately
  filtering the raw `client_name` column rather than the party-resolved
  `client_label`, since joining `PartyORM` into the bare `filtered_total`
  count query -- which has no join at all -- would silently cross-join and
  inflate the count) -> contracts -> `query_catalog_page` -> desktop API ->
  controller (`projectNameFilter`/`clientNameFilter` properties +
  `setProjectNameFilter`/`setClientNameFilter` slots) -> presenter -> QML
  popup fields + removable chips. Popup widened 380px -> 440px to give the
  now free-text fields (vs. short-code dropdowns) more room; margin/padding
  audited against the sibling Tasks/Timesheets filter popups and found
  already consistent (`dialogPadding`-based margins, `padding: 0` on the
  dialog itself) -- no fix needed there.

### Testing added

- Real DB test (`test_workspace_database_pagination.py`): Project Name and
  Client Name filters proven independently and composed (AND), plus a
  zero-match case.
- QML-offscreen verification (ComboBox search/instant-scroll, filter popup
  width/field-wiring/chips, currency dropdown default-to-XAF/preserve-existing):
  all ad hoc, not committed as permanent tests except where noted.

**R4.2 FOLLOW-UP (CURRENCY DROPDOWN + SEARCHABLE COMBOBOX + NAME FILTERS):
COMPLETE.** Not committed.

## 38. R4.3 (Tasks) opened: deep data/filter/dialog/detail verification pass

At explicit user request ("we move to the next, follow as project
workspace, verify from fields in datatable, dialogs, filters, detail pages
all backend all"), the same field-by-field verification discipline used for
R4.2-reopened (§35) was applied to Tasks -- the next workspace in the R4
roadmap (§28's R4.1 characterization already covered Tasks at a high level;
this is the detailed field-level pass). Read-only recon first (via a
sub-agent trace of the full call chain per surface), then fixes.

Tasks starts from a materially stronger position than Projects did pre-R4.2:
it already has a real multi-section lazy-loaded detail inspector (10
sections) and five genuinely composable server-side filters (Project,
Status, Priority, Schedule, plus a tokenized advanced-search syntax e.g.
`priority>=70`) -- there was no catalog/filter architecture to build, only
correctness to verify.

### DataTable column audit and fixes

Traced every column: QML key -> `serialize_task_record_view_models` ->
`TaskDesktopDto` -> `TaskService.query_workspace_page` ->
`SqlAlchemyTaskWorkspaceReader` (a recursive CTE rolling up summary-task
status/progress/dates from leaf descendants). Findings and fixes:

- **`wbsCode` (a `required`, always-visible, leftmost column) rendered
  blank for every single row.** `serialize_task_record_view_models` never
  emitted a top-level `wbsCode` key -- only nested under `row["state"]` --
  and `DynamicTableModel.data()` does a flat `row_dict.get(key)` lookup with
  no fallback into `state`. The value was real and correctly computed all
  the way through the reader; it just never reached the row root. Fixed by
  adding `"wbsCode": str(view_model.state.get("wbsCode", "") or "")` to the
  serializer.
- **`materialDemandLabel` ("Material" column, shown only with
  `inventory.stock.read`) had no data source anywhere in the list-row
  pipeline** -- `TaskDesktopDto`/`TaskWorkspacePageDesktopDto` never carried
  it, it wasn't in the reader's allowed sort keys, and `sortable: false` was
  already set (a tell that whoever wrote it knew it wasn't server-backed).
  Building it properly would need a new bulk-by-task-ids material-demand
  query; the existing single-task lookup (`get_task_material_demand`) fetches
  up to 500 reservations *per task* (see below), which would be an N+1
  disaster across a page of rows. Removed the column outright (`baseColumns()`
  no longer takes a capability param); the real, correctly-scoped Material
  Demand detail-section data is untouched.
- **Priority column showed the raw numeric priority (e.g. "95") in a
  `type: "status"` chip instead of a bucketed label.** `StatusChip` maps
  known status words to a color; an arbitrary number matches nothing and
  silently rendered as a neutral gray chip -- visually indistinguishable
  from "no priority" regardless of actual value. Fixed by computing a
  bucketed label (`_priority_bucket_label` in `task_mapper.py`: High >=70,
  Medium 30-69, Low <30 -- copied verbatim from the Priority *filter*'s own
  buckets and the reader's predicate, so the label and the filter that
  selects it always agree) and extending `StatusChip`'s shared token list
  with `high`/`medium`/`low`/`critical` (danger/warning/info/danger tones).
  This is a shared widget, so it also retroactively fixes the identical
  dead-chip bug for Register's risk-severity chip (`LOW`/`MEDIUM`/`HIGH`/
  `CRITICAL`), which had the exact same "text doesn't match any known
  token -> neutral gray" problem.
- **Start/Finish/Deadline/Actual-date columns showed raw ISO strings**
  (`2026-05-01`) instead of the human format used everywhere else in PM.
  Tasks had its own `formatting.py:format_date_label` that never got the
  `%d %b %Y` fix Projects received in §35; now it does. Confirmed safe:
  the reader sorts these columns on the underlying date *column*
  (`rows.c.start_date`/`rows.c.end_date`), never on this display label, so
  the format change cannot affect sort order.
- `title`, `statusLabel`, `projectName`, `progressValue` traced and
  confirmed correctly mapped end to end -- no fix needed. `title`'s
  whitespace-indent hierarchy hack (`'    ' * hierarchyDepth`) is real data,
  just UX debt already flagged in §28 (a proper WBS tree view is a
  distinct, larger feature) -- not touched here.

Column disposition: `wbsCode` **FIX DATA MAPPING**; `materialDemandLabel`
**REMOVE**; `priorityLabel` **FIX FORMAT** (+ shared-widget fix);
`startDateLabel`/`endDateLabel`/`deadlineLabel`/`actualStartLabel`/
`actualEndLabel` **FIX FORMAT**; everything else **KEEP**.

### Filters: verified, not changed

Priority (`high`/`medium`/`low`) and Schedule (`overdue`/`due_7`/
`no_deadline`) filter option labels (`presenters/tasks/task_filters.py`)
checked byte-for-byte against the reader's own bucket predicates
(`sqlalchemy_workspace_reader.py`) -- exact match, no gap. Project/Status/
Priority/Schedule/search-text are all real, independently composable,
server-side filters already; nothing here needed the kind of
multi-filter-architecture build R4.2 required for Projects.

### Dialogs: repository-layer sweep, no dropped fields found

Checked the same class of bug §35 found in Projects (a repository
`update()` whose column-value dict silently omits fields the domain object
actually carries) across every Task-adjacent repository `update()`:
`Task.update()` (all 15 domain fields present), `TaskAssignment.update()`
(direct attribute assignment, not dict-based -- structurally immune),
`TaskDependency.update()` (same), `TaskComment.update()` (all 16 non-PK/
non-version fields present, including every `*_json` field). All four are
complete. Cross-checked `TaskEditorDialog`'s editable-field set against
`update_task()`'s parameter list (name/description/start/duration/status/
priority/deadline/code) and the WBS-move/progress dialogs against their own
dedicated commands (`move_task`, task-progress) -- each dialog's fields map
onto exactly the command built for it, with WBS/progress/schedule fields
deliberately routed through separate dedicated commands rather than the
general `update_task()`. No dropped-field bug found; the Projects
repository bug in §35 appears to have been a one-off, not a systemic
pattern in this codebase.

### Detail sections: verified, one real performance defect found (documented, not fixed)

Assignments/Dependencies/Time/Collaboration/Skills/Schedule Impact are all
genuinely lazy (real "loaded for task id" guards) and task-scoped at the
query level -- confirmed real, not stubs.

**Material Demand is a real PERFORMANCE DEFECT, left unfixed as
out-of-scope cross-module work.** The "Details" section (`_sec0`, loaded
eagerly on every task selection, *not* behind a lazy slot, and with no
capability gate) calls `build_material_demand_state()` ->
`get_task_material_demand()` -> `list_task_reservations()`, which fetches
**up to 500 reservations across the entire organization** and filters them
in Python for one task's `source_reference_id`. This fires on every single
task row click, for every user regardless of whether they hold
`inventory.stock.read` or will ever open the Material Demand tab. Root
cause: `TaskReservationGateway` (the Protocol PM depends on, matching
Inventory's real `ReservationService.list_reservations` shape exactly) has
no `source_reference_type`/`source_reference_id` filter parameter at all --
there is no way to ask for "reservations for this task" at the query level
today. Fixing this properly means extending that cross-module Protocol and
its concrete Inventory implementation, which is real backend feature work,
not a verification-pass fix -- and PM importing Inventory internals
directly to work around it would violate this design's own module-boundary
rule (§15). Documented here as a **FUTURE FEATURE / PERFORMANCE DEFECT**
for whoever picks up Inventory/Procurement-side work next; the dedicated
Material Demand and Reservations *sections* read the same eagerly-computed
data (they were never separately lazy despite appearing so in the section
list), so fixing the query fixes both at once. The Procurement section
remains a capability-gated navigation-only CTA by design (confirmed
intentional, not dead).

### Testing added

- `src/tests/pm/test_tasks_serializer.py`: real DB round-trip proving
  `wbsCode` reaches the row root (not just `state`), `materialDemandLabel`
  is absent, priority buckets match the filter's own bucket boundaries
  (including a same-task cross-check: filtering by `priority=high/medium/low`
  returns exactly the tasks whose label says so), and the date-label format
  fix.
- `src/tests/test_qml_status_chip_priority_severity_variants.py` (new,
  `StatusChip` had zero prior test coverage): confirms `high`/`critical` ->
  danger, `medium` -> warning, `low` -> info, and an unrelated word still
  falls through to neutral.
- Full `src/tests/project_management -k task` sweep (124 tests) and the
  broader `project_management`/`pm` suite re-run green after every change.

**R4.3 (TASKS) DEEP VERIFICATION PASS: fields/filters/dialogs done,
detail-section audit done with one documented-not-fixed performance
finding.** Not committed.

## 39. R4.3 follow-up: shared ComboBox border overflow, and the Tasks detail-page IA consolidation §38 deferred

Two more user-driven fixes, both explicitly asking "did you actually check
each detail-page section the way you did for Projects" and reporting the
Tasks filter popup's fields visually overflowing its border.

### Shared `App.Controls.ComboBox` border-overflow bug

A long selected label (a long project name in the Tasks filter's Project
combo, but this is app-wide, not Tasks-specific) inflated the control's
`implicitWidth` (`Math.max(160, contentItem.implicitWidth + spacingXl)`).
QtQuick Layouts uses `implicitWidth` as the effective `Layout.minimumWidth`
whenever the latter isn't set explicitly, so `Layout.fillWidth: true` alone
could never shrink the control below that inflated width -- it overflowed
past its container/dialog border instead of eliding, exactly as reported.
Fixed by adding `Layout.minimumWidth: 0` to the shared component, so
`fillWidth` can actually shrink it down to the already-present
`elide: Text.ElideRight` truncation. Could not be reliably reproduced in
an offscreen automated test in this environment (`Text.implicitWidth`
computed as `0` for synthetic inline QML in the headless test harness here,
a font-metrics/offscreen-platform artifact, not evidence the real bug
doesn't exist) -- the fix follows directly from documented QtQuick Layouts
behavior and is safe/inert for every existing caller regardless. Please
confirm visually in a real run.

### Tasks detail-page section audit: the one real duplicate, found and merged

§38 verified each detail section's *backend wiring* (real vs. stub) but
did not yet do the Projects-style *IA* audit (purpose / duplication /
merge-or-remove per section) -- this closes that gap. Reviewed all 10
sections for purpose and overlap:

- **Material Demand, Reservations, and Procurement were three sections
  showing the same content.** All three read the identical
  `taskDetail.state.materialDemand*` fields (from the one eager
  `build_material_demand_state()` call §38 already flagged as a
  performance defect); Reservations was a strict subset of Material
  Demand's own display (same subtitle text, same counts, minus the
  fulfilled/cancelled breakdown); Procurement showed no task-specific data
  at all. All three ended at the same two "navigate away" actions
  ("Open Reservations" / "Open Procurement"), both of which Material
  Demand's own toolbar *already* exposes as independently-gated buttons
  (`canOpenReservations`/`canOpenProcurement`). Merged: `TasksReservationsSection.qml`
  and `TasksProcurementSection.qml` deleted outright (zero unique content,
  same standard this design applied to Projects' dead sections in §29/§35);
  `TasksWorkspaceState.qml`'s `detailSections` now pushes a single
  "Material Demand" entry gated on *any* of the three related capabilities
  (`inv.stock.read` OR `inv.reservations.create` OR
  `procurement.requisitions.create`) rather than three separately-gated
  tabs -- each button inside the surviving section still gates itself
  independently, so no capability combination loses an action it used to
  have. `TasksDetailPanel.qml`'s two now-orphaned `LazySectionLoader`s
  removed, the remaining ones renumbered (`_sec6`/`_sec7` for Skills/
  Schedule Impact). Also deleted: `canViewDetailSection()`, a
  `TasksWorkspaceState.qml` function that duplicated this exact
  capability check but was never called from anywhere -- dead code found
  incidentally while doing this audit.
- **Details, Assignments, Dependencies, Time, Skills, Schedule Impact,
  Activity: reviewed, no duplication found.** Each covers a genuinely
  distinct domain (core fields / resource allocation / task-to-task links /
  time tracking / skill requirements / CPM delay analysis / comments) with
  no overlapping content or redundant navigation target -- unlike Material
  Demand's cluster, these don't collapse into each other.

Section count: 10 -> 8 (Details, Assignments, Skills, Dependencies, Time,
Material Demand, Schedule Impact, Activity).

### Gateway-wiring check, done on user request before trusting the merge

PM's `gateway/` packages deliberately declare Protocols whose concrete
implementation is left to Inventory/Procurement (injected at the
composition root), so "no code in PM" does not mean "no real backend" --
worth checking explicitly before deleting anything that looks like a thin
CTA. Checked both gateways this merge touches:

- **`gateway/task/reservation.py` (`TaskReservationGateway`) is real and
  wired**, not a stub: `app_container.py` populates a live
  `inventory_reservation_service: ReservationService` from the actual
  Inventory module and threads it through to this gateway. This doesn't
  change the merge decision, though -- neither the deleted "Reservations"
  section nor the surviving "Material Demand" section ever rendered the
  individual reservation records this gateway can return; both only ever
  showed the same derived summary counts. No capability was hidden by
  removing the duplicate tile; the one surviving "Open Reservations"
  button is wired to the identical capability check either way.
- **No task-level Procurement gateway exists at all** -- `gateway/task/`
  has only `reservation.py`. A different gateway,
  `gateway/procurement/financial_source.py`
  (`ProcurementFinancialSourceProvider`), does exist, but its own
  docstring states it explicitly: "this one currently has zero
  implementations anywhere in the codebase ... not wired into any runtime
  composition today." It's also a different concern entirely (a
  project-level Finance commitment/receipt-accrual pull contract), not
  connected to the task detail page. The removed "Procurement" section's
  only backend action was always plain route navigation.

### Testing added

- QML-offscreen verification (ad hoc): `detailSections` no longer contains
  "Reservations"/"Procurement" and only includes "Material Demand" when a
  related capability is granted; `TasksDetailPanel.qml` loads cleanly with
  the two sections' `LazySectionLoader`s removed. Full
  `src/tests/project_management -k task` sweep (124 tests) re-run green
  after the merge.

**R4.3 FOLLOW-UP (COMBOBOX BORDER FIX + DETAIL-PAGE IA CONSOLIDATION):
COMPLETE.** Not committed.

## 40. R4.3 follow-up: per-section button-duplication audit, and the Assignments redesign

At explicit user request: checked every detail section (not just backend
wiring, as in §38, but the actual on-screen buttons) for the
"toolbar-and-another-one-below-it" duplication pattern, and for actions
that should be selection-gated but weren't.

### Button-duplication audit result: one real case, in Assignments

There are two toolbar layers in the Tasks detail page: a page-level
"pinned" `ContextualActionToolbar` (task title, back button, and
`TasksWorkspaceState.qml`'s `detailActionsForSection()`), and each
section's *own* internal `ContextualActionToolbar`
("sits below the DataTable toolbar; visible while a record is selected,"
per that shared widget's own doc comment). Checked all 8:

- **Assignments: real duplicate, now fixed.** The page-level toolbar
  computed a *second*, independent copy of Allocation/Set Hours/Remove for
  the selected assignment -- and did it *wrong*: it always showed those
  three regardless of the assignment's state, while the section's own
  toolbar already correctly branches (Accept/Decline for a still-pending
  assignment, Allocation/Set Hours/Remove only once accepted) and was
  already fully wired end to end, including the Accept/Decline case the
  page-level copy never handled at all. Removed the "Assignments" branch
  from `detailActionsForSection()` and the now-dead
  `edit_allocation`/`set_assignment_hours`/`remove_assignment` handling in
  `TasksWorkspacePage.qml` -- the section's own toolbar is now the single,
  correct source for these actions.
- **Details, Dependencies, Skills, Time, Schedule Impact, Material Demand,
  Activity: no duplication.** Each has its selected-row/task actions
  living in exactly one place -- either the page-level toolbar
  (Details, Dependencies) or its own section toolbar (Activity's
  Mark-Read/Refresh, Material Demand's Open Reservations/Procurement) --
  never both.
- **Selection-gating: already correct everywhere checked.** Both the
  page-level and every section-local toolbar's `actions` array is already
  computed as `[]` when nothing is selected (`ContextualActionToolbar`
  renders zero buttons for an empty array, not disabled placeholders), so
  no action button was ever visible without a valid target row.

### Assignments section: professional redesign

Replaced the plain `AppWidgets.DataTable` grid (Resource/Allocation/
Effort/Response as generic text columns) with a person-list row design,
following common resource-assignment UI conventions (name+avatar+status
at a glance, allocation shown as a visual bar not just a number, real-time
overallocation/skill/certification warnings already present in this app's
backend -- the redesign surfaces what was already computed, it doesn't add
new backend capability):

- New shared widget `App.Widgets.Avatar`: a colored initials circle,
  color picked deterministically from the resource's name (same name ->
  same color every time) from a fixed, theme-independent decorative
  palette -- reusable anywhere a list identifies a person (comment
  authors, other resource lists), not just here.
- Each assignment now renders as a full-width row: avatar, resource name,
  an `App.Widgets.ProgressBar` for allocation % (green up to 100%, red
  once overallocated -- using the existing `colorHint` override rather
  than the bar's default "low value = red" completion-progress semantics,
  which would have been backwards for an allocation percentage), hours
  logged, and a response-status chip -- selection highlight and hover
  state on the row itself (matching the divider/selection-bar convention
  already used by `RecordListCard`/`DataTable`), replacing "select a grid
  row, then look up at a toolbar far above" with the status/identity
  visible directly on the row.
- Fixed two more `StatusChip` dead tokens found while wiring the response
  chip: `accepted`/`declined` (assignment response status) weren't in its
  known-word list either -- same bug class as §38's `high`/`medium`/`low`/
  `critical` fix, now also covering this case.

External research done before designing (avatar+name+status row
conventions; allocation/workload visibility and conflict-warning
practices already implemented in this app's backend, confirming the
redesign direction rather than motivating new backend work):

Sources:
- [Data table UI design reference guide for 2026](https://www.setproduct.com/blog/data-table-ui-design)
- [Avatar UI design: What to show when there's no photo](https://www.setproduct.com/blog/avatar-ui-design)
- [Manage user or role allocation percentage on tasks (Adobe Workfront)](https://experienceleague.adobe.com/en/docs/workfront/using/manage-work/tasks/assign-tasks/manage-allocation-percentage-on-tasks)
- [Effectively Manage Team Workload: 5 Steps to Balance (Asana)](https://asana.com/resources/effectively-manage-team-workload)
- [Workload planning: A complete guide](https://resourceguruapp.com/blog/project-management/workload-planning-guide)

### Resolved finding: Task Time section duplicated the planned Timesheets destination

Flagged by the user, confirmed real, and removed on explicit user
decision: §2.1's target IA already plans "Workload Management -> My Time
/ Review Queue" as dedicated destinations for personal time capture and
manager review (R1.5 "Timesheet Review" is already closed per §14 -- the
Review Queue is real and live today, with `submitPeriod`/`approvePeriod`/
`lockPeriod`/`unlockPeriod`/`bulkApprovePeriods`). The Tasks detail page's
own "Time" section had a "Workflow" tab (`TaskTimePeriodWorkflow.qml`)
duplicating the same period-level submit/lock/unlock actions, embedded
inside every single task -- confirmed not just visually duplicated but the
*exact same backend call*: `time_command_handler.py`'s
`submit_task_period`/`lock_task_period`/`unlock_task_period` were thin
pass-throughs to `timesheets_desktop_api.submit_period`/`lock_period`/
`unlock_period` -- the identical desktop API the real Timesheets workspace
controller calls directly. No unique logic existed behind the embedded
tab. Also a real UX/IA correctness concern, not just duplication: a
*period* can span multiple tasks/assignments, so "submit this period" from
inside one task's detail view was conceptually narrower than what the
action actually does.

Removed per the user's explicit decision (option 3: replace with a
contextual link-out, no second workflow implementation, no deep-link
state invention): `TaskTimePeriodWorkflow.qml` deleted outright; the
"Workflow" tab removed from `TasksTimeEntriesSection.qml`'s `_detailTabs`
(now just Assignment/Capture/Ledger -- what's genuinely task-scoped);
replaced with an "Open in Timesheets" toolbar action that navigates to
the single existing `project_management.timesheets` route (there is only
one Timesheets route -- My Time vs. Review Queue is an internal view
choice the Timesheets workspace makes for itself, not two separate routes
-- so no role/capability duplication was needed on the Tasks side to pick
between them). `navigateToRoute()` only ever accepts a bare route id (no
deep-link parameter contract exists), so the CTA stays a plain route
hand-off, matching the existing Reservations/Procurement CTA precedent,
per the instruction not to invent a parallel state system for context
that isn't actually supported.

Backend cleanup (obsolete once the only caller was gone): removed
`submitTaskPeriod`/`lockTaskPeriod`/`unlockTaskPeriod` from
`PMTimeController`; `submit_task_period`/`lock_task_period`/
`unlock_task_period` from `ProjectTasksWorkspacePresenter` and
`time_command_handler.py`; the matching facade functions and controller
slots in `task_mutation_facade.py`/`tasks_workspace_controller.py`; and
three now-stale entries left behind in `task_mutation_facade.py`'s
`__all__` (a real latent bug -- `submit_task_period`/`lock_task_period`/
`unlock_task_period` stayed listed in `__all__` for functions that no
longer existed in the module). Signal chain
(`submitRequested`/`lockRequested`/`unlockRequested` ->
`timeSubmitRequested`/`timeLockRequested`/`timeUnlockRequested`) collapsed
to a single `openTimesheetsRequested()` forwarded the same way as every
other cross-workspace CTA in this file.

### Testing added

- QML-offscreen verification (ad hoc): Assignments' selected-action set
  correctly switches between Accept/Decline and Allocation/Set Hours/
  Remove depending on the selected row's state; overallocation math;
  `Avatar` initials for one-word and multi-word names; Time section's
  tabs are exactly Assignment/Capture/Ledger with an `openTimesheetsRequested`
  signal; `TasksDetailPanel.qml` no longer exposes the old
  `timeSubmitRequested`/etc. signals.
- `test_qml_tasks_time_entries_section_contract.py` (a pre-existing
  characterization test that intentionally pinned the *old* contract,
  including the Workflow tab) rewritten to assert the new one instead,
  plus an explicit assertion that `TaskTimePeriodWorkflow.qml` no longer
  exists.
- `test_pm_time_controller_callbacks.py`'s `TestPeriodMutationsUseFacade`
  class (tested only the removed slots) replaced with a single assertion
  that `submitTaskPeriod`/`lockTaskPeriod`/`unlockTaskPeriod` are gone from
  `PMTimeController`; its entry-mutation routing tests (unaffected) kept
  as-is.
- Full `src/tests/project_management -k task` sweep (124 tests) and the
  broader `project_management`/`pm` suite re-run green after every change
  in this section.

**R4.3 FOLLOW-UP (BUTTON-DUPLICATION AUDIT + ASSIGNMENTS REDESIGN +
TIMESHEETS WORKFLOW-TAB REMOVAL): COMPLETE.** Not committed.

## 41. Shared Activity-log design, extracted and reused for Tasks

User request: make Projects' Activity section design (§35/§36/§37) a
genuinely shared, reusable base rather than a Projects-only
implementation, and give Tasks its own real Activity (audit trail) tab
using it -- Tasks previously had no such feed at all, despite already
recording rich real activity (`task.create`/`update`/`delete`/
`set_status`/`update_progress`/`wbs_move`, plus `task_assignment.*`) that
had zero UI surface anywhere.

### Extraction

- **Python**: `presenters/common/activity_log_builder.py` (new, shared
  across PM workspaces) -- generalizes what was Projects-only logic in
  `presenters/projects/activity_builder.py`: action-word status
  classification, actor lookup (Employee-preferred), diff-summary
  formatting, and `fetch_entity_activity_entries()` (queries one primary
  entity plus optional child entity types, each via `parent_entity_id` --
  a real, indexed column on the activity record, tighter than
  `workspace_id`, which every entity recorded against the same workspace
  shares and would leak). `build_activity_records()` takes a
  `record_factory` callable so each workspace still gets its own typed
  view model (`ProjectRecordViewModel`/`TaskRecordViewModel`) without the
  shared code needing to know about either.
- **QML**: `ProjectManagement.Widgets.ActivityLogSection` (new, alongside
  the existing `RecordListCard` in the same module) -- the exact search +
  `RecordListCard` design from `ProjectsActivitySection.qml`, generalized
  (`label`, `errorKey`, `activityModel` instead of Projects-specific prop
  names). `ProjectsActivitySection.qml` is now a five-line wrapper
  extending it directly (inherits `sectionErrors`/`label`/`errorKey` as-is;
  only `projectActivityModel` -> `activityModel` needs a name translation,
  kept so `ProjectsDetailPanel.qml` didn't need to change).

### A real bug found while wiring the shared query into Projects

Refactoring Projects onto `fetch_entity_activity_entries()` surfaced that
its `project_resource` child query used `workspace_id`, not
`parent_entity_id` (the safer filter this section's own design argues
for) -- because `project_resource_commands.py`'s four `record_activity()`
calls never set `parent_entity_id` at all, only `workspace_id`. Fixed by
adding `parent_entity_id=project_id` to all four
(add/update/set_active/delete), alongside the existing `workspace_id`
(kept, since removing it would be an unrelated, unnecessary change).
Proven with a real DB test
(`test_project_resource_activity_is_queryable_by_parent_project_id`)
showing two different projects' resource activity no longer cross-leaks
when queried by `parent_entity_id`.

### Tasks' new Activity tab

- `presenters/tasks/task_activity_builder.py` (new): `entity_type="task"`
  (the task's own lifecycle) plus a `task_assignment` child query scoped
  by `parent_entity_id=task_id` (already set correctly by the existing
  `assignment_activity.py` -- no backend gap there, unlike project_resource
  above). Task lifecycle commands don't record a field-level `changes`
  diff the way Projects' `_diff_project_fields()` does, so entries show
  actor/action/timestamp without a diff-summary line -- a real, documented
  gap (not required for the feed to be real and useful; adding that
  diff-tracking is a natural, separate follow-up).
- Wired the same way every other lazy Tasks section is: `TaskCatalogWorkspaceViewModel.task_activity`
  field, `tasks_workspace_presenter.build_task_activity_state()`,
  `taskActivity` property + `loadSelectedTaskActivity` slot directly on
  the main `tasks_workspace_controller.py` (matching `scheduleImpact`'s
  placement, not a sub-controller -- Activity doesn't belong to any single
  existing sub-domain).
- **The pre-existing "Activity" tab (comments/mentions/presence) is
  renamed "Discussion".** Same component (`TasksCollaborationSection.qml`,
  whose own toolbar was already titled "Discussion"), same data, just no
  longer sharing a name with the new, unrelated audit-trail tab. Its
  section-error key renamed `"activity"` -> `"discussion"` to match,
  freeing `"activity"` for the new tab's own error key.
- New section order: Details, Assignments, Skills, Dependencies, Time,
  [Material Demand], Schedule Impact, **Activity**, **Discussion** (10 ->
  10, since one tab split into two distinctly-purposed ones rather than
  net-adding).

### Testing added

- QML-offscreen verification (ad hoc): `ActivityLogSection` loads and
  filters standalone; `ProjectsActivitySection`'s wrapper still delegates
  correctly; `detailSections` contains both "Activity" and "Discussion"
  with no duplicate; `TasksDetailPanel.qml` loads with the new section.
- `test_projects_workspace_presenter.py`'s one query-shape assertion
  updated (`workspace_id=` -> `parent_entity_id=` for the
  `project_resource` child query) -- confirmed intentional, not a
  regression, since the new filter is strictly more precise.
- Full `src/tests/project_management -k task` sweep (125 tests, up from
  124) and `test_projects_workspace_presenter.py` (36 tests) re-run green.

### Follow-up bug, found live by the user immediately after this shipped

Opening a task's new Activity tab threw
`PlatformActivityDesktopApi.list_recent() got an unexpected keyword
argument 'parent_entity_id'`. Root cause: `ActivityService.list_recent()`
(the application-layer service) supports `parent_entity_id`, and my real
DB test above (`test_project_resource_activity_is_queryable_by_parent_project_id`)
called that service directly and passed -- but `PlatformActivityDesktopApi`
(the desktop-facing facade `fetch_entity_activity_entries()` actually calls
in production) never forwarded that parameter at all. A drift between two
layers' signatures, not caught because the mock-based presenter tests
don't enforce a real method signature, and my one real-DB test happened
to bypass the exact layer that was broken.

Fixed: added `parent_entity_id` to `PlatformActivityDesktopApi.list_recent()`,
forwarded straight through. Verified by extending the same DB test to
*also* go through `PlatformActivityDesktopApi` directly (not just the
service) -- confirmed this addition actually reproduces the user's exact
error message when the fix is reverted, then confirmed it passes with the
fix restored. Lesson applied: when a real backend capability spans more
than one layer (service -> facade -> presenter), a test must exercise the
outermost layer the presenter actually calls, not stop at whichever layer
is easiest to reach directly.

**SHARED ACTIVITY-LOG DESIGN + TASKS ACTIVITY TAB: COMPLETE** (including
the `PlatformActivityDesktopApi.parent_entity_id` follow-up fix). Not
committed.

## 42. Unplanned: real production bug found and fixed -- `task_skill_requirements.version` missing column

While the R4.3 work above was running, the user hit a live error in the
"Assign Resource" dialog: `sqlite3.OperationalError: no such column:
task_skill_requirements.version`, breaking the availability/skill/
certification validation check entirely. Investigated and fixed; unrelated
to any change in this session.

**Root cause**: `TaskSkillRequirementORM` has always declared
`version: Mapped[int]`, and the migration that created this table
(`i2j3k4l5m6n7_pm_enterprise_upgrade.py`) correctly included `version` on
the *other* two tables it created in the same migration
(`resource_skills`, `resource_certifications`) -- only
`task_skill_requirements`'s own `create_table()` omitted it. A one-off
authoring mistake in that migration, not a systemic pattern (confirmed by
checking the sibling tables), and invisible to the existing test suite
because tests build their schema via `Base.metadata.create_all()` from
the current ORM models (always complete) rather than by replaying migration
history the way a real persisted database does.

**Fix**: new migration `a9f3e7c2b8d1_add_task_skill_requirements_version.py`
(head, following `q7r8s9t0u1v2`) adds the column with the same
`_has_column` idempotency guard used elsewhere, plus `server_default="1"`
matching the ORM default. Could not edit the original migration in place
(it's already been applied to real databases; Alembic migrations are
additive history, not editable after the fact).

**Verification**: ran the *entire* migration chain from scratch against a
throwaway SQLite file (`alembic upgrade head` via `Config`/`command`, not
the ORM-driven test-fixture path) and confirmed `task_skill_requirements`
now has the column; reproduced the exact failing ORM query
(`select(TaskSkillRequirementORM).where(...)`) and confirmed it now
succeeds; verified downgrade removes the column and re-upgrade restores it
(idempotency guard proven, not just a one-shot fix). Added a permanent
regression test,
`test_task_skill_requirements_version_migration.py`, exercising exactly
this (the kind of test that would have caught the original bug, since it
replays real migration history rather than `create_all()`).

**PRODUCTION BUG FIX (task_skill_requirements.version): COMPLETE.** Not
committed.

## 43. R4.3 Task Detail — Assignment + Time: deep backend audit, enterprise upgrade, QML redesign

Scope for this pass: Task Detail → Assignment, Task Detail → Time. Explicitly
excluded: Resources workspace, Timesheets workspace, Material Demand/Inventory,
R4.4 Planning. Nothing committed.

### A/B. Current-state audit (verified via two independent full-stack traces,
DB → domain → application → repository/reader → desktop API → controller →
QML → tests → cross-module callers)

**Assignment.** Table `task_assignments` (`TaskAssignmentORM`): `id, task_id,
resource_id, allocation_percent, hours_logged (Decimal), allocated_planned_hours
(Decimal), version (int), project_resource_id, response_status, responded_at`.
No `role`/`is_lead`/`is_primary` column exists anywhere — there is no
primary/lead-assignment concept in this domain today. Unique constraint on
`(task_id, resource_id)` — one assignment per resource per task, DB-enforced.
`TaskAssignment` is a real validated domain value object (not an anemic ORM
row) with field-level invariants (allocation `0 < x <= 100`, non-negative
hours/planned-hours, `version >= 1`, `response_status` enum). Application
mixin `TaskAssignmentMixin` (`application/tasks/commands/assignment.py`) owns
every write path: `assign_project_resource`, `unassign_resource`,
`set_assignment_hours`, `set_assignment_allocation`,
`update_assignment_planned_hours` (dual optimistic-lock WBS-hours
distribution against the `ProjectResource` envelope), `accept_assignment`/
`decline_assignment` (assignee-identity-gated). All mutating methods call
`record_assignment_action` → `record_activity(..., parent_entity_id=task_id)`
— fully audited. Authorization (`task.manage`/`task.read`, global + project-
scoped) and tenant/org scoping (`ProjectORM.tenant_id/organization_id` join)
are enforced in the application/repository layers, not QML. Reader side:
`SqlAlchemyAssignmentRepository` has genuine batched/joined methods
(`list_by_tasks`, `list_by_ids`, `list_timesheet_contexts`) used correctly by
`SchedulingEngine`, `ResourceLevelingEngine`, `PlannedCostService`,
`LaborCostEngine`. Desktop API (`ProjectManagementTasksDesktopApi`) exposes a
clean `TaskAssignmentDesktopDto` with no ORM leakage.

**Time.** There is exactly **one** authoritative implementation, owned by the
**platform** module (`src/core/platform/application/time_management/time/`,
tables `time_entries`/`timesheet_periods`). Project_management's own
`application/tasks/commands/time_entries.py` (`TaskTimeEntryMixin`) is a pure
forwarder to the same `TimesheetService(TimeService)` instance — there is no
project_management-local time-entry table. The **maintenance** module's
`MaintenanceLaborService(TimeService)` is the same pattern again — a
work-order task's labor booking is a row in the very same `time_entries`
table, keyed by the generic `work_allocation_id`. This is intentional, shared
platform infrastructure, not accidental duplication. Lifecycle
(submit/approve/reject/lock/unlock/reopen) lives exclusively in
`timesheet_periods.py` (platform); confirmed removed from Task Detail earlier
this session (§40) and re-confirmed clean here — no dead signals/slots/tests
remain. `_ensure_timesheet_period_editable` is the single gate blocking entry
mutation once a period is `SUBMITTED/APPROVED/LOCKED` (deliberately does *not*
block `REJECTED`, to allow correction/resubmission). No `version`/optimistic-
lock column exists on either time table.

### C. Ownership boundaries (confirmed, and where they were leaking)

`ASSIGNMENT` = who/what + how much capacity is allocated (`allocation_percent`,
`allocated_planned_hours`). `TIME` = what was actually recorded
(`hours_logged`, kept in sync automatically from time entries via
`_sync_work_allocation_hours_from_entries()` — this makes `hours_logged` a
**derived, Time-owned** value that Assignment must not independently edit).
`TIMESHEETS` = period lifecycle. Two real leaks were found (see D) where these
collapsed into each other in the current implementation.

### D. Discovered defects (evidence-based, not hypothetical)

1. **`allocated_planned_hours` and `version` are completely invisible to the
   UI.** `TaskAssignmentDesktopDto` and the QML view-model mapper never
   surface them, and `update_assignment_planned_hours` — a fully implemented,
   dual-optimistic-locked, finance-consumed application method — has **no**
   desktop API method or command DTO at all. A real, audited, financially
   load-bearing field (Finance's `PlannedCostService` reads it) is unreachable
   from Task Detail.
2. **Optimistic concurrency is inconsistent.** The `version` column exists and
   is domain-validated, but only `update_assignment_planned_hours` enforces it
   (via `update_planned_hours_with_version_check`). `set_assignment_allocation`
   — the one allocation-changing path actually reachable from Task Detail UI —
   uses the plain `update()`, silently ignoring `version`: two managers
   editing the same assignment's allocation concurrently is last-writer-wins
   with no conflict detection, despite the column and the compare-and-swap
   helper (`update_with_version_check`) already being an established,
   in-use convention for exactly this purpose elsewhere in this repository
   (`Task.update`, `ProjectResource.update`, `Resource.update`,
   `RegisterEntry.update`, several finance repositories).
3. **Task Detail's Time Summary "Hours" figure is resource-wide, not
   task-scoped** — an ownership leak in the *opposite* direction from #1/#2.
   `build_assignment_snapshot` computes its `period_summary` from
   `list_time_entries_for_resource_period` (**all** of that resource's
   allocations for the period, across every task/project they work on), while
   the task-scoped entries (`list_time_entries_for_assignment_period`,
   already fetched into `task_entries`) are counted (`len(task_entries)`) but
   their hours are **never summed**. A user viewing Task X's Time section
   today sees an "Hours" total that silently includes hours logged against
   other, unrelated tasks. This is exactly the "Task Time may capture/show
   task-specific entries" boundary (§0/§63) being violated by the read path.
4. **`set_assignment_hours` ("Set Hours" dialog) is an Assignment-side edit of
   a Time-owned, derived value.** The backend already defends against the
   worst case (it raises `ValidationError` once any real time entry exists for
   the assignment, telling the user to "edit the timesheet instead"), which
   means that for any assignment with active time tracking — the normal case
   once Time Capture is used — this action always fails. It is a genuine
   ownership-boundary violation per this pass's own Phase 0 principle (Time
   owns what was actually recorded), now that a real Time Capture/Ledger UI
   exists as the correct path to log hours.
5. **One QML-only authorization gap, but it is a pre-existing, repository-wide
   convention, not an Assignment-specific defect.** `TasksDetailPanel.qml`'s
   `canCreate` for "Assign Resource" (and, identically, for "Add Dependency")
   is computed purely from `_hasTask && !_isSummary && options.length > 0`,
   with no capability flag. This is safe (the actual mutation is fail-closed
   server-side via `_require_manage` — a denied user just sees an avoidable
   error toast), and it is applied uniformly across sibling Task Detail
   create-actions, not singled out on Assignment. Fixing it well would mean
   auditing every create-button in Task Detail, which is out of this pass's
   scope (Assignment + Time only). **Decision: documented, not fixed in this
   pass** — see Deferred Items.
6. **N+1s exist, but not on the Task Detail read path.** `task_query.py`'s
   `list_tasks_for_resource`/`list_assignments_for_resource`/
   `list_assignments_for_tasks` (per-id `task_repo.get()` in a loop) and
   `_check_resource_overallocation` (same pattern) are real, but they serve
   the **Resources workspace** and **Dashboard**, not Task Detail's own
   `list_assignments(task_id)` call (which already batches resource-name
   lookups and does not exhibit this pattern). Similarly, Timesheets'
   `list_time_entries_for_resource_period` is O(allocations-for-resource) —
   it backs period submit/approve/lock and the (already-leaking, see #3)
   resource-wide summary, not Task Detail's own task-scoped ledger read
   (`list_time_entries_for_assignment_period`, a single direct query, no
   loop). **Decision: out of scope, documented as deferred cross-module debt**
   (fixing them means touching Resources/Dashboard/Timesheets, explicitly
   excluded from this pass).
7. **No "reassign" command, no "primary/lead assignment" concept.** Neither
   has any evidence of being a real, currently-needed capability (no domain
   field, no caller, no test expecting one) — decline/remove + create-new is
   the existing pattern. **Not invented in this pass**, per "do not invent
   missing operations."

### E/F/G. Target model, commands, contracts actually implemented this pass

Given the evidence above, the following — and only the following — backend
changes were made (deliberately narrow; everything else in D is documented
and deferred rather than blindly "fixed"):

- `TaskAssignmentDesktopDto` gains `allocated_planned_hours: str`, `version: int`,
  and `project_resource_version: int` (closes D1's read gap).
  **Revised from the original decision to defer the write path**: shipping
  Planned/Remaining as read-only with no way to ever set Planned Work was
  identified (correctly) as a worse, half-finished state than doing the small
  amount of extra plumbing — so editing is now implemented on both sides:
  - **At creation**: `assign_project_resource` accepts an optional
    `allocated_planned_hours`, validated against the resource's shared
    `ProjectResource.planned_hours` envelope via a new shared helper,
    `_check_planned_hours_envelope` (extracted from the pre-existing
    `update_assignment_planned_hours` logic so both call sites enforce the
    identical invariant, not two hand-maintained copies of it). No version
    check needed at creation — there is no existing assignment row to race
    against, matching the existing convention already used for the
    allocation-percent overallocation check at creation.
  - **After creation**: a dedicated "Edit Planned Work" row action opens
    `TaskAssignmentPlannedHoursDialog.qml`, which round-trips both the
    assignment's `version` and the newly-exposed `project_resource_version`
    into the existing, already-implemented
    `update_assignment_planned_hours` dual-optimistic-lock command (desktop
    API method + `TaskAssignmentPlannedHoursCommand` added this pass; the
    application-layer command itself already existed from before this
    session and needed no changes).
  - **Real finding surfaced while testing this**: the dual-lock only
    protects concurrent *allocation* changes across sibling assignments
    sharing one envelope (every call to `update_assignment_planned_hours`
    bumps `project_resource.version`, even though it writes no columns other
    than a version touch). It does **not** protect against the envelope
    itself being resized concurrently via `ProjectResourceService.update()`,
    which never touches `version` at all. This is a genuine, pre-existing
    inconsistency in the ProjectResource aggregate's own concurrency
    story — logged here as deferred cross-module debt (it lives in
    Resources/Planning's `ProjectResource.update`, not in Assignment), not
    fixed in this pass.
- `AssignmentRepository` gains `update_allocation_with_version_check(...)`,
  mirroring the existing `update_planned_hours_with_version_check` convention
  exactly. `TaskService.set_assignment_allocation` now takes an
  `expected_version` and uses the versioned write path — closing D2 for the
  one allocation-write path Task Detail actually uses. `accept_assignment`/
  `decline_assignment` were deliberately **not** given version checks: their
  own `response_status == "pending"` precondition is already a stronger,
  status-based conflict guard for that specific transition.
- `build_assignment_snapshot`/`serialize_period_summary` path: the Time
  Summary's primary "Logged" figure is now computed from the already-fetched
  task-scoped `task_entries` (sum of hours), not the resource-wide aggregate —
  closing D3. The resource-wide figure is kept only as an explicitly-labeled
  secondary "Resource total this period" line (it remains informative context
  for a person logging against several tasks in one period, but no longer
  masquerades as the task's own number). "Planned" and "Remaining" fields are
  added from the assignment's own `allocated_planned_hours`/`hours_logged`
  (both page-independent, authoritative, already-synced values — no new
  query needed) — closes the "Planned/Remaining" gap from Phase D §35 using
  data that was already correct and available, just not surfaced.
- The "Set Hours" action and its dialog are removed from the Assignment
  section's row actions (closing D4); the backend `set_assignment_hours`
  command/API/tests are left in place (no reference proof it is fully dead —
  it may still serve non-UI/import paths — so it is not deleted, only its one
  QML entry point is).
- Assignment row/inspector in QML now displays Planned Work and Remaining
  (Planned − Logged) alongside the existing allocation/logged display,
  read-only.

### H/I. Database/migrations

No schema changes required — every field involved (`allocated_planned_hours`,
`version`) already exists on `task_assignments` from prior migrations
(§2 of the investigation). No new indexes needed: all reads are single-row
(`get_assignment`) or already-indexed single-query batches. Nothing in this
pass touches the DB schema.

### J/K. Authorization / concurrency decision

No authorization changes: `set_assignment_allocation` already enforces
`task.manage` before the write; adding `expected_version` only adds a second,
orthogonal failure mode (stale-version conflict) on top of the existing
capability check, it does not change who is allowed to call it. Concurrency
decision, explicitly scoped: version-check added only to
`set_assignment_allocation` (the one reachable, genuinely-concurrent-edit-prone
write path); not added to `accept_assignment`/`decline_assignment` (already
guarded by status transition) or retrofitted onto `set_assignment_hours`
(being removed from the UI, not extended).

### L/M. QML design delivered

**Assignment** (extends the Repeater-based redesign already shipped in §40):
rows/inspector now show Planned Work and Remaining in addition to Allocation
and Logged; "Set Hours" removed from row actions; "Edit Allocation" dialog now
round-trips `version` and surfaces a clear "this assignment was changed by
someone else — reload and try again" error on conflict instead of silently
overwriting. The create dialog (`TaskAssignmentEditorDialog.qml`, create mode)
gained an optional "Planned Work (h)" field; a new "Edit Planned Work" row
action opens `TaskAssignmentPlannedHoursDialog.qml` for editing it afterwards,
both wired through the existing dual-version-check command.

**Time**: Summary tab now labels the task-scoped figure as "Logged" (with
"This period" broken out from it) and adds "Planned"/"Remaining"; the
previously-unlabeled resource-wide number is now explicitly "Resource total
this period" so it can no longer be mistaken for the task's own hours.
Capture/Ledger tabs and the `[ Open Timesheets ]` CTA are unchanged — already
correct from §40's removal of the duplicate Workflow tab.

### N. Timesheets ownership — reconfirmed intact

Re-verified (independently, via a fresh full-stack trace rather than trusting
the prior session's own account): submit/approve/reject/lock/unlock/reopen
exist only in the platform `timesheet_periods.py`; `pm_time_controller.py`
exposes only add/update/delete entry slots with an explanatory comment on why
period actions are deliberately absent; `TasksTimeEntriesSection.qml` has
exactly 3 tabs and no dead signal/handler referencing the removed Workflow
tab. There is no separate "My Time" workspace distinct from "Review Queue" in
the code as it exists today — both live in one combined
`project_management.timesheets` route/page — and the navigation layer
(`navigateToRoute`) does not currently support passing context params, so the
existing simple bare-route CTA (built in §40) is confirmed to already be the
correct, "don't invent a second state system," choice per the user's own
prior explicit decision.

### O. Performance — before/after

No new queries added anywhere in this pass's scope: the "Planned/Remaining"
figures reuse data already loaded on the same assignment fetch; the
task-scoped "Logged" figure reuses `task_entries`, already fetched by
`build_assignment_snapshot` for a different purpose (it was being counted but
not summed). Net query count for Task Detail Assignment/Time load is
unchanged.

### P. Duplication removed

None newly found beyond what §40 already removed (Reservations/Procurement
duplicates, Workflow tab). This pass's only removal is the "Set Hours" UI
entry point (D4).

### Q. Deferred cross-module debt (explicitly out of scope for this pass)

- `task_query.py` N+1s (`list_tasks_for_resource`, `list_assignments_for_resource`,
  `list_assignments_for_tasks`) — serve Resources workspace and Dashboard.
- Dashboard's `widgets/upcoming.py`/`widgets/professional.py` per-task
  `list_assignments_for_task` loop (one query per visible task) — Dashboard-owned.
- Timesheets' `list_time_entries_for_resource_period` O(allocations) pattern
  and the Review Queue's per-entry/per-period `project_name_for_id` N+1s —
  Timesheets-owned.
- QML-only `canCreate` gating on Task Detail create-buttons (Assignment's
  "Assign Resource" and Dependencies' "Add Dependency" alike) having no
  capability check — safe today (server fail-closed) but real UX debt;
  fixing it properly means auditing every Task Detail create-button, not just
  Assignment's.
- `ProjectResource.update()` (envelope resize) not incrementing `version` at
  all, unlike `touch_version_with_check` — a real inconsistency in the
  ProjectResource aggregate's own concurrency story, discovered while testing
  the planned-hours dual-lock. Lives in Resources/Planning, not Assignment;
  not fixed in this pass. (Editing `allocated_planned_hours` from Task
  Detail itself is no longer deferred — see §E/F/G — it shipped this pass.)
- No forecast/finance-side consumption of time entries was found (only an
  actuals pipeline off `TimesheetPeriodStatus.APPROVED`) — noted for the
  record, not a defect.

### R. Test evidence

Full `src/tests/project_management` + `src/tests/pm` suite: **904 passed**,
13 failed — the same pre-existing, unrelated set confirmed via `git stash`
earlier in the session to exist on unmodified HEAD (`test_baseline_lifecycle.py`
×7, `test_constraint_validator.py` ×5, `test_financial_desktop_forecast_delegation.py`
×1). New/updated coverage for this pass:
`test_assignment_time_task_detail_r43.py` (21 tests — version-check
concurrency, allocation-then-envelope create/edit including planned-hours
at creation, task-scoped vs resource-wide Time Summary regression, the
removed "Set Hours" affordance). One real regression was found and fixed
mid-pass (a hand-rolled QML-presenter test fake missing the 4 new
snapshot fields, causing 5 test failures) — production code was made
defensive (`getattr` with fallback) rather than only patching the fake,
since a snapshot-shape mismatch should degrade gracefully, not crash, in
any caller. Not committed.

## 44. R4.3 Resource → ProjectResource → TaskAssignment → Time — enterprise planning/capacity upgrade

Baseline for this pass was the current-state audit already on record (three
independent deep-dive traces of Resource/calendar/capacity,
ProjectResource/TaskAssignment/planned-hours/allocation-percent, and
Time/Finance/Scheduling/Workload/Authorization/QML — findings folded into
this section rather than repeated). Nothing was re-audited from scratch;
every change below was verified against the exact current code before being
made. Not committed.

**Scope decision, stated up front**: this pass delivered the ProjectResource/
TaskAssignment/Time backend hardening and reconciliation work in full, plus a
light, real (not placeholder) QML wiring pass for the Projects → Resources
surface. It explicitly did **not** deliver the single largest, riskiest item
in the brief — consolidating onto one calendar-based capacity authority and
migrating the assignment-preview/overallocation/leveling calculation off the
flat `capacity_percent` + naive Mon–Fri model. That item is real, well-
scoped by the audit, and deliberately deferred to its own pass — see §15/§20
below for why and what the concrete next steps are. Exit-gate items #1
("one authoritative capacity source") and #2 ("calendar resolution wired in
production") are therefore **not met** by this pass; every other applicable
item is.

### 1. Final capacity authority — NOT consolidated this pass (deferred)

The audit found four independent, non-integrated capacity/utilization
calculators (`ResourceCapacityCalculator`/`EnterpriseResourceAvailabilityService`
— calendar-derived, correct semantics, but no production caller feeds it real
assignment data; `ResourceAvailabilityService` — allocation_percent vs. flat
`capacity_percent`, never constructed in production; `ResourceLoadEngine` —
peak-concurrent allocation_percent, feeds a real Dashboard/Scheduling KPI;
`PortfolioResourcePoolService` — portfolio-wide, own SQL read model). None of
these were consolidated, deleted, or rewired this pass. The two confirmed
dead-wiring bugs found by the audit (the assignment-preview's
`resource_availability_service` never being passed by
`desktop_api_builder.py`, and `ResourcesCalendarSection.qml`'s
`enterpriseCapacity` binding never being populated because the wired
`EnterpriseResourceAvailabilityService` has no `check_availability` method)
are both **still present** — deliberately not patched in isolation, since a
narrow fix would either (a) wire the wrong calculator in for a quick win, or
(b) require redesigning the assignment-preview/overallocation call path
anyway once the right calculator is chosen — better done once, correctly, as
its own pass. See §15/§20.

### 2. Resource.capacity_percent semantics — unchanged, already correctly defined

Confirmed the audit's finding still holds and needed no code change: the ORM
comment on this column (`orm/resource.py`) already states the intended
"macro capacity modifier" semantics precisely as this brief's §5 describes —
`effective_capacity = calendar_capacity × capacity_percent / 100` — the
definition already exists in a comment; what's missing is the calendar side
of that formula actually being computed anywhere real (see §1).

### 3. Calendar precedence — unchanged, real, but still disconnected from assignment/overallocation

`EnterpriseCalendarResolver`'s org→site→department→employee/resource
precedence chain is real, tested, and untouched by this pass. It remains
unconnected to `_check_resource_overallocation`, the assignment-preview
formula, and both leveling engines, all three of which still compute
capacity from `Resource.capacity_percent` alone plus a plain Mon–Fri day
model. Not migrated this pass (see §15).

### 4. ProjectResource.planned_hours semantics — reconfirmed, formalized in code

Reconfirmed as the project-level control envelope (not a work estimate, not a
capacity reservation in the calendar sense). Its three real consumers
(the WBS-distribution ceiling, the envelope-shrink guard, and Finance's
`LaborCostEngine` whole-envelope planned-cost row) are unchanged in meaning;
what changed is that the ceiling/shrink-guard arithmetic that used to be
written out independently in two files is now one shared, tested policy
module (see §9).

### 5. TaskAssignment.allocated_planned_hours semantics — reconfirmed, unchanged

Reconfirmed as the task/WBS share of the ProjectResource envelope; no
semantic or field change this pass beyond what §43 already shipped (create-
time + edit-time UI, version-checked edit).

### 6. allocation_percent semantics — reconfirmed, unchanged, NOT tied to hours this pass

Reconfirmed as a bare percentage with no calendar-hours meaning anywhere in
the codebase (`_check_resource_overallocation` compares it against
`Resource.capacity_percent`, another bare percentage — never multiplied by
real hours). Not changed this pass; doing so is exactly the deferred §1/§15
work.

### 7/8. Actual-hours authority and ProjectResource reconciliation — NEW this pass

The audit's clearest, single most concrete gap — "how much of this resource's
project envelope has actually been burned" had no code answer at all — is now
answered authoritatively:

- New shared policy module,
  `application/common/project_resource_envelope_policy.py`: 
  `allocated_to_tasks_hours`, `actual_hours_total`,
  `resource_assignments_in_project` (the one bounded query — via the
  already-batched `AssignmentRepository.list_by_tasks`, never a per-row loop
  or a "currently loaded page" sum), `envelope_status` (`UNALLOCATED` /
  `PARTIALLY_ALLOCATED` / `FULLY_ALLOCATED` / `OVERALLOCATED`), `burn_status`
  (`NOT_STARTED` / `WITHIN_PLAN` / `NEAR_PLAN` / `OVERRUN`, reusing the
  already-established 90%-near-capacity threshold from
  `resource_load_engine.py`'s utilization bands rather than inventing a new
  one), `planned_burn_percent`, and the two invariant-enforcing functions
  `require_can_allocate_task_hours`/`require_can_reduce_envelope`.
- `ProjectResourceQueryMixin.get_usage(project_resource_id)` (application
  layer) returns a new `ProjectResourceUsageFact`
  (`contracts/reads/projects/models.py`): `planned_hours,
  allocated_to_tasks_hours, unallocated_planned_hours, actual_hours,
  remaining_project_hours, planned_burn_percent, task_assignment_count,
  envelope_status, burn_status, version`. `actual_hours` sums
  `TaskAssignment.hours_logged` — itself already the TimeEntry-derived,
  all-time-synced authoritative total per assignment — across every
  assignment for that resource in that project, so this is the real
  `TimeEntry → TaskAssignment → ProjectResource` rollup the audit found
  missing, in one step, with no new mutable counter persisted anywhere
  (matches the "query aggregate, not a second stored truth" instruction).
  `remaining_project_hours`/`unallocated_planned_hours` are signed, not
  clamped — an overrun or an over-allocation shows as a real negative
  number, not a silent zero.
- Desktop-facing: `ProjectResourceUsageDesktopDto` +
  `serialize_project_resource_usage` + new desktop API method
  `get_project_resource_usage(project_resource_id)`.

### 9. Envelope invariant — centralized to one semantic authority

Both independent implementations of "SUM(TaskAssignment.allocated_planned_hours)
≤ ProjectResource.planned_hours" — the assignment-side check in
`application/tasks/commands/assignment.py` and the ProjectResource-side
shrink guard in `application/resources/commands/project_resource_commands.py`
— now delegate to the shared `project_resource_envelope_policy` module
instead of each recomputing the sum independently. The assignment-side
query was also upgraded in the process: it used to sum via
`AssignmentRepository.list_by_resource(resource_id)` filtered by
task-id-in-project (a wider, less-scoped query pulling a resource's
assignments across every project them're on before filtering), now uses the
same batched, project-scoped `list_by_tasks` the ProjectResource side
already used — one less query shape for the same invariant, and a
marginally tighter one.

### 10. Capacity-overload invariant — NOT migrated to calendar capacity this pass

`_check_resource_overallocation` (the assignment-creation/edit-time
warn/strict check) is unchanged: still flat `capacity_percent` + naive
Mon–Fri. Deliberately not touched — see §1/§15. It remains correctly
*distinct* from the envelope invariant in §9 (this was already true before
this pass and stays true — a project-envelope violation and a resource-
capacity overload are still two different error codes,
`PROJECT_RESOURCE_HOURS_OVERALLOCATED` vs `RESOURCE_OVERALLOCATED`/the warn
path, never collapsed into one generic result).

### 11. Concurrency — ProjectResource is now version-checked; TaskAssignment unchanged (already done in §43)

`ProjectResourceRepository` gains `update_with_version_check(pr, *,
expected_version)`, implemented exactly like `TaskAssignment`'s established
convention (a single atomic `UPDATE ... WHERE id=? AND version=?` via the
shared `update_with_version_check` helper). `ProjectResourceCommandMixin.update`
takes an optional `expected_version` (defaults to `None` → falls back to the
old plain-overwrite `update()`, so no existing caller breaks); when supplied,
a stale write raises `ConcurrencyError(code="STALE_WRITE")` — the same
structured-conflict contract already used everywhere else in this module,
not a generic failure. Desktop DTO/command both carry `version`/
`expected_version` now. `TaskAssignment` concurrency is unchanged (already
version-checked for both allocation and planned-hours edits per §43).

### 12. Deletion / history policy — application-layer guards added, no schema change

Chosen model, per the audit's own framing: **guard before touching the
cascade, not instead of eventually revisiting it**. Two new, symmetric
guards, both raising a structured `BusinessRuleError` rather than silently
proceeding:
- `ProjectResourceCommandMixin.delete` now checks whether any of that
  resource's assignments on the project have `hours_logged > 0`; if so,
  raises `PROJECT_RESOURCE_HAS_HISTORICAL_ACTUALS` and does not delete.
  Unused/no-actuals ProjectResources still hard-delete exactly as before
  (matches "unused → hard delete may be allowed").
- `TaskAssignmentMixin.unassign_resource` now checks the assignment's own
  `hours_logged`; if `> 0`, raises `ASSIGNMENT_HAS_HISTORICAL_ACTUALS` and
  does not delete (previously it unconditionally deleted the assignment
  *and* cascade-deleted its time entries — this is a real, deliberate
  behavior change, confirmed via the one existing test that asserted the old
  behavior, which has been rewritten into two tests: one proving the
  no-actuals case still succeeds, one proving the with-actuals case is now
  blocked and nothing is touched).

**Explicitly not done this pass**: the underlying DB `ON DELETE CASCADE` on
`task_assignments.project_resource_id` (and `time_entries.assignment_id`) is
unchanged. The guards above make it unreachable through the two mutation
paths audited, but a determined lower-level deletion (e.g. deleting the
`Resource` itself, or a future new code path) would still cascade. Migrating
the FK behavior itself (`CASCADE` → `RESTRICT`/soft-lifecycle) needs a
dedicated forward migration plus a decision on `ProjectResource`/
`TaskAssignment` deactivation UX first — flagged as a deferred follow-up,
not attempted here given no schema change was required to close the actual
gap this pass targeted (both audited mutation entry points).

### 13. Authorization changes — Time gains project scoping

Added a template-method hook, `_require_time_project_scope(*, work_allocation,
work_owner, operation_label)`, to the **shared platform**
`TimesheetSupportMixin` (default no-op — this mixin also serves
`maintenance`'s `MaintenanceLaborService`, which has no "project" scoping
concept at all, so the base implementation must stay a safe no-op). Called
from the three real mutation entry points
(`add_work_entry`/`update_time_entry`/`delete_time_entry` in the platform's
`timesheet_entries.py`) right after the work-allocation context is resolved.
`project_management`'s `TimesheetService` overrides the hook to resolve the
project via the already-existing `_resolve_entry_project_id` helper and
enforce `require_any_project_permission(..., ("time.manage", "task.manage"))`
— closing exactly the gap the audit found (a user with only the *global*
time.manage/task.manage capability could write time against any project's
tasks, unlike every other Task/ProjectResource mutation in this module,
which already double-checks global + project scope). Read paths
(list/query) were deliberately left global-only: the Review Queue is
correctly cross-project-by-design for reviewers (it already restricts to
`allowed_project_ids` when the session is project-restricted), so adding
project-scoping to the shared read helpers would have been wrong, not just
unnecessary. Full Maintenance suite (all its tests) re-run after this change
with zero failures, confirming the hook is a genuine no-op for that module.

### 14. Finance control-total semantics — verified, no double-counting, no code change needed

Audited both Finance paths side by side: `LaborCostEngine`'s planned-row
reads `ProjectResource.planned_hours` (the whole envelope) directly;
`PlannedCostService` reads `TaskAssignment.allocated_planned_hours` (the
WBS-distributed share) for its per-line output plus a separate, explicitly-
labeled `PROJECT_RESOURCE_ENVELOPE_MISSING`/`_OVERALLOCATED`/etc. diagnostic
comparing the two. Neither path adds envelope + distribution together
anywhere; they are presented as two different rows/diagnostics, never summed.
No change was needed to prevent the double-counting the brief warns about —
it wasn't happening — but this is now explicitly documented (here, and in
the module docstrings already present) rather than left as tacit knowledge.

### 15. Scheduling integration status — deferred, documented as an R4.4-blocking item

Per the brief's own explicit allowance (§21 of the request): the leveling
engines' capacity input (`Resource.capacity_percent` + plain working-day
iteration, read directly from `TaskAssignment.allocation_percent`) was
**not** migrated to a calendar-based capacity service this pass. Reasoning:
- Both leveling engines (`leveling_mixin.py`, `resource_leveling_engine.py`)
  don't just *read* capacity, they **actively reschedule real task dates**
  in an iterative loop (up to `max_iterations`). Changing their capacity
  source changes real scheduling outcomes, not just a displayed number —
  this needs its own dedicated before/after test matrix (§44 of the
  request: normal/non-working/holiday/exception/part-time/employee/
  project/resource-calendar/capacity_percent<100/overlapping-tasks), which
  doesn't exist yet for either engine against calendar data.
  Attempting it inside an already-large mixed pass risked a low-confidence,
  under-tested change to behavior with real scheduling consequences.
- CPM itself remains confirmed fully resource-independent (unchanged,
  verified again by grep — zero references to allocation/hours/
  ProjectResource in `scheduling_engine.py`).
- What *was* done to unblock this without touching Scheduling: the shared
  envelope/reconciliation policy module (§9) and the `ProjectResourceUsageFact`
  reader (§7/8) are the "shared capacity abstraction" building blocks a
  future calendar migration would compose with — they're already
  application-layer, already tested, and don't need to change shape when
  the leveling engines eventually move onto real calendar capacity.

**Concrete next-step plan for the deferred capacity-authority migration**
(§1/§3/§6/§10/§15, to be done as its own pass): (1) pick
`ResourceCapacityCalculator`/`EnterpriseResourceAvailabilityService` as the
one authority (it already has the correct "never stored, computed on
demand from resolved calendar contexts" semantics — the other three
calculators are display/reporting consumers, not competing sources of
truth); (2) wire real `assigned_hours_by_date` into it from
`TaskAssignment` data (currently no caller supplies this); (3) fix the two
confirmed dead-wiring bugs (`desktop_api_builder.py` never passing
`resource_availability_service`; `EnterpriseResourceAvailabilityService`
missing the `check_availability` method `availability_builder.py` calls);
(4) migrate `_check_resource_overallocation` to call it, preserving the
existing warn/strict policy toggle exactly (§18 of the request); (5) only
then migrate the leveling engines, with the full calendar test matrix in
place first; (6) leave `ResourceLoadEngine`/`PortfolioResourcePoolService`
as downstream aggregation consumers of the same authority rather than
deleting them (§22/§23 of the request already permits this).

### 16. QML — Projects → Resources: real, light wiring (not a placeholder)

`ProjectsResourcesSection.qml`'s existing edit dialog (no new
inspector/redesign — see scope decision) now: labels the field "Project
planned hours" with the exact helper text the brief specifies ("Total
planned work for this resource across this project"); on open, calls the
new `getProjectResourceUsage` controller slot and shows read-only
"Currently distributed to tasks / Remaining unallocated / Actual worked
(... remaining vs. plan)" context sourced from the real
`ProjectResourceUsageFact`, not computed in QML; round-trips `version` on
save and shows the exact required conflict copy ("This resource plan was
updated by another user. Refresh the latest values before saving again.")
with a Refresh action instead of silently overwriting or showing a generic
error; the delete-confirmation dialog now actually checks the mutation
result (previously ignored it entirely) and surfaces
`PROJECT_RESOURCE_HAS_HISTORICAL_ACTUALS` as a real section error instead of
appearing to silently no-op. `qmllint` clean (added to the guardrail
enumeration); no new business-rule computation in QML — every number shown
comes from the desktop API.

### 17/18. QML Task Assignment / Time — unchanged this pass

No changes beyond what §43 already shipped. The Assignment/Time inspector
redesign described in the brief's §54-70 (capacity preview cards,
project-context reconciliation block inside Task Detail, tooltips,
responsive table/inspector layout) is explicitly deferred to a follow-up
QML-focused pass, per the brief's own §47 sequencing ("only after backend
is sound, update QML") — the backend facts that pass would consume
(`ProjectResourceUsageFact`, the centralized envelope policy) are now in
place and tested, so that follow-up isn't blocked on anything backend-side.

### 19. Performance results

Fixed, with `list_by_ids` added to `ResourceRepository` (contract + impl,
mirroring the existing `AssignmentRepository.list_by_ids` convention):
`ResourceQueryMixin.list_for_project_workspace`/`list_for_task_workspace`
(were: whole-tenant `.list()` + Python filter); `LaborCostEngine
.calculate_project_labor_details`'s per-resource `.get()` loop; both leveling
engines' `_build_resource_name_map` per-assignment `.get()` loop (previously
recomputed, with the N+1, on **every** leveling iteration — up to 60 per
run). **Explicitly not fixed this pass** (documented, not silently
dropped): the Resources-workspace assignment builder's per-distinct-project
`project_service.get_project()` loop, and the Financials workspace query's
whole-tenant `resource_repo.list()` call for a name-lookup map — both real,
both bounded by a small N (distinct projects a resource has tasks in;
resources on one project's finance view) relative to the ones fixed, and
lower priority than finishing the backend/QML/authorization work with the
remaining pass budget.

### 20. Deferred R5 Workload Management features

Nothing in R5 Workload Management UI was started (exit-gate #30 honored).
Explicitly noted as now-unblocked-when-picked-up: `ProjectResourceUsageFact`
and the envelope policy module are the right building blocks for a future
resource-workload view; they were designed as reusable application-layer
facts/policy, not Projects-workspace-specific, for exactly that reason.

### Test evidence

New test file `test_r43_resource_capacity_upgrade.py` (24 tests): ProjectResource
version-checked update success/stale-conflict/backward-compatible-without-version;
`ProjectResourceUsageFact` reconciliation across 3 tasks with mixed
planned/actual (including a page-independence check and a not-found check);
`Resource.is_active` rejection at assignment creation; both deletion guards
(blocked-with-actuals, allowed-without); the dead-bridge-path removal now
failing closed; project-scoped time-authorization allow/deny via the real
auth stack (`login_as` + `access.assign_scope_grant`, not a mocked
permission check); desktop-API-level coverage for both the usage-fact
endpoint and `expected_version` forwarding/conflict. One existing test
(`test_unassigning_resource_removes_associated_time_entries`) was rewritten
into two tests reflecting the intentional behavior change in §12. Full
`src/tests/project_management` + `src/tests/pm` + `src/tests/platform` +
`src/tests/maintenance` regression run: **1911 passed, 23 failed, 12 errors**.
None of the failures/errors touch anything this pass changed — verified by
sampling (`test_enterprise_calendar_resolver.py`, the most calendar-adjacent
and therefore most suspicious-looking failure set, since this pass edits
calendar-adjacent code) via `git stash`: the exact same 3 errors reproduce
against unmodified HEAD with every change from this pass stashed out. The
remainder (site/org desktop API, RLS bootstrap classification, calendar
shift-pattern/exception fixture tests) are unrelated subsystems this pass
never touched; this was simply the first time this session the full
`src/tests/platform` suite was run end-to-end, so no prior-session baseline
existed for it the way one already did for `project_management`/`pm`. Not
committed.

### Mid-pass follow-up (A–D): the two dead capacity paths, warn/strict proof, the Resource-deletion gap, and query-count evidence

While the above was being written up, four additional explicit requirements
arrived responding directly to the current-state audit. All four are now
done — this supersedes §1/§12/§15/§19's earlier "deferred" framing for the
specific items listed below (the larger calendar-authority-consolidation
deferral in §1/§3/§6/§10/§15 still stands; what changed is that the two
*dead-wiring* bugs specifically are no longer dead).

**A. Both dead capacity/availability paths fixed, not just one.** Root-caused
both properly before touching either:
- **Task assignment preview**: `desktop_api_builder.py` never passed a
  `resource_availability_service` into the Tasks desktop API factory at all
  — the param existed, nothing was wired to it. Fixed by constructing a real
  `ResourceAvailabilityService` (percent-based: `allocation_percent` vs.
  `Resource.capacity_percent` — deliberately the *same* model
  `TaskValidationMixin._check_resource_overallocation` already enforces, so
  the preview predicts what the real enforcement will do, rather than
  showing a different, calendar-based number while enforcement itself
  stays percent-based per the still-standing §1/§15 deferral) in the
  composition root and threading it through
  (`project_registry.py` → `ProjectManagementServiceBundle` →
  `app_container.py`'s services dict, under a new
  `"task_assignment_availability_service"` key, deliberately *not*
  overwriting the existing `"resource_availability_service"` key that
  already (correctly, per its own comment) points at the calendar-based
  `EnterpriseResourceAvailabilityService` for whenever that migration
  happens → `service_resolver.py` → `desktop_api_builder.py`). Its own
  confirmed N+1 (`_compute_window`'s per-task `task_repo.get()` loop) was
  fixed in the same change, via a new `TaskRepository.list_by_ids()`
  (contract + impl, mirroring the existing `AssignmentRepository`
  convention).
- **`ResourcesCalendarSection.qml`'s "Derived Capacity" card**: re-examined
  the actual QML rather than assuming — this card is already correctly
  gated (`visible: root._hasEnterpriseData`) and was never the thing
  rendering fake zeros; since `enterpriseCapacity` was always `{}`, it
  stayed correctly hidden. The thing actually rendering misleading zeros in
  production was the **fallback** "Allocation Summary" card
  (`visible: !root._hasEnterpriseData`), because `build_resource_availability`
  called `availability_service.check_availability(...)` on whatever service
  is registered at `resolved.availability_service` — the calendar-based
  `EnterpriseResourceAvailabilityService`, which has no such method,
  silently swallowed by a blanket `except Exception: return None`. Fixed
  the same way as the Tasks side: `build_project_management_resources_desktop_api`
  now receives the new real `ResourceAvailabilityService` too (which does
  have `check_availability`), so the "Allocation Summary" card now renders
  genuine allocation data instead of a None-triggered all-zero fallback.
  Wiring the calendar-based "Derived Capacity" card itself with real
  assigned-hours data remains deferred (a new
  `compute_resource_capacity_from_assignments` helper was written and is
  ready for that follow-up — see below — but completing that card's full
  property chain, which doesn't exist at all today, not even a broken one,
  is closer to a small new feature than a wiring fix, and is left for the
  dedicated capacity-authority pass in §15).
- **A real, independent bug surfaced by actually exercising the
  now-live preview end to end** (not caught by the existing
  characterization test, which fed the formula whatever window data it
  wanted directly): `build_assignment_preview`'s conflict-project-name
  resolution read a `project_name` attribute that `Task` domain objects
  don't have, so `conflict_projects` was *always* empty regardless of real
  data — a second, independent reason the preview looked "dead." Fixed by
  passing the API's already-existing, already-scoped, already-batched
  `_project_name_by_id()` lookup into the builder and resolving by
  `project_id` instead. This also directly answers the audit's privacy
  question (§20 of the request: separate the capacity result from
  conflict-detail disclosure) — the lookup is scoped to what the current
  API instance's `project_service` calls resolve, so a conflict in a
  project the batched lookup doesn't include simply omits that project's
  name (the overallocation percentage still surfaces) rather than needing
  a second, separate authorization check bolted on top. Added a test
  (`test_da0_assignment_preview_omits_conflict_names_outside_authorized_project_scope`)
  proving exactly that omission behavior, alongside updating the one
  existing characterization test that had been asserting the broken
  attribute-based lookup.

**B. Warn vs. strict overallocation policy, both branches now proven.**
`_check_resource_overallocation`'s policy is a plain instance attribute
(`self._overallocation_policy`, set once from `PM_OVERALLOCATION_POLICY` at
service construction) — no env-var gymnastics needed in tests, just set it
directly on the constructed service. Three new tests:
warn-mode-sets-a-warning-and-proceeds, strict-mode-rejects-with-
`RESOURCE_OVERALLOCATED`-and-creates-nothing, and — to prove strict isn't a
blanket rejection — strict-mode-still-allows-a-genuinely-non-conflicting
allocation.

**C. Historical-actuals guard extended to a third, more dangerous silent
path.** The audit's framing ("Establish the domain lifecycle first, then
align: commands; repository behavior; FK delete behavior; QML actions;
tests") prompted re-checking every deletion path, not just the two already
guarded (§12) — and found `ResourceCommandMixin.delete_resource` **explicitly,
unconditionally** looped its assignments calling
`time_entry_repo.delete_by_assignment()` before deleting each assignment,
completely bypassing the invariant just established on the more targeted
ProjectResource/TaskAssignment paths. This is arguably the more dangerous
of the three, since deleting a Resource is a much more casual-looking
action than either of the other two. Added the identical guard
(`hours_logged > 0` on any of the resource's assignments →
`RESOURCE_HAS_HISTORICAL_ACTUALS`, deletion refused) and rewrote the one
existing test that asserted the old unconditional-cascade behavior into the
same allowed/blocked pair used for the other two guards. On the DB
FK-cascade question itself (`ON DELETE CASCADE` on `task_assignments
.project_resource_id`/`time_entries.assignment_id`): confirmed, and still
deliberately not changed at the schema level — a blanket `RESTRICT` would
incorrectly also block the legitimate "assignments exist but none have
actuals" case all three guards already allow, since a database FK
constraint cannot conditionally inspect `hours_logged`. That distinction is
inherently an application-layer invariant; the three guards are now the
complete, aligned set of application-layer entry points that could
otherwise reach the cascade, which is the enforceable form of "align
commands/repository behavior" the request asked for. Not treated as
optional — all three now share the same reasoning, the same error-code
pattern, and the same test shape.

**D. Query-count evidence added for the paths this pass actually touched.**
Not a general repository-optimization sweep (explicitly out of scope, per
the request's own instruction) — two targeted regression tests, reusing the
established class-method-patching counter pattern from
`test_approved_time_work_allocation_n_plus_one.py`: leveling's
`_build_resource_name_map` now issues one `ResourceRepository.list_by_ids()`
call and zero `.get()` calls for N distinct resources (previously one
`.get()` per distinct resource, recomputed every leveling iteration); the
availability service's task lookup now issues one `TaskRepository.list_by_ids()`
call and zero `.get()` calls. The two remaining, smaller, already-documented
N+1s from §19 (Resources-workspace per-project `get_project()` loop;
Financials' whole-tenant resource list for a name map) were not touched by
anything in this follow-up and remain deferred as originally scoped.

**Test evidence for this follow-up**: `test_r43_resource_capacity_upgrade.py`
grew from 13 to 21 tests; `test_pm_desktop_adapter_da0_characterization.py`
gained one test and had one updated to match the corrected conflict-name
resolution; `test_collaboration_import_timesheet_regressions.py`'s resource-
deletion test was rewritten the same way the assignment/project-resource
ones already were. Full file passes: 21/21 and 32/32 respectively. Full
`src/tests/project_management` + `src/tests/pm` regression re-run in
progress at time of writing — see the following entry. Not committed.
