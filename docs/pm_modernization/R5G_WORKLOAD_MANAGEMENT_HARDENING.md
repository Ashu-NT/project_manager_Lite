# R5G Workload Management Hardening

## 1. Status

**IMPLEMENTATION COMPLETE; EVIDENCE GATES OPEN.** R5A through R5F are the
approved implementation baseline. R5G adds no product capability and does not
change the approved information architecture. The integrated code defects found
in this pass are fixed and the targeted PM suites are green. R5G is not formally
closed because PostgreSQL runtime-role/RLS/query-plan evidence and parts of the
manual keyboard/dialog matrix require an appropriate runtime environment.

Current baseline findings:

- Server-authoritative Resource and Review Queue readers, paging, filtering,
  sorting, stable tie-breakers, scoped reads, optimistic TimesheetPeriod review,
  and lazy Resource Detail sections are present.
- Resource Inspector already distinguishes compact overlay and bounded side
  presentation from actual workspace content width.
- Review Queue now keeps its server table mounted and presents the selected
  period in one responsive Inspector authority: bounded side Inspector when the
  table retains 720 px, otherwise a right overlay.
- Resource and Review Queue filters use the approved application-standard
  centered modal dialog pattern. R5G validates that all fields and actions fit
  the minimum viewport; it does not introduce a separate popup pattern.
- SQLite scale and statement evidence exists for earlier phases. Both Resources
  and Review Queue now pass the integrated five-viewport QML matrix. PostgreSQL
  EXPLAIN/ANALYZE, runtime-role RLS negatives, and 50k fixtures remain open and
  must not be inferred.
- No R5G source change may weaken Task Detail -> Time, scheduling authority,
  ResourceKind semantics, tenant/organization scope, or deny-safe permissions.

## 2. Scope

R5G covers responsive composition, popup/dialog geometry, keyboard essentials,
bounded models, stale-state protection, SQL/statement evidence, tenant and
organization isolation, PostgreSQL RLS evidence, permissions, concurrency,
transaction atomicity, targeted invalidation, ResourceKind behavior, state
semantics, and cross-feature regressions for Resources and Review Queue.

Excluded: new navigation, matching/ranking, AI assignment, a Workload tab,
Time Entry redesign, Finance/R6, generic approval infrastructure, scheduling or
Gantt redesign, and broad R8 accessibility work.

## 3. Frozen IA

The PM-local navigation remains exactly:

```text
Workload Management
|-- Resources
`-- Review Queue
```

Resource Detail remains Overview, Capability, Availability, Projects,
Assignments, and Activity. Review Queue remains a projection over the platform
TimesheetPeriod aggregate. No persisted review aggregate exists.

## 4. Responsive Strategy

Responsive decisions use the QML workspace's actual content width after shell
and PM navigation chrome. Resource Inspector has one selected Resource ID and
switches presentation only: overlay on constrained content and bounded side
panel when at least 720 px of catalog width remains. A presentation fallback
must not overwrite durable user state or create another selection authority.

Review Queue will use the same principle: full-width table plus overlay Inspector
when constrained, and table plus bounded Inspector when enough table width
remains. No permanent compact side pane and no three-column layout are allowed.

## 5. Viewport Matrix

| Viewport | Resources | Review Queue | Evidence |
|---|---|---|---|
| 1024x640 | Pass | Pass | Runtime component geometry; compact Inspector mode |
| 1280x720 | Pass | Pass | Runtime component geometry; width-derived mode |
| 1366x768 | Pass | Pass | Runtime component geometry; width-derived mode |
| 1440x900 | Pass | Pass | Runtime component geometry; bounded wide mode |
| 1920x1080 | Pass | Pass | Runtime component geometry; bounded wide mode |

Evidence: `test_r5b_resource_workspace_runtime_geometry` and
`test_r5g_review_queue_runtime_geometry`; the required widths were rerun in the
targeted R5G validation. No layout-management, missing-type, or ReferenceError
warning was observed.

## 6. Resource Catalog Geometry

The catalog uses a shared server-mode DataTable and bounded pagination. The
current workspace computes Inspector mode from `ResourcesWorkspacePage.width`,
not global Window width. R5G must prove toolbar reachability and core columns at
all viewports and preserve useful catalog width when Inspector is selected.

## 7. Resource Inspector Geometry

One controller-owned selected Resource ID is authoritative. Compact mode uses a
right-side overlay Popup and wide mode uses the shared InspectorPanel at a fixed
token width. Opening Resource Detail closes the compact Inspector. The five
integrated viewports pass, `restoreTableFocus()` runs after close, and existing
request generations reject stale Resource selection results. Repeated
open/close memory observation remains a manual gate.

## 8. Resource Detail Geometry

The existing SectionDetailPage pins its contextual toolbar and section-scoped
messages. LazySectionLoader instantiates only the active section. Projects,
Assignments, and Activity are bounded/paged. Capability and Availability adapt
internally. R5G must verify one-column compact composition and no nested scroll
or clipped action regressions at 1024x640.

## 9. Review Queue Geometry

**R5G-UI-001 fixed:** row activation no longer replaces the queue with a
full-page `SectionDetailPage`. The queue remains mounted beside a bounded
Inspector when at least 720 px of table width remains; constrained widths use a
right overlay. `selectedQueuePeriodId` remains the sole selection authority and
the read/versioned command contracts are unchanged. The obsolete detail panel,
its `qmldir`, and unused detail-section metadata were removed.

## 10. Dialog / Popup Geometry

EntityDialog already clamps width and height, scrolls its form body, and keeps
header/footer actions pinned. Resource, skill, certification, lifecycle, and
review decision dialogs use shared dialog foundations.

Resource and Review Queue filters intentionally use the shared centered modal
dialog pattern used by the other PM filters. They retain staged Apply/Clear
semantics and shared viewport width clamping. Runtime geometry exposed that the
former 340/360 px widths were narrower than their 400/408 px content. Both now
use the established 440 px PM modal width and pass complete content/action-row
fit at 1024x640. Review Queue DateFields remain bounded by the dialog content.

## 11. Keyboard Essentials

Open evidence: DataTable Up/Down selection and activation, Inspector open/close
and focus return, local section navigation, Tab/Shift+Tab/Escape in all touched
dialogs/popups, safe Enter behavior, and focus retention after conflict/error.
R5G does not claim broad accessibility certification.

## 12. Large Data Fixtures

Required deterministic fixtures: Resources and TimesheetPeriods at 100, 1k,
10k, and 50k where practical; PERSON/CREW/EQUIPMENT; active/inactive; scoped
departments/sites; capability, staffing, assignment, calendar, activity, and
review-state variation. Existing 1k/10k fixtures will be reused rather than
duplicated. Fixture generation must remain test-only.

## 13. Resource Catalog Performance

Prior local SQLite evidence: 100 p50 4.14 ms/p95 8.08 ms; 1k p50 6.78 ms/p95
12.50 ms; 10k p50 40.48 ms/p95 41.29 ms; four statements including the scope
lease. These are baseline engineering numbers, not PostgreSQL R5G closure.

## 14. Resource Inspector Performance

Prior local SQLite evidence: p50 2.20 ms, warm p95 3.60 ms, cold 5.64 ms, two
statements including scope. The reader projects bounded scalar facts and
correlated counts, not child collections. R5G must rerun integrated evidence and
rapid-selection behavior.

## 15. Detail Section Performance

Capability is server-paged. Projects uses count/data plus authorization;
Assignments joins Task/Project and aggregates TimeEntry actuals; Activity reads
the shared indexed ledger newest-first. Prior evidence: 1k Projects 8.10 ms,
10k Assignments 74.75 ms, and 10k Activity 21.87 ms on SQLite. Availability is
bounded by a requested date range. PostgreSQL plans and integrated statement
budgets remain open.

## 16. Review Queue Performance

The queue uses a count, grouped page projection, and one project-attribution
query for current page IDs. Statement count is independent of page row count.
R5G must record 100/1k/10k/50k p50/p95 and verify the <=3 reader-statement target
under the agreed counting boundary.

## 17. SQL Query Plans

PostgreSQL plans are required for catalog default/search/filters, Inspector,
Availability, Projects, Assignments, Activity, queue default/filter/sorts, and
queue Inspector. SQLite query plans are characterization only. No PostgreSQL
plan result will be fabricated when a configured PostgreSQL test database is
unavailable.

## 18. Index Findings

Existing relevant indexes include tenant/resource scope indexes,
`idx_project_resource_resource`, `idx_task_assignments_resource`, TimeEntry
assignment indexes, and `idx_activity_related`. R5G adds or removes an index only
when PostgreSQL plan/cardinality evidence justifies it; column presence alone is
not evidence.

## 19. Memory / Object Bounds

Catalog, queue, Projects, Assignments, Capability, Activity, and timesheet entry
models retain only current pages. Resource request IDs invalidate Inspector,
detail, Projects, Assignments, Activity, and Availability responses on selection
change. Workspace controller domain subscriptions disconnect on QObject
destruction. Repeated route/Inspector/dialog observations remain open.

## 20. Scope Switching

Controller refresh hooks must clear selected IDs, Inspector/detail facts, lazy
section models, and request generations before loading a new tenant or
organization. Tests must prove old-scope IDs cannot be reopened and late results
cannot repopulate stale data.

## 21. Permission Matrix

Reads and actions remain backend-authorized. QML consumes exact `can*` facts and
unknown/loading/error states fail closed. Required matrices cover Resource read
and manage, capability read/manage, workload reads, project restrictions,
activity visibility, queue read, approve/return, and lock/unlock. Mid-session
revocation must be rejected at command time and remove protected state after
refresh.

## 22. RLS / Database Security

R5 operational tables include resources, resource_skills,
resource_certifications, project_resources, task_assignments, time_entries,
timesheet_periods, activity_entries, audit entries, and applicable outbox rows.
R5G requires a non-superuser/non-BYPASSRLS PostgreSQL role, runtime session
context, direct SELECT/INSERT/UPDATE/DELETE negatives, child-table bypass tests,
and recorded `pg_class`/`pg_policy` evidence. ORM scoping tests do not close this
gate.

## 23. Concurrency

Resource, ResourceSkill, ResourceCertification, and TimesheetPeriod mutations
carry expected versions. R5G reruns stale edit/delete/review scenarios through
integrated service/controller paths and confirms authoritative refresh after a
conflict.

## 24. Transaction Atomicity

Resource master, capability, and TimesheetPeriod review use caller-owned units
of work. Representative injected failures must prove mutation, audit, and
required outbox rollback together; post-commit events must not fire on rollback.

## 25. Event / Invalidation Integration

Resource controllers subscribe once and disconnect on destruction. Lazy section
refresh is guarded by selected Resource and loaded-state checks. R5G must verify
that capability, assignment, TimeEntry, and review changes invalidate only
relevant loaded views and that event bursts do not create refresh loops or
unbounded queries.

## 26. ResourceKind Integration

PERSON, CREW, and EQUIPMENT remain explicit Resource kinds. Employee-only UI and
identity logic applies only to PERSON. Capacity/Projects/Assignments/Activity
must not crash for CREW/EQUIPMENT. Timesheet eligibility remains active PERSON +
LABOR + EMPLOYEE/EXTERNAL; unsupported kinds must not enter review workflow.

## 27. Empty / Error / Loading States

Each surface must distinguish true empty, filtered empty, permission denied,
loading, and query error. A lazy Resource Detail section failure stays local.
Queue Inspector failure must preserve the table. Raw exceptions must not reach
QML.

## 28. Cross-Feature Scenarios

Required integrated scenarios: Resource master update, skill update,
certification expiry, capacity arithmetic, over-allocation, hidden Project,
Timesheet approval, stale reviewer, Task Detail Time, and organization switch.

## 29. Task Detail Time Regression

Task Detail -> Time remains its existing primary UI. R5 may consume TimeEntry
facts but must not relocate ownership or change its command/read contract.

## 30. R4.4 / R4.5 Regression

Targeted Resource Leveling, calendar, scheduling, and Gantt tests must pass.
R5G must not change CPM, leveling, Gantt, TaskAssignment, or calendar authority.

## 31. QML Runtime Warnings

Capture representative Resources and Review Queue navigation. R5-owned missing
properties, bad anchors, binding loops, stale-object access, and signal mismatch
are blockers. Generated type-metadata warnings must be classified rather than
silently ignored.

## 32. Static Tooling Results

| Tool | Result |
|---|---|
| Python compile | Open |
| Targeted qmllint | Open |
| git diff --check | Open |
| Repository lint/type tooling | Open/availability not yet checked |

## 33. Performance Evidence Table

| Surface | Fixture | Rows | p50 | p95 | SQL statements | Result / notes |
|---|---:|---:|---:|---:|---:|---|
| Resource Catalog | Prior SQLite | 100 | 4.14 ms | 8.08 ms | 4 | Baseline only |
| Resource Catalog | Prior SQLite | 1,000 | 6.78 ms | 12.50 ms | 4 | Baseline only |
| Resource Catalog | Prior SQLite | 10,000 | 40.48 ms | 41.29 ms | 4 | Baseline only |
| Resource Inspector | Prior SQLite | bounded | 2.20 ms | 3.60 ms warm | 2 | Baseline only |
| Resource Overview | Prior SQLite | one | 1.88 ms | 1.88 ms | 2 | Baseline only |
| Projects | Prior SQLite | 1,000 | not recorded | 8.10 ms sample | 3 | Baseline only |
| Assignments | Prior SQLite | 10,000 | not recorded | 74.75 ms sample | 3 | Baseline only |
| Activity | Prior SQLite | 10,000 | not recorded | 21.87 ms sample | 3 | Baseline only |
| Capability | R5G | Open | Open | Open | Open | Pending |
| Availability | R5G | Open | Open | Open | Open | Pending |
| Review Queue | R5G | Open | Open | Open | Open | Pending |
| Queue Inspector | R5G | Open | Open | Open | Open | Pending |
| Review command | R5G | Open | Open | Open | Open | Pending |

Environment for prior values: local SQLite development fixture, warm-up and
sample counts as recorded in R5B/R5E. R5G measurements will separately disclose
database, fixture size, warm-up, repetitions, and machine context.

## 34. Security Evidence Table

| Gate | Evidence | Status |
|---|---|---|
| Resource permission matrix | Existing targeted tests; integrated rerun required | Open |
| Review Queue permission matrix | Existing R5F tests; integrated rerun required | Open |
| Tenant/org application scope | Scoped readers/repository tests present | Partial |
| Hidden Project behavior | Reader policy/tests present | Partial |
| PostgreSQL runtime role | No current evidence recorded | Open |
| PostgreSQL tenant/org RLS negatives | No current direct-SQL evidence recorded | Open |
| Child-table bypass | No current direct-SQL evidence recorded | Open |
| pg_class / pg_policy inspection | No current evidence recorded | Open |

## 35. Issues Fixed

R5G-UI-001 tracks the Review Queue bounded Inspector correction. The initial
anchored-filter proposal was superseded by the approved application-standard
centered filter decision and is not an open defect.

## 36. Explicit Deferred Scope

Deferred by product boundary, not hidden debt: automated matching/ranking,
optimization, AI assignment, new top-level destinations, Time Entry redesign,
generic review infrastructure, staffing write redesign, scheduling/Gantt
changes, Finance/R6, HR/payroll, and broad R8 accessibility certification.

Environment-dependent R5G gates are not product deferrals: PostgreSQL plan/RLS
evidence and visual runtime observations remain blockers until an appropriate
runtime/database is available.

## 37. R5H Handoff

R5H has not started. After all R5G critical/high defects and evidence gates are
closed, R5H will inventory R5 files/contracts/routes/QML, remove proven dead or
legacy artifacts, establish one authority per concept, run final broad suites,
reconcile documents, and produce final R5 closure. No compatibility artifact is
to survive without an explicit owner and removal condition.

### R5G Exit-Gate Ledger

The authoritative 168 gates are grouped here to avoid false precision while
implementation is active:

| Group | Gate range | Current state |
|---|---:|---|
| Responsive/dialog | 1-20 | In progress; two defects confirmed |
| Keyboard | 21-29 | Open |
| Resource performance | 30-49 | Partial prior SQLite evidence |
| Review performance | 50-59 | Open |
| Query plans/indexes | 60-72 | PostgreSQL evidence open |
| Memory/async | 73-81 | Partial code guards; runtime evidence open |
| Security | 82-96 | Partial application tests; PostgreSQL evidence open |
| Concurrency/transactions | 97-105 | Prior targeted evidence; integrated rerun open |
| Events/integration | 106-114 | Partial implementation; integrated tests open |
| ResourceKind | 115-119 | Prior implementation; integrated matrix open |
| States/errors | 120-134 | Open integrated matrix |
| Cross-feature | 135-144 | Open integrated scenarios |
| QML/regression | 145-158 | Open |
| Tooling/docs | 159-168 | In progress |
