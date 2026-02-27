# UI Resource Module

`ui/resource/` manages the enterprise resource catalog and operational resource
state.

## Files

- coordinator: `tab.py`
- actions: `actions.py`
- flow and selection helpers: `flow.py`
- filters: `filtering.py`
- table model: `models.py`
- edit dialog: `dialogs.py`

## Coordinator (`ResourceTab`)

Main functions:

- list resources
- create resource
- edit resource
- delete resource
- toggle active status
- filter resources by search and attributes

Layout:

- top action toolbar
- filter area
- resource grid with tuned column resize behavior

## Service Dependency

- `ResourceService`

## Permission Model

- mutable actions require `resource.manage`
- action controls use permission hints and conditional enablement

## Event Model

- subscribes to `domain_events.resources_changed`
- reloads grid when resource mutations occur in this tab or others

## Data Considerations

Resource records include labor economics and currency details. This data feeds:

- assignment operations
- project-resource planning overrides
- finance and reporting computations
