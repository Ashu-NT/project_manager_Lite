# UI Control Module

`ui/platform/control/` contains cross-platform oversight workspaces that are not
pure administration screens but still belong to the shared platform layer.

## Current Workspaces

- `audit/`
  - cross-module audit exploration and privileged-action visibility

## Audit Explorer (`AuditLogTab`)

Capabilities:

- reads recent audit entries (`limit=1000`)
- filters by project, entity type, action text, actor text, and date mode
- date modes: all, single date, date range
- resolves IDs into labels where reference maps exist

Reference maps include:

- projects
- tasks
- resources
- cost items
- baselines

Event-driven behavior:

- subscribes to domain events and reloads automatically
- reacts to module-entitlement changes so the audit surface stays aligned with
  platform runtime context

## Notes

- audit is intentionally documented outside `ui/platform/admin/` because it is
  an oversight/control surface rather than a workflow for managing users or
  runtime configuration
