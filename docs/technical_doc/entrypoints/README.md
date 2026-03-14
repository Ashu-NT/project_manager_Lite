# Entrypoints Module

This module documents process bootstrap and runtime orchestration for both GUI
and CLI execution modes.

## Files

- `main_qt.py`: production GUI launcher (PySide6)
- `main.py`: CLI utility shell for service-level workflows

## GUI Startup (`main_qt.py`)

Startup sequence:

1. Configure logging via `infra.platform.logging_config.setup_logging()`.
2. Create `QApplication`.
3. Load persisted settings (`MainWindowSettingsStore`):
   - theme mode
   - governance mode
4. Set runtime env from settings (`PM_THEME`, `PM_GOVERNANCE_MODE`).
5. Apply application icon from packaged resource path.
6. Apply global UI theme stylesheet.
7. Build services (`build_services()`):
   - execute Alembic migrations
   - open SQLAlchemy session
   - build service graph via `infra.platform.services.build_service_dict`
8. Show login dialog unless both of these are true:
   - `PM_SKIP_LOGIN` is enabled
   - the shared user session is already authenticated
9. Create `ui.platform.shell.main_window.MainWindow`, show it, and enter Qt event loop.

### Important Characteristics

- DB schema migrations are enforced at app startup.
- Settings are loaded before style application, so app launches in persisted mode.
- Login is integrated into startup and the main window then resolves the active platform runtime context.
- `PM_SKIP_LOGIN` is a support/bootstrap convenience only; it does not create an anonymous authenticated desktop session by itself.

## CLI Startup (`main.py`)

CLI sequence:

1. Run migrations.
2. Build service dictionary.
3. Enter interactive command loop.

CLI exposes direct service operations for:

- project CRUD
- task CRUD/progress/dependencies/assignments
- resource and cost operations
- scheduling recalculation
- calendar and working-day operations
- cascade delete flows

### Role in the System

- Useful for smoke-testing service layer logic without the UI.
- Serves as a minimal operational fallback if GUI is unavailable.

## Service Construction Contract

Both entrypoints rely on a shared contract:

- `build_service_dict(session)` returns a fully wired dict containing:
  - repositories
  - platform and module services
  - application seams
  - user session context
  - scheduling/reporting/finance/dashboard services

This guarantees that GUI and CLI use the same business logic stack.

## Packaging Interaction

- Runtime migration lookup supports:
  - dev layout
  - PyInstaller onefile extraction (`_MEIPASS`)
  - PyInstaller onedir fallback paths
- Icon and static assets resolve through `infra.platform.resource.resource_path`.
