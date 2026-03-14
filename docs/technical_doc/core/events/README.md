# Core Events Module

`core/platform/notifications/` provides a framework-agnostic event bus used to synchronize UI
state with domain mutations.

## Files

- `signal.py`: thread-safe observer primitive
- `domain_events.py`: typed event registry and global event hub instance

## Signal Primitive (`Signal[T]`)

Features:

- subscriber registration (`connect`)
- unregistration (`disconnect`)
- emission with payload (`emit`)
- thread-safe subscriber list via `RLock`

Resilience behavior:

- auto-prunes stale callbacks that raise QObject-deleted runtime errors
- handles `ReferenceError` cleanup

This is critical for long-lived desktop sessions where widgets are created and
destroyed frequently.

## Domain Event Channels

Global singleton `domain_events` exposes these channels:

- `project_changed(project_id)`
- `tasks_changed(project_id)`
- `costs_changed(project_id)`
- `resources_changed(resource_id)`
- `baseline_changed(project_id)`
- `approvals_changed(request_id)`
- `register_changed(project_id)`
- `auth_changed(user_id)`
- `employees_changed(employee_id)`
- `organizations_changed(organization_id)`
- `access_changed(project_id)`
- `collaboration_changed(task_id)`
- `portfolio_changed(entity_id)`
- `modules_changed(module_code)`

## Emission and Consumption Pattern

Typical pattern:

1. service performs mutation and commits transaction
2. service emits the corresponding domain event
3. subscribed desktop views reload the affected state

This yields eventual consistency in the UI without hard module coupling.

## Why Not Qt Signals Directly

Reasons for framework-agnostic event layer:

- core layer stays decoupled from Qt dependencies
- events can be used in CLI/tests without Qt app context
- avoids circular imports between services and widgets

## Testing Implications

Domain event behavior is covered by dedicated tests to guarantee:

- correct signal emission for governed and direct mutation flows
- robust handling of stale widget callbacks
