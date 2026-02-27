# UI Cost Module

`ui/cost/` is the operational cost-control workspace. It combines cost item
editing, labor summaries, budget KPIs, and project-level filtering.

## Files

- coordinator: `tab.py`
- actions: `actions.py`
- project and filter flow: `project_flow.py`, `filters.py`
- dialogs: `cost_dialogs.py`, `labor_dialogs.py`
- layout helpers: `layout.py`
- summary logic: `labor_summary.py`
- models: `models.py`
- compatibility facade: `components.py`

## Tab Composition (`CostTab`)

Primary UI blocks:

- project selector and reload controls
- cost CRUD toolbar
- KPI cards:
  - budget
  - planned
  - committed
  - actual
  - available
- cost item grid with filters
- labor summary and detail panel

## Service Dependencies

- `ProjectService`
- `TaskService`
- `CostService`
- `ReportingService`
- `ResourceService`

## Behavior and Data Flow

- project selection drives task map, cost rows, KPI refresh, and labor summary.
- cost mutations route through `CostActionsMixin`.
- UI refreshes on `domain_events.costs_changed`, `tasks_changed`, `project_changed`, and `resources_changed`.

## Governance-Aware UX

Action enablement uses governed-action checks:

- create cost: `cost.add`
- edit cost: `cost.update`
- delete cost: `cost.delete`

If governance is enabled, users with `approval.request` can still initiate
change requests even without direct `cost.manage`.

## Models and Rendering

- `CostTableModel`: table backing for cost item list
- `LaborPlanVsActualTableModel`: labor visibility for planned vs actual view

Formatting and table styles are centralized via shared style helpers and
`UIConfig` constants for consistent desktop behavior.
