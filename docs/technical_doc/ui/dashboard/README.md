# UI Dashboard Module

`ui/dashboard/` is the executive and operational overview module for project
health, schedule status, resource loading, baseline tracking, and leveling.

## Files

- coordinator: `tab.py`
- data operations: `data_ops.py`, `async_actions.py`
- leveling operations: `leveling_ops.py`
- rendering split:
  - `rendering.py` facade
  - `rendering_summary.py`
  - `rendering_charts.py`
  - `rendering_alerts.py`
  - `rendering_evm.py`
- widgets and style:
  - `widgets.py`
  - `styles.py`
  - `evm_rows.py`
- access policy:
  - `access.py`

## Core UI Regions

- top project/baseline control bar
- summary and KPI panel
- alert and upcoming-task panel
- burndown and resource-load chart panel
- EVM panel
- resource conflict and leveling controls

## Service Dependencies

- `DashboardService`
- `ProjectService`
- `BaselineService`

Dashboard service aggregates reporting, task, schedule, and resource insights.

## Async and Responsiveness

Long operations are asynchronous:

- dashboard refresh (`run_refresh_dashboard_async`)
- baseline creation (`run_generate_baseline_async`)
- conflict leveling actions

The module supports silent refresh mode to avoid startup progress-dialog noise.

## Access and Permission Behavior

`access.py` configures:

- visibility and enablement for baseline and leveling controls
- permission hints on gated actions
- synchronization of related buttons and workflows

## Event Integration

Tab subscribes to:

- `project_changed`
- `tasks_changed`
- `costs_changed`
- `resources_changed`
- `baseline_changed`

This keeps dashboard visuals consistent with mutations made in other tabs.

## Engineering Notes

- Rendering logic is split from data loading to keep the coordinator lean.
- Chart widgets are reusable custom components.
- Conflict workflows support preview, auto-level, and manual shift paths.
