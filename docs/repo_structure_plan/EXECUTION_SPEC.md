# Clean Refactor Execution Spec

This file is the execution-level companion to `README.md`.

It captures the practical refactor rules from the provided specs, including `PySide6_Widgets_to_QML_Migration_Spec.docx`, but applies the project decision that the migration must be clean:

- no compatibility facades
- no re-export wrappers
- no temporary old-path modules
- no duplicated business logic
- each completed slice removes its old paths

When this file and the original downloaded execution spec differ, this file wins for migration mechanics because it reflects the no-facade decision.

For desktop UI migration, `PySide6_Widgets_to_QML_Migration_Spec.docx` wins over older Widget-oriented wording:

- final desktop UI lives under `src/ui_qml/*`
- active Widget UI under `src/ui/*` remains temporary legacy UI until each screen is migrated
- old Widget paths are deleted only after the matching QML screen, presenter, view model, route, and tests are complete
- `src/ui_qml/*` is scaffolded and the initial shell route/registry/navigation/QML engine foundation exists, but it must not become the active entrypoint until the QML shell is complete and tested end-to-end

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
QML view -> presenter -> view model -> module desktop API -> application handler -> domain + contracts -> infrastructure implementation
```

Future HTTP runtime:

```text
HTTP router/controller -> top-level HTTP API -> module HTTP API -> application handler -> domain + contracts -> infrastructure implementation
```

Rules:

- QML-facing presenters import module desktop APIs from `src/core/modules/<module>/api/desktop/...`
- shell/runtime bootstrap may import a thin aggregation entrypoint from `src/api/desktop/...`
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
- SQLAlchemy `Base` and metadata loading
- shared DB helpers

Global placement:

```text
src/infra/persistence/
  db/
  migrations/
  orm/                  # Base + metadata registry only; not module row ownership
```

Platform infrastructure owns:

- platform repository implementations
- platform ORM row definitions
- platform ORM mappers or mapping helpers

Platform placement:

```text
src/core/platform/infrastructure/persistence/
  orm/
  <area>/
```

Module infrastructure owns:

- module repository implementations
- module ORM row definitions
- module ORM mappers or mapping helpers
- module read models
- module query projections

Module placement:

```text
src/core/modules/<module>/infrastructure/persistence/
  orm/
  repositories/
  mappers/
  read_models/
```

Preferred ORM row placement:

```text
src/core/modules/<module>/infrastructure/persistence/orm/
```

`src/infra/persistence/orm/<module>/` is not the final home for business-module rows. Any existing module folders there are transitional Slice 1 de-mixing locations and must be removed during the owning module slice after rows move into module-local infrastructure. Platform-owned persistence follows the module pattern under `src/core/platform/infrastructure/persistence/{orm,mappers,repositories}/`.

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
| portfolio | `application/projects/{commands,queries}/` plus `infrastructure/persistence/read_models/portfolio_*` when dedicated portfolio read projections are extracted |
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

## QML UI Migration Rule

Target UI structure:

```text
src/ui_qml/
  shell/
    app.py
    login.py
    main_window.py
    navigation.py
    qml_engine.py
    qml_registry.py
    routes.py
    qml/
      App.qml
      MainWindow.qml
      LoginDialog.qml
      ShellHeader.qml
      ShellDrawer.qml
  shared/
    qml/
      App/
        Controls/
        Dialogs/
        Widgets/
        Layouts/
        Theme/
    presenters/
    view_models/
    models/
    services/
    formatting/
  platform/
    qml/
      Platform/
        Widgets/
      workspaces/
        admin/
        control/
        settings/
      dialogs/
      widgets/
    presenters/
    view_models/
  modules/
    <module>/
      qml/
        workspaces/
        dialogs/
        widgets/
      presenters/
      view_models/
  legacy_widgets/
    migration_only/
      adapters/
      screens/
      dialogs/
```

`src/ui_qml/shell/` holds:

- app bootstrap glue
- QML engine setup
- login wiring
- main window wiring
- navigation registration
- QML route registration

`src/ui_qml/shared/` holds:

- reusable QML controls
- reusable QML dialogs
- reusable QML widgets
- QML layouts and theme assets
- shared presenters
- shared view models
- formatting helpers
- UI models
- UI services

`src/ui_qml/platform/` holds:

- platform-owned QML workspaces
- platform-owned QML dialogs
- platform-owned QML widgets
- platform presenters and view models

`src/ui_qml/modules/<module>/` must use:

```text
qml/workspaces/
qml/dialogs/
qml/widgets/
presenters/
view_models/
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

QML migration rules:

- QML renders and binds state only
- QML must not contain business rules or direct repository/session/ORM access
- presenters or workspace-controller/catalog objects own user intent, loading/busy/error/feedback state, refresh, mutation sequencing, navigation, dialog orchestration, and API calls
- presenters call module-owned desktop APIs, not repositories or handlers directly
- view models expose display-ready values only
- reusable QML must be exposed through `qmldir`-backed named modules, not parent-relative imports
- shared reusable QML uses `App.*` namespaces and platform reusable QML uses `Platform.*` namespaces
- keep aliases consistent in active files: `Theme`, `AppLayouts`, `AppWidgets`, `AppControls`, and `PlatformWidgets`
- old Widget screens under `src/ui/*` remain active only until migrated
- delete old Widget files screen-by-screen after QML replacement, navigation rewrite, and tests
- quarantine temporary Widget artifacts only under `src/ui_qml/legacy_widgets/migration_only/*`
- no permanent Widget/QML mixed screen after a screen slice is complete

QML shell migration status as of 2026-04-24:

- `src/ui_qml/shell/routes.py` defines QML route metadata and shell QML path resolution
- `src/ui_qml/shell/qml_registry.py` owns duplicate-safe route registration and route lookup
- `src/ui_qml/shell/navigation.py` and `main_window.py` build shell navigation view models from registered routes
- `src/ui_qml/shell/context.py` exposes `shellContext` for QML-safe app title, navigation items, current route, theme mode, and user display name binding
- `src/ui_qml/shell/qml_engine.py` now registers shared/platform/module QML import roots so named modules resolve during runtime and offscreen loading
- `src/ui_qml/shell/login.py` contains initial QML login view-model state
- `src/ui_qml/shell/qml/*` contains valid shell QML component placeholders bound to `shellContext`
- `src/ui_qml/shell/qml/MainWindow.qml` now hosts the selected registered workspace through a `Loader` bound to `shellContext.currentRouteSource`
- `shell.app` is the top-level QML app route and `shell.home` now points at `HomeWorkspace.qml`, not back at `MainWindow.qml`, so the shell can host routed workspaces without recursive loading
- `main_qt.py` still points to `src.ui.shell.app`; the QWidget app remains the active runtime until the QML shell has full parity
- `tests/test_qml_shell_migration.py` covers the shell route registry, route-source navigation metadata, login view-model defaults, and entrypoint safety
- offscreen QML loading has verified that `App.qml` loads with the exposed `shellContext`

Shared QML primitive status as of 2026-04-24:

- `src/ui_qml/shared/qml/App/Theme/AppTheme.qml` defines the first QML token set aligned to the existing Widget `UIConfig` palette
- `src/ui_qml/shared/qml/App/{Theme,Controls,Widgets,Layouts}/qmldir` now define stable named modules for `App.Theme`, `App.Controls`, `App.Widgets`, and `App.Layouts`
- `src/ui_qml/shared/qml/App/Controls/PrimaryButton.qml` provides the first reusable QML action control
- `src/ui_qml/shared/qml/App/Widgets/MetricCard.qml` provides the first reusable dashboard/status card primitive
- `src/ui_qml/shared/qml/App/Layouts/WorkspaceFrame.qml` provides the first reusable workspace shell frame with a default content slot
- shell, platform, and current PM QML now import these shared primitives through named modules instead of deep parent-relative paths
- `tests/test_qml_shared_primitives.py` covers the primitive file contract and token alignment

Platform QML route status as of 2026-04-24:

- `src/ui_qml/platform/routes.py` registers QML routes for platform admin, control, and settings workspaces
- `src/ui_qml/platform/qml/workspaces/admin/AdminWorkspace.qml`, `control/ControlWorkspace.qml`, and `settings/SettingsWorkspace.qml` are now thin entry wrappers over split workspace pages
- `src/ui_qml/platform/qml/workspaces/admin/{AdminConsolePage,AdminMetricsSection,AdminCatalogGrid,AdminDocumentSection,AdminOverviewSections,AdminDialogHost}.qml` now own the split platform-admin QML surface
- `src/ui_qml/platform/qml/workspaces/control/{ControlWorkspacePage,ControlMetricsSection,ApprovalQueueSection,AuditFeedSection}.qml` now own the split platform-control QML surface
- `src/ui_qml/platform/qml/workspaces/settings/{SettingsWorkspacePage,SettingsMetricsSection,SettingsRuntimeSection,ModuleEntitlementsSection,OrganizationProfilesSection,SettingsOverviewSections}.qml` now own the split platform-settings QML surface
- `src/ui_qml/platform/context.py` still exposes `PlatformWorkspaceCatalog`, but the shell now injects that object onto loaded workspaces instead of leaving the workspace pages to reach for a raw global context property
- `src/ui_qml/platform/qml/Platform/Controllers/{qmldir,typeinfo/*}` plus `src/ui_qml/platform/qml_type_registration.py` now expose typed platform controller classes to QML tooling and runtime, and the grouped `typeinfo/*.fragment` files keep the metadata maintainable
- `src/ui_qml/platform/presenters/runtime_presenter.py` consumes `src.api.desktop.platform.PlatformRuntimeDesktopApi`
- `src/ui_qml/platform/presenters/{admin_presenter,control_presenter,settings_presenter}.py` now compose grouped platform admin/control/settings overview state from split platform desktop APIs
- `src/ui_qml/platform/view_models/{runtime,workspace}.py` defines QML-safe platform runtime and grouped workspace overview view models
- `src/ui_qml/platform/presenters/{control_queue_presenter,settings_catalog_presenter}.py` now compose real control/settings action-list data from split platform desktop APIs without growing the overview presenters into dump files
- grouped controller classes under `src/ui_qml/platform/controllers/{common,admin,control,settings}/*` now own common workspace state plus action and refresh sequencing; the old top-level `workspace_state.py`, `admin_workspace_state.py`, and `access_workspace_state.py` are no longer the active structure
- the stale `src/ui_qml/platform/controllers/admin/admin_workspace_controller.py` file has been deleted; `PlatformAdminWorkspaceController` is now exported from `src/ui_qml/platform/controllers/admin/admin_console_controller.py` and delegates to the split admin controllers instead of duplicating their state
- `src/ui_qml/platform/presenters/{organization_catalog_presenter,site_catalog_presenter,department_catalog_presenter,employee_catalog_presenter,user_catalog_presenter,party_catalog_presenter,document_catalog_presenter}.py` now provide the split admin QML workflow presenters for organization/site/department/employee/user/party/document actions
- `src/ui_qml/platform/presenters/document_management_presenter.py` now owns document focus, preview-state, linked-record, and structure-management presentation logic so those workflows do not bloat the document catalog presenter or the QML file
- document state ownership is now cleanly split: `document_controller.py` owns document catalog, selected-document, preview, and link state, while `document_structure_controller.py` owns structure catalog and structure editor options
- `src/ui_qml/platform/presenters/access_workspace_presenter.py` now provides the split admin QML scoped-access and account-security presenter
- `src/ui_qml/platform/qml/Platform/Widgets/{OverviewSectionCard,RecordListCard,WorkspaceStateBanner,AdminCatalogPanel,DocumentDetailPanel}.qml` provide reusable grouped overview, action-list, workspace-state, admin catalog, and document-detail rendering for the platform workspaces
- `src/ui_qml/platform/qml/Platform/Dialogs/{OrganizationEditorDialog,SiteEditorDialog,DepartmentEditorDialog,EmployeeEditorDialog,UserEditorDialog,PartyEditorDialog,DocumentEditorDialog,DocumentLinkEditorDialog,DocumentStructureEditorDialog,ApprovalDecisionDialog,ModuleLifecycleDialog}.qml` provide focused QML dialogs for the current migrated platform workflows
- `platform.admin` now exposes a real QML organization/site/department/employee/user/party/document surface with create, edit, toggle-active, set-active, role, and password-reset flows
- `platform.admin` now also exposes a real QML selected-document surface with preview/open state, linked-record actions, and document-structure management through controller-owned state/actions
- `platform.admin` now also exposes a real QML scoped-access and account-security surface
- `platform.control` now exposes a real QML approval queue with approve/reject actions, decision-note entry, and a real QML audit feed
- `platform.settings` now exposes a real QML module-entitlement surface with license/enable toggles, lifecycle-status changes, plus organization-profile visibility
- platform admin/control/settings QML no longer uses page-local `refreshWorkspace()` JavaScript or page-local feedback orchestration
- support now has a real QML workflow through the split support desktop API/controller path, but the legacy QWidget support files still remain until the old platform shell is retired
- `tests/test_qml_platform_routes.py` covers platform route registration and workspace file existence
- `tests/test_qml_platform_presenters.py` covers platform QML presenter/context behavior for connected, preview, grouped-overview, direct-runtime-fallback, admin master-data action lists, admin mutations, and control/settings action states
- `src/ui_qml/shell/qml/Shell/Context/{qmldir,plugins.qmltypes}` plus `src/ui_qml/shell/qml_type_registration.py` now expose a typed shell runtime surface for `shellModel`
- `App.qml` now receives `shellModel`, `platformCatalog`, and `pmCatalog` through initial properties, and `MainWindow.qml` injects those runtime objects onto loaded workspace roots
- offscreen QML loading has verified that the platform workspaces resolve with the shared QML primitives and the new runtime-injection pattern

Project Management QML route status as of 2026-04-29:

- `src/ui_qml/modules/project_management/routes.py` registers the full PM QML route set for the Slice 2 workspace names
- PM QML entry workspaces exist for `projects`, `tasks`, `scheduling`, `resources`, `financials`, `risk`, `portfolio`, `register`, `collaboration`, `timesheets`, and `dashboard`
- the dashboard now uses a split `DashboardWorkspace.qml` -> `DashboardWorkspacePage.qml` pattern with local section components, matching the platform workspace layout style
- the projects workspace now uses a split `ProjectsWorkspace.qml` -> `ProjectsWorkspacePage.qml` pattern with local metrics, filters, catalog, detail, and dialog-host components, matching the platform workspace layout style
- the remaining PM workspaces now render through `ProjectManagement.Widgets/WorkspacePlaceholderPage.qml` instead of repeating ad-hoc placeholder layouts
- the remaining PM workspaces are still landing zones only; `dashboard` is the first real read-only migrated slice and `projects` is the first real CRUD migrated slice, while active PM QWidget screens under `src/ui/*` remain active until each screen has a real QML replacement, presenter, view model, navigation rewrite, and tests
- PM QML now receives a typed `pmCatalog` through the shell loader, and `App.qml` / `MainWindow.qml` no longer treat PM as an untyped `var`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/{Controllers,Dialogs,Widgets}/qmldir` now define stable named modules for PM controller, dialog, and widget imports
- `tests/test_qml_project_management_routes.py` covers PM route registration and workspace file existence
- offscreen QML loading has verified that all PM workspaces resolve with the shared QML primitives and the typed PM runtime injection pattern

Project Management QML presenter/view-model status as of 2026-04-29:

- `src/core/modules/project_management/api/desktop/workspaces.py` defines the first module-owned PM desktop API surface used by QML routes and presenters
- `src/core/modules/project_management/api/desktop/dashboard.py` defines the first PM dashboard desktop API snapshot contract, including selector options, KPI descriptors, analysis-panel descriptors, chart descriptors, and read-only dashboard section descriptors
- `src/ui_qml/modules/project_management/view_models/workspace.py` defines the first PM QML workspace view model
- `src/ui_qml/modules/project_management/view_models/dashboard.py` defines PM dashboard overview, selector, analysis-panel, chart, section, and workspace view models for the QML dashboard slice
- `src/ui_qml/modules/project_management/presenters/workspace_presenter.py` defines the first PM QML workspace presenter contract
- `src/ui_qml/modules/project_management/presenters/dashboard_presenter.py` maps the PM dashboard desktop API overview into QML-safe view models
- `src/ui_qml/modules/project_management/presenters/dashboard_workspace_presenter.py` maps the PM dashboard desktop API snapshot into typed selector, section, and empty-state view models
- `src/ui_qml/modules/project_management/context.py` now exposes `ProjectManagementWorkspaceCatalog` as the typed PM QML catalog
- `src/ui_qml/modules/project_management/controllers/common/workspace_controller_base.py` defines the PM workspace-state base used for typed controller exposure
- `src/ui_qml/modules/project_management/controllers/dashboard/dashboard_workspace_controller.py` exposes the dashboard through a typed `ProjectManagementDashboardWorkspaceController`
- `src/ui_qml/modules/project_management/qml_type_registration.py` plus `ProjectManagement/Controllers/typeinfo/*` now expose typed runtime/tooling registration for the PM catalog and dashboard controller
- every registered PM QML route has a matching presenter-backed view model scaffold
- PM QML files now bind title, summary, migration status, and legacy-runtime status through a typed `pmCatalog` surface instead of generic `property var pmCatalog`
- `DashboardWorkspacePage.qml` now renders API-backed project selection, baseline selection, KPI cards, analysis panels, chart surfaces, workspace-state feedback, and read-only dashboard sections through a typed controller and split QML sections
- presenter/catalog scaffolding now calls the PM workspace desktop API for metadata, while the dashboard also consumes the first PM screen-specific desktop API snapshot with analysis-panel and chart state; real workflow/query desktop APIs for the other workspaces remain pending
- the dashboard read-only snapshot API is the first PM screen-specific desktop API contract; dialogs and live mutations remain pending
- active PM QWidget screens remain active; no Widget screen has been deleted or replaced
- `tests/test_qml_project_management_presenters.py` covers route-to-presenter alignment, typed dashboard controller exposure, named-module usage, QML-safe catalog maps, and guards against legacy Widget or infrastructure imports in the PM QML layer
- `tests/test_project_management_desktop_api.py` covers PM desktop workspace API descriptors and guards against QML or infrastructure imports from the desktop API layer

QML architecture guardrail status as of 2026-04-29:

- `tests/test_qml_architecture_guardrails.py` protects the QML migration dependency direction
- `tests/test_qml_offscreen_loading.py` loads every registered QML route through `QQmlApplicationEngine` with `QT_QPA_PLATFORM=offscreen`
- core source under `src/core/**` must not import `src.ui_qml` or legacy `src.ui`
- QML Python under `src/ui_qml/**` must not import legacy Widget UI, infrastructure, persistence repositories, or `PySide6.QtWidgets`
- module desktop APIs under `src/core/modules/*/api/desktop/**` must not import `src.ui_qml`
- QML files must not reference repository, ORM, SQLAlchemy, session, or persistence concepts
- QML files must not use parent-relative import paths; named-module imports are now enforced for reusable QML
- PM QML must not fall back to generic `property var pmCatalog`; typed PM catalog bindings are now enforced
- these guardrails must pass before wiring real QML screens to module desktop APIs
- registered QML routes must continue loading offscreen before any old Widget screen is deleted
- the latest PM-focused verification batches pass with `24 passed`, `9 passed`, `1 passed`, `7 passed`, and `22 passed`; and a full `qmllint` scan across `src/ui_qml/**/*.qml` is clean

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

Status as of 2026-04-19:

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
- platform ORM model files were moved out of `infra/platform/db/`; business-module ORM rows landed in temporary global de-mixing homes until their module slices move them under module-local infrastructure:
  - `models.py` initially lived at `src/infra/persistence/orm/platform/models.py`, then moved to `src/core/platform/infrastructure/persistence/orm/models.py`, and is now split into `src/core/platform/infrastructure/persistence/orm/{access,approval,audit,auth,documents,modules,org,party,runtime_tracking,time}.py`
  - `inventory_models.py` now lives at `src/infra/persistence/orm/inventory_procurement/models.py`
  - `maintenance_models.py` now lives at `src/infra/persistence/orm/maintenance/models.py`
  - `maintenance_preventive_runtime_models.py` now lives at `src/infra/persistence/orm/maintenance/preventive_runtime_models.py`
- platform persistence adapters, metadata loading, tests, and timesheet regression checks now import platform-owned infrastructure under `src.core.platform.infrastructure.persistence`
- the old global `src/infra/persistence/orm/platform/` package was deleted after direct import rewrites
- shared platform persistence helper code now lives under `src/infra/persistence/db/`:
  - `optimistic.py`
- platform persistence adapters now live under `src/core/platform/infrastructure/persistence/`:
  - `access`
  - `approval`
  - `audit`
  - `auth`
  - `documents`
  - `modules`
  - `org`
  - `party`
  - `runtime_tracking`
  - `time`
- the old global `src/infra/persistence/db/platform/` package was deleted after direct import rewrites
- the old `infra/platform/db/` source package was deleted after direct import rewrites
- old platform DB facade files were removed instead of recreated:
  - `infra/platform/db/repositories.py`
  - `infra/platform/db/repositories_org.py`
  - `infra/platform/db/mappers.py`
- composition registries, module repositories, regression tests, architecture guardrails, and test path rewrites now use direct imports
- platform runtime/ops utilities now live under `src/infra/platform/`:
  - `path.py`
  - `resource.py`
  - `logging_config.py`
  - `version.py`
  - `update.py`
  - `updater.py`
  - `diagnostics.py`
  - `operational_support.py`
  - `app_version.txt`
- shell startup, main window update checks, support workspace flows, settings persistence, persistence engine DB path lookup, PM collaboration attachments, tests, and PyInstaller data packaging now use `src.infra.platform.*`
- `src/infra/platform/resource.py` was adjusted for its deeper `src/` location so assets still resolve from the project root
- local/offline update support was preserved in the moved update helpers by keeping plain filesystem manifest paths and `file://` installer downloads working
- the old top-level `infra/platform/` package was deleted after all live files were moved
- architecture guardrails now prevent reintroducing the legacy `infra/platform/` runtime package or legacy `infra.platform` runtime imports
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
  - `platform/models/*` defines desktop result envelopes, DTOs, and commands split by concern
  - `platform/runtime.py` adapts platform runtime and organization flows for desktop consumers
- platform UI should communicate through the top-level platform API surface under `src/api/desktop/platform/*` and `src/api/desktop/runtime.py`, not through platform persistence or infrastructure modules
- the legacy QWidget Platform Home screen now consumes `PlatformRuntimeDesktopApi.get_runtime_context()` instead of calling platform runtime application-service snapshot/list methods directly
- the legacy QWidget Module Licensing screen now consumes `PlatformRuntimeDesktopApi` and `ModuleStatePatchCommand` instead of calling `PlatformRuntimeApplicationService` directly; this is the first platform Widget workflow moved onto the platform API boundary before QML replacement
- the legacy QWidget Organizations screen now consumes `PlatformRuntimeDesktopApi`, `OrganizationProvisionCommand`, and `OrganizationUpdateCommand` instead of calling `OrganizationService` or `PlatformRuntimeApplicationService` directly
- the old broad platform org desktop adapter was split into focused `src/api/desktop/platform/{site,department,employee}.py` adapters
- the legacy QWidget Sites screen now consumes `PlatformSiteDesktopApi`, `SiteCreateCommand`, and `SiteUpdateCommand` instead of calling `SiteService` directly
- `PlatformDepartmentDesktopApi` now owns department DTOs/commands and department location-reference lookup for default maintenance locations
- the legacy QWidget Departments screen now consumes `PlatformDepartmentDesktopApi`, `PlatformSiteDesktopApi`, `DepartmentCreateCommand`, and `DepartmentUpdateCommand` instead of calling `DepartmentService` or `SiteService` directly
- the legacy QWidget Employees screen now consumes `PlatformEmployeeDesktopApi`, `PlatformDepartmentDesktopApi`, `PlatformSiteDesktopApi`, `EmployeeCreateCommand`, and `EmployeeUpdateCommand` instead of calling `EmployeeService`, `SiteService`, or `DepartmentService` directly
- platform desktop API DTOs and commands now live in split files under `src/api/desktop/platform/models/{common,organization,runtime,site,department,employee,document,party,user}.py`
- focused `src/api/desktop/platform/{document,party,user}.py` adapters now own the admin document, party, and user desktop contracts
- the legacy QWidget Documents screen now consumes `PlatformDocumentDesktopApi` plus document/document-structure/link command DTOs instead of calling `DocumentService` directly
- the legacy QWidget Parties screen now consumes `PlatformPartyDesktopApi`, `PartyCreateCommand`, and `PartyUpdateCommand` instead of calling `PartyService` directly
- the legacy QWidget Users screen now consumes `PlatformUserDesktopApi`, `UserCreateCommand`, `UserUpdateCommand`, and `UserPasswordResetCommand` instead of calling `AuthService` directly
- focused `src/api/desktop/platform/{access,approval,audit}.py` adapters plus split `src/api/desktop/platform/models/{access,approval,audit}.py` files now own the platform access-control, approval-queue, and audit desktop contracts
- `PlatformUserDesktopApi` now also owns unlock-user and revoke-user-sessions actions so the Security workspace stays on the user desktop API boundary
- the legacy QWidget Access and Security screens now consume `PlatformAccessDesktopApi`, `PlatformUserDesktopApi`, and shell-provided scope loaders instead of calling `AccessControlService`, `AuthService`, or `ProjectService` directly
- the legacy QWidget Approvals screen now consumes `PlatformApprovalDesktopApi` instead of calling `ApprovalService` directly
- the legacy QWidget Audit screen now consumes `PlatformAuditDesktopApi`; audit label/detail resolution moved into the desktop API so the widget no longer calls `AuditService`, `ProjectService`, `TaskService`, `ResourceService`, `CostService`, or `BaselineService` directly
- the document structure manager, document preview flow, and linked-record dialog now stay on the document desktop API boundary
- `tests/test_platform_persistence_structure.py` verifies platform persistence now matches the module structure with only `persistence/{mappers,orm,repositories}/`
- `src/ui/shell/app.py` now exposes the desktop API registry and platform runtime desktop adapter in the desktop service map
- `src/ui/shell/app.py` and shell workspace context now expose separate site, department, employee, access, approval, audit, document, party, and user platform desktop adapters in the desktop service map
- the PM governance tab now wraps its governed-change queue with `PlatformApprovalDesktopApi` before handing it to the shared approval queue component, keeping the shared queue on the same contract
- targeted desktop adapter tests were added for platform runtime flows
- targeted desktop adapter tests were added for platform document, party, and user flows
- `tests/test_qml_architecture_guardrails.py` now prevents Platform Home, Module Licensing, Organizations, Sites, Departments, Employees, Documents, Parties, and Users from drifting back to direct platform service access
- `src/ui_qml/shell/context.py` and `src/ui_qml/shell/navigation.py` now expose QML-safe route-source metadata, and `src/ui_qml/shell/qml/MainWindow.qml` now hosts the selected registered workspace through a `Loader`
- `shell.home` now points at `src/ui_qml/shell/qml/HomeWorkspace.qml` so the routed shell no longer recursively loads `MainWindow.qml`
- `src/ui_qml/platform/context.py` now composes grouped admin/control/settings overview maps from split platform desktop APIs, backed by `src/ui_qml/platform/presenters/{admin_presenter,control_presenter,settings_presenter}.py`, `src/ui_qml/platform/view_models/workspace.py`, and `src/ui_qml/platform/qml/Platform/Widgets/OverviewSectionCard.qml`
- `src/ui_qml/platform/presenters/{control_queue_presenter,settings_catalog_presenter}.py` now provide the first real control/settings QML workflow presenters for approval actions, audit feeds, and module-entitlement toggles
- `src/ui_qml/platform/context.py` now exposes QML-safe `approvalQueue()`, `auditFeed()`, `moduleEntitlements()`, `organizationProfiles()`, `approveRequest()`, `rejectRequest()`, `toggleModuleLicensed()`, and `toggleModuleEnabled()` methods
- `src/ui_qml/platform/qml/workspaces/control/ControlWorkspace.qml` now renders a real approval queue and audit feed, and `src/ui_qml/platform/qml/workspaces/settings/SettingsWorkspace.qml` now renders real module-entitlement and organization-profile surfaces
- `src/ui_qml/platform/qml/Platform/Widgets/RecordListCard.qml` now provides reusable action-list rendering for migrated platform QML workflows
- `src/ui_qml/platform/presenters/{user_catalog_presenter,party_catalog_presenter,document_catalog_presenter}.py` now extend the same split admin-workflow pattern to users, parties, and documents
- `src/ui_qml/platform/qml/workspaces/admin/AdminWorkspace.qml` now renders real organization/site/department/employee/user/party/document QML surfaces, and `src/ui_qml/platform/qml/Platform/Dialogs/{UserEditorDialog,PartyEditorDialog,DocumentEditorDialog}.qml` provide the new editor dialogs for that slice
- `src/ui_qml/platform/controllers/admin/access_workspace_controller.py`, `src/ui_qml/platform/presenters/access_workspace_presenter.py`, and `src/ui_qml/platform/qml/Platform/Widgets/AccessSecurityPanel.qml` now move scoped access and account-security workflows onto the QML side through a separate controller-owned state surface
- `src/ui_qml/platform/qml/Platform/Dialogs/{ApprovalDecisionDialog,ModuleLifecycleDialog}.qml` now provide QML-side decision-note and lifecycle selection flows, and `RecordListCard.qml` now exposes a tertiary action slot so those workflows do not force page-specific list widgets
- `src/ui_qml/platform/qml/workspaces/control/ControlWorkspace.qml` now routes approve/reject through `approveRequestWithNote()` and `rejectRequestWithNote()`, while `src/ui_qml/platform/qml/workspaces/settings/SettingsWorkspace.qml` now routes lifecycle changes through `changeModuleLifecycleStatus()`
- `src/ui_qml/platform/qml/Platform/Controllers/{qmldir,plugins.qmltypes}` plus `src/ui_qml/platform/qml_type_registration.py` now provide typed runtime/tooling registration for `PlatformWorkspaceCatalog`, `PlatformAdminWorkspaceController`, `PlatformAdminAccessWorkspaceController`, `PlatformControlWorkspaceController`, and `PlatformSettingsWorkspaceController`, and the active platform QML files no longer declare controller properties as generic `QtObject`
- `src/ui_qml/platform/presenters/document_management_presenter.py`, `src/ui_qml/platform/controllers/admin/{admin_console_controller.py,document_controller.py,document_structure_controller.py}`, and `src/ui_qml/platform/qml/workspaces/admin/AdminWorkspace.qml` now move document preview-state, linked-record, and structure-management workflows onto the QML side with controller-owned refresh and mutation orchestration
- `src/ui_qml/platform/qml/Platform/Widgets/DocumentDetailPanel.qml` plus `src/ui_qml/platform/qml/Platform/Dialogs/{DocumentLinkEditorDialog,DocumentStructureEditorDialog}.qml` now replace the missing advanced document-admin QML surface without putting workflow logic back into QML
- `src/api/desktop/platform/support.py`, `src/ui_qml/platform/controllers/admin/support_workspace_controller.py`, `src/ui_qml/platform/presenters/support_workspace_presenter.py`, and `src/ui_qml/platform/qml/workspaces/admin/AdminSupportSection.qml` now move the core support workflow onto the QML side through a split typed controller instead of bloating `PlatformAdminWorkspaceController`
- the migrated QML support slice now covers update settings persistence, manifest checks, Windows installer handoff, save-file diagnostics export, incident package creation, incident-trace copying, support-folder opening, and incident-scoped support activity feeds through `PlatformSupportDesktopApi`
- keep `src/ui/platform/workspaces/admin/support/*` in place for now because the legacy QWidget platform shell is still present even though the support workflow now has QML parity; do not delete those Widget files yet
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
- modules now live under `src/core/platform/modules/`:
  - `domain/module_definition.py`
  - `domain/module_entitlement.py`
  - `domain/subscription.py`
  - `domain/defaults.py`
  - `domain/module_codes.py`
  - `application/module_catalog_service.py`
  - `application/module_catalog_context.py`
  - `application/module_catalog_mutation.py`
  - `application/module_catalog_query.py`
  - `application/authorization.py`
  - `application/guard.py`
  - `contracts.py`
- placeholder module target files were removed from `src/core/platform/modules/`
- entitlement runtime, composition, runtime access helpers, import/export/report runtime, persistence, UI, tests, and module guards now use `src.core.platform.modules`
- the old `core/platform/modules/` source package was deleted after direct import rewrites
- org now lives under `src/core/platform/org/`:
  - `domain/organization.py`
  - `domain/site.py`
  - `domain/department.py`
  - `domain/employee.py`
  - `application/organization_service.py`
  - `application/site_service.py`
  - `application/department_service.py`
  - `application/employee_service.py`
  - `application/employee_support.py`
  - `contracts.py`
  - `support.py`
  - `access_policy.py`
- placeholder org target files were removed from `src/core/platform/org/`
- org-specific repository contracts moved out of `core/platform/common/interfaces.py` into `src/core/platform/org/contracts.py`
- composition, persistence, platform services, module services, UI, tests, and test path rewrites now use `src.core.platform.org`
- the old `core/platform/org/` source package was deleted after direct import rewrites
- party now lives under `src/core/platform/party/`:
  - `domain/party.py`
  - `application/party_service.py`
  - `contracts.py`
- placeholder party target files were removed from `src/core/platform/party/`
- composition, persistence, platform services, inventory/maintenance services, UI, tests, and test path rewrites now use `src.core.platform.party`
- the old `core/platform/party/` source package was deleted after direct import rewrites
- approval now lives under `src/core/platform/approval/`:
  - `domain/approval_request.py`
  - `domain/approval_state.py`
  - `application/approval_service.py`
  - `contracts.py`
  - `policy.py`
- placeholder approval target files were removed from `src/core/platform/approval/`
- the approval repository contract moved out of `core/platform/common/interfaces.py` into `src/core/platform/approval/contracts.py`
- composition, persistence, governance UI, PM governance helpers, inventory procurement approval flows, tests, and test path rewrites now use `src.core.platform.approval`
- the old `core/platform/approval/` source package was deleted after direct import rewrites
- documents now live under `src/core/platform/documents/`:
  - `domain/document.py`
  - `domain/document_link.py`
  - `domain/document_structure.py`
  - `application/document_service.py`
  - `application/document_integration_service.py`
  - `contracts.py`
  - `support.py`
- placeholder document target files were removed from `src/core/platform/documents/`
- composition, persistence, PM collaboration, inventory item master, maintenance document services, admin document UI, tests, and test path rewrites now use `src.core.platform.documents`
- the old `core/platform/documents/` source package was deleted after direct import rewrites
- notifications now live under `src/core/platform/notifications/` as the real event hub:
  - `domain_events.py`
  - `signal.py`
- placeholder notification target files were removed from `src/core/platform/notifications/`
- platform services, module services, shell/UI listeners, tests, and test path rewrites now use `src.core.platform.notifications.domain_events` and `src.core.platform.notifications.signal`
- the old `core/platform/notifications/` source package was deleted after direct import rewrites
- audit now lives under `src/core/platform/audit/`:
  - `domain/audit_entry.py`
  - `application/audit_service.py`
  - `contracts.py`
  - `helpers.py`
- placeholder audit target files were removed from `src/core/platform/audit/`
- the audit repository contract moved out of `core/platform/common/interfaces.py` into `src/core/platform/audit/contracts.py`
- composition, persistence, platform services, PM/inventory/maintenance services, UI, tests, and test path rewrites now use `src.core.platform.audit`
- the old `core/platform/audit/` source package was deleted after direct import rewrites
- common now lives under `src/core/platform/common/`:
  - `exceptions.py`
  - `ids.py`
  - `interfaces.py`
  - `runtime_access.py`
  - `service_base.py`
- platform packages, modules, UI, tests, `main.py`, and test path rewrites now use `src.core.platform.common`
- the old `core/platform/common/` source package was deleted after direct import rewrites
- data exchange now lives under `src/core/platform/data_exchange/`:
  - `service.py`
  - `__init__.py`
- composition, tests, and test path rewrites now use `src.core.platform.data_exchange`
- the old `core/platform/data_exchange/` source package was deleted after direct import rewrites
- settings UI now lives under `src/ui/platform/settings/`:
  - `__init__.py`
  - `main_window_store.py`
- shell, PM UI, support UI, tests, and test path rewrites now use `src.ui.platform.settings`
- the old `ui/platform/settings/` source package was deleted after direct import rewrites
- shared UI now lives under `src/ui/shared/`:
  - dialogs:
    - `async_job.py`
    - `incident_support.py`
    - `login_dialog.py`
  - formatting:
    - `formatting.py`
    - `style_utils.py`
    - `theme.py`
    - `theme_refresh.py`
    - `theme_stylesheet.py`
    - `theme_tokens.py`
    - `ui_config.py`
  - models:
    - `deferred_call.py`
    - `table_model.py`
    - `undo.py`
    - `worker_services.py`
  - widgets:
    - `code_generation.py`
    - `combo.py`
    - `guards.py`
- shell, platform admin/control, PM UI, inventory UI, maintenance UI, tests, and test path rewrites now use `src.ui.shared.*`
- the old `ui/platform/shared/` source package was deleted after direct import rewrites
- control workspaces now live under `src/ui/platform/workspaces/control/`:
  - approvals:
    - `presentation.py`
    - `queue.py`
    - `tab.py`
  - audit:
    - `tab.py`
- shell workspace registration, governance UI, procurement tests, user-admin tests, and test path rewrites now use `src.ui.platform.workspaces.control.*`
- the old `ui/platform/control/` source package was deleted after direct import rewrites
- admin UI now lives under the target `src/ui/platform/*` groupings:
  - workspaces:
    - `src/ui/platform/workspaces/admin/access/tab.py`
    - `src/ui/platform/workspaces/admin/departments/tab.py`
    - `src/ui/platform/workspaces/admin/documents/tab.py`
    - `src/ui/platform/workspaces/admin/employees/tab.py`
    - `src/ui/platform/workspaces/admin/modules/tab.py`
    - `src/ui/platform/workspaces/admin/organizations/tab.py`
    - `src/ui/platform/workspaces/admin/parties/tab.py`
    - `src/ui/platform/workspaces/admin/sites/tab.py`
    - `src/ui/platform/workspaces/admin/support/*.py`
    - `src/ui/platform/workspaces/admin/users/tab.py`
  - dialogs:
    - `src/ui/platform/dialogs/admin/departments/dialogs.py`
    - `src/ui/platform/dialogs/admin/documents/dialogs.py`
    - `src/ui/platform/dialogs/admin/documents/structure_dialogs.py`
    - `src/ui/platform/dialogs/admin/employees/dialogs.py`
    - `src/ui/platform/dialogs/admin/organizations/dialogs.py`
    - `src/ui/platform/dialogs/admin/parties/dialogs.py`
    - `src/ui/platform/dialogs/admin/sites/dialogs.py`
    - `src/ui/platform/dialogs/admin/users/dialogs.py`
    - `src/ui/platform/dialogs/documents/viewer_dialogs.py`
  - widgets:
    - `src/ui/platform/widgets/admin_header.py`
    - `src/ui/platform/widgets/admin_surface.py`
    - `src/ui/platform/widgets/document_preview.py`
- shell workspace registration, maintenance document previews/viewers, admin tests, architecture guardrails, and test path rewrites now use `src.ui.platform.workspaces.admin.*`, `src.ui.platform.dialogs.*`, and `src.ui.platform.widgets.*`
- the old `ui/platform/admin/` source package was deleted after direct import rewrites
- PM-owned ORM rows were moved into the temporary Slice 1 de-mixing home `src/infra/persistence/orm/project_management/models.py`; the first Slice 2 persistence cleanup moved them into `src/core/modules/project_management/infrastructure/persistence/orm/` and removed the global PM ORM package:
  - `ProjectORM`
  - `TaskORM`
  - `ResourceORM`
  - `ProjectResourceORM`
  - `TaskAssignmentORM`
  - `TaskDependencyORM`
  - `CostItemORM`
  - `CalendarEventORM`
  - `WorkingCalendarORM`
  - `HolidayORM`
  - `ProjectBaselineORM`
  - `BaselineTaskORM`
  - `RegisterEntryORM`
  - `TaskCommentORM`
  - `TaskPresenceORM`
  - `PortfolioScoringTemplateORM`
  - `PortfolioIntakeItemORM`
  - `PortfolioScenarioORM`
  - `PortfolioProjectDependencyORM`
- PM persistence adapters and collaboration storage were first rewired to the temporary `src.infra.persistence.orm.project_management.models` path; they now import split feature ORM files under `src.core.modules.project_management.infrastructure.persistence.orm.*`
- inventory persistence adapters now import `src.infra.persistence.orm.inventory_procurement.models` directly instead of pulling inventory rows through `src.infra.persistence.orm.platform.models`
- `src/infra/persistence/orm/__init__.py` now loads all current ORM packages directly for metadata registration, and `src/infra/persistence/migrations/env.py` imports the ORM package root instead of the old platform model barrel; this loader must be adjusted as module ORM rows move to module-local infrastructure
- the stale `core/__init__.py` UI bootstrap side effect was removed so `src.infra.composition.app_container` imports cleanly in a fresh process again

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
  - direct import of `src.core.platform.modules.ModuleCatalogService`, `ModuleEntitlementRepository`, `ModuleEntitlementRecord`, `SupportsModuleEntitlements`, `EnterpriseModule`, `ModuleEntitlement`, and `PlatformCapability`
  - direct import of `src.core.platform.org.DepartmentService`, `EmployeeService`, `OrganizationService`, `SiteService`, `DepartmentRepository`, `EmployeeRepository`, `OrganizationRepository`, `SiteRepository`, `Department`, `Employee`, `EmploymentType`, `Organization`, and `Site`
  - direct import of `src.core.platform.party.Party`, `PartyRepository`, `PartyService`, and `PartyType`
  - direct import of `src.core.platform.approval.ApprovalRequest`, `ApprovalRepository`, `ApprovalService`, `ApprovalStatus`, `DEFAULT_GOVERNED_ACTIONS`, and `is_governance_required`
  - direct import of `src.core.platform.documents.Document`, `DocumentIntegrationService`, `DocumentLinkRepository`, `DocumentRepository`, `DocumentService`, `DocumentStorageKind`, `DocumentStructure`, `DocumentStructureRepository`, and `DocumentType`
  - direct import of `src.core.platform.notifications.DomainChangeEvent`, `DomainEvents`, `Signal`, and `domain_events`
  - direct import of `src.core.platform.audit.AuditLogEntry`, `AuditLogRepository`, `AuditService`, and `record_audit`
  - direct import of `src.core.platform.common.BusinessRuleError`, `ServiceBase`, `generate_id`, `src.core.platform.common.interfaces.TimeEntryRepository`, `src.core.platform.common.runtime_access.enforce_runtime_access`, `src.core.platform.data_exchange.MasterDataExchangeService`, and `MasterDataExportRequest`
  - direct import of `src.ui.platform.settings.MainWindowSettingsStore`
  - direct import of `src.ui.shared.dialogs.LoginDialog`, `start_async_job`, `src.ui.shared.formatting.UIConfig`, `apply_app_style`, `src.ui.shared.models.UndoStack`, and `src.ui.shared.widgets.CodeFieldWidget`
- direct import of `src.ui.platform.workspaces.control.ApprovalControlTab`, `ApprovalQueuePanel`, `AuditLogTab`, `approval_display_label`, and `approval_context_label`
- direct import of `src.ui.platform.workspaces.admin.AccessTab`, `DepartmentAdminTab`, `DocumentAdminTab`, `EmployeeAdminTab`, `ModuleLicensingTab`, `OrganizationAdminTab`, `PartyAdminTab`, `SiteAdminTab`, `SupportTab`, and `UserAdminTab`
  - direct import of `src.ui.platform.dialogs.DocumentLinksDialog`, `DocumentPreviewDialog`, `DocumentEditDialog`, `OrganizationEditDialog`, `PasswordResetDialog`, `UserCreateDialog`, and `UserEditDialog`
  - direct import of `src.ui.platform.widgets.build_admin_header`, `build_admin_table`, `DocumentPreviewWidget`, and `build_document_preview_state`
  - direct import of `src.infra.persistence.orm.Base`, PM split ORM files for project/task/resource/baseline/collaboration/portfolio, `src.infra.persistence.orm.inventory_procurement.models.InventoryItemCategoryORM`, `PurchaseOrderORM`, `StockItemORM`, and `src.core.platform.infrastructure.persistence.orm.models.TimeEntryORM`, `TimesheetPeriodORM`, `UserORM`, `OrganizationORM`
  - direct metadata smoke import confirms `src.core.platform.infrastructure.persistence.orm.models.TimeEntryORM`, `TimesheetPeriodORM`, `UserORM`, `OrganizationORM`, `AuditLogORM`, and `RuntimeExecutionORM` remain registered in `Base.metadata`
  - direct import of `src.infra.composition.app_container.build_service_dict`
  - direct import of `src.infra.platform.path`, `resource`, `version`, `update`, `updater`, `diagnostics`, and `operational_support`; `resource_path("assets/icons/app.ico")` resolves to the project-root asset path
- `python -m compileall -q src/ui_qml tests/test_qml_shell_migration.py tests/test_qml_platform_presenters.py tests/test_qml_platform_routes.py tests/test_qml_offscreen_loading.py tests/test_qml_migration_scaffold.py`
- `pytest tests/test_qml_shell_migration.py tests/test_qml_shared_primitives.py tests/test_qml_project_management_routes.py tests/test_qml_project_management_presenters.py tests/test_qml_platform_routes.py tests/test_qml_platform_presenters.py tests/test_qml_offscreen_loading.py tests/test_qml_migration_scaffold.py tests/test_qml_architecture_guardrails.py -q`
  - observed result after the QML shell/platform overview checkpoint: 47 passed
- `pytest tests/test_main_window_shell_navigation.py -q`
  - observed result after the QML shell/platform overview checkpoint: 7 passed
- `python -m compileall -q src/ui_qml tests/test_qml_platform_presenters.py tests/test_qml_platform_routes.py tests/test_qml_offscreen_loading.py tests/test_qml_shell_migration.py tests/test_qml_migration_scaffold.py`
- `pytest tests/test_qml_platform_presenters.py tests/test_qml_platform_routes.py tests/test_qml_offscreen_loading.py tests/test_qml_shell_migration.py tests/test_qml_migration_scaffold.py tests/test_qml_architecture_guardrails.py -q`
  - observed result after the control/settings workflow checkpoint: 38 passed
- `pytest tests/test_qml_shell_migration.py tests/test_qml_shared_primitives.py tests/test_qml_project_management_routes.py tests/test_qml_project_management_presenters.py tests/test_qml_platform_routes.py tests/test_qml_platform_presenters.py tests/test_qml_offscreen_loading.py tests/test_qml_migration_scaffold.py tests/test_qml_architecture_guardrails.py -q`
  - observed result after the control/settings workflow checkpoint: 49 passed
- `pytest tests/test_main_window_shell_navigation.py -q`
  - observed result after the control/settings workflow checkpoint: 7 passed
- `python -m compileall -q src/ui_qml src/api/desktop tests/test_platform_support_desktop_api.py tests/test_qml_platform_presenters.py tests/test_qml_architecture_guardrails.py tests/test_qml_offscreen_loading.py`
- `pytest tests/test_platform_support_desktop_api.py tests/test_qml_platform_presenters.py tests/test_qml_architecture_guardrails.py tests/test_qml_offscreen_loading.py tests/test_platform_admin_desktop_api.py -q`
  - observed result after the extended platform support QML checkpoint: 46 passed
- `pytest tests/test_operational_support.py tests/test_support_productization.py tests/test_updater.py tests/test_version.py tests/test_ui_settings_persistence.py tests/test_main_window_shell_navigation.py -q`
  - observed result after the extended platform support QML checkpoint: 26 passed
- full `qmllint` scan across `src/ui_qml/**/*.qml`
  - observed result after the extended platform support QML checkpoint: clean
- `pytest tests/test_platform_runtime_desktop_api.py tests/test_platform_runtime_http_api.py -q`
- `pytest tests/test_platform_control_desktop_api.py tests/test_phase_b_user_admin_ui.py tests/test_enterprise_pm_foundation.py tests/test_enterprise_rbac_matrix.py tests/test_qml_architecture_guardrails.py -q`
- `pytest tests/test_platform_admin_desktop_api.py tests/test_platform_control_desktop_api.py tests/test_platform_org_desktop_api.py tests/test_platform_runtime_desktop_api.py tests/test_document_admin_ui.py tests/test_phase_b_user_admin_ui.py tests/test_main_window_shell_navigation.py tests/test_qml_architecture_guardrails.py tests/test_architecture_guardrails.py -q`
  - `pytest tests/test_operational_support.py tests/test_support_productization.py tests/test_updater.py tests/test_version.py tests/test_ui_settings_persistence.py tests/test_main_window_shell_navigation.py tests/test_architecture_guardrails.py::test_legacy_infra_platform_runtime_package_is_removed -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_db_facades_are_removed tests/test_architecture_guardrails.py::test_composition_imports_focused_persistence_adapters -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_db_facades_are_removed tests/test_architecture_guardrails.py::test_composition_imports_focused_persistence_adapters tests/test_platform_runtime_http_api.py tests/test_platform_runtime_desktop_api.py -q`
  - `pytest tests/test_platform_import_export_report_runtime.py tests/test_runtime_execution_tracking.py tests/test_maintenance_runtime_contracts.py -q`
  - `pytest tests/test_platform_import_export_report_runtime.py tests/test_runtime_execution_tracking.py tests/test_maintenance_runtime_contracts.py tests/test_architecture_guardrails.py::test_legacy_platform_import_export_packages_are_removed -q`
  - `pytest tests/test_shared_collaboration_import_and_timesheets.py tests/test_service_architecture.py tests/test_architecture_guardrails.py::test_legacy_platform_time_package_is_removed -q`
  - `pytest tests/test_auth_module_phase_a.py tests/test_auth_validation_and_query.py tests/test_authorization_engine.py tests/test_passwords.py tests/test_phase_b_session_permissions.py -q`
  - `pytest tests/test_service_architecture.py tests/test_platform_access_scopes.py tests/test_architecture_guardrails.py::test_legacy_platform_auth_package_is_removed tests/test_architecture_guardrails.py::test_auth_service_is_orchestrator_only -q`
  - `pytest tests/test_authorization_engine.py tests/test_platform_access_scopes.py tests/test_auth_module_phase_a.py tests/test_architecture_guardrails.py::test_legacy_platform_authorization_package_is_removed -q`
  - `pytest tests/test_auth_module_phase_a.py tests/test_authorization_engine.py tests/test_platform_access_scopes.py tests/test_service_architecture.py tests/test_architecture_guardrails.py::test_legacy_platform_access_package_is_removed tests/test_architecture_guardrails.py::test_platform_common_interfaces_are_platform_only -q`
  - `pytest tests/test_enterprise_platform_catalog.py tests/test_platform_import_export_report_runtime.py tests/test_architecture_guardrails.py::test_legacy_platform_modules_package_is_removed tests/test_architecture_guardrails.py::test_module_catalog_service_is_orchestrator_only -q`
  - `pytest tests/test_service_architecture.py tests/test_phase_b_user_admin_ui.py tests/test_platform_access_scopes.py tests/test_architecture_guardrails.py::test_legacy_platform_org_package_is_removed tests/test_architecture_guardrails.py::test_org_package_exports_services_and_contracts tests/test_architecture_guardrails.py::test_platform_common_interfaces_are_platform_only -q`
  - `pytest tests/test_maintenance_foundation.py tests/test_maintenance_reliability_foundation.py tests/test_maintenance_preventive_foundation.py tests/test_maintenance_phase4_foundation.py tests/test_maintenance_execution_foundation.py tests/test_maintenance_sensor_foundation.py tests/test_maintenance_reliability_analytics.py tests/test_maintenance_integration_foundation.py -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_party_package_is_removed tests/test_architecture_guardrails.py::test_party_package_exports_service_and_contracts tests/test_service_architecture.py -q`
  - `pytest tests/test_inventory_import_export_reporting.py tests/test_inventory_maintenance_material_contracts.py tests/test_inventory_procurement_foundation.py tests/test_inventory_procurement_requisition.py tests/test_inventory_procurement_purchasing.py tests/test_inventory_procurement_scaffold.py tests/test_inventory_procurement_ui.py tests/test_maintenance_foundation.py tests/test_code_generation_ui.py -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_approval_package_is_removed tests/test_architecture_guardrails.py::test_approval_package_exports_service_and_contracts tests/test_architecture_guardrails.py::test_platform_common_interfaces_are_platform_only tests/test_service_architecture.py tests/test_governance_tab_mode_toggle_ui.py tests/test_phase_b_approval_workflow.py tests/test_phase_b_session_permissions.py tests/test_phase_b_user_admin_ui.py tests/test_phase_b_audit_log.py tests/test_domain_event_wiring.py -q`
  - `pytest tests/test_inventory_procurement_requisition.py tests/test_inventory_procurement_purchasing.py tests/test_inventory_import_export_reporting.py tests/test_inventory_procurement_ui.py -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_documents_package_is_removed tests/test_architecture_guardrails.py::test_documents_package_exports_services_and_contracts tests/test_service_architecture.py tests/test_document_admin_ui.py -q`
  - `pytest tests/test_inventory_procurement_foundation.py tests/test_inventory_procurement_ui.py tests/test_maintenance_foundation.py tests/test_shared_collaboration_import_and_timesheets.py -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_notifications_package_is_removed tests/test_architecture_guardrails.py::test_notifications_package_exports_event_hub tests/test_domain_events.py tests/test_domain_event_wiring.py -q`
  - `pytest tests/test_dashboard_leveling_flow.py tests/test_project_management_platform_alignment.py tests/test_phase2_register_import_and_ui.py tests/test_inventory_maintenance_material_contracts.py tests/test_maintenance_foundation.py tests/test_maintenance_execution_foundation.py tests/test_service_architecture.py -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_audit_package_is_removed tests/test_architecture_guardrails.py::test_audit_package_exports_service_and_contracts tests/test_architecture_guardrails.py::test_platform_common_interfaces_are_platform_only tests/test_service_architecture.py tests/test_phase_b_audit_log.py tests/test_phase_b_user_admin_ui.py tests/test_domain_event_wiring.py -q`
  - `pytest tests/test_inventory_procurement_foundation.py tests/test_inventory_procurement_ui.py tests/test_maintenance_foundation.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_phase2_register_import_and_ui.py tests/test_maintenance_execution_foundation.py -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_common_package_is_removed tests/test_architecture_guardrails.py::test_legacy_platform_data_exchange_package_is_removed tests/test_architecture_guardrails.py::test_common_package_exports_shared_utilities tests/test_architecture_guardrails.py::test_data_exchange_package_exports_service tests/test_architecture_guardrails.py::test_platform_common_interfaces_are_platform_only tests/test_architecture_guardrails.py::test_legacy_platform_settings_ui_package_is_removed tests/test_architecture_guardrails.py::test_platform_settings_package_exports_store -q`
  - `pytest tests/test_service_architecture.py tests/test_shared_master_data_exchange.py tests/test_shared_master_reuse_access.py tests/test_ui_settings_persistence.py tests/test_main_window_shell_navigation.py tests/test_governance_tab_mode_toggle_ui.py -q`
  - `pytest tests/test_shared_collaboration_import_and_timesheets.py tests/test_inventory_import_export_reporting.py tests/test_maintenance_foundation.py -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_shared_ui_package_is_removed tests/test_architecture_guardrails.py::test_shared_dialogs_package_exports_dialog_helpers tests/test_architecture_guardrails.py::test_shared_formatting_package_exports_theme_and_ui_config tests/test_architecture_guardrails.py::test_shared_models_package_exports_runtime_helpers tests/test_architecture_guardrails.py::test_shared_widgets_package_exports_widget_helpers tests/test_async_job_runtime.py tests/test_code_generation_ui.py tests/test_ui_rbac_matrix_and_guards.py -q`
  - `pytest tests/test_refactor_regressions.py tests/test_pro_set_v1_ui.py tests/test_dashboard_professional_panels.py tests/test_inventory_procurement_ui.py tests/test_main_window_shell_navigation.py tests/test_phase_b_user_admin_ui.py -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_control_ui_package_is_removed tests/test_architecture_guardrails.py::test_platform_control_workspace_package_exports_tabs tests/test_phase_b_user_admin_ui.py tests/test_inventory_procurement_purchasing.py tests/test_governance_tab_mode_toggle_ui.py -q`
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_admin_ui_package_is_removed tests/test_architecture_guardrails.py::test_platform_admin_workspace_package_exports_tabs tests/test_architecture_guardrails.py::test_platform_widgets_package_exports_admin_helpers tests/test_architecture_guardrails.py::test_platform_dialogs_package_exports_admin_and_document_dialogs tests/test_document_admin_ui.py tests/test_phase_b_user_admin_ui.py tests/test_tab_surface_consistency.py tests/test_code_generation_ui.py -q`
  - `pytest tests/test_enterprise_pm_foundation.py tests/test_enterprise_rbac_matrix.py tests/test_maintenance_foundation.py tests/test_maintenance_execution_foundation.py -q`
  - `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_architecture_guardrails.py::test_inventory_persistence_imports_inventory_orm_models tests/test_architecture_guardrails.py::test_orm_package_root_loads_all_model_packages -q`
  - `pytest tests/test_service_architecture.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_inventory_import_export_reporting.py tests/test_inventory_procurement_foundation.py tests/test_project_management_platform_alignment.py tests/test_collaboration_import_timesheet_regressions.py -q`
  - `pytest tests/test_architecture_guardrails.py::test_composition_imports_focused_persistence_adapters tests/test_architecture_guardrails.py::test_orm_package_root_loads_all_model_packages tests/test_service_architecture.py tests/test_shared_master_data_exchange.py tests/test_shared_master_reuse_access.py tests/test_auth_module_phase_a.py tests/test_phase_b_session_permissions.py tests/test_phase_b_user_admin_ui.py tests/test_phase_b_audit_log.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_runtime_execution_tracking.py -q`
  - `pytest tests/test_architecture_guardrails.py -q`
  - latest full architecture result after the Slice 2 PM risk register-domain split: 94 passed
- no Python import statements remain for `core.platform.importing` or `core.platform.exporting`
- no Python import statements remain for `core.platform.time`
- no Python import statements remain for `core.platform.auth`
- no Python import statements remain for `core.platform.authorization`
- no Python import statements remain for `core.platform.access`
- no Python import statements remain for `core.platform.modules`
- no Python import statements remain for `core.platform.org`
- no Python import statements remain for `core.platform.party`
- no Python import statements remain for `core.platform.approval`
- no Python import statements remain for `core.platform.documents`
- no Python import statements remain for `core.platform.notifications`
- no Python import statements remain for `core.platform.audit`
- no Python import statements remain for `core.platform.common`
- no Python import statements remain for `core.platform.data_exchange`
- no Python import statements remain for `ui.platform.settings`
- no Python import statements remain for `ui.platform.shared`
- no Python import statements remain for `ui.platform.control`
- no Python import statements remain for `ui.platform.admin`
- no Python runtime import statements remain for `infra.platform`
- the old top-level `infra/platform/` package path has been deleted
- no Python import statements remain for `src.infra.persistence.db.platform`
- no Python import statements remain for `src.infra.persistence.orm.platform.models`
- all planned `core/platform/*` package splits for Slice 1 are complete
- all planned platform UI regrouping for Slice 1 is complete
- all remaining mixed-ownership ORM rows are out of the platform model aggregate for Slice 1

Known blocker:

- the default interpreter outside `pmenv` still fails on `reportlab` during full app/test imports because that environment dependency is not installed there
- executing migrations also requires the declared `alembic` dependency to be installed in the active environment

Resolved:

- `conda run -n pmenv pytest tests/test_architecture_guardrails.py -q` now passes after the Slice 2 PM domain package-root cleanup removed the old duplicated task definitions from `core/modules/project_management/domain/__init__.py`
- after the PM project/application transfer, focused verification now passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py`
  - observed result: 107 passed
- after the PM task/application transfer, focused verification now passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py tests/test_dashboard_professional_panels.py tests/test_task_dependency_ux_logic.py tests/test_progress_flow.py`
  - observed result: 121 passed
- after the PM scheduling/calendar/work-calendar application transfer, focused verification now passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py tests/test_dashboard_professional_panels.py tests/test_task_dependency_ux_logic.py tests/test_progress_flow.py tests/test_cpm_flow.py tests/test_resource_leveling_workflow.py tests/test_baseline_comparison_workflow.py`
  - observed result: 133 passed
- after the PM resource/cost/finance application transfer, focused verification now passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py tests/test_dashboard_professional_panels.py tests/test_task_dependency_ux_logic.py tests/test_progress_flow.py tests/test_cpm_flow.py tests/test_resource_leveling_workflow.py tests/test_baseline_comparison_workflow.py tests/test_finance_layer_integration.py tests/test_currency_defaults.py tests/test_technical_math_reporting.py tests/test_exporters_configuration.py tests/test_ui_professional_filters.py`
  - observed result: 165 passed
- after the PM risk/register application transfer plus the PM reporting infrastructure transfer, focused verification now passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_phase2_register_import_and_ui.py tests/test_project_management_desktop_api.py tests/test_dashboard_professional_panels.py tests/test_project_management_platform_alignment.py tests/test_refactor_regressions.py tests/test_exporters_configuration.py tests/test_technical_math_reporting.py tests/test_ui_professional_filters.py`
  - observed result: 184 passed
  - `conda run -n pmenv pytest -q tests/test_platform_import_export_report_runtime.py tests/test_cost_report_ui.py tests/test_dashboard_portfolio_flow.py`
  - observed result: 15 passed
- after the PM baseline application transfer and scheduling/reporting import-cycle cleanup, focused verification now passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py tests/test_dashboard_professional_panels.py tests/test_baseline_comparison_workflow.py tests/test_exporters_configuration.py tests/test_project_management_platform_alignment.py tests/test_platform_import_export_report_runtime.py`
  - observed result: 154 passed
- after the PM dashboard application transfer, focused verification now passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py tests/test_dashboard_professional_panels.py tests/test_dashboard_portfolio_flow.py tests/test_dashboard_leveling_flow.py tests/test_project_management_platform_alignment.py tests/test_refactor_regressions.py tests/test_pro_set_v1_ui.py`
  - observed result: 177 passed

Continue next:

1. The legacy PM service-transfer set is now completed through `services/timesheet/*` and `services/import_service/*`; continue with PM API, UI, and test regrouping on top of the new module-local structure.
2. Update test path strategy and remove path rewrites only after the new paths are complete.

### Slice 2: Project Management

Hold status as of 2026-04-22:

- resume Slice 2 with repo-structure transfer as the active track; QML remains part of Slice 2 but should follow the new structure instead of blocking it
- continue PM domain/application/infrastructure/API moves first, then incorporate QML naturally on top of those slices
- completed Slice 2 persistence/contracts/domain work remains valid and must not be reverted
- active Widget UI under `src/ui/*` remains runnable during migration
- final PM desktop UI target is now `src/ui_qml/modules/project_management/*`
- old PM Widget screens are deleted only after matching QML workspaces/dialogs, presenters, view models, routes, and tests are complete
- QML shell foundation is started and independently smoke-tested; do not wire `main_qt.py` to QML yet, but do not let that foundation block the remaining structure transfer
- the platform-first QML checkpoint now has a routed shell host, grouped platform admin/control/settings overviews, a real QML approval/audit control surface, and a real QML module-entitlement/runtime-settings surface, all backed by split platform desktop APIs; full workflow parity and Widget deletion still remain pending
- PM QML route landing zones are complete with typed controller/catalog scaffolding, and `projects` plus `dashboard` have now moved beyond placeholders; keep that progress, but do not let it replace the remaining module-structure work
- PM QML presenter/view-model scaffolding is complete for the route set, and `projects` plus `dashboard` now have typed controllers plus split page sections backed by screen-specific desktop APIs; that UI progress remains valid and should not be reverted
- PM QML now binds to presenter-backed metadata through a typed `pmCatalog` and named PM controller/dialog/widget modules; outside `projects` and `dashboard`, the next source of truth should be the refactored module-local application/API structure
- real PM workflow/query desktop APIs are now in place for `dashboard` and `projects`; add the rest one migrated screen at a time
- QML architecture guardrails are in place and should stay green before any old Widget screen is deleted
- automated offscreen QML route loading is in place and should stay green before any old Widget screen is deleted
- PM Dashboard QML now has API-backed read-only project selection, baseline selection, KPI cards, EVM/register/cost analysis panels, burndown/resource visuals, and delivery-health sections; dialogs, mutations, and deeper parity remain on the Widget dashboard until parity is completed
- PM Projects QML now has API-backed filters, catalog/detail sections, and create/edit/status/delete dialogs; import flows, resource-assignment side panels, and deeper parity remain on the Widget projects workspace until parity is completed

Refactor-first priority for the remaining PM slice:

- move the remaining legacy PM service packages under `core/modules/project_management/services/*` into their module-local homes under `src/core/modules/project_management/{application,infrastructure}/*`, while keeping completed `projects`, `tasks`, `scheduling`, `baseline`, `dashboard`, `resources`, `financials`, `risk`, and `reporting` transfers clean and facade-free
- keep dashboard/reporting reads infrastructure-owned on `src/core/modules/project_management/infrastructure/reporting/*` and keep the new PM service boundaries stable while API and UI regrouping continues
- expand module-local PM desktop and HTTP APIs over those application handlers, not over the broad legacy service layer
- regroup PM tests under `src/tests/project_management/*`
- keep QML migration attached to those refactored module-local APIs instead of using it to drive slice ordering

Do:

1. Split PM domain by `projects`, `tasks`, `scheduling`, `resources`, `risk`, and `financials`.
2. Extract PM repository contracts from broad interfaces; create gateway contracts only when real gateway boundaries appear.
3. Break scheduling engine into graph builder, forward pass, backward pass, critical path, calendars, and baseline comparison.
4. Convert broad PM services into command/query handlers.
5. Move PM repositories, read models, and ORM rows under module infrastructure.
6. Add PM desktop API adapters.
7. Add PM QML workspaces/dialogs/widgets under `src/ui_qml/modules/project_management/qml/*`.
8. Add PM QML presenters and view models under `src/ui_qml/modules/project_management/{presenters,view_models}/`.
9. Rewrite imports/navigation and delete old PM Widget paths only after the migrated QML screen passes tests.

Status as of 2026-04-19:

Completed:

- moved `core/modules/project_management/services/project/service.py` into `src/core/modules/project_management/application/projects/service.py`
- moved `core/modules/project_management/services/project/lifecycle.py` into `src/core/modules/project_management/application/projects/commands/lifecycle.py`
- moved `core/modules/project_management/services/project/validation.py` into `src/core/modules/project_management/application/projects/commands/validation.py`
- moved `core/modules/project_management/services/project/query.py` into `src/core/modules/project_management/application/projects/queries/project_query.py`
- moved `core/modules/project_management/services/project/resource_service.py` into `src/core/modules/project_management/application/resources/project_resource_service.py`, split across `commands/project_resource_commands.py` and `queries/project_resource_queries.py`
- rewired PM composition, PM desktop APIs, dashboard/import helpers, legacy PM Widget callers, path rewrites, and architecture tests to the new `src.core.modules.project_management.application.{projects,resources}` imports
- deleted the old source files under `core/modules/project_management/services/project/` after callers were rewritten, with no facade re-export package kept behind
- moved `core/modules/project_management/services/task/service.py` into `src/core/modules/project_management/application/tasks/service.py`
- moved `core/modules/project_management/services/task/lifecycle.py`, `assignment.py`, `assignment_audit.py`, `assignment_bridge.py`, `dependency.py`, `schedule_sync.py`, `time_entries.py`, and `validation.py` into `src/core/modules/project_management/application/tasks/commands/*`
- moved `core/modules/project_management/services/task/query.py` and `dependency_diagnostics.py` into `src/core/modules/project_management/application/tasks/queries/*`
- rewired PM composition, PM desktop/platform APIs, dashboard/import helpers, PM Widget callers, dependency-impact UI imports, path rewrites, and architecture tests to the new `src.core.modules.project_management.application.tasks` imports
- deleted the old source files under `core/modules/project_management/services/task/` after callers were rewritten, with no facade re-export package kept behind
- moved `core/modules/project_management/services/scheduling/date_compute.py`, `engine.py`, `graph.py`, `leveling.py`, `leveling_models.py`, `leveling_service.py`, `models.py`, `passes.py`, and `results.py` into `src/core/modules/project_management/application/scheduling/*`
- moved `core/modules/project_management/services/calendar/service.py` into `src/core/modules/project_management/application/scheduling/calendar_service.py`
- moved `core/modules/project_management/services/work_calendar/engine.py` and `service.py` into `src/core/modules/project_management/application/scheduling/work_calendar_{engine,service}.py`
- rewired PM composition, baseline/reporting/dashboard services, PM calendar/dashboard Widget callers, path rewrites, and architecture tests to the new `src.core.modules.project_management.application.scheduling` imports
- deleted the old source files and legacy package roots under `core/modules/project_management/services/{scheduling,calendar,work_calendar}/` after callers were rewritten, with no facade re-export package kept behind
- moved `core/modules/project_management/services/resource/service.py` into `src/core/modules/project_management/application/resources/resource_service.py` and split the live workflow into `commands/resource_commands.py` plus `queries/resource_queries.py`
- moved `core/modules/project_management/services/cost/service.py` into `src/core/modules/project_management/application/financials/cost_service.py`, with `lifecycle.py`, `query.py`, and `support.py` landing in `commands/cost_lifecycle.py`, `queries/cost_query.py`, and `cost_support.py`
- moved `core/modules/project_management/services/finance/{service,analytics,cashflow,helpers,ledger,models,policy}.py` into `src/core/modules/project_management/application/financials/*`
- rewired PM composition, import support, reporting/export surfaces, platform desktop audit support, PM calendar/cost/resource/report/task/project Widget callers, path rewrites, and architecture tests to import `ResourceService`, `CostService`, `FinanceService`, and finance models from `src.core.modules.project_management.application.{resources,financials}`
- deleted the old source files and legacy package roots under `core/modules/project_management/services/{resource,cost,finance}/` after callers were rewritten, with no facade re-export package kept behind
- moved `core/modules/project_management/services/register/service.py` into `src/core/modules/project_management/application/risk/register_service.py`, with `lifecycle.py`, `query.py`, and `models.py` landing in `commands/register_lifecycle.py`, `queries/register_query.py`, and `dto/register_summary.py`
- rewired PM composition, dashboard services, PM desktop dashboard APIs, PM register Widget callers, path rewrites, and architecture tests to import `RegisterService` and register summary DTOs from `src.core.modules.project_management.application.risk`
- deleted the old source files and legacy package root under `core/modules/project_management/services/register/` after callers were rewritten, with no facade re-export package kept behind
- moved `core/modules/project_management/services/reporting/{baseline_compare,cost_breakdown,cost_policy,evm,evm_core,evm_series,kpi,labor,models,service,variance}.py` into `src/core/modules/project_management/infrastructure/reporting/*`
- rewired PM composition, financial services, reporting/export adapters, dashboard services, PM cost/project/report Widget callers, dashboard alert rendering, path rewrites, and architecture tests to import reporting services and models from `src.core.modules.project_management.infrastructure.reporting`
- deleted the old source files and legacy package root under `core/modules/project_management/services/reporting/` after callers were rewritten, with no facade re-export package kept behind
- moved `core/modules/project_management/services/baseline/service.py` into `src/core/modules/project_management/application/scheduling/baseline_service.py`
- rewired PM composition, PM desktop APIs, platform audit support, dashboard Widget callers, path rewrites, and architecture tests to import `BaselineService` from the new scheduling module-local path
- flattened scheduling imports inside the reporting infrastructure onto concrete scheduling modules so the scheduling/reporting import graph stays acyclic after the baseline transfer
- deleted the old source file and legacy package root under `core/modules/project_management/services/baseline/` after callers were rewritten, with no facade re-export package kept behind
- moved `core/modules/project_management/services/dashboard/{service,alerts,upcoming,burndown,evm,register,portfolio,professional,models,portfolio_models}.py` into `src/core/modules/project_management/application/dashboard/*`
- rewired PM composition, desktop runtime/dashboard APIs, dashboard Widget callers, dashboard desktop snapshot builders, path rewrites, and architecture tests to import `DashboardService`, `DashboardData`, and `PORTFOLIO_SCOPE_ID` from `src.core.modules.project_management.application.dashboard`
- deleted the old source files and legacy package root under `core/modules/project_management/services/dashboard/` after callers were rewritten, with no facade re-export package kept behind
- moved `core/modules/project_management/services/collaboration/{service,comments,documents,inbox,mentions,notifications,presence,principal,support}.py` into `src/core/modules/project_management/application/tasks/{collaboration_service.py,collaboration_mentions.py,collaboration_principal.py,collaboration_support.py,commands/*,queries/*}`
- rewired PM composition, PM task/collaboration Widget callers, path rewrites, and architecture/service tests to import `CollaborationService` from `src.core.modules.project_management.application.tasks`
- deleted the old source files and legacy package root under `core/modules/project_management/services/collaboration/` after callers were rewritten, with no facade re-export package kept behind
- moved `core/modules/project_management/services/portfolio/{service,dependencies,executive,intake,scenarios,support,templates}.py` into `src/core/modules/project_management/application/projects/{portfolio_service.py,portfolio_support.py,commands/*,queries/*}`
- rewired PM composition, PM portfolio Widget callers, path rewrites, and architecture/service tests to import `PortfolioService` from `src.core.modules.project_management.application.projects`
- deleted the old source files and legacy package root under `core/modules/project_management/services/portfolio/` after callers were rewritten, with no facade re-export package kept behind
- moved the PM timesheet wrapper from `core/modules/project_management/services/timesheet/*` into `src/core/modules/project_management/application/resources/timesheet_service.py`, with shared time-entry and timesheet-period workflows remaining owned by `src.core.platform.time`
- rewired PM composition, PM task/governance/timesheet Widget callers, task application time-entry commands, path rewrites, and architecture/service tests to import `TimesheetService` from `src.core.modules.project_management.application.resources`
- deleted the old source files and legacy package root under `core/modules/project_management/services/timesheet/` after callers were rewritten, with no facade re-export package kept behind
- moved `core/modules/project_management/services/import_service/{service,execution,preview,support,models,schemas}.py` and `core/modules/project_management/importing/definitions.py` into `src/core/modules/project_management/infrastructure/importers/*`
- rewired PM composition, PM project/import Widget callers, path rewrites, and architecture/service tests to import `DataImportService` from `src.core.modules.project_management.infrastructure.importers`
- deleted the old source files and legacy package roots under `core/modules/project_management/services/import_service/` and `core/modules/project_management/importing/` after callers were rewritten, with no facade re-export package kept behind
- PM ORM rows now live under `src/core/modules/project_management/infrastructure/persistence/orm/`
- PM persistence adapters, collaboration storage, metadata loading, and architecture guardrails now import split feature ORM files under `src.core.modules.project_management.infrastructure.persistence.orm.*`
- the old `src/infra/persistence/orm/project_management/` global module ORM package was deleted after direct import rewrites
- the PM ORM monolith `src/core/modules/project_management/infrastructure/persistence/orm/models.py` was split into `project.py`, `resource.py`, `task.py`, `cost_calendar.py`, `baseline.py`, `register.py`, `collaboration.py`, and `portfolio.py`
- PM repository implementations now live under `src/core/modules/project_management/infrastructure/persistence/repositories/`
- PM mapper implementations now live under `src/core/modules/project_management/infrastructure/persistence/mappers/`
- composition, PM persistence internals, test path rewrites, refactor regressions, and architecture guardrails now use the new PM infrastructure imports
- the old `infra/modules/project_management/db/` package was deleted after direct import rewrites
- old PM timesheet/task-timesheet bridge files were removed instead of carried forward as facades; platform time persistence remains under `src/core/platform/infrastructure/persistence/time/`
- PM repository contracts now live under `src/core/modules/project_management/contracts/repositories/` as `project.py`, `task.py`, `resource.py`, `cost_calendar.py`, `baseline.py`, `register.py`, `collaboration.py`, and `portfolio.py`
- PM services and PM persistence adapters now import the specific repository contract modules directly
- the old `core/modules/project_management/interfaces.py` file was deleted after direct import rewrites
- `contracts/gateways/` remains empty for this pass because the deleted PM interfaces file contained repository contracts only
- `Project` and `ProjectResource` now live in `src/core/modules/project_management/domain/projects/project.py`
- PM services, PM persistence, repository contracts, and UI callers now import the project domain model from the new subdomain file directly
- the old flat `core/modules/project_management/domain/project.py` file was deleted after direct import rewrites
- `core/modules/project_management/domain/__init__.py` was reduced to a package docstring because no callers import PM domain objects from the package root
- `Task`, `TaskAssignment`, and `TaskDependency` now live in `src/core/modules/project_management/domain/tasks/task.py`
- PM task, scheduling, calendar, reporting, persistence, repository contracts, UI, and focused test callers now import the task domain model from the new subdomain file directly
- the old flat `core/modules/project_management/domain/task.py` file was deleted after direct import rewrites
- obsolete PM task-domain re-exports of platform timesheet objects were removed; platform time domain objects remain owned by `src/core/platform/time/domain/`
- `Resource` now lives in `src/core/modules/project_management/domain/resources/resource.py`
- PM resource service, resource persistence, repository contracts, resource UI, task assignment UI, and labor-cost UI callers now import the resource domain model from the new subdomain file directly
- the old flat `core/modules/project_management/domain/resource.py` file was deleted after direct import rewrites
- `CostItem` now lives in `src/core/modules/project_management/domain/financials/cost.py`
- PM cost services, cost persistence, cost/calendar repository contracts, and cost UI callers now import the cost domain model from the new financials subdomain file directly
- the old flat `core/modules/project_management/domain/cost.py` file was deleted after direct import rewrites
- `CalendarEvent`, `WorkingCalendar`, and `Holiday` now live in `src/core/modules/project_management/domain/scheduling/calendar.py`
- PM calendar services, work-calendar services, cost/calendar persistence, and cost/calendar repository contracts now import the calendar domain model from the new scheduling subdomain file directly
- the old flat `core/modules/project_management/domain/calendar.py` file was deleted after direct import rewrites
- `ProjectBaseline` and `BaselineTask` now live in `src/core/modules/project_management/domain/scheduling/baseline.py`
- PM baseline service, baseline reporting, baseline persistence, and baseline repository contracts now import the baseline domain model from the new scheduling subdomain file directly
- the old flat `core/modules/project_management/domain/baseline.py` file was deleted after direct import rewrites
- `RegisterEntry`, register enums, and register enum normalizers now live in `src/core/modules/project_management/domain/risk/register.py`
- PM register services, register persistence, register ORM enum usage, register repository contracts, register UI, dashboard register rendering, and focused tests now import the register domain model from the new risk subdomain file directly
- the old flat `core/modules/project_management/domain/register.py` file was deleted after direct import rewrites
- the remaining PM module-owned access/domain/support files from `core/modules/project_management/{access,domain,services/common}/*` now live under `src/core/modules/project_management/{access,domain,application/common}/*`
- the remaining PM reporting runtime entrypoints from `core/modules/project_management/reporting/*` now live under `src/core/modules/project_management/infrastructure/reporting/*`
- the PM collaboration storage helpers from `infra/modules/project_management/{collaboration_store,collaboration_attachments}.py` now live under `src/core/modules/project_management/infrastructure/*`
- PM composition, widgets, tests, and path rewrites now point at the final module-local PM access/domain/reporting/infrastructure imports, and the accidental `src.src.*` import drift from the sweep was removed
- the final legacy PM roots `core/modules/project_management/` and `infra/modules/project_management/` were deleted after direct import rewrites, with no facade package kept behind

Verified:

- `python -m compileall -q src infra ui core tests main.py main_qt.py main_qt.spec`
- direct metadata smoke import confirms PM ORM rows load from split feature ORM files and stay registered in `Base.metadata`
- direct import smoke confirms PM repositories load from `src.core.modules.project_management.infrastructure.persistence.repositories.*`
- direct import smoke confirms PM repository contracts load from `src.core.modules.project_management.contracts.repositories.*`
- direct import smoke confirms `Project` and `ProjectResource` load from `src.core.modules.project_management.domain.projects.project`
- direct import smoke confirms `Task`, `TaskAssignment`, and `TaskDependency` load from `src.core.modules.project_management.domain.tasks.task`
- direct import smoke confirms `Resource` loads from `src.core.modules.project_management.domain.resources.resource`
- direct import smoke confirms `CostItem` loads from `src.core.modules.project_management.domain.financials.cost`
- direct import smoke confirms `CalendarEvent`, `WorkingCalendar`, and `Holiday` load from `src.core.modules.project_management.domain.scheduling.calendar`
- direct import smoke confirms `ProjectBaseline` and `BaselineTask` load from `src.core.modules.project_management.domain.scheduling.baseline`
- direct import smoke confirms `RegisterEntry`, `RegisterEntryType`, and `RegisterEntrySeverity` load from `src.core.modules.project_management.domain.risk.register`
- `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_architecture_guardrails.py::test_composition_imports_focused_persistence_adapters tests/test_architecture_guardrails.py::test_orm_package_root_loads_all_model_packages tests/test_service_architecture.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_project_management_platform_alignment.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py -q`
- PM contract split verification: `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py -q`, observed 65 passed
- PM project-domain split verification: `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_enterprise_pm_foundation.py tests/test_phase_b_user_admin_ui.py -q`, observed 112 passed
- PM task-domain split verification: `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_enterprise_pm_foundation.py tests/test_phase_b_user_admin_ui.py tests/test_task_dependency_ux_logic.py tests/test_cpm_flow.py tests/test_resource_leveling_workflow.py tests/test_progress_flow.py -q`, observed 126 passed
- PM resource-domain split verification: `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_enterprise_pm_foundation.py tests/test_phase_b_user_admin_ui.py tests/test_resource_leveling_workflow.py tests/test_finance_layer_integration.py tests/test_ui_professional_filters.py -q`, observed 123 passed
- PM financial cost-domain split verification: `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_finance_layer_integration.py tests/test_currency_defaults.py tests/test_large_scale_performance.py tests/test_exporters_configuration.py tests/test_technical_math_reporting.py tests/test_ui_professional_filters.py -q`, observed 95 passed, 1 skipped
- PM scheduling calendar-domain split verification: `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_cpm_flow.py tests/test_resource_leveling_workflow.py tests/test_technical_math_reporting.py tests/test_large_scale_performance.py -q`, observed 81 passed, 1 skipped
- PM scheduling baseline-domain split verification: `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_baseline_comparison_workflow.py tests/test_business_rules_and_edge_cases.py tests/test_domain_event_wiring.py tests/test_technical_math_reporting.py tests/test_exporters_configuration.py -q`, observed 125 passed
- PM risk register-domain split verification: `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_architecture_guardrails.py::test_orm_package_root_loads_all_model_packages tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_phase2_register_import_and_ui.py tests/test_dashboard_professional_panels.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py -q`, observed 69 passed
- latest full architecture result after the PM risk register-domain split: 94 passed
- PM collaboration application transfer verification: `pytest tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_project_management_platform_alignment.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_task_mentions_pro.py -q`, observed 174 passed
- PM portfolio application transfer verification: `pytest tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py tests/test_dashboard_portfolio_flow.py tests/test_enterprise_pm_foundation.py tests/test_project_management_platform_alignment.py tests/test_refactor_regressions.py tests/test_pro_set_v1_ui.py -q`, observed 194 passed
- PM timesheet/import-service transfer verification: `pytest tests/test_architecture_guardrails.py tests/test_service_architecture.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_project_management_platform_alignment.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_project_management_desktop_api.py -q`, observed 181 passed
- direct filesystem check confirms `core/modules/project_management/` and `infra/modules/project_management/` no longer exist
- PM root-cleanup verification: `pytest tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_project_management_desktop_api.py -q`, observed 170 passed

Continue next:

1. Continue the PM domain, service, API, and UI work before starting another module, with the legacy PM roots now fully removed and the remaining work happening only under `src/core/modules/project_management/*`.
2. Prioritize the remaining PM repo-structure transfer under `src/core/modules/project_management/{application,infrastructure,api}` before further QML-first expansion.
3. Regroup PM tests from the flat `tests/` area into `src/tests/project_management/*` as the feature slices settle.
4. Add PM gateway contracts under `src/core/modules/project_management/contracts/gateways/*` only when real gateway boundaries are extracted; do not add facade re-exports.

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

- `src/core/**` must not import `src/ui/**` or `src/ui_qml/**`
- `src/core/**` must not import `src/api/**`
- `src/core/**` must not import repository implementations
- `src/ui_qml/**` must not import `src/core/**/infrastructure/**`
- legacy `src/ui/**` must not import `src/core/**/infrastructure/**`
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

`infra/platform/*` runtime/ops utility target:

- move `path.py`, `resource.py`, `logging_config.py`, `version.py`, `update.py`, `updater.py`, `diagnostics.py`, `operational_support.py`, and `app_version.txt` into `src/infra/platform/`
- rewrite callers to `src.infra.platform.*`
- do not keep an `infra.platform` compatibility package

`migration/` target:

- `src/infra/persistence/migrations/`

`api/http/platform/*` target:

- `src/api/http/platform/*`
- add matching `src/api/desktop/platform/*`

`ui/platform/shell/*` target:

- historical Widget-era target was `src/ui/shell/*`
- final QML target is `src/ui_qml/shell/*`
- keep `src/ui/shell/*` active only until QML shell bootstrap is complete, tested, and entrypoints are switched

`ui/platform/admin` target:

- historical Widget-era platform screens live under `src/ui/platform/*`
- final platform QML screens target `src/ui_qml/platform/qml/workspaces/{admin,control,settings}/`
- final platform QML dialogs target `src/ui_qml/platform/qml/Platform/Dialogs/`
- final platform reusable QML widgets target `src/ui_qml/platform/qml/Platform/Widgets/`
- reusable final QML pieces live under `src/ui_qml/shared/qml/App/*`
- delete old Widget paths only after their matching QML screen/dialog/widget is complete and tested

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
