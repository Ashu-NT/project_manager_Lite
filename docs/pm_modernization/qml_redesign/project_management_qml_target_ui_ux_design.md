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

## 22. R3.4 closure: Portfolio IA tabs

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

## 23. R3.5 closure: Portfolio interaction redesign

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

## 24. R3 -- Overview Scalable Queries

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
