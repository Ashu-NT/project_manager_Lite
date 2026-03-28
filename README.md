# ProjectManagerLite

ProjectManagerLite is a desktop-first enterprise operations platform built with Python + PySide6.
The current default-enabled production business capability is the `Project Management` module, supported by shared platform features such as admin, access, audit, organizations, employees, module licensing, approvals, documents, and notifications.
The codebase also now includes an implemented first-phase `Inventory & Procurement` module that can be licensed and enabled at runtime.

The staged migration plan toward a broader modular enterprise platform is tracked in `docs/ENTERPRISE_PLATFORM_EXECUTION_PLAN.md`.

## Current Status

Delivered in the current codebase:

- `Project Management` as the active production module for planning, execution, control, dashboarding, reporting, collaboration, and timesheets
- `Inventory & Procurement` phase 1 as an available module for item master, storerooms, stock balances and transactions, reservations, requisitions, purchase orders, receiving, and shared document/approval integration
- grouped enterprise shell and platform admin workspaces
- organization and employee management
- persistent module licensing with organization-scoped entitlements
- enterprise RBAC foundation, collaboration, portfolio, approvals, audit, and support tooling
- PM in-app notifications, task-level workflow notification badges, service-backed task collaboration runtime, saved portfolio scenario comparison, PMO scoring templates, portfolio executive heatmaps, recent PM action summaries, task presence indicators, portfolio-level cross-project dependency visualization, and desktop optimistic-lock guards in normal edit flows
- application-layer and transport-layer seams for future web/server adoption

Pending major work:

- deeper hardening for `Inventory & Procurement`, especially maintenance-facing integration workflows, broader serial/lot lifecycle traceability, and richer warehouse execution policies beyond the delivered document-import and receiving hardening
- `Maintenance Management`, `QHSE`, and `HR Management` business modules
- deeper enterprise identity controls such as hosted SSO rollout, richer contextual policy evaluation, broader scope adoption, and stronger security operations on top of the delivered federation/MFA/per-session groundwork
- a concrete hosted web/router layer when the product moves beyond desktop-first deployment

The PM-specific enterprise roadmap is tracked in `docs/ENTERPRISE_PM_ROADMAP.md`; it currently has no remaining carryover backlog. The remaining PM work is now technical alignment follow-up, tracked separately in `docs/project_management_followup/README.md`.

## Next Priority

The next priority is to harden the implemented `Inventory & Procurement` phase into a fuller enterprise-ready rollout, then wire `Maintenance Management` to consume it by reference.

The initial maintenance blueprint is tracked in `docs/maintenance_management/README.md`.
The inventory blueprint is now tracked in `docs/inventory_procurement/README.md`.

The broader platform direction is now governed by a simple architecture rule: share enterprise capabilities, not business ownership. Shared capabilities should live once under the platform spine, business workflows should stay in the module that owns them, and cross-module collaboration should happen through references and events rather than direct schema coupling. The short frozen ownership decisions are now locked in `docs/architecture_decisions/ADR-001-cross-platform-ownership-model.md` and `docs/architecture_decisions/ADR-002-location-and-system-ownership.md`. See also `docs/ENTERPRISE_PLATFORM_EXECUTION_PLAN.md` and `docs/maintenance_management/README.md`.

The concrete follow-up tracker for making the current codebase match that architecture is now kept in `docs/platform_alignment_followup/README.md`. The shared-master alignment block is now complete, and the next module-facing work continues from the implemented inventory phase.

Why this comes first:

- the shared platform time boundary now exists and already carries module-neutral `work_entry` ownership plus employee/site/department snapshot context
- that removes the biggest platform blocker before opening the next business module
- enterprise customers may want stock and purchasing without maintenance
- professional CMMS patterns usually keep inventory and purchasing as a dedicated business capability that maintenance work orders integrate with
- maintenance is stronger when it consumes a clean stock and purchasing module instead of owning duplicate inventory logic

The current enterprise auth/access hardening block delivered:

1. federation and MFA hooks in the shared auth service: linked federated identities, MFA secret provisioning and verification, per-user session-timeout policy, session-revision validation, and richer login/session metadata
2. true non-project scoped access persistence with the first live non-project scope type: `storeroom`, including principal hydration from mixed project + scoped grants
3. cross-cutting enterprise guardrails: first separation-of-duties enforcement for conflicting security/governance permission sets and a split `Access` vs `Security` admin workspace
4. a platform-owned authorization engine seam in `core/platform/authorization` so future web auth middleware and ABAC-style adapters have one central integration point
5. per-session persistence through dedicated `auth_sessions`, including single-session revocation and session-backed principal validation for desktop + future web use
6. broader non-project scope rollout with first live `site` scope policy support alongside `storeroom`

The next implementation slice should now focus on:

1. hosted web auth transport and middleware on top of the delivered per-session model
2. hosted SSO/IdP adapters and deeper `security.manage` workflows such as stronger device visibility and security event handling
3. richer authorization-engine context inputs plus broader scoped-access adoption inside inventory flows beyond current site/storeroom boundaries, then asset/maintenance-area scope types
4. fuller security admin UX for password reset, MFA state, and federated-account lifecycle

The concrete tracker for that work is now `docs/platform_alignment_followup/auth_access_scaling/README.md`.

After that, the next priority should be the `Maintenance Management` skeleton, then deeper shared master data for formal site/department directories, and then the `QHSE` module skeleton.

This does not mean Project Management will never grow again. It means the current PM enterprise roadmap has been delivered, and the next enterprise module investment should establish inventory and procurement as a reusable business capability before Maintenance depends on it.

## Core Capabilities

### Planning and Scheduling
- Project setup with date and budget context
- Task planning with duration, priority, and status
- Dependency management (`FS`, `SS`, `FF`, `SF`) with lag support
- CPM-based schedule recalculation with critical path and float
- Working calendar support (working days, hours/day, holidays)

### Execution and Control
- Resource catalog with rates, activity status, and currency
- Project-specific resource planning (`ProjectResource`) with planned hours/rates
- Task assignment with allocation `%`, time entries, and monthly timesheet approval periods
- Cost tracking (planned, committed, actual) with labor integration
- Baseline creation and schedule/cost variance analysis
- Risk / issue / change register with ownership, severity, status, and due dates

### Reporting and Exports
- Dashboard: KPIs, alerts, upcoming tasks, resource load, burndown, EVM snapshot, portfolio overview, milestone health, critical-path watchlist, register summary
- Report views: KPI, Gantt, Critical Path, Resource Load, Performance Variance, EVM
- Exports:
  - Gantt PNG
  - EVM PNG
  - Excel workbook
  - PDF report

## Architecture

The codebase is split into five complementary layers:

- `application/`: cross-surface orchestration seams that desktop and future web/API adapters can share
- `core/`: domain models, business rules, scheduling/reporting engines, service orchestration
- `infra/`: SQLAlchemy repositories, mappers, migration/bootstrap wiring
- `ui/`: Qt tabs/dialogs and presentation workflows
- `api/`: transport-facing adapters for future HTTP/web delivery

Within `core/`, `infra/`, and `ui/`, the repo is also split between shared `platform/` concerns and business `modules/`.

Architectural guardrails are enforced by tests in `tests/test_architecture_guardrails.py`.
For design details and refactor history, see `docs/ARCHITECTURE_BLUEPRINT.md`.

## Project Structure

```text
project_mangement_app/
  application/
  api/
  core/
    platform/
    modules/
  infra/
    platform/
    modules/
  ui/
    platform/
    modules/
  tests/
  docs/
  main_qt.py
  main.py
  requirements.txt
```

## Requirements

- Python 3.11+
- Windows/macOS/Linux (desktop)
- Dependencies from `requirements.txt`

## Quick Start

### Option A: Conda (recommended)

```powershell
conda create -n pmenv python=3.11 -y
conda activate pmenv
pip install -r requirements.txt
python main_qt.py
```

### Option B: venv

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main_qt.py
```

## Running the Application

### Desktop UI (primary)

```powershell
python main_qt.py
```

Business module visibility is driven by module entitlements at runtime. `Project Management` is enabled by default; planned modules stay out of the shell until they are licensed and enabled.

### CLI mode (optional)

```powershell
python main.py
```

## Database, Migrations, and Logs

- Migrations run automatically at startup (`alembic upgrade head` via `infra/platform/migrate.py`)
- Local SQLite database location:
  - Windows: `%APPDATA%\TECHASH\ProjectManagerLite\project_manager.db`
  - macOS: `~/Library/Application Support/TECHASH/ProjectManagerLite/project_manager.db`
  - Linux: `~/.local/share/TECHASH/ProjectManagerLite/project_manager.db`
- Application log file:
  - `<user_data_dir>/logs/app.log`

## Data Import

- Projects tab now opens an import wizard for `projects`, `resources`, `tasks`, and `costs`
- Supports CSV preview before commit, column mapping, dry-run diagnostics, and partial-valid imports

## Theme

- Runtime theme switcher available in the main window (`Light` / `Dark`)
- Optional environment default:

```powershell
$env:PM_THEME = "light"
python main_qt.py
```

## Support And Updates

- New admin `Support` tab includes:
  - update channel selection (`stable` / `beta`)
  - manifest source setting (URL or local file path), prefilled to GitHub `latest` by default
  - manual update checks
  - `Install Now` flow (Windows): downloads installer, verifies SHA256, closes app, runs installer, relaunches app
  - diagnostics bundle export (metadata + logs + DB snapshot)
  - quick links to logs/data folders
- Optional app version override for packaged builds:

```powershell
$env:PM_APP_VERSION = "2.1.1"
$env:PM_UPDATE_MANIFEST_URL = "https://github.com/Ashu-NT/project_manager_Lite/releases/latest/download/release-manifest.json"
python main_qt.py
```

- Update manifest JSON shape (example):

```json
{
  "channels": {
    "stable": {
      "version": "2.1.1",
      "url": "https://example.com/ProjectManagerLite-2.1.1.exe",
      "notes": "Production release",
      "sha256": "..."
    },
    "beta": {
      "version": "2.2.0-beta1",
      "url": "https://example.com/ProjectManagerLite-2.2.0-beta1.exe",
      "notes": "Preview release",
      "sha256": "..."
    }
  }
}
```

## Testing

Run full test suite:

```powershell
conda run -n pmenv python -m pytest -q -p no:cacheprovider
```

Run selected suites:

```powershell
conda run -n pmenv python -m pytest -q tests/test_technical_math_reporting.py -p no:cacheprovider
conda run -n pmenv python -m pytest -q tests/test_exporters_configuration.py -p no:cacheprovider
conda run -n pmenv python -m pytest -q tests/test_architecture_guardrails.py -p no:cacheprovider
```

Run the opt-in large-scale performance workflow test:

```powershell
$env:PM_RUN_PERF_TESTS = "1"
conda run -n pmenv python -m pytest -q tests/test_large_scale_performance.py -p no:cacheprovider
```

Optional scale and SLA knobs (defaults shown):

```powershell
$env:PM_PERF_TASKS = "1500"
$env:PM_PERF_RESOURCES = "200"
$env:PM_PERF_COST_ITEMS = "1500"
$env:PM_PERF_ASSIGNMENT_STRIDE = "1"
$env:PM_PERF_CROSS_DEP_GAP = "9"
$env:PM_PERF_START_DATE = "2025-01-06"
$env:PM_PERF_SLA_SEED_SECONDS = "180"
$env:PM_PERF_SLA_SCHEDULE_SECONDS = "45"
$env:PM_PERF_SLA_BASELINE_SECONDS = "60"
$env:PM_PERF_SLA_REPORT_SECONDS = "90"
$env:PM_PERF_SLA_DASHBOARD_SECONDS = "90"
$env:PM_PERF_SLA_TOTAL_SECONDS = "360"
```

## Build and Distribution

- PyInstaller is used for packaging
- NSIS installer script and artifact are under `installer/`

### GitHub Actions Release Automation

This repo now includes a release workflow:

- workflow file: `.github/workflows/release.yml`
- trigger: push a tag like `v2.1.1` (or run manually with `workflow_dispatch`)
- output assets:
  - `Setup_ProjectManagerLite_<version>.exe`
  - `Setup_ProjectManagerLite_<version>.exe.sha256`
  - `release-manifest.json`

After release, you can use this manifest URL in the Support tab:

```text
https://github.com/<owner>/<repo>/releases/latest/download/release-manifest.json
```

Notes:

- The workflow injects NSIS installer version from the Git tag (`/DAPP_VERSION=...`).
- The workflow also stamps `infra/app_version.txt`, so Support tab compares against the installed release version.
- `installer/ProjectManagerLite.nsi` supports CI override and still falls back to `2.1.1` locally.

## Notes

- No `.env` file is required by default
- Legacy compatibility modules are preserved in several packages for smoother refactors

## License

MIT. See `LICENSE`.
