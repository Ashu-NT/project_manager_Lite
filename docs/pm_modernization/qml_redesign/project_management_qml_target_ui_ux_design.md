# Project Management Target UI/UX Design

Status: R0.1 approved; behavior-preserving R0.5 complete; target redesign not started  
Depends on: `project_management_qml_existing_state_audit.md`  
Target: maintainable enterprise desktop PM at 1024x768 and larger

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
| People & Time | Resources, Timesheets | organization/global plus active project |
| Finance | Financials | active project required |
| Governance | Register, Collaboration | global or active project |

The route target is one canonical Project Management module/workspace route. Inside that route, PM-local navigation presents the six approved destinations, with secondary navigation inside Work, People & Time, and Governance. The six destinations must not become six unrelated global application-drawer entries unless implementation proves the shell cannot host a unified PM module route.

The ten existing route IDs remain only as migration and deep-link compatibility routes. While they exist, each resolves into the canonical PM workspace with the corresponding PM-local destination selected. They are removed only after callers, saved links, tests, and shell dependencies migrate. R0.5 preserves their current behavior; canonical-route implementation belongs to R2.

```text
Project Management
|-- Overview
|-- Portfolio
|-- Work
|   |-- Projects
|   |-- Tasks
|   `-- Planning
|-- People & Time
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

### 6.7 People & Time

```text
+--------------------------------------------------------------------------+
| People & Time: Resources | My Time | Review Queue                        |
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

Use available content width after the shell drawer, not window width.

| Content width | Target behavior |
|---:|---|
| below 760 | compact toolbars; no inspector; section rail becomes selector; nonessential table columns hidden through presets |
| 760-1179 | full list/table; no persistent inspector; two visible context actions plus More |
| 1180-1519 | optional 320-pixel inspector; fixed section rail; two-column dashboards |
| 1520+ | 360-pixel inspector and wider analytics grids; never stretch form text excessively |

1024x768 acceptance criteria:

- no horizontal clipping of required actions;
- no dialog exceeds available width/height;
- table always retains identity and status columns;
- project and section context remain visible;
- all actions are reachable through overflow;
- scroll ownership is unambiguous, with no nested full-page flickables.

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
Status: complete on 2026-08-14. All 23 guarded candidates were proven dead and removed; the ten route IDs and all target product decisions remain unchanged. Automated route/dialog/offscreen, task-time, shared primitive, adapter/pagination/event, architecture, and performance gates show no attributable regression. R1 is now in progress; R1.2 shared sorting ownership is complete.

### R1 - Query integrity, truthful controls, and deny-safe capability presentation

Objective: remove no-ops, add explicit table sorting modes, implement server sort contracts, replace Collaboration/Timesheet partial queries, and replace fail-open capability presentation with deny-safe, capability-complete UI state.  
Affected: shared DataTable, Projects, Tasks, Scheduling, Resources, Register, Timesheets, Collaboration, Portfolio, Dashboard, Finance collection readers.  
Gate: no PM control implies unsupported behavior; query tests prove totals and stable ordering; permission lookup absence/failure never advertises an unauthorized action.
Status: in progress. R1.2 sorting ownership, R1.3 server-sort infrastructure,
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
remain authoritative. R1.9 is now closed; R2 has not started.

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

### R3 - Overview and Portfolio

Objective: build the new analytics shell and replace Portfolio's fixed bottom panel with focused tabs/work surfaces.  
Excludes: unbacked rebalance.  
Gate: global/project totals are query-correct and performance stays within agreed budgets.

### R4 - Work

Objective: add the responsive catalog/inspector pattern to Projects and Tasks and the target Planning console.  
Dependencies: inspector and action-overflow primitives.  
Gate: list state survives full detail/back; 1024 and keyboard paths pass.

### R5 - People & Time

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
Gate: the canonical route, remaining compatibility routes, QML engine, dialogs, controllers, architecture, PM workflows, and visual acceptance checks pass.

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

The target is complete when one canonical PM module route provides the six approved PM-local destinations, compatibility routes are retired after dependency migration, users move from portfolio to project to task without implicit context changes, every visible control is real, scalable lists use authoritative queries, permission presentation is deny-safe, Timesheets defaults by capability while supporting capture and review, Finance exposes approved PM-owned commands without crossing Accounting boundaries, and the workspace remains keyboard-accessible and usable at 1024x768.

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
presentation remain intact. R1.10 and R2 have not started.

The user committed the R1.9 source and focused test during verification; Codex
did not issue a commit. The closure-document update remains separate.
