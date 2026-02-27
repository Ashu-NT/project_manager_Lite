# Infrastructure Module

`infra/` provides all non-domain runtime plumbing: persistence, migrations,
service wiring, diagnostics, update flow, and platform path/resource handling.

## Responsibilities

- Build and configure SQLAlchemy engine/session.
- Run Alembic migrations in dev and packaged runtimes.
- Implement repository adapters for core interfaces.
- Compose the full service graph and dependency injection wiring.
- Manage logging, diagnostics, version/update runtime behavior.

## Key Files

- `infra/db/base.py`: DB URL resolution, engine, session factory
- `infra/migrate.py`: robust Alembic path discovery + upgrade-to-head
- `infra/services.py`: service graph composition and governance apply handlers
- `infra/logging_config.py`: rotating app log setup
- `infra/path.py`: OS-aware user data directory and DB path helpers
- `infra/resource.py`: resource path resolution for dev/PyInstaller
- `infra/update.py`: update manifest parsing + version comparison
- `infra/updater.py`: installer download/checksum/handoff/relaunch logic
- `infra/diagnostics.py`: diagnostics bundle generation
- `infra/version.py`: runtime version resolution

## Service Graph Construction

`build_service_graph(session)` composes:

- repositories (project/task/resource/cost/calendar/auth/audit/approval/etc.)
- service instances (auth, project, task, cost, scheduling, reporting, finance, dashboard)
- user session context
- governance apply handlers for approval workflows

Governance request handlers map request types to executable service actions:

- baseline create
- dependency add/remove
- cost add/update/delete

## Update and Productization Runtime

Update subsystem capabilities:

- manifest source resolution with default `releases/latest/download/release-manifest.json`
- channel-aware payload lookup (`stable`, `beta`)
- semantic-ish numeric version comparison
- installer download + SHA256 verification
- Windows handoff script:
  - waits for app process exit
  - runs installer
  - relaunches app executable

## Diagnostics Runtime

Diagnostics bundles include:

- metadata (`app_version`, Python version, platform, settings snapshot)
- rotating log files (`app.log*`)
- optional DB snapshot copy

Output is a zip archive suitable for admin support triage.

## Persistence Notes

- SQLite default DB lives in user app-data path, not install directory.
- optimistic locking support is implemented in repository update helpers.
- migrations are mandatory at startup in both CLI and GUI flows.

## Environment Controls

- `PM_DB_URL`: override database connection URL.
- `PM_APP_VERSION`: runtime version override.
- `PM_UPDATE_MANIFEST_URL`: default manifest source override.
