# PM Reporting Layer Refactor

## Current Ownership

- `application/reporting` owns authorized report and KPI query orchestration. Its
  builders use repository/read contracts and existing scheduling, resource, and
  Finance calculation authorities. It does not import infrastructure.
- `infrastructure/reporting` owns concrete PDF, Excel, PNG, formatting, and
  export-runtime adapters. The desktop financial and scheduling APIs are the
  user-facing entry points; `export_runtime.py` wires the concrete renderers.
- `api/desktop/projects/import_preview.py` owns the current desktop-only file
  preview adapter. The QML presenter normalizes the file URL before calling
  it. This removes the former `application/imports` re-export of concrete
  parser implementations.
- Project and Project Resource write commands receive a generic UoW factory
  from composition rather than constructing SQLAlchemy UoWs in application.
  Composition preserves their existing shared-session transaction behavior.

## Removed

- The unused metadata-driven `ReportDefinition`/`SavedReportView` model and
  its exports. It had no production consumer or persistence path; it was not
  the active Platform callback report registry.
- The unused `reporting/exporters/api.py` re-export shim and empty reporting
  utility package.
- The former `infrastructure/reporting/api.py` name and the
  `application/imports` infrastructure re-export. There are no compatibility
  wrappers for these pre-release paths.

## Guardrails

- `test_pm_dependency_direction.py` rejects infrastructure imports from PM
  application, domain, and contracts. Concrete adapters are wired outside
  these business layers.
- The resource-load summary now uses the repository's scoped batch lookup
  instead of one resource query per assignment resource.
- No generic top-level analytics package was added. Financial calculation
  authority remains in the existing Finance capability; dashboard/resource
  analytics remain with their owning capabilities.

Final focused verification: 264 reporting/export/project-write/architecture
and resource-capacity tests passed, including the batch-lookup guard.
Touched-file Ruff F/I, Python compilation, and `git diff --check` passed.
The full PM suite was not rerun for this structural cutover.
