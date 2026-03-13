# Technical Documentation

This folder is the engineering reference for the ProjectManagerLite codebase.
It is organized by runtime module so you can understand boundaries, data flow,
extension points, and operational behavior without reverse-engineering the code.

## Architecture Snapshot

- Layered architecture:
  - `core/`: domain model + business rules + service orchestration
  - `infra/`: persistence, migrations, runtime infrastructure, DI/wiring
  - `ui/`: Qt presentation, user workflows, async job orchestration
- Runtime entrypoints:
  - GUI: `main_qt.py`
  - CLI: `main.py`
- Packaging:
  - PyInstaller bundle + NSIS installer + GitHub Actions release workflow

## Module Documentation Index

- [Entrypoints](entrypoints/README.md)
- [Core](core/README.md)
  - [Core Domain](core/domain/README.md)
  - [Core Events](core/platform/notifications/README.md)
  - [Core Services](core/services/README.md)
  - [Core Reporting Export Layer](core/modules/project_management/reporting/README.md)
- [Infrastructure](infra/README.md)
  - [Infrastructure Database Layer](infra/db/README.md)
- [UI Layer](ui/README.md)
  - [UI Admin](ui/platform/admin/README.md)
  - [UI Auth](ui/platform/shared/auth/README.md)
  - [UI Calendar](ui/modules/project_management/calendar/README.md)
  - [UI Cost](ui/modules/project_management/cost/README.md)
  - [UI Dashboard](ui/modules/project_management/dashboard/README.md)
  - [UI Governance](ui/modules/project_management/governance/README.md)
  - [UI Project](ui/modules/project_management/project/README.md)
  - [UI Report](ui/modules/project_management/report/README.md)
  - [UI Resource](ui/modules/project_management/resource/README.md)
  - [UI Settings](ui/platform/settings/README.md)
  - [UI Shared](ui/platform/shared/README.md)
  - [UI Styles](ui/platform/shared/styles/README.md)
  - [UI Support](ui/platform/admin/support/README.md)
  - [UI Task](ui/modules/project_management/task/README.md)
- [Migration](migration/README.md)
- [Installer](installer/README.md)
- [CI/CD Release Pipeline](ci-cd/README.md)
- [Tests](tests/README.md)

## Cross-Cutting Runtime Controls

Environment variables used across modules:

- Data and persistence:
  - `PM_DB_URL`
- Auth bootstrap:
  - `PM_ADMIN_USERNAME`
  - `PM_ADMIN_PASSWORD`
- Governance:
  - `PM_GOVERNANCE_MODE`
  - `PM_GOVERNANCE_ACTIONS`
- UI/theme:
  - `PM_THEME`
- Version/update:
  - `PM_APP_VERSION`
  - `PM_UPDATE_MANIFEST_URL`
- Packaging and startup:
  - `PM_SKIP_LOGIN`

## Operational Principles

- Business logic is permission-gated at service and UI levels.
- Important mutations emit domain events for UI refresh synchronization.
- Long-running UI operations use async workers (`QThreadPool`) to avoid UI blocking.
- Persistence uses optimistic locking (`version` columns) for stale-write protection.
- Release automation generates installer + checksum + update manifest in one workflow.
