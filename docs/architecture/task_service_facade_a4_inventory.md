# A4 TaskService Facade Inventory

Status: incremental cutover; TaskService facade simplification is not closed.
Scope: production callers in `src/core/modules/project_management`, desktop
runtime/API, composition and importers. Test fixture callers are retained as
regression constraints, not as a reason to preserve private APIs indefinitely.

## Baseline and decision

The current facade was 816 lines at the start of this audit, not 1,898 lines.
Earlier A4 extractions already moved operation logic to injected handlers. It
has 77 methods including `__init__`; nearly all remaining methods forward to
handlers. Do not replace it with several forwarding-only facades. The first
verified cut brings it to 798 lines and 76 methods including `__init__` by
removing four unused constructor inputs and one dead private delegate. The
guarded facade remains the desktop-facing compatibility boundary
until adapter capability injection and module-entitlement checks are migrated
together. Pre-release compatibility is not a reason to retain it permanently.

## Method-to-consumer map

The methods below are grouped only when they have the same authority,
implementation owner and consumer boundary. Each name is listed explicitly.

| Classification / handler | Methods | Production consumers and disposition |
| --- | --- | --- |
| Command / deletion | `delete_task`, `delete_tasks` | Tasks desktop API; keep guarded facade until API receives explicit command capability. |
| Command / assignment | `assign_resource`, `assign_project_resource`, `unassign_resource`, `set_assignment_hours`, `set_assignment_allocation`, `update_assignment_planned_hours`, `accept_assignment`, `decline_assignment` | Tasks desktop API and import/test setup; Timesheets desktop uses the composed assignment handler only for a scoped read. Preserve skill/capacity checks and one UoW. |
| Assignment reads / assignment handler | `list_assignments_for_task`, `get_assignment`, `get_task_time_summary`, `preview_assignment_capacity`, `get_assignment_action_context` | Tasks/Timesheets desktop APIs and Dashboard; split command/read injection only after module-guard and read permission equivalence is proved. |
| Command / dependency | `add_dependency`, `remove_dependency`, `update_dependency` | Tasks/Scheduling desktop APIs; ordinary command path owns its UoW. |
| Dependency reads / query handler | `get_dependency`, `list_dependencies_for_task`, `list_dependencies_for_project` | Tasks/Scheduling desktop APIs; query handler is already scoped. |
| Command / lifecycle and WBS | `create_task`, `update_task`, `move_task`, `recode_task` | Tasks desktop API and CSV importer; importer uses several capabilities and may justify one narrow import workflow rather than full TaskService. |
| Command / constraint and leveling | `update_task_scheduling_constraint`, `build_resource_leveling_preview`, `apply_resource_leveling_plan` | Scheduling desktop API; keep approval-controlled execution distinct from ordinary command UoW. |
| Command / progress | `set_status`, `set_tasks_status`, `update_progress` | Tasks desktop API and CSV importer; progress handler owns validation/UoW. |
| Command / hierarchy | `move_task`, `recode_task` | Tasks desktop API and CSV importer; hierarchy handler owns subtree checks/UoW. |
| Time bridge / time-entry handler | `initialize_timesheet_for_assignment`, `list_time_entries_for_assignment`, `list_time_entries_for_task_page`, `list_time_entries_for_assignment_period`, `get_time_entry`, `add_time_entry`, `update_time_entry`, `delete_time_entry`, `list_timesheet_periods_for_resource`, `list_time_entries_for_resource_period`, `submit_timesheet_period`, `approve_timesheet_period`, `reject_timesheet_period`, `lock_timesheet_period`, `unlock_timesheet_period`, `reopen_approved_timesheet_period_for_correction` | Tasks/Timesheets desktop APIs; preserve Time-owned evidence and timesheet authority; avoid exposing Task UoW as Time UoW. |
| Detail/hierarchy queries | `get_task`, `list_task_hierarchy`, `list_leaf_tasks_for_project`, `get_task_hierarchy_rollup`, `list_task_hierarchy_rollups` | Tasks/Scheduling desktop APIs, dashboard helpers, importers; existing detail/hierarchy handlers are candidates for narrow injection. |
| Dependency diagnostics queries | `get_dependency_diagnostics`, `preview_dependency_removal` | Tasks/Scheduling desktop APIs; existing diagnostics handler is candidate for narrow injection. |
| Lookup queries | `list_tasks_for_project`, `list_tasks_for_resource`, `list_assignments_for_resource`, `query_tasks` | CSV import and Timesheets desktop now use the lookup handler directly; Tasks/Scheduling desktop APIs use remaining facade methods. The lookup handler enforces task/project permissions; callers retain their module guards. |
| Page queries | None remain on TaskService | Tasks desktop now receives the composed detail and workspace query handlers directly; Dashboard receives the workspace handler. Readers own paging/sorting and DTO projection, not QML. |
| Warning sidecars / assignment handler | `consume_last_overallocation_warning`, `consume_last_skill_violation_warning` | Tasks desktop API; preserve consumption timing until warning output is part of an explicit result contract. |
| Approval participant / dependency handler | `_apply_dependency_add_decision`, `_apply_dependency_remove_decision`, `_apply_dependency_update_decision` | `infrastructure/approval/task_apply_participant.py` only. These are participant-owned, not public commands; migrate participant and shared UoW/event scope together. |
| Approval participant / constraint and leveling handlers | `_apply_task_scheduling_constraint_decision`, `_apply_resource_leveling_plan_decision` | Same Task approval participant; preserve outer approval transaction and event drain. |
| Financial Change participant / schedule handler | `_validate_approved_schedule_changes`, `_apply_approved_schedule_changes` | `application/financials/financial_changes/service.py`; preserve Financial Change's transaction boundary and task event handling. |
| Shared transaction/event scope | `_take_pending_task_events` | Task approval participant and Financial Change service; TaskUowScope is the actual owner. Do not remove until both consumers receive one correctly scoped event capability. |

`_validate_constraint_date_is_working_day` had no production caller and was
deleted. The facade contains no remaining shared policy/validation calculation
or genuine multi-handler orchestration; private approval forwarding is an
integration boundary, not an ordinary public command. The facade's direct
`session`, repositories, scheduler, activity/approval and audit attributes are
not used by its methods but some current composition tests inspect them. Those
tests must move to the actual handler/UoW before the fields are deleted.

## Capability and lifetime design

- Reuse the existing lifecycle, assignment, dependency, progress, hierarchy,
  constraint, leveling, time, detail, lookup and page handlers. Avoid a new
  command bus, registry or one-method Protocols.
- Module-owned composition should expose typed Task capabilities with the same
  request/approval-participant lifetime as their current TaskService instance.
  Do not build a second session or handler graph for the same operation.
- Desktop and future HTTP adapters should receive the capabilities they use.
  Direct injection must preserve the current module-entitlement guard as well
  as handler permission/project checks; handler authorization alone is not
  equivalent to the guarded facade.
- Approval participant and Financial Change migrations must retain the outer
  transaction's UoW and pending-event drain. No ordinary command method may
  replace their participant apply entry point.
- Dashboard now receives the existing lookup and assignment handlers from a
  typed PM Task composition result. Its own module guard remains active.
- CSV import now receives only lifecycle, hierarchy, progress and lookup
  handlers through `TaskImportCapabilities`; `DataImportService` retains its
  module guard. The handlers retain their authorization and UoW ownership.

## Verification and remaining gate

This slice removed `work_calendar_engine`, `project_repo`,
`tenant_context_service` and `task_workspace_reader` from TaskService's
constructor. Their authoritative users remain the injected handlers/readers.
The facade's constructor shrank from 31 to 27 inputs. Focused assignment and
approval participant tests passed 48 cases after the cut. Facade forwarding
count is not yet materially reduced; the next slice must migrate a real
consumer before deleting its forwarding methods. PostgreSQL/RLS and broader
desktop/Task integration verification remain required for A4 closure.

The subsequent Dashboard/CSV import cut migrated two internal consumers off
TaskService without creating another forwarding facade. The retired
`list_assignments_for_tasks` facade delegate had no remaining production or
dynamic caller; Dashboard calls the existing batched lookup handler directly.
The facade is now 795 lines, 75 methods including `__init__`, and 27
constructor inputs (from 816/77/31 at the start of this audit). Focused
Dashboard/composition/WBS tests passed 52 cases; import regressions passed 44;
architecture guards passed 26; module-guard/permission/lookup tests passed 45;
Dashboard batching measurement passed 2; live PostgreSQL security/RLS passed
14. At that checkpoint Desktop Tasks, Scheduling, Timesheets and Dashboard adapters still received
the large facade, as did Task approval and Financial Change participants. Those
callers must be migrated before their forwarding methods can be removed; A4
facade completion is not yet established.

The Dashboard delayed-tasks desktop adapter now receives the existing
`TaskWorkspacePageQueryHandler` directly from PM composition, rather than the
entire TaskService. Its desktop boundary checks the PM module entitlement
before invoking the handler; the handler still enforces task/project permission
and tenant/org scope. At that checkpoint Tasks desktop still consumed
`query_workspace_page`, so the facade delegate remained active. The facade was
795 lines, 75 methods
and 27 constructor inputs. Focused Dashboard, module-guard, composition and
architecture tests passed 49 cases.

The Timesheets desktop adapter now receives the existing Task lookup and
assignment handlers directly. Assignment selectors use the lookup handler;
assignment snapshots use that handler plus the assignment handler. The adapter
checks PM module entitlement before calling either handler, while their
existing task/project permission checks and Timesheet UoW behavior remain in
place. The measurement test now observes the lookup handler directly, and the
unused `list_timesheet_assignment_contexts` and
`get_timesheet_assignment_context` TaskService delegates were deleted. The
facade is now 782 lines, 73 methods including `__init__`, and 27 constructor
inputs. Focused Timesheets/composition/guard/registry tests passed 54 cases.

The Tasks desktop workspace page now receives the same composed
`TaskWorkspacePageQueryHandler` used by Dashboard and checks PM entitlement at
its adapter boundary. All production callers of the facade
`query_workspace_page` delegate were migrated; the delegate and its unused
constructor dependency were removed. The two approval/Financial Change
participant-only TaskService constructions no longer build an unused workspace
query handler. Query-count measurement still exercises the guarded Tasks
desktop route. TaskService is now 745 lines, 72 methods including `__init__`,
and 26 constructor inputs. Focused page/serialization/composition tests passed
45; approval/Financial Change/Tasks API/Dashboard/architecture tests passed 41.
QML task presenter/controller regressions passed 20; live PostgreSQL
security/RLS passed 14. Scoped Ruff F/I, Mypy, compilation and diff checks
passed after this cut.

The Tasks desktop adapter now receives the same composed
`TaskDetailPageQueryHandler` that TaskService used for assignment, dependency
and activity pages. Its boundary checks PM entitlement before calling the
handler, which continues to enforce task/project and tenant/org scope. The
three unused facade page-query delegates were removed; `get_task` remains on
the facade for still-active callers, so its detail-handler constructor input
remains. TaskService is now 709 lines, 69 methods including `__init__`, and 26
constructor inputs. Focused detail/reader/composition tests passed 46;
adapter/module-guard/architecture tests passed 28; QML and approval/Financial
Change regressions passed 40; live PostgreSQL security/RLS passed 14.
The desktop construction guard was narrowed to permit only the explicit
`require_module_enabled` policy call; a regression proves it still rejects
application-object construction. The affected API/architecture rerun passed
27 tests.

The Tasks desktop dependency-impact previews now use the composed
`TaskDependencyDiagnosticsQueryHandler` directly. The same instance remains
inside `TaskDependencyCommandHandler`, so preview and committed dependency
validation share one authority. Tasks desktop checks PM module entitlement
before invoking it; the handler retains task/project permission and scope
checks. Its two unused TaskService preview delegates and constructor input
were removed, including from approval-participant-only constructions without
changing their transaction-scoped command handler. TaskService is now 682
lines, 67 methods including `__init__`, and 25 constructor inputs. Focused
Task/API/approval/composition tests passed 71; architecture/API/composition
tests passed 37; live PostgreSQL security/RLS passed 14. Scoped Ruff F/I,
Mypy, compilation and diff checks passed. A4 remains open for other facade
callers and transaction-scoped participant contracts.
