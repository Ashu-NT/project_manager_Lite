# UI Project Module

`ui/project/` is the project lifecycle workspace with inline project-resource
planning and assignment controls.

## Files

- coordinator: `tab.py`
- actions: `actions.py`
- filters: `filtering.py`
- table model: `models.py`
- dialogs:
  - `project_edit_dialog.py`
  - `project_resource_edit_dialog.py`
  - `dialogs.py` facade
- inline project-resource panel: `resource_panel.py`

## Coordinator Behavior (`ProjectTab`)

Main functions:

- list and filter projects
- create, edit, update status, delete project
- select project to manage project-resource rows inline
- react to domain events and keep table state synchronized

Layout:

- toolbar + filter bar
- horizontal splitter:
  - left: project table
  - right: project-resource management panel

## Service Dependencies

- `ProjectService`
- `TaskService`
- `ReportingService`
- `ProjectResourceService`
- `ResourceService`

## Permission Model

- project actions require `project.manage`
- project-resource actions map to same management capability
- button states and tooltips are permission-aware

## Event Model

- reload on `domain_events.project_changed`
- refresh resource panel on `domain_events.resources_changed`

## Resource Planning Integration

The inline resource panel manages:

- project-specific rate and currency overrides
- planned hours
- active/inactive assignment state

This data feeds baseline and finance/reporting policy computations downstream.
