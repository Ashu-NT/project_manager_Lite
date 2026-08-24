# R5D Resource Capability and Capacity

## 1. Status

**IMPLEMENTED; FINAL CLOSURE GATES IN PROGRESS.** R5A-R5C are the approved baseline. Resource Detail `Capability` and `Availability` are now production-backed; R5D stops before R5E, R5F, and R6. The remaining work is final targeted reconciliation of all R5D closure gates, not product implementation for deferred sections.

## 2. Scope

R5D hardens ResourceSkill and ResourceCertification CRUD/read contracts, deterministic task-requirement visibility, and one bounded calendar-backed workload projection. Resource master lifecycle, Resource Projects/Assignments/Activity UI, Tasks, Time Entry, Review Queue, Finance, resource leveling behavior, recommendation, ranking, and auto-assignment are excluded.

## 3. Capability vs Capacity

Capability answers what a Resource is qualified to perform. Capacity answers how much calendar-derived working time exists and how much TaskAssignment demand consumes it. They remain separate contracts and independently lazy Resource Detail sections.

## 4. ResourceSkill Ownership

ResourceSkill remains a versioned child entity of Resource with its own repository. Resource does not hydrate a mutable skills collection. The current facts are ID, Resource ID, normalized code, name, proficiency, notes, and version.

## 5. ResourceCertification Ownership

ResourceCertification remains a versioned child entity of Resource. It is not embedded in Resource aggregate hydration and does not introduce document management.

## 6. Skill Contract

The canonical proficiency values remain `BEGINNER`, `INTERMEDIATE`, `ADVANCED`, and `EXPERT`. Codes are normalized case-insensitively and unique per Resource. The read contract will be immutable, scalar-only, scoped, filterable, sortable, and bounded.

## 7. Certification Contract

Canonical vocabulary is `certificate_number`, `issuer`, `issued_at`, and `expires_at` at application/read/UI boundaries. Existing SQL columns may be migrated explicitly; duplicate `issuing_body` and `issuing_authority` aliases must not remain in final production contracts.

## 8. Certification Status/Expiry Policy

Status is derived, never persisted: `NO_EXPIRY`, `VALID`, `EXPIRING_SOON`, or `EXPIRED`. The product threshold is one backend policy constant, initially 30 calendar days inclusive. QML and SQL must not duplicate the threshold.

## 9. Capability Commands

Typed commands cover add, edit, and remove for both child types. Edit/remove require child ID and `expected_version`; all commands identify the parent Resource where needed and validate normalized facts before persistence.

## 10. Capability Permissions

`resource.read` protects capability reads and `resource.manage` protects all mutations. QML capability visibility is deny-safe but is not an authorization boundary. Repository parent scoping remains a second tenant/organization defense.

## 11. Capability Concurrency

Updates and removals compare `expected_version` with the scoped current row and raise typed `ConcurrencyError` on stale actions. Updates increment exactly once. No stale delete is silently accepted.

## 12. Capability Transactions

Repositories flush but never commit. A caller-owned capability unit of work encloses child mutation plus audit staging, commits once, rolls back on failure, and dispatches notifications only after commit.

## 13. Capability Events

Targeted post-commit events identify tenant, organization, Resource, child ID, child version, child type, and change type. They invalidate only Resource Capability and bounded Resource summaries that actually include capability counts.

## 14. Task Requirement Visibility

TaskSkillRequirement is task-owned and already supports either a skill code or certification code with `WARN`, `BLOCK`, or `OVERRIDE`. R5D consumes these facts without redesigning task writes.

## 15. Explicit Matching Boundary

Comparison outcomes are deterministic and explainable: `SATISFIED`, `MISSING`, `INSUFFICIENT_PROFICIENCY`, or expired/missing certification where an authoritative certification requirement exists. R5D implements no score, candidate ranking, recommendation, or automatic assignment.

## 16. Capacity Authority Inventory

- `EnterpriseCalendarResolver` is Platform working-time authority and owns calendar precedence, holidays, exceptions, and working hours.
- `EnterpriseResourceAvailabilityService` adapts Resource/Employee identity to that resolver but does not apply `Resource.capacity_percent` or TaskAssignment demand.
- `ResourceCapacityCalculator` aggregates resolver output but currently omits the Resource modifier, clamps remaining hours, and needs caller-supplied demand.
- `compute_resource_capacity_from_assignments` was an unreferenced transitional Resource-detail helper and has been deleted.
- `ResourceAvailabilityService` was an obsolete percent/day implementation. Its file, exports, desktop API parameter, runtime resolver field, service-graph field/key, composition construction, and legacy tests have been deleted.
- `evaluate_task_assignment_capacity` applies the modifier and exact Decimal math but currently limits existing load to one project; it is an adapter candidate, not a second truth.
- `ResourceLoadEngine` and portfolio pool calculations serve scheduling/dashboard/portfolio consumers and require classification/parity before deletion or adaptation.

## 17. Canonical Capacity Contract

For an explicit inclusive interval: `effective capacity = enterprise calendar available hours x Resource.capacity_percent / 100`; `remaining = effective capacity - planned TaskAssignment commitment`; `planned utilization = commitment / effective capacity`. Remaining and utilization are not clamped, so overload remains visible.

## 18. Calendar Authority

Only EnterpriseCalendarResolver-derived contexts may supply working days/hours, holidays, exceptions, and fallback chains. No QML weekday math and no PM Monday-Friday shortcut is permitted.

## 19. Resource Capacity Modifier

`Resource.capacity_percent` is a macro availability modifier applied exactly once to calendar availability. Zero is valid zero capacity and must never become 100 through truthiness fallback.

## 20. ProjectResource Boundary

ProjectResource remains Project-owned staffing context. Its planned hours and allocation are not Resource master capacity and do not replace TaskAssignment demand.

## 21. TaskAssignment Demand

TaskAssignment is the planned commitment authority. Its allocation percentage applies across the authoritative Task planned interval; `allocated_planned_hours`, where populated with authoritative semantics, must be preserved rather than silently reinterpreted. Actual TimeEntry hours remain separate.

## 22. Date Range / Granularity

Every workload query requires an explicit inclusive start/end and rejects invalid or unbounded ranges. Resource Detail uses a bounded daily fact set with product-controlled maximum range and supports controlled range presets/custom dates.

## 23. Multi-Project Aggregation

Resource Availability aggregates all in-scope overlapping TaskAssignments across projects in one bounded read, with batched task lookup/SQL aggregation. Project selection may filter an authorized view but cannot redefine Resource-wide capacity truth.

## 24. Authorization / Hidden Project Policy

Resource-level capacity totals include authorized aggregate commitments only. Protected project/task identities and titles are never exposed. If the permission model requires hidden commitments to influence conflict safety, they may contribute to redacted aggregate demand only under an explicit tested policy; detail rows remain omitted.

## 25. ResourceWorkloadFact

The final immutable Decimal-safe fact includes Resource ID, range, calendar source chain, base hours, capacity modifier, effective hours, planned committed hours, remaining hours, utilization, over-allocation, conflict dates, project/assignment counts, and immutable daily facts. Zero-capacity outcomes are explicit and division-safe.

## 26. Availability Read Architecture

Implemented flow: Resource Detail -> desktop API -> `ResourceWorkloadService` -> tenant/organization-scoped `SqlAlchemyResourceWorkloadDemandReader` overlap query plus `EnterpriseResourceAvailabilityService` -> immutable `ResourceWorkloadFact` -> desktop DTO -> presenter/controller -> QML. SQL filters TaskAssignment demand by the explicit Task date overlap before materialization. Query failures remain section failures, not empty facts.

## 27. Catalog Summary Integration

No workload enrichment is added to the R5B catalog unless it can be produced in bounded set-based statements without per-Resource calendar or assignment queries. The current server-authoritative catalog remains unchanged during the first R5D cut.

## 28. Inspector Enrichment

Capability/workload counts may be added only as bounded scalar facts. Inspector selection must not load skill/certification collections or a full workload range.

## 29. Capability UI

Capability remains one Resource Detail destination containing Skills and Certifications. Both use shared server-mode DataTables with explicit empty/error/busy states and contextual add/edit/remove actions. Dialogs support create/edit, field errors, busy/duplicate-submit safety, and stale conflict messaging.

## 30. Availability UI

Implemented. Availability lazy-loads only when its Resource Detail destination is active. Shared 30/60/90-day presets and custom bounded dates sit above two result tabs because the selected range governs both: `Summary` owns capacity/commitment/remaining/utilization metrics plus calendar/workload context, while `Daily Availability` owns the read-only daily DataTable. The section performs no working-day or capacity calculation in QML and exposes no editable calendar rules or fabricated project/task navigation.

## 31. Responsive Matrix

Validate 1024x640, 1280x720, 1366x768, 1440x900, and 1920x1080. Compact layouts stack bounded summaries and forms, keep actions/range controls reachable, and retain a usable table fallback; wide layouts allocate additional width to workload visualization without unbounded form stretching.

## 32. Legacy Capacity Implementations

Classification is complete for the Resource Detail path. `EnterpriseCalendarResolver` and `EnterpriseResourceAvailabilityService` remain calendar authority/adapters; `ResourceWorkloadService` plus its bounded SQL demand reader own Resource Detail workload truth; `evaluate_task_assignment_capacity` remains the Task command preview/enforcement path; `ResourceLoadEngine` and portfolio readers remain distinct set-based projections. R4.4 scheduling semantics were not changed.

## 33. Legacy Deletions / Adapters

Completed retirement: `ResourceAvailabilityService` and `compute_resource_capacity_from_assignments` were deleted after zero-production-reference verification. All percent-based service DI aliases and constructor parameters were removed rather than retained as compatibility code. `evaluate_task_assignment_capacity` remains because Tasks actively use it for assignment preview and save-time enforcement against the enterprise calendar adapter; it is not transition-only dead code.

## 34. RLS / Scope

Child access inherits tenant/organization ownership through the scoped Resource parent. PostgreSQL RLS must cover ResourceSkill and ResourceCertification through parent-scope policy or equivalent direct scope columns. Direct cross-tenant and cross-organization reads/writes must fail independently of application filters.

## 35. Performance

Capability lists are paged and measured at 10/100/1,000 rows. Single-Resource Availability targets local warm p95 <= 300 ms for normal bounded ranges. SQL statement count must be bounded by query shape, not Resource or assignment count; any catalog/Inspector enrichment requires regression benchmarks.

## 36. Test Results

Availability/capability focused suite: **58 passed** covering canonical R4.3 capacity regression, R5B Resource reads/runtime geometry, R5D bounded workload/range/permission/scope/QML contracts, capability controller, and secondary-write tenant hardening. Python targeted compilation passed. `qmllint` passed for `ResourcesAvailabilitySection.qml`; shared page lint reports only pre-existing generated-QML-type metadata warnings. `git diff --check` is part of the final exit pass. Optional `ruff` was unavailable in `pmenv` (`No module named ruff`).

## 37. Explicit Deferred Scope

Deferred: taxonomy management, certification documents, HR compliance/training, Resource Projects, Resource Assignments, Resource Activity, task write redesign, candidate matching/ranking, recommendations, auto-assignment, Time Entry, Review Queue, portfolio heatmaps, Resource Leveling changes, and Finance/rates.

## 38. R5E Handoff

R5E owns paged Resource-to-ProjectResource and Resource-to-TaskAssignment projections, source navigation, planned-versus-actual context, authoritative Resource Activity, pseudo-activity deletion, and responsive large sections. ProjectResource remains Project-owned, TaskAssignment Task-owned, and TimeEntry actual-work authority.
