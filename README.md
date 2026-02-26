# ProjectManagerLite

ProjectManagerLite is a desktop project management application for planning, scheduling, execution control, and reporting.
It is built with Python + PySide6 and follows a layered architecture designed for maintainability and scale.

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
- Task assignment with allocation `%` and logged hours
- Cost tracking (planned, committed, actual) with labor integration
- Baseline creation and schedule/cost variance analysis

### Reporting and Exports
- Dashboard: KPIs, alerts, upcoming tasks, resource load, burndown, EVM snapshot
- Report views: KPI, Gantt, Critical Path, Resource Load, Performance Variance, EVM
- Exports:
  - Gantt PNG
  - EVM PNG
  - Excel workbook
  - PDF report

## Architecture

The codebase is split into three main layers:

- `core/`: domain models, business rules, scheduling/reporting engines, service orchestration
- `infra/`: SQLAlchemy repositories, mappers, migration/bootstrap wiring
- `ui/`: Qt tabs/dialogs and presentation workflows

Architectural guardrails are enforced by tests in `tests/test_architecture_guardrails.py`.
For design details and refactor history, see `docs/ARCHITECTURE_BLUEPRINT.md`.

## Project Structure

```text
project_mangement_app/
  core/
  infra/
  ui/
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

### CLI mode (optional)

```powershell
python main.py
```

## Database, Migrations, and Logs

- Migrations run automatically at startup (`alembic upgrade head` via `infra/migrate.py`)
- Local SQLite database location:
  - Windows: `%APPDATA%\TECHASH\ProjectManagerLite\project_manager.db`
  - macOS: `~/Library/Application Support/TECHASH/ProjectManagerLite/project_manager.db`
  - Linux: `~/.local/share/TECHASH/ProjectManagerLite/project_manager.db`
- Application log file:
  - `<user_data_dir>/logs/app.log`

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
  - manifest source setting (URL or local file path)
  - manual update checks
  - diagnostics bundle export (metadata + logs + DB snapshot)
  - quick links to logs/data folders
- Optional app version override for packaged builds:

```powershell
$env:PM_APP_VERSION = "2.1.0"
python main_qt.py
```

- Update manifest JSON shape (example):

```json
{
  "channels": {
    "stable": {
      "version": "2.1.0",
      "url": "https://example.com/ProjectManagerLite-2.1.0.exe",
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

## Notes

- No `.env` file is required by default
- Legacy compatibility modules are preserved in several packages for smoother refactors

## License

MIT. See `LICENSE`.
