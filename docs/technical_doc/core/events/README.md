# Core Events Module

`core/events/` provides a framework-agnostic event bus used to synchronize UI
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

## Emission and Consumption Pattern

Typical pattern:

1. Service performs mutation and commits transaction.
2. Service emits corresponding domain event.
3. UI tabs subscribed to that signal reload affected views.

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
