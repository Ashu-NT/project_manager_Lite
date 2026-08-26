# R5H Workload Management Closure

## 1. R5 Status

**R5 IS CLOSED.** R5 implementation, the R5H.1 PostgreSQL security/scale gate,
and final PM regression reconciliation are complete. The final code audit found
one authority per workload concept, removed verified dead paths, restored
TimeEntry optimistic concurrency, and passed both focused and broad PM
regression. Five-viewport geometry and repeated route-lifecycle behavior are
verified by integrated QML runtime tests rather than inferred from source-only
checks. Optional human visual review and broad accessibility certification are
R8 work, not R5 implementation blockers.

## 2. Final Product IA

The canonical PM module has six groups and eleven destinations:

| Group | Destinations |
|---|---|
| Overview | Overview |
| Portfolio | Portfolio |
| Work | Projects, Tasks, Planning, Timesheets |
| Workload Management | Resources, Review Queue |
| Finance | Finance |
| Governance | Register, Collaboration |

Timesheets and Review Queue are distinct. MINE, TEAM, and ALL are Timesheets
query scopes, not routes or pages. Resource Detail remains Overview,
Capability, Availability, Projects, Assignments, and Activity.

## 3. Final Authority Matrix

| Concept | Authoritative owner | R5 projection/use |
|---|---|---|
| Resource | Resource aggregate/repository | Master data and lifecycle |
| ResourceKind | Resource domain enum/policy | PERSON, CREW, EQUIPMENT behavior |
| ResourceSkill | Resource capability child | Paged capability fact |
| ResourceCertification | Resource capability child | Paged certification fact |
| Working time | Enterprise calendar resolver | Availability capacity input |
| Capacity modifier | `Resource.capacity_percent` | Multiplies calendar capacity |
| Project staffing | Project-owned `ProjectResource` | Projects projection/control envelope |
| Task commitment | Task-owned `TaskAssignment` | Assignments/workload projection |
| Actual work | Platform `TimeEntry` | Timesheets and Task Detail Time |
| Period workflow | Platform `TimesheetPeriod` | Submit/review/lock state |
| Review Queue | None persisted | Projection over TimesheetPeriod |
| Resource Activity | Shared ActivityEntry evidence | Resource-scoped activity projection |
| Project schedule | SchedulingEngine / `run_cpm` | Availability/assignment context only |
| Resource leveling | Accepted scheduling decision mechanism | No second R5 authority |

## 4. Resource Architecture

The active vertical slice is QML workspace/detail sections -> Resource
controller -> presenter -> desktop API -> application query/command service ->
scoped reader/repository. Active production packages are the Resource domain,
`application/resources`, desktop `api/resources`, resource SQL readers and
repositories, Resource controllers/presenters, and the `resources` QML tree.
SQL pages return immutable facts/desktop DTOs; QML does not receive ORM rows or
mutable aggregates. Create, edit, deactivate, and reactivate use the canonical
Resource command/UoW path.

## 5. ResourceKind

`ResourceKind` has PERSON, CREW, and EQUIPMENT. Master-data and workload reads
support all three without Employee assumptions. The single time-reporting
policy permits only active labor PERSON resources with EMPLOYEE or EXTERNAL
worker type; CREW and EQUIPMENT do not acquire human-timesheet behavior by
being assignable resources.

## 6. Capability Architecture

ResourceSkill and ResourceCertification are Resource-owned versioned child
facts. Reads are server-paged and counts are produced server-side. Writes use
resource authorization, scoped repositories, one capability UoW, staged
activity/audit, one commit, and targeted Resource invalidation. Expiry status is
derived in the backend; QML only presents returned facts and capabilities.

## 7. Capacity Authority

The enterprise calendar resolver supplies working time. Effective capacity is
calendar capacity multiplied by `Resource.capacity_percent`. It is compared
with TaskAssignment commitments. No obsolete local calculator or QML formula
is an authority, and `ProjectResource.planned_hours` is not physical capacity.

## 8. ProjectResource Boundary

ProjectResource remains Project-owned project staffing and the project-level
planned-hours envelope. Resource Projects is a read-only projection. Project
staffing writes remain outside the Resource workspace authority.

## 9. TaskAssignment Boundary

TaskAssignment remains Task-owned. `allocated_planned_hours` is the task's
planned-work share, `allocation_percent` is the effective-capacity commitment,
and TimeEntry is actual work. Resource Assignments is projection-only and does
not mutate assignment ownership.

## 10. TimeEntry Authority

Platform TimeEntry is the sole actual-work record for both Timesheets and Task
Detail -> Time. Add/update/delete share the platform command path. TimeEntry now
has a persisted version; update/delete require expected version and use atomic
tenant/organization/version predicates. A stale mutation conflicts instead of
silently overwriting. Audit failure rolls back the business row.

## 11. TimesheetPeriod Authority

TimesheetPeriod is the sole period workflow authority. The governed lifecycle
is OPEN -> SUBMITTED -> APPROVED or REJECTED/Returned, REJECTED -> SUBMITTED,
APPROVED -> LOCKED, and policy-governed unlock/correction. Expected version is
mandatory for transitions. SUBMITTED, APPROVED, and LOCKED periods cannot be
edited through normal Timesheets entry commands.

## 12. Timesheets Architecture

`Work -> Timesheets` is the one owner/timekeeper workspace. Its active packages
are the typed timesheet workspace read contract/SQL reader, PM TimesheetService,
desktop timesheet API, resource-timesheets presenter/controller, and
`resource_timesheets` QML tree. It shows one authorized Resource-period at a
time, with server-backed resource selection, period summary, paged entries,
history, CRUD, and submit/resubmit. It does not own review decisions.

## 13. TimesheetScope

`TimesheetScope` is the typed MINE/TEAM/ALL contract. MINE resolves the current
user's Resource on the server and rejects impersonation. TEAM derives Resources
from managed or explicitly authorized projects. ALL requires
`timesheet.read_all`. A supplied Resource ID is always an authorized filter,
never a grant. Selector count, filtering, ordering, limit, and offset execute in
SQL and remain tenant/organization scoped.

## 14. Employee / External Behavior

Active PERSON+EMPLOYEE and PERSON+EXTERNAL Resources are eligible under the
single time-reporting policy. An identity-linked external can use MINE. An
external without login can be handled only by a TEAM/ALL actor with the relevant
edit permission and, for submission, `timesheet.submit_on_behalf`. Resource
owner and authenticated actor remain separate persisted/audit facts.

## 15. Review Queue Architecture

`Workload Management -> Review Queue` is a server-paged projection over
TimesheetPeriod only. Default status is SUBMITTED. Reviewer actions are Approve,
Return/Reject, Lock, and Unlock according to status/capability. There is no
reviewer Submit, unsafe bulk action, generic ReviewQueue aggregate,
ApprovalRequest aggregate, or generic approval workflow hidden behind it.

## 16. Activity Authority

Resource Activity reads shared `ActivityEntry` evidence correlated to Resource,
ProjectResource, and TaskAssignment identity under tenant/organization and
project visibility. The previous pseudo-history builder is not active. The
projection does not manufacture lifecycle history in QML or a presenter.

## 17. CQRS Boundaries

R5 reads follow QML -> controller -> presenter/desktop API -> query service ->
Reader -> bounded SQL -> immutable fact -> desktop DTO. R5 writes follow QML ->
controller -> desktop command -> application service/UoW -> authorization ->
domain/repository -> audit/outbox -> commit -> post-commit event. Query services
do not commit, mutate state, import desktop DTOs, or return ORM entities.

## 18. Transaction Ownership

Repositories do not commit. Resource master/capability command UoWs and the
platform TimeService own one transaction boundary. Business mutation,
fail-closed audit, and required outbox staging commit together. Domain
invalidation is emitted only after successful commit. Injected audit-failure
tests prove TimeEntry rollback; Resource/capability/review atomicity is covered
by their focused transaction suites.

## 19. Concurrency

Resource, ResourceSkill, ResourceCertification, TimeEntry, and TimesheetPeriod
mutations use optimistic versions. TimeEntry stale update and stale delete are
now explicitly tested. Review decisions and period submission reject stale
versions. Controllers refresh authoritative state after conflicts rather than
optimistically retaining a rejected local version.

## 20. Audit / Outbox

Resource and capability changes stage authoritative activity/audit in the same
transaction. TimeEntry CRUD uses fail-closed audit with no nested commit.
Timesheet approval stages approved-time integration evidence in the outbox in
the period transaction. Owner Resource and authenticated actor are preserved;
QML does not supply trusted actor fields.

## 21. Events / Invalidation

Resource master/capability commits emit targeted `resources_changed(resource_id)`.
Project/assignment changes emit project/task changes consumed by Resource
detail refresh. TimeEntry changes emit task-scoped invalidation. Period
transitions emit `timesheet_periods_changed(period_id)` after commit, refreshing
Timesheets and Review Queue. Workspace subscriptions are lifecycle-bound and
the audit found no duplicate R5 subscription authority or event loop.

## 22. Permissions

| Surface | Actual permission identifiers |
|---|---|
| Resource read | `resource.read` |
| Resource manage/lifecycle | `resource.manage` |
| Capability read/manage | `resource.read`, `resource.manage` |
| Availability read | `resource.read` |
| Own timesheet | `timesheet.read_own`, `timesheet.edit_own`, `timesheet.submit` |
| Team timesheet | `timesheet.read_team`, `timesheet.edit_team` |
| Organization timesheet | `timesheet.read_all`, `timesheet.edit_all` |
| Delegated submit | `timesheet.submit_on_behalf` |
| Review decision | `timesheet.approve` |
| Lock lifecycle | `timesheet.lock` |
| Source identity | `project.read`, `task.read` and project-scoped grants |

Read-other, edit-other, submit-on-behalf, approve, and lock are independent.
Unknown/loading/error capability state is denied. Reviewer permission does not
grant edit-other.

## 23. Tenant / Organization / Project Security

Application readers and writes explicitly scope tenant and organization.
MINE/TEAM/ALL target validation blocks manual cross-Resource IDs; TEAM and ALL
do not broaden tenant/org scope. Project names/task identity are returned only
under source visibility while authorized hours remain truthful. Application
tenant/org, cross-resource, cross-team, ALL-without-permission, hidden-project,
and organization-switch tests pass. Database defense-in-depth is now covered by
the live R5H.1 PostgreSQL evidence below.

## 24. RLS

The fresh PostgreSQL baseline classifies direct scoped R5 tables and generates
forced parent-correlated policies for ResourceSkill, ResourceCertification,
ProjectResource, Task, TaskAssignment, and TaskSkillRequirement. R5H.1 runs
Alembic from a fresh schema under a separate migration owner and executes live
checks through `app_runtime`, which is NOSUPERUSER, NOBYPASSRLS, and owns no
application tables. `pg_class` and `pg_policies` inspection, absent-context
denial, cross-tenant and same-tenant/cross-organization CRUD negatives, and all
six child-table bypass attempts pass. See `R5H_1_POSTGRESQL_EVIDENCE.md`. The
PostgreSQL RLS exit gate is closed.

## 25. Responsive Results

Automated integrated QML geometry covers 1024x640, 1280x720, 1366x768,
1440x900, and 1920x1080 for Resources, Resource Detail, and Review Queue; the
Resource catalog additionally covers 800x640. The runtime tests open and close
both centralized filters and the Review Queue decision dialog at every approved
viewport, prove bounded sizing, verify responsive side/overlay Inspector
behavior, and prove keyboard focus returns to the originating DataTable.
Resource Skill and Certification tables additionally prove bottom-pinned
pagination at all five approved viewports. Resources and Review Queue each
survive three create/show/detach/destroy cycles per viewport without QML layout,
type, reference, or lifecycle failures. Optional human visual review and broad
R8 accessibility certification remain outside R5.

## 26. Performance Results

Measured local SQLite engineering evidence, not PostgreSQL production claims:

| Read | Fixture/result | Statement budget |
|---|---|---:|
| Resource Catalog | 100 p95 4.11 ms; 1k p95 10.27 ms; 10k p95 52.06 ms | 4 |
| Resource Inspector | warm p95 2.94 ms; cold 7.38 ms | 2 |
| Resource Summary | p95 2.61 ms | 2 |
| Resource Projects | 1k 9.20 ms | 3 |
| Resource Assignments | 10k 63.88 ms | 3 |
| Resource Activity | 10k 30.08 ms | 3 |

Availability is date-range bounded and paged detail models retain only the
current page. Live PostgreSQL 10k/50k p95 is 43.27/132.38 ms for Resource
Catalog, 24.21/63.06 ms for the Timesheets Resource selector, and 49.53/179.03
ms for Review Queue. At 50k, Resource Inspector is 9.22 ms, Availability demand
5.63 ms, Timesheet entries 40.92 ms, Timesheet history 42.07 ms, and Review
Queue Inspector 48.48 ms p95. Catalog/selector/queue statement budgets are
3/2/2. Runtime-role `EXPLAIN (ANALYZE, BUFFERS)` covers every listed surface;
no speculative index was required. The PostgreSQL performance matrix is closed.

## 27. Memory / Async Results

Resource Catalog, capability, Projects, Assignments, Activity, Timesheets, and
Review Queue models are page bounded. Resource asynchronous detail requests use
generation/request IDs so stale selection results are discarded; focused tests
prove stale Inspector and Activity responses cannot replace a newer selection.
Timesheets and Review Queue currently execute synchronously on the Qt main
thread, so they cannot accept a late worker result, and presenter tests prove
selected IDs/models reset on scope changes. Organization-switch reads fail
closed. Source/subscription audits found no unbounded R5 collection. Integrated
runtime tests repeatedly construct, show, detach, and destroy both workload
routes at every approved viewport without a QML lifecycle failure; the separate
subscription audit found no duplicate R5 subscription authority. Dedicated
long-duration heap profiling is optional operational evidence, not an R5
closure requirement.

## 28. End-to-End Workflow Results

Targeted tests pass Resource create/edit/deactivate/reactivate, capability CRUD,
capacity projections, self time entry and versioned submit, returned correction
and resubmit, approval and lock rules, external delegated entry/submission,
TEAM/ALL authorization, Review Queue roundtrip, hidden-project redaction,
organization switching, Task Detail -> Time shared commands, R4.4 leveling, and
R4.5 Gantt. TimeEntry audit rollback and stale update/delete pass. No new R5
feature was introduced during R5H.

## 29. Legacy Code Removed

Deleted or retired artifacts include the personal-only owner reader/DTO/
serializer and owner-timesheets packages, old owner QML/qmldir artifacts,
zero-consumer `ResourcesWorkspace.qml`, zero-consumer
`TimesheetsWorkspace.qml`, the empty timesheets sections qmldir, obsolete
placeholder architecture assertions, old personal-only test naming, pseudo
Resource activity construction, reviewer Submit, and unsafe bulk-review UI.
Imports, composition registration, type metadata, and qmldir entries were
updated with the removals. No transition adapter remains for the personal-only
model.

## 30. Compatibility Code Retained

The canonical route is `project_management.workspace`. Ten pre-existing PM
route IDs are intentionally retained only as shell/deep-link compatibility
routes: dashboard, portfolio, projects, tasks, scheduling, resources,
timesheets, financials, register, and collaboration. They all resolve into the
canonical shell and have active route consumers/tests. Review Queue has no
legacy route ID. Removal condition: retire each compatibility route when shell
and external deep-link dependencies no longer reference it.

## 31. Full Test Results

Focused R5H reconciliation: 52 passed. The final policy/R5G/TimeEntry evidence
set adds 20 passed. Earlier focused concurrency, assignment, integration,
security, runtime, migration, and performance groups also passed. The final
broad `src/tests/project_management` reconciliation is **1,417 passed in
702.55 seconds (11m42s)**. This includes the corrected SQL-offset contract, the
authoritative assignment mutation/explicit-refresh lifecycle, and all earlier
R5 stale-contract/fake regressions.

R5H.1 adds 18 live PostgreSQL tests: 14 security/concurrency checks plus 10k/50k
reader measurements and runtime-role query plans. The focused Review
Queue/Timesheets compatibility set adds 13 passed.

This continuation adds an 82-test focused R5 workload/presenter run and a
57-test targeted boundary run covering canonical/deep-link routes, Task Detail
Time, R4.4 leveling, and R4.5 Gantt closure. The final R5G hardening subset is
28 passed and executes real popup/dialog behavior, focus return, capability
pagination geometry, and repeated route lifecycle at all five approved
viewports. The assignment refresh regression and immediate mutation contract
also pass together in a focused two-test check.

## 32. Static Tool Results

R5-owned Python `compileall` passed. R5 QML `qmllint`, run with all application
import roots, is silent and exits zero. Offscreen runtime/component tests pass.
`git diff --check` passed with line-ending notices only. No configured full
type-check command is established for this closure. The agent did not invoke a
commit; the user committed concurrent work during the audit.

## 33. Known Deferred Debt

| Classification | Item |
|---|---|
| CLOSED BY R5H.1 | PostgreSQL runtime-role RLS negatives, child bypass, and catalog inspection evidence |
| CLOSED BY R5H.1 | PostgreSQL 10k/50k reader matrix and runtime-role plans for Catalog, selector, Review Queue, Availability demand, Timesheets, and Inspectors |
| CLOSED BY R5H | Five-viewport clipping/geometry and repeated route open-close lifecycle evidence |
| R6 | Finance implementation and any Finance-owned regression |
| R8 | Broad accessibility certification and non-blocking visual polish |
| PLATFORM | Unrelated Platform test/cache/workspace hygiene |
| INTENTIONAL COMPATIBILITY | Ten tested PM deep-link route IDs |

## 34. Explicit R6 Boundary

R6 is Finance and was not started by R5H. Approved Budget remains Finance-owned;
Projects may project read-only budget facts. PM may prepare billing evidence and
profitability views but cannot manufacture accounting, tax, GL, receivable, or
statutory truth. Resource capacity, ProjectResource, TaskAssignment, and
TimeEntry semantics must not be repurposed as financial amounts.

## 35. R5 Closure Decision

All R5 exit gates are complete. PostgreSQL runtime-role/RLS and 10k/50k scale
evidence are recorded in `R5H_1_POSTGRESQL_EVIDENCE.md`; responsive/lifecycle
runtime evidence is green at the five approved viewports; and the complete PM
suite passes 1,417 tests. Optional human visual review, long-duration heap
profiling, and broad accessibility certification remain explicitly assigned to
R8 and do not retain R5 code or compatibility debt.

**R5 CLOSED - 2026-08-26**
