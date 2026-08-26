# R5A Workload Management Enterprise Audit

## 1. Status and Scope

**Status:** COMPLETE - read-only engineering and product audit.

This audit covers the approved Project Management Workload Management information architecture only:

```text
Workload Management
|-- Resources
`-- Review Queue
```

Resources and Review Queue are the only top-level destinations. ProjectResource, TaskAssignment, capacity, calendars, TimeEntry, TimesheetPeriod, skills, certifications, activity, Finance, and platform identity are assessed only as authoritative context or dependencies. No R5 implementation, production source change, migration, test edit, route addition, or commit is part of R5A.

Evidence was traced through QML, controllers, presenters, desktop APIs, application services, domain models, contracts, readers, repositories, SQLAlchemy models, Alembic/RLS configuration, composition, event invalidation, and targeted tests. Recommendations below are implementation requirements, not claims that the current application already meets them.

## 2. Executive Summary

The approved Workload Management IA is correct and is already represented by the canonical PM workspace route. Resources and Review Queue remain its only destinations. R5F.1 subsequently approved one separate `Work -> Timesheets` destination; the product must not add Workload, Capacity, My Time, or Time Entries as additional destinations.

The current Resource catalog has a strong scalable base: authoritative SQL paging, filtering, sorting, deterministic ordering, tenant/organization scoping, and bounded statement tests. It is not yet an enterprise Resource experience. The read contract leaks a mutable domain entity, there is no lightweight Inspector, detail sections use service fan-out and pseudo-history, capabilities are incomplete, skill/certification writes lack reliable authorization/transaction/event behavior, and editing can silently reset capacity to 100 percent.

The current Review Queue is correctly a projection over authoritative TimesheetPeriod workflow state, not a new workflow aggregate. It currently reviews only TimesheetPeriod submissions. Its SQL page is bounded and server-authoritative, but write correctness is not ready: no optimistic concurrency token exists, bulk actions are non-atomic and report success imprecisely, audit atomicity is inconsistent, the QML status binding is mismatched, and submit/lock actions send payloads their presenter cannot execute.

R5 should first correct contracts, scope, transactions, capabilities, and concurrency; then build bounded Resource detail readers and the queue UX. Skills and certifications are included as foundation-quality Resource capabilities. Automated matching, HR, Finance, drag scheduling, and a generic multi-workflow review engine are explicitly deferred.

## 3. Current Workload Management IA

`PMWorkspaceNavigationController` exposes exactly `Resources` and `Review Queue` beneath Workload Management. This is aligned with the approved product IA.

The canonical route is `project_management.workspace`. Existing `project_management.resources` and `project_management.timesheets` route IDs are compatibility/deep-link inputs that resolve to the canonical workspace and select `resources` or `review_queue`. They must not become separate global shell destinations.

The current naming is partly stale: Review Queue is selected through the legacy `timesheets` compatibility route and parts of workspace state still use the title `Timesheets`. R5 should correct labels and internal ownership without introducing a third destination.

## 4. Current Routes / QML Tree

Current effective route and view flow:

```text
project_management.workspace
  -> ProjectManagementWorkspacePage.qml
     -> Workload Management
        -> ResourcesWorkspacePage.qml
        -> TimesheetsWorkspacePage.qml (visible destination: Review Queue)

Compatibility only:
project_management.resources  -> workspace / workload / resources
project_management.timesheets -> workspace / workload / review_queue
```

The canonical page lazy-loads destination content. This is preferable to exposing multiple unrelated application-drawer routes. The `TimesheetsWorkspacePage` file/controller naming can be internally retired during the R5F migration after compatibility dependencies are characterized; route behavior must remain canonical.

## 5. Current Resources Architecture

Current catalog read path:

```text
Resources QML
-> Resources workspace controller/presenter
-> PM desktop API
-> resource query service
-> SQL ResourceCatalogReader
-> ResourceCatalogReadItem
-> controller rows
-> shared DataTable
```

The catalog performs database paging, filtering, search, and sorting. The reader applies tenant, organization, permission-derived scope, allowed sort mappings, and an ID tie-breaker. This is the correct logical CQRS direction.

Current detail/write paths are less coherent. Detail data is assembled from the selected page row plus multiple services, while writes travel through desktop API/application services/repositories. Resource writes use permissions and version-aware repository operations, but services own commits and publish activity/events after commit. Skills and certifications bypass several of those guarantees.

## 6. Current Review Queue Architecture

Current queue read path:

```text
Review Queue QML
-> timesheets workspace controller/presenter
-> PM desktop API
-> timesheet review query
-> SQL review queue reader
-> TimesheetReviewQueueItem
-> server-mode DataTable
```

The reader projects TimesheetPeriod, TimeEntry, Resource, TaskAssignment, Task, and Project data. It performs scoped SQL paging, filtering, search, sorting, aggregate counts, and deterministic tie-breaking. The queue does not own state, which is correct.

The controller/presenter remains mixed with personal time-entry concerns that are not part of the approved Review Queue UI. Review actions call authoritative TimesheetPeriod workflow services, but QML action contracts, transaction ownership, concurrency, bulk behavior, and audit behavior are inconsistent.

## 7. Resource Domain

`Resource` currently represents a PM delivery-capacity record with identity and planning/commercial attributes: name, code, role, active status, worker type, employee link, organization/department, capacity modifier, cost type, hourly rate, currency, contact/address, and version.

The enterprise definition for R5 is: **a tenant- and organization-owned provider of schedulable project delivery capacity**. A Resource may be linked to a platform Employee but is not an Employee aggregate. It owns PM planning identity, lifecycle, capability associations, and availability modifier; platform identity and calendars remain authoritative elsewhere.

Hourly rates and cost classifications already exist but are not the center of R5. Their broader redesign belongs to R6 Finance.

## 8. Resource Types

Current `WorkerType` supports only `EMPLOYEE` and `EXTERNAL`. This describes engagement, not whether a Resource is a person, crew, or equipment. `CostType.EQUIPMENT` does not safely substitute for resource type because cost classification and capacity semantics are different concepts.

R5 should add a small explicit `ResourceKind` with `PERSON`, `CREW`, and `EQUIPMENT`. Materials are not schedulable workload Resources. `WorkerType` remains applicable engagement context where meaningful. Capability sections may vary by kind; for example certifications may apply to a person or equipment, while employee identity is person-only.

## 9. Resource Aggregate Boundary

Keep Resource small. It owns Resource identity, lifecycle, kind, PM role, capacity modifier, organization/department references, optional employee association, and version.

ResourceSkill and ResourceCertification remain separate child entities/repositories with their own versions and lifecycle. ProjectResource belongs to the Project staffing boundary. TaskAssignment belongs to the Task execution boundary. Calendars and Employee identity remain platform-owned. TimeEntry and TimesheetPeriod remain platform/workflow-owned.

Do not load all skills, certifications, projects, assignments, time entries, or activity into a giant Resource aggregate. Use scoped commands for mutations and bounded readers for presentation.

## 10. Resource Lifecycle

Normal lifecycle is create, edit, deactivate, and reactivate. Deactivation preserves planning, assignment, time, approval, and audit history. Hard delete is permitted only for a never-used draft/resource with no historical or current references, under an explicit destructive permission and confirmation.

Current delete checks actual hours but can cascade planning associations and uses optional guard wiring. That is too permissive. R5 should make deactivation the primary UI action, remove bulk hard delete, and make any exceptional purge fail closed on every relevant reference.

## 11. Skills

Skills already exist as normalized `ResourceSkill` records with code, name, proficiency, notes, and version. Task skill requirements also exist with warn/block/override policy. There is no canonical tenant skill taxonomy; code/name values are copied into associations.

Current gaps are material: add/remove paths lack explicit permission enforcement, reliable caller-owned commit, activity/audit, and invalidation; list failures can be converted into empty success; no update command exists; and versions are not used consistently.

R5 includes Skills as a foundation capability: CRUD, visibility, deterministic requirement comparison, scope, concurrency, and audit. It does not include automated matching or recommendations.

## 12. Certifications

Certifications already exist as `ResourceCertification` records with code, name, issue/expiry dates, issuer, notes, and version. The ORM also has a certificate number not consistently represented through domain/mapper/UI contracts, and naming differs between `issuing_authority` and `issuing_body`.

R5 includes certification foundation quality: coherent fields, create/edit/remove, expiry visibility, permission, transaction, concurrency, audit, and invalidation. A global compliance/taxonomy product is deferred.

## 13. Capability vs Capacity

Capability answers **what work a Resource is qualified to perform**: Resource kind, role, skills, certifications, and task requirements. Capacity answers **how much schedulable time is available and committed**: calendar working hours, availability modifier, assignments, dates, and utilization.

These must remain separate in contracts and UI. Capability may produce deterministic warnings for missing/expired requirements. It must not automatically assign or rank Resources in R5.

## 14. ProjectResource

ProjectResource is the Project-to-Resource staffing association. It owns project membership, project-specific planned hours, active status, version, and currently project-specific rate/currency context. It is not Resource master capacity and is not a TaskAssignment.

Its service enforces project permissions and uses repository scope, but commits internally and emits activity/events afterward. R5 should expose ProjectResource as a paged `Projects` section in Resource detail while preserving Project ownership. Commercial fields should remain permissioned and must not expand into R6 Finance work.

## 15. TaskAssignment

TaskAssignment links a Resource to a Task and owns allocation percentage, allocated planned hours, logged hours, response status, optional ProjectResource link, and version. Its effective interval comes from Task dates.

It is the execution commitment used for workload facts. It must appear through a paged `Assignments` Resource projection. Assignment acceptance/decline is a separate workflow from Timesheet Review Queue and must not become a Review Queue item in R5 without a separately approved source workflow.

## 16. Capacity Authority

Platform `EnterpriseCalendarResolver` and `EnterpriseResourceAvailabilityService` are the working-time authority. Stored `Resource.capacity_percent` is a PM availability modifier, not a calendar and not an independently authoritative capacity total. TaskAssignment commitments supply planned load.

The target calculation is explicit:

```text
base calendar hours
x Resource availability modifier
= effective capacity hours

effective capacity hours
- committed assignment hours/allocation
= remaining capacity and utilization
```

Older `ResourceAvailabilityService`, `ResourceLoadEngine`, `PortfolioResourcePool`, and calculators are not fully reconciled. R5D must designate one calculation contract and adapt or delete superseded implementations.

## 17. TimeEntry Context

Platform TimeEntry records actual effort against a work allocation, optionally a TaskAssignment, with generic owner/scope and employee/department/site context. Hours currently use float rather than Decimal and there is no optimistic version.

TimeEntry matters to R5 as actual workload/activity evidence and as input to TimesheetPeriod review. It is not a new Workload Management destination. The present queue SQL primarily sees task-assignment-backed project entries, so direct/non-task/project-scoped entries require an explicit product/query decision before claiming complete review totals.

## 18. Task / Project Activity Context

Task activity is supported when TimeEntry resolves through TaskAssignment. Project activity is supported when the assignment/task resolves to Project, or when an explicitly supported project scope is present. Current data does not justify fabricating project/task attribution for generic entries.

R5 Resource detail may show bounded assignment and approved-time activity with source links and honest attribution. It must not redesign Tasks, Projects, or Time Entry UI and must label unattached/general time distinctly.

## 19. Timesheet Context

TimesheetPeriod is the authoritative review workflow with `OPEN`, `SUBMITTED`, `APPROVED`, `REJECTED`, and `LOCKED` states plus submit/decision/lock metadata. The domain/ORM has no version token and stores only a current decision note rather than an immutable decision history.

Review Queue must invoke this workflow; it must never mutate a queue row as an independent record. Tenant/organization fields are currently nullable in key models even though queue behavior requires a resolved active scope.

## 20. Resource Catalog

The current catalog is the strongest R5 foundation. It uses authoritative database paging, text/filter predicates, mapped sort keys, deterministic ID tie-breaking, scoped counts, and permission-derived access. Existing tests cover cross-page ascending/descending order, unsupported sort fallback, page normalization, tenant/organization isolation, and a bounded four-statement budget.

Problems:

- `ResourceCatalogReadItem` embeds a mutable Resource domain object instead of scalar immutable read facts.
- Search includes contact/address/phone/email data, increasing PII exposure and index cost.
- Summary totals are scope-wide while `filtered_total` is filter-aware; labels must make that distinction explicit.
- The catalog does not expose normalized workload/capability summaries suitable for an Inspector.
- Global `resource_code` uniqueness conflicts with tenant/organization SaaS ownership.

R5B should preserve the SQL reader and replace its output contract, not regress to repository/domain hydration.

## 21. Resource DataTable

The shared DataTable is appropriate for Resource Catalog. It must remain in `sortingMode: "server"` with controller-owned query state, server filtering/paging, allowed sort mappings, and stable tie-breakers. No client-side filtering or page-local sorting is acceptable at 10,000 Resources.

Columns should be bounded and operational: code, name, kind, role, organization/department where authorized, status, effective capacity/utilization summary, and capability warning summary. Contact and rate fields should not be default table columns. Selection should survive a refresh only when the selected ID remains in scope and should not imply that a page row is a complete detail object.

## 22. Resource Inspector

There is no true lightweight list-adjacent Resource Inspector today. Selection is based on the current page item and row activation opens full detail. This limits contextual review and encourages detail assembly from an incomplete page DTO.

R5B should add an ID-driven bounded Inspector reader. Wide layouts may show it beside the table; compact layouts use a drawer or navigate to full detail. It must not load all assignments/activity or duplicate the full detail page.

## 23. Resource Detail

Current detail exposes Overview, Assignments, Capacity, Calendar, Skills, Certifications, Cost Rates, Availability, and Activity. The breadth looks complete, but the data architecture is not: assignments/projects are assembled through service calls, current-page rows seed detail, and Activity is an assignment snapshot rather than history.

The target is a full Resource page loaded by Resource ID with independently authorized, bounded, paged/lazy section readers. Calendar, capacity, and availability should become one coherent Availability section. Cost Rates must not drive R5 or bypass the R6 boundary.

## 24. Resource Dialogs

Current create/edit dialog covers employee, worker type, category, rate/currency, address, and contact. Organization/site/department context is mainly employee-derived and not a complete independent scoped selector strategy for external/non-human resources.

Critical defect: `ResourceEditorDialog.buildPayload()` omits `capacityPercent`; the presenter defaults a missing value to `100.0`. Editing a Resource can therefore silently reset a valid non-100 availability modifier.

Skill/certification dialogs use fixed two-column forms around a 480-pixel width and certification DateFields do not consistently provide the dialog popup boundary. R5 dialogs need responsive one/two-column forms, scrollable bodies, reachable fixed actions, scoped selectors, field-level validation, and concurrency tokens.

## 25. Resource Activity / History

The current Activity section is not authoritative history. It derives assignment-oriented rows and catches failures as empty results. It cannot answer who changed a Resource, when, what changed, or why.

R5 should include a lazy, paged Activity section backed by the existing audit/activity architecture, with typed events and links to source entities. It should not create a second ledger or retain pseudo-history once the real reader is available.

## 26. Resource Workload Facts

Introduce an immutable `ResourceWorkloadFact` projection containing at minimum:

- Resource ID and as-of/range boundaries.
- Calendar source and base working hours.
- Availability modifier and effective capacity hours.
- Planned/committed hours and allocation percentage.
- Actual approved/submitted hours where relevant and authorized.
- Remaining hours, utilization percentage, over-allocation flag, and conflict dates.
- Project/assignment counts and calculation freshness/source version.

The reader must calculate sets in SQL/bounded services rather than load every Resource and run per-row Python calendar/assignment queries.

## 27. Review Queue Item Sources

Today the queue reviews exactly one item type: **TimesheetPeriod**. Rows are projections enriched by Resource, TimeEntry, TaskAssignment, Task, and Project context. Those joined entities are context, not additional queue item types.

R5 must retain a typed `TIMESHEET_PERIOD` discriminator for future extensibility but must not introduce a generic queue entity or pretend assignments, expenses, change requests, or other workflows are reviewable today.

## 28. Review Queue States

Authoritative states are `OPEN`, `SUBMITTED`, `APPROVED`, `REJECTED`, and `LOCKED`. Review Queue normally lists reviewable `SUBMITTED` periods and may expose approved/rejected/locked history via filters when supported by the authoritative reader.

Allowed transitions must remain in the TimesheetPeriod application/domain workflow, not QML. A queue row is stale immediately when its source state/version changes.

## 29. Review Queue Actions

Authoritative reviewer actions are:

- `Approve`: `SUBMITTED -> APPROVED`, requiring `timesheet.approve`.
- `Reject/Return`: `SUBMITTED -> REJECTED`, requiring `timesheet.approve` and a required reason.
- `Lock`: eligible terminal state -> `LOCKED`, requiring `timesheet.lock`.
- `Unlock`: `LOCKED -> prior/approved policy state`, requiring `timesheet.lock` and explicit policy.

Submit belongs to the time-entry owner workflow, not the reviewer queue. Current detail exposes submit/lock paths whose QML payloads do not match presenter requirements (`resourceId` and `periodStart` are missing). These actions are broken or misplaced and must be removed from Review Queue until the authoritative contract supports them truthfully.

## 30. Review Queue Permissions

Backend query/action permissions are partly sound: queue access uses approve/lock permissions and project restrictions; approve/reject and lock/unlock require their specific permissions. The presentation layer is not deny-safe.

The PM capability controller does not expose complete queue approve/lock capabilities, bulk buttons remain visible/enabled without a reliable capability/state matrix, and the legacy detail query is broader than the optimized queue contract. R5F must expose backend-derived capabilities per destination and per item, hide or disable unavailable actions consistently, and still revalidate authorization in every command.

## 31. Review Queue Concurrency

TimesheetPeriod, ORM rows, queue facts, controller payloads, and review commands currently have no optimistic version. The check-then-update flow permits two reviewers to act on the same submitted item.

R5F requires a version token and conditional transition such as `UPDATE ... WHERE id/scope/status/version`. Zero rows updated is a stale/conflict result, not success. The UI keeps authoritative state, informs the reviewer, refreshes the row/detail, and never optimistically removes an item before command success.

## 32. Review Queue Auditability

Audit entries exist, but transaction ownership is inconsistent. Approve writes its financial outbox and audit in the transaction; submit/reject/lock/unlock commonly commit workflow state before audit. A crash can therefore leave a transition without matching audit history. `decision_note` is mutable current state, not history.

All review transitions must atomically persist workflow state, append-only decision/audit evidence, and any required outbox record under one caller-owned transaction. Review Queue history reads that authoritative evidence; it does not own another ledger.

## 33. Review Queue DataTable

The current table correctly uses server sorting and query-state paging. Existing tests cover authoritative cross-page ordering, filters, scope, and a bounded three-statement budget.

Defects and improvements:

- QML reads `state.periodStatus` while presenter state uses `status`, so state-based action enablement can fail open.
- Explicit `submittedAt` sort support needs contract coverage even though it is the effective default.
- Row totals are constrained by assignment/project joins and can omit unsupported entry shapes.
- Bulk controls do not enforce homogeneous states, capabilities, or honest per-item outcomes.
- The filter popup is centered rather than consistently anchored to its trigger.

The queue remains a shared server-mode DataTable, primarily tabular, with filters for status, project, Resource, date/age, and typed item source.

## 34. Review Queue Inspector

Current detail is not a bounded queue Inspector and mixes workflow actions with broad time-entry workspace concerns. The target Inspector shows only decision context: Resource/period, status/version, submitted time, total hours, project/task allocation summary, exceptions/warnings, submitter, prior decision summary, and source navigation.

It must fetch by queue item ID/version, not trust the selected row as authoritative. Large entry detail and full history are lazy/paged. On compact screens it becomes a drawer/full detail surface rather than a permanent third column.

## 35. Dialog Standards

Required shared behavior:

- One clear purpose and typed payload per dialog.
- Responsive one-column layout at narrow widths and controlled two-column layout when safe.
- Scrollable content with fixed, reachable actions.
- Date popups bounded to the dialog/window and never clipped outside it.
- Organization/site/department/calendar selectors only when required by the backend contract, with authoritative defaults and deny-safe choices.
- Field-level Pydantic/application errors mapped to controls; no raw exceptions.
- Version carried on edits/reviews; stale conflict keeps user input and offers refresh.
- Destructive/deactivation confirmation states consequences plainly.

Review decisions need dedicated approve confirmation and reject/return reason UX rather than one untyped generic dialog.

## 36. Responsive Audit

Required validation matrix is exactly `1024x640`, `1280x720`, `1366x768`, `1440x900`, and `1920x1080`.

Current workspace/table layouts generally fill available space, and the main Resource editor can switch columns by width. Gaps remain: no real Inspector behavior, fixed skill/certification forms, long detail content, centered queue filter popup, and no runtime geometry suite across all five viewports.

At `1024x640`, use table plus drawer/full detail, never a permanent three-column composition. At `1280x720` and `1366x768`, allow a collapsible Inspector if minimum table width remains usable. At `1440x900` and `1920x1080`, table plus bounded Inspector is appropriate; detail sections still use controlled max widths rather than stretching forms.

## 37. Backend Read Architecture

Target Resource flow:

```text
QML -> ResourcesController -> desktop API -> ResourceQueryService
    -> ResourceCatalogReader / bounded detail readers
    -> immutable scalar facts -> desktop DTOs -> QML
```

Target queue flow:

```text
QML -> ReviewQueueController -> desktop API -> ReviewQueueQueryService
    -> ReviewQueueReader -> immutable queue facts -> DTOs -> QML
```

Catalog and queue readers remain optimized SQL projections. Detail, Inspector, projects, assignments, capability, availability, and activity receive purpose-built bounded readers. Reader interfaces live in contracts/readers; facts live in PM/platform-neutral contracts owned by the authoritative capability. No ORM/domain aggregate or desktop DTO crosses into application query services.

## 38. Backend Write Architecture

Target write flow:

```text
QML/dialog -> controller -> desktop API -> command/application service
-> authorization and scope revalidation -> domain transition
-> repository flush -> audit/outbox -> caller/UoW commit
-> post-commit targeted event -> query refresh
```

Resource, skill, certification, and TimesheetPeriod commands must share this rule. Commands return typed success, validation, forbidden, not-found, and conflict outcomes. QML never encodes transition rules and queue projections are never mutated directly.

## 39. Readers / Repositories / DTOs

`Reader != Repository` remains mandatory. Readers answer presentation queries with immutable scalar facts and optimized joins/aggregates. Repositories persist and rehydrate authoritative domain entities under scope; they do not provide UI grids.

Keep the existing SQL catalog/queue reader direction. Refactor Resource catalog facts to remove embedded Resource entities. Add ID-driven Inspector/detail readers. Do not let desktop DTOs leak into application services and do not let ORM objects leave infrastructure.

## 40. Transactions

Repositories must flush but never commit. The caller/application UoW owns one transaction containing mutation, version check, audit/activity, and required outbox records. Events are published only after successful commit.

Current Resource/ProjectResource/TaskAssignment/TimesheetPeriod services often commit internally; skill/certification flows may flush without a durable commit; queue bulk loops commit item-by-item. These paths require staged refactoring with characterization tests. A command must never report aggregate success after silent partial completion.

## 41. Optimistic Concurrency

Resource and several association entities already carry versions, but contracts do not consistently require them. TimesheetPeriod and TimeEntry do not. R5 requires mandatory version tokens for Resource, ResourceSkill, ResourceCertification, ProjectResource/TaskAssignment mutations touched by R5, and every review transition.

Conditional writes must include tenant/organization, ID, current state where relevant, and version. Conflict is a first-class typed outcome surfaced safely to QML.

## 42. Events / Invalidation

Current in-process events include targeted Resource and TimesheetPeriod changes, but refresh can still rebuild broad workspace state. Skills/certifications lack reliable events. Some events/activity are emitted after service-owned commits, which weakens one-command ownership.

R5 should publish typed post-commit events carrying tenant, organization, entity ID, change type, and version. Controllers invalidate only affected catalog row, Inspector/detail section, count, or queue page. The existing approved-time financial outbox remains the durable cross-boundary mechanism; local UI invalidation does not need a second durable bus.

## 43. Authorization

Resource catalog/read and Resource master write permissions are generally enforced in backend services. Skills/certifications and UI capability presentation are the major gaps. R5 must define and enforce explicit read/manage/capability permissions and timesheet review/lock permissions at query and command boundaries.

Presentation is deny-safe: absence, loading failure, or unknown capability means no action. Backend authorization remains authoritative regardless of visibility. Project-restricted permissions must shape queue/resource facts as well as commands.

## 44. Tenant / Organization Isolation

All direct Resource and Timesheet facts must have non-null tenant and organization ownership in R5 target schema and commands. Active scope is taken from runtime/session context, never trusted from a mutable QML payload. IDs are always queried with scope predicates.

Current strengths include scoped repositories, reader predicates, and permission-derived project restrictions. Weaknesses include nullable tenant/organization fields, globally unique Resource code, and child entities relying only on parent joins. Uniqueness should be at least `(tenant_id, organization_id, resource_code)`.

## 45. RLS Considerations

The fresh PostgreSQL baseline enables forced RLS for direct tenant/organization tables including Resources, TimeEntries, and TimesheetPeriods. Runtime session context configures tenant/organization and validates the database role.

ProjectResource, TaskAssignment, ResourceSkill, ResourceCertification, and other child tables are intentionally excluded and rely on protected-parent repository joins. Parent RLS does not automatically protect an unscoped direct SQL query against a child table. Because the product is pre-release, R5 should prefer explicit child-table tenant/organization columns and policies for high-risk operational rows, or proven RLS policies using parent `EXISTS` predicates. Add direct PostgreSQL negative isolation tests; repository discipline alone is not equivalent to defense in depth.

## 46. Performance / Scalability

Reference scale is at least 10,000 Resources and tens of thousands of historical/pending queue facts. Keep server paging/sorting/filtering and bounded statement counts. Resource detail sections are independently paged/lazy; no per-Resource assignment/calendar loops are permitted.

Proposed implementation gates, measured on the agreed local PostgreSQL benchmark fixture after warm-up:

| Surface | Target |
|---|---|
| Resource catalog page | p95 <= 200 ms; <= 4 SQL statements; no cardinality-dependent statements |
| Review Queue page | p95 <= 200 ms; <= 3 SQL statements; no source N+1 |
| Inspector | cached p95 <= 100 ms; cold p95 <= 300 ms; bounded detail query |
| Resource summary detail | p95 <= 300 ms; sections lazy and independently paged |
| Dialog open/submit feedback | visible response <= 100 ms; completed local command target <= 500 ms excluding justified I/O |

These are proposed exit thresholds, not measurements of current performance. R5G must create repeatable 10k/50k fixtures and record actual p50/p95 results.

## 47. Test Coverage

Existing strengths include Resource catalog and Review Queue cross-page sorting/filtering tests, query-statement budgets, repository scope tests, permission tests, and DataTable server-query contracts.

Missing required coverage:

- Resource edit preserves capacity and every omitted/unchanged field.
- Skill/certification authorization, commit, version conflict, audit, and invalidation.
- Timesheet reviewer concurrency and stale conflicts.
- Atomic transition + audit/outbox behavior for every action.
- Bulk per-item/transaction outcome behavior if bulk is retained.
- Runtime QML capability/status/action contracts, including the `status` mismatch.
- Review Queue item-shape completeness for direct/non-task entries.
- Five-viewport runtime geometry and keyboard essentials.
- 10k/50k load/query-budget benchmarks.
- Direct PostgreSQL RLS denial against child tables and cross-scope IDs.

## 48. Current Product Gaps

The principal product gaps are no clear Resource kind model, no real Inspector, no authoritative Resource activity, fragmented capacity presentation, incomplete external/non-human context, non-truthful review actions, no reviewer concurrency, no immutable review history, and no coherent deny-safe capabilities.

The current UI appears broader than its reliable behavior. R5 should reduce false affordances first, then add evidence-backed capability.

## 49. Current Technical Debt

Priority debt:

| Severity | Debt | Required disposition |
|---|---|---|
| Critical | Resource edit omits capacity and can reset it to 100 percent | Fix and characterize in R5C |
| Critical | Review decisions have no optimistic concurrency | Schema/domain/command change in R5F |
| Critical | QML `periodStatus` vs presenter `status`; submit/lock payload mismatch | Remove/fix before truthful queue actions |
| High | Skill/certification writes lack complete auth/transaction/event guarantees | Refactor in R5D |
| High | Bulk delete/review loops permit partial results | Remove or replace with explicit server command policy |
| High | Service-owned commits split mutation/audit/event ownership | Move to caller/UoW incrementally |
| High | Mutable domain entity embedded in Resource read fact | Replace in R5B |
| High | Nullable scope and child-table RLS gaps | Harden schema/RLS with PostgreSQL tests |
| Medium | Activity is assignment pseudo-history | Delete after real activity reader ships |
| Medium | Duplicate/unreconciled capacity calculators | Designate authority, adapt, then delete legacy |
| Medium | Mixed personal-time and reviewer controller concerns | Split internally in R5F; keep two-destination IA |

## 50. Resource IA Options

| Criterion | Option A: Catalog -> Inspector -> Detail | Option B: Overview / Capability / Allocation workspace tabs |
|---|---|---|
| Enterprise clarity | Strong master-data entry and one canonical Resource | Weaker; one Resource concern is split across workspace modes |
| Navigation depth | One list, contextual Inspector, full detail when needed | Fewer initial clicks but nested tabs become ambiguous |
| Scalability | Excellent with one paged catalog and lazy detail | Risks repeated large collections and cross-tab query state |
| Responsive behavior | Table/drawer/full-page patterns adapt cleanly | Tabs plus nested sections are crowded at 1024x640 |
| Implementation complexity | Reuses approved PM catalog/Inspector pattern | Requires broader state coordination and duplicate selection logic |

**Decision:** Option A. Resources opens a scalable catalog; selection opens a bounded Inspector where space permits; `Open Resource` navigates to the canonical full detail page.

## 51. Review Queue IA Options

| Criterion | Option A: One authoritative table + filters + Inspector | Option B: Pending / My Reviews / History tabs |
|---|---|---|
| Current source evidence | Fits the single TimesheetPeriod item type | Implies reviewer assignment and review-history products not present |
| Query integrity | One query contract with explicit state filters | Risks three subtly different query contracts/counts |
| Decision speed | Strong with saved filters/grouping and Inspector | Extra navigation for a small source model |
| Scalability | Server paging and indexed filters remain direct | Historical tab can become an unbounded second product |
| Complexity | Lowest truthful design | Premature abstraction |

**Decision:** Option A. Keep Review Queue primarily tabular. Use status/project/Resource/age filters and optional grouping only when it improves triage. History is a filter plus source activity, not a separate top-level tab or ledger.

## 52. Recommended Final R5 IA

```text
Project Management
`-- Workload Management
    |-- Resources
    |   |-- Catalog
    |   |   `-- Resource Inspector
    |   `-- Resource Detail
    |       |-- Overview
    |       |-- Capability
    |       |-- Availability
    |       |-- Projects
    |       |-- Assignments
    |       `-- Activity
    `-- Review Queue
        |-- Authoritative Queue Table
        |-- Queue Inspector
        `-- Source Activity / Decision History
```

No other Workload Management destination is approved. R5F.1 subsequently approved one `Work -> Timesheets` destination with MINE/TEAM/ALL as query scopes; My Time and Time Entry remain non-destinations. Compatibility route IDs may continue resolving to the canonical PM workspace until separately retired.

## 53. Recommended Resource Detail IA

| Order / section | Purpose and read source | Mutations | Loading / component | Permission / responsive behavior |
|---|---|---|---|---|
| 1. Overview | Authoritative identity, code, kind, worker/employee relation, role, org/dept/site, active/version; Resource summary reader | Edit; deactivate/reactivate | Eager bounded fact; structured cards/fields | `resource.read`; mutations require `resource.manage`; one column narrow, bounded two-column wide |
| 2. Capability | Skills, certifications, expiry and deterministic requirement warnings; capability readers | Add/edit/remove skill/certification | Lazy; two paged DataTables plus compact summary | Read permission plus `resource.capability.manage`; stacked narrow, grouped wide |
| 3. Availability | Calendar source, modifier, effective hours, commitments, utilization, conflicts; workload fact reader | Edit availability modifier/calendar association only where owned | Lazy by explicit date range; summary cards plus specialized timeline/table | Workload read; manage for changes; summary-first narrow, visualization only when width permits |
| 4. Projects | ProjectResource memberships, status, planned hours; scoped Resource-project reader | Open Project; assign/remove only through Project-owned command | Lazy paged DataTable | Project/resource permissions intersect; compact columns narrow |
| 5. Assignments | TaskAssignment commitments, dates, allocation, planned/actual, response; scoped assignment reader | Open Task; assignment commands remain Task-owned | Lazy paged DataTable with range/status filters | Task/resource permissions intersect; drawer/full row detail narrow |
| 6. Activity | Append-only Resource/capability/assignment/time facts with actor/time/source | Navigate to source; no direct history mutation | Lazy paged activity reader | Event-specific visibility; compact chronological list/table |

Cost Rates is not a primary R5 detail section. Existing permissioned fields may remain during migration, but rate architecture and financial semantics are R6-owned.

## 54. Recommended Resource Inspector

The Inspector is a fast contextual summary, not detail duplication. Show:

- Name, code, kind, active state, role, organization/department/site, and employee/external marker.
- Effective capacity, current committed load, utilization/over-allocation, and next conflict for the active range.
- Skill count, missing requirement count, certification count, and nearest expiry warning.
- Active project and assignment counts.
- Deny-safe `Open Resource`, `Edit`, and `Deactivate/Reactivate` actions.

Do not show full address/contact, rate history, all skills, all entries, or activity. Fetch by Resource ID through one bounded Inspector reader; expose `as_of`, range, and version. At narrow widths use a drawer or full navigation.

## 55. Recommended Resource Dialogs

Minimum R5 set:

| Dialog | Purpose | Requirements |
|---|---|---|
| Create Resource | Create scoped PM capacity provider | Kind-aware fields; org/dept/site/calendar selectors where contract requires; capacity modifier; validation |
| Edit Resource | Edit Resource master facts | Full current values including capacity; required version; no silent defaults |
| Deactivate/Reactivate Resource | Lifecycle transition | Impact summary, reason where policy requires, no hard-delete affordance |
| Add/Edit Skill | Manage one bounded capability | Code/name/proficiency/notes/version; permission and audit |
| Add/Edit Certification | Manage credential | Code/name/number/issuer/dates/notes/version; bounded DateFields |

Exceptional hard purge should be an administrative backend operation until a proven product need exists. Project membership and Task assignment dialogs remain owned by those capabilities rather than copied into Resource master.

## 56. Recommended Review Queue UX

Use one server-authoritative DataTable with pending-first default, status/project/Resource/date-age filters, stable sorting, accurate counts, and row selection. The Inspector fetches current decision context and version. Approve opens a concise confirmation with optional note; Reject/Return requires a reason. Lock/unlock are visible only when both workflow state and `timesheet.lock` allow them.

Command flow is pessimistically truthful: keep the row until the authoritative command commits; show busy state for that item; on success invalidate/remove or refresh it; on conflict retain input, explain staleness, and refresh; on authorization loss remove the affordance and show a safe message. Source navigation opens the relevant Resource/Project/Task/period where supported.

Current submit action is not part of Review Queue. Current broken/mismatched actions must be removed rather than cosmetically retained.

## 57. Skills Scope Decision

**Decision: Skills foundation is included in R5.** Deliver normalized ResourceSkill CRUD, versions, permission, scope through Resource, transaction ownership, audit/activity, events, paged reads, and deterministic requirement visibility. A tenant skill taxonomy can be a later approved extension; automated ranking/matching is deferred.

## 58. Certification Scope Decision

**Decision: Certification foundation is included in R5.** Reconcile certificate number/issuer fields, support CRUD and expiry facts, apply versions/permissions/transactions/audit/events, and expose paged detail. Enterprise compliance administration, document storage, and global credential taxonomy are deferred.

## 59. Capability-Matching Decision

**Decision: visibility and deterministic validation only.** R5 may state whether a Resource satisfies explicit Task skill/certification requirements and why. It must not rank candidates, recommend assignments, auto-assign, use AI, or hide the policy behind a score.

## 60. Activity / History Decision

**Decision: include Resource Activity using the existing audit/activity foundation.** Build a bounded read projection over authoritative events/audit evidence. Delete the current assignment-derived pseudo-activity after parity tests. History is append-only and never editable from the activity view.

## 61. Review Queue History Decision

**Decision: no queue-owned history entity.** Current/historical rows are TimesheetPeriod projections filtered by authoritative state. Decision history comes from append-only workflow audit/decision evidence and appears in the Inspector/source activity. Do not persist duplicate queue records.

## 62. Task / Project Activity Decision

Task/project TimeEntry activity matters as Resource workload evidence and reviewer context when authoritative links exist. R5 shows bounded task/project attribution, status, planned/actual hours, and source links in Resource Assignments/Activity and Queue Inspector. Generic/unattached entries remain explicitly labeled and are not guessed. No separate Time Entry destination or Tasks/Projects redesign is part of R5.

## 63. Required Backend Changes

| Classification | Change |
|---|---|
| KEEP | SQL Resource catalog reader, SQL Review Queue reader, server paging/filter/sort, deterministic tie-breakers, repository Protocol boundaries, platform calendar authority, authoritative TimesheetPeriod workflow |
| REFACTOR | Resource catalog fact to scalar immutable data; mixed Resources/Timesheets presenters/controllers; service-owned commits; skill/cert error handling; capability evaluation; queue action payload/state contracts |
| NEW READER | Resource Inspector, Resource summary, capability, availability/workload, Resource projects, Resource assignments, Resource activity, queue Inspector/detail/history |
| NEW DTO | Typed catalog, Inspector, detail-section, workload, queue item/detail, capability, conflict, and per-item command-result DTOs |
| NEW COMMAND | Resource deactivate/reactivate; skill/cert edit; versioned review transitions; optional bounded bulk review only after approval |
| NEW SERVICE | One authoritative workload calculation/query service and caller-owned UoW orchestration where composition requires it |
| DOMAIN CHANGE | ResourceKind; mandatory versions/state transition contracts; append-only review decision evidence; coherent certificate fields |
| SCHEMA CHANGE | Non-null scope; scoped Resource code uniqueness; TimesheetPeriod version; Resource kind; decision/audit evidence; required indexes; child RLS hardening |
| DELETE LEGACY | Assignment pseudo-activity, superseded capacity calculators/adapters, broken queue submit/action paths, stale timesheets review facade portions, unsafe bulk hard delete |
| DEFER | Skill taxonomy product, recommendation/matching engine, generic review framework, Finance/rate redesign, HR integrations |

Delete candidates are conditional on replacement characterization and references reaching zero. R5H must prove and execute deletion; no temporary adapter may be left unmarked.

## 64. Required Domain / Schema Changes

1. Add `ResourceKind` independently of worker engagement and cost type.
2. Make direct operational tenant/organization ownership non-null and validate scope at construction/command boundaries.
3. Replace global Resource code uniqueness with scoped uniqueness and supporting lookup index.
4. Add TimesheetPeriod version and version-aware transition persistence.
5. Reconcile ResourceCertification certificate number and issuer naming; add uniqueness policy if the business key is approved.
6. Add append-only review decision/audit evidence or guarantee an existing audit projection has complete typed fields and transactional integrity.
7. Add queue indexes for tenant/org/state/submitted date/resource/project join paths and Resource search/sort indexes proven by query plans.
8. Add direct child-table tenant/org columns with RLS or parent-`EXISTS` RLS policies for sensitive associations.
9. Preserve Decimal for cost/hours in new PM contracts; plan separate migration away from float TimeEntry hours with platform ownership.

Skills/certifications remain separate child entities, ProjectResource remains Project-owned, TaskAssignment remains Task-owned, and Review Queue gets no persisted aggregate.

## 65. Required QML Changes

- Preserve exactly Resources and Review Queue in PM-local navigation.
- Build Resource Catalog -> Inspector -> Resource Detail; never hydrate detail from a page row.
- Replace the nine-section detail with the six approved sections and lazy state per section.
- Make every action capability/state/version aware and deny-safe.
- Fix Resource edit field completeness, especially capacity.
- Replace fixed skill/cert forms with responsive shared dialogs and bounded date popups.
- Split reviewer-only controller/presenter state from hidden personal time-entry state internally.
- Remove Review Queue submit and any action without a valid authoritative payload.
- Add bounded Queue Inspector and dedicated approve/reject UX.
- Do not optimistically remove queue rows before command success.
- Retire pseudo-activity and compatibility internals only after references/tests are removed.

## 66. DataTable Strategy

Use shared DataTable for Resource Catalog, Skills, Certifications, Projects, Assignments, and Review Queue. Every potentially large collection uses server mode, controller-authoritative sort/filter/page state, allowlisted SQL mappings, stable ID tie-breakers, page reset on query-shape change, and scope-preserving refresh.

Specialized components are justified only for bounded capacity/utilization visualization and chronological activity. The smallest useful workload visualization is summary metrics plus a Resource detail allocation timeline for an explicit date range. A Resource-by-time heatmap is not required for R5.

Dangerous bulk Resource delete is removed. Queue bulk is deferred by default; if approved later, it requires server commands, homogeneous eligibility checks, version per item, bounded transaction policy, and honest per-item outcomes.

## 67. Responsive Strategy

| Viewport | Resources | Review Queue / dialogs |
|---|---|---|
| 1024x640 | Catalog full width; Inspector drawer; detail full page; compact columns | Table full width; Inspector drawer/full view; forms one column and scrollable |
| 1280x720 | Collapsible side Inspector if table minimum width holds | Optional side Inspector; bounded filter/action popups |
| 1366x768 | Table + Inspector preferred; sections remain lazy | Table + Inspector; decision dialog centered/anchored and height-safe |
| 1440x900 | Stable split with controlled max widths | Stable split; richer bounded context, no ornamental panels |
| 1920x1080 | Do not stretch forms/tables without max-width policy | Preserve readable density and predictable action placement |

Keyboard essentials in R5 include table navigation, selection, opening/closing Inspector, focus-safe dialogs, Escape/close, and reachable actions. Broader accessibility remains R8, but basic usability cannot be deferred.

## 68. Proposed R5B-H Sequence

### R5B - Resource Catalog and Read Architecture

Preserve authoritative catalog SQL; introduce immutable scalar facts; add ID-driven Inspector and Resource summary/detail read foundation; add server-query contracts and catalog/Inspector responsive shell. Correct scoped uniqueness/read indexes needed by this read model.

### R5C - Resource Master Write UX

Implement ResourceKind and scoped Resource lifecycle; fix complete create/edit payloads; make version mandatory; move transaction ownership to caller/UoW for touched paths; add create/edit/deactivate/reactivate dialogs and Overview actions. No skill/certification or queue redesign yet.

### R5D - Resource Capability and Capacity

Harden Skills/Certifications end to end; add capability readers and deterministic requirement visibility; designate platform calendar + PM modifier + assignment commitments as one workload authority; implement bounded Availability facts; mark and retire superseded calculators after parity.

### R5E - Resource Project and Assignment Views

Add scoped paged Resource->Projects and Resource->Assignments readers; preserve ProjectResource and TaskAssignment ownership; add approved detail sections and bounded source navigation; add real Resource Activity projection without changing Tasks/Projects UI.

### R5F - Review Queue Redesign

Add versioned TimesheetPeriod transitions and atomic audit/outbox handling; formalize typed queue item/detail contracts; split reviewer controller/presenter concerns; implement server table, Inspector, dedicated decisions, deny-safe capabilities, conflict behavior, and targeted invalidation. Bulk remains deferred unless separately approved after single-item correctness.

### R5G - Responsive, Performance, and Integration Hardening

Validate all five viewports, keyboard essentials, popup/dialog geometry, 10k/50k data fixtures, query plans/budgets, scope/RLS, capability matrices, event refresh, and combined Resource/queue scenarios.

### R5H - Validation, Cleanup, and Closure

Run targeted then broad regression, delete every marked legacy/temporary path whose references are zero, remove stale compatibility internals without changing approved routes, reconcile docs, record performance/security evidence, and close R5 only when all gates pass.

## 69. Phase Exit Gates

| Phase | Required exit gate |
|---|---|
| R5B | Scalar immutable facts; Reader/Repository separation; scoped deterministic server queries; Inspector loaded by ID; catalog cross-page tests; <=4 statements; five-width shell characterization; no writes/queue redesign |
| R5C | ResourceKind/lifecycle approved; create/edit preserves every field; mandatory version conflicts; deny-safe actions; one mutation/audit transaction; responsive dialogs; no capability/Finance expansion |
| R5D | Skills/certs authorized, scoped, committed, versioned, audited, invalidated; one capacity authority; bounded workload projection; no N+1; capability UI responsive; no recommendations |
| R5E | ProjectResource/TaskAssignment ownership preserved; paged scoped sections; activity is authoritative; source navigation valid; large-section tests; no Tasks/Projects redesign |
| R5F | Queue remains projection; exact TimesheetPeriod source; conditional transitions; atomic audit/outbox; truthful capabilities/actions; dedicated reason UX; cross-page/scoped/concurrency tests; no generic review engine |
| R5G | Five viewports pass runtime geometry/keyboard tests; 10k/50k performance and query budgets pass; PostgreSQL RLS negative tests pass; event refresh is targeted; no cross-phase feature additions |
| R5H | Targeted and broad suites green; no known critical/high R5 defects; all temporary/legacy markers resolved by deletion or explicit future owner; docs and architecture diagrams match code; no dead QML/Python/contracts |

Every phase gate covers architecture, correctness, authorization, tenant/organization isolation, responsive behavior, tests, scalability, and explicit scope containment. A phase is not complete because its UI renders.

## 70. R5 / R6 Boundary

R5 owns Resource master, capability, availability/capacity, assignment/workload facts, and Timesheet Review Queue. R6 owns Finance, including financial rate strategy, budgeting, billing, accounting, and commercial reporting.

R5 may preserve existing rate fields and show only narrowly authorized context required for current behavior. It must not redesign rates, derive accounting truth, add budget controls, or couple workload readers to Finance aggregates. Project Finance remains managerial/commercial projection; Accounting remains authoritative for statutory and receivable facts.

## 71. R5 / R8 Boundary

R5 delivers usable responsiveness, truthful dialogs/actions, basic keyboard operation, stable focus, readable density, bounded popups, and deny-safe capability presentation. R8 retains broad accessibility conformance, platform-wide UI cleanup, generalized motion/polish, and non-R5 component modernization.

Resource and queue usability at the five required viewports is an R5 exit condition, not work deferred to R8.

## 72. Explicit Deferred Scope

The following are not part of R5 unless separately approved. R5F.1 supplied that later approval for one `Work -> Timesheets` destination only:

- HR/payroll, leave, performance management, recruitment, and employee master redesign.
- Automatic skill-based assignment, candidate ranking, AI recommendations, and opaque matching scores.
- Drag scheduling, resource leveling engine, and cross-project scheduling redesign.
- Financial budgeting, rate architecture, billing, invoicing, accounting, and Finance workspace redesign.
- Broad document management or certificate document repository.
- Generic multi-workflow Review Queue or persisted queue aggregate.
- Additional My Time, Time Entries, Workload, or Capacity destinations, or any Timesheets destination beyond the single R5F.1 workspace.
- Enterprise skill/certification taxonomy administration beyond the R5 foundations.
- Resource-by-time portfolio heatmap unless later evidence proves catalog/detail summaries insufficient.

## 73. Final Recommendation

Proceed to R5B only after approving this audit's product decisions. Preserve the existing canonical PM workspace and exactly two Workload Management destinations. Build from authoritative scoped read contracts outward, then correct Resource writes, capability/capacity, associations, and Review Queue in that order. Do not redesign visually around contracts that still permit silent data loss, stale approvals, fail-open actions, or cross-tenant ambiguity.

### Final decisions A-T

| Decision | Answer |
|---|---|
| A. What is Resource? | A tenant/organization-owned provider of schedulable PM delivery capacity, optionally linked to platform Employee identity. |
| B. Multiple types? | Yes: explicit `PERSON`, `CREW`, `EQUIPMENT`; separate from worker engagement and cost type. |
| C. Skills in R5? | Yes, foundation-quality CRUD, visibility, validation, audit, and concurrency. |
| D. Certifications in R5? | Yes, foundation-quality CRUD, expiry visibility, audit, and concurrency. |
| E. Structural owner? | ResourceSkill and ResourceCertification are bounded child entities/repositories scoped through Resource, not fields on a giant aggregate. |
| F. Resource Overview facts? | Identity, code, kind, status, role, employee/external relation, org/dept/site, calendar reference, availability modifier, version, and compact workload/capability summaries. |
| G. Inspector vs Detail? | Inspector contains fast identity/workload/warning/count facts and open/edit/lifecycle actions; full collections and history belong in Detail. |
| H. Detail sections? | Overview, Capability, Availability, Projects, Assignments, Activity, in that order. |
| I. Dialogs? | Create, Edit, Deactivate/Reactivate, Add/Edit Skill, Add/Edit Certification; exceptional hard purge is not normal UI. |
| J. Deactivate/delete? | Deactivate normally; purge only unused/unreferenced records under exceptional fail-closed administration; no bulk hard delete. |
| K. Workload/capacity facts? | Base calendar hours, modifier, effective capacity, commitments, actuals where authorized, remaining capacity, utilization, conflicts, and source/range freshness. |
| L. What does Review Queue review today? | TimesheetPeriod submissions only. TimeEntry/Resource/Task/Project are context. |
| M. Multiple review item types? | No in R5. Keep a typed discriminator for future extension without a generic queue entity. |
| N. Authoritative actions? | Approve and Reject/Return; Lock/Unlock only under explicit state and permission. Submit is not a reviewer action. |
| O. Queue Inspector? | Period/Resource/status/version/submission/hours/allocation/exceptions/submitter/history summary plus source navigation. |
| P. Bulk actions? | Defer by default. Do not retain current unsafe loops; later approval requires versioned server commands and honest per-item results. |
| Q. Queue history? | A filtered authoritative TimesheetPeriod projection plus append-only workflow audit/decision evidence; no second ledger. |
| R. Task/Project activity? | Yes as bounded, honestly attributed context in Resource Activity/Assignments and Queue Inspector; not a new destination. |
| S. Readers/contracts? | Replace mutable catalog facts; add Resource Inspector/summary/capability/workload/projects/assignments/activity and Queue Inspector/history readers with immutable facts. |
| T. Sequence? | R5B reads, R5C Resource writes, R5D capability/capacity, R5E project/assignment/activity, R5F queue, R5G hardening, R5H cleanup/closure. |

### Product approvals required before R5B

The audit is decisive, but these consequential product choices require owner approval rather than being inferred from implementation:

1. The `PERSON`, `CREW`, `EQUIPMENT` ResourceKind set.
2. The six-section Resource Detail order and removal of Cost Rates as an R5 primary section.
3. Skills and Certifications foundation inclusion, with automated matching deferred.
4. Review Queue limited to TimesheetPeriod and submit removed from reviewer UX.
5. Current bulk review and bulk Resource delete removed/deferred until safe server semantics exist.
6. Direct child-table RLS/schema hardening during R5 rather than repository-only protection.

### Required 42-item closure return

1. **Report path:** `docs/pm_modernization/R5A_WORKLOAD_MANAGEMENT_ENTERPRISE_AUDIT.md`.
2. **Executive conclusion:** the two-destination IA is correct; read foundations are promising; Resource writes/details and review concurrency/action truth require staged hardening.
3. **Current IA:** Workload Management -> Resources, Review Queue.
4. **Current Resources architecture:** QML/controller/presenter/desktop API -> query service -> SQL reader for catalog; service/repository fan-out for detail/writes.
5. **Current Review Queue architecture:** QML/controller/presenter/desktop API -> SQL projection -> authoritative TimesheetPeriod services for transitions.
6. **Resource domain:** scoped PM capacity record with identity, role, engagement, modifier, commercial fields, employee/org/dept links, lifecycle, and version.
7. **Current Resource meaning:** predominantly human employee/external labor; it cannot truthfully distinguish crew/equipment today.
8. **Skills exist:** yes, normalized ResourceSkill plus TaskSkillRequirement.
9. **Certifications exist:** yes, normalized ResourceCertification with contract inconsistencies.
10. **ProjectResource semantics:** Project-owned staffing membership and project-specific planning/commercial context.
11. **TaskAssignment semantics:** Task-owned execution commitment with allocation, hours, response state, dates inherited from Task, and version.
12. **Capacity authority:** platform calendar hours x Resource modifier, reduced by TaskAssignment commitments; older calculators are unreconciled.
13. **TimeEntry relevance:** actual workload and Timesheet review context only; not an R5 destination.
14. **Current queue item types:** TimesheetPeriod only.
15. **Queue state/actions:** OPEN/SUBMITTED/APPROVED/REJECTED/LOCKED; reviewer authority is approve/reject and permissioned lock/unlock.
16. **Catalog/DataTable problems:** mutable domain leakage, PII-heavy search, incomplete summaries; server paging/sorting itself is sound.
17. **Detail/Inspector problems:** no true Inspector, page-row detail seed, service fan-out, nine fragmented sections, pseudo-activity.
18. **Dialog problems:** capacity omitted/reset risk, incomplete independent scope selection, narrow two-column skill/cert forms, inconsistent date boundaries.
19. **Responsive problems:** no five-viewport runtime evidence, no adaptive Inspector, fixed forms, centered queue filter.
20. **Read-model problems:** Resource fact leaks domain entity; missing bounded detail facts; queue contract placement/completeness needs hardening.
21. **Scalability problems:** detail/service N+1 risk, Python capacity fan-out, unbounded history/associations, no 10k/50k benchmark evidence.
22. **Final IA:** exactly Resources and Review Queue under Workload Management.
23. **Resource Detail IA:** Overview, Capability, Availability, Projects, Assignments, Activity.
24. **Resource Inspector:** bounded identity, capacity/load, warnings, counts, version, and deny-safe actions.
25. **Resource dialogs:** Create, Edit, Deactivate/Reactivate, Add/Edit Skill, Add/Edit Certification.
26. **Skills decision:** foundation included in R5.
27. **Certification decision:** foundation included in R5.
28. **Matching decision:** deterministic visibility only; no recommendations or auto-assignment.
29. **Capacity presentation:** summary facts plus date-range allocation timeline; no required portfolio heatmap.
30. **Queue architecture:** disposable typed projection over authoritative TimesheetPeriod workflow.
31. **Queue UI:** server DataTable + bounded Inspector + dedicated approve/reject UX + truthful lock policy.
32. **Bulk recommendation:** remove/defer current unsafe bulk behavior.
33. **Activity/history:** append-only audit/activity projection; delete pseudo-history.
34. **Task/Project activity:** show only when authoritative links exist, with source navigation and no inferred attribution.
35. **Backend/domain/schema changes:** classified in sections 63-64, centered on immutable facts, scope, kind, version, transactions, audit, indexes, and RLS.
36. **QML redesign:** classified in sections 52-67, preserving canonical navigation and shared primitives.
37. **Sequence:** R5B through R5H as specified in section 68.
38. **Exit gates:** explicit architecture/correctness/security/responsive/test/scalability/scope gates in section 69.
39. **Owner approvals:** the six consequential decisions listed above require approval before R5B.
40. **Production code modified:** no.
41. **R5 implementation started:** no.
42. **Commit created:** no.

**Stop condition:** R5A ends with this audit. Do not begin R5B until the product approvals above are resolved.
