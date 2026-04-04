# Technical Documentation

This folder is the engineering reference for the current ProjectManagerLite codebase.
It focuses on actual package boundaries, runtime flow, and the current enterprise-platform transition state.

## Architecture Snapshot

- Layered architecture:
  - `application/`: shared orchestration seams used by desktop today and future remote delivery later
  - `core/`: domain model, business rules, and platform/module services
  - `infra/`: persistence, migrations, diagnostics, and service wiring
  - `api/`: transport-facing adapters for future HTTP/web delivery
  - `ui/`: Qt shell, admin workspaces, and module presentation logic
- Platform/module split:
  - shared concerns live under `platform/`
  - business capabilities live under `modules/`
- Current business-module state:
  - `project_management` is production-ready
  - `inventory_procurement` is implemented as a first-phase available module with runtime services and UI workspaces
  - `maintenance_management` is implemented as an early available module with persisted foundations plus first dashboard/assets/sensors/requests/work-orders/documents/reliability workspaces
  - `qhse` and `hr_management` remain planned scaffolds
- Runtime entrypoints:
  - GUI: `main_qt.py`
  - CLI: `main.py`

## Documentation Index

- [Application Layer](application/README.md)
- [API Transport Layer](api/README.md)
- [Entrypoints](entrypoints/README.md)
- [Core](core/README.md)
  - [Core Domain](core/domain/README.md)
  - [Core Events](core/events/README.md)
  - [Core Services](core/services/README.md)
  - [Core Reporting Export Layer](core/reporting/README.md)
- [Infrastructure](infra/README.md)
  - [Infrastructure Database Layer](infra/db/README.md)
- [UI Layer](ui/README.md)
  - [UI Admin](ui/admin/README.md)
  - [UI Auth](ui/auth/README.md)
  - [UI Calendar](ui/calendar/README.md)
  - [UI Control](ui/control/README.md)
  - [UI Cost](ui/cost/README.md)
  - [UI Dashboard](ui/dashboard/README.md)
  - [UI Governance](ui/governance/README.md)
  - [UI Project](ui/project/README.md)
  - [UI Report](ui/report/README.md)
  - [UI Resource](ui/resource/README.md)
  - [UI Settings](ui/settings/README.md)
  - [UI Shared](ui/shared/README.md)
  - [UI Styles](ui/styles/README.md)
  - [UI Support](ui/support/README.md)
  - [UI Task](ui/task/README.md)
- [Migration](migration/README.md)
- [Installer](installer/README.md)
- [CI/CD Release Pipeline](ci-cd/README.md)
- [Tests](tests/README.md)

## Cross-Cutting Runtime Controls

Environment variables used across the current platform:

- Data and persistence:
  - `PM_DB_URL`
  - `PM_LICENSED_MODULES`
  - `PM_ENABLED_MODULES`
- Auth bootstrap:
  - `PM_ADMIN_USERNAME`
  - `PM_ADMIN_PASSWORD` (required when the first bootstrap admin is created)
  - `PM_ALLOW_DEFAULT_ADMIN_PASSWORD` (escape hatch for explicitly allowing the insecure default bootstrap password in non-production scenarios)
- Governance:
  - `PM_GOVERNANCE_MODE`
  - `PM_GOVERNANCE_ACTIONS`
- UI/theme:
  - `PM_THEME`
- Version/update:
  - `PM_APP_VERSION`
  - `PM_UPDATE_MANIFEST_URL`
- Packaging and startup:
  - `PM_SKIP_LOGIN` (only suppresses the desktop login dialog when a session is already authenticated)

## Operational Principles

- Business logic is permission-gated at service and UI levels.
- Important mutations emit domain events for UI refresh synchronization.
- Long-running desktop operations use async workers to avoid UI blocking.
- Persistence uses optimistic locking on mutable aggregates.
- Module entitlements and organization context affect shell visibility and backend access.
- Release automation generates installer, checksum, and update manifest in one workflow.
