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
| Command / assignment | `assign_resource`, `assign_project_resource`, `unassign_resource`, `set_assignment_hours`, `set_assignment_allocation`, `update_assignment_planned_hours`, `accept_assignment`, `decline_assignment` | Tasks desktop API, Timesheets desktop API, import/test setup; eventual assignment capability, preserving skill/capacity checks and one UoW. |
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
| Lookup queries | `list_tasks_for_project`, `list_tasks_for_resource`, `list_assignments_for_resource`, `list_assignments_for_tasks`, `list_timesheet_assignment_contexts`, `get_timesheet_assignment_context`, `query_tasks` | Dashboard uses task and batched assignment lookups; CSV importer uses project lookup; Timesheets builders use assignment contexts; Tasks/Scheduling desktop APIs use the rest. The lookup handler enforces task/project permissions but not the facade's module guard. |
| Page queries | `query_workspace_page`, `query_task_assignments_page`, `query_task_dependencies_page`, `query_task_activity_page` | Tasks and Dashboard desktop APIs; readers own paging/sorting and DTO projection, not QML. |
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
- Dashboard and importer are the best next internal cuts: Dashboard needs a
  read-only task/assignment lookup capability; importer needs lifecycle,
  hierarchy, progress and lookup. Both require explicit module-guard parity.

## Verification and remaining gate

This slice removed `work_calendar_engine`, `project_repo`,
`tenant_context_service` and `task_workspace_reader` from TaskService's
constructor. Their authoritative users remain the injected handlers/readers.
The facade's constructor shrank from 31 to 27 inputs. Focused assignment and
approval participant tests passed 48 cases after the cut. Facade forwarding
count is not yet materially reduced; the next slice must migrate a real
consumer before deleting its forwarding methods. PostgreSQL/RLS and broader
desktop/Task integration verification remain required for A4 closure.
