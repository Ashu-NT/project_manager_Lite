# R5E Resource Projects, Assignments, and Activity

## 1. Status

Implementation complete. Targeted backend, security, performance, migration, QML lint, and offscreen runtime validation pass. Because the application is pre-release, the Activity correlation schema is part of the authoritative fresh baseline and no upgrade-only compatibility revision is retained.

## 2. Scope

R5E completes Resource Detail Projects, Assignments, and Activity. It adds bounded Resource-oriented projections and read-only source navigation. It does not redesign Projects, Tasks, Time Entry, Review Queue, or Finance.

## 3. Ownership Guardrails

`Resource` remains the Resource master/capability owner. It does not contain ProjectResources, TaskAssignments, TimeEntries, or Activity collections. The new facts are disposable read projections, not aggregate state.

## 4. ProjectResource Semantics

`ProjectResource` remains Project-owned. `planned_hours` is the Project-level staffing control envelope, not physical capacity, assignment demand, or actual work. Resource Detail exposes no ProjectResource commands.

## 5. TaskAssignment Semantics

`TaskAssignment` remains Task-owned. `allocated_planned_hours`, `allocation_percent`, response status, schedule references, and version preserve their existing meanings. Resource Detail exposes no assignment create/update/delete path.

## 6. TimeEntry Boundary

`TimeEntry` remains actual-work authority. Task Detail -> Time remains present and unchanged. Resource Assignments consumes only assignment-linked TimeEntries and does not attribute generic TimeEntries to arbitrary Tasks.

## 7. Planned vs Actual Boundary

Project envelope, assignment planned work, and TimeEntry actual work remain distinct facts. Regression evidence uses `120 h` Project envelope, `70 h` assignment planned work, and `35 h` actual work; they are never added into a synthetic workload total.

## 8. Projects Read Architecture

Flow: QML server DataTable -> Resource controller query state -> Resource presenter -> Resources Desktop API -> `ResourceService.query_resource_projects_page()` -> `ResourceProjectsReader` -> SQL count/data query. The Reader joins ProjectResource, Resource, and Project without aggregate hydration or row fan-out.

## 9. ResourceProjectFact

`ResourceProjectFact` is frozen and scalar-only: ProjectResource ID, Resource ID, Project identity/code/name/status, planned envelope, active state, Project dates, version, and navigation capability. No ORM or domain entity crosses the Reader boundary.

## 10. Projects DataTable

Columns: Project, code, status, planned envelope, staffing state, and Project dates. Filters: search, active state, and Project status. Server sort allowlist: Project name/code/status, planned hours, start date, and end date. Stable ProjectResource ID is the tie-breaker. Pagination is pinned to the section bottom.

## 11. Project Permissions

The query requires `resource.read` and `project.read`, active tenant/organization scope, and intersects Project-scoped authorization. Hidden Project IDs, names, commercial facts, and navigation are omitted rather than redacted into identifiable placeholders.

## 12. Assignments Read Architecture

Flow: QML server DataTable -> independent controller query state -> presenter -> Desktop API -> `ResourceService.query_resource_assignments_page()` -> `ResourceAssignmentsReader` -> joined TaskAssignment/Resource/Task/Project SQL plus one grouped TimeEntry subquery. Count and data statements are independent of row count.

## 13. ResourceAssignmentFact

The frozen fact contains assignment/Resource IDs, authorized Project and Task identity, authoritative Task dates/status, allocated planned hours, allocation percent, actual hours/source, response status, optional ProjectResource ID, version, and source-navigation capabilities.

## 14. Assignments DataTable

Columns: Task, Project, schedule, planned hours, allocation, actual hours, Task status, and response. Filters: search, current/history/all lifecycle, Task status, response, Project ID at API level, and overlapping date range. Server sorts are allowlisted and use assignment ID as the deterministic tie-breaker. Pagination is pinned to the section bottom.

## 15. Actual Hours Source

Assignment-linked TimeEntries are summed in SQL. If no linked TimeEntry exists, validated synchronized `TaskAssignment.hours_logged` is used as a read optimization and the fact identifies that source. Actual hours are never mutable from Resource Detail.

## 16. Source Navigation

Open Project uses `pmNavigation.openEntity("projects", projectId, "overview")`. Open Task uses `pmNavigation.openEntity("tasks", taskId, "details")`. Navigation is emitted only when the authorized fact permits it.

## 17. Activity Authority

Resource Activity reads the existing shared `activity_entries` ledger. It does not infer history from current assignments and does not create a second ledger. Existing Resource lifecycle, capability, ProjectResource, and TaskAssignment commands supply authoritative evidence from implementation forward.

## 18. ResourceActivityReader

The bounded Reader selects direct Resource entries plus entries correlated through indexed generic `related_entity_type/id` fields. Staffing entries are additionally intersected with Project/Task Project authorization. Query failures remain section errors and do not become empty-history states.

## 19. Activity Fact

`ResourceActivityFact` is frozen and deny-safe: activity ID, Resource ID, occurrence time, event/category, safe actor label, summary, source type/ID, authorized Project/Task references, and navigation capability. Raw JSON payloads are not exposed to QML.

## 20. Activity Categories

Supported bounded categories are All, Resource, Capability, Projects, Assignments, and Work. Default order is timestamp descending then activity ID descending. Date range and pagination are server-owned.

## 21. Pseudo-Activity Removal

The old assignment-snapshot builder, serializer, presenter helper, and deferred QML placeholder were deleted. Resource Activity now uses the shared `ProjectManagement.Widgets.ActivityLogSection` presentation in server mode. No legacy fallback or pseudo-history reconstruction remains.

## 22. Security / Scope

All Readers require explicit tenant and organization IDs and first prove the Resource exists in that scope. Projects and Assignments join only same-scope Resource/Project rows. Activity applies tenant/org/module scope and separate Project permission allowlists for ProjectResource and TaskAssignment evidence. Actor identity is displayed as `System` or `Authorized user`; raw identity/payload data do not leak.

## 23. Events / Invalidation

Project changes refresh loaded Projects and Activity. Task/Time changes refresh loaded Assignments, Availability, and Activity. Resource changes refresh loaded Activity. Lazy sections that were never opened are not queried. Resource selection increments request generations, clears all three contexts, and prevents late responses from replacing the current Resource. Capability changes do not reload Projects.

## 24. Responsive Matrix

Projects, Assignments, and Activity were instantiated offscreen at `1024x640`, `1280x720`, `1366x768`, `1440x900`, and `1920x1080`. All 15 combinations place the pagination bottom edge at the section bottom. The outer detail page remains the single vertical scroll owner; Projects/Assignments use bounded DataTables and Activity uses the shared Activity Log.

## 25. Query Plans / Indexes

Existing `idx_project_resource_resource` supports Resource Projects. The fresh baseline includes `idx_task_assignments_resource` for Resource Assignments and `idx_activity_related(related_entity_type, related_entity_id, timestamp)` for shared-ledger correlation. Existing Task Project, TimeEntry assignment, Activity entity, tenant/org timestamp, and workspace indexes support joins and scope. PostgreSQL EXPLAIN was unavailable in this SQLite development run.

## 26. Projects Performance

Measured with 1,000 ProjectResource relationships: page 20 at 25 rows returned in `8.10 ms` using three statements (entitlement authorization, count, data). Statement count is independent of returned rows.

## 27. Assignments Performance

Measured with 10,000 TaskAssignments: page 200 at 25 rows returned in `74.75 ms` using three statements. Task, Project, and actual-hours resolution are joined/aggregated; there is no per-row lookup.

## 28. Activity Performance

Measured with 10,000 correlated assignment events plus Resource creation: page 200 at 25 rows returned in `21.87 ms` using three statements. Indexed correlation replaces serialized-details scanning.

## 29. Tests

Dedicated R5E correctness/runtime suite: `25 passed`. Dedicated scale suite: `1 passed`. Final targeted R5E/Resource/shared-Activity/migration matrix: `78 passed`. Shared Project Activity regression: `36 passed`. Earlier Desktop/presenter compatibility checkpoint: `17 passed`; broader Resource/capability checkpoint: `50 passed` with one obsolete R5B assertion subsequently corrected. Targeted `qmllint` is silent, Python compilation passes, and `git diff --check` passes. No full suite was run by request.

## 30. Explicit Deferred Scope

Deferred to later approved phases: Review Queue redesign (R5F), Finance (R6), Project/Task redesign, assignment write UX, Time Entry redesign, automatic matching, and resource leveling changes. PostgreSQL-specific EXPLAIN/ANALYZE remains deployment validation, not a hidden implementation dependency.

## 31. R5F Handoff

R5F owns the TimesheetPeriod Review Queue projection and OPEN/SUBMITTED/APPROVED/REJECTED/LOCKED workflow, reviewer Approve/Reject and permissioned Lock/Unlock commands, optimistic concurrency, transaction/audit consistency, and deny-safe QML actions. R5E does not alter that workspace.
