# Clean Refactor Execution Spec

This file is the execution-level companion to `README.md`.

It captures the practical refactor rules from the provided spec, but applies the project decision that the migration must be clean:

- no compatibility facades
- no re-export wrappers
- no temporary old-path modules
- no duplicated business logic
- each completed slice removes its old paths

When this file and the original downloaded execution spec differ, this file wins for migration mechanics because it reflects the no-facade decision.

## Purpose

This document tells Codex how to execute the repo restructuring safely while keeping the desktop app functional.

It answers:

1. how to execute the migration one slice at a time
2. what each new folder must contain
3. what each folder must never contain
4. how handlers, DTOs, repositories, APIs, presenters, and registries should be shaped
5. where currently-live repo features should land when the canonical tree did not name them

## Hard Execution Rules

1. Preserve runtime behavior.
2. Move one architectural slice at a time.
3. Finish the active slice before starting the next slice.
4. Do not use compatibility facades or old-path re-exports.
5. Rewrite all imports for the active slice before deleting old files.
6. Delete old paths for the active slice before marking it complete.
7. Do not change business behavior while restructuring.
8. Do not delete live features because the canonical tree omitted them.
9. Assign omitted live features to final homes before their slice closes.
10. Every completed slice must leave the desktop app runnable.

## Target Runtime Call Chain

Desktop runtime:

```text
Qt UI -> top-level desktop API -> module desktop API -> application handler -> domain + contracts -> infrastructure implementation
```

Future HTTP runtime:

```text
HTTP router/controller -> top-level HTTP API -> module HTTP API -> application handler -> domain + contracts -> infrastructure implementation
```

Rules:

- UI imports from `src/api/desktop/...`
- shell/runtime bootstrap imports from `src/api/desktop/runtime.py`
- hosted HTTP bootstrap imports from `src/api/http/...`
- module-local APIs live under `src/core/modules/<module>/api/...`
- module-local APIs do not own UI rendering or persistence

## `src/` Package Strategy

The target layout is a true `src/` layout.

Execution rule:

- create the `src/` tree first
- move code slice by slice
- rewrite callers to `src.*` paths inside the same slice
- remove old root package paths for the completed slice
- do not keep old package names as compatibility modules

Tooling that must be updated when the `src/` layout becomes active:

- `pytest.ini`
- import bootstrap assumptions in tests
- `main_qt.py`
- `main.py`
- `main_qt.spec`
- packaging scripts
- migration/Alembic paths

## Transaction Boundary Rule

Each state-changing application handler must define exactly one transaction boundary.

Rules:

- transaction begins in the application handler or application service boundary
- repositories use the provided session or unit of work
- UI does not manage transactions
- API adapters do not manage transactions
- domain entities do not manage transactions
- new handlers should accept repositories and gateways, not raw global service dictionaries

## Error And Result Convention

Command handlers return either:

- a DTO
- `Result[DTO]` when `src/application/common/result.py` exists for that slice

Query handlers return:

- DTOs
- lists of DTOs
- paged DTOs

Standard error categories:

- `DomainValidationError`
- `ApplicationPermissionError`
- `ApplicationNotFoundError`
- `InfrastructureOperationError`

Transport mapping belongs in API adapters:

- desktop API maps exceptions into UI-friendly messages or typed desktop results
- HTTP API maps validation to `400`
- HTTP API maps permission errors to `403`
- HTTP API maps not-found errors to `404`
- HTTP API maps optimistic-lock/conflict errors to `409`
- HTTP API maps infrastructure/runtime errors to `500`

Handlers must not format UI or HTTP responses.

## Handler Naming Convention

State-changing use case file:

```text
<verb>_<aggregate>.py
```

Examples:

- `create_work_order.py`
- `assign_work_order.py`
- `close_work_order.py`
- `create_project.py`
- `approve_purchase_request.py`

Each command file contains:

- one command object
- one handler class
- optional private helper functions when genuinely local

Class naming:

- command object: `CreateWorkOrderCommand`
- handler: `CreateWorkOrderHandler`

Query naming:

- file: `get_work_order.py`
- query object: `GetWorkOrderQuery`
- handler: `GetWorkOrderHandler`

DTO naming:

- `WorkOrderDto`
- `WorkOrderDetailDto`
- `WorkOrderBoardItemDto`

Forbidden in migrated slices:

- new catch-all `service.py`
- new catch-all `manager.py`
- new catch-all `helper.py`
- new catch-all `utils.py`

## Repository Contract Convention

Repository contracts must be use-case driven and aggregate scoped.

Allowed method categories:

- `get_by_id(...)`
- `save(...)`
- `delete(...)` only when delete semantics are real
- aggregate-specific `list_*` or `find_*` methods
- list methods scoped by organization, site, project, asset, warehouse, or another owned boundary

Forbidden repository styles:

- giant generic repositories
- one repository serving unrelated aggregates
- repositories exposing raw ORM query objects outside infrastructure

Repository interface placement:

```text
src/core/modules/<module>/contracts/repositories/
```

Repository implementation placement:

```text
src/core/modules/<module>/infrastructure/persistence/repositories/
```

## Persistence Split Rule

Global infrastructure owns:

- engine creation
- session factory
- unit of work
- migration bootstrap
- shared ORM base metadata roots
- shared DB helpers

Global placement:

```text
src/infra/persistence/
  db/
  migrations/
  orm/
```

Module infrastructure owns:

- module repository implementations
- module ORM mappers or mapping helpers
- module read models
- module query projections

Module placement:

```text
src/core/modules/<module>/infrastructure/persistence/
  repositories/
  mappers/
  read_models/
```

Preferred ORM row placement:

```text
src/infra/persistence/orm/<module>/
```

Preferred domain-to-ORM mapper placement:

```text
src/core/modules/<module>/infrastructure/persistence/mappers/
```

Dashboard, board, planner, and report reads belong in:

```text
src/core/modules/<module>/infrastructure/persistence/read_models/
```

## Unnamed Live Feature Final Homes

These features exist today and must not be lost.

### Project Management

| Live feature | Final target home |
| --- | --- |
| portfolio | `application/projects/queries/` plus `infrastructure/persistence/read_models/portfolio_*` |
| register | `application/risk/queries/` when risk semantics apply, otherwise `application/projects/queries/` |
| collaboration | `application/tasks/commands/`, `application/tasks/queries/`, `contracts/gateways/`, and infra-backed collaboration storage |
| timesheet | `application/resources/` initially, or `application/time_entries/` if the slice expands it |
| import_service | `infrastructure/importers/` plus application command handlers |
| dashboard coordinators | application queries plus infrastructure read models |

### Inventory & Procurement

| Live feature | Final target home |
| --- | --- |
| reservations | `domain/inventory/` plus `application/inventory/commands/` and `queries/` |
| stock_control | fold into the `inventory` subdomain |
| maintenance_integration | `contracts/gateways/maintenance_*` plus infrastructure adapters |
| data_exchange | `contracts/gateways/` plus `infrastructure/importers/` and `exporters/` |
| reporting helpers | `infrastructure/reporting/` |

### Maintenance

| Live feature | Final target home |
| --- | --- |
| planner | `application/preventive/queries/`, planner read models, and `ui/modules/maintenance/workspaces/planner_*` |
| dashboard | `application/reliability/queries/` plus dashboard read models |
| task templates | `domain/preventive/` or `domain/work_orders/` based on ownership found during extraction |
| asset library | asset queries plus `ui/modules/maintenance/workspaces/` |
| preventive library | preventive queries plus `ui/modules/maintenance/workspaces/` |
| runtime contract catalog | module API/support area until broader runtime contract strategy is finalized |

### HR, Payroll, And QHSE Ownership

- HR owns employee master data.
- Payroll reads employee payroll-facing data through contracts or gateways.
- QHSE may reference asset IDs and employee IDs only.
- Maintenance uses employee lookup gateways and must not import HR internals.

## Composition Root Rule

Current composition root:

- `infra/platform/services.py`
- `infra/platform/service_registration/*`

Target composition root:

```text
src/infra/composition/
  app_container.py
  platform_registry.py
  project_registry.py
  inventory_registry.py
  maintenance_registry.py
  hr_registry.py
  payroll_registry.py
  qhse_registry.py
```

Each registry must:

- instantiate repository implementations
- instantiate command handlers
- instantiate query handlers
- instantiate module API adapters
- expose one bundle object to the app container

`app_container.py` must:

- load settings
- create engine and session factory
- create event bus, storage, and notifiers
- create platform registry
- create module registries
- expose a typed container for entrypoints

No business logic belongs in composition.

## UI Refactor Rule

Target UI structure:

```text
src/ui/
  shell/
  shared/
  platform/
  modules/
```

`src/ui/shell/` holds:

- app bootstrap glue
- login dialog wiring
- main window
- navigation registration

`src/ui/shared/` holds:

- reusable widgets
- reusable dialogs
- formatting helpers
- UI models

`src/ui/platform/` holds:

- platform-owned workspaces
- platform-owned dialogs
- platform-owned widgets

`src/ui/modules/<module>/` must use:

```text
workspaces/
dialogs/
presenters/
view_models/
widgets/
```

Presenter priority:

- PM dashboard and scheduling screens
- Maintenance planner
- Maintenance work orders
- Inventory stock control
- Inventory reservations

View models are UI-shaped only.

Examples:

- `WorkOrderRowViewModel`
- `TaskBoardCardViewModel`
- `StockBalanceRowViewModel`

## API Refactor Rule

Create top-level desktop APIs:

```text
src/api/desktop/runtime.py
src/api/desktop/platform/
src/api/desktop/project_management/
src/api/desktop/inventory_procurement/
src/api/desktop/maintenance/
```

Create parallel HTTP APIs:

```text
src/api/http/platform/
src/api/http/project_management/
src/api/http/inventory_procurement/
src/api/http/maintenance/
```

Desktop APIs must:

- expose stable methods for UI usage
- accept typed command/query objects or primitive inputs
- return DTOs or result envelopes
- translate application exceptions to UI-friendly errors

HTTP APIs must:

- map web input to command/query objects
- return serialized DTOs
- translate exceptions to HTTP-level responses

## Slice Execution Order

### Slice 1: Platform And `src/` Bootstrap

Do:

1. Create the `src/` tree.
2. Move platform runtime orchestration into `src/application/runtime/`.
3. Create `src/infra/composition/`.
4. Move platform DB bootstrapping into `src/infra/persistence/`.
5. Move shell code into `src/ui/shell/`.
6. Create `src/api/desktop/runtime.py`.
7. Rewrite entrypoints and tests to new imports.
8. Delete old platform paths after callers are rewritten.

Do not:

- move all modules at once
- keep root package wrappers
- delete live behavior

Status as of 2026-04-16:

Completed:

- `src/` tree and package markers are in place
- platform runtime orchestration now lives in `src/application/runtime/platform_runtime.py`
- entitlement/module runtime now lives in `src/application/runtime/entitlement_runtime.py`
- old `application/` package path was deleted after import rewrite
- platform HTTP API now lives in `src/api/http/platform/`
- old top-level `api/` package path was deleted after import rewrite
- composition root now lives in `src/infra/composition/app_container.py`
- platform, project, inventory, and maintenance service-registration bundles now live as composition registries under `src/infra/composition/`
- old `infra/platform/services.py` and `infra/platform/service_registration/` paths were deleted after import rewrite
- database bootstrap was split from `infra/platform/db/base.py` into:
  - `src/infra/persistence/orm/base.py`
  - `src/infra/persistence/db/engine.py`
  - `src/infra/persistence/db/session_factory.py`
  - `src/infra/persistence/db/unit_of_work.py`
- old `infra/platform/db/base.py` was deleted after import rewrite
- Alembic assets were moved from `migration/*` to `src/infra/persistence/migrations/*`
- migration execution moved from `infra/platform/migrate.py` to `src/infra/persistence/migrations/runner.py`
- `main.py`, `main_qt.py`, and `main_qt.spec` now reference the new migration runner/assets path
- platform ORM model files were moved out of `infra/platform/db/`:
  - `models.py` now lives at `src/infra/persistence/orm/platform/models.py`
  - `inventory_models.py` now lives at `src/infra/persistence/orm/inventory_procurement/models.py`
  - `maintenance_models.py` now lives at `src/infra/persistence/orm/maintenance/models.py`
  - `maintenance_preventive_runtime_models.py` now lives at `src/infra/persistence/orm/maintenance/preventive_runtime_models.py`
- platform persistence helpers and adapters now live under `src/infra/persistence/db/`:
  - `optimistic.py`
  - `platform/access`
  - `platform/approval`
  - `platform/audit`
  - `platform/auth`
  - `platform/documents`
  - `platform/modules`
  - `platform/org`
  - `platform/party`
  - `platform/runtime_tracking`
  - `platform/time`
- the old `infra/platform/db/` source package was deleted after direct import rewrites
- old platform DB facade files were removed instead of recreated:
  - `infra/platform/db/repositories.py`
  - `infra/platform/db/repositories_org.py`
  - `infra/platform/db/mappers.py`
- composition registries, module repositories, regression tests, architecture guardrails, and test path rewrites now use direct imports
- the real shell package now lives under `src/ui/shell/`:
  - `__init__.py`
  - `app.py`
  - `login.py`
  - `main_window.py`
  - `navigation.py`
  - `common.py`
  - `workspaces.py`
  - `platform/*`
  - `project_management/*`
  - `inventory_procurement/*`
  - `maintenance_management/*`
- `src/ui/shell/app.py` now owns shell startup glue and `main_qt.py` delegates to it
- `src/ui/shell/login.py` now owns login dialog wiring
- UI tests and test path rewrites now use `src.ui.shell`
- the old `ui/platform/shell/` source package was deleted after direct import rewrites
- desktop runtime/platform API now lives under `src/api/desktop/`:
  - `runtime.py` builds a desktop API registry from the service graph
  - `platform/models.py` defines desktop result envelopes, DTOs, and commands
  - `platform/runtime.py` adapts platform runtime and organization flows for desktop consumers
- `src/ui/shell/app.py` now exposes the desktop API registry and platform runtime desktop adapter in the desktop service map
- targeted desktop adapter tests were added for platform runtime flows
- runtime tracking now lives under `src/core/platform/runtime_tracking/`:
  - `domain/runtime_execution.py`
  - `contracts.py`
  - `application/runtime_execution_service.py`
- placeholder runtime-tracking target files were removed from `src/core/platform/runtime_tracking/`
- importing/exporting/report runtime, composition, and persistence now use `src.core.platform.runtime_tracking`
- the old `core/platform/runtime_tracking/` source package was deleted after direct import rewrites
- report runtime now lives under `src/core/platform/report_runtime/`:
  - `domain/report_definition.py`
  - `domain/report_document.py`
  - `application/report_definition_registry.py`
  - `application/report_runtime.py`
- placeholder report-runtime target files were removed from `src/core/platform/report_runtime/`
- reporting contracts/services/tests now use `src.core.platform.report_runtime`
- the old `core/platform/report_runtime/` source package was deleted after direct import rewrites
- importing now lives under `src/core/platform/importing/`:
  - `domain/import_definition.py`
  - `domain/import_models.py`
  - `application/import_definition_registry.py`
  - `application/csv_import_runtime.py`
- exporting now lives under `src/core/platform/exporting/`:
  - `domain/export_definition.py`
  - `domain/export_models.py`
  - `application/artifact_delivery.py`
  - `application/export_definition_registry.py`
  - `application/export_runtime.py`
- platform data exchange, module import/export services, report runtime, UI import flows, and tests now use `src.core.platform.importing` and `src.core.platform.exporting`
- the old `core/platform/importing/` and `core/platform/exporting/` source packages were deleted after direct import rewrites
- time now lives under `src/core/platform/time/`:
  - `domain/timesheet_models.py`
  - `contracts.py`
  - `application/time_service.py`
  - `application/timesheet_entries.py`
  - `application/timesheet_periods.py`
  - `application/timesheet_query.py`
  - `application/timesheet_review.py`
  - `application/timesheet_support.py`
- placeholder time target files were removed from `src/core/platform/time/`
- composition, persistence, PM timesheet wrappers/domain/UI, maintenance labor, and tests now use `src.core.platform.time`
- the old `core/platform/time/` source package was deleted after direct import rewrites
- auth now lives under `src/core/platform/auth/`:
  - `domain/user.py`
  - `domain/session.py`
  - `contracts/auth_repository.py`
  - `application/auth_query.py`
  - `application/auth_validation.py`
  - `application/auth_service.py`
  - `authorization.py`
  - `datetime_utils.py`
  - `mfa.py`
  - `passwords.py`
  - `policy.py`
  - `sod.py`
- placeholder auth target files were removed from `src/core/platform/auth/`
- auth-specific repository contracts moved out of `core/platform/common/interfaces.py` into `src/core/platform/auth/contracts/auth_repository.py`
- composition, platform services, runtime packages, module services, UI, tests, persistence, and test path rewrites now use `src.core.platform.auth`
- the old `core/platform/auth/` source package was deleted after direct import rewrites
- authorization now lives under `src/core/platform/authorization/`:
  - `domain/authorization_engine.py`
  - `application/session_authorization_engine.py`
- placeholder authorization target files were removed from `src/core/platform/authorization/`
- platform auth/access helpers and authorization tests now use `src.core.platform.authorization`
- the old `core/platform/authorization/` source package was deleted after direct import rewrites
- access now lives under `src/core/platform/access/`:
  - `domain/access_scope.py`
  - `domain/feature_access.py`
  - `application/access_control_service.py`
  - `contracts.py`
  - `authorization.py`
- placeholder access target files were removed from `src/core/platform/access/`
- access-specific repository contracts moved out of `core/platform/common/interfaces.py` into `src/core/platform/access/contracts.py`
- composition, auth principal building, persistence, platform services, module services, UI, tests, and test path rewrites now use `src.core.platform.access`
- the old `core/platform/access/` source package was deleted after direct import rewrites

Verified:

- `python -m compileall -q src infra ui core tests main.py main_qt.py main_qt.spec`
- direct import/smoke checks for platform runtime, entitlement runtime, HTTP platform adapter, and persistence bootstrap
- direct import of `src.infra.persistence.db.optimistic.update_with_version_check`
- direct import of `src.ui.shell.navigation.ShellNavigation`
- migration asset lookup resolves the new `src/infra/persistence/migrations/alembic.ini`
- in `conda run -n pmenv`:
  - direct import of `src.ui.shell.main_window.MainWindow`
  - direct import of `src.api.desktop.runtime.build_desktop_api_registry`
  - direct import of `src.core.platform.runtime_tracking.RuntimeExecutionService`, `RuntimeExecutionRepository`, and `RuntimeExecution`
  - direct import of `src.core.platform.report_runtime.ReportDefinitionRegistry`, `ReportRuntime`, `ReportDocument`, and `ReportFormat`
  - direct import of `src.core.platform.importing.CsvImportRuntime`, `ImportDefinitionRegistry`, and `ImportFieldSpec`
  - direct import of `src.core.platform.exporting.ExportArtifactDraft`, `ExportDefinitionRegistry`, and `ExportRuntime`
  - direct import of `src.core.platform.time.application.TimeService`, `src.core.platform.time.contracts.TimeEntryRepository`, `src.core.platform.time.domain.TimesheetPeriodStatus`, and `src.core.platform.time.application.timesheet_review.TimesheetReviewQueueItem`
  - direct import of `src.core.platform.auth.AuthService`, `UserSessionContext`, `UserSessionPrincipal`, `UserRepository`, `AuthSessionRepository`, `UserAccount`, and `AuthSession`
  - direct import of `src.core.platform.authorization.AuthorizationEngine`, `SessionAuthorizationEngine`, `get_authorization_engine`, and `set_authorization_engine`
  - direct import of `src.core.platform.access.AccessControlService`, `ScopedRolePolicy`, `ScopedRolePolicyRegistry`, `ProjectMembershipRepository`, `ScopedAccessGrantRepository`, `ProjectMembership`, and `ScopedAccessGrant`
  - `pytest tests/test_platform_runtime_desktop_api.py tests/test_platform_runtime_http_api.py -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_db_facades_are_removed tests/test_architecture_guardrails.py::test_composition_imports_focused_persistence_adapters -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_db_facades_are_removed tests/test_architecture_guardrails.py::test_composition_imports_focused_persistence_adapters tests/test_platform_runtime_http_api.py tests/test_platform_runtime_desktop_api.py -q`
  - `pytest tests/test_platform_import_export_report_runtime.py tests/test_runtime_execution_tracking.py tests/test_maintenance_runtime_contracts.py -q`
  - `pytest tests/test_platform_import_export_report_runtime.py tests/test_runtime_execution_tracking.py tests/test_maintenance_runtime_contracts.py tests/test_architecture_guardrails.py::test_legacy_platform_import_export_packages_are_removed -q`
  - `pytest tests/test_shared_collaboration_import_and_timesheets.py tests/test_service_architecture.py tests/test_architecture_guardrails.py::test_legacy_platform_time_package_is_removed -q`
  - `pytest tests/test_auth_module_phase_a.py tests/test_auth_validation_and_query.py tests/test_authorization_engine.py tests/test_passwords.py tests/test_phase_b_session_permissions.py -q`
  - `pytest tests/test_service_architecture.py tests/test_platform_access_scopes.py tests/test_architecture_guardrails.py::test_legacy_platform_auth_package_is_removed tests/test_architecture_guardrails.py::test_auth_service_is_orchestrator_only -q`
  - `pytest tests/test_authorization_engine.py tests/test_platform_access_scopes.py tests/test_auth_module_phase_a.py tests/test_architecture_guardrails.py::test_legacy_platform_authorization_package_is_removed -q`
  - `pytest tests/test_auth_module_phase_a.py tests/test_authorization_engine.py tests/test_platform_access_scopes.py tests/test_service_architecture.py tests/test_architecture_guardrails.py::test_legacy_platform_access_package_is_removed tests/test_architecture_guardrails.py::test_platform_common_interfaces_are_platform_only -q`
- no Python import statements remain for `core.platform.importing` or `core.platform.exporting`
- no Python import statements remain for `core.platform.time`
- no Python import statements remain for `core.platform.auth`
- no Python import statements remain for `core.platform.authorization`
- no Python import statements remain for `core.platform.access`

Known blocker:

- the default interpreter outside `pmenv` still fails on `reportlab` during full app/test imports because that environment dependency is not installed there
- executing migrations also requires the declared `alembic` dependency to be installed in the active environment

Continue next:

1. Split the remaining `core/platform/*` packages into `domain/`, `application/`, and `contracts/` without wrappers: `modules`, `org`, `party`, `approval`, `documents`, `notifications`, and `audit`.
2. Split the large ORM aggregate further as module slices move ownership into their target infrastructure packages.
3. Move platform admin/control/settings/shared UI paths.
4. Update test path strategy and remove path rewrites only after the new paths are complete.

### Slice 2: Project Management

Do:

1. Split PM domain by `projects`, `tasks`, `scheduling`, `resources`, `risk`, and `financials`.
2. Extract PM contracts from broad interfaces.
3. Break scheduling engine into graph builder, forward pass, backward pass, critical path, calendars, and baseline comparison.
4. Convert broad PM services into command/query handlers.
5. Move PM repositories and read models under module infrastructure.
6. Add PM desktop API adapters.
7. Add PM presenters and view models.
8. Rewrite imports and delete old PM paths for the moved code.

### Slice 3: Inventory & Procurement

Do:

1. Split into `catalog`, `inventory`, `procurement`, and `pricing`.
2. Fold stock control into `inventory`.
3. Keep reservations as explicit inventory use cases.
4. Keep maintenance integration behind gateway contracts.
5. Add inventory desktop API adapters.
6. Rewrite imports and delete old inventory paths for the moved code.

### Slice 4: Maintenance

Do:

1. Rename `maintenance_management` to `maintenance`.
2. Split domain by `assets`, `locations`, `work_requests`, `work_orders`, `preventive`, `reliability`, and `documents`.
3. Split service files into command/query handlers.
4. Move repositories, mappers, and read models into module infrastructure.
5. Add planner and dashboard read models.
6. Add maintenance desktop API adapters.
7. Add presenters for planner and work orders.
8. Rewrite imports and delete old maintenance-management paths.

### Slice 5: HR, Payroll, And QHSE Skeletons

Do:

1. Create package skeletons.
2. Create registries and empty API surfaces.
3. Establish ownership rules through contracts.
4. Add architecture tests for cross-module isolation.

### Slice 6: Cleanup

Do:

1. Delete any remaining legacy paths.
2. Delete path rewrite helpers.
3. Update architecture tests to forbid old imports.
4. Update README and packaging docs.

## Architecture Tests Codex Must Add

Layer import tests:

- `src/core/**` must not import `src/ui/**`
- `src/core/**` must not import `src/api/**`
- `src/core/**` must not import repository implementations
- `src/ui/**` must not import `src/core/**/infrastructure/**`
- `src/api/**` must not import ORM repositories directly

Cross-module isolation tests:

- one module must not import another module's `domain/` directly
- one module must not import another module's `infrastructure/` directly
- allowed cross-module references go through contracts, gateways, events, or IDs

Giant-file regression tests:

- enforce file-size ceilings for known hotspots
- prioritize scheduling engine, work-order flows, preventive flows, and large UI tabs

Clean-cutover tests:

- old imports for completed slices must fail or be absent
- entrypoints must import from the target paths
- runtime must start through the new app container

## Current-To-Target Mapping Rules

`main_qt.py` target split:

- `src/ui/shell/app.py` for shell startup glue
- `src/infra/composition/app_container.py` for container build
- `src/api/desktop/runtime.py` for runtime-facing desktop API
- keep `main_qt.py` only as the root entrypoint that calls the new shell app

`infra/platform/services.py` target split:

- `src/infra/composition/app_container.py`
- `src/infra/composition/platform_registry.py`
- `src/infra/composition/project_registry.py`
- `src/infra/composition/inventory_registry.py`
- `src/infra/composition/maintenance_registry.py`

`infra/platform/service_registration/*` target:

- convert into `src/infra/composition/*_registry.py`
- do not leave old bundle builders after the slice is complete

`migration/` target:

- `src/infra/persistence/migrations/`

`api/http/platform/*` target:

- `src/api/http/platform/*`
- add matching `src/api/desktop/platform/*`

`ui/platform/shell/*` target:

- `src/ui/shell/*`

`ui/platform/admin`, `control`, `settings`, and `shared` target:

- platform-owned screens to `src/ui/platform/workspaces/`
- platform-owned dialogs to `src/ui/platform/dialogs/`
- platform-owned widgets to `src/ui/platform/widgets/`
- reusable pieces to `src/ui/shared/*`

`core/modules/project_management/services/*` target:

- `application/<subdomain>/commands/`
- `application/<subdomain>/queries/`
- reporting and import code to infrastructure adapters
- scheduling split under `domain/scheduling/` and `application/scheduling/`

`core/modules/inventory_procurement/services/*` target:

- catalog application handlers
- inventory application handlers
- procurement application handlers
- reporting, import, and export under infrastructure

`core/modules/maintenance_management/services/*` target:

- assets application handlers
- work requests application handlers
- work orders application handlers
- preventive application handlers
- reliability application handlers
- reporting, import, export, and read models under infrastructure

## File Creation Rules

Allowed names:

- `create_<aggregate>.py`
- `update_<aggregate>.py`
- `get_<aggregate>.py`
- `list_<aggregate>.py`
- `<aggregate>_dto.py`
- `<aggregate>_mapper.py`
- `sql_<aggregate>_repository.py`

Avoid generic names:

- `utils.py`
- `helpers.py`
- `manager.py`
- `common_service.py`
- `misc.py`

Generic names are allowed only when the file is truly cross-cutting and the owning layer is obvious.

## Codex Working Modes

Scaffold:

- create folders
- add `__init__.py`
- create placeholder classes/files
- do not move logic yet

Extract:

- move existing code into new files without changing behavior
- rewrite imports as part of the same slice

Normalize:

- standardize handler names
- standardize DTO names
- standardize interfaces
- standardize registries

Enforce:

- add architecture tests
- remove old paths for the completed slice
- verify entrypoints and tests

Forbidden behavior:

- inventing new product behavior
- deleting current live features because the canonical tree omitted them
- changing business logic during pure structure moves
- leaving compatibility facades after a slice is complete

## Completion Criteria

A migration slice is complete only when:

- the desktop app still launches
- tests for the slice pass
- architecture tests enforce the new boundary
- old paths for the completed slice are removed
- no new `ui -> repository` dependency exists
- no new direct cross-module internal import exists

## Final Instruction

Use `README.md` as the architecture map.

Use this file as the execution contract.

When the two differ:

- `README.md` controls destination structure
- this file controls clean migration mechanics, naming conventions, dependency rules, and unresolved feature placement

If a feature or file is still ambiguous after both documents, stop and assign it a final home before moving that slice. Do not preserve it through compatibility facades.
