# UI Module

`ui/` is the presentation layer built on PySide6. It coordinates user intent,
delegates business operations to core services, and renders state-rich views.

## Architectural Pattern

Primary pattern is coordinator + mixins/components:

- Tab classes wire layout and high-level interactions.
- Mixins handle focused concerns (actions, filtering, rendering, data ops).
- Dialog modules isolate dense interaction forms.
- Shared utilities unify guards, async job handling, styling, and helpers.

This avoids mega-tabs and improves local maintainability.

## Runtime Structure

- `ui/platform/shell/`: main window, grouped navigation tree, workspace registration
- `ui/platform/admin/`: shared admin workspaces
  - access
  - users
  - employees
  - organizations
  - modules
  - support
- `ui/platform/control/`: cross-platform oversight workspaces such as audit
- `ui/platform/settings/`: persisted desktop preference storage
- `ui/platform/shared/`: guard helpers, async jobs, shared widgets, styles
- `ui/modules/project_management/`: current production business workspaces
  - project
  - task
  - resource
  - cost
  - calendar
  - report
  - dashboard
  - governance
  - register
  - collaboration
  - portfolio
  - timesheet
- `ui/modules/inventory_procurement/`: available module workspaces for inventory, procurement, data exchange, and reporting
- `ui/modules/maintenance_management/`: early maintenance workspaces for dashboard, assets, sensors, requests, work orders, documents, planner, and reliability

Placeholder package roots still exist for `qhse` and `hr_management`.

Legacy compatibility package roots such as `ui/modules/payroll/` remain available during the rename transition.

## Permission and Governance UX

Two-layer access control:

1. Service layer hard enforcement.
2. UI-layer affordance gating:
   - buttons disabled when permission missing
   - tooltips explain required permission
   - governed actions can remain executable if `approval.request` is allowed and governance is enabled

Helpers in `ui.platform.shared.guards` centralize this behavior.

## Async UX Under Load

Long operations run through `ui.platform.shared.async_job`:

- job cancellation token
- progress reporting
- retry on failure
- optional silent mode (no progress dialog)
- busy-state control for action buttons

Dashboard refresh, baseline generation, report exports, scheduling, diagnostics,
and update installation all use async flows to prevent UI blocking.

## Domain Event Wiring

Tabs subscribe to `core.platform.notifications.domain_events` signals:

- project/task/resource/cost/baseline/approval changes trigger targeted reloads
- avoids stale on-screen state after mutations in other tabs

## Theming and Visual Consistency

`ui/platform/shared/styles` provides:

- tokenized theme variables
- centralized stylesheet generation
- formatting helpers
- table styling and sizing helpers

Main window loads persisted theme and reapplies style globally at startup.

## Shell Model

The current desktop shell is platform-aware:

- slim header for global controls
- grouped navigation for platform and business modules
- shell rebuild on organization and module-entitlement changes
- hidden top tabs with navigation driving the active workspace stack

## Documentation Map

- [Admin](admin/README.md)
- [Auth](auth/README.md)
- [Calendar](calendar/README.md)
- [Cost](cost/README.md)
- [Control](control/README.md)
- [Dashboard](dashboard/README.md)
- [Governance](governance/README.md)
- [Project](project/README.md)
- [Report](report/README.md)
- [Resource](resource/README.md)
- [Settings](settings/README.md)
- [Shared](shared/README.md)
- [Styles](styles/README.md)
- [Support](support/README.md)
- [Task](task/README.md)
