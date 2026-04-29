# Repo Structure Migration Plan

This document captures the exact target structure from `UpdateCodeBaseStructure.md`, the QML UI migration target from `PySide6_Widgets_to_QML_Migration_Spec.docx`, and a safe execution plan to reach it without breaking the current desktop app, runtime wiring, or test suite.

This is a planning document only. No runtime code is changed by this step.

## Instruction Precedence

This README now follows three inputs and one local execution companion:

1. `UpdateCodeBaseStructure.md` for the target tree and named folders
2. `me.md` for the detailed architectural rules, folder responsibilities, migration sequence, and refactor guardrails
3. `PySide6_Widgets_to_QML_Migration_Spec.docx` for the desktop UI migration from PySide6 Widgets to QML
4. `EXECUTION_SPEC.md` for the clean, no-facade execution mechanics

When the two documents differ in detail level, this README uses:

- the exact extracted tree from `UpdateCodeBaseStructure.md`
- the stricter behavioral rules from `me.md`
- the QML desktop UI target from `PySide6_Widgets_to_QML_Migration_Spec.docx`
- the clean hard-cutover mechanics from `EXECUTION_SPEC.md`

This means the extracted structure remains visible, but the refactor instructions below are now driven by the more detailed guidance in `me.md`.

Execution rule:

- use this README as the architecture map
- use `EXECUTION_SPEC.md` as the execution contract
- use `PySide6_Widgets_to_QML_Migration_Spec.docx` as the UI migration contract
- if a downloaded spec suggests temporary facades or compatibility wrappers, ignore that part and follow the clean hard-cutover rule instead
- if older README wording says `src/ui/*` for final desktop UI, interpret the final target as `src/ui_qml/*`; `src/ui/*` is legacy QWidget UI until each screen is migrated, verified, and deleted

## Active Pivot: QML UI Migration

Slice 2 project-management restructuring is paused as of 2026-04-22 while the desktop UI target is updated from PySide6 Widgets to QML.

New final UI rule:

- final desktop UI lives under `src/ui_qml/*`
- QML files render and bind state only
- workspace controller/catalog objects own refresh, mutation orchestration, loading/busy flags, error handling, and feedback state
- presenters own UI behavior and orchestration
- view models expose UI-shaped state only
- presenters call module-owned desktop APIs under `src/core/modules/<module>/api/desktop/*`
- `src/ui/*` remains the active legacy QWidget UI only until a screen has a complete QML replacement and regression coverage
- old QWidget paths are deleted only after their migrated screen is complete, imports/navigation are rewritten, and tests pass
- no new QWidget screens should be added for migrated modules

QML scaffold status:

- `src/ui_qml/*` has been created as the final landing zone
- shell bootstrap foundation exists under `src/ui_qml/shell/*`, including route definitions, a route registry, navigation view-model construction, QML engine loading glue, login view-model state, and valid shell QML components
- shell bootstrap now separates the top-level QML application route from navigable workspace routes, exposes a typed `Shell.Context` module under `src/ui_qml/shell/qml/Shell/Context/*`, and passes `shellModel`, `platformCatalog`, and `pmCatalog` into `App.qml` through initial properties instead of leaving those as untyped global QML context access
- shell bootstrap now loads the selected registered workspace inside `MainWindow.qml` through a `Loader` bound to `shellModel.currentRouteSource`; `shell.home` now targets `HomeWorkspace.qml`, and the loader injects `shellModel`, `platformCatalog`, and `pmCatalog` onto loaded workspace roots so the routed pages no longer depend on raw global context properties
- shared QML primitives now exist as namespace-backed modules under `src/ui_qml/shared/qml/App/{Theme,Controls,Widgets,Layouts}/*`, with `qmldir` definitions for stable named imports such as `App.Theme`, `App.Controls`, `App.Widgets`, and `App.Layouts`
- platform QML workspaces now exist under `src/ui_qml/platform/qml/workspaces/{admin,control,settings}/*` and are registered as navigable routes
- platform QML workspaces now bind through `platformWorkspaceCatalog`, which is backed by `src/api/desktop/platform/*` when a desktop API registry is connected
- platform QML admin/control/settings workspaces now render grouped presenter-backed overviews, using split platform desktop APIs for runtime, organization master data, approvals, and audit flows
- platform admin/control/settings now bind through grouped controller classes under `src/ui_qml/platform/controllers/{common,admin,control,settings}/*`; QML pages no longer own `refreshWorkspace()` orchestration or page-local feedback state
- platform controller types are now exposed to QML through the typed module `src/ui_qml/platform/qml/Platform/Controllers/{qmldir,typeinfo/*}`, with runtime registration in `src/ui_qml/platform/qml_type_registration.py`; workspace pages no longer declare controller objects as generic `QtObject`, and the grouped typeinfo fragments keep the controller metadata from collapsing back into one dump file
- platform `admin` now uses grouped controllers under `src/ui_qml/platform/controllers/admin/*`, including a dedicated `access_workspace_controller.py` alongside organization/site/department/employee/user/party/document controllers
- the stale `src/ui_qml/platform/controllers/admin/admin_workspace_controller.py` file has been removed; `PlatformAdminWorkspaceController` now lives in `src/ui_qml/platform/controllers/admin/admin_console_controller.py` as a thin orchestrator over the split admin controllers
- platform `admin` now exposes real QML organization/site/department/employee/user/party/document panels with controller-owned create, edit, toggle-active, set-active, role, and password-reset orchestration through `src/api/desktop/platform/*`
- platform `admin` now also exposes controller-owned document focus, preview-state, linked-record, and document-structure workflows through `src/ui_qml/platform/presenters/document_management_presenter.py`, `src/ui_qml/platform/qml/Platform/Widgets/DocumentDetailPanel.qml`, and focused document link/structure dialogs under `src/ui_qml/platform/qml/Platform/Dialogs/*`
- document state ownership is now cleanly split: `document_controller.py` owns document catalog, selected-document, preview, and link state, while `document_structure_controller.py` owns structure catalog and structure editor options
- platform `admin` now also exposes scoped access and account-security workflows through `src/ui_qml/platform/controllers/admin/access_workspace_controller.py`, `src/ui_qml/platform/presenters/access_workspace_presenter.py`, and `src/ui_qml/platform/qml/Platform/Widgets/AccessSecurityPanel.qml`
- platform `control` now exposes a QML approval queue with approve/reject actions, decision-note entry, and a QML audit feed, all through `platformWorkspaceCatalog` and split platform desktop APIs
- platform `settings` now exposes a QML module entitlement surface with license toggles, enable toggles, lifecycle-status changes, plus organization-profile visibility, all through `platformWorkspaceCatalog` and `PlatformRuntimeDesktopApi`
- platform `admin` now also exposes a QML support operations section through `src/api/desktop/platform/support.py`, `src/ui_qml/platform/controllers/admin/support_workspace_controller.py`, `src/ui_qml/platform/presenters/support_workspace_presenter.py`, and `src/ui_qml/platform/qml/workspaces/admin/AdminSupportSection.qml`
- the migrated QML support section now covers update settings persistence, manifest checks, Windows installer handoff, save-file diagnostics export, incident package creation, incident-trace copying, support-folder opening, and incident-scoped support activity feeds through the desktop API boundary
- the old QWidget support files should still stay in place for now because the legacy QWidget platform shell is still present and the QML shell is not the active runtime yet; do not delete `src/ui/platform/workspaces/admin/support/*` yet
- platform QML widgets now live under the named module `src/ui_qml/platform/qml/Platform/Widgets/*`, including `OverviewSectionCard.qml`, `RecordListCard.qml`, `WorkspaceStateBanner.qml`, and `AdminCatalogPanel.qml`
- platform QML dialogs now live under the named module `src/ui_qml/platform/qml/Platform/Dialogs/*`, including focused editor dialogs for organizations, sites, departments, employees, users, parties, documents, document links, and document structures plus `ApprovalDecisionDialog.qml` and `ModuleLifecycleDialog.qml`
- platform workspace entry files are now thin wrappers, and the large pages have been split into `AdminConsolePage.qml`, `SettingsWorkspacePage.qml`, `ControlWorkspacePage.qml`, plus focused section/dialog-host files under their workspace folders
- QML imports now use named modules with stable aliases instead of deep parent-relative paths; the active convention is `Theme`, `AppLayouts`, `AppWidgets`, `AppControls`, and `PlatformWidgets`
- the legacy QWidget Platform Home screen has been moved onto the same `src/api/desktop/platform/*` API boundary while the QML shell remains pending
- the legacy QWidget Module Licensing screen has been moved onto the same `src/api/desktop/platform/*` API boundary while it waits for full QML replacement
- the legacy QWidget Organizations screen has been moved onto the same `src/api/desktop/platform/*` API boundary while it waits for full QML replacement
- the legacy QWidget Sites screen has been moved onto the same `src/api/desktop/platform/*` API boundary while it waits for full QML replacement
- the legacy QWidget Departments and Employees screens have been moved onto the same `src/api/desktop/platform/*` API boundary while they wait for full QML replacement
- project-management QML workspaces now exist under `src/ui_qml/modules/project_management/qml/workspaces/{projects,tasks,scheduling,resources,financials,risk,portfolio,register,collaboration,timesheets,dashboard}/*` and are registered as navigable routes
- project-management QML presenter/view-model scaffolding now exists under `src/ui_qml/modules/project_management/{presenters,view_models}/*`
- project-management QML now binds to presenter-backed workspace metadata through loader-injected typed `pmCatalog` properties and named `ProjectManagement.Controllers` / `ProjectManagement.Widgets` modules
- project-management desktop API workspace metadata now exists under `src/core/modules/project_management/api/desktop/workspaces.py` and backs the PM QML route/presenter metadata path
- project-management dashboard now has a read-only desktop API snapshot contract under `src/core/modules/project_management/api/desktop/dashboard.py`, with project-scope selection, baseline selection, KPI overview metrics, EVM/register/cost analysis panels, burndown/resource chart descriptors, and read-only alert/milestone/critical-path/upcoming/register sections mapped into QML-safe presenter/view-model state
- project-management dashboard QML now renders that first real Slice 2 workflow slice through `DashboardSelectionBar.qml`, `DashboardMetricsSection.qml`, `DashboardAnalysisPanels.qml`, `DashboardChartsSection.qml`, `DashboardOverviewSections.qml`, `ProjectManagement.Widgets/WorkspaceStateBanner.qml`, `ProjectManagement.Widgets/DashboardPanelCard.qml`, `ProjectManagement.Widgets/DashboardChartCard.qml`, and `ProjectManagement.Widgets/DashboardSectionCard.qml`
- shared, platform, module, and `legacy_widgets/migration_only/*` folders exist for screen-by-screen migration
- the scaffold is intentionally not wired into `main_qt.py` yet, so the active QWidget app remains unchanged
- focused QML shell migration smoke coverage exists in `tests/test_qml_shell_migration.py`
- focused shared QML primitive coverage exists in `tests/test_qml_shared_primitives.py`
- focused platform QML route coverage exists in `tests/test_qml_platform_routes.py`
- focused platform QML presenter/API coverage exists in `tests/test_qml_platform_presenters.py`
- focused project-management QML route coverage exists in `tests/test_qml_project_management_routes.py`
- focused project-management QML presenter/view-model coverage exists in `tests/test_qml_project_management_presenters.py`
- focused project-management desktop API coverage exists in `tests/test_project_management_desktop_api.py`
- focused QML architecture guardrail coverage exists in `tests/test_qml_architecture_guardrails.py`
- automated offscreen QML route loading coverage exists in `tests/test_qml_offscreen_loading.py`
- project-management QML now also exposes typed `ProjectManagement.Controllers` / `ProjectManagement.Widgets` modules, a split dashboard page/controller, and a shared placeholder-page pattern aligned with the platform QML structure
- the latest PM-focused verification batches pass with `24 passed`, `9 passed`, `1 passed`, `7 passed`, and `22 passed`; `python -m compileall -q src/ui_qml src/core/modules/project_management tests` passes; and a full `qmllint` scan across `src/ui_qml/**/*.qml` is clean
- the focused platform support/QML batch now passes with `46 passed`, the broader support/runtime regression batch passes with `26 passed`, and a full `qmllint` scan across `src/ui_qml/**/*.qml` is clean

## Core Rule

The whole refactor follows this rule:

- business rules live in `domain/` and `application/`
- infrastructure only implements contracts
- UI only presents and delegates

## Detailed Architectural Instructions

### Top-Level Folder Responsibilities

#### `src/application/`

This is the cross-module application layer.

Use it only for:

- runtime orchestration
- cross-module application services
- generic app-level result wrappers
- pagination helpers
- bus abstractions
- cross-module read coordination

Put here:

- runtime context loading
- entitlement evaluation at app level
- common request/response envelopes
- generic command/query helpers
- application service base classes when truly cross-module

Do not put here:

- maintenance business logic
- project scheduling rules
- SQLAlchemy code
- Qt widgets

Rule:

- if logic belongs to one specific module, it does not belong in `src/application/`

#### `src/core/`

This is the business heart of the system.

It contains:

- `platform/` for shared enterprise business capabilities
- `modules/` for business domains

`src/core/` must not depend on:

- Qt
- FastAPI
- SQLAlchemy session objects
- filesystem adapters directly
- email sender implementations directly

`src/core/` may depend on:

- pure Python
- dataclasses and typing
- same-layer contracts
- shared kernel utilities

#### `src/core/platform/`

This holds shared business capabilities used by many modules.

Examples:

- auth
- authorization
- organization
- documents
- notifications
- module entitlements
- audit
- approvals
- report runtime
- time rules

This is shared business logic, not technical infrastructure.

Put here:

- permission rules
- audit entry domain objects
- module subscription domain objects
- document attachment business contracts
- organization, site, department, and business unit ownership

Do not put here:

- generic DB engine setup
- logger config
- SMTP connection implementation
- local file storage code

Those belong in global `src/infra/`.

#### `src/core/modules/`

This holds all business modules:

- `maintenance`
- `project_management`
- `inventory_procurement`
- `hr_management`
- `payroll`
- `qhse`

Each module must be able to function as a mini-application.

Each module must contain:

- `domain/`
- `application/`
- `contracts/`
- `infrastructure/`
- `api/`

#### `src/infra/`

This is global technical infrastructure.

Put here:

- DB engine and session setup
- transaction and unit-of-work support
- migration support
- event dispatch plumbing
- storage adapters
- notification adapters
- config loading
- composition root

Do not put here:

- maintenance work-order rules
- project task scheduling rules
- HR leave approval rules

Those belong in `src/core/`.

#### `src/api/`

This is the transport adapter layer.

It adapts application use cases for delivery channels:

- desktop
- future HTTP

Put here:

- DTO mapping from application handlers to transport payloads
- response formatting
- transport-level validation wrappers
- route or controller adapters

Do not put here:

- SQLAlchemy code
- deep business rules
- Qt widget code

#### `src/ui_qml/`

This is the final desktop presentation layer.

It should contain:

- QML shell and navigation
- QML workspaces
- QML dialogs
- QML widgets and controls
- presenters
- view models
- UI services
- formatting helpers

Put here:

- QML rendering and binding
- presenter-owned user interaction handling
- calling desktop API or application handlers
- formatting values for display

Do not put here:

- repository access
- domain creation rules
- entitlement logic
- audit write logic
- approval engine logic
- SQLAlchemy sessions
- QWidget screens as final-state UI

#### `src/ui/`

This is now legacy PySide6 QWidget UI.

Rules:

- keep it runnable until each QML replacement is complete
- do not add new final-state screens here
- delete each old QWidget screen only after the matching `src/ui_qml/*` screen is implemented, navigation/imports are rewritten, and tests pass
- if a temporary Widget quarantine is needed during active migration, place it under `src/ui_qml/legacy_widgets/migration_only/*`

#### `src/tests/`

Tests should be split by:

- architecture
- platform
- module
- UI

Put here:

- unit tests
- handler tests
- repository tests
- architecture dependency tests
- UI smoke tests

### Standard Internal Structure

Every module under `src/core/modules/<module_name>/` must use this structure:

```text
domain/
application/
contracts/
infrastructure/
api/
```

Each platform capability under `src/core/platform/<capability>/` should follow the same mini-module pattern:

```text
domain/
application/
contracts/
infrastructure/   # optional
```

Subfolder rule:

- inside `domain/`, create subfolders by business subdomain, not generic buckets like `entities/` or `models/`
- inside `application/`, create subfolders by business subdomain and then split into `commands/`, `queries/`, `dto/`, and `mappers/`
- inside `contracts/`, split into `repositories/`, `gateways/`, and `services/` when needed
- inside `infrastructure/`, split into `persistence/repositories/`, `persistence/mappers/`, `persistence/read_models/`, and add `importers/`, `exporters/`, or `reporting/` only when needed
- inside `api/`, keep separate `desktop/` and `http/` adapters

### Layer Responsibilities Inside A Module

#### `domain/`

This is the pure business model of the module.

It represents:

- what the business concepts are
- what rules apply to them
- what state changes are valid
- what business events happen

Domain contains:

- aggregates and entities
- value objects
- rules and invariants
- domain services when needed
- domain events

Domain must not contain:

- SQLAlchemy models
- Qt classes
- HTTP request or response objects
- DB sessions
- email sending
- file upload logic

Domain may import:

- Python stdlib
- shared kernel utilities
- same-module domain files

Domain must not import:

- infrastructure
- UI
- transport adapters

#### `application/`

This is the use-case layer of the module.

It answers:

- what the user or system is trying to do
- what steps are needed
- what repositories and gateways are needed
- what data is returned

Application contains:

- commands
- queries
- DTOs
- DTO mappers
- application policies when needed

Application must:

- orchestrate repositories and gateways
- enforce access and entitlement through platform services or policies
- create and update domain entities
- persist through contracts
- emit domain events or audit hooks
- return DTOs or results

Application must not:

- write SQL directly
- access Qt
- access FastAPI request objects
- perform raw filesystem work directly
- contain rendering logic

Application may import:

- same-module domain
- same-module contracts
- platform application services or policies when needed
- shared result types

Application must not import:

- repository implementation classes from infrastructure
- Qt widgets
- HTTP adapters

Handler file convention:

- each state-changing use case gets its own command file
- each important read flow gets its own query file
- command files should usually contain a typed command object plus a handler
- command objects carry input data only and should not contain business logic
- handlers should validate access and entitlements, load required data, create or update domain entities, persist through contracts, trigger audit or events, and return DTOs or results

#### `contracts/`

This folder defines the interfaces the module depends on.

Contracts contain:

- repository interfaces
- gateways to other modules, platform capabilities, or external systems
- reusable service interfaces
- published event contracts when needed

Contracts must not contain:

- SQLAlchemy
- concrete implementations
- Qt
- HTTP

Rule:

- contracts must be small and use-case driven, not giant generic interfaces

#### `infrastructure/`

This is the module-local implementation layer.

It implements the module's contracts.

Infrastructure contains:

- persistence repository implementations
- ORM and data mappers
- read models
- import and export adapters
- reporting helpers

Infrastructure must not contain:

- business rules that belong in domain
- permission rules
- UI rendering

Important distinction:

- if something is used by many modules, it belongs in global `src/infra/`
- if something only supports one module's contracts, it belongs in that module's `infrastructure/`

#### `api/`

This adapts module use cases to delivery channels.

Module API contains:

- `desktop/` thin adapters used by the PySide UI
- `http/` thin adapters for future FastAPI routes or controllers

Module API must:

- call application handlers
- convert results into transport-friendly payloads
- convert transport exceptions into response-friendly errors

Module API must not:

- contain domain logic
- contain persistence logic
- contain UI rendering

### QML UI Instructions

The final desktop UI must be split under `src/ui_qml/` by:

- shell
- shared QML controls, dialogs, widgets, layouts, theme, services, formatting helpers, presenters, view models, and models
- platform QML workspaces, dialogs, widgets, presenters, and view models
- module-owned QML workspaces, dialogs, widgets, presenters, and view models
- temporary legacy QWidget migration buckets

Target structure:

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

`src/ui_qml/modules/<module>/qml/workspaces/` contains full screens and top-level module workspaces.

Each QML workspace should:

- render UI
- bind to presenter/view-model state
- forward user intent to presenter methods
- display loading, empty, error, and success states

Each QML workspace must not:

- create domain entities directly
- instantiate repositories
- know SQLAlchemy
- own business rules in JavaScript
- call handlers or infrastructure directly

Presenter rules:

- presenters call module-owned desktop APIs
- presenters or workspace-controller/catalog objects own loading, busy, error, feedback, retry, refresh, navigation, and dialog orchestration state
- presenters map DTOs into UI-shaped view models
- presenters must not create repositories, manage transactions, render QML, or mutate domain aggregates directly

QML module rules:

- do not use parent-relative QML imports such as `../../../../`
- expose reusable QML through `qmldir`-backed named modules
- shared reusable imports use `App.*` namespaces
- platform reusable imports use `Platform.*` namespaces
- keep aliasing consistent across files: `Theme`, `AppLayouts`, `AppWidgets`, `AppControls`, and `PlatformWidgets`
- QML files render state and emit simple user-intent actions; workspace controllers/catalogs own refresh and mutation sequencing

View-model rules:

- view models expose display-ready state only
- view models may contain labels, formatted dates, formatted money, selection flags, enabled flags, and user-facing status text
- view models must not call APIs, repositories, handlers, or SQLAlchemy

Reusable QML controls such as filters, cards, tables, badges, toolbars, charts, and date pickers belong in `src/ui_qml/shared/qml/*` and must not contain business logic.

### Hard Refactor Rules

1. Do not leave giant catch-all files like `domain.py`, `interfaces.py`, or `service.py` once a module becomes large.
2. Every state-changing use case should become a dedicated command handler file.
3. Every important screen query should become a dedicated query handler or read model file.
4. No module may import another module's internals directly.
5. Allowed cross-module interaction is by IDs, contracts or gateways, published events, and platform services.
6. No UI class may import repository implementations.
7. No domain file may import infrastructure or UI.
8. Repository implementations live in `infrastructure/`; contracts live in `contracts/`.
9. DTOs returned to UI or API live in `application/`.
10. Transport formatting lives in `api/`, not in handlers.
11. Composition and wiring live only in `src/infra/composition/`.
12. Preserve behavior while restructuring.
13. Global technical plumbing goes in `src/infra`; shared business capabilities go in `src/core/platform`.
14. Add architecture tests to enforce these boundaries.

## Source Of Truth Extracted From The Uploaded Spec

### Canonical Source Tree

```text
src/
  application/
    runtime/
      platform_runtime.py
      entitlement_runtime.py
    common/
      bus.py
      result.py
      pagination.py

  core/
    platform/
      access/
      approval/
      audit/
      auth/
      authorization/
      common/
      data_exchange/
      documents/
      notifications/
      org/
      party/
      report_runtime/
      runtime_tracking/
      time/

    modules/
      maintenance/
      project_management/
      inventory_procurement/
      hr_management/
      payroll/
      qhse/

  infra/
    composition/
      app_container.py
      platform_registry.py
      maintenance_registry.py
      project_registry.py
      inventory_registry.py
      hr_registry.py
      payroll_registry.py
      qhse_registry.py

    persistence/
      db/
        engine.py
        session_factory.py
        unit_of_work.py
      migrations/
      orm/
        platform/
        maintenance/
        project_management/
        inventory_procurement/
        hr_management/
        payroll/
        qhse/

    messaging/
      event_bus.py
      domain_event_dispatcher.py

    storage/
      file_store.py
      local_file_store.py

    notifications/
      email_sender.py
      desktop_notifier.py

    reporting/
      export_service.py

    config/
      settings.py
      logging.py

  api/
    desktop/
      runtime.py
      platform/
      maintenance/
      project_management/
      inventory_procurement/
      hr_management/
      payroll/
      qhse/
    http/
      runtime.py
      platform/
      maintenance/
      project_management/
      inventory_procurement/
      hr_management/
      payroll/
      qhse/

  ui/
    shell/
      app.py
      login.py
      main_window.py
      navigation.py
    platform/
      workspaces/
      dialogs/
      widgets/
    modules/
      maintenance/
      project_management/
      inventory_procurement/
      hr_management/
      payroll/
      qhse/

  tests/
    architecture/
    platform/
    maintenance/
    project_management/
    inventory_procurement/
    hr_management/
    payroll/
    qhse/
    ui/
```

### Canonical Platform Core Tree

```text
core/platform/
  auth/
    domain/
      user.py
      credential.py
      session.py
    application/
      login.py
      logout.py
      change_password.py
    contracts/
      auth_repository.py
      password_hasher.py

  authorization/
    domain/
      role.py
      permission.py
      policy.py
    application/
      grant_role.py
      revoke_role.py
      check_permission.py

  access/
    domain/
      access_scope.py
      feature_access.py
    application/
      access_control_service.py
    contracts.py
    authorization.py

  modules/
    domain/
      module_definition.py
      module_entitlement.py
      subscription.py
      defaults.py
      module_codes.py
    application/
      module_catalog_service.py
      module_catalog_context.py
      module_catalog_mutation.py
      module_catalog_query.py
      authorization.py
      guard.py
    contracts.py

  org/
    domain/
      organization.py
      site.py
      department.py
      employee.py
    application/
      organization_service.py
      site_service.py
      department_service.py
      employee_service.py
      employee_support.py
    contracts.py
    support.py
    access_policy.py

  party/
    domain/
      party.py
    application/
      party_service.py
    contracts.py

  approval/
    domain/
      approval_request.py
      approval_state.py
    application/
      approval_service.py
    contracts.py
    policy.py

  documents/
    domain/
      document.py
      attachment_link.py
      document_version.py
    application/
      upload_document.py
      attach_document.py
      version_document.py

  notifications/
    domain/
      notification.py
      channel.py
      preference.py
    application/
      send_notification.py
      list_notifications.py

  audit/
    contracts.py
    helpers.py
    domain/
      audit_entry.py
    application/
      audit_service.py

  report_runtime/
    domain/
      report_definition.py
      report_execution.py
    application/
      run_report.py
      export_report.py

  runtime_tracking/
    domain/
      runtime_event.py
      user_activity.py
    application/
      track_activity.py

  time/
    domain/
      calendar.py
      business_day.py
      recurrence.py
    application/
      evaluate_due_date.py
```

### Canonical Project Management Tree

```text
core/modules/project_management/
  domain/
    projects/
      project.py
      project_phase.py
      project_status.py
      project_rules.py
      events.py

    tasks/
      task.py
      dependency.py
      milestone.py
      assignment.py
      progress_entry.py
      rules.py

    scheduling/
      schedule.py
      network_graph.py
      critical_path.py
      calendar.py
      baseline.py
      rules.py

    resources/
      team_member.py
      allocation.py
      capacity.py

    risk/
      risk_item.py
      issue.py
      action_item.py

    financials/
      budget.py
      cost_entry.py
      forecast.py

  application/
    projects/
      commands/
        create_project.py
        update_project.py
        archive_project.py
      queries/
        list_projects.py
        get_project_dashboard.py

    tasks/
      commands/
        create_task.py
        update_task.py
        assign_task.py
        complete_task.py
        reorder_task.py
      queries/
        list_tasks.py
        get_task_board.py
        get_task_detail.py

    scheduling/
      commands/
        recalculate_schedule.py
        set_baseline.py
        update_calendar.py
      queries/
        get_schedule.py
        get_critical_path.py
        get_schedule_variance.py

    resources/
      commands/
        allocate_resource.py
        rebalance_workload.py
      queries/
        get_resource_load.py
        get_capacity_plan.py

    financials/
      commands/
        update_budget.py
        record_cost.py
      queries/
        get_budget_summary.py
        get_cost_variance.py

  contracts/
    repositories/
      project_repository.py
      task_repository.py
      schedule_repository.py
      allocation_repository.py
      budget_repository.py
    gateways/
      employee_lookup.py
      notification_service.py
      report_service.py

  infrastructure/
    persistence/
      repositories/
        sql_project_repository.py
        sql_task_repository.py
        sql_schedule_repository.py
        sql_budget_repository.py
      mappers/
        project_mapper.py
        task_mapper.py
        schedule_mapper.py
      read_models/
        project_dashboard_read.py
        gantt_read.py
        resource_load_read.py
    reporting/
      earned_value_report.py
      milestone_report.py

  api/
    desktop/
      projects_api.py
      tasks_api.py
      scheduling_api.py
      resources_api.py
    http/
      projects_router.py
      tasks_router.py
      scheduling_router.py
      resources_router.py
```

### Canonical Maintenance Tree

```text
core/modules/maintenance/
  domain/
    assets/
      asset.py
      asset_component.py
      asset_hierarchy.py
      asset_status.py
      rules.py
      events.py

    locations/
      location.py
      maintenance_system.py
      site_map.py

    work_requests/
      work_request.py
      request_priority.py
      request_status.py
      rules.py
      events.py

    work_orders/
      work_order.py
      work_order_task.py
      work_order_task_step.py
      work_order_labor.py
      work_order_material.py
      work_order_status.py
      work_order_source.py
      rules.py
      events.py

    preventive/
      preventive_plan.py
      preventive_plan_task.py
      preventive_schedule.py
      recurrence.py
      trigger_policy.py
      generation_rules.py

    reliability/
      downtime_event.py
      failure_code.py
      root_cause.py
      sensor.py
      sensor_reading.py
      sensor_exception.py
      reliability_rules.py

    documents/
      maintenance_document_link.py

  application/
    assets/
      commands/
        create_asset.py
        update_asset.py
        retire_asset.py
        move_asset.py
      queries/
        get_asset.py
        list_assets.py
        get_asset_history.py
        get_asset_hierarchy.py
      dto/
        asset_dto.py
        asset_summary_dto.py

    work_requests/
      commands/
        create_work_request.py
        approve_work_request.py
        reject_work_request.py
        convert_request_to_order.py
      queries/
        list_work_requests.py
        get_work_request.py
        get_request_backlog.py
      dto/
        work_request_dto.py

    work_orders/
      commands/
        create_work_order.py
        assign_work_order.py
        reschedule_work_order.py
        start_work_order.py
        pause_work_order.py
        complete_work_order.py
        close_work_order.py
        cancel_work_order.py
        add_task.py
        add_material_requirement.py
        record_labor.py
      queries/
        list_work_orders.py
        get_work_order.py
        get_work_order_board.py
        get_work_order_backlog.py
      dto/
        work_order_dto.py
        work_order_detail_dto.py
        work_order_board_item_dto.py

    preventive/
      commands/
        create_plan.py
        update_plan.py
        suspend_plan.py
        regenerate_schedule.py
        generate_due_work.py
      queries/
        list_plans.py
        get_plan.py
        get_forecast.py
      dto/
        preventive_plan_dto.py
        preventive_forecast_item_dto.py

    reliability/
      commands/
        record_downtime.py
        add_failure_code.py
        capture_sensor_reading.py
        raise_sensor_exception.py
      queries/
        get_reliability_summary.py
        list_downtime_events.py
        get_asset_health.py
      dto/
        downtime_dto.py
        reliability_summary_dto.py

  contracts/
    repositories/
      asset_repository.py
      location_repository.py
      work_request_repository.py
      work_order_repository.py
      work_order_task_repository.py
      preventive_plan_repository.py
      downtime_repository.py
      sensor_repository.py
      failure_code_repository.py
    gateways/
      employee_lookup.py
      document_service.py
      notification_service.py
    events/
      work_order_events.py
      preventive_events.py

  infrastructure/
    persistence/
      repositories/
        sql_asset_repository.py
        sql_location_repository.py
        sql_work_request_repository.py
        sql_work_order_repository.py
        sql_preventive_plan_repository.py
        sql_downtime_repository.py
        sql_sensor_repository.py
      mappers/
        asset_mapper.py
        work_request_mapper.py
        work_order_mapper.py
        preventive_mapper.py
        reliability_mapper.py
      read_models/
        work_order_backlog_read.py
        preventive_forecast_read.py
        reliability_dashboard_read.py
    reporting/
      maintenance_kpis.py
      export_work_orders.py
    importers/
      import_assets.py
      import_failure_codes.py
    exporters/
      export_pm_schedule.py

  api/
    desktop/
      assets_api.py
      work_requests_api.py
      work_orders_api.py
      preventive_api.py
      reliability_api.py
    http/
      assets_router.py
      work_requests_router.py
      work_orders_router.py
      preventive_router.py
      reliability_router.py
```

### Canonical Inventory & Procurement Tree

```text
core/modules/inventory_procurement/
  domain/
    catalog/
      item.py
      item_category.py
      unit_of_measure.py
      vendor_item.py

    inventory/
      stock_lot.py
      stock_balance.py
      warehouse.py
      bin_location.py
      stock_movement.py
      cycle_count.py
      reorder_rule.py

    procurement/
      vendor.py
      purchase_request.py
      purchase_order.py
      purchase_order_line.py
      goods_receipt.py
      invoice_match.py

    pricing/
      price_list.py
      contract_price.py

  application/
    catalog/
      commands/
        create_item.py
        update_item.py
      queries/
        list_items.py
        get_item.py

    inventory/
      commands/
        receive_stock.py
        issue_stock.py
        transfer_stock.py
        adjust_stock.py
        count_stock.py
      queries/
        get_stock_balance.py
        list_movements.py
        get_reorder_suggestions.py

    procurement/
      commands/
        create_purchase_request.py
        approve_purchase_request.py
        create_purchase_order.py
        receive_goods.py
      queries/
        list_purchase_orders.py
        get_vendor_performance.py
        get_open_requests.py

  contracts/
    repositories/
      item_repository.py
      stock_repository.py
      movement_repository.py
      vendor_repository.py
      po_repository.py
    gateways/
      document_service.py
      approval_service.py

  infrastructure/
    persistence/
      repositories/
        sql_item_repository.py
        sql_stock_repository.py
        sql_po_repository.py
      mappers/
        item_mapper.py
        inventory_mapper.py
        procurement_mapper.py
      read_models/
        stock_dashboard_read.py
        procurement_pipeline_read.py
    reporting/
      stock_valuation_report.py
      purchasing_spend_report.py

  api/
    desktop/
      catalog_api.py
      inventory_api.py
      procurement_api.py
    http/
      catalog_router.py
      inventory_router.py
      procurement_router.py
```

### Canonical Global Infrastructure Tree

```text
infra/
  persistence/
    db/
      engine.py
      session_factory.py
      unit_of_work.py
    migrations/
    orm/
      base.py

  messaging/
    event_bus.py
    event_dispatcher.py

  storage/
    file_store.py
    local_file_store.py

  notifications/
    email_sender.py
    desktop_notifier.py

  composition/
    app_container.py
    platform_registry.py
    maintenance_registry.py
    project_registry.py
    inventory_registry.py
    hr_registry.py
    payroll_registry.py
    qhse_registry.py

  config/
    settings.py
    logging.py
```

### Canonical QML UI Module Pattern

```text
src/ui_qml/modules/<module_name>/
  qml/
    workspaces/
      main/
        MainPage.qml
      board/
        BoardPage.qml
      dashboard/
        DashboardPage.qml
    dialogs/
      CreateDialog.qml
      EditDialog.qml
      DetailDialog.qml
    widgets/
      Filters.qml
      Grid.qml
      Cards.qml
  presenters/
    list_presenter.py
    form_presenter.py
    detail_presenter.py
  view_models/
    list_vm.py
    detail_vm.py
    form_vm.py
```

### Architectural Rules From The Uploaded Spec

- `src/ui_qml` can depend on module desktop APIs and QML-safe presenter/view-model helpers, not on repositories
- legacy `src/ui` must not receive new final-state screens
- `api` can depend on `application`, not directly on ORM repositories
- `application` can depend on `domain` and `contracts`
- `infrastructure` can implement `contracts`
- `domain` must not depend on `ui`
- one module must not import another module's internals directly

## Current Repo Delta Against The Target

The current repo already has the right high-level concepts, but not yet in the target shape:

- source packages live at repo root today: `application/`, `api/`, `core/`, `infra/`, `ui/`
- the target introduces a new `src/` root
- `application/` currently only contains platform runtime orchestration
- `api/` currently only contains `api/http/platform/*`
- `api/desktop/*` does not exist yet
- `core/platform/*` exists, but most packages are still organized as flat `service.py`, `domain.py`, `interfaces.py`, `query.py`, or `support.py` files instead of `domain/`, `application/`, and `contracts/`
- `core/modules/project_management/*` exists, but it is organized as `domain/`, `services/`, `reporting/`, and `importing/` rather than the target `domain/`, `application/`, `contracts/`, `infrastructure/`, and `api/`
- `core/modules/maintenance_management/*` must be renamed to `core/modules/maintenance/*`
- `infra/platform/service_registration/*` is the current composition root; the target expects `infra/composition/*_registry.py`
- migrations currently live in `migration/`, not under `infra/persistence/migrations/`
- platform ORM rows, repositories, and mappers now live under `src/core/platform/infrastructure/persistence/{orm,mappers,repositories}/*`
- business-module ORM rows currently live under `src/infra/persistence/orm/inventory_procurement/*` and `maintenance/*`; those folders are transitional Slice 1 de-mixing homes, not the final module-owned infrastructure layout
- platform repositories and mappers now use the same structure as module persistence: `src/core/platform/infrastructure/persistence/repositories/<area>.py`, `mappers/<area>.py`, and `orm/<area>.py`; business-module repositories still use transitional module infrastructure such as `infra/modules/*/db/*` until each module slice moves them under module-owned infrastructure
- `src/ui/*` currently contains migrated-but-still-Widget desktop UI from the earlier refactor; it is now legacy active UI, not the final presentation target
- final desktop UI now targets `src/ui_qml/*` with QML rendering, Python presenters, and Python view models
- `src/ui_qml/*` scaffold is in place for shell, shared, platform, module, and legacy-widget migration buckets
- `src/ui_qml/shell/*` now has route/registry/navigation/QML engine glue, a QML-bound `shellContext`, a routed `MainWindow.qml` host, and a dedicated `HomeWorkspace.qml` landing route; `main_qt.py` still imports `src.ui.shell.app`
- `src/ui_qml/shared/qml/*` now has first-pass reusable QML design primitives aligned to the legacy widget token palette
- `src/ui_qml/platform/routes.py` registers platform QML routes for admin, control, and settings, and `src/ui_qml/platform/context.py` now exposes grouped overview maps for those workspaces
- `src/ui_qml/platform/presenters/{runtime,admin_presenter,control_presenter,settings_presenter,control_queue_presenter,settings_catalog_presenter,organization_catalog_presenter,site_catalog_presenter,department_catalog_presenter,employee_catalog_presenter}.py`, `src/ui_qml/platform/view_models/{runtime,workspace}.py`, `src/ui_qml/platform/controllers/admin/admin_console_controller.py`, and `src/ui_qml/platform/qml/{widgets,dialogs}/*` now provide grouped overview, admin master-data actions, dialogs, action-list, and workspace-state surfaces for platform QML
- `src/ui_qml/modules/project_management/routes.py` registers the PM QML route set named by Slice 2
- `src/ui_qml/modules/project_management/presenters/workspace_presenter.py` and `view_models/workspace.py` provide the first PM QML presenter/view-model contract without importing legacy widgets or infrastructure
- `src/ui_qml/modules/project_management/context.py` exposes a QML-safe PM workspace catalog used by PM QML placeholders
- `src/core/modules/project_management/api/desktop/workspaces.py` now owns PM workspace descriptors used by QML routes and presenters; QML file paths remain owned by `src/ui_qml`
- `src/core/modules/project_management/api/desktop/dashboard.py`, `src/ui_qml/modules/project_management/presenters/{dashboard_presenter,dashboard_workspace_presenter}.py`, and `view_models/dashboard.py` now define the first real PM dashboard QML read-only snapshot contract with selectors, KPI cards, analysis panels, chart descriptors, and delivery-health sections
- `tests/test_qml_architecture_guardrails.py` now protects the QML migration dependency direction: core cannot import UI, QML Python cannot import legacy widgets or persistence, QML Python cannot use QtWidgets, module desktop APIs cannot import QML, and QML files cannot reference persistence concerns
- `tests/test_qml_offscreen_loading.py` now loads every registered QML route with `QT_QPA_PLATFORM=offscreen` and the required shell/PM context objects
- `src/ui_qml/legacy_widgets/migration_only/*` is the only temporary holding area for QWidget screens during an active migration window
- old `src/ui/*` Widget folders are deleted screen-by-screen only after the matching QML screen, presenter, view model, route, and tests are complete
- employee management currently lives in platform-oriented code, but the detailed guide says HR should own employee master data in the target structure
- tests are currently mostly flat under `tests/`; the target expects grouped test packages under `tests/architecture`, `tests/platform`, `tests/project_management`, `tests/inventory_procurement`, `tests/maintenance`, and `tests/ui`

## Clarifications And Detailed Overrides

The extracted tree is still correct as a structure target, but `me.md` adds important clarifications that this plan now treats as binding:

1. The repo should use both top-level `src/api/` and module-local `core/modules/<module>/api/`.
   Working interpretation:
   - module-local `api/` contains module-scoped desktop and HTTP adapters
   - top-level `src/api/` contains platform application transport entrypoints, runtime adapters, and channel aggregation; platform UI must communicate through this platform API surface instead of direct infrastructure access

2. The repo should use global `src/infra/persistence/orm/` only for shared SQLAlchemy metadata concerns, and module-local `infrastructure/persistence/` for module-owned persistence.
   Working interpretation:
   - global `orm/` holds `Base` plus the metadata loader/registry used by migrations
   - module-local `infrastructure/persistence/` holds module-specific ORM rows, repositories, mappers, and read models
   - existing global module ORM packages such as `src/infra/persistence/orm/inventory_procurement/*` and `maintenance/*` are temporary and must be removed during the owning module slice after rows move to `src/core/modules/<module>/infrastructure/persistence/orm/`
   - platform-owned rows live under `src/core/platform/infrastructure/persistence/orm/`
   - platform-owned repositories and mappers live under `src/core/platform/infrastructure/persistence/repositories/<area>.py` and `src/core/platform/infrastructure/persistence/mappers/<area>.py`

3. The QML migration spec replaces the old final `src/ui/*` Widget target with `src/ui_qml/*`.
   Added instruction:
   - use `src/ui_qml/shared/qml/*`, `src/ui_qml/shared/presenters`, `src/ui_qml/shared/view_models`, `src/ui_qml/shared/services`, and `src/ui_qml/shared/formatting` for reusable presentation assets
   - keep `src/ui_qml/platform/*` for platform-owned QML workspaces, dialogs, widgets, presenters, and view models
   - keep `src/ui/*` only as active legacy QWidget UI until each screen is migrated and deleted

4. The detailed guide clarifies business ownership that matters for future modules.
   Added instruction:
   - HR owns employee master data
   - other modules should reference employee IDs or use gateways, not import HR internals
   - payroll must stay isolated from HR internals except through approved contracts
   - QHSE may reference asset IDs and employee IDs, but must not import maintenance or HR internals directly

5. Several live features in the current app are not named in the extracted module trees.
   Current examples:
   - project management: portfolio, register, collaboration, timesheets, data import, dashboard coordinators
   - maintenance: planner, task templates, dashboard workspace, library-style UIs
   - inventory: reservations, stock control split, data exchange, maintenance integration, reporting helpers
   Refactor rule:
   - assign each of them a final target home before moving the slice
   - do not keep them behind compatibility modules after the slice is completed

6. The uploaded trees describe the source layout, not the whole repository.
   Assumption used in this plan:
   - root entrypoints and support files such as `main_qt.py`, `main.py`, `assets/`, `installer/`, `docs/`, `.github/`, and packaging files stay at repo root while source code moves under `src/`

## Non-Breaking Migration Rules

These rules govern every phase:

1. No big-bang rename.
   We still move one slice at a time, but each completed slice is a hard cutover with the old paths removed for that slice.

2. Keep entrypoints stable.
   `main_qt.py`, `main.py`, packaging scripts, and startup behavior stay working throughout the migration.

3. Finish one slice before the next.
   Platform first, then one business module end-to-end before starting the next one.

4. Move by dependency direction.
   Public callers are rewritten to the new application and API adapter paths inside the same slice before the old paths are removed.

5. Do not preserve old imports.
   Rewrite imports, entrypoints, tests, and wiring inside the same slice and remove legacy paths before marking that slice complete.

6. Add architectural tests as we move.
   New path rules are enforced before deleting the old paths.

7. Do not delete live features just because the uploaded tree does not name them yet.
   They must be assigned a final destination before the relevant slice is completed.

## Global Rollout Order

This is the safest order for the current repo:

1. Platform
2. Project Management
3. Inventory & Procurement
4. Maintenance
5. HR Management, Payroll, and QHSE placeholders
6. Legacy path cleanup

This order is one intentional inference from the current codebase, not from the uploaded text: `Maintenance` currently integrates with `Inventory & Procurement`, so finishing inventory before the maintenance rename minimizes cross-module churn.

## Required Subphase Sequence Inside Every Slice

The detailed guide in `me.md` requires the same internal migration sequence for every slice:

1. Create folders only.
   Create the target folder structure and `__init__.py` files without moving logic yet.
2. Move domain files.
   Split giant domain files by business subdomain without changing behavior.
3. Move contracts.
   Extract repository and gateway interfaces into `contracts/`.
4. Split services into handlers.
   Convert large service files into command handlers, query handlers, DTOs, and mappers.
5. Move repository implementations.
   Move concrete persistence code into module `infrastructure/`.
6. Add API adapters.
   Create desktop and HTTP adapters per module.
7. Thin the UI.
   Add presenters and view models and reduce widget responsibilities.
8. Clean the composition root.
   Replace giant service-registration files with registries and the app container.
9. Add architecture tests.
   Add tests enforcing import boundaries.

Non-negotiable rule:

- do not move everything at once
- do not change business behavior while a slice is only being restructured

## Slice Plan

### Slice 1: Platform

Goal: establish `src/`, move platform-owned runtime/composition/persistence/UI shell, and complete a clean platform cutover with no legacy compatibility layer left behind.

#### Exact changes

| Current path | Target path | Change |
| --- | --- | --- |
| `application/platform/runtime/service.py` | `src/application/runtime/platform_runtime.py` | move current platform runtime application service |
| `core/platform/modules/runtime.py` plus module runtime orchestration in `core/platform/modules/service.py` | `src/application/runtime/entitlement_runtime.py` | extract entitlement/runtime application workflow |
| `application/__init__.py`, `application/platform/__init__.py`, `application/platform/runtime/__init__.py` | removed after import rewrite | move all callers to `src/application/...` and delete the legacy package path in the same slice |
| `core/platform/*` | `src/core/platform/*` | split packages into the exact `domain/`, `application/`, and `contracts/` layout from the uploaded spec |
| `infra/platform/service_registration/*` | `src/infra/composition/*_registry.py` | rename bundles into registries |
| `infra/platform/services.py` | `src/infra/composition/app_container.py` | move service graph/container build |
| `infra/platform/db/base.py` | `src/infra/persistence/db/engine.py`, `session_factory.py`, `unit_of_work.py` | split engine/session/UoW responsibilities |
| `migration/*` | `src/infra/persistence/migrations/*` | move Alembic environment and versions under target tree |
| `infra/platform/db/*` | `src/infra/persistence/db/*` and `src/core/platform/infrastructure/persistence/orm/*` | separate db plumbing from platform ORM models/mappers; business-module ORM rows in global folders are transitional only |
| `infra/platform/path.py`, `resource.py`, `logging_config.py`, `version.py`, `update.py`, `updater.py`, `diagnostics.py`, `operational_support.py`, `app_version.txt` | `src/infra/platform/*` | move platform-owned runtime/ops utilities and runtime version file |
| `api/http/platform/*` | `src/api/http/platform/*` | keep current platform HTTP adapter under new root |
| none | `src/api/desktop/runtime.py` and `src/api/desktop/platform/*` | add desktop-facing platform API adapter layer |
| `ui/platform/shell/*` | `src/ui/shell/*` | move shell app, login, main window, navigation |
| `ui/platform/settings/*` | `src/ui/platform/settings/*` | move shell-owned persisted desktop settings under the new platform UI root |
| `ui/platform/admin/*`, `ui/platform/control/*` | `src/ui/platform/workspaces/*` | platform workspaces move under target UI grouping |
| current platform dialogs | `src/ui/platform/dialogs/*` | consolidate platform-owned dialogs out of workspace folders |
| cross-cutting UI helpers now under `ui/platform/shared/*` | `src/ui/shared/*` | move reusable widgets, dialogs, formatting, and UI models into the shared presentation layer required by the detailed guide |
| platform-only UI helpers | `src/ui/platform/widgets/*` | keep platform-owned widgets separate from globally shared presentation helpers |
| `tests/test_architecture_guardrails.py` | `src/tests/architecture/*` | split rules by dependency concern |
| flat platform tests under `tests/` | `src/tests/platform/*` | regroup platform-specific tests |

#### Platform package split map

- `core/platform/auth/*` becomes `src/core/platform/auth/domain/*`, `application/*`, and `contracts/*`
- `core/platform/authorization/*` becomes `src/core/platform/authorization/domain/*` and `application/*`
- `core/platform/common/*` becomes `src/core/platform/common/exceptions.py`, `ids.py`, `interfaces.py`, `runtime_access.py`, and `service_base.py`
- `core/platform/access/*` becomes `src/core/platform/access/domain/*`, `application/*`, `contracts.py`, and `authorization.py`
- `core/platform/data_exchange/*` becomes `src/core/platform/data_exchange/service.py` and `__init__.py`
- `core/platform/modules/*` becomes `src/core/platform/modules/domain/*`, `application/*`, and `contracts.py`
- `core/platform/org/*` becomes `src/core/platform/org/domain/*`, `application/*`, `contracts.py`, `support.py`, and `access_policy.py`
- `core/platform/party/*` becomes `src/core/platform/party/domain/*`, `application/*`, and `contracts.py`
- `core/platform/approval/*` becomes `src/core/platform/approval/domain/*`, `application/*`, `contracts.py`, and `policy.py`
- `core/platform/documents/*` becomes `src/core/platform/documents/domain/*`, `application/*`, `contracts.py`, and `support.py`
- `core/platform/notifications/*` becomes the real event-hub package under `src/core/platform/notifications/domain_events.py` and `signal.py` until notification workflows are implemented
- `core/platform/audit/*` becomes `src/core/platform/audit/domain/audit_entry.py`, `application/audit_service.py`, `contracts.py`, and `helpers.py`
- `core/platform/importing/*` becomes `src/core/platform/importing/domain/*` and `application/*`
- `core/platform/exporting/*` becomes `src/core/platform/exporting/domain/*` and `application/*`
- `core/platform/report_runtime/*` becomes `src/core/platform/report_runtime/domain/*` and `application/*`
- `core/platform/runtime_tracking/*` becomes `src/core/platform/runtime_tracking/domain/*` and `application/*`
- `core/platform/time/*` becomes `src/core/platform/time/domain/*` and `application/*`

#### Platform safety checks

- update `main_qt.py` and `main.py` to import from the new `src` paths inside this slice
- update `pytest.ini` and test bootstrapping to use only the new path strategy once this slice lands
- remove `tests/path_rewrites.py` as soon as the new path strategy is fully active
- do not cement employee master-data ownership inside platform during this slice; keep current behavior compatible, then move ownership into `hr_management` when Slice 5 is executed
- run architecture and platform suites after platform migration before touching any module

#### Slice 1 execution status

Updated: 2026-04-24

Completed in the clean/no-facade execution:

- created the target `src/` tree and package markers
- moved `application/platform/runtime/service.py` to `src/application/runtime/platform_runtime.py`
- deleted the old `application/` package path after all callers were rewritten
- moved `core/platform/modules/runtime.py` to `src/application/runtime/entitlement_runtime.py`
- removed module-runtime re-exports from `core/platform/__init__.py` and `core/platform/modules/__init__.py`
- moved `api/http/platform/*` to `src/api/http/platform/*`
- deleted the old top-level `api/` package path after all callers were rewritten
- moved `infra/platform/services.py` to `src/infra/composition/app_container.py`
- moved `infra/platform/service_registration/*` into `src/infra/composition/*_registry.py` and `src/infra/composition/repositories.py`
- deleted the old `infra/platform/service_registration/` package path after all callers were rewritten
- split `infra/platform/db/base.py` into `src/infra/persistence/orm/base.py`, `src/infra/persistence/db/engine.py`, `src/infra/persistence/db/session_factory.py`, and `src/infra/persistence/db/unit_of_work.py`
- deleted `infra/platform/db/base.py` after ORM models, entrypoints, workers, and tests were rewritten
- moved `migration/*` to `src/infra/persistence/migrations/*`
- moved `infra/platform/migrate.py` to `src/infra/persistence/migrations/runner.py`
- updated `main.py`, `main_qt.py`, and `main_qt.spec` to use the new migration runner/assets path
- moved platform ORM model files out of `infra/platform/db/`; business-module ORM rows landed in temporary global de-mixing homes until their module slices move them under module-local infrastructure:
  - `models.py` to `src/infra/persistence/orm/platform/models.py` initially, then to `src/core/platform/infrastructure/persistence/orm/models.py`, and now split by platform area under `src/core/platform/infrastructure/persistence/orm/{access,approval,audit,auth,documents,modules,org,party,runtime_tracking,time}.py`
  - `inventory_models.py` to `src/infra/persistence/orm/inventory_procurement/models.py`
  - `maintenance_models.py` to `src/infra/persistence/orm/maintenance/models.py`
  - `maintenance_preventive_runtime_models.py` to `src/infra/persistence/orm/maintenance/preventive_runtime_models.py`
- rewired platform persistence adapters, metadata loading, tests, and timesheet regression checks to platform-owned infrastructure imports under `src.core.platform.infrastructure.persistence`
- deleted the old global `src/infra/persistence/orm/platform/` package after callers were rewritten
- moved `infra/platform/db/optimistic.py` to `src/infra/persistence/db/optimistic.py`
- moved platform persistence adapters from `src/infra/persistence/db/platform/*` to `src/core/platform/infrastructure/persistence/*` for access, approval, audit, auth, documents, modules, org, party, runtime tracking, and time
- deleted the old global `src/infra/persistence/db/platform/` package after callers were rewritten
- deleted the old `infra/platform/db/` package after callers were rewritten
- removed `infra/platform/db/repositories.py`, `repositories_org.py`, and `mappers.py` instead of keeping compatibility facades
- rewired composition registries, module repositories, regression tests, architecture guardrails, and test path rewrites to the new direct imports
- moved the remaining platform runtime/ops utilities from `infra/platform/*` to `src/infra/platform/*`:
  - `path.py`
  - `resource.py`
  - `logging_config.py`
  - `version.py`
  - `update.py`
  - `updater.py`
  - `diagnostics.py`
  - `operational_support.py`
  - `app_version.txt`
- rewired shell startup, main window update checks, support workspace flows, settings persistence, persistence engine DB path lookup, PM collaboration attachments, tests, and PyInstaller data packaging to `src.infra.platform.*`
- fixed `src/infra/platform/resource.py` root discovery after the deeper `src/` move so bundled assets still resolve from the project root
- preserved local/offline update support in the moved update helpers by keeping plain filesystem manifest paths and `file://` installer downloads working
- deleted the old top-level `infra/platform/` package after all live files were moved
- added a guardrail for removing the legacy `infra/platform/` runtime package and legacy `infra.platform` runtime imports
- moved the real shell package from `ui/platform/shell/*` to `src/ui/shell/*`
- replaced `src/ui/shell/app.py` and `src/ui/shell/login.py` placeholders with real shell startup and login wiring
- updated `main_qt.py`, UI tests, and test path rewrites to import from `src.ui.shell`
- deleted the old `ui/platform/shell/` package after callers were rewritten
- replaced `src/api/desktop/runtime.py` with a real desktop API registry builder
- added real platform desktop adapters under `src/api/desktop/platform/`:
  - `models.py`
  - `runtime.py`
- wired `src/ui/shell/app.py` to expose the desktop API registry and platform runtime desktop adapter in the desktop service map
- added targeted desktop adapter tests for platform runtime flows
- rewired the legacy QWidget Platform Home screen to consume `PlatformRuntimeDesktopApi.get_runtime_context()` instead of platform runtime application-service snapshot/list calls
- rewired the legacy QWidget Module Licensing screen to consume `PlatformRuntimeDesktopApi` and `ModuleStatePatchCommand` instead of calling `PlatformRuntimeApplicationService` directly
- rewired the legacy QWidget Organizations screen to consume `PlatformRuntimeDesktopApi`, `OrganizationProvisionCommand`, and `OrganizationUpdateCommand` instead of calling `OrganizationService` or `PlatformRuntimeApplicationService` directly
- split platform desktop API DTOs and commands out of the old monolithic `src/api/desktop/platform/models.py` into `src/api/desktop/platform/models/{common,organization,runtime,site,department,employee,document,party,user}.py`
- split the old broad platform org desktop adapter into focused `src/api/desktop/platform/{site,department,employee}.py` adapters
- rewired the legacy QWidget Sites screen to consume `PlatformSiteDesktopApi`, `SiteCreateCommand`, and `SiteUpdateCommand` instead of calling `SiteService` directly
- rewired the legacy QWidget Departments screen to consume `PlatformDepartmentDesktopApi`, `PlatformSiteDesktopApi`, `DepartmentCreateCommand`, and `DepartmentUpdateCommand` instead of calling `DepartmentService` or `SiteService` directly
- rewired the legacy QWidget Employees screen to consume `PlatformEmployeeDesktopApi`, `PlatformDepartmentDesktopApi`, `PlatformSiteDesktopApi`, `EmployeeCreateCommand`, and `EmployeeUpdateCommand` instead of calling `EmployeeService`, `SiteService`, or `DepartmentService` directly
- added focused `src/api/desktop/platform/{document,party,user}.py` adapters and rewired the legacy QWidget Documents, Parties, and Users screens to consume `PlatformDocumentDesktopApi`, `PlatformPartyDesktopApi`, and `PlatformUserDesktopApi` instead of calling `DocumentService`, `PartyService`, or `AuthService` directly
- added focused `src/api/desktop/platform/{access,approval,audit}.py` adapters plus split `src/api/desktop/platform/models/{access,approval,audit}.py` DTO/command files so the platform API surface stays split by workflow instead of growing new dump files
- extended `PlatformUserDesktopApi` with account-security actions so the Security workspace stays on the user desktop API boundary for unlock and session-revocation flows
- rewired the legacy QWidget Access and Security screens to consume `PlatformAccessDesktopApi`, `PlatformUserDesktopApi`, and shell-provided scope loaders instead of calling `AccessControlService`, `AuthService`, or `ProjectService` directly
- rewired the legacy QWidget Approvals and Audit screens to consume `PlatformApprovalDesktopApi` and `PlatformAuditDesktopApi` instead of calling `ApprovalService`, `AuditService`, or PM display-resolution services directly
- moved audit display resolution into `PlatformAuditDesktopApi`, so the audit widget now renders resolved project/entity/detail labels without reaching into PM services
- rewired the document structure manager, document preview/dialog flow, and document link management to stay on the document desktop API boundary
- wired the desktop API registry and shell context to expose `desktop_platform_site_api`, `desktop_platform_department_api`, `desktop_platform_employee_api`, `desktop_platform_access_api`, `desktop_platform_approval_api`, `desktop_platform_audit_api`, `desktop_platform_document_api`, `desktop_platform_party_api`, and `desktop_platform_user_api`
- updated the shared PM governance approval queue integration to hand `ApprovalQueuePanel` a `PlatformApprovalDesktopApi`, keeping the shared queue on one contract even before the PM module slice is migrated
- added QML architecture guardrails that keep Platform Home, Module Licensing, Organizations, Sites, Departments, Employees, Access, Approvals, Audit, Documents, Parties, and Users on the platform desktop API boundary while their QML replacements are pending
- extended `src/ui_qml/shell/context.py` and `src/ui_qml/shell/navigation.py` to expose QML-safe route-source metadata, and rewired `src/ui_qml/shell/qml/MainWindow.qml` to host the selected registered workspace through a `Loader`
- split the navigable shell landing route onto `src/ui_qml/shell/qml/HomeWorkspace.qml` so `shell.home` no longer points back at `MainWindow.qml`
- upgraded the platform QML surface beyond placeholders by adding grouped admin/control/settings presenters under `src/ui_qml/platform/presenters/{admin_presenter,control_presenter,settings_presenter}.py`, grouped view models under `src/ui_qml/platform/view_models/workspace.py`, reusable section cards under `src/ui_qml/platform/qml/Platform/Widgets/OverviewSectionCard.qml`, and grouped desktop-API-backed overview serialization in `src/ui_qml/platform/context.py`
- added `src/ui_qml/platform/presenters/{control_queue_presenter,settings_catalog_presenter}.py` so `platform.control` and `platform.settings` can expose action-list data without growing the overview presenters into dump files
- extended `src/ui_qml/platform/context.py` with QML-safe `approvalQueue()`, `auditFeed()`, `moduleEntitlements()`, `organizationProfiles()`, `approveRequest()`, `rejectRequest()`, `toggleModuleLicensed()`, and `toggleModuleEnabled()` methods
- added `src/ui_qml/platform/controllers/admin/admin_console_controller.py` plus `src/ui_qml/platform/presenters/{organization_catalog_presenter,site_catalog_presenter,department_catalog_presenter,employee_catalog_presenter}.py` so `platform.admin` can own real org/site/department/employee workflows without turning the overview presenter into a dump file
- upgraded `src/ui_qml/platform/qml/workspaces/control/ControlWorkspace.qml` from overview-only to a real approval/audit surface, and upgraded `src/ui_qml/platform/qml/workspaces/settings/SettingsWorkspace.qml` from overview-only to a real module-entitlement/runtime-settings surface
- added `src/ui_qml/platform/presenters/{user_catalog_presenter,party_catalog_presenter,document_catalog_presenter}.py` so `platform.admin` can extend the same controller-owned pattern to users, parties, and documents without growing the admin controller into API-specific orchestration code
- upgraded `src/ui_qml/platform/qml/workspaces/admin/AdminWorkspace.qml` from the first org/site/department/employee surface into a broader admin QML surface for organizations, sites, departments, employees, users, parties, and documents, backed by `src/ui_qml/platform/qml/Platform/Widgets/AdminCatalogPanel.qml` and `src/ui_qml/platform/qml/Platform/Dialogs/{OrganizationEditorDialog,SiteEditorDialog,DepartmentEditorDialog,EmployeeEditorDialog,UserEditorDialog,PartyEditorDialog,DocumentEditorDialog}.qml`
- added `src/ui_qml/platform/controllers/admin/access_workspace_controller.py`, `src/ui_qml/platform/presenters/access_workspace_presenter.py`, and `src/ui_qml/platform/qml/Platform/Widgets/AccessSecurityPanel.qml` so `platform.admin` now owns scoped access grants and account-security actions through a separate controller instead of growing the admin controller into another dump file
- upgraded `src/ui_qml/platform/qml/workspaces/control/ControlWorkspace.qml` with `ApprovalDecisionDialog.qml` and controller-owned `approveRequestWithNote()` / `rejectRequestWithNote()` flows so approval decision notes now live on the QML side
- upgraded `src/ui_qml/platform/qml/workspaces/settings/SettingsWorkspace.qml` with `ModuleLifecycleDialog.qml`, controller-owned lifecycle options, and `changeModuleLifecycleStatus()` so module lifecycle changes now live on the QML side without putting lifecycle rules into QML
- added `src/ui_qml/platform/qml/Platform/Controllers/{qmldir,plugins.qmltypes}` plus `src/ui_qml/platform/qml_type_registration.py`, typed `PlatformWorkspaceCatalog` controller properties in `src/ui_qml/platform/context.py`, and rewired the active platform QML pages/widgets to consume typed controller properties instead of generic `QtObject`
- added `src/ui_qml/platform/presenters/document_management_presenter.py`, split selected-document/preview/link/structure state across `src/ui_qml/platform/controllers/admin/{admin_console_controller.py,document_controller.py,document_structure_controller.py}`, and upgraded `src/ui_qml/platform/qml/workspaces/admin/AdminWorkspace.qml` so document preview-state, linked-record management, and structure management now live on the QML side through controller-owned actions
- added `src/ui_qml/platform/qml/Platform/Widgets/DocumentDetailPanel.qml` plus `src/ui_qml/platform/qml/Platform/Dialogs/{DocumentLinkEditorDialog,DocumentStructureEditorDialog}.qml` so the document admin slice no longer depends on the legacy widget document dialogs for those workflows
- at that checkpoint support was still on the legacy QWidget side; later slices moved the support workflow into `src/ui_qml/*`, but the old Widget files still remain until the legacy shell is retired
- split `core/platform/runtime_tracking/*` into the real `src/core/platform/runtime_tracking/` package:
  - `domain/runtime_execution.py`
  - `contracts.py`
  - `application/runtime_execution_service.py`
- deleted placeholder runtime-tracking target files from `src/core/platform/runtime_tracking/`
- rewired importing/exporting/report runtime, composition, and persistence imports to `src.core.platform.runtime_tracking`
- deleted the old `core/platform/runtime_tracking/` package after callers were rewritten
- split `core/platform/report_runtime/*` into the real `src/core/platform/report_runtime/` package:
  - `domain/report_definition.py`
  - `domain/report_document.py`
  - `application/report_definition_registry.py`
  - `application/report_runtime.py`
- deleted placeholder report-runtime target files from `src/core/platform/report_runtime/`
- rewired module reporting contracts/services/tests to `src.core.platform.report_runtime`
- deleted the old `core/platform/report_runtime/` package after callers were rewritten
- split `core/platform/importing/*` into the real `src/core/platform/importing/` package:
  - `domain/import_definition.py`
  - `domain/import_models.py`
  - `application/import_definition_registry.py`
  - `application/csv_import_runtime.py`
- split `core/platform/exporting/*` into the real `src/core/platform/exporting/` package:
  - `domain/export_definition.py`
  - `domain/export_models.py`
  - `application/artifact_delivery.py`
  - `application/export_definition_registry.py`
  - `application/export_runtime.py`
- rewired platform data exchange, module import/export services, report runtime, UI import flows, and tests to `src.core.platform.importing` and `src.core.platform.exporting`
- deleted the old `core/platform/importing/` and `core/platform/exporting/` packages after callers were rewritten
- split `core/platform/time/*` into the real `src/core/platform/time/` package:
  - `domain/timesheet_models.py`
  - `contracts.py`
  - `application/time_service.py`
  - `application/timesheet_entries.py`
  - `application/timesheet_periods.py`
  - `application/timesheet_query.py`
  - `application/timesheet_review.py`
  - `application/timesheet_support.py`
- deleted placeholder target files from `src/core/platform/time/`
- rewired composition, persistence, PM timesheet wrappers/domain/UI, maintenance labor, and tests to `src.core.platform.time`
- deleted the old `core/platform/time/` package after callers were rewritten
- split `core/platform/auth/*` into the real `src/core/platform/auth/` package:
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
- deleted placeholder target files from `src/core/platform/auth/`
- moved auth-specific repository contracts out of `core/platform/common/interfaces.py` into `src/core/platform/auth/contracts/auth_repository.py`
- rewired composition, platform services, runtime packages, module services, UI, tests, persistence, and test path rewrites to `src.core.platform.auth`
- deleted the old `core/platform/auth/` package after callers were rewritten
- split `core/platform/authorization/*` into the real `src/core/platform/authorization/` package:
  - `domain/authorization_engine.py`
  - `application/session_authorization_engine.py`
- deleted placeholder target files from `src/core/platform/authorization/`
- rewired platform auth/access helpers and authorization tests to `src.core.platform.authorization`
- deleted the old `core/platform/authorization/` package after callers were rewritten
- split `core/platform/access/*` into the real `src/core/platform/access/` package:
  - `domain/access_scope.py`
  - `domain/feature_access.py`
  - `application/access_control_service.py`
  - `contracts.py`
  - `authorization.py`
- deleted placeholder target files from `src/core/platform/access/`
- moved access-specific repository contracts out of `core/platform/common/interfaces.py` into `src/core/platform/access/contracts.py`
- rewired composition, auth principal building, persistence, platform services, module services, UI, tests, and test path rewrites to `src.core.platform.access`
- deleted the old `core/platform/access/` package after callers were rewritten
- split `core/platform/modules/*` into the real `src/core/platform/modules/` package:
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
- deleted placeholder target files from `src/core/platform/modules/`
- rewired entitlement runtime, composition, runtime access helpers, import/export/report runtime, persistence, UI, tests, and module guards to `src.core.platform.modules`
- deleted the old `core/platform/modules/` package after callers were rewritten
- split `core/platform/org/*` into the real `src/core/platform/org/` package:
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
- deleted placeholder target files from `src/core/platform/org/`
- moved org-specific repository contracts out of `core/platform/common/interfaces.py` into `src/core/platform/org/contracts.py`
- rewired composition, persistence, platform services, module services, UI, tests, and test path rewrites to `src.core.platform.org`
- deleted the old `core/platform/org/` package after callers were rewritten
- split `core/platform/party/*` into the real `src/core/platform/party/` package:
  - `domain/party.py`
  - `application/party_service.py`
  - `contracts.py`
- deleted placeholder target files from `src/core/platform/party/`
- rewired composition, persistence, platform services, inventory/maintenance services, UI, tests, and test path rewrites to `src.core.platform.party`
- deleted the old `core/platform/party/` package after callers were rewritten
- split `core/platform/approval/*` into the real `src/core/platform/approval/` package:
  - `domain/approval_request.py`
  - `domain/approval_state.py`
  - `application/approval_service.py`
  - `contracts.py`
  - `policy.py`
- deleted placeholder target files from `src/core/platform/approval/`
- moved the approval repository contract out of `core/platform/common/interfaces.py` into `src/core/platform/approval/contracts.py`
- rewired composition, persistence, governance UI, PM governance helpers, inventory procurement approval flows, tests, and test path rewrites to `src.core.platform.approval`
- deleted the old `core/platform/approval/` package after callers were rewritten
- split `core/platform/documents/*` into the real `src/core/platform/documents/` package:
  - `domain/document.py`
  - `domain/document_link.py`
  - `domain/document_structure.py`
  - `application/document_service.py`
  - `application/document_integration_service.py`
  - `contracts.py`
  - `support.py`
- deleted placeholder target files from `src/core/platform/documents/`
- rewired composition, persistence, PM collaboration, inventory item master, maintenance document services, admin document UI, tests, and test path rewrites to `src.core.platform.documents`
- deleted the old `core/platform/documents/` package after callers were rewritten
- moved the live notifications event hub from `core/platform/notifications/*` to the real `src/core/platform/notifications/` package:
  - `domain_events.py`
  - `signal.py`
- deleted placeholder notification target files from `src/core/platform/notifications/`
- rewired platform services, module services, shell/UI listeners, tests, and test path rewrites to `src.core.platform.notifications.domain_events` and `src.core.platform.notifications.signal`
- deleted the old `core/platform/notifications/` package after callers were rewritten
- split `core/platform/audit/*` into the real `src/core/platform/audit/` package:
  - `domain/audit_entry.py`
  - `application/audit_service.py`
  - `contracts.py`
  - `helpers.py`
- deleted placeholder target files from `src/core/platform/audit/`
- moved `AuditLogRepository` out of `core/platform/common/interfaces.py` into `src/core/platform/audit/contracts.py`
- rewired composition, persistence, platform services, PM/inventory/maintenance services, UI, tests, and test path rewrites to `src.core.platform.audit`
- deleted the old `core/platform/audit/` package after callers were rewritten
- moved the remaining shared platform utilities from `core/platform/common/*` to the real `src/core/platform/common/` package:
  - `exceptions.py`
  - `ids.py`
  - `interfaces.py`
  - `runtime_access.py`
  - `service_base.py`
- rewired platform packages, modules, UI, tests, `main.py`, and path rewrites to `src.core.platform.common`
- deleted the old `core/platform/common/` package after callers were rewritten
- moved the remaining platform master-data exchange package from `core/platform/data_exchange/*` to `src/core/platform/data_exchange/`:
  - `service.py`
  - `__init__.py`
- rewired composition, tests, and path rewrites to `src.core.platform.data_exchange`
- deleted the old `core/platform/data_exchange/` package after callers were rewritten
- moved `ui/platform/settings/*` to `src/ui/platform/settings/*`:
  - `__init__.py`
  - `main_window_store.py`
- rewired shell, PM UI, support UI, test helpers, and test path rewrites to `src.ui.platform.settings`
- deleted the old `ui/platform/settings/` package after callers were rewritten
- moved the cross-cutting shared UI layer from `ui/platform/shared/*` to `src/ui/shared/*`:
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
- rewired shell, platform admin/control, PM UI, inventory UI, maintenance UI, tests, and test path rewrites to `src.ui.shared.*`
- deleted the old `ui/platform/shared/` package after callers were rewritten
- moved the platform control workspaces from `ui/platform/control/*` to `src/ui/platform/workspaces/control/*`:
  - approvals:
    - `presentation.py`
    - `queue.py`
    - `tab.py`
  - audit:
    - `tab.py`
- rewired shell workspace registration, governance UI, procurement tests, user-admin tests, and test path rewrites to `src.ui.platform.workspaces.control.*`
- deleted the old `ui/platform/control/` package after callers were rewritten
- moved the remaining platform admin UI from `ui/platform/admin/*` into the target `src/ui/platform/*` groupings:
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
- rewired shell workspace registration, maintenance document previews/viewers, admin tests, architecture guardrails, and test path rewrites to `src.ui.platform.workspaces.admin.*`, `src.ui.platform.dialogs.*`, and `src.ui.platform.widgets.*`
- deleted the old `ui/platform/admin/` package after callers were rewritten
- split the remaining mixed-ownership ORM aggregate by moving PM-owned rows into the temporary Slice 1 de-mixing home `src/infra/persistence/orm/project_management/models.py`; this temporary global PM ORM package was removed in the first Slice 2 persistence cleanup:
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
- rewired PM persistence adapters and collaboration storage to the temporary `src.infra.persistence.orm.project_management.models` path during Slice 1; those imports now point at split feature ORM files under `src.core.modules.project_management.infrastructure.persistence.orm.*`
- rewired inventory persistence adapters to `src.infra.persistence.orm.inventory_procurement.models` instead of importing inventory rows through `src.infra.persistence.orm.platform.models`
- updated `src/infra/persistence/orm/__init__.py` and `src/infra/persistence/migrations/env.py` so metadata loading imports all current ORM packages directly rather than relying on the platform model barrel; this loader must be adjusted as module ORM rows move to module-local infrastructure
- removed the stale `core/__init__.py` UI side effect so `src.infra.composition.app_container` imports cleanly in a fresh process again

Verified:

- `python -m compileall -q src infra ui core tests main.py main_qt.py main_qt.spec` passes
- direct imports for platform runtime, entitlement runtime, platform HTTP API, and persistence bootstrap pass
- direct import of `src.infra.persistence.db.optimistic.update_with_version_check` passes
- direct import of `src.ui.shell.navigation.ShellNavigation` passes
- migration asset lookup resolves `src/infra/persistence/migrations/alembic.ini`
- in `conda run -n pmenv`, direct import of `src.ui.shell.main_window.MainWindow` passes
- in `conda run -n pmenv`, direct import of `src.api.desktop.runtime.build_desktop_api_registry` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.runtime_tracking.RuntimeExecutionService`, `RuntimeExecutionRepository`, and `RuntimeExecution` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.report_runtime.ReportDefinitionRegistry`, `ReportRuntime`, `ReportDocument`, and `ReportFormat` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.importing.CsvImportRuntime`, `ImportDefinitionRegistry`, and `ImportFieldSpec` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.exporting.ExportArtifactDraft`, `ExportDefinitionRegistry`, and `ExportRuntime` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.time.application.TimeService`, `src.core.platform.time.contracts.TimeEntryRepository`, `src.core.platform.time.domain.TimesheetPeriodStatus`, and `src.core.platform.time.application.timesheet_review.TimesheetReviewQueueItem` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.auth.AuthService`, `UserSessionContext`, `UserSessionPrincipal`, `UserRepository`, `AuthSessionRepository`, `UserAccount`, and `AuthSession` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.authorization.AuthorizationEngine`, `SessionAuthorizationEngine`, `get_authorization_engine`, and `set_authorization_engine` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.access.AccessControlService`, `ScopedRolePolicy`, `ScopedRolePolicyRegistry`, `ProjectMembershipRepository`, `ScopedAccessGrantRepository`, `ProjectMembership`, and `ScopedAccessGrant` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.modules.ModuleCatalogService`, `ModuleEntitlementRepository`, `ModuleEntitlementRecord`, `SupportsModuleEntitlements`, `EnterpriseModule`, `ModuleEntitlement`, and `PlatformCapability` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.org.DepartmentService`, `EmployeeService`, `OrganizationService`, `SiteService`, `DepartmentRepository`, `EmployeeRepository`, `OrganizationRepository`, `SiteRepository`, `Department`, `Employee`, `EmploymentType`, `Organization`, and `Site` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.party.Party`, `PartyRepository`, `PartyService`, and `PartyType` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.approval.ApprovalRequest`, `ApprovalRepository`, `ApprovalService`, `ApprovalStatus`, `DEFAULT_GOVERNED_ACTIONS`, and `is_governance_required` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.documents.Document`, `DocumentIntegrationService`, `DocumentLinkRepository`, `DocumentRepository`, `DocumentService`, `DocumentStorageKind`, `DocumentStructure`, `DocumentStructureRepository`, and `DocumentType` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.notifications.DomainChangeEvent`, `DomainEvents`, `Signal`, and `domain_events` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.audit.AuditLogEntry`, `AuditLogRepository`, `AuditService`, and `record_audit` passes
- in `conda run -n pmenv`, direct import of `src.core.platform.common.BusinessRuleError`, `ServiceBase`, `generate_id`, `src.core.platform.common.interfaces.TimeEntryRepository`, `src.core.platform.common.runtime_access.enforce_runtime_access`, `src.core.platform.data_exchange.MasterDataExchangeService`, and `MasterDataExportRequest` passes
- in `conda run -n pmenv`, direct import of `src.ui.platform.settings.MainWindowSettingsStore` passes
- in `conda run -n pmenv`, direct import of `src.ui.shared.dialogs.LoginDialog`, `start_async_job`, `src.ui.shared.formatting.UIConfig`, `apply_app_style`, `src.ui.shared.models.UndoStack`, and `src.ui.shared.widgets.CodeFieldWidget` passes
- in `conda run -n pmenv`, direct import of `src.ui.platform.workspaces.control.ApprovalControlTab`, `ApprovalQueuePanel`, `AuditLogTab`, `approval_display_label`, and `approval_context_label` passes
- in `conda run -n pmenv`, direct import of `src.ui.platform.workspaces.admin.AccessTab`, `DepartmentAdminTab`, `DocumentAdminTab`, `EmployeeAdminTab`, `ModuleLicensingTab`, `OrganizationAdminTab`, `PartyAdminTab`, `SiteAdminTab`, `SupportTab`, and `UserAdminTab` passes
- in `conda run -n pmenv`, direct import of `src.ui.platform.dialogs.DocumentLinksDialog`, `DocumentPreviewDialog`, `DocumentEditDialog`, `OrganizationEditDialog`, `PasswordResetDialog`, `UserCreateDialog`, and `UserEditDialog` passes
- in `conda run -n pmenv`, direct import of `src.ui.platform.widgets.build_admin_header`, `build_admin_table`, `DocumentPreviewWidget`, and `build_document_preview_state` passes
- in `conda run -n pmenv`, direct import of `src.infra.persistence.orm.Base`, PM split ORM files for project/task/resource/baseline/collaboration/portfolio, `src.infra.persistence.orm.inventory_procurement.models.InventoryItemCategoryORM`, `PurchaseOrderORM`, `StockItemORM`, and `src.core.platform.infrastructure.persistence.orm.models.TimeEntryORM`, `TimesheetPeriodORM`, `UserORM`, `OrganizationORM` passes
- in `conda run -n pmenv`, direct import of `src.infra.composition.app_container.build_service_dict` passes again after removing the stale `core/__init__.py` side effect
- in `conda run -n pmenv`, direct import of `src.infra.platform.path`, `resource`, `version`, `update`, `updater`, `diagnostics`, and `operational_support` passes; `resource_path("assets/icons/app.ico")` resolves to the project-root asset path
- direct metadata smoke import confirms platform repositories load from `src.core.platform.infrastructure.persistence.repositories.*`, platform mappers load from `src.core.platform.infrastructure.persistence.mappers.*`, and split platform ORM files keep `TimeEntryORM`, `TimesheetPeriodORM`, `UserORM`, `OrganizationORM`, `AuditLogORM`, and `RuntimeExecutionORM` registered in `Base.metadata`
- `python -m compileall -q src/ui_qml tests/test_qml_shell_migration.py tests/test_qml_platform_presenters.py tests/test_qml_platform_routes.py tests/test_qml_offscreen_loading.py tests/test_qml_migration_scaffold.py` passes
- in `conda run -n pmenv`, `pytest tests/test_qml_shell_migration.py tests/test_qml_shared_primitives.py tests/test_qml_project_management_routes.py tests/test_qml_project_management_presenters.py tests/test_qml_platform_routes.py tests/test_qml_platform_presenters.py tests/test_qml_offscreen_loading.py tests/test_qml_migration_scaffold.py tests/test_qml_architecture_guardrails.py -q` passes with 47 passed
- in `conda run -n pmenv`, `pytest tests/test_main_window_shell_navigation.py -q` passes with 7 passed
- `python -m compileall -q src/ui_qml tests/test_qml_platform_presenters.py tests/test_qml_platform_routes.py tests/test_qml_offscreen_loading.py tests/test_qml_shell_migration.py tests/test_qml_migration_scaffold.py` passes after the control/settings workflow slice
- in `conda run -n pmenv`, `pytest tests/test_qml_platform_presenters.py tests/test_qml_platform_routes.py tests/test_qml_offscreen_loading.py tests/test_qml_shell_migration.py tests/test_qml_migration_scaffold.py tests/test_qml_architecture_guardrails.py -q` passes with 38 passed after the control/settings workflow slice
- in `conda run -n pmenv`, `pytest tests/test_qml_shell_migration.py tests/test_qml_shared_primitives.py tests/test_qml_project_management_routes.py tests/test_qml_project_management_presenters.py tests/test_qml_platform_routes.py tests/test_qml_platform_presenters.py tests/test_qml_offscreen_loading.py tests/test_qml_migration_scaffold.py tests/test_qml_architecture_guardrails.py -q` passes with 49 passed after the control/settings workflow slice
- `python -m compileall -q src/ui_qml src/api/desktop tests/test_platform_support_desktop_api.py tests/test_qml_platform_presenters.py tests/test_qml_architecture_guardrails.py tests/test_qml_offscreen_loading.py` passes after the extended platform support QML slice
- in `conda run -n pmenv`, `pytest tests/test_platform_support_desktop_api.py tests/test_qml_platform_presenters.py tests/test_qml_architecture_guardrails.py tests/test_qml_offscreen_loading.py tests/test_platform_admin_desktop_api.py -q` passes with 46 passed after the extended platform support QML slice
- in `conda run -n pmenv`, `pytest tests/test_operational_support.py tests/test_support_productization.py tests/test_updater.py tests/test_version.py tests/test_ui_settings_persistence.py tests/test_main_window_shell_navigation.py -q` passes with 26 passed after the extended platform support QML slice
- a full `qmllint` scan across `src/ui_qml/**/*.qml` is clean after the extended platform support QML slice
- in `conda run -n pmenv`, platform persistence shape verification passes:
  - `pytest tests/test_platform_persistence_structure.py -q`
- in `conda run -n pmenv`, `pytest tests/test_platform_runtime_desktop_api.py tests/test_platform_runtime_http_api.py -q` passes
- in `conda run -n pmenv`, platform control desktop API and migrated widget verification passes:
  - `pytest tests/test_platform_control_desktop_api.py tests/test_phase_b_user_admin_ui.py tests/test_enterprise_pm_foundation.py tests/test_enterprise_rbac_matrix.py tests/test_qml_architecture_guardrails.py -q`
- in `conda run -n pmenv`, broader platform desktop API + shell regression verification passes:
  - `pytest tests/test_platform_admin_desktop_api.py tests/test_platform_control_desktop_api.py tests/test_platform_org_desktop_api.py tests/test_platform_runtime_desktop_api.py tests/test_document_admin_ui.py tests/test_phase_b_user_admin_ui.py tests/test_main_window_shell_navigation.py tests/test_qml_architecture_guardrails.py tests/test_architecture_guardrails.py -q`
- in `conda run -n pmenv`, operational runtime utility verification passes:
  - `pytest tests/test_operational_support.py tests/test_support_productization.py tests/test_updater.py tests/test_version.py tests/test_ui_settings_persistence.py tests/test_main_window_shell_navigation.py tests/test_architecture_guardrails.py::test_legacy_infra_platform_runtime_package_is_removed -q`
- in `conda run -n pmenv`, platform ORM/repository relocation verification passes:
  - `pytest tests/test_architecture_guardrails.py::test_composition_imports_focused_persistence_adapters tests/test_architecture_guardrails.py::test_orm_package_root_loads_all_model_packages tests/test_service_architecture.py tests/test_shared_master_data_exchange.py tests/test_shared_master_reuse_access.py tests/test_auth_module_phase_a.py tests/test_phase_b_session_permissions.py tests/test_phase_b_user_admin_ui.py tests/test_phase_b_audit_log.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_runtime_execution_tracking.py -q`
- in `conda run -n pmenv`, targeted architecture guardrail checks for the deleted platform DB facades and focused persistence imports pass
- in `conda run -n pmenv`, combined runtime-tracking/platform adapter verification passes:
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_db_facades_are_removed tests/test_architecture_guardrails.py::test_composition_imports_focused_persistence_adapters tests/test_platform_runtime_http_api.py tests/test_platform_runtime_desktop_api.py -q`
- in `conda run -n pmenv`, report-runtime verification passes:
  - `pytest tests/test_platform_import_export_report_runtime.py tests/test_runtime_execution_tracking.py tests/test_maintenance_runtime_contracts.py -q`
- in `conda run -n pmenv`, import/export runtime verification plus legacy-package removal guardrail passes:
  - `pytest tests/test_platform_import_export_report_runtime.py tests/test_runtime_execution_tracking.py tests/test_maintenance_runtime_contracts.py tests/test_architecture_guardrails.py::test_legacy_platform_import_export_packages_are_removed -q`
- in `conda run -n pmenv`, time-runtime verification plus legacy-package removal guardrail passes:
  - `pytest tests/test_shared_collaboration_import_and_timesheets.py tests/test_service_architecture.py tests/test_architecture_guardrails.py::test_legacy_platform_time_package_is_removed -q`
- in `conda run -n pmenv`, auth verification passes:
  - `pytest tests/test_auth_module_phase_a.py tests/test_auth_validation_and_query.py tests/test_authorization_engine.py tests/test_passwords.py tests/test_phase_b_session_permissions.py -q`
- in `conda run -n pmenv`, auth/platform integration verification passes:
  - `pytest tests/test_service_architecture.py tests/test_platform_access_scopes.py tests/test_architecture_guardrails.py::test_legacy_platform_auth_package_is_removed tests/test_architecture_guardrails.py::test_auth_service_is_orchestrator_only -q`
- in `conda run -n pmenv`, authorization verification plus legacy-package removal guardrail passes:
  - `pytest tests/test_authorization_engine.py tests/test_platform_access_scopes.py tests/test_auth_module_phase_a.py tests/test_architecture_guardrails.py::test_legacy_platform_authorization_package_is_removed -q`
- in `conda run -n pmenv`, access verification plus contract/legacy-package guardrails passes:
  - `pytest tests/test_auth_module_phase_a.py tests/test_authorization_engine.py tests/test_platform_access_scopes.py tests/test_service_architecture.py tests/test_architecture_guardrails.py::test_legacy_platform_access_package_is_removed tests/test_architecture_guardrails.py::test_platform_common_interfaces_are_platform_only -q`
- in `conda run -n pmenv`, modules verification plus legacy-package/orchestrator guardrails passes:
  - `pytest tests/test_enterprise_platform_catalog.py tests/test_platform_import_export_report_runtime.py tests/test_architecture_guardrails.py::test_legacy_platform_modules_package_is_removed tests/test_architecture_guardrails.py::test_module_catalog_service_is_orchestrator_only -q`
- in `conda run -n pmenv`, org verification plus contract/legacy-package guardrails passes:
  - `pytest tests/test_service_architecture.py tests/test_phase_b_user_admin_ui.py tests/test_platform_access_scopes.py tests/test_architecture_guardrails.py::test_legacy_platform_org_package_is_removed tests/test_architecture_guardrails.py::test_org_package_exports_services_and_contracts tests/test_architecture_guardrails.py::test_platform_common_interfaces_are_platform_only -q`
- in `conda run -n pmenv`, org maintenance integration verification passes:
  - `pytest tests/test_maintenance_foundation.py tests/test_maintenance_reliability_foundation.py tests/test_maintenance_preventive_foundation.py tests/test_maintenance_phase4_foundation.py tests/test_maintenance_execution_foundation.py tests/test_maintenance_sensor_foundation.py tests/test_maintenance_reliability_analytics.py tests/test_maintenance_integration_foundation.py -q`
- in `conda run -n pmenv`, party verification plus legacy-package guardrails passes:
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_party_package_is_removed tests/test_architecture_guardrails.py::test_party_package_exports_service_and_contracts tests/test_service_architecture.py -q`
- in `conda run -n pmenv`, party inventory/maintenance integration verification passes:
  - `pytest tests/test_inventory_import_export_reporting.py tests/test_inventory_maintenance_material_contracts.py tests/test_inventory_procurement_foundation.py tests/test_inventory_procurement_requisition.py tests/test_inventory_procurement_purchasing.py tests/test_inventory_procurement_scaffold.py tests/test_inventory_procurement_ui.py tests/test_maintenance_foundation.py tests/test_code_generation_ui.py -q`
- in `conda run -n pmenv`, approval verification plus contract/legacy-package guardrails passes:
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_approval_package_is_removed tests/test_architecture_guardrails.py::test_approval_package_exports_service_and_contracts tests/test_architecture_guardrails.py::test_platform_common_interfaces_are_platform_only tests/test_service_architecture.py tests/test_governance_tab_mode_toggle_ui.py tests/test_phase_b_approval_workflow.py tests/test_phase_b_session_permissions.py tests/test_phase_b_user_admin_ui.py tests/test_phase_b_audit_log.py tests/test_domain_event_wiring.py -q`
- in `conda run -n pmenv`, approval procurement integration verification passes:
  - `pytest tests/test_inventory_procurement_requisition.py tests/test_inventory_procurement_purchasing.py tests/test_inventory_import_export_reporting.py tests/test_inventory_procurement_ui.py -q`
- in `conda run -n pmenv`, documents verification plus contract/legacy-package guardrails passes:
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_documents_package_is_removed tests/test_architecture_guardrails.py::test_documents_package_exports_services_and_contracts tests/test_service_architecture.py tests/test_document_admin_ui.py -q`
- in `conda run -n pmenv`, documents integration verification passes:
  - `pytest tests/test_inventory_procurement_foundation.py tests/test_inventory_procurement_ui.py tests/test_maintenance_foundation.py tests/test_shared_collaboration_import_and_timesheets.py -q`
- in `conda run -n pmenv`, notifications verification plus legacy-package/event-hub guardrails passes:
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_notifications_package_is_removed tests/test_architecture_guardrails.py::test_notifications_package_exports_event_hub tests/test_domain_events.py tests/test_domain_event_wiring.py -q`
- in `conda run -n pmenv`, notifications cross-module sweep passes:
  - `pytest tests/test_dashboard_leveling_flow.py tests/test_project_management_platform_alignment.py tests/test_phase2_register_import_and_ui.py tests/test_inventory_maintenance_material_contracts.py tests/test_maintenance_foundation.py tests/test_maintenance_execution_foundation.py tests/test_service_architecture.py -q`
- in `conda run -n pmenv`, audit verification plus contract/legacy-package guardrails passes:
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_audit_package_is_removed tests/test_architecture_guardrails.py::test_audit_package_exports_service_and_contracts tests/test_architecture_guardrails.py::test_platform_common_interfaces_are_platform_only tests/test_service_architecture.py tests/test_phase_b_audit_log.py tests/test_phase_b_user_admin_ui.py tests/test_domain_event_wiring.py -q`
- in `conda run -n pmenv`, audit cross-module sweep passes:
  - `pytest tests/test_inventory_procurement_foundation.py tests/test_inventory_procurement_ui.py tests/test_maintenance_foundation.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_phase2_register_import_and_ui.py tests/test_maintenance_execution_foundation.py -q`
- in `conda run -n pmenv`, common/data-exchange/settings guardrails pass:
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_common_package_is_removed tests/test_architecture_guardrails.py::test_legacy_platform_data_exchange_package_is_removed tests/test_architecture_guardrails.py::test_common_package_exports_shared_utilities tests/test_architecture_guardrails.py::test_data_exchange_package_exports_service tests/test_architecture_guardrails.py::test_platform_common_interfaces_are_platform_only tests/test_architecture_guardrails.py::test_legacy_platform_settings_ui_package_is_removed tests/test_architecture_guardrails.py::test_platform_settings_package_exports_store -q`
- in `conda run -n pmenv`, service graph, shared master-data exchange, settings persistence, shell navigation, and governance UI verification pass:
  - `pytest tests/test_service_architecture.py tests/test_shared_master_data_exchange.py tests/test_shared_master_reuse_access.py tests/test_ui_settings_persistence.py tests/test_main_window_shell_navigation.py tests/test_governance_tab_mode_toggle_ui.py -q`
- in `conda run -n pmenv`, cross-module verification after the common/data-exchange/settings cutovers passes:
  - `pytest tests/test_shared_collaboration_import_and_timesheets.py tests/test_inventory_import_export_reporting.py tests/test_maintenance_foundation.py -q`
- in `conda run -n pmenv`, shared UI guardrails and focused shared/runtime UI tests pass:
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_shared_ui_package_is_removed tests/test_architecture_guardrails.py::test_shared_dialogs_package_exports_dialog_helpers tests/test_architecture_guardrails.py::test_shared_formatting_package_exports_theme_and_ui_config tests/test_architecture_guardrails.py::test_shared_models_package_exports_runtime_helpers tests/test_architecture_guardrails.py::test_shared_widgets_package_exports_widget_helpers tests/test_async_job_runtime.py tests/test_code_generation_ui.py tests/test_ui_rbac_matrix_and_guards.py -q`
- in `conda run -n pmenv`, shared formatting and shell/UI regression verification pass:
  - `pytest tests/test_refactor_regressions.py tests/test_pro_set_v1_ui.py tests/test_dashboard_professional_panels.py tests/test_inventory_procurement_ui.py tests/test_main_window_shell_navigation.py tests/test_phase_b_user_admin_ui.py -q`
- in `conda run -n pmenv`, control workspace guardrails and approval/audit regressions pass:
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_control_ui_package_is_removed tests/test_architecture_guardrails.py::test_platform_control_workspace_package_exports_tabs tests/test_phase_b_user_admin_ui.py tests/test_inventory_procurement_purchasing.py tests/test_governance_tab_mode_toggle_ui.py -q`
- in `conda run -n pmenv`, admin workspace/dialog/widget guardrails and admin UI regressions pass:
  - `pytest tests/test_architecture_guardrails.py::test_legacy_platform_admin_ui_package_is_removed tests/test_architecture_guardrails.py::test_platform_admin_workspace_package_exports_tabs tests/test_architecture_guardrails.py::test_platform_widgets_package_exports_admin_helpers tests/test_architecture_guardrails.py::test_platform_dialogs_package_exports_admin_and_document_dialogs tests/test_document_admin_ui.py tests/test_phase_b_user_admin_ui.py tests/test_tab_surface_consistency.py tests/test_code_generation_ui.py -q`
- in `conda run -n pmenv`, admin cross-module regressions pass:
  - `pytest tests/test_enterprise_pm_foundation.py tests/test_enterprise_rbac_matrix.py tests/test_maintenance_foundation.py tests/test_maintenance_execution_foundation.py -q`
- in `conda run -n pmenv`, ORM ownership guardrails pass:
  - `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_architecture_guardrails.py::test_inventory_persistence_imports_inventory_orm_models tests/test_architecture_guardrails.py::test_orm_package_root_loads_all_model_packages -q`
- in `conda run -n pmenv`, PM/inventory ORM regression verification passes:
  - `pytest tests/test_service_architecture.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_inventory_import_export_reporting.py tests/test_inventory_procurement_foundation.py tests/test_project_management_platform_alignment.py tests/test_collaboration_import_timesheet_regressions.py -q`
- in `conda run -n pmenv`, full architecture guardrails originally failed only on an existing project-management size budget; this was resolved during the Slice 2 PM domain package-root cleanup:
  - `pytest tests/test_architecture_guardrails.py -q`
  - latest observed result after the PM risk register-domain split: 94 passed
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
- module-owned ORM rows under `src/infra/persistence/orm/inventory_procurement` and `maintenance` remain transitional and must move to each module's `infrastructure/persistence/orm/` package during its slice
- the default interpreter used outside `pmenv` is still blocked on `reportlab` for full app/test imports because the environment dependency is not installed there

Still remaining in Slice 1:

- update test path strategy and remove `tests/path_rewrites.py` only after all required callers are on the new paths

Resolved verification note:

- `conda run -n pmenv pytest tests/test_architecture_guardrails.py -q` now passes after the Slice 2 PM domain package-root cleanup removed the old duplicated task definitions from `core/modules/project_management/domain/__init__.py`

### Slice 2: Project Management

Goal: complete the full project management slice before moving to the next module.

#### Exact changes

| Current path | Target path | Change |
| --- | --- | --- |
| `core/modules/project_management/domain/*` | `src/core/modules/project_management/domain/projects/*`, `tasks/*`, `scheduling/*`, `resources/*`, `risk/*`, `financials/*` | split the current flat domain by subdomain |
| `core/modules/project_management/services/project/*` | `src/core/modules/project_management/application/projects/commands/*` and `queries/*` | map project lifecycle/query services |
| `core/modules/project_management/services/task/*` | `src/core/modules/project_management/application/tasks/commands/*` and `queries/*` | map task workflows |
| `core/modules/project_management/services/scheduling/*`, `services/calendar/*`, `services/work_calendar/*`, `services/baseline/*` | `src/core/modules/project_management/application/scheduling/*` and `domain/scheduling/*` | fold schedule, calendar, and baseline logic into scheduling |
| `core/modules/project_management/services/resource/*` | `src/core/modules/project_management/application/resources/*` | move resource allocation/query logic |
| `core/modules/project_management/services/cost/*` and `services/finance/*` | `src/core/modules/project_management/application/financials/*` and `domain/financials/*` | fold cost/finance into financials |
| deleted legacy `core/modules/project_management/interfaces.py` | `src/core/modules/project_management/contracts/repositories/{project,task,resource,cost_calendar,baseline,register,collaboration,portfolio}.py` | completed repository contract split; no gateway contracts existed in the source file |
| `infra/modules/project_management/db/*` | `src/core/modules/project_management/infrastructure/persistence/repositories/*` and `mappers/*` | move PM repositories/mappers/read models under module infrastructure |
| `core/modules/project_management/reporting/renderers/*` and reporting services | `src/core/modules/project_management/infrastructure/reporting/*` | reporting adapters move into infrastructure |
| none | `src/core/modules/project_management/api/desktop/*.py` and `api/http/*.py` | create module-local desktop adapters and HTTP routers |
| `ui/modules/project_management/*` and active legacy `src/ui/modules/project_management/*` Widget screens | `src/ui_qml/modules/project_management/qml/workspaces/{projects,tasks,scheduling,resources,financials,risk,portfolio,register,collaboration,timesheets,dashboard}/*`, `qml/dialogs/*`, `qml/widgets/*`, `presenters/*`, `view_models/*` | migrate PM desktop UI from QWidget screens to QML, presenters, and view models |
| `ui/platform/shell/project_management/workspaces.py` | shell adapter only | shell registration becomes a thin adapter over the new PM UI workspaces |
| flat PM tests under `tests/` | `src/tests/project_management/*` | regroup PM tests under target test tree |

#### Detailed guide rules for Project Management

- break the scheduling engine into smaller files for:
  - graph builder
  - forward pass
  - backward pass
  - critical path
  - calendars
  - baseline comparison
- keep project, task, scheduling, resource, and finance use cases split into dedicated command and query handlers

#### Current PM features that are live but not explicitly named in the uploaded PM tree

- `portfolio`
- `register`
- `collaboration`
- `timesheet`
- `import_service`
- dashboard coordinator helpers

Safe handling:

- `dashboard` and `reporting` map into application queries plus infrastructure read models/reporting adapters
- `baseline` and `calendar` map into `scheduling`
- `cost` and `finance` map into `financials`
- `timesheet` now lands in `application/resources/` while shared entry and period workflows remain platform-time-owned
- import workflows now land in `infrastructure/importers/` on top of the platform import runtime

#### Slice 2 execution status

Updated: 2026-04-29

Hold status:

- Slice 2 project-management restructuring is paused as of 2026-04-22 for the QML UI migration pivot
- Slice 2 should now resume with the repo-structure transfer as the active track; QML is part of Slice 2 but must follow the new structure instead of blocking it
- continue PM domain/application/infrastructure/API moves first, then let QML attach naturally to the new module-local structure
- completed Slice 2 backend/domain work remains valid and should not be reverted
- active QWidget UI under `src/ui/*` remains runnable until each QML screen is complete and tested
- final PM desktop UI target is now `src/ui_qml/modules/project_management/*`, not `src/ui/modules/project_management/*`
- QML shell foundation has started and is verified independently; that work remains valid, but it is no longer the reason to hold backend/domain restructuring
- the platform-first QML checkpoint now has a routed shell host, grouped platform admin/control/settings overviews, a real QML approval/audit control surface, and a real QML module-entitlement/runtime-settings surface, all backed by split platform desktop APIs; full workflow parity and QWidget deletion still remain pending
- PM QML landing-zone routes are now in place for every Slice 2 PM workspace, with typed controller/catalog scaffolding and shared placeholder-page structure; keep that progress, but do not let it replace the remaining structure transfer work
- PM QML presenter/view-model scaffolding is in place for every PM workspace route, and the dashboard now has a typed controller plus split page sections backed by a screen-specific desktop API snapshot that includes analysis panels and chart state; that UI progress remains valid and should not be reverted
- PM QML now consumes presenter-backed metadata through a typed QML catalog/controller surface; outside the dashboard, workflow/query API wiring still needs to come from the refactored module structure first
- PM QML should now be incorporated naturally as each backend/application/API slice settles, not treated as the sole active Slice 2 track
- QML architecture guardrails are now in place before real screen migration begins
- registered QML routes are now covered by an automated offscreen loading smoke test
- PM Dashboard QML now renders API-backed project selection, baseline selection, KPI cards, EVM/register/cost analysis panels, burndown/resource visuals, and read-only delivery-health sections through a typed controller and split section layout; dialogs, mutations, and deeper dashboard parity remain on the QWidget dashboard until parity is completed

Refactor-first priority for the remaining PM slice:

- keep the completed legacy PM service-transfer set under `src/core/modules/project_management/{application,infrastructure}/*` clean and facade-free, with `timesheet` now settled under `application/resources` and `import_service` under `infrastructure/importers`
- keep dashboard/reporting reads infrastructure-owned on `src/core/modules/project_management/infrastructure/reporting/*` and keep the new PM service boundaries stable while API and UI regrouping continues
- expand module-local PM desktop and HTTP APIs over those application handlers, not over legacy broad services
- regroup PM tests under `src/tests/project_management/*`
- keep QML migration attached to those refactored module-local APIs and packages instead of using it to drive slice ordering

Completed in the clean/no-facade execution:

- moved `core/modules/project_management/services/project/service.py` into `src/core/modules/project_management/application/projects/service.py`
- moved `core/modules/project_management/services/project/lifecycle.py` into `src/core/modules/project_management/application/projects/commands/lifecycle.py`
- moved `core/modules/project_management/services/project/validation.py` into `src/core/modules/project_management/application/projects/commands/validation.py`
- moved `core/modules/project_management/services/project/query.py` into `src/core/modules/project_management/application/projects/queries/project_query.py`
- moved `core/modules/project_management/services/project/resource_service.py` into `src/core/modules/project_management/application/resources/project_resource_service.py`, split across `commands/project_resource_commands.py` and `queries/project_resource_queries.py`
- rewired PM composition, PM desktop APIs, dashboard/import helpers, legacy PM Widget callers, path rewrites, and architecture tests to import `ProjectService` from `src.core.modules.project_management.application.projects` and `ProjectResourceService` from `src.core.modules.project_management.application.resources`
- deleted the old source files under `core/modules/project_management/services/project/` after callers were rewritten; no facade re-export package was left behind
- moved `core/modules/project_management/services/task/service.py` into `src/core/modules/project_management/application/tasks/service.py`
- moved `core/modules/project_management/services/task/lifecycle.py`, `assignment.py`, `assignment_audit.py`, `assignment_bridge.py`, `dependency.py`, `schedule_sync.py`, `time_entries.py`, and `validation.py` into `src/core/modules/project_management/application/tasks/commands/*`
- moved `core/modules/project_management/services/task/query.py` and `dependency_diagnostics.py` into `src/core/modules/project_management/application/tasks/queries/*`
- rewired PM composition, PM desktop/platform APIs, dashboard/import helpers, PM Widget callers, dependency-impact UI imports, path rewrites, and architecture tests to import `TaskService` from `src.core.modules.project_management.application.tasks`
- deleted the old source files under `core/modules/project_management/services/task/` after callers were rewritten; no facade re-export package was left behind
- moved `core/modules/project_management/services/scheduling/date_compute.py`, `engine.py`, `graph.py`, `leveling.py`, `leveling_models.py`, `leveling_service.py`, `models.py`, `passes.py`, and `results.py` into `src/core/modules/project_management/application/scheduling/*`
- moved `core/modules/project_management/services/calendar/service.py` into `src/core/modules/project_management/application/scheduling/calendar_service.py`
- moved `core/modules/project_management/services/work_calendar/engine.py` and `service.py` into `src/core/modules/project_management/application/scheduling/work_calendar_{engine,service}.py`
- rewired PM composition, baseline/reporting/dashboard services, PM calendar/dashboard QWidget callers, path rewrites, and architecture tests to import scheduling, calendar, and work-calendar types from `src.core.modules.project_management.application.scheduling`
- deleted the old source files and legacy package roots under `core/modules/project_management/services/{scheduling,calendar,work_calendar}/` after callers were rewritten; no facade re-export package was left behind
- moved `core/modules/project_management/services/resource/service.py` into `src/core/modules/project_management/application/resources/resource_service.py` and split the live workflow into `commands/resource_commands.py` plus `queries/resource_queries.py`
- moved `core/modules/project_management/services/cost/service.py` into `src/core/modules/project_management/application/financials/cost_service.py`, with `lifecycle.py`, `query.py`, and `support.py` landing in `commands/cost_lifecycle.py`, `queries/cost_query.py`, and `cost_support.py`
- moved `core/modules/project_management/services/finance/{service,analytics,cashflow,helpers,ledger,models,policy}.py` into `src/core/modules/project_management/application/financials/*`
- rewired PM composition, import support, reporting/export surfaces, platform desktop audit support, PM cost/resource/report/task/project QWidget callers, path rewrites, and architecture tests to import `ResourceService`, `CostService`, `FinanceService`, and finance models from `src.core.modules.project_management.application.{resources,financials}`
- deleted the old source files and legacy package roots under `core/modules/project_management/services/{resource,cost,finance}/` after callers were rewritten; no facade re-export package was left behind
- moved `core/modules/project_management/services/register/service.py` into `src/core/modules/project_management/application/risk/register_service.py`, with `lifecycle.py`, `query.py`, and `models.py` landing in `commands/register_lifecycle.py`, `queries/register_query.py`, and `dto/register_summary.py`
- rewired PM composition, dashboard services, PM desktop dashboard APIs, PM register QWidget callers, path rewrites, and architecture tests to import `RegisterService` and register summary DTOs from `src.core.modules.project_management.application.risk`
- deleted the old source files and legacy package root under `core/modules/project_management/services/register/` after callers were rewritten; no facade re-export package was left behind
- moved `core/modules/project_management/services/reporting/{baseline_compare,cost_breakdown,cost_policy,evm,evm_core,evm_series,kpi,labor,models,service,variance}.py` into `src/core/modules/project_management/infrastructure/reporting/*`
- rewired PM composition, financial services, reporting/export adapters, dashboard services, PM cost/project/report QWidget callers, dashboard alert rendering, path rewrites, and architecture tests to import reporting services and models from `src.core.modules.project_management.infrastructure.reporting`
- deleted the old source files and legacy package root under `core/modules/project_management/services/reporting/` after callers were rewritten; no facade re-export package was left behind
- moved `core/modules/project_management/services/baseline/service.py` into `src/core/modules/project_management/application/scheduling/baseline_service.py`
- rewired PM composition, PM desktop APIs, platform audit support, dashboard QWidget callers, path rewrites, and architecture tests to import `BaselineService` from the new scheduling module-local path
- flattened scheduling imports inside the reporting infrastructure onto concrete scheduling modules so the scheduling/reporting import graph stays acyclic after the baseline transfer
- deleted the old source file and legacy package root under `core/modules/project_management/services/baseline/` after callers were rewritten; no facade re-export package was left behind
- moved `core/modules/project_management/services/dashboard/{service,alerts,upcoming,burndown,evm,register,portfolio,professional,models,portfolio_models}.py` into `src/core/modules/project_management/application/dashboard/*`
- rewired PM composition, desktop runtime/dashboard APIs, dashboard QWidget callers, dashboard desktop snapshot builders, path rewrites, and architecture tests to import `DashboardService`, `DashboardData`, and `PORTFOLIO_SCOPE_ID` from `src.core.modules.project_management.application.dashboard`
- deleted the old source files and legacy package root under `core/modules/project_management/services/dashboard/` after callers were rewritten; no facade re-export package was left behind
- moved `core/modules/project_management/services/collaboration/{service,comments,documents,inbox,mentions,notifications,presence,principal,support}.py` into `src/core/modules/project_management/application/tasks/{collaboration_service.py,collaboration_mentions.py,collaboration_principal.py,collaboration_support.py,commands/*,queries/*}`
- rewired PM composition, PM task/collaboration QWidget callers, path rewrites, and architecture/service tests to import `CollaborationService` from `src.core.modules.project_management.application.tasks`
- deleted the old source files and legacy package root under `core/modules/project_management/services/collaboration/` after callers were rewritten; no facade re-export package was left behind
- moved `core/modules/project_management/services/portfolio/{service,dependencies,executive,intake,scenarios,support,templates}.py` into `src/core/modules/project_management/application/projects/{portfolio_service.py,portfolio_support.py,commands/*,queries/*}`
- rewired PM composition, PM portfolio QWidget callers, path rewrites, and architecture/service tests to import `PortfolioService` from `src.core.modules.project_management.application.projects`
- deleted the old source files and legacy package root under `core/modules/project_management/services/portfolio/` after callers were rewritten; no facade re-export package was left behind
- moved the PM timesheet wrapper from `core/modules/project_management/services/timesheet/*` into `src/core/modules/project_management/application/resources/timesheet_service.py`, keeping shared time-entry and timesheet-period workflows owned by `src.core.platform.time`
- rewired PM composition, PM task/governance/timesheet QWidget callers, task application time-entry commands, path rewrites, and architecture/service tests to import `TimesheetService` from `src.core.modules.project_management.application.resources`
- deleted the old source files and legacy package root under `core/modules/project_management/services/timesheet/` after callers were rewritten; no facade re-export package was left behind
- moved `core/modules/project_management/services/import_service/{service,execution,preview,support,models,schemas}.py` and `core/modules/project_management/importing/definitions.py` into `src/core/modules/project_management/infrastructure/importers/*`
- rewired PM composition, PM project/import QWidget callers, path rewrites, and architecture/service tests to import `DataImportService` from `src.core.modules.project_management.infrastructure.importers`
- deleted the old source files and legacy package roots under `core/modules/project_management/services/import_service/` and `core/modules/project_management/importing/` after callers were rewritten; no facade re-export package was left behind
- moved PM ORM rows from `src/infra/persistence/orm/project_management/*` into `src/core/modules/project_management/infrastructure/persistence/orm/*`
- rewired PM persistence adapters, collaboration storage, metadata loading, and architecture guardrails to split feature ORM files under `src.core.modules.project_management.infrastructure.persistence.orm.*`
- deleted the old global `src/infra/persistence/orm/project_management/` package after callers were rewritten
- split the PM ORM monolith by deleting `src/core/modules/project_management/infrastructure/persistence/orm/models.py` and moving rows into:
  - `project.py`
  - `resource.py`
  - `task.py`
  - `cost_calendar.py`
  - `baseline.py`
  - `register.py`
  - `collaboration.py`
  - `portfolio.py`
- moved PM repository implementations from `infra/modules/project_management/db/*/repository.py` into `src/core/modules/project_management/infrastructure/persistence/repositories/*.py`
- moved PM mapper implementations from `infra/modules/project_management/db/*/mapper.py` into `src/core/modules/project_management/infrastructure/persistence/mappers/*.py`
- rewired composition, PM persistence internals, test path rewrites, refactor regressions, and architecture guardrails to the new PM infrastructure imports
- deleted the old `infra/modules/project_management/db/` package after callers were rewritten
- removed the old PM timesheet/task-timesheet bridge files instead of carrying facade re-exports forward; platform time persistence remains owned by `src/core/platform/infrastructure/persistence/time/`
- split PM repository contracts from `core/modules/project_management/interfaces.py` into `src/core/modules/project_management/contracts/repositories/{project,task,resource,cost_calendar,baseline,register,collaboration,portfolio}.py`
- rewired PM services and PM persistence adapters to import the specific repository contract modules directly
- deleted the old `core/modules/project_management/interfaces.py` file after callers were rewritten
- kept `contracts/gateways/` empty for this pass because the deleted source file contained repository contracts only, not gateway contracts
- moved `Project` and `ProjectResource` from `core/modules/project_management/domain/project.py` into `src/core/modules/project_management/domain/projects/project.py`
- rewired PM services, PM persistence, contract, and UI callers to import the project domain model from the new subdomain file directly
- deleted the old flat `core/modules/project_management/domain/project.py` file after callers were rewritten
- reduced `core/modules/project_management/domain/__init__.py` to a package docstring because no callers import PM domain objects from the package root
- moved `Task`, `TaskAssignment`, and `TaskDependency` from `core/modules/project_management/domain/task.py` into `src/core/modules/project_management/domain/tasks/task.py`
- rewired PM task, scheduling, calendar, reporting, persistence, contract, UI, and focused test callers to import the task domain model from the new subdomain file directly
- deleted the old flat `core/modules/project_management/domain/task.py` file after callers were rewritten
- removed the obsolete PM task-domain re-export of platform timesheet objects; platform time domain objects remain owned by `src/core/platform/time/domain/`
- moved `Resource` from `core/modules/project_management/domain/resource.py` into `src/core/modules/project_management/domain/resources/resource.py`
- rewired PM resource service, resource persistence, resource contract, resource UI, task assignment UI, and labor-cost UI callers to import the resource domain model from the new subdomain file directly
- deleted the old flat `core/modules/project_management/domain/resource.py` file after callers were rewritten
- moved `CostItem` from `core/modules/project_management/domain/cost.py` into `src/core/modules/project_management/domain/financials/cost.py`
- rewired PM cost services, cost persistence, cost/calendar contract, and cost UI callers to import the cost domain model from the new financials subdomain file directly
- deleted the old flat `core/modules/project_management/domain/cost.py` file after callers were rewritten
- moved `CalendarEvent`, `WorkingCalendar`, and `Holiday` from `core/modules/project_management/domain/calendar.py` into `src/core/modules/project_management/domain/scheduling/calendar.py`
- rewired PM calendar services, work-calendar services, cost/calendar persistence, and cost/calendar contract callers to import the calendar domain model from the new scheduling subdomain file directly
- deleted the old flat `core/modules/project_management/domain/calendar.py` file after callers were rewritten
- moved `ProjectBaseline` and `BaselineTask` from `core/modules/project_management/domain/baseline.py` into `src/core/modules/project_management/domain/scheduling/baseline.py`
- rewired PM baseline service, baseline reporting, baseline persistence, and baseline contract callers to import the baseline domain model from the new scheduling subdomain file directly
- deleted the old flat `core/modules/project_management/domain/baseline.py` file after callers were rewritten
- moved `RegisterEntry`, register enums, and register enum normalizers from `core/modules/project_management/domain/register.py` into `src/core/modules/project_management/domain/risk/register.py`
- rewired PM register services, register persistence, register ORM enum usage, register contract, register UI, dashboard register rendering, and focused tests to import the register domain model from the new risk subdomain file directly
- deleted the old flat `core/modules/project_management/domain/register.py` file after callers were rewritten

Verified:

- `python -m compileall -q src infra ui core tests main.py main_qt.py main_qt.spec` passes
- direct metadata smoke import confirms `ProjectORM`, `TaskORM`, `ResourceORM`, `ProjectBaselineORM`, `TaskCommentORM`, and `PortfolioScenarioORM` load from split PM ORM files and remain registered in `Base.metadata`
- direct import smoke confirms PM repositories load from `src.core.modules.project_management.infrastructure.persistence.repositories.*`
- direct import smoke confirms PM repository contracts load from `src.core.modules.project_management.contracts.repositories.*`
- direct import smoke confirms `Project` and `ProjectResource` load from `src.core.modules.project_management.domain.projects.project`
- direct import smoke confirms `Task`, `TaskAssignment`, and `TaskDependency` load from `src.core.modules.project_management.domain.tasks.task`
- direct import smoke confirms `Resource` loads from `src.core.modules.project_management.domain.resources.resource`
- direct import smoke confirms `CostItem` loads from `src.core.modules.project_management.domain.financials.cost`
- direct import smoke confirms `CalendarEvent`, `WorkingCalendar`, and `Holiday` load from `src.core.modules.project_management.domain.scheduling.calendar`
- direct import smoke confirms `ProjectBaseline` and `BaselineTask` load from `src.core.modules.project_management.domain.scheduling.baseline`
- direct import smoke confirms `RegisterEntry`, `RegisterEntryType`, and `RegisterEntrySeverity` load from `src.core.modules.project_management.domain.risk.register`
- in `conda run -n pmenv`, PM persistence relocation verification passes:
  - `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_architecture_guardrails.py::test_composition_imports_focused_persistence_adapters tests/test_architecture_guardrails.py::test_orm_package_root_loads_all_model_packages tests/test_service_architecture.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_project_management_platform_alignment.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py -q`
- in `conda run -n pmenv`, PM ORM split verification passes:
  - `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_architecture_guardrails.py::test_orm_package_root_loads_all_model_packages tests/test_service_architecture.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_project_management_platform_alignment.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py -q`
- in `conda run -n pmenv`, PM contract split verification passes:
  - `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py -q`
  - observed result after the PM contract split: 65 passed
- in `conda run -n pmenv`, PM project-domain split verification passes:
  - `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_enterprise_pm_foundation.py tests/test_phase_b_user_admin_ui.py -q`
  - observed result after the PM project-domain split: 112 passed
- in `conda run -n pmenv`, PM task-domain split verification passes:
  - `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_enterprise_pm_foundation.py tests/test_phase_b_user_admin_ui.py tests/test_task_dependency_ux_logic.py tests/test_cpm_flow.py tests/test_resource_leveling_workflow.py tests/test_progress_flow.py -q`
  - observed result after the PM task-domain split: 126 passed
- in `conda run -n pmenv`, PM resource-domain split verification passes:
  - `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_enterprise_pm_foundation.py tests/test_phase_b_user_admin_ui.py tests/test_resource_leveling_workflow.py tests/test_finance_layer_integration.py tests/test_ui_professional_filters.py -q`
  - observed result after the PM resource-domain split: 123 passed
- in `conda run -n pmenv`, PM financial cost-domain split verification passes:
  - `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_finance_layer_integration.py tests/test_currency_defaults.py tests/test_large_scale_performance.py tests/test_exporters_configuration.py tests/test_technical_math_reporting.py tests/test_ui_professional_filters.py -q`
  - observed result after the PM financial cost-domain split: 95 passed, 1 skipped
- in `conda run -n pmenv`, PM scheduling calendar-domain split verification passes:
  - `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_cpm_flow.py tests/test_resource_leveling_workflow.py tests/test_technical_math_reporting.py tests/test_large_scale_performance.py -q`
  - observed result after the PM scheduling calendar-domain split: 81 passed, 1 skipped
- in `conda run -n pmenv`, PM scheduling baseline-domain split verification passes:
  - `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_baseline_comparison_workflow.py tests/test_business_rules_and_edge_cases.py tests/test_domain_event_wiring.py tests/test_technical_math_reporting.py tests/test_exporters_configuration.py -q`
  - observed result after the PM scheduling baseline-domain split: 125 passed
- in `conda run -n pmenv`, PM risk register-domain split verification passes:
  - `pytest tests/test_architecture_guardrails.py::test_project_management_persistence_imports_project_management_orm_models tests/test_architecture_guardrails.py::test_orm_package_root_loads_all_model_packages tests/test_service_architecture.py tests/test_project_management_platform_alignment.py tests/test_phase2_register_import_and_ui.py tests/test_dashboard_professional_panels.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py -q`
  - observed result after the PM risk register-domain split: 69 passed
- in `conda run -n pmenv`, full architecture guardrails pass:
  - `pytest tests/test_architecture_guardrails.py -q`
  - observed result after the PM risk register-domain split: 94 passed
- after the PM project/application transfer, focused verification passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py`
  - observed result after the PM project/application transfer: 107 passed
- after the PM task/application transfer, focused verification passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py tests/test_dashboard_professional_panels.py tests/test_task_dependency_ux_logic.py tests/test_progress_flow.py`
  - observed result after the PM task/application transfer: 121 passed
- after the PM scheduling/calendar/work-calendar application transfer, focused verification passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py tests/test_dashboard_professional_panels.py tests/test_task_dependency_ux_logic.py tests/test_progress_flow.py tests/test_cpm_flow.py tests/test_resource_leveling_workflow.py tests/test_baseline_comparison_workflow.py`
  - observed result after the PM scheduling/calendar/work-calendar application transfer: 133 passed
- after the PM resource/cost/finance application transfer, focused verification passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py tests/test_dashboard_professional_panels.py tests/test_task_dependency_ux_logic.py tests/test_progress_flow.py tests/test_cpm_flow.py tests/test_resource_leveling_workflow.py tests/test_baseline_comparison_workflow.py tests/test_finance_layer_integration.py tests/test_currency_defaults.py tests/test_technical_math_reporting.py tests/test_exporters_configuration.py tests/test_ui_professional_filters.py`
  - observed result after the PM resource/cost/finance application transfer: 165 passed
- after the PM risk/register application transfer plus the PM reporting infrastructure transfer, focused verification passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_phase2_register_import_and_ui.py tests/test_project_management_desktop_api.py tests/test_dashboard_professional_panels.py tests/test_project_management_platform_alignment.py tests/test_refactor_regressions.py tests/test_exporters_configuration.py tests/test_technical_math_reporting.py tests/test_ui_professional_filters.py`
  - observed result after the PM risk/register and reporting transfer: 184 passed
  - `conda run -n pmenv pytest -q tests/test_platform_import_export_report_runtime.py tests/test_cost_report_ui.py tests/test_dashboard_portfolio_flow.py`
  - observed result after the PM reporting runtime/report-UI regression batch: 15 passed
- after the PM baseline application transfer and scheduling/reporting import-cycle cleanup, focused verification passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py tests/test_dashboard_professional_panels.py tests/test_baseline_comparison_workflow.py tests/test_exporters_configuration.py tests/test_project_management_platform_alignment.py tests/test_platform_import_export_report_runtime.py`
  - observed result after the PM baseline transfer: 154 passed
- after the PM dashboard application transfer, focused verification passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py tests/test_dashboard_professional_panels.py tests/test_dashboard_portfolio_flow.py tests/test_dashboard_leveling_flow.py tests/test_project_management_platform_alignment.py tests/test_refactor_regressions.py tests/test_pro_set_v1_ui.py`
  - observed result after the PM dashboard transfer: 177 passed
- after the PM collaboration application transfer, focused verification passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_project_management_platform_alignment.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_task_mentions_pro.py`
  - observed result after the PM collaboration transfer: 174 passed
- after the PM portfolio application transfer, focused verification passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv pytest -q tests/test_service_architecture.py tests/test_architecture_guardrails.py tests/test_project_management_desktop_api.py tests/test_dashboard_portfolio_flow.py tests/test_enterprise_pm_foundation.py tests/test_project_management_platform_alignment.py tests/test_refactor_regressions.py tests/test_pro_set_v1_ui.py`
  - observed result after the PM portfolio transfer: 194 passed
- after the PM timesheet/import-service transfer, focused verification passes:
  - `python -m compileall -q src/core/modules/project_management src/infra/composition src/api core/modules/project_management ui/modules/project_management tests`
  - `conda run -n pmenv python -m pytest -q tests/test_architecture_guardrails.py tests/test_service_architecture.py tests/test_shared_collaboration_import_and_timesheets.py tests/test_project_management_platform_alignment.py tests/test_collaboration_import_timesheet_regressions.py tests/test_refactor_regressions.py tests/test_project_management_desktop_api.py`
  - observed result after the PM timesheet/import-service transfer: 181 passed

Still remaining in Slice 2:

- continue splitting PM domain, services, API adapters, and UI according to the Slice 2 plan before starting another module
- prioritize the remaining repo-structure transfer under `src/core/modules/project_management/{application,infrastructure,api}` before further QML-first expansion
- the legacy PM service-transfer set is now completed through `services/timesheet/*` and `services/import_service/*`; continue the PM API, test, and UI regrouping on top of the new module-local structure
- migrate PM UI screens to `src/ui_qml/modules/project_management/*` one workspace/dialog at a time against the refactored module-local APIs; delete old Widget files only after matching QML screens pass tests
- regroup PM tests from the flat `tests/` area into `src/tests/project_management/*` as the feature slices settle
- if real PM gateway boundaries appear during the application/API split, place those contracts under `src/core/modules/project_management/contracts/gateways/*` without facade re-exports

### Slice 3: Inventory & Procurement

Goal: complete inventory and procurement before maintenance, because maintenance consumes inventory-facing services today.

#### Exact changes

| Current path | Target path | Change |
| --- | --- | --- |
| `core/modules/inventory_procurement/domain.py` | `src/core/modules/inventory_procurement/domain/catalog/*`, `inventory/*`, `procurement/*`, `pricing/*` | split the current flat domain model |
| `services/item_master/*` | `src/core/modules/inventory_procurement/application/catalog/*` | map item/category workflows |
| `services/inventory/*` and `services/stock_control/*` | `src/core/modules/inventory_procurement/application/inventory/*` | fold stock control into inventory application layer |
| `services/procurement/*` | `src/core/modules/inventory_procurement/application/procurement/*` | move PR/PO/receiving workflows |
| `interfaces.py` | `src/core/modules/inventory_procurement/contracts/repositories/*` and `gateways/*` | split contracts |
| `infra/modules/inventory_procurement/db/*` | `src/core/modules/inventory_procurement/infrastructure/persistence/*` | move repositories/mappers/read models |
| inventory reporting helpers | `src/core/modules/inventory_procurement/infrastructure/reporting/*` | move reporting adapters |
| none | `src/core/modules/inventory_procurement/api/desktop/*.py` and `api/http/*.py` | create module-local desktop adapters and HTTP routers |
| `ui/modules/inventory_procurement/*` and active legacy `src/ui/modules/inventory_procurement/*` Widget screens | `src/ui_qml/modules/inventory_procurement/qml/workspaces/{catalog,inventory,procurement,pricing,dashboard,reservations}/*`, `qml/dialogs/*`, `qml/widgets/*`, `presenters/*`, `view_models/*` | migrate inventory UI from QWidget screens to QML, presenters, and view models |
| flat inventory tests under `tests/` | `src/tests/inventory_procurement/*` | regroup tests |

#### Detailed guide rules for Inventory & Procurement

- do not mix stock movement logic and purchase order logic in the same files
- keep `catalog`, `inventory`, `procurement`, and `pricing` as distinct subdomains

#### Current inventory features that are live but not explicitly named in the uploaded inventory tree

- `reservation`
- `data_exchange`
- `maintenance_integration`
- split `stock_control` UI/service package
- inventory reporting service helpers

Safe handling:

- `stock_control` folds into the `inventory` subdomain/application layer
- reporting moves into `infrastructure/reporting`
- reservations and maintenance integration must be assigned final homes before the inventory slice is closed
- data exchange stays temporarily attached to inventory as an integration adapter, not as a direct cross-module dependency

### Slice 4: Maintenance

Goal: rename `maintenance_management` to `maintenance` and complete the full maintenance slice after inventory is stable.

#### Exact changes

| Current path | Target path | Change |
| --- | --- | --- |
| `core/modules/maintenance_management/*` | `src/core/modules/maintenance/*` | rename the module package |
| current flat maintenance domain files | `src/core/modules/maintenance/domain/assets/*`, `locations/*`, `work_requests/*`, `work_orders/*`, `preventive/*`, `reliability/*`, `documents/*` | split by business subdomain |
| `services/asset/*`, `services/component/*` | `src/core/modules/maintenance/application/assets/*` | map asset workflows |
| `services/work_request/*` | `src/core/modules/maintenance/application/work_requests/*` | map request workflows |
| `services/work_order/*`, `services/work_order_task/*`, `services/work_order_task_step/*`, `services/material_requirement/*`, `services/labor/*` | `src/core/modules/maintenance/application/work_orders/*` | map work-order workflows |
| `services/preventive/*`, `services/preventive_plan/*`, `services/preventive_plan_task/*` | `src/core/modules/maintenance/application/preventive/*` | map preventive workflows |
| `services/reliability/*`, `services/sensor/*`, `services/sensor_reading/*`, `services/sensor_exception/*`, `services/failure_code/*`, `services/downtime_event/*` | `src/core/modules/maintenance/application/reliability/*` | map reliability workflows |
| `interfaces.py` | `src/core/modules/maintenance/contracts/repositories/*`, `gateways/*`, `events/*` | split contracts and events |
| `infra/modules/maintenance_management/db/*` | `src/core/modules/maintenance/infrastructure/persistence/*` | move repositories/mappers/read models |
| maintenance reporting/import/export helpers | `src/core/modules/maintenance/infrastructure/reporting/*`, `importers/*`, `exporters/*` | move adapters into target infrastructure layout |
| none | `src/core/modules/maintenance/api/desktop/*.py` and `api/http/*.py` | create module-local desktop adapters and HTTP routers |
| `ui/modules/maintenance_management/*` and active legacy `src/ui/modules/maintenance*/*` Widget screens | `src/ui_qml/modules/maintenance/qml/workspaces/{assets,work_requests,work_orders,preventive,reliability,dashboard,planner}/*`, `qml/dialogs/*`, `qml/widgets/*`, `presenters/*`, `view_models/*` | migrate maintenance UI from QWidget screens to QML, presenters, and view models |
| flat maintenance tests under `tests/` | `src/tests/maintenance/*` | regroup tests |

#### Current maintenance features that are live but not explicitly named in the uploaded maintenance tree

- planner workspace
- dashboard workspace
- task templates
- asset library and preventive library UI naming
- runtime contract catalog helpers

Safe handling:

- library-style UIs fold into `assets` and `preventive` workspaces
- planner and dashboard must be assigned final homes before the maintenance slice is closed
- runtime catalog helpers stay as adapters until the target runtime contract boundaries are finalized

### Slice 5: HR Management, Payroll, And QHSE Placeholders

Goal: make the repo shape match the uploaded structure without inventing business behavior that does not exist yet.

#### Exact changes

- create `src/core/modules/hr_management/`, `src/core/modules/payroll/`, and `src/core/modules/qhse/` package skeletons
- create module-local persistence skeletons under `src/core/modules/hr_management/infrastructure/persistence/`, `src/core/modules/payroll/infrastructure/persistence/`, and `src/core/modules/qhse/infrastructure/persistence/`; do not add new global module ORM row folders without real persistence behavior
- create matching registries under `src/infra/composition/hr_registry.py`, `payroll_registry.py`, and `qhse_registry.py`
- create matching API folders under `src/api/desktop/*` and `src/api/http/*`
- create matching QML UI folders under `src/ui_qml/modules/*`
- create matching test package folders under `src/tests/*`

#### Required placeholder subdomains from the detailed guide

HR Management:

- domain subfolders: `employees/`, `organization/`, `attendance/`, `performance/`, `training/`
- important ownership rule: HR owns employee master data; other modules use employee IDs or gateways

Payroll:

- domain subfolders: `payroll_runs/`, `earnings/`, `deductions/`, `employees/`, `compliance/`
- important ownership rule: payroll stays isolated from HR internals for permissions and calculation safety

QHSE:

- domain subfolders: `incidents/`, `inspections/`, `audits/`, `risks/`, `capa/`, `compliance/`
- important ownership rule: QHSE may reference asset IDs and employee IDs, but must not import maintenance or HR internals directly

These stay as placeholders until actual module behavior is implemented.

### Slice 6: Legacy Path Cleanup

Goal: remove any remaining legacy paths and verify the repo is clean after all hard cutovers are complete.

#### Exact changes

- delete any still-existing legacy root paths and transitional files
- retire `tests/path_rewrites.py`
- update architecture tests to ban old package imports
- remove duplicate shell/module registration code that only existed for the transition
- update root `README.md` to show the new `src/` tree after the refactor is complete

## Definition Of Done For Each Slice And Subphase

A slice or subphase is only complete when all of the following are true:

1. all callers have been moved to the new paths and the old paths for that slice have been removed
2. the desktop app starts and navigates normally
3. the module or platform slice has passed its targeted tests
4. architecture guard tests enforce the new dependency rules for that slice
5. no direct `ui -> repository` dependency is introduced
6. no module imports another module's internals directly

## What I Will Preserve During The Migration

To avoid breaking the functioning app, this plan assumes:

- root entrypoints remain available throughout the migration
- each slice lands as a full cutover with imports and wiring rewritten together
- module service bundles keep working while registries and app container paths are introduced
- shell navigation stays operational during the UI move
- migrations and database models keep the same runtime behavior while files are reorganized

## Working Decisions Captured In This README

This plan now assumes the following unless you later override them:

1. the global rollout order is `platform -> project_management -> inventory_procurement -> maintenance -> hr/payroll/qhse placeholders -> legacy cleanup`
2. features not explicitly named in the extracted module trees must be given final homes before their slice is considered complete
3. top-level `src/api/*` acts as the application transport layer, while module-local `core/modules/*/api/*` holds module-scoped desktop and HTTP adapters
4. HR becomes the owner of employee master data in the target architecture, while other modules interact through IDs and gateways
5. `src/infra/persistence/orm/` is a shared SQLAlchemy metadata/root loader, not the final home for module-owned ORM rows; module rows move to each module's `infrastructure/persistence/orm/` during its slice
6. platform persistence follows the module pattern under `src/core/platform/infrastructure/persistence/{orm,mappers,repositories}/`, not old per-service folders or the global ORM package
