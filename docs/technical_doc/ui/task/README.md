# UI Task Module

`ui/task/` is the execution control center for tasks, dependencies, and
assignments.

## Files

- coordinator: `tab.py`
- actions:
  - `actions.py` (task lifecycle)
  - `assignment_actions.py` (assignment operations)
- project/task loading: `project_flow.py`
- filtering: `filtering.py`
- models:
  - `models.py` (task table)
  - `assignment_models.py`
- assignment panel and helpers:
  - `assignment_panel.py`
  - `assignment_helpers.py`
  - `assignment_summary.py`
- dependency dialogs:
  - `dependency_add_dialog.py`
  - `dependency_list_dialog.py`
  - `dependency_dialogs.py`
  - `dependency_shared.py`
- task dialogs:
  - `task_dialogs.py`
  - `task_progress_dialog.py`
- compatibility facade: `components.py`

## Coordinator (`TaskTab`)

Layout:

- project selector and reload controls
- task action toolbar
- task filters
- horizontal splitter:
  - left: task table
  - right: assignment and dependency management panel

## Service Dependencies

- `ProjectService`
- `TaskService`
- `ResourceService`
- `ProjectResourceService`

## Permission and Governance Integration

- direct task management requires `task.manage`
- dependency add/remove can be enabled through governance request model:
  - `can_execute_governed_action(..., governance_action=\"dependency.add/remove\")`
- action buttons reflect permission and governance state

## Event Model

Subscribes to:

- `tasks_changed`
- `project_changed`
- `resources_changed`

Ensures list and side panel stay synchronized after external mutations.

## Assignment and Dependency Workflows

Assignment panel supports:

- add assignment
- edit logged hours and allocation
- remove assignment
- dependency list visibility and inline management

Overallocation warnings are surfaced via helper functions tied to task service
policy outputs.
