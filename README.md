# ProjectManagerLite

**ProjectManagerLite** is a desktop-first, multi-module enterprise operations platform for
project management, inventory & procurement, and maintenance (CMMS/EAM), built on a shared
tenancy/RBAC/audit platform layer.

- **Frontend:** PySide6 (Qt Quick / QML)
- **Backend:** Pure Python domain & application layer, no framework coupling
- **Persistence:** SQLAlchemy 2.0 ORM + Alembic migrations, SQLite by default (Postgres/MySQL/MSSQL/Oracle URLs supported)
- **Delivery:** Single-process desktop application today; the application/API layers are already seamed for a future hosted/web deployment

## Table of Contents

- [Module Status](#module-status)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Database & Migrations](#database--migrations)
- [Testing](#testing)
- [Build & Release](#build--release)
- [Documentation](#documentation)
- [License](#license)

## Module Status

| Module | Status | Notes |
|---|---|---|
| **Project Management** | Production | Planning/scheduling (CPM), execution, cost, baselines, register (risk/issue/change), portfolio, collaboration, timesheets, dashboards & reporting/exports |
| **Inventory & Procurement** | Available (phase 1, hardened) | Item master, storerooms, stock balances/transactions, reservations, requisitions, purchase orders, receiving |
| **Maintenance Management** | Available (early phase) | Asset/system/location registry, sensors, preventive plans, work requests/orders with technician execution actions, reliability analytics |
| **QHSE** | Skeleton only | Package scaffolding and module catalog entry only — no runtime capability yet |
| **HR Management** | Skeleton only | Package scaffolding only; a Payroll-first slice is the intended first cut |

Module visibility at runtime is driven by per-organization **module entitlements** — a module
must be both *licensed* and *enabled* before it appears in the shell. Business modules never
share schema directly with each other; cross-module collaboration goes through the shared
platform layer (references and domain events), per
[`docs/architecture_decisions/ADR-001-cross-platform-ownership-model.md`](docs/architecture_decisions/ADR-001-cross-platform-ownership-model.md).

Shared platform capabilities available to every module: authentication (password + MFA +
federated identity hooks), session management, RBAC (18 system roles / 56 permission codes),
tenancy & organization context, sites/departments/employees/parties, module licensing,
approvals, documents, activity & audit trails, platform calendar, notifications, and a shared
import/export/report runtime.

For the full, up-to-date list of what's implemented vs. still open across every module, see
[`docs/REMAINING_WORK.md`](docs/REMAINING_WORK.md).

## Architecture

```
+------------------------------------------------------------------+
|  QML FRONTEND            src/ui_qml/                              |
|  Screens, dialogs, design-system components, QML models           |
+------------------------------------------------------------------+
|  DESKTOP API BRIDGE      src/api/desktop/                         |
|  Python QObject controllers exposed to QML                        |
+------------------------------------------------------------------+
|  APPLICATION SERVICES    src/application/, src/core/*/application/|
|  Cross-surface orchestration + module/platform services           |
+------------------------------------------------------------------+
|  DOMAIN                  src/core/*/domain/                       |
|  Pure Python domain objects, value objects, domain events         |
+------------------------------------------------------------------+
|  REPOSITORY CONTRACTS    src/core/*/contracts.py                  |
+------------------------------------------------------------------+
|  INFRASTRUCTURE          src/infra/persistence/                   |
|  SQLAlchemy ORM, Alembic migrations, concrete repositories         |
+------------------------------------------------------------------+
|  COMPOSITION / DI        src/infra/composition/                   |
+------------------------------------------------------------------+
|  DATABASE  (SQLite by default; other SQLAlchemy dialects via PM_DB_URL) |
+------------------------------------------------------------------+
```

Within `core/`, `infra/`, and `ui_qml/`, the codebase is consistently split between shared
`platform/` concerns (tenancy, auth, org, calendar, documents, audit, activity, approval, ...)
and business `modules/` (`project_management`, `inventory_procurement`, `maintenance`, `qhse`,
`hr_management`/`payroll`). An optional HTTP transport layer exists under `src/api/http/` for
future server-mode delivery but is not the primary deployment path.

Multi-tenancy is implemented as **column-based isolation**: every business row carries
`tenant_id`/`organization_id` and repositories enforce scoping at both read and write time. The
architecture is designed for multi-tenant operation but the current desktop deployment runs
single-tenant by default. Architectural rules are enforced by tests in
`src/tests/architecture/`.

**Detailed references:**

- [`docs/ARCHITECTURE_README.md`](docs/ARCHITECTURE_README.md) — tenancy, org, auth, RBAC, tenant context, and repository-scoping reference with known risks/gaps
- [`docs/architecture/enterprise-platform-architecture.md`](docs/architecture/enterprise-platform-architecture.md) — full enterprise platform architecture and roadmap
- [`docs/architecture_decisions/`](docs/architecture_decisions/) — ADRs recording cross-module ownership decisions
- [`docs/REMAINING_WORK.md`](docs/REMAINING_WORK.md) — consolidated backlog across every module and platform concern

## Project Structure

```text
project_manager_Lite/
  main_qt.py                 # Desktop entrypoint (QML shell bootstrap)
  requirements.txt
  pytest.ini                  # testpaths = src/tests
  resources/                  # Qt resource bundle (icons, compiled .qrc)
  installer/                  # NSIS installer script
  .github/workflows/          # CI/CD (release automation)
  docs/                       # Architecture references, ADRs, module plans, REMAINING_WORK.md
  src/
    api/
      desktop/                # QObject bridge controllers exposed to QML
      http/                   # Future HTTP transport adapters (platform only, so far)
    application/
      runtime/                # Cross-surface orchestration (entitlements, platform runtime)
    core/
      platform/                # Shared: tenancy, auth, authorization, org, access, site,
                                #   department, employee, party, calendar, documents, audit,
                                #   activity, approval, modules (licensing), importing,
                                #   exporting, report_runtime, integration, time, ...
      modules/
        project_management/    # Production module
        inventory_procurement/ # Available module (phase 1)
        maintenance/            # Available module (early phase)
        qhse/                   # Skeleton
        hr_management/          # Skeleton
        payroll/                 # Legacy-compat alias package during the hr_management rename
      shared/                  # Cross-cutting utilities: events, audit helpers, security
    infra/
      composition/             # AppContainer / registries (dependency injection root)
      config/                  # Runtime configuration
      persistence/             # SQLAlchemy ORM, Alembic migrations, concrete repositories
      platform/                # OS-level helpers: paths, logging, versioning, updater
    ui_qml/
      shell/                   # App bootstrap, main window, navigation
      platform/                # Admin console, auth, settings, control-center QML/controllers
      modules/                 # Per-module QML workspaces (mirrors core/modules/)
      shared/                  # Design-system QML components
    tests/                     # pytest suite (architecture, platform, project_management,
                                #   inventory_procurement, maintenance, hr_management, qhse, ...)
```

## Requirements

- Python 3.11+ (actively developed and verified on 3.13)
- Windows / macOS / Linux desktop environment (Qt Quick)
- Dependencies pinned in `requirements.txt` (PySide6 6.10, SQLAlchemy 2.0, Alembic 1.17, pytest 9.0, reportlab, openpyxl, ...)

## Getting Started

### 1. Create an environment

**Conda (recommended — matches the maintained `pmenv` environment):**

```powershell
conda create -n pmenv python=3.13 -y
conda activate pmenv
pip install -r requirements.txt
```

**venv:**

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the application

```powershell
python main_qt.py
```

On first run, the app runs Alembic migrations automatically, bootstraps default roles/
permissions/an admin user, and opens the login screen. Module visibility in the shell depends
on licensing/entitlement state — `project_management` is enabled by default.

## Configuration

All configuration is via environment variables (optionally loaded from a `.env` file at repo
root — none is required by default). Key variables:

| Variable | Purpose |
|---|---|
| `PM_DB_URL` | Override the database URL (defaults to a per-user SQLite file). Supports `sqlite`, `postgresql`, `mysql`, `oracle`, `mssql` schemes. |
| `PM_ADMIN_USERNAME` / `PM_ADMIN_PASSWORD` | Bootstrap admin credentials on first run |
| `PM_ALLOW_DEFAULT_ADMIN_PASSWORD` | Escape hatch to allow an insecure default bootstrap password (non-production only) |
| `PM_LICENSED_MODULES` / `PM_ENABLED_MODULES` | Comma-separated module codes to license/enable at runtime |
| `PM_THEME` | `light` or `dark` UI theme default |
| `PM_SKIP_LOGIN` | Suppress the login dialog when a session is already authenticated |
| `PM_GOVERNANCE_MODE` / `PM_GOVERNANCE_ACTIONS` | Approval-governance policy configuration |
| `PM_AUTH_LOCKOUT_ATTEMPTS` / `PM_AUTH_LOCKOUT_MINUTES` / `PM_AUTH_SESSION_MINUTES` | Auth lockout & session policy (defaults: 5 / 15 / 480) |
| `PM_APP_VERSION` / `PM_UPDATE_MANIFEST_URL` | Version override and update-manifest source for packaged builds |
| `PM_SLOW_QUERY_MS` / `PM_SQL_TRACE` | SQL diagnostics thresholds/tracing |
| `PM_DEBUG_LOGGING` / `PM_LOG_LEVEL` | Logging verbosity |
| `PM_RUN_PERF_TESTS` + `PM_PERF_*` | Opt-in large-scale performance test suite and its scale/SLA knobs |

## Database & Migrations

- Alembic migrations run automatically at startup (`src/infra/persistence/migrations/runner.py`, invoked from `src/ui_qml/shell/app.py`)
- Default local SQLite database location:
  - Windows: `%APPDATA%\TECHASH\ProjectManagerLite\project_manager.db`
  - macOS: `~/Library/Application Support/TECHASH/ProjectManagerLite/project_manager.db`
  - Linux: `~/.local/share/TECHASH/ProjectManagerLite/project_manager.db`
- Application log file: `<user_data_dir>/logs/app.log`

## Testing

The suite lives under `src/tests/` (configured via `pytest.ini`), organized by
architecture guardrails, platform, and each business module.

```powershell
conda run -n pmenv python -m pytest -q -p no:cacheprovider
```

Run a targeted suite:

```powershell
conda run -n pmenv python -m pytest -q src/tests/architecture -p no:cacheprovider
conda run -n pmenv python -m pytest -q src/tests/project_management -p no:cacheprovider
conda run -n pmenv python -m pytest -q src/tests/platform -p no:cacheprovider
```

Opt-in large-scale performance workflow test:

```powershell
$env:PM_RUN_PERF_TESTS = "1"
conda run -n pmenv python -m pytest -q src/tests/test_large_scale_performance.py -p no:cacheprovider
```

## Build & Release

- **Packaging:** PyInstaller
- **Installer:** NSIS script at `installer/ProjectManagerLite.nsi`
- **CI/CD:** `.github/workflows/release.yml` — triggered by pushing a tag (e.g. `v2.1.1`) or manually via `workflow_dispatch`; produces the installer `.exe`, a `.sha256` checksum, and a `release-manifest.json`
- **In-app updates:** the admin **Support** workspace supports channel selection (`stable`/`beta`), manifest source configuration, manual update checks, an `Install Now` flow (Windows), and diagnostics bundle export

## Documentation

- [`docs/REMAINING_WORK.md`](docs/REMAINING_WORK.md) — single consolidated backlog of everything not yet done, across every module and the platform layer
- [`docs/ARCHITECTURE_README.md`](docs/ARCHITECTURE_README.md) — tenancy/org/auth/RBAC deep reference
- [`docs/architecture/enterprise-platform-architecture.md`](docs/architecture/enterprise-platform-architecture.md) — full architecture & roadmap
- [`docs/architecture_decisions/`](docs/architecture_decisions/) — ADRs
- [`docs/inventory_procurement/`](docs/inventory_procurement/), [`docs/maintenance_management/`](docs/maintenance_management/), [`docs/pm_modernization/`](docs/pm_modernization/) — per-module design/execution plans
- [`docs/cache_service_strategy/`](docs/cache_service_strategy/) — shared cache service design (not yet implemented)
- [`docs/platform_alignment_followup/`](docs/platform_alignment_followup/), [`docs/platform_modernization/`](docs/platform_modernization/), [`docs/repo_structure_plan/`](docs/repo_structure_plan/), [`docs/tenant_repository_hardening/`](docs/tenant_repository_hardening/) — active cross-cutting workstreams
- [`docs/INLINE_MESSAGE_STANDARDIZATION_README.md`](docs/INLINE_MESSAGE_STANDARDIZATION_README.md), [`docs/ux_design.md`](docs/ux_design.md) — UI/UX conventions

## License

MIT. See [`LICENSE`](LICENSE).
