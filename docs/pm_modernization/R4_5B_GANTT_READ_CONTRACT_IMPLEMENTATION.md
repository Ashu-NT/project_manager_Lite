# R4.5B Gantt Read Contract Implementation

**Status:** COMPLETE  
**Handoff status:** R4.5B-H complete; R4.5 closed
**Commit:** none created

## Boundary

R4.5B implements data ownership, typed projection, indexing, selection, and local-view foundations. It does not introduce the specialized Gantt visual surface, dependency Canvas, baseline visuals, time header, zoom, timescale, or R5 workload features. Canonical CPM, dependency, constraint, calendar, leveling, and Schedule Impact semantics remain unchanged.

The Gantt projection is disposable. It is rebuilt from authorized application services after authoritative project/task/dependency/calendar/baseline changes and is never persisted as schedule truth.

## Files Changed

The R4.5B working tree contains 25 modified files and 9 new files:

```text
docs/pm_modernization/R4_5_GANTT_ENGINEERING_AUDIT.md
docs/pm_modernization/R4_5B_GANTT_READ_CONTRACT_IMPLEMENTATION.md
src/core/modules/project_management/api/desktop/__init__.py
src/core/modules/project_management/api/desktop/scheduling/__init__.py
src/core/modules/project_management/api/desktop/scheduling/api.py
src/core/modules/project_management/api/desktop/scheduling/builders/__init__.py
src/core/modules/project_management/api/desktop/scheduling/builders/gantt_builder.py
src/core/modules/project_management/api/desktop/scheduling/factories/scheduling_api_factory.py
src/core/modules/project_management/api/desktop/scheduling/models/__init__.py
src/core/modules/project_management/api/desktop/scheduling/models/gantt.py
src/core/modules/project_management/api/desktop/scheduling/models/schedule.py
src/core/modules/project_management/api/desktop/scheduling/serializers/schedule_serializer.py
src/core/modules/project_management/api/desktop_runtime/desktop_api_builder.py
src/core/modules/project_management/api/desktop_runtime/service_resolver.py
src/core/modules/project_management/application/scheduling/baselines/baseline_service.py
src/core/modules/project_management/domain/scheduling/baseline.py
src/core/modules/project_management/infrastructure/persistence/mappers/baseline.py
src/core/modules/project_management/infrastructure/persistence/orm/baseline.py
src/infra/persistence/migrations/versions/f3c89cac079d_initial_schema.py
src/tests/project_management/test_baseline_domain_validation.py
src/tests/project_management/test_baseline_milestone_migration.py
src/tests/project_management/test_qml_project_management_presenters_scheduling.py
src/tests/project_management/test_r4_5b_gantt_read_contract.py
src/ui_qml/modules/project_management/controllers/scheduling/gantt_legacy_adapter.py
src/ui_qml/modules/project_management/controllers/scheduling/gantt_list_model.py
src/ui_qml/modules/project_management/controllers/scheduling/gantt_selection.py
src/ui_qml/modules/project_management/controllers/scheduling/scheduling_selection_actions.py
src/ui_qml/modules/project_management/controllers/scheduling/scheduling_state_loader.py
src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py
src/ui_qml/modules/project_management/controllers/scheduling/state.py
src/ui_qml/modules/project_management/presenters/scheduling/option_resolver.py
src/ui_qml/modules/project_management/presenters/scheduling/record_mappers.py
src/ui_qml/modules/project_management/presenters/scheduling/workspace_builder.py
src/ui_qml/modules/project_management/view_models/scheduling.py
```

No production QML visual file was changed.

## Typed Contracts

The transport-neutral contracts are in `api/desktop/scheduling/models/gantt.py`:

- `GanttTaskRowDto`: explicit tenant, organization, project, task identity, authoritative `Task.code`, hierarchy facts, canonical schedule/latest/actual facts, date ordinals, status/progress, explicit milestone, critical/infeasible flags, constraints, deadline, and authority-presence state;
- `GanttDependencyEdgeDto`: explicit scope, stable edge/endpoints, FS/SS/FF/SF type, and signed lag;
- `GanttBaselineTaskSnapshotDto`: explicit scope, baseline/task identity, immutable dates/duration/milestone, and date ordinals;
- `GanttProjectionDto`: selected scope/project, `canonical` authority status, optional selected baseline, complete rows, complete project edges, and baseline snapshots.

No DTO contains ORM objects, mutable aggregates, QML pixel geometry, free float, resource lanes, or page state.

## Projection Assembly

`gantt_builder.build_gantt_projection()` performs an indexed merge:

1. consume canonical WBS preorder hierarchy nodes;
2. index canonical leaf CPM DTOs by stable task ID;
3. traverse nodes once in reverse order and merge each child aggregate into its parent;
4. emit rows in original canonical WBS preorder;
5. validate and deterministically sort project edges;
6. validate and map selected-baseline snapshots.

The merge is O(N + E + B) time and O(N + E + B) memory for N hierarchy rows, E edges, and B baseline snapshots. Summary dates, progress, status, criticality, and infeasibility are display rollups only. Summary tasks are never supplied to CPM and never create new dependency semantics.

Canonical schedule input remains the complete project graph. The target projection has no Gantt pagination. R4.5C now feeds the production viewport directly from `GanttListModel`; the temporary page adapter and duplicate collections have been deleted.

## Authority And Scope

`ProjectManagementSchedulingDesktopApi.build_gantt_projection()` requires:

- active tenant and organization IDs from `TenantContextService`;
- an authorized project lookup;
- the real `SchedulingEngine`;
- the authorized task hierarchy and project dependency reads;
- the permission-checked baseline bulk read when a baseline is selected.

Missing SchedulingEngine or TenantContextService fails closed. A project with explicit tenant/organization facts that differs from active scope is rejected before CPM. Project tasks and dependency endpoints are validated before merge; mixed-baseline snapshot input is rejected.

The canonical merge also fails closed for duplicate schedule task IDs, foreign-project schedule rows, or any mismatch between the hierarchy leaf-task set and CPM output. A partial result cannot be labeled canonical.

Production runtime composition now passes `tenant_context_service` explicitly through the desktop runtime service resolver and Scheduling API factory.

## Baseline Snapshot

`BaselineTask.baseline_is_milestone` is a new immutable historical fact. It is:

- copied from `Task.is_milestone` during baseline capture;
- persisted by `BaselineTaskORM` and its mapper;
- present in the clean pre-release Alembic baseline;
- returned by `BaselineService.list_baseline_tasks()` through one scoped repository list query;
- exposed by the typed Gantt baseline snapshot with raw dates and ordinals.

Changing the current task after capture does not change the existing snapshot. Milestone identity is never inferred from duration or equal dates.

## Indexed Model

`GanttListModel` is one compact `QAbstractListModel`; it does not create per-row Python `QObject` wrappers. It owns:

- immutable complete rows;
- O(1) `task_id -> row` lookup;
- O(1) `dependency_id -> edge` lookup;
- indexed `task_id -> incident edge IDs` adjacency;
- O(1) `task_id -> baseline snapshot` lookup;
- local effective rows and hierarchy/flat presentation state.

Hierarchy mode preserves canonical WBS preorder. Arbitrary sort activates flat mode and reports zero display depth; missing sort values remain last in both directions. The locked default expansion includes summary rows through depth one; deeper summaries remain collapsed. Search/filter results include truthful ancestor context in hierarchy mode.

## Selection Ownership

`set_gantt_selection()` resolves rows from the O(1) model index and assigns `selectedActivityId` and `selectedActivity` before emitting either signal. The invariant is:

```text
selectedActivityId == selectedActivity.taskId
```

or both are empty. No first row is automatically selected. Selection clears on project change or when a local filter excludes the selected task. Selection performs no CPM call, repository query, presenter rebuild, or timer refresh.

## Local View Separation

Search, status filter, critical-only filter, delayed-only filter, sort, and hierarchy expansion call the local indexed model path. They do not call `controller.refresh()` and therefore do not rerun SchedulingEngine. The production Gantt has no page or page-size state.

**R4.5C deletion completed:** `gantt_legacy_adapter.py`, its imports, the paginated Gantt `DataTable`, and `SchedulingTimelinePanel` were deleted. No compatibility shim or duplicate production renderer remains.

## Invalidation

Existing PM domain subscriptions rebuild the disposable projection for project, project-task/dependency, project-baseline, resource, and working-calendar changes. Project switch, baseline selection, explicit refresh, CPM recomputation, and accepted leveling continue through authoritative refresh. UI-only selection/filter/sort/page operations remain local.

## Performance

Measurements use the `pmenv` interpreter on the current development machine. Setup data creation and canonical CPM/database work are excluded. Projection includes hierarchy merge, complete dependency mapping, baseline mapping, and date ordinals. Index measurement includes row, edge adjacency, baseline, and effective-row construction.

| Rows | Projection | Model/index | Peak measured allocation |
|---:|---:|---:|---:|
| 100 | 11.560 ms | 3.211 ms | 0.133 MiB |
| 1,000 | 164.675 ms | 7.309 ms | 1.271 MiB |
| 5,000 | 746.510 ms | 38.346 ms | 5.923 MiB |

The 5,000-row projection is below the R4.5A 1,000 ms target. Growth is consistent with the O(N + E + B) implementation; no per-node descendant scan or N+1 baseline read exists.

## Verification

Focused coverage proves:

- authoritative code and same-day non-milestone distinction;
- hierarchy facts, summary rollups, deterministic preorder, and flat-sort semantics;
- FS/SS/FF/SF edges with negative, zero, and positive lag;
- edge adjacency and baseline indexes;
- baseline bulk scope, explicit milestone capture, immutability, and fresh-schema persistence;
- canonical/degraded authority behavior;
- fail-closed duplicate, incomplete, and cross-project canonical schedule input;
- tenant/organization/project rejection boundaries;
- no auto-selection and atomic selected ID/detail state;
- local operations do not invoke refresh/CPM;
- 100/1,000/5,000 projection and index construction;
- affected Scheduling, baseline, hierarchy, dependency-performance, persistence-security, and QML IA regressions.

The final affected R4.5B matrix completed with 66 passing tests. `ruff` was unavailable in `pmenv`; targeted Python compilation completed successfully. No full test suite was run, per the targeted-test constraint.

## R4.5C Closure

R4.5C consumes `controller.ganttRowsModel` directly and provides:

1. the specialized integrated row viewport;
2. one vertical row authority for frozen grid and timeline lane;
3. one horizontal timeline authority;
4. direct row/bar selection through the existing atomic controller seam;
5. responsive Grid/Timeline/Split composition required by C.

R4.5C added no dependency Canvas, baseline visuals, timescale/zoom, or R5 resource lanes. The adapter and independently scrolling timeline path are removed. Exact measurements, verification, and the R4.5D handoff are recorded in `R4_5C_GANTT_VIEWPORT_IMPLEMENTATION.md`.

## Final R4.5H Reconciliation

R4.5H confirmed this projection remains the only production Gantt read path,
removed the remaining duplicate Scheduling detail/dependency side-channel, and
passed the final architecture, runtime, scope, and broad PM regression gates.
The authoritative final state is recorded in `R4_5_GANTT_CLOSURE.md`.
