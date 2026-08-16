# Platform QML — Existing-State UI/UX Reconstruction Audit

**Scope:** `src/ui_qml/platform/` (all 69 `.qml` files) plus every shared/shell dependency it pulls in.
**Purpose:** Read-only baseline for a future redesign. No code was modified to produce this document.
**Method:** Static analysis only — every claim below was verified by opening the cited file(s). No instance of the running app was required or used (see §2).

Legend used throughout: **Observed** = directly evident in code, cited `file:line`. **Inferred** = derived from tracing multiple files, not runtime-verified. **Unable to determine from static analysis.** = flagged explicitly rather than guessed.

All paths are relative to `C:\Users\ashu\Desktop\PersonalProjects\project_manager_Lite\` unless given in full.

---

## 1. Executive Summary

"Platform" is one of four top-level modules in this desktop ERP shell (alongside Project Management, Maintenance, Inventory & Procurement). It is reached from the shell's left navigation drawer and currently presents itself as **four separate top-level workspaces** — Admin Console, Control Center, Settings, and Tenant Management — each a standalone route with its own internal navigation, rather than one unified "Platform" screen with sub-tabs.

The codebase is disciplined about a few architectural rules (QML is a thin view, all business logic sits behind Python `PlatformWorkspaceControllerBase` subclasses; every mutation goes through a `run_mutation`/`serialize_operation_result` contract; every list is `DataTable` + `TableToolbar` + `TablePaginationBar`; every full-record view is `SectionDetailPage` + `ContextualActionToolbar`). At the same time, static analysis surfaced a number of **incomplete or inconsistent areas that materially affect what the current UI actually does**, the most important being:

- The Admin Console's right-hand inline detail/inspector panel (`AdminEntityDetailPanel`, 288px) is **hardcoded `visible: false`** (`AdminConsolePage.qml:902`) — fully built, fully wired, never shown. All entity inspection today happens through full-page detail views instead.
- Two Settings sections (**Platform Defaults**, **Security**) are **100% hardcoded static display data** with no controller binding at all — they look like configuration screens but change nothing and reflect nothing real.
- Two Control Center tabs (**Escalations**, **System Events**) are empty `DataTable`s with hardcoded `rows: []` and no backend wiring.
- Table pagination (`TablePaginationBar`) is **inert** for every Admin Console entity list, because those lists all bind a Python `DynamicTableModel`, and the pagination bar is explicitly hidden whenever that's the case (`AdminEntityWorkspace.qml:139`, comment: "server-side pagination pending").
- "Filter" and "Views" buttons that appear on nearly every list toolbar across Admin/Control/Settings open popups containing **only static placeholder text** ("Filters will appear here") — none are functional.
- Four QML components are registered but **provably dead code** (never imported/instantiated anywhere): `AdminCatalogPanel.qml`, `WorkspaceStateBanner.qml` (Platform's own copy), `MasterDetailLayout.qml`, `SettingsOverviewSections.qml`.
- The global header's "Global search," "Approvals," and "Notifications" affordances (`ShellHeader.qml`) are visual only — no click handlers, no backing data.
- There is no dark-mode implementation at the token layer: `AppTheme.qml` is a single fixed light palette; `themeMode` is tracked and displayed in Settings but never changes a single color.
- **Tenant** (a hosting/licensing container, switched via the global header pill or the dedicated Tenant Management workspace) and **Organization** (a business-entity master record managed inside Admin Console → Organizations) are two distinct concepts that share no visual vocabulary to distinguish them for a new user.

None of this is guessed — every item above is cited with file:line evidence in the relevant section below.

---

## 2. Scope and Method

- Every one of the 69 `.qml` files under `src/ui_qml/platform/` was opened and read.
- 25 of the 53 shared design-system QML files under `src/ui_qml/shared/qml/App/` were opened directly (the ones actually referenced by Platform code): `Theme/AppTheme.qml`, `Layouts/WorkspaceFrame.qml`, `Layouts/MasterDetailLayout.qml`, `Widgets/DataTable.qml`, `Widgets/EntityDialog.qml`, `Widgets/SectionDetailPage.qml`, `Widgets/ContextualActionToolbar.qml`, `Widgets/TableToolbar.qml`, `Widgets/TablePaginationBar.qml`, `Widgets/PageHeader.qml`, `Widgets/StatusChip.qml`, `Widgets/EmptyState.qml`, `Widgets/InlineMessage.qml`, `Widgets/KpiStrip.qml`, `Widgets/MetricCard.qml`, `Widgets/SectionCard.qml`, `Widgets/SectionHeading.qml`, `Widgets/CodeFieldRow.qml`, `Widgets/FormField.qml`, `Widgets/SectionScopedInlineMessage.qml`, `Widgets/LazySectionLoader.qml`, `Widgets/LazyObjectLoader.qml`, `Widgets/SectionNavigationRail.qml`, `Widgets/ActivityFeed.qml`, `Widgets/AnchoredPopup.qml`, plus representative `App.Controls` files (`CenteredDialog.qml`, `PrimaryButton.qml`, `SecondaryButton.qml`, `SearchField.qml`) and `Icons/AppIcon.qml`.
- All 9 shell Python files and 6 shell QML files were opened to trace startup → shell → navigation → Platform.
- ~30 Platform Python files were opened directly: both `context.py`/`routes.py`, the full `admin_console_controller.py`, `access_workspace_controller.py`, `support_workspace_controller.py`, `control_workspace_controller.py`, `settings_workspace_controller.py`, `tenant_switcher_controller.py`, the common layer (`workspace_controller_base.py`, `mutation_runner.py`, `serializers.py`, `admin_refresh_service.py`), a representative entity controller/presenter pair (`organization_controller.py` / `organization_catalog_presenter.py`), `admin_presenter.py`, all 3 view-model files, and the shared `data_table_model.py`. The remaining per-entity controllers (calendar/site/department/employee/user/party/document/document_structure) and presenters were confirmed, by opening `admin_console_controller.py`'s composition root, to follow the identical thin-wrapper construction pattern as `organization_controller.py` (same constructor signature, same `refresh()`/`create*`/`update*`/`toggle*Active` slot shape, same `run_mutation` usage) — this is called out explicitly wherever it is relied upon, tagged **Inferred (pattern-consistent)**.
- Static analysis was sufficient for every claim in this document. The app was **not launched** — with the login gate, database migrations, and multi-tenant runtime state involved, a safe read-only launch could not be guaranteed without risking state mutation, so per the task's instructions this was skipped in favor of exhaustive code reading.

---

## 3. Platform UI Entry Points

Trace, file:line cited at each hop:

1. **Process start** — `src/ui_qml/shell/app.py:main()` builds services, runs DB migrations (`run_migrations`, line 51), optionally shows `LoginWindow.qml` (`_prompt_for_login_qml`, lines 89–118), then builds the QML route registry (`build_qml_route_registry()`, line 149) which aggregates `build_shell_routes()` + `build_platform_routes()` + PM/Inventory/Maintenance routes (`qml_registry.py:38-47`).
2. **Shell context** — `build_shell_context(build_main_window_navigation(registry))` (`app.py:157`) creates a `ShellContext` (`shell/context.py:18`) holding `navigationItems`, `currentRouteId`, `currentRouteSource` (a `file://` URI resolved from the route's `qml_path`).
3. **Workspace catalogs** — `PlatformWorkspaceCatalog(...)` is constructed (`app.py:180-184`, class in `platform/context.py:44`) wiring every Platform controller (admin/access/support/control/settings/tenant-switcher) to its presenter(s) and the `desktop_api_registry`.
4. **QML engine load** — `create_qml_engine()` adds import roots `shared/qml`, `shell/qml`, `platform/qml`, and each `modules/*/qml` (`qml_engine.py:53-58`); `load_qml(engine, shell_route.qml_path, initial_properties={shellModel, platformCatalog, pmCatalog, inventoryCatalog, maintenanceCatalog})` loads **`shell/qml/App.qml`** (`app.py:226-239`).
5. **`App.qml`** (`shell/qml/App.qml:6-28`) — an `ApplicationWindow`, fixed initial `width: 1280, height: 800` (line 14-15), hosts `MainWindow { anchors.fill: parent }` passing through `shellModel` and all module catalogs.
6. **`MainWindow.qml`** (`shell/qml/MainWindow.qml:6-89`) — `ColumnLayout`: `ShellHeader` (top, full width) then a `RowLayout` of `ShellDrawer` (left nav) + 1px divider + a `Loader` (`workspaceLoader`, line 58-85) whose `source` is bound to `shellModel.currentRouteSource`. When the loaded item exposes `platformCatalog`/`pmCatalog`/etc. properties, `MainWindow` pushes them in (`onLoaded`, lines 65-84) — this is how every top-level workspace QML file (including all 4 Platform ones) receives its catalog.
7. **Clicking "Platform" in the drawer** — `ShellDrawer.qml` renders `shellModel.navigationItems` grouped by `moduleLabel` (lines 72-100), and Platform's 4 routes are registered with `module_label="Platform"` and distinct `group_label`s (`platform/routes.py:16-49`: `Administration`/`Control`/`Settings`/`Tenants`). Clicking any Platform row calls `shellModel.selectRoute(routeId)` (`ShellDrawer.qml:277`) → `ShellContext.selectRoute()` (`shell/context.py:89-110`) sets `currentRouteId`/`currentRouteSource` → `MainWindow`'s `Loader` swaps to the corresponding workspace QML.
8. **Platform workspace shell** — each of the 4 routes points at a top-level `*Workspace.qml` file which is a **one-line wrapper** delegating to a `*WorkspacePage.qml` (e.g. `workspaces/admin/AdminWorkspace.qml:3` is literally `AdminConsolePage {}`; same pattern for Control, Settings, Tenants — `AdminWorkspace.qml`, `ControlWorkspace.qml`, `SettingsWorkspace.qml`, `TenantManagementWorkspace.qml` are all pass-through shells). The actual page (`AdminConsolePage.qml`, `ControlWorkspacePage.qml`, `SettingsWorkspacePage.qml`, `TenantManagementWorkspacePage.qml`) is where all real layout/behavior lives.
9. **Platform-local navigation** — described fully in §7.
10. **Selected page content** — described in §10+.

---

## 4. Current Folder Structure (annotated)

```
src/ui_qml/platform/
├── __init__.py
├── context.py                          Builds PlatformWorkspaceCatalog (the single QML-exposed root object for Platform)
├── routes.py                           Declares the 4 platform.* QmlRoutes (admin/control/settings/tenants)
│
├── controllers/                        Python (PySide6 QObject) — all @QmlUncreatable, constructed only by context.py
│   ├── admin/
│   │   ├── admin_console_controller.py         PlatformAdminWorkspaceController — composes 9 sub-controllers (org/calendar/site/dept/employee/user/party/doc/doc-structure)
│   │   ├── access_workspace_controller.py      PlatformAdminAccessWorkspaceController — Roles & Access scope-grant assignment + security actions
│   │   ├── support_workspace_controller.py     PlatformSupportWorkspaceController — release mgmt, diagnostics export, incident reports
│   │   ├── organization_controller.py          Thin per-entity controller (table model + CRUD slots) — read fully
│   │   ├── calendar_controller.py              Same pattern, calendars
│   │   ├── site_controller.py                  Same pattern, sites
│   │   ├── department_controller.py            Same pattern, departments
│   │   ├── employee_controller.py              Same pattern, employees
│   │   ├── user_controller.py                  Same pattern, users
│   │   ├── party_controller.py                 Same pattern, parties
│   │   ├── document_controller.py              Documents + selection/preview + document-link sub-state
│   │   ├── document_structure_controller.py    Document structures (classification taxonomy)
│   │   ├── admin_action_runner.py              Small shared action-invocation helper used by admin_*_actions modules
│   │   ├── admin_calendar_actions.py           Calendar CRUD/exception/recurring-event/assignment mutation functions
│   │   ├── admin_calendar_command_builders.py  Builds desktop-API command objects for calendar mutations
│   │   ├── admin_calendar_context.py           calendar_detail_context / calendar_assignment_context lookups
│   │   ├── admin_calendar_serializers.py       Serializes calendar rules/exceptions/events to QML dicts
│   │   ├── admin_child_signal_binder.py        Rebroadcasts each sub-controller's Changed signals onto the parent controller
│   │   ├── admin_document_actions.py           Document + document-link + document-structure mutation functions
│   │   ├── admin_domain_event_binder.py        Subscribes admin controller to cross-module domain_events for auto-refresh
│   │   ├── admin_entity_actions.py             Organization/Site/Department/Employee/User/Party CRUD + toggle-active + code-gen
│   │   └── admin_helpers.py                    Small shared helpers
│   ├── common/
│   │   ├── workspace_controller_base.py        PlatformWorkspaceControllerBase — overview/isLoading/isBusy/error/feedback/operationResult + domain-event subscription plumbing shared by every workspace controller
│   │   ├── mutation_runner.py                  run_mutation() — the one create/update slot pattern used everywhere
│   │   └── serializers.py                      serialize_workspace_overview / serialize_action_list / serialize_action_item / serialize_operation_result
│   ├── control/
│   │   └── control_workspace_controller.py     PlatformControlWorkspaceController — approval queue + audit feed + approve/reject
│   ├── settings/
│   │   └── settings_workspace_controller.py    PlatformSettingsWorkspaceController — module entitlements, org profiles, integration capabilities
│   └── shell/
│       └── tenant_switcher_controller.py       TenantSwitcherController — used by BOTH ShellHeader's TenantSwitcher pill and the Tenant Management workspace
│
├── presenters/                          Pure-Python view-model builders (no QObject/Qt), one per catalog/workspace, translate desktop-API DTOs → PlatformWorkspace*ViewModel dataclasses
│   ├── admin_presenter.py                       Admin Console overview (metrics + 3 dashboard sections + activity feed)
│   ├── organization_catalog_presenter.py        Organizations list/create/update/set-active/suggest-code
│   ├── calendar_catalog_presenter.py, department_catalog_presenter.py, employee_catalog_presenter.py,
│   │   party_catalog_presenter.py, site_catalog_presenter.py, user_catalog_presenter.py   Same shape as organization_catalog_presenter.py (Inferred pattern-consistent, composition confirmed in admin_console_controller.py)
│   ├── document_catalog_presenter.py             Documents list/CRUD
│   ├── document_management_presenter.py          Document links + document structures (517 lines — largest presenter)
│   ├── access_workspace_presenter.py             Scope-grant + security-user view-models for Roles & Access
│   ├── support_workspace_presenter.py            Release/diagnostics/incident-report business logic
│   ├── control_presenter.py, control_queue_presenter.py     Control Center overview + approval queue/audit feed + approve/reject
│   ├── settings_presenter.py, settings_catalog_presenter.py Settings overview + module entitlements/org profiles/integration capabilities
│   ├── runtime_presenter.py                      PlatformRuntimePresenter — generic runtime overview (used for `runtimeOverview()` slot on the catalog)
│   ├── tenant_switcher_presenter.py              Tenant list + active-tenant + switch operation
│   └── support.py                                Small shared coercion helpers (bool_value/int_value/string_value/option_item/tuple_of_strings/preview_error_result)
│
├── view_models/                         Plain frozen dataclasses (no Qt), the presenter → controller contract
│   ├── workspace.py                             PlatformWorkspaceOverviewViewModel / *SectionViewModel / *RowViewModel / *ActionItemViewModel / *ActionListViewModel
│   ├── tenant.py                                 TenantSwitcherItemViewModel
│   └── runtime.py                                PlatformMetricViewModel / PlatformRuntimeOverviewViewModel
│
└── qml/
    ├── Platform/Controllers/            qmldir + typeinfo only — no .qml files; this is where the Python @QmlElement classes register as "Platform.Controllers 1.0"
    ├── Platform/Dialogs/  (15 files — every Platform create/edit dialog, all extend shared EntityDialog)
    │   ├── OrganizationEditorDialog.qml        New/Edit Organization (code, name, timezone, currency, active, initial-module checkboxes on create)
    │   ├── SiteEditorDialog.qml                 New/Edit Site (code, org read-only label, name, description, city/country, tz/currency, type, status, notes, active)
    │   ├── DepartmentEditorDialog.qml           New/Edit Department (code, name, description, Site/Location/Parent-Dept combos, type, cost center, notes, active)
    │   ├── EmployeeEditorDialog.qml              New/Edit Employee (code, full name, dept/site combos, title, employment type, email, phone, active)
    │   ├── UserEditorDialog.qml                  New/Edit User (username, display name, email, password [required on create], active, role checkboxes [edit only])
    │   ├── PartyEditorDialog.qml                 New/Edit Party (code, name, type combo, legal name, contact, email/phone, address block, tax/external ref, notes, active)
    │   ├── DocumentEditorDialog.qml              New/Edit Document (code, title, type/structure/storage-kind combos, storage URI, filename/mime, source system, confidentiality, version, notes, current/active)
    │   ├── DocumentLinkEditorDialog.qml          Add Document Link (module code, entity type, entity id, link role — all free-text)
    │   ├── DocumentStructureEditorDialog.qml     New/Edit Document Structure (code, name, description, parent/scope/default-type combos, sort order spin, notes, active)
    │   ├── CalendarEditorDialog.qml               New/Edit Calendar (code, name, type combo [locked on edit], timezone, description, is-default)
    │   ├── CalendarExceptionDialog.qml            Add Calendar Exception (calendar combo, date, name, exception-type, impact-type, hours override, description)
    │   ├── CalendarRecurringEventDialog.qml       Add Recurring Event (calendar combo, title, event/impact type, editable RRULE combo, start/end time, effective range)
    │   ├── CalendarAssignmentDialog.qml           Assign Calendar to an entity (read-only entity label, calendar combo, effective from/to)
    │   ├── ModuleLifecycleDialog.qml               Change a module's lifecycle status (single combo + Apply)
    │   └── ApprovalDecisionDialog.qml              Approve/Reject an approval request (single optional note textarea)
    ├── Platform/Widgets/  (6 files)
    │   ├── AccessSecurityPanel.qml               Roles & Access: assignment form + scope-grants table + inline grant inspector + security-users table+toolbar
    │   ├── AdminCatalogPanel.qml                 **Dead code** — registered in qmldir, imported nowhere in the codebase
    │   ├── DocumentDetailPanel.qml                Rich document preview card (badges, preview status, Open Source button, metadata grid, notes)
    │   ├── OverviewSectionCard.qml                Generic {title, rows[{label,value,supportingText}]} card, used by Settings Sys-Info and (unused) SettingsOverviewSections
    │   ├── RecordListCard.qml                     Generic titled row-list card w/ up to 3 per-row actions + selection state (backs OverviewSectionCard's sibling AdminEntityListCard concept)
    │   └── WorkspaceStateBanner.qml                Loading/busy/error/feedback banner stack — **unused within Platform** (every other module has its own separate copy that IS used)
    │
    └── workspaces/
        ├── admin/            "Admin Console" — see §11
        │   ├── AdminWorkspace.qml               1-line pass-through → AdminConsolePage
        │   ├── AdminConsolePage.qml              The real page: 3-pane RowLayout (nav sidebar | content | disabled detail panel) + dialog host loader
        │   ├── AdminWorkspaceState.qml            Local UI-state item: activeSection/selectedRowId/entityDetailOpen + all 9 entity table column definitions
        │   ├── components/
        │   │   ├── AdminNavSidebar.qml            Collapsible 220/48px local nav — 5 groups, 11 leaf sections
        │   │   ├── AdminEntityWorkspace.qml        Reusable list surface: title bar + TableToolbar + DataTable + (inert) TablePaginationBar
        │   │   ├── AdminDetailTableSection.qml     Reusable in-detail-page mini table section (gate/empty/info states)
        │   │   ├── AdminInformationalDetailSection.qml  Reusable "this is governed elsewhere" boundary-notice card (heavily reused)
        │   │   ├── AdminSupportActivityPanel.qml, AdminSupportDiagnosticsPanel.qml, AdminSupportPathsPanel.qml, AdminSupportReleasePanel.qml, AdminSupportRuntimePanel.qml  Support section's 5 sub-panels
        │   │   └── SupportMetaRow.qml, SupportPathRow.qml   Tiny label/value row helpers for the Support panels
        │   ├── detail/  (11 files — one full-page detail per entity type, all SectionDetailPage-based)
        │   │   ├── AdminEntityDetailPage.qml       Generic 3-section (Overview/Context/Audit) detail — used as the base building block by AdminDocumentStructureDetailPage
        │   │   ├── AdminOrganizationDetailPage.qml Overview / Runtime Scope / Audit
        │   │   ├── AdminCalendarDetailPage.qml     Overview / [Working Rules / Exceptions / Recurring Events / Assignments if enterprise] / Calculator / Audit — richest detail page
        │   │   ├── AdminSiteDetailPage.qml         Overview / Departments / [Structures/Warehouses/Projects/Assets if module enabled] / Calendar / Documents / Audit
        │   │   ├── AdminDepartmentDetailPage.qml   Overview / Employees / Users / [Projects/Warehouses if enabled] / Calendar / Documents / Audit
        │   │   ├── AdminEmployeeDetailPage.qml     Overview / User Account / Assignments / [Timesheets/Certifications if PM enabled] / Calendar / Documents / Audit
        │   │   ├── AdminUserDetailPage.qml         Overview / Roles & Access / Sessions / Module Access / Audit
        │   │   ├── AdminPartyDetailPage.qml        Overview / Contacts / [Supplier Profile if inventory] / Customer-Client Profile / [Linked Projects if PM] / [Linked Procurement if inventory] / Documents / Audit
        │   │   ├── AdminDocumentsDetailPage.qml    Overview (rich DocumentDetailPanel) / Revisions / Linked Entities / Approvals / Access / Audit
        │   │   ├── AdminDocumentStructureDetailPage.qml  Thin subclass of AdminEntityDetailPage (Overview/Classification Context/Audit)
        │   │   └── AdminAccessDetailPage.qml        Overview / Permissions / Scope / Audit (opened additively on grant-row activation)
        │   ├── dialogs/AdminDialogHost.qml         Owns & wires all 13 entity/calendar dialogs to the right controller create/update slots
        │   ├── panels/AdminEntityDetailPanel.qml   The disabled (visible:false) 288px right-rail inspector
        │   └── sections/
        │       ├── AdminAuditSection.qml           "Audit" leaf: 2-column governance dashboard (activity feed + 3 stat sections)
        │       ├── AdminCalendarAssignmentSection.qml  Reusable calendar-assignment card used inside Site/Department/Employee detail pages
        │       └── AdminSupportSection.qml          "Support" leaf: composes the 5 AdminSupport* panels
        │
        ├── control/          "Control Center" — see §12
        │   ├── ControlWorkspace.qml               1-line pass-through → ControlWorkspacePage
        │   ├── ControlWorkspacePage.qml             The real page: KPI strip + horizontal tab bar (Approvals/Audit/Escalations/System Events) + tab content
        │   ├── ControlWorkspaceState.qml            Local UI-state (activePanel/selectedRowId/pagination/detail-open + queue columns)
        │   ├── detail/ControlApprovalDetailPage.qml  Overview / Request Payload / Decision History / Audit
        │   └── sections/ControlMetricsSection.qml   Standalone KPI-strip wrapper (Flow of MetricCards) — not directly referenced by ControlWorkspacePage (which uses AppWidgets.KpiStrip inline instead); Inferred unused/legacy
        │
        ├── settings/         "Settings" — see §13
        │   ├── SettingsWorkspace.qml               1-line pass-through → SettingsWorkspacePage
        │   ├── SettingsWorkspacePage.qml             The real page: local nav sidebar + KPI/banners + 6 mutually-exclusive sections + module-detail overlay
        │   ├── components/SettingsSidebarNav.qml    Collapsible 220/48px local nav — 3 groups, 6 leaf sections
        │   ├── detail/SettingsModuleDetailPage.qml  Overview / Capabilities / Consumers / Audit (module entitlement detail)
        │   └── sections/
        │       ├── SettingsRuntimeSection.qml        Read-only theme/API-status/summary rows
        │       ├── SettingsModulesSection.qml        Module Entitlements list (DataTable, row→SettingsModuleDetailPage)
        │       ├── SettingsDefaultsSection.qml        **Fully hardcoded** static "Platform Defaults" cards — no backend at all
        │       ├── SettingsIntegrationsSection.qml    Integration Capabilities list (read-only DataTable)
        │       ├── SettingsSecuritySection.qml         **Fully hardcoded** static "Security" cards — no backend at all
        │       ├── SettingsSysInfoSection.qml          Support & Diagnostics — Flow of OverviewSectionCards from workspaceController.overview.sections
        │       └── SettingsOverviewSections.qml       **Dead code** — not referenced by any other file
        │
        └── tenants/          "Tenant Management" — see §14
            ├── TenantManagementWorkspace.qml         1-line pass-through → TenantManagementWorkspacePage
            └── TenantManagementWorkspacePage.qml       The real page: single-pane tenant list (no local nav) reusing the same TenantSwitcherController as the header pill
```

All 69 `.qml` files are accounted for above (15 Dialogs + 6 Widgets + 30 admin + 5 control + 11 settings + 2 tenants = 69).

---

## 5. Dependency and Import Map (major files)

| File | Platform-local imports | Shared-UI imports | Python-bridge imports |
|---|---|---|---|
| `AdminConsolePage.qml` | `Platform.Widgets` (`AccessSecurityPanel`), local dirs `components`/`detail`/`panels`/`sections`/`dialogs` | `App.Layouts.WorkspaceFrame`, `App.Widgets` | `Platform.Controllers` (`PlatformWorkspaceCatalog`, `PlatformAdminWorkspaceController`, `PlatformAdminAccessWorkspaceController`, `PlatformSupportWorkspaceController`, `PlatformSettingsWorkspaceController`) |
| `AdminNavSidebar.qml` | none | `App.Icons`, `App.Theme`, `App.Controls` | none (pure QML state) |
| `AdminEntityWorkspace.qml` | none | `App.Widgets` (`TableToolbar`, `InlineMessage`, `DataTable`, `TablePaginationBar`), `App.Theme`, `App.Controls` | none — receives `catalog`/`catalogModel` as plain properties |
| `AdminDialogHost.qml` | `Platform.Dialogs` (all 13 dialog types) | none | `Platform.Controllers` (`PlatformAdminWorkspaceController`) |
| `ControlWorkspacePage.qml` | `Platform.Dialogs.ApprovalDecisionDialog`, local `detail` | `App.Layouts.WorkspaceFrame`, `App.Widgets`, `App.Controls`, `App.Icons`, `App.Theme` | `Platform.Controllers` (`PlatformWorkspaceCatalog`, `PlatformControlWorkspaceController`) |
| `SettingsWorkspacePage.qml` | local `components`/`sections`/`detail` | `App.Layouts.WorkspaceFrame`, `App.Widgets`, `App.Icons`, `App.Theme` | `Platform.Controllers`, `Shell.Context` (receives `shellModel` for theme display) |
| `TenantManagementWorkspacePage.qml` | none | `App.Layouts.WorkspaceFrame`, `App.Widgets`, `App.Controls`, `App.Icons`, `App.Theme` | `Platform.Controllers.PlatformWorkspaceCatalog` (reads `.tenantSwitcher`) |
| `AdminCalendarDetailPage.qml` | `workspaces.admin.components` (`AdminDetailTableSection`, `AdminInformationalDetailSection`) | `App.Widgets`, `App.Controls`, `App.Theme` | `Platform.Controllers.PlatformAdminWorkspaceController` |
| `AdminSiteDetailPage.qml` | `workspaces.admin.components`, `workspaces.admin.sections` (`AdminCalendarAssignmentSection`) | `App.Widgets`, `App.Controls`, `App.Theme` | `Platform.Controllers.PlatformWorkspaceCatalog` (module-capability checks) |
| `*EditorDialog.qml` (all 15) | none (dialogs are leaves) | `App.Widgets.EntityDialog`/`CodeFieldRow`/`FormField`, `App.Controls.*`, `App.Theme` | none directly — payload handling lives in `AdminDialogHost.qml`/`ControlWorkspacePage.qml`/`SettingsModuleDetailPage.qml` |
| `TenantSwitcher.qml` (shell) | none | `App.Icons`, `App.Theme`, `App.Controls` | `controller` typed as `PlatformWorkspaceControllerBase`-shaped `TenantSwitcherController` (duck-typed via `platformCatalog.tenantSwitcher`) |

`Platform.Controllers` QML import maps to the Python `@QmlElement` classes registered under `QML_IMPORT_NAME = "Platform.Controllers"` (every controller file declares this same import name — Observed in every controller file opened).

---

## 6. Global Application Navigation

`ShellDrawer.qml` renders `shellModel.navigationItems` (built from `QmlRouteRegistry.list_navigation_routes()`, i.e. every route with `appears_in_navigation=True`, the default) grouped by `moduleLabel`, in registration order: **Shell** (hidden from the group header, only `shell.home` — `ShellDrawer.qml:84` explicitly skips rendering a group header for `moduleLabel === "Shell"` but "QML Home" nav item itself still appears), **Platform** (4 routes), **Project Management**, **Maintenance** (registered as `module_label="Maintenance"` but icon-map keys use `maintenance_management.*`), **Inventory & Procurement** (`inventory_procurement.*`) — module registration order observed in `qml_registry.py:41-46`.

Each module group is independently collapsible (`_collapsedGroups` state, `ShellDrawer.qml:60-70`) and the whole drawer is collapsible to a 52px icon rail (`Theme.sidebarCollapsedWidth`) via the header hamburger toggle or the drawer's own bottom "Collapse sidebar" row (`ShellDrawer.qml:293-347`). A `SearchField` filters visible items by title substring (`ShellDrawer.qml:113-124`, `_filter`/`_renderList`).

Platform sits as **one module among four**, with no visual distinction (no divider, no different icon treatment) marking it as an "administration" module versus the three business modules — Observed, `ShellDrawer.qml` group rendering is uniform for all `moduleLabel`s.

**Finding:** `platform.tenants` (Tenant Management) is **not present** in `ShellDrawer.iconForRoute()`'s icon map (`ShellDrawer.qml:26-57` — the map has `platform.admin`, `platform.control`, `platform.settings` but no `platform.tenants` key), so it silently falls back to `"default"` (`ShellDrawer.qml:56`), which `AppIcon.qml:115` renders as the generic "apps" glyph (`\uF133`). All other Platform/module routes get a semantically distinct icon; Tenant Management does not. **Observed.**

---

## 7. Platform Navigation Architecture

```
Global Drawer (Platform group)
├── Admin Console        (platform.admin)    — group_label "Administration"
├── Control Center        (platform.control)  — group_label "Control"
├── Settings              (platform.settings) — group_label "Settings"
└── Tenant Management     (platform.tenants)  — group_label "Tenants"
        │
        ▼ (each is a fully separate top-level route/workspace; no shared "Platform" shell wraps them)
        │
┌───────────────────────────────────────────────────────────────────────────┐
│ Admin Console (AdminConsolePage.qml)                                       │
│   Local nav: AdminNavSidebar (collapsible 220/48px, 5 groups)              │
│     ORGANIZATION: Organizations, Calendars, Sites, Departments             │
│     WORKFORCE:     Employees, Users, Parties                              │
│     CONTENT:       Documents, Structures                                  │
│     ACCESS:        Roles & Access                                         │
│     SYSTEM:        Support, Audit                                         │
│   Selection model: single active leaf (activeSection string), no tabs,    │
│     no breadcrumbs. Each leaf = list view OR (list + full-page detail     │
│     Loader swap on row double-click / rowActivated).                     │
│   Back-navigation: detail page's own "Back" button (top-left of          │
│     SectionDetailPage header) → closeEntityDetail() → returns to list.   │
│   Right rail: AdminEntityDetailPanel exists in the tree but is           │
│     hardcoded invisible (§11.0) — NOT part of the real navigation model. │
│   "Roles & Access" leaf has its OWN secondary detail layer               │
│     (AdminAccessDetailPage) opened additively on grant-row activation.   │
└───────────────────────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────────────────┐
│ Control Center (ControlWorkspacePage.qml)                                  │
│   Local nav: horizontal tab bar (not a sidebar) — Approvals / Audit /     │
│     Escalations / System Events. No collapse, no groups, no counts       │
│     except Approvals/Audit show a numeric badge.                        │
│   Approvals tab has its own full-page detail (ControlApprovalDetailPage) │
│     opened as a Loader overlay INSIDE the approvals column (KPI strip    │
│     above remains visible) on row activation. Back button returns.       │
└───────────────────────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────────────────┐
│ Settings (SettingsWorkspacePage.qml)                                       │
│   Local nav: SettingsSidebarNav (collapsible 220/48px, 3 groups)          │
│     PLATFORM:       Runtime, Module Entitlements                          │
│     CONFIGURATION:  Platform Defaults, Integration Capabilities, Security │
│     SYSTEM:         Support & Diagnostics                                 │
│   Module Entitlements leaf → full-page detail (SettingsModuleDetailPage) │
│     via Loader overlay (z:10, covers the whole page incl. sidebar? — see │
│     §13; Observed: Loader anchors.fill: parent at the SettingsWorkspace  │
│     root level, so YES it covers the local sidebar too, unlike Control's │
│     detail overlay which stays inside the tab content column).           │
└───────────────────────────────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────────────────────────────┐
│ Tenant Management (TenantManagementWorkspacePage.qml)                      │
│   No local nav at all — single flat list, no drill-down detail page.     │
│   "Switch" button per row is the only per-row action.                    │
└───────────────────────────────────────────────────────────────────────────┘
```

There is **no breadcrumb trail anywhere in Platform** (Observed — no breadcrumb component exists in `shared/qml/App/Widgets`, and none of the 4 workspace pages render one). Back-navigation is exclusively a per-detail-page "Back" button plus the global drawer to jump between top-level areas — there is no "up one level" gesture beyond that single Back button, and no keyboard/Escape-to-back binding was found in any detail page (`SectionDetailPage.qml` has no `Keys.onEscapePressed`).

---

## 8. Complete Platform Information Architecture

```
Platform (4 independent top-level areas — not a unified module screen)
├── Admin Console
│   ├── Organizations           (list + detail: Overview / Runtime Scope / Audit)
│   ├── Calendars                (list + detail: Overview / [Working Rules / Exceptions /
│   │                             Recurring Events / Assignments — enterprise only] / Calculator / Audit)
│   ├── Sites                    (list + detail: Overview / Departments / [Structures / Warehouses /
│   │                             Projects / Assets — module-gated] / Calendar / Documents / Audit)
│   ├── Departments              (list + detail: Overview / Employees / Users / [Projects / Warehouses
│   │                             — module-gated] / Calendar / Documents / Audit)
│   ├── Employees                (list + detail: Overview / User Account / Assignments /
│   │                             [Timesheets / Certifications — PM-gated] / Calendar / Documents / Audit)
│   ├── Users                    (list + detail: Overview / Roles & Access / Sessions / Module Access / Audit)
│   ├── Parties                  (list + detail: Overview / Contacts / [Supplier Profile — inventory-gated] /
│   │                             Customer-Client Profile / [Linked Projects — PM-gated] /
│   │                             [Linked Procurement — inventory-gated] / Documents / Audit)
│   ├── Documents                (list + detail: Overview(rich preview) / Revisions / Linked Entities /
│   │                             Approvals / Access / Audit)
│   ├── Structures               (Document Structures — list + detail: Overview / Classification Context / Audit)
│   ├── Roles & Access           (assignment form + grants table + inline inspector + additive detail page
│   │                             (Overview/Permissions/Scope/Audit) + Account Security & Sessions sub-table)
│   ├── Support                  (Release Management, Runtime Status, Incident Diagnostics, Runtime Paths,
│   │                             Support Activity feed — no list/detail pattern, it's a fixed dashboard)
│   └── Audit                    (2-column governance dashboard: activity feed + Runtime/Identity/Master-Data stats)
│
├── Control Center
│   ├── Approvals                (queue list + detail: Overview / Request Payload / Decision History / Audit)
│   ├── Audit                    (read-only activity feed)
│   ├── Escalations               (**empty placeholder**, hardcoded rows:[])
│   └── System Events             (**empty placeholder**, hardcoded rows:[])
│
├── Settings
│   ├── Runtime                   (read-only: theme mode, platform API status, workspace summary)
│   ├── Module Entitlements       (list + detail: Overview / Capabilities / Consumers / Audit)
│   ├── Platform Defaults          (**fully static**, 5 cards — Locale & Fiscal, Data Management,
│   │                              Approval Workflow, Notification Defaults, Compliance & Governance)
│   ├── Integration Capabilities   (read-only list, no detail)
│   ├── Security                  (**fully static**, 4 cards — Password Policy, Session Policy,
│   │                              RBAC Defaults, Approval Thresholds)
│   └── Support & Diagnostics      (Flow of read-only OverviewSectionCards)
│
└── Tenant Management
    └── (single flat list of tenants + Switch action; no create/edit/delete tenant UI anywhere)
```

---

## 9. Existing Application Shell Reconstruction (ASCII)

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ ShellHeader  (height≈48-58px)                                                             │
│ [☰] TECHASH ENTERPRISE          [Tenant▼]  [🔍 Global search........]  [✅][🔔]  [J] Jane │
│      Admin Console               (pill,     (decorative,             (decorative, (avatar)│
│                                    multi-     no search                no click            │
│                                    tenant     executes)                 handlers)          │
│                                    only)                                                    │
├───────────────┬────────────────────────────────────────────────────────────────────────────┤
│ GLOBAL DRAWER │  PLATFORM LOCAL NAV      │  PLATFORM WORKSPACE (content area)               │
│ (248/52px)    │  (220/48px, per-page)    │                                                   │
│ ▸ Shell       │  Admin Console:          │  e.g. Admin Console → Organizations:            │
│   • QML Home  │   ORGANIZATION           │   ┌ Organizations  N ─────────────────────────┐  │
│ ▸ PLATFORM    │    Organizations ◀active │   │ [🔍 search] [Filter][Columns][Refresh][+New]│  │
│   • Admin     │    Calendars             │   ├──────────────────────────────────────────┤  │
│     Console◀  │    Sites                 │   │ DataTable (rows...)                       │  │
│   • Control   │    Departments           │   │                                            │  │
│     Center    │   WORKFORCE              │   └──────────────────────────────────────────┘  │
│   • Settings  │    Employees             │   (pagination bar INERT — hidden, Python model)  │
│   • Tenant    │    Users                 │                                                   │
│     Mgmt      │    Parties               │  Right rail (AdminEntityDetailPanel, 288px)      │
│ ▸ PROJECT MGT │   CONTENT                │  — exists, wired, but visible:false (never shown)│
│ ▸ MAINTENANCE │    Documents             │                                                   │
│ ▸ INVENTORY & │    Structures            │                                                   │
│   PROCUREMENT │   ACCESS                 │                                                   │
│               │    Roles & Access        │                                                   │
│               │   SYSTEM                 │                                                   │
│               │    Support               │                                                   │
│               │    Audit                 │                                                   │
└───────────────┴──────────────────────────┴───────────────────────────────────────────────────┘
```

**Persistent nav panels visible simultaneously (Admin Console, expanded):** global drawer (`Theme.AppTheme.sidebarWidth`, 248px) + `MainWindow.qml`'s 1px divider `Rectangle` between drawer and workspace loader + local Admin nav (`AdminNavSidebar.implicitWidth`, hardcoded 220px, not theme-sourced) = **469px** of the 1280px window (36.6%) consumed by navigation chrome before any content renders — cross-checked directly against source (`AppTheme.qml:108`, `MainWindow.qml:47`, `AdminNavSidebar.qml:19`); reconciled with the identical 469px figure in §19's workspace-width budget table below (an earlier draft of this line read "468px," omitting the divider — corrected). Collapsed both: `Theme.AppTheme.sidebarCollapsedWidth` (52, theme-sourced) + 1px divider + `AdminNavSidebar`'s hardcoded collapsed width (48, **not** the same 52px token the global drawer uses, and not centralized — `SettingsSidebarNav.qml:17` hardcodes the identical literal `collapsed ? 48 : 220` independently) = 101px (7.9%).

---

## 10. (folded into §11-14 below, each area's own IA/nav/pages)

---

## 11. Admin Console

### 11.0 Shell (`AdminConsolePage.qml`)

Three-pane `RowLayout` (`AdminConsolePage.qml:388-938`): `AdminNavSidebar` (left, `Layout.preferredWidth: implicitWidth`, 220/48px) → center `Item` containing one `Components.AdminEntityWorkspace` (list) + one `Loader` (detail page) **per entity section**, each `visible`/`active` gated on `adminState.activeSection` — all 9 list+detail pairs exist simultaneously in the tree, toggled by visibility, not re-instantiated (`AdminConsolePage.qml:411-846`) → right `Panels.AdminEntityDetailPanel` (288px).

**Major finding — dead inline inspector:** the right panel is instantiated and fully data-bound (`detailItem`, `selectedDocument`, `documentPreviewState`, edit/toggle/set-active handlers — `AdminConsolePage.qml:898-936`) but its `visible` property is hardcoded to `false` (`AdminConsolePage.qml:902`):
```qml
Panels.AdminEntityDetailPanel {
    id: _detailPanel
    Layout.fillHeight:     true
    Layout.preferredWidth: 288
    visible:               false
    ...
```
Consequently, single-clicking a row (`onRowSelected`, which only sets `adminState.selectedRowId`) has **no visible effect** anywhere in Admin Console — the only way to see or act on a record is double-clicking (`onRowActivated` → `openEntityDetail()`) to open the full-page detail. **Observed**, `AdminConsolePage.qml:898-936` + every `AdminEntityWorkspace` instance's `onRowSelected` handler (e.g. line 427).

A single `dialogHostLoader` (`AppWidgets.LazyObjectLoader`, `AdminConsolePage.qml:941-948`) lazily instantiates `Dialogs.AdminDialogHost`, which owns all 13 entity/calendar dialogs (`AdminDialogHost.qml`).

### 11.1 Organizations

- **Entry path:** Admin Console → (default) Organizations.
- **List controls:** `AdminEntityWorkspace` title bar ("Organizations", count) + `TableToolbar` (search, refresh, column-customize — `showCustomize: root.columns.length > 0`, true here) + `DataTable`. No filter/views buttons here (`showFilter`/`showViews` not set → default false, `AdminEntityWorkspace.qml`).
- **Table columns** (`AdminWorkspaceState.qml:31-36`): Name, Code / Timezone, Status (chip), Version.
- **Row interaction:** single-click selects (no visible effect, §11.0); double-click → `AdminOrganizationDetailPage` (Overview / Runtime Scope / Audit).
- **Create:** `TableToolbar` "New Organization" → `dialogHostLoader.invoke("openOrganizationCreate")` → `OrganizationEditorDialog` (`Platform/Dialogs/OrganizationEditorDialog.qml`), 560px wide. Fields: Organization Code (with Generate button calling `workspaceController.generateEntityCode("organization", formData)`), Display Name*, Timezone, Currency, Active checkbox, and (create-only) a checklist of "Initial modules" from `organizationEditorOptions.moduleOptions`. Client-side validation: code and display name required (`submitDialog()`, lines 29-40). Save → `workspaceController.createOrganization(payload)` / `updateOrganization(payload)` (`AdminDialogHost.qml:224-232`) → `PlatformAdminWorkspaceController.createOrganization` slot (`admin_console_controller.py:273-275`) → `admin_entity_actions.create_organization` → `PlatformOrganizationCatalogPresenter.create_organization()` (`organization_catalog_presenter.py:94-106`) → desktop API `provision_organization(OrganizationProvisionCommand(...))`. On success the dialog closes and the list refreshes (`run_mutation`'s `on_success=self.refresh`, `organization_controller.py:110`).
- **Detail page** (`AdminOrganizationDetailPage.qml`): Overview (Organization Code, Display Name, Timezone, Base Currency, Status, Version + "Set Active" action if not active) / Runtime Scope (informational — explains shared-record resolution chain) / Audit (informational, points to shared audit workspace).

### 11.2 Calendars

- **Entry path:** Admin Console → Calendars.
- **Columns** (`AdminWorkspaceState.qml:37-42`): Calendar, Working Days, Status, Ownership.
- **Create:** "New Calendar" → `CalendarEditorDialog` (640px): Code (locked on edit), Name*, Calendar Type combo (GLOBAL/SITE/DEPARTMENT/EMPLOYEE/PROJECT/RESOURCE, locked after create), Timezone, Description, "Mark as default" checkbox. Save → `createEnterpriseCalendar`/`updateEnterpriseCalendar`.
- **Detail page** (`AdminCalendarDetailPage.qml`) — the richest detail page in Platform: sections are dynamic based on `isEnterpriseCalendar` — base `[Overview]`, then if enterprise `[Working Rules, Exceptions, Recurring Events, Assignments]`, then always `[Calculator, Audit]`. Exceptions/Recurring Events tables support row selection + Delete (calls `deleteCalendarException`/`deleteCalendarRecurringEvent` directly — no confirm dialog, Observed at `AdminCalendarDetailPage.qml:212-222`) and "Add" opens `CalendarExceptionDialog`/`CalendarRecurringEventDialog`. **Calculator** section is a live mini-tool: Start Date + Working Days fields, "Calculate Days" button calls `workspaceController.calculateCalendarWorkingDays({...})` and shows the result inline (`AdminCalendarDetailPage.qml:155-167`).

### 11.3 Sites

- **Columns:** Name, Code/Location, Organization, Status, Timezone/FX (`AdminWorkspaceState.qml:43-49`).
- **Create/Edit:** `SiteEditorDialog` (620px) — Code (Generate button), read-only Organization label (defaults to active org name), Name*, Description, City/Country, Timezone/Currency, Site Type, Status (free-text field, not a combo — Observed inconsistency vs. e.g. Department's typed combos), Notes, Active checkbox.
- **Detail page** (`AdminSiteDetailPage.qml`): sections computed dynamically — `[Overview, Departments]` always, then `Structures` if Maintenance enabled, `Warehouses` if Inventory enabled, `Projects` if PM enabled, `Assets` if Maintenance enabled, then always `[Calendar, Documents, Audit]`. Departments/Calendar sections are functional (filtered department table; `AdminCalendarAssignmentSection` reused component); Structures/Warehouses/Projects/Assets/Documents/Audit are all `AdminInformationalDetailSection` boundary notices pointing at the owning module — **no actual cross-module data is shown**, only static guidance text (Observed, e.g. `AdminSiteDetailPage.qml:380-392`).

### 11.4 Departments

- **Columns:** Name, Code/Type, Site, Status, Cost Center.
- **Create/Edit:** `DepartmentEditorDialog` (620px) — Code, Name*, Description, Site/Default-Location/Parent-Department combos (parent excludes self on edit), Type, Cost Center, Notes, Active.
- **Detail page:** `[Overview, Employees]` always, `Projects` if PM, `Warehouses` if Inventory, always `[Users, Calendar, Documents, Audit]`. Employees section is functional (filtered table); Users/Projects/Warehouses/Documents/Audit are informational-only boundary cards.

### 11.5 Employees

- **Columns:** Name, Code/Job Title, Department, Site, Status, Employment.
- **Create/Edit:** `EmployeeEditorDialog` (620px) — Code, Full Name*, Department/Site combos, Job Title, Employment Type combo (Full/Part-Time, Contractor, Temporary), Email, Phone, Active.
- **Detail page:** `[Overview, User Account, Assignments]` always, `Timesheets`/`Certifications` if PM enabled, always `[Calendar, Documents, Audit]`. Only Overview and Calendar are functional; the rest are informational boundary cards pointing to Users/PM Resources/PM Timesheets workspaces.

### 11.6 Users

- **Columns:** Display Name, Username, Status, Security.
- **Create/Edit:** `UserEditorDialog` (560px) — Username*, Display Name, Email, Password (required on create, optional reset on edit), Active checkbox, and (edit-only) a Roles checklist. Primary button is additionally gated: `primaryEnabled: usernameField.text.trim().length > 0 && (mode === "edit" || passwordField.text.length > 0)` (`UserEditorDialog.qml:24`).
- **Detail page** (`AdminUserDetailPage.qml`): Overview / Roles & Access (read-only role list, links to Access workspace) / Sessions (informational, links to shared security) / Module Access (`AdminDetailTableSection` showing `moduleEntitlementCatalog`) / Audit.

### 11.7 Parties

- **Columns:** Name, Code/Type, Status, Legal Name.
- **Create/Edit:** `PartyEditorDialog` (620px) — Code, Name*, Party Type combo, Legal Name, Contact Name, Email/Phone, Country/City, Address Line 1/2, Postal Code, Website, Tax Registration, External Reference, Notes, Active. The largest form in Platform (18 fields).
- **Detail page:** `[Overview, Contacts]` always, `Supplier Profile` if Inventory, always `Customer/Client Profile`, `Linked Projects` if PM, `Linked Procurement` if Inventory, always `[Documents, Audit]`. All sections past Overview/Contacts are informational-only.

### 11.8 Documents

- **Columns:** Title, Code/Type, Status, Storage.
- **Create/Edit:** `DocumentEditorDialog` (660px, widest dialog) — Code, Title*, Document Type/Structure/Storage-Kind combos, Storage URI, File Name/MIME Type, Source System, Confidentiality, Business Version, Notes, "Current version"/"Active document" checkboxes.
- **Row select vs activate:** unlike other entities, single-click on a document row also calls `root.inspectDocument(id)` (`AdminConsolePage.qml:638-641`), which populates the `selectedDocument`/`documentPreview` state used by the (invisible) right panel **and** by the detail page's Overview section — meaning the preview data is live-computed on selection even though the right panel that would show it is hidden; only opening the full detail page surfaces it.
- **Detail page** (`AdminDocumentsDetailPage.qml`): Overview (rich `PlatformWidgets.DocumentDetailPanel` — badges, preview status + Open Source button via `Qt.openUrlExternally`, metadata grid) / Revisions (informational) / Linked Entities (functional `AdminDetailTableSection` of `documentLinkCatalog`, "Add Link" → `DocumentLinkEditorDialog`) / Approvals (informational, points to Control) / Access (read-only confidentiality/storage/preview-status rows) / Audit.

### 11.9 Structures (Document Structures)

- **Columns:** Name, Code/Type, Status, Info.
- **Create/Edit:** `DocumentStructureEditorDialog` (620px) — Code, Name*, Description, Parent Structure/Object Scope/Default Document Type combos, Sort Order (SpinBox), Notes, Active.
- **Detail page:** `AdminDocumentStructureDetailPage.qml` is a thin subclass of the generic `AdminEntityDetailPage.qml` (Overview / Classification Context / Audit) — the only entity that reuses the fully-generic 3-section base rather than a bespoke page.

### 11.10 Roles & Access

- **Entry path:** Admin Console → Roles & Access.
- **Surface** (`AccessSecurityPanel.qml`) is structurally different from every other Admin leaf — no `AdminEntityWorkspace` list pattern. It combines, top to bottom:
  1. **Access Assignment** inline form: Scope Type / Scope / Principal / Role combos + "Assign Access" button → `controller.assignMembership()`.
  2. **Scoped Access Grants** `DataTable` (`scopeGrantsTableModel`) with an inline 272px-wide grant inspector `Rectangle` that appears on single-click selection (functional — unlike the disabled main Admin panel) showing Principal/Username/Permissions/Assigned + "Revoke Access" button.
  3. Row **double-click** (`onRowActivated`) additionally emits `grantActivated(grantId)` which the host (`AdminConsolePage.qml:856-878`) uses to open a **third** surface: `AdminAccessDetailPage` (Overview / Permissions / Scope / Audit), rendered as a full-page `Loader` replacing the whole Access leaf content (list+inspector hidden while open).
  4. **Account Security & Sessions**: a second, independent `DataTable` (`securityUsersTableModel`) with a `ContextualActionToolbar` (visible only when a session row is selected) offering Unlock Account / Revoke Sessions / Force Password Reset, each gated by `canPrimaryAction`/`canSecondaryAction` backend flags.
- This is the only Admin leaf with **three simultaneous selection/detail mechanisms** (inline form, inline inspector, additive full-page detail) — a structural inconsistency versus every other entity's single list→detail pattern.

### 11.11 Support

- **Entry path:** Admin Console → Support. Not a list/detail page at all — a fixed dashboard of 5 panels (`AdminSupportSection.qml`): **Release Management** (channel combo, auto-check checkbox, manifest source field, Save/Check-Updates/Install-Now/Open-Download buttons — Install triggers a confirm `EntityDialog` then quits the app to hand off to an OS-level installer, `AdminSupportSection.qml:54-66`), **Runtime Status** (read-only version/theme/governance info), **Incident Diagnostics** (trace-ID field + New/Copy buttons, Export Diagnostics via `FileDialog`, Report Incident), **Runtime Paths** (Logs/Data folder open links), **Support Activity** (timeline feed). Filter/Views toolbar buttons here are the same decorative placeholder popups as elsewhere.

### 11.12 Audit

- **Entry path:** Admin Console → Audit. A 2-column governance dashboard (`AdminAuditSection.qml`): left = `ActivityFeed` of governance events (`overview.activityFeed`); right = 3 scrollable stat sections (Runtime Context, Identity & Workforce, Master Data Coverage) built from the same `admin_presenter.build_overview()` sections used to compute the Admin Console's overview. No table, no create action. Filter/Views popups are the same static placeholders.

---

## 12. Control Center

- **Entry path:** Global drawer → Control Center.
- **Shell** (`ControlWorkspacePage.qml`): `AppWidgets.KpiStrip` (approvals metrics) → info/error/success banners → horizontal tab bar (Approvals `count=queueCount` / Audit `count=feedCount` / Escalations `0` / System Events `0`) → tab content.
- **Approvals tab:** `TableToolbar` (search/filter/views/refresh) + `DataTable` (`approvalQueueTableModel`) + `TablePaginationBar` (functional here — no Python `sourceModel`-hides-pagination guard is present in `ControlWorkspacePage.qml`, unlike Admin's entity lists, though the underlying data is still Python-backed; **Inferred**: pagination controls exist and are wired to local `state.queueCurrentPage`/`queuePageSize` but it is not verified whether the backend actually slices data server-side or the client silently discards the paging params — **Unable to determine from static analysis** whether paging has any real effect on `approvalQueueTableModel`'s row set, since `DynamicTableModel.set_rows()` receives the full list regardless).
  - Row activation → `ControlApprovalDetailPage` (Overview / Request Payload / Decision History / Audit) as a `Loader` **inside the approvals column** (KPI strip stays visible above it).
  - Approve/Reject (available only when status looks pending, `_isPending` keyword match) open `ApprovalDecisionDialog` (single optional note) → `approveRequestWithNote`/`rejectRequestWithNote`.
- **Audit tab:** read-only `ActivityFeed`, no table, no toolbar actions besides implicit refresh via workspace refresh.
- **Escalations / System Events tabs:** **hardcoded empty placeholders.** `ControlWorkspacePage.qml:259-271` (Escalations) and `:290-302` (System Events) both instantiate a `DataTable` with `rows: []` (a literal empty array, not a controller property) and static column definitions, `emptyText` fixed strings ("No active escalations — all requests are within SLA", "No system events recorded in this session"). There is no `PlatformControlWorkspaceController` property for escalations or system events at all (confirmed absent from `control_workspace_controller.py`). **Observed: not implemented.**

---

## 13. Settings

- **Entry path:** Global drawer → Settings.
- **Shell** (`SettingsWorkspacePage.qml`): `SettingsSidebarNav` (left, 220/48px) + right column (`KpiStrip` + banners + section content). The module-detail `Loader` is placed as a **sibling of the whole RowLayout** at the workspace root (`SettingsWorkspacePage.qml:215-247`, `z:10`, `anchors.fill: parent`), so opening a module's detail page covers the local sidebar too — different from Control's overlay, which stays confined to the tab-content column.

### 13.1 Runtime

Read-only 3-row list: Theme Mode (from `shellModel.themeMode`), Platform API status label, workspace summary string. No edit affordance of any kind despite the section icon suggesting configuration (`settings` icon, `SettingsSidebarNav.qml:99`).

### 13.2 Module Entitlements

- **Columns:** Module, Stage/License, Lifecycle (chip), Runtime.
- Row activation → `SettingsModuleDetailPage` (Overview / Capabilities / Consumers / Audit). Overview toolbar actions: **Lifecycle** (opens `ModuleLifecycleDialog`, a single combo + Apply, gated by `canTertiaryAction`), **Licensed** (direct toggle, gated `canPrimaryAction`), **Enabled** (direct toggle, gated `canSecondaryAction`) — Licensed/Enabled have **no confirmation dialog**, they mutate immediately on click (`SettingsModuleDetailPage.qml:129-136`). Capabilities/Consumers sections are informational-only, pointing back at Integration Capabilities.

### 13.3 Platform Defaults

**Fully hardcoded.** `SettingsDefaultsSection.qml:53-89` defines a literal JS array of 5 cards (Locale & Fiscal, Data Management, Approval Workflow, Notification Defaults, Compliance & Governance) each with fixed `label`/`value` rows (e.g. "Default timezone" → "UTC+00:00 (configurable per org)", "Password expiry" is actually in the Security section but similarly "90 days"). **No property on `PlatformSettingsWorkspaceController` backs any of this** (confirmed absent in `settings_workspace_controller.py`). There is no edit action anywhere on this page. It reads as a settings screen but is decoration. **Observed.**

### 13.4 Integration Capabilities

Read-only `DataTable` (`integrationCapabilitiesTableModel`), refresh only, no row detail, no create.

### 13.5 Security

**Fully hardcoded**, same pattern as Platform Defaults — 4 cards (Password Policy, Session Policy, RBAC Defaults, Approval Thresholds) with fixed values (`SettingsSecuritySection.qml:54-78`), zero controller binding, zero edit affordance. **Observed.**

### 13.6 Support & Diagnostics

A `Flow` of `OverviewSectionCard`s built from `workspaceController.overview.sections` — reuses the generic Settings overview object (same one driving the KPI strip regardless of active section) rather than a Support-specific data source.

### Dead section

`SettingsOverviewSections.qml` exists in `sections/` but is imported by nothing (confirmed via repo-wide grep — only its own `qmldir` registration references it). **Observed dead code.**

---

## 14. Tenant Management

- **Entry path:** Global drawer → Tenant Management.
- **Shell:** `WorkspaceFrame` (title "Tenant Management", subtitle "N tenants") with **no local nav sidebar** — the only Platform area with a single flat pane.
- **Content:** a bordered `ListView` of tenants — status dot (active=success green / suspended=warning amber / other=muted), Display Name + Code, "Current" badge if active tenant, status badge if not `isActive`, and a "Switch" button (disabled for the current tenant or for any tenant whose `isActive` flag is false).
- **Toolbar:** Refresh only. **No create/edit/delete/provision tenant action exists anywhere in this workspace or elsewhere in Platform** — tenant lifecycle management is entirely absent from the UI (Observed: no dialog, no button, no route references tenant creation).
- **Duplication finding:** this workspace and `ShellHeader.qml`'s `TenantSwitcher` pill are both bound to the exact same `TenantSwitcherController`/`TenantSwitcherPresenter` instance (`platformCatalog.tenantSwitcher`, both `TenantManagementWorkspacePage.qml:16` and `ShellHeader.qml:135`/`TenantSwitcher.qml:12`). The two surfaces render the same list with the same Switch capability in two different visual styles (dropdown Menu vs. full-page ListView) — full functional duplication with no differentiation beyond presentation. **Observed.**

---

## 15. Shared Components Used by Platform

| Component | Source file | What it renders |
|---|---|---|
| `WorkspaceFrame` | `shared/qml/App/Layouts/WorkspaceFrame.qml` | Page chrome: `PageHeader` (title/subtitle) + content slot, `pagePadding` margins. Used by all 4 top-level workspace pages. |
| `MasterDetailLayout` | `shared/qml/App/Layouts/MasterDetailLayout.qml` | A `SplitView`-based master/detail scaffold — **not used anywhere** (dead code; Admin/Access hand-roll their own layouts instead). |
| `DataTable` | `shared/qml/App/Widgets/DataTable.qml` | Custom `TableView`-based 2D grid (not `ListView`), status/progress/text cell renderers, optional frozen multi-select checkbox column, client-side or Python-model-backed. Used by every list in Platform. |
| `TableToolbar` | `.../TableToolbar.qml` | Search + optional Filter/Customize/Views buttons + Refresh/Import/Export/Create. |
| `TablePaginationBar` | `.../TablePaginationBar.qml` | Page-size combo + "Showing X–Y of Z" + Prev/Next — client-side only, hidden whenever a Python table model is bound (Admin entity lists). |
| `EntityDialog` | `.../EntityDialog.qml` (extends `App.Controls.CenteredDialog`) | Standard dialog shell: subtitle + priority messages + scrollable form + footer [Destructive? spacer busy Cancel Primary]. Backs all 15 Platform dialogs. |
| `SectionDetailPage` | `.../SectionDetailPage.qml` | Standard full-page detail shell: panel header (Back + title + optional Edit/Delete — **always disabled in Platform**) + `SectionNavigationRail` + scrollable content with a pinned `ContextualActionToolbar`. Backs every Admin/Control/Settings detail page. |
| `ContextualActionToolbar` | `.../ContextualActionToolbar.qml` | The actual action-button row used inside every detail page (since `SectionDetailPage`'s own Edit/Delete are unused). |
| `SectionNavigationRail` | `.../SectionNavigationRail.qml` | Left-hand section list inside a detail page, supports optional grouping/collapse. |
| `LazySectionLoader` / `LazyObjectLoader` | `.../LazySectionLoader.qml`, `.../LazyObjectLoader.qml` | Async component loaders with a spinner placeholder; used for every detail-page section and the Admin dialog host. Both contain `console.debug`/`console.warn` calls left in (code-hygiene note). |
| `KpiStrip` / `MetricCard` | `.../KpiStrip.qml`, `.../MetricCard.qml` | KpiStrip = horizontal `Flow` of `MetricCard`s; used at the top of Control Center and Settings. |
| `StatusChip` | `.../StatusChip.qml` | Single shared status-pill renderer (keyword-bucketed success/info/warning/danger/neutral); used in every table, activity feed, and detail overview. |
| `InlineMessage` / `SectionScopedInlineMessage` | `.../InlineMessage.qml`, `.../SectionScopedInlineMessage.qml` | Loading/error/success banners; the "scoped" variant auto-hides when the user switches detail-page section so a stale error doesn't linger. |
| `EmptyState` | `.../EmptyState.qml` | Centered title+message shown when a table/feed has zero rows. |
| `CodeFieldRow` | `.../CodeFieldRow.qml` | Entity-code input + "Generate" button, used by 7 of the 15 dialogs (org/site/dept/employee/party/document/doc-structure). |
| `FormField` | `.../FormField.qml` | Generic labelled-field wrapper, used by nearly every other field in every dialog. |
| `SectionCard` / `SectionHeading` | `.../SectionCard.qml`, `.../SectionHeading.qml` | Titled bordered card / underlined section label, used throughout detail-page content. |
| `ActivityFeed` | `.../ActivityFeed.qml` | Timeline list (colored dot + connecting line + title/status-chip/meta), used by Support Activity, Control Audit, Admin Audit. |
| `AnchoredPopup` | `.../AnchoredPopup.qml` | Anchors a `Popup` under a toolbar button; used for every (non-functional) Filter/Views popup. |
| `AppIcon` | `shared/qml/App/Icons/AppIcon.qml` | Glyph-font icon system (two private Fluent TTFs), hardcoded name→glyph map, silent fallback to a generic "apps" glyph for unmapped names. |
| `AppTheme` | `shared/qml/App/Theme/AppTheme.qml` | Singleton token source — see §16. |
| `PrimaryButton` / `SecondaryButton` | `shared/qml/App/Controls/*.qml` | The two button styles used everywhere (accent-filled vs. outlined), both support `iconName`/`danger`. |
| `CenteredDialog` | `shared/qml/App/Controls/CenteredDialog.qml` | Base `Dialog` with theme-styled background/shadow/centering, extended by `EntityDialog`. |
| `SearchField` | `shared/qml/App/Controls/SearchField.qml` | Debounced search input with clear button, used by every `TableToolbar`. |
| `PlatformWidgets.AccessSecurityPanel` | `Platform/Widgets/AccessSecurityPanel.qml` | Platform-local (not shared), the Roles & Access combined surface (§11.10). |
| `PlatformWidgets.DocumentDetailPanel` | `Platform/Widgets/DocumentDetailPanel.qml` | Platform-local, rich document-preview card used by the Documents detail page and (unreachable) right panel. |
| `PlatformWidgets.OverviewSectionCard` | `Platform/Widgets/OverviewSectionCard.qml` | Platform-local, generic title+rows card used by Settings Sys-Info. |

---

## 16. Styling and Design System

`AppTheme.qml` is a `pragma Singleton` `QtObject` (`shared/qml/App/Theme/AppTheme.qml:1-5`) — one fixed color palette, no light/dark branching logic anywhere in the file. Font: `"Segoe UI Variable Text"` (line 6). A `densityMode` property (`compact`/`comfortable`/`spacious`, default `"compact"`, line 8) drives many spacing/sizing tokens via ternaries (e.g. `spacingMd`, `toolbarHeight`, `inputHeight`) but **no QML file anywhere in Platform (or, so far as this audit traced, the whole app) exposes a control to change it** — it is a dead lever.

| Concern | Current implementation | Source file |
|---|---|---|
| Color palette | Single fixed light palette (surface/border/text/accent/semantic color groups) | `AppTheme.qml:15-64` |
| Dark mode | Not implemented — no conditional branch on any theme-mode value anywhere in the token file | `AppTheme.qml` (absence) |
| Theme-mode tracking | `ShellContext.themeMode` persisted/displayed (Settings → Runtime shows it) but never consumed to change a color | `shell/context.py:81-83`, `SettingsRuntimeSection.qml:90` |
| Density scale | 3-tier (`compactDensity`/`comfortableDensity`/`spaciousDensity`) drives spacing/margin/row-height/icon tokens | `AppTheme.qml:8-12, 67-116` |
| Density control | No UI setter found anywhere | — (absence) |
| Typography scale | 8-step type scale (`captionSize` 11px → `headerSize` 24px) | `AppTheme.qml:85-92` |
| Spacing scale | 5-step (`spacingXs..spacingXl`), density-aware | `AppTheme.qml:67-71` |
| Radii | 3-step (`radiusSm/Md/Lg`: 4/8/12) | `AppTheme.qml:80-82` |
| Icon system | Two private Fluent glyph fonts, string-keyed lookup table, silent "default" fallback | `AppIcon.qml:31-38, 42-116` |
| Status color mapping | Single shared keyword-bucketing function (`StatusChip._variant`) reused everywhere a status renders | `StatusChip.qml:17-33` |
| Dialog chrome | Fixed shadow/border/radius/padding tokens, content-driven height capped to window | `AppTheme.qml:147-159`, `EntityDialog.qml:96-107` |
| Table column sizing | Type-based natural widths (status/progress/wide-text heuristics) + flex distribution | `AppTheme.qml:161-166`, `DataTable.qml:233-265` |
| Nav sidebar widths | Hardcoded 220/48 (local nav) vs. 248/52 (global drawer) — **two different collapsed/expanded widths for conceptually identical sidebars** | `AdminNavSidebar.qml:19`, `SettingsSidebarNav.qml:17`, `AppTheme.qml:108-109` |

---

## 17. Interaction Patterns

- **List → detail:** single-click selects (row highlight only, since the one panel that would react is disabled); double-click (or Enter, `DataTable.qml:667-676`) opens a full-page detail via `Loader`. Consistent across every Admin entity and Control's Approvals.
- **Create:** toolbar "New X" button → `LazyObjectLoader`/direct dialog instantiation → `EntityDialog`-based modal, client-side required-field validation, `submitDialog()` keeps the dialog open and shows the error inline on failure, closes only on backend success (`EntityDialog.qml:19-26` inline comment documents this contract explicitly).
- **Edit:** every dialog is dual-mode (`mode: "create"|"edit"`) reusing the same QML file and validation path.
- **Delete:** **no delete action exists anywhere in Admin Console for the 9 master-data entity types** — every detail page's "Delete" button that appears is a decorative leftover on the (invisible) right panel only (`AdminEntityDetailPanel.qml:374-382`, `onClicked: {}` — an explicitly empty handler). Calendar Exceptions/Recurring Events are the only records with a real delete action, and it fires with no confirmation step.
- **Toggle-active:** direct one-click mutation (Sites/Departments/Employees/Users/Parties/Documents/Document-Structures/Organizations' "Set Active"), no confirmation dialog anywhere.
- **Module-gated sections:** detail pages conditionally add/remove whole `SectionNavigationRail` entries based on `platformCatalog.isModuleEnabled(...)` — the only place entitlement visibly reshapes Admin Console's navigation (see §20).
- **Filter/Views:** present as toolbar buttons in Admin Audit, Control Approvals, and Admin Support, but every one opens an `AnchoredPopup` containing only static explanatory text and a Close button — none filter or change the view. **Observed non-functional across the board.**
- **Refresh:** every workspace/list has a manual Refresh button; in addition, domain-event subscriptions (`_subscribe_domain_signal`/`_subscribe_domain_change` in `workspace_controller_base.py:143-192`) trigger automatic background refreshes on cross-module data changes, deferred while the controller is busy/loading (`_pending_domain_refresh` flush logic).

---

## 18. Loading / Empty / Error / Permission-denied / Disabled / Selected / Other States

| State | Handling |
|---|---|
| Loading | `InlineMessage` (tone "info", "Loading...") shown when `isLoading|isBusy` and no error, consistently across Admin/Control/Settings/Tenant workspaces (e.g. `AdminConsolePage`'s per-section `AdminEntityWorkspace.isLoading`; `ControlWorkspacePage.qml:52-57`). `DataTable` also has its own `BusyIndicator` overlay when `loading:true` (`DataTable.qml:834-853`). |
| Busy (mutation in flight) | Separate `InlineMessage` ("Saving changes...") driven by `isBusy`; buttons across dialogs/toolbars disable via `enabled: !busy`. |
| Empty | `EmptyState` component, per-list custom title/message from `catalog.emptyState`; Control's Escalations/System Events show **hardcoded** empty text regardless of real state (not implemented, see §12). |
| Error | `InlineMessage` (tone "danger") bound to `errorMessage`; takes priority over the success banner everywhere (`... && root._err.length === 0` guard repeated in every workspace page). |
| Success/feedback | `InlineMessage` (tone "success") bound to `feedbackMessage`, shown only when no concurrent error. |
| Permission-denied | **Not implemented as a distinct state anywhere found.** No QML file renders a "you don't have permission" message, disabled overlay, or 403-style empty state. RBAC/permission enforcement, if any, is presumed to happen entirely server-side with generic error messages surfacing through the same `errorMessage` channel as any other failure. **Unable to determine from static analysis** whether the backend ever returns a permission-specific error category that the UI could special-case (the `serialize_operation_result` contract only carries `category`/`code`/`message` strings, and no QML file branches on `category === "permission"` or similar). |
| Disabled (module not licensed/entitled) | Handled by **hiding** the affected `SectionNavigationRail` entries in detail pages (`root.pmEnabled ? sections.push(...)`) rather than showing them disabled/grayed-out with an explanation — i.e. entitlement gating is invisible-by-omission, not visible-but-disabled. |
| Selected (list row) | Left accent bar + `selectedSurface`/`hoverSurface` background swap in `DataTable` cell delegate (`DataTable.qml:711-729`); `AccessSecurityPanel`'s grant table uses the same `DataTable` so it's consistent there too. |
| Selected (nav item) | Left accent bar + `navSelectedBackground`/`navSelectedText` — consistent between `ShellDrawer`, `AdminNavSidebar`, `SettingsSidebarNav`, and `SectionNavigationRail` (4 independent re-implementations of the same visual idiom, not a shared component — see §24). |
| Column customize | `TableColumnCustomizer` popup (referenced, not opened in this audit) available only on Admin entity lists (`showCustomize` true there, false everywhere else). |

---

## 19. Window Resizing and Layout Behaviour

- **Window:** `ApplicationWindow` fixed *initial* size `1280×800` (`App.qml:14-15`); no `minimumWidth`/`minimumHeight` set anywhere in `App.qml`, so the OS default resize behavior applies with no enforced floor — **Unable to determine from static analysis** what happens visually below some width (e.g. whether the fixed 288px/220px/248px rails start overlapping content), since no explicit minimum-width guards were found on any `RowLayout` in the Admin/Settings shells.
- **Global drawer:** `implicitWidth` animated between `sidebarWidth` (248) and `sidebarCollapsedWidth` (52) via a `NumberAnimation` Behavior (`ShellDrawer.qml:16-22`), `Layout.preferredWidth: implicitWidth` in `MainWindow.qml:42` — fixed, non-flexible; does not participate in `Layout.fillWidth`.
- **Local nav (Admin/Settings):** same fixed 220/48 pattern, independently re-implemented (`AdminNavSidebar.qml:19`, `SettingsSidebarNav.qml:17`) rather than sharing one component.
- **Center content:** `Layout.fillWidth: true` / `Layout.fillHeight: true` throughout — genuinely flexible, resizes with the window.
- **Right rail (Admin):** fixed `Layout.preferredWidth: 288` but `visible: false` — per documented Qt Quick Layouts behavior, an invisible child is excluded from layout space allocation, so this rail is **Inferred** (not runtime-verified) to consume 0px at runtime despite its declared preferred width.
- **Detail page rail (`SectionNavigationRail`):** fixed `Layout.preferredWidth: Theme.AppTheme.detailRailWidth` (220px, `SectionDetailPage.qml:224`), non-flexible.
- **Tables:** `DataTable` computes column widths itself (flex distribution over remaining space after fixed-width/status/progress columns, `DataTable.qml:210-265`); a horizontal `ScrollBar` appears when total minimum column width exceeds the viewport (`_hScrollBar`, `DataTable.qml:816-824`).
- **Dialogs:** width fixed per-dialog (420/480/520/560/600/620/640/660px across the 15 dialogs — no shared standard width; see table below), height is content-driven up to `maxDialogHeight = parent.height - dialogPadding*2` (`EntityDialog.qml:96-107`), body scrolls (`Flickable`) once capped.
- **SplitView usage:** `MasterDetailLayout.qml` is the only `SplitView`-based component in the shared library and it is unused — every actual master/detail surface in Platform uses fixed-width `RowLayout` panes instead of a user-draggable `SplitView`. **No resizable panes exist anywhere in Platform.**

**Workspace-width budget (1280px window, Admin Console, both nav levels expanded):**

| Element | Width | Running total |
|---|---:|---:|
| Global drawer (`sidebarWidth`) | 248px | 248px |
| Divider | 1px | 249px |
| Admin local nav (`AdminNavSidebar` expanded) | 220px | 469px |
| **Remaining workspace area** | **811px** | 1280px |
| — of which right rail (invisible, 0px effective per Inferred Layout semantics) | 0px (288px declared, not laid out) | — |

Both collapsed: 52 + 1 + 48 = 101px chrome, 1179px workspace (92.1%). Both expanded: 469px chrome, 811px workspace (63.4%).

---

## 20. QML-to-Python Interaction Map

- **Registration:** every Python controller/model declares `QmlElement` + `QML_IMPORT_NAME` (`"Platform.Controllers"` for all Platform controllers, `"App.Models"` for `DynamicTableModel`) and is import-side-effect-registered by `qml_engine.py`'s long list of `import ...` lines (lines 14-19 for Platform specifically) before the engine loads any `.qml`.
- **Property binding:** every workspace controller exposes `@Property("QVariantMap", notify=...)` view-model dicts (e.g. `organizations`, `moduleEntitlements`, `approvalQueue`) that QML binds directly (`root.organizationCatalog`, etc.), plus `@Property(QObject, constant=True)` `DynamicTableModel` instances used as `DataTable.sourceModel` for the actual row rendering.
- **Mutation call pattern:** QML calls a `@Slot("QVariantMap", result="QVariantMap")` (e.g. `createOrganization`) → Python composes/validates → calls presenter → desktop API → wraps result via `run_mutation()`/`serialize_operation_result()` → returns a `{ok, category, code, message}` dict that the calling dialog inspects to decide whether to close itself (`AdminDialogHost._handleResult`, `AdminDialogHost.qml:28-35`).
- **Cross-cutting capability slots:** `PlatformWorkspaceCatalog.isModuleEnabled`/`hasCapability`/`canUseIntegration`/`capabilitySnapshot`/`resolveSoftReference` (`context.py:281-334`) are called directly from QML detail pages to decide whether to add a section to `SectionNavigationRail` — this is the *only* two-way integration point between Admin Console UI and the cross-module `IntegrationCapabilityDesktopApi`.
- **Domain-event → auto-refresh:** every workspace controller subscribes to `src.core.shared.events.domain_events` signals in its constructor (e.g. `PlatformControlWorkspaceController._bind_domain_events` subscribes to `approvals_changed`, `project_changed`, `tasks_changed`, `costs_changed`, `resources_changed`, `baseline_changed`, `register_changed`, `modules_changed` — `control_workspace_controller.py:102-113`) so that changes made in *other* modules (e.g. PM) can silently refresh Platform's Control Center without any user action. Refreshes are deferred while `isBusy`/`isLoading` and flushed afterward (`workspace_controller_base.py:194-216`).
- **Table model push, not pull:** `DynamicTableModel.set_rows()`/`set_columns()` are called directly by controllers (Python→Python, no QML round-trip) whenever a `_set_<catalog>()` setter fires, so QML never re-serializes rows itself — the `DataTable`'s `rows:` (plain-QML) path is a **fallback**, only exercised when `sourceModel` is null (e.g. Control's hardcoded Escalations/System Events tables, and the two hardcoded Settings sections use no table at all).
- **Tenant switch side-effect:** `TenantSwitcher.qml`'s `Connections { target: root.controller; function onTenantSwitched() { platformCatalog.refreshAllWorkspaces() } }` (`TenantSwitcher.qml:31-38`) is the one place a QML file directly orchestrates a cross-controller refresh cascade rather than relying on domain events.

---

## 21. Authorization and Tenant Scope Behaviour

- **Tenant scope:** `TenantSwitcherController.isMultiTenant` (`tenant_switcher_controller.py:52-54`) is `true` only when more than one tenant exists; `TenantSwitcher.qml:25` binds the header pill's `visible` directly to this — **Observed:** in a single-tenant deployment the tenant switcher UI disappears entirely from the header (though the Tenant Management workspace itself remains reachable from the drawer regardless, still showing a 1-row list).
- **Tenant status gating:** in both the header menu and the Tenant Management list, a tenant row's "Switch"/`MenuItem` is enabled only if `modelData.isActive === true` and it isn't already the current tenant (`TenantSwitcher.qml:87-90`, `TenantManagementWorkspacePage.qml:109`) — suspended/archived tenants are visibly badged (amber "Suspended" / red archived-style badge) but not switchable. This is a genuine, code-verified visible/enabled binding, not naming-only.
- **Module entitlement scope:** confirmed to visibly reshape the UI — every Site/Department/Employee/Party detail page computes its `_sections` array conditionally on `platformCatalog.isModuleEnabled("project_management"|"inventory_procurement"|"maintenance_management")` (e.g. `AdminSiteDetailPage.qml:52-73`), and hides (not disables) the corresponding `SectionNavigationRail` entries. This is the clearest instance of entitlement-driven UI in the codebase.
- **Role/permission scope:** **no direct evidence found of role-based show/hide or enable/disable at the QML level for individual buttons or fields**, apart from the generic `canPrimaryAction`/`canSecondaryAction`/`canTertiaryAction` boolean flags returned per-row inside every `ActionItemViewModel` (`view_models/workspace.py:30-40`) and consumed to enable/disable specific row/detail actions (e.g. Module Entitlement's Lifecycle/Licensed/Enabled buttons, User's Sessions Unlock/Revoke/Force-Reset buttons). These flags are opaque server-computed booleans — **Inferred** they encode some backend permission/state logic, but **Unable to determine from static analysis** exactly what governs each flag (business-rule state such as "already active" vs. actual RBAC permission checks) without reading the desktop-API layer behind the presenters, which is out of scope for this Platform-UI-only audit.
- **Organization scope vs. Tenant scope:** the Admin Console's "active organization" (set via Organizations → "Set Active") is a *separate* scoping concept from the header's tenant switch — an organization is scoped *within* the active tenant (Observed: `AdminOrganizationDetailPage.qml`'s Runtime Scope section explicitly describes "organization context → shared sites → shared departments → shared documents → downstream module integrations" as a resolution chain that exists *underneath* whatever tenant is currently active). The UI provides **no visible indicator anywhere** (header, breadcrumb, or otherwise) of which organization is currently active outside of visiting Admin Console → Organizations and reading the "Active" status chip on a row.

---

## 22. Current UX Strengths

- Extremely consistent list-page anatomy (title bar → toolbar → table → pagination) and detail-page anatomy (nav rail → pinned action toolbar → lazy-loaded sections) across essentially every Admin/Control/Settings screen — a new page can be predicted almost entirely from having seen one.
- Loading/busy/error/success banner ordering (error > success > info) is applied identically everywhere, so state feedback is never ambiguous about which message wins.
- Module-entitlement-aware section visibility in detail pages is a genuinely useful, consistently-implemented pattern for keeping Platform Admin from duplicating other modules' data.
- The dialog validation contract (`submitDialog()` keeps the dialog open and shows the error in place; closes only on confirmed backend success) is applied uniformly and prevents silent data loss on failed saves.
- `LazySectionLoader`'s `keepLoaded` flag means switching between already-visited detail-page tabs doesn't re-fetch/re-render from scratch, which should feel fast once a detail page has been opened.
- Column-type-aware rendering (`status`, `progress`, `text`) in `DataTable` is centralized in one component, so status chips and progress bars are visually identical everywhere they appear.

---

## 23. Current UX Problems and Inconsistencies

1. **Disabled inline inspector** (§11.0) — the right-hand Admin detail panel is fully built and wired but permanently hidden, meaning single-click selection anywhere in Admin Console currently does nothing visible. This is the single biggest gap between "what the code can do" and "what the UI shows."
2. **Fake-configurable settings** — Platform Defaults and Security in Settings look like editable configuration screens (cards, labeled rows, section icons implying settings) but are 100% static text with zero backend and zero edit UI.
3. **Fake-empty Control tabs** — Escalations and System Events always show their hardcoded empty-state text regardless of real system state, because there is no real state to check.
4. **Universally decorative Filter/Views** — every Filter/Views button across Admin/Control opens a popup that says, verbatim, that filters "will appear here" — this is present on enough screens that users will reasonably expect it to work somewhere.
5. **Non-functional pagination** — the pagination bar is built, styled, and present in the component tree conceptually, but is unconditionally hidden for every Admin entity list (the exact case it exists for), making it effectively decoration-in-waiting.
6. **No delete anywhere** — none of the 9 Admin master-data entities can be deleted from the UI; the only "Delete" button in the codebase (on the disabled right panel) has an empty click handler.
7. **No confirmation on destructive-ish actions** — toggling active state, deleting a calendar exception/recurring event, and applying module lifecycle/licensed/enabled changes all fire immediately with no "are you sure."
8. **Triplicated interaction model in Roles & Access** — inline form + inline inspector + additive full detail page is three affordances for what is conceptually one "manage a grant" task, and none of the sibling entity leaves use more than one.
9. **Global header controls that don't work** — Global Search, Approvals bell/badge, and Notifications bell in `ShellHeader.qml` have no click handlers and no backing data; they are pure chrome.
10. **Duplicated tenant-switch UI** — the header pill and the Tenant Management workspace are two full UI implementations of the exact same capability with no differentiation.
11. **Sidebar re-implementation, not reuse** — `ShellDrawer`, `AdminNavSidebar`, `SettingsSidebarNav`, and `SectionNavigationRail` are four independent QML implementations of "collapsible grouped nav list with selected-accent-bar," each with slightly different collapsed-widths (52 vs 48) and none sharing a base component.
12. **No visible "active organization" indicator** outside the Organizations list itself, despite organization scope materially affecting what shared records resolve.
13. **No dark mode** despite a tracked/displayed `themeMode` value.
14. **Missing nav icon** for Tenant Management (falls back to the generic default glyph).
15. **Dead code left registered:** `AdminCatalogPanel.qml`, `WorkspaceStateBanner.qml` (Platform's copy), `MasterDetailLayout.qml`, `SettingsOverviewSections.qml`, and `sections/ControlMetricsSection.qml` (built but not wired into `ControlWorkspacePage.qml`, which uses `AppWidgets.KpiStrip` inline instead — **Inferred** unused/legacy, not confirmed dead via grep the way the other four were, since it's plausible another future consumer intends to use it).

---

## 24. Navigation and Information Architecture Findings

- Platform is **4 sibling top-level areas**, not 1 module with sub-navigation — from the shell's perspective, Admin Console/Control Center/Settings/Tenant Management are as separate from each other as Project Management is from Maintenance. There is no "Platform home" screen.
- The rationale for splitting Admin Console vs. Control Center vs. Settings vs. Tenant Management is **not self-evident from the UI** and only becomes clear by reading code: Admin Console = master data + RBAC + support tooling; Control Center = cross-module approval/audit queue; Settings = module entitlement + (currently decorative) global configuration; Tenant Management = hosting-container switch. A first-time user has no in-app explanation of this split (no descriptive subtitle differentiates them beyond a one-line generic subtitle per workspace).
- Depth-of-access is shallow everywhere except Roles & Access (3 competing mechanisms, §23.8) and Calendars (richest single detail page with 4-7 dynamic sections).
- No global "recently viewed" or cross-workspace search exists to jump directly to, say, a specific Employee from anywhere other than Admin Console → Employees.

### Navigation-depth audit

| Task | Current path | Depth (decisions) |
|---|---|---|
| Create a new Organization | Drawer→Admin Console (1) → Organizations already default (0) → "New Organization" (2) → fill form → Create (3) | 3 |
| Approve a pending request | Drawer→Control Center (1) → Approvals tab already default (0) → double-click row (2) → Approve (3) → optional note → confirm (4) | 4 |
| Assign a calendar to a Site | Drawer→Admin Console (1) → Sites (2) → double-click a site (3) → Calendar section tab (4) → Assign Calendar (5) → pick calendar (6) → Assign (7) | 7 |
| Toggle a module's "Enabled" flag | Drawer→Settings (1) → Module Entitlements (2) → double-click module (3) → Enabled button (4) | 4 |
| Switch active tenant (header) | Header pill (1) → pick tenant from menu (2) | 2 |
| Switch active tenant (workspace) | Drawer→Tenant Management (1) → Switch button on row (2) | 2 |
| Revoke a user's scoped access grant | Drawer→Admin Console (1) → Roles & Access (2) → select grant row (3) → Revoke Access in inline inspector (4) | 4 |
| View why a Party can't see "Linked Procurement" | Drawer→Admin Console (1) → Parties (2) → double-click party (3) → Linked Procurement tab, only visible if Inventory enabled (4) — otherwise the tab silently doesn't exist, no explanation surfaced | 4 (if visible) / N/A |

### Component relationship diagram

```
AppShell (App.qml)
 └─ MainWindow.qml
     ├─ ShellHeader.qml ── TenantSwitcher.qml (bound to platformCatalog.tenantSwitcher)
     ├─ ShellDrawer.qml (global nav — reads shellModel.navigationItems)
     └─ workspaceLoader (Loader, source = shellModel.currentRouteSource)
          ├─ AdminWorkspace.qml → AdminConsolePage.qml
          │    ├─ Components.AdminNavSidebar          (local nav)
          │    ├─ Components.AdminEntityWorkspace × 9  (list surfaces)
          │    ├─ Detail.Admin*DetailPage × 11         (detail pages, SectionDetailPage-based)
          │    ├─ PlatformWidgets.AccessSecurityPanel  (Roles & Access)
          │    ├─ Sections.AdminSupportSection / AdminAuditSection
          │    ├─ Panels.AdminEntityDetailPanel        (visible:false — inert)
          │    └─ Dialogs.AdminDialogHost → 13 Platform.Dialogs.* editor dialogs
          ├─ ControlWorkspace.qml → ControlWorkspacePage.qml
          │    ├─ tab bar (Approvals/Audit/Escalations/System Events)
          │    ├─ Detail.ControlApprovalDetailPage
          │    └─ PlatformDialogs.ApprovalDecisionDialog
          ├─ SettingsWorkspace.qml → SettingsWorkspacePage.qml
          │    ├─ Components.SettingsSidebarNav        (local nav)
          │    ├─ Sections.Settings*Section × 7
          │    ├─ Detail.SettingsModuleDetailPage → PlatformDialogs.ModuleLifecycleDialog
          └─ TenantManagementWorkspace.qml → TenantManagementWorkspacePage.qml
               └─ (reads platformCatalog.tenantSwitcher — same controller as ShellHeader's TenantSwitcher)
```

### Ownership/responsibility table

| UI Concept | QML Owner | Python Owner | Shared Components | Notes |
|---|---|---|---|---|
| Organizations | `AdminConsolePage.qml` + `detail/AdminOrganizationDetailPage.qml` + `Dialogs/OrganizationEditorDialog.qml` | `organization_controller.py` / `organization_catalog_presenter.py` | `DataTable`, `EntityDialog`, `SectionDetailPage` | "Set Active" changes org runtime scope, no visible global indicator elsewhere |
| Calendars | `AdminCalendarDetailPage.qml` + 4 dialog types | `calendar_controller.py`, `admin_calendar_actions.py`, `admin_calendar_context.py` | same + `AdminDetailTableSection`, `AdminInformationalDetailSection` | richest single detail page in Platform |
| Roles & Access | `AccessSecurityPanel.qml` + `AdminAccessDetailPage.qml` | `access_workspace_controller.py` / `access_workspace_presenter.py` | `DataTable`, `ContextualActionToolbar` | 3 competing interaction surfaces (§23.8) |
| Module Entitlements | `SettingsModulesSection.qml` + `SettingsModuleDetailPage.qml` + `ModuleLifecycleDialog.qml` | `settings_workspace_controller.py` / `settings_catalog_presenter.py` | `DataTable`, `SectionDetailPage` | same underlying catalog also read (read-only) from Admin User detail's "Module Access" tab |
| Approval Queue | `ControlWorkspacePage.qml` + `ControlApprovalDetailPage.qml` + `ApprovalDecisionDialog.qml` | `control_workspace_controller.py` / `control_queue_presenter.py` | `DataTable`, `KpiStrip` | subscribes to 8 cross-module domain-event signals for auto-refresh |
| Support/Diagnostics | `AdminSupportSection.qml` + 5 sub-panels | `support_workspace_controller.py` / `support_workspace_presenter.py` | `SectionHeading`, `InlineMessage` | only place that can quit the app (Install Update handoff) |
| Tenant switch | `TenantSwitcher.qml` (header) + `TenantManagementWorkspacePage.qml` (workspace) | `tenant_switcher_controller.py` / `tenant_switcher_presenter.py` | none — bespoke in both | fully duplicated capability, two skins |
| Cross-module capability gating | every Admin detail page's `_sections` computation | `PlatformWorkspaceCatalog.isModuleEnabled/hasCapability` → `IntegrationCapabilityDesktopApi` | — | the only two-way Admin↔module-entitlement integration point |

---

## 25. Component Reuse / Duplication Findings

- **Reused well:** `DataTable`, `TableToolbar`, `EntityDialog`, `SectionDetailPage`, `ContextualActionToolbar`, `InlineMessage`/`SectionScopedInlineMessage`, `StatusChip`, `CodeFieldRow`/`FormField`, `AdminInformationalDetailSection` (the "governed elsewhere" boundary card is reused across 6+ detail pages verbatim).
- **Duplicated instead of reused:**
  - Four separate collapsible-grouped-nav-list implementations (`ShellDrawer`, `AdminNavSidebar`, `SettingsSidebarNav`, `SectionNavigationRail`) with near-identical visual language but no shared base component, and inconsistent collapsed widths (52 vs 48px).
  - `MasterDetailLayout.qml` exists specifically to provide a resizable master/detail `SplitView` and is used **nowhere** — every actual master/detail screen in Platform (Admin's list+panel, Access's grants+inspector) hand-rolls a fixed-width `RowLayout` instead.
  - `WorkspaceStateBanner.qml` exists in `Platform/Widgets/` but Platform doesn't use its own copy; three *other* modules (Maintenance, Project Management, Inventory & Procurement) each maintain a **separate, independent copy of the same-named component** rather than sharing one from `shared/`.
  - Tenant-switch UI (header pill vs. Tenant Management workspace) — full functional duplication, §14/§23.10.
  - `ControlMetricsSection.qml` duplicates what `ControlWorkspacePage.qml` already does inline with `AppWidgets.KpiStrip` — appears to be a superseded/legacy component left in place.
- **Dead/unused entirely:** `AdminCatalogPanel.qml`, `SettingsOverviewSections.qml` (both confirmed via repo-wide grep to have zero consumers beyond their own `qmldir` registration).

---

## 26. Technical Constraints Relevant to Future Redesign

- **QML import-path model:** every Platform-local component group (`Platform.Controllers`, `Platform.Dialogs`, `Platform.Widgets`) and every workspace's local dirs (`components`, `detail`, `dialogs`, `panels`, `sections`) is a directory-scoped QML module registered via a local `qmldir` — any redesign that reorganizes folders must re-declare these `qmldir` files or QML type resolution breaks at load time, not compile time.
- **`@QmlUncreatable` controllers:** every workspace controller is explicitly non-instantiable from QML (`@QmlUncreatable(...)`) — they only ever arrive as constructor-injected properties from `PlatformWorkspaceCatalog`; a redesign cannot introduce a new "ad hoc" controller instance directly in QML without Python-side wiring changes in `context.py`.
- **`DynamicTableModel` coupling:** any list that wants Python-side sorting/pagination must bind `sourceModel` to a `DynamicTableModel`; the moment a screen uses the plain `rows:` property instead (as Control's Escalations/System Events do today), pagination/sorting is entirely absent — this is a real technical fork in behavior, not just a data-source choice.
- **Domain-event coupling:** the auto-refresh behavior in Control/Settings/Access/Admin is driven by a shared global `domain_events` bus (`src.core.shared.events.domain_events`) — redesigning any workspace's refresh cadence must account for these subscriptions continuing to fire in the background regardless of which screen is visible.
- **`run_mutation`/`serialize_operation_result` contract:** every create/update/toggle action returns a `{ok, category, code, message}` shape that QML dialogs and detail pages depend on structurally (`result.ok`, `result.message`) to decide dialog-close vs. stay-open-with-error — any redesign of the mutation UX must preserve or deliberately migrate this contract.
- **Fixed dialog widths, content-driven heights:** dialogs cannot be freely resized by a redesign without touching each of the 15 individual `width:` values (no shared "dialog size" token/enum exists — each dialog picks its own literal pixel width from a range 420–660px).
- **No SplitView usage in practice:** despite `MasterDetailLayout.qml` existing, no Platform screen lets a user resize a nav rail or detail panel — any redesign introducing resizable panes is greenfield UX, not an extension of existing behavior.
- **Single fixed theme:** introducing dark mode requires adding conditional branches throughout `AppTheme.qml` (currently zero) rather than toggling an existing but unused mechanism (`themeMode` is tracked but not wired to any token).
- **Column customize only in one place:** `TableColumnCustomizer` is currently reachable only from Admin entity lists — any redesign that wants consistent column customization across Control/Settings tables needs new wiring, not just a visibility flag flip (those `TableToolbar` instances never set `showCustomize`).

---

## 27. Existing-State ASCII UI Catalogue

### 27.1 Admin Console — Organizations (list)

```
┌ Global Header ───────────────────────────────────────────────────────────────────┐
│ [☰] TECHASH ENTERPRISE  Admin Console      [Tenant▼] [🔍 search] [✅][🔔] [J]Jane │
├────────────┬───────────────┬──────────────────────────────────────────┬──────────┤
│ Global Nav │ Admin Local   │ Organizations                    N       │ (right   │
│ (248px)    │ Nav (220px)   │ ┌──────────────────────────────────────┐ │  panel   │
│ ▸Shell     │ ORGANIZATION  │ │[🔍search][Filter*][Columns][Refresh]│ │  288px — │
│ ▾PLATFORM  │ •Organizations│ │                        [+New Org]    │ │  NEVER   │
│  ○Admin ◀  │  Calendars    │ ├──────────────────────────────────────┤ │  VISIBLE │
│   Console  │  Sites        │ │Name        │Code/TZ  │Status│Version │ │  (visible│
│  ○Control  │  Departments  │ ├────────────┼─────────┼──────┼────────┤ │  :false) │
│   Center   │ WORKFORCE     │ │Acme Group  │ACM/UTC  │●Active│ v3    │ │          │
│  ○Settings │  Employees    │ │Beta Corp   │BET/EST  │Inactive│v1    │ │          │
│  ○Tenant   │  Users        │ │  ...        │        │      │       │ │          │
│   Mgmt     │  Parties      │ │                                      │ │          │
│ ▸PROJECT.. │ CONTENT       │ └──────────────────────────────────────┘ │          │
│ ▸MAINT..   │  Documents    │ (pagination bar HIDDEN — Python model)   │          │
│ ▸INVENTORY │  Structures   │                                          │          │
│            │ ACCESS        │                                          │          │
│            │  Roles&Access │                                          │          │
│            │ SYSTEM        │                                          │          │
│            │  Support      │                                          │          │
│            │  Audit        │                                          │          │
└────────────┴───────────────┴──────────────────────────────────────────┴──────────┘
* Filter button opens a popup that only says "Status, module, and date filters will appear here."
```

### 27.2 Admin Console — Organization Detail (full-page, opened on row double-click)

```
┌ Panel Header ──────────────────────────────────────────────────────────────────┐
│ [‹ Back] │ Acme Group                                          [Edit][Delete]* │
├───────────────┬──────────────────────────────────────────────────────────────┤
│ SECTIONS      │ ContextualActionToolbar: Overview      [Edit][Set Active][Refresh] │
│ •Overview ◀   │ ┌ Organization Summary ──────────────┐ ┌ Operational Notes ──────┐│
│  Runtime Scope│ │ Organization Code: ACM              │ │ [●Active]                ││
│  Audit        │ │ Display Name: Acme Group             │ │ Base currency: USD        ││
│               │ │ Timezone: Europe/Amsterdam           │ │ "This org is the active   ││
│               │ │ Base Currency: USD                   │ │  runtime scope..."        ││
│               │ │ Status: Active                       │ └──────────────────────────┘│
│               │ │ Version: 3                           │                             │
│               │ └──────────────────────────────────────┘                             │
└───────────────┴──────────────────────────────────────────────────────────────────────┘
* showEdit/showDelete are always false in practice — this header Edit/Delete pair from
  SectionDetailPage is never actually rendered; the REAL "Edit" action lives in the
  ContextualActionToolbar row below the header, a second/different action bar.
```

### 27.3 Control Center

```
┌ KPI Strip: [12 Pending][45 Approved][3 Rejected][128 Audit entries] ─────────────┐
├ Tabs: [Approvals 12] [Audit 128] [Escalations] [System Events] ──────────────────┤
│ ┌ TableToolbar: [search][Filter][Views][Refresh] ────────────────────────────┐   │
│ │ Request          │Submitted by│Status  │Module/Info                       │   │
│ │ Budget change #44 │J. Smith    │●Pending│PM / cost-baseline                │   │
│ │ ...                                                                        │   │
│ └────────────────────────────────────────────────────────────────────────────┘   │
│ (pagination bar shown, page-size 25/50/100)                                       │
│ Escalations tab (if selected): DataTable — ALWAYS shows "No active escalations —  │
│   all requests are within SLA" (hardcoded, rows: [] literal, no controller data)  │
│ System Events tab (if selected): DataTable — ALWAYS shows "No system events       │
│   recorded in this session" (hardcoded, same pattern)                             │
└────────────────────────────────────────────────────────────────────────────────────┘
```

### 27.4 Control Center — Approval Detail (Loader overlay inside Approvals column, KPI strip stays visible above)

```
┌ KPI Strip (still visible) ────────────────────────────────────────────────────┐
├ [‹ Back]  Budget change #44                                                    │
├ SECTIONS: Overview◀ / Request Payload / Decision History / Audit              │
│ ContextualActionToolbar: "Pending"          [Approve]  [Reject]                │
│ ┌ Request Summary ─────────────────────────────────────────────────────────┐  │
│ │ Submitted by: J. Smith   Module/Source: PM   Status: Pending             │  │
│ │ Context: "..."           Request ID: apr_0044                            │  │
│ └───────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘
[Approve]/[Reject] → ApprovalDecisionDialog (title changes per mode, one optional
  note textarea, primary button "Approve"/"Reject")
```

### 27.5 Settings

```
┌ Local Nav (220px) │ KPI Strip: [Licensed N][Enabled N][Planned N][Orgs N] ───────┐
│ PLATFORM          │ (same overview regardless of which section below is active) │
│ •Runtime ◀         │ ┌ Runtime Configuration ─────────────────────────────────┐ │
│  Module Entitlmts │ │ Theme Mode: light                                        │ │
│ CONFIGURATION      │ │ Platform API: Connected                                  │ │
│  Platform Defaults*│ │ Summary: "..."                                           │ │
│  Integration Caps  │ └──────────────────────────────────────────────────────────┘ │
│  Security*         │ (* = Platform Defaults & Security sections are STATIC —      │
│ SYSTEM             │    5/4 fixed cards, zero backend, zero edit control)         │
│  Support & Diag    │                                                              │
└────────────────────┴──────────────────────────────────────────────────────────────┘
```

### 27.6 Settings — Module Entitlement Detail (full-page Loader overlay covering local nav too)

```
┌ [‹ Back]  Project Management                                                   │
│ SECTIONS: Overview◀ / Capabilities / Consumers / Audit                         │
│ ContextualActionToolbar: "Licensed | Enabled"   [Lifecycle][Licensed][Enabled] │
│   ↑ Lifecycle opens ModuleLifecycleDialog (combo + Apply)                      │
│   ↑ Licensed/Enabled toggle IMMEDIATELY on click, no confirmation              │
│ ┌ Module Summary ───────────────────────────────────────────────────────────┐ │
│ │ Module: Project Management   Stage/License: production | Licensed         │ │
│ │ Lifecycle: Active            Runtime: Yes | Capabilities: scheduling,...  │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 27.7 Tenant Management

```
┌ Tenant Management — N tenants ────────────────────────────────── [Refresh] ────┐
│ ┌────────────────────────────────────────────────────────────────────────────┐ │
│ │ ● Acme Group (ACM)                                    [Current]           │ │
│ │ ● Beta Corp (BET)                                   [Switch]              │ │
│ │ ○ Gamma LLC (GAM)              [Suspended]           [Switch disabled]    │ │
│ └────────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
(No create/edit/delete tenant control anywhere on this screen or elsewhere in Platform)
```

### 27.8 Roles & Access (Admin Console leaf — 3 interaction surfaces in one screen)

```
┌ Roles & Access ─────────────────────────────────────────── [Refresh] ─────────┐
│ ACCESS ASSIGNMENT                                                              │
│ [Scope Type▼] [Scope▼] [Principal▼] [Role▼]                  [Assign Access]  │
│ "hint text about the selected scope..."                                        │
│─────────────────────────────────────────────────────────────────────────────  │
│ Scoped Access Grants                                                           │
│ ┌ DataTable ───────────────────────────┐┌ Grant Inspector (272px, on select)─┐ │
│ │ Principal │Username│Role  │Assigned  ││ [X close]                          │ │
│ │ J. Smith  │jsmith  │●Admin│2024-01-01││ J. Smith                           │ │
│ │ ...                                  ││ [●Admin]                           │ │
│ │ (double-click → AdminAccessDetailPage││ Username: jsmith                   │ │
│ │  replaces whole leaf content)        ││ Permissions: "..."                 │ │
│ │                                       ││ Assigned: "..."                    │ │
│ │                                       ││ [Revoke Access]                    │ │
│ └───────────────────────────────────────┘└─────────────────────────────────────┘ │
│─────────────────────────────────────────────────────────────────────────────  │
│ Account Security & Sessions                                                    │
│ ContextualActionToolbar (visible only when a session row selected):           │
│   "J. Smith"                    [Unlock Account][Revoke Sessions][Force Reset]│
│ ┌ DataTable (securityUsersTableModel) ─────────────────────────────────────┐  │
│ │ User      │Username│Status │Posture           │Details                   │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 27.9 Admin Console — Documents Detail (richest single-page inspector besides Calendars)

```
┌ [‹ Back]  Pump Maintenance Manual                                              │
│ SECTIONS: Overview◀ / Revisions / Linked Entities(3) / Approvals / Access / Audit│
│ ContextualActionToolbar: "Manual v2, current"     [Edit][Set Active][Refresh]  │
│ ┌ DocumentDetailPanel ───────────────────────────────────────────────────────┐│
│ │ Pump Maintenance Manual                                                    ││
│ │ [PDF] [Rev C] [Confidential: Internal]           Preview: [●Available]     ││
│ │                                                    [Open Source ↗]          ││
│ └──────────────────────────────────────────────────────────────────────────┘│
│ ┌ Metadata ───────────────────────────────────────────────────────────────┐  │
│ │ Document Code: DOC-0042   Title: Pump Maintenance Manual                 │  │
│ │ Document Type: Manual     Storage Kind: FILE_PATH                        │  │
│ └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 28. Redesign Questions — DO NOT ANSWER YET

1. Should Platform become one unified module screen with sub-tabs (Admin/Control/Settings/Tenants), or remain 4 independent top-level areas?
2. Should the disabled `AdminEntityDetailPanel` be re-enabled as the primary inspection surface (replacing full-page navigation for simple lookups), retired entirely, or redesigned?
3. Should single-click selection do *anything* visible again, and if so, what — inline preview, or nothing (current de facto state)?
4. Are Platform Defaults and Security in Settings meant to become real, editable, backend-connected configuration screens, or should they be removed/relabeled as documentation?
5. Should Escalations and System Events in Control Center be built out as real features, or removed from the tab bar until they are?
6. What should Filter/Views actually filter/switch to, across every screen that currently shows the placeholder popup?
7. Should the header's Global Search, Approvals bell, and Notifications bell be wired up, or removed until they are?
8. Should the tenant-switch capability be consolidated into one surface (header only, or workspace only), or is having both intentional (e.g. quick-switch vs. full-management)?
9. Should Tenant Management gain actual tenant create/suspend/archive controls, or is tenant lifecycle intentionally kept outside this UI (e.g. managed by a separate ops tool)?
10. Should the four independent collapsible-nav-list implementations be unified into one shared component, and if so, what should the canonical collapsed/expanded widths be (52/220 vs 48/220 today)?
11. Is a resizable (SplitView-style) master/detail layout desired anywhere, given `MasterDetailLayout.qml` already exists unused for exactly this purpose?
12. Should Roles & Access be simplified to one interaction model (list→detail, matching every other entity) instead of its current three-surface design?
13. What is the intended distinction, in the *UI itself* (not just in code), between Tenant and Organization, and should the active organization be surfaced somewhere persistent (header, breadcrumb) rather than only inside Organizations' row status?
14. Should a delete action exist for master-data entities, and if so what confirmation/audit-trail UX should gate it?
15. Should destructive-ish one-click actions (toggle-active, exception/recurring-event delete, module lifecycle/licensed/enabled changes) gain a confirmation step?
16. Is dark mode / theme-mode actually wanted, given the plumbing (`themeMode`) already exists but is disconnected from the token layer?
17. Is the `densityMode` (compact/comfortable/spacious) token system meant to become user-controllable, and if so, from where?
18. Should column customization (`TableColumnCustomizer`) be extended to Control/Settings/Access tables, given it currently only appears on Admin entity lists?
19. What should happen, from a UI-state perspective, when a user lacks permission for an action — is a distinct "permission denied" state desired (none exists today), or should permission simply be reflected via disabled controls without extra messaging?
20. Should the dead components (`AdminCatalogPanel`, `WorkspaceStateBanner` Platform copy, `MasterDetailLayout`, `SettingsOverviewSections`, and possibly `ControlMetricsSection`) be deleted, or were they retained deliberately for near-term reuse?

---

## 29. Evidence / Key File Index

**Shell entry point:** `src/ui_qml/shell/app.py`, `main_window.py`, `navigation.py`, `routes.py`, `context.py`, `qml_engine.py`, `qml_registry.py`, `runtime_session.py`, `login.py`; `src/ui_qml/shell/qml/App.qml`, `MainWindow.qml`, `HomeWorkspace.qml`, `ShellDrawer.qml`, `ShellHeader.qml`, `TenantSwitcher.qml`.

**Platform composition root:** `src/ui_qml/platform/context.py`, `routes.py`.

**Admin Console:** `src/ui_qml/platform/qml/workspaces/admin/AdminWorkspace.qml`, `AdminConsolePage.qml`, `AdminWorkspaceState.qml`, all files under `components/`, `detail/`, `dialogs/`, `panels/`, `sections/` (30 files total, listed in full in §4).

**Control Center:** `src/ui_qml/platform/qml/workspaces/control/ControlWorkspace.qml`, `ControlWorkspacePage.qml`, `ControlWorkspaceState.qml`, `detail/ControlApprovalDetailPage.qml`, `sections/ControlMetricsSection.qml`.

**Settings:** `src/ui_qml/platform/qml/workspaces/settings/SettingsWorkspace.qml`, `SettingsWorkspacePage.qml`, `components/SettingsSidebarNav.qml`, `detail/SettingsModuleDetailPage.qml`, all 7 `sections/*.qml`.

**Tenant Management:** `src/ui_qml/platform/qml/workspaces/tenants/TenantManagementWorkspace.qml`, `TenantManagementWorkspacePage.qml`.

**Platform Dialogs (15):** `src/ui_qml/platform/qml/Platform/Dialogs/*.qml`.

**Platform Widgets (6):** `src/ui_qml/platform/qml/Platform/Widgets/*.qml`.

**Python controllers/presenters/view-models opened:** `controllers/admin/admin_console_controller.py`, `access_workspace_controller.py`, `support_workspace_controller.py`, `organization_controller.py`, `admin_refresh_service.py`; `controllers/common/workspace_controller_base.py`, `mutation_runner.py`, `serializers.py`; `controllers/control/control_workspace_controller.py`; `controllers/settings/settings_workspace_controller.py`; `controllers/shell/tenant_switcher_controller.py`; `presenters/admin_presenter.py`, `organization_catalog_presenter.py`; `view_models/workspace.py`, `tenant.py`, `runtime.py`; `shared/models/data_table_model.py`.

**Shared design system files opened:** `shared/qml/App/Theme/AppTheme.qml`; `Layouts/WorkspaceFrame.qml`, `MasterDetailLayout.qml`; `Widgets/DataTable.qml`, `EntityDialog.qml`, `SectionDetailPage.qml`, `ContextualActionToolbar.qml`, `TableToolbar.qml`, `TablePaginationBar.qml`, `PageHeader.qml`, `StatusChip.qml`, `EmptyState.qml`, `InlineMessage.qml`, `KpiStrip.qml`, `MetricCard.qml`, `SectionCard.qml`, `SectionHeading.qml`, `CodeFieldRow.qml`, `FormField.qml`, `SectionScopedInlineMessage.qml`, `LazySectionLoader.qml`, `LazyObjectLoader.qml`, `SectionNavigationRail.qml`, `ActivityFeed.qml`, `AnchoredPopup.qml`; `Controls/CenteredDialog.qml`, `PrimaryButton.qml`, `SecondaryButton.qml`, `SearchField.qml`; `Icons/AppIcon.qml`.

**Dead-code confirmations (via repo-wide grep, not assumption):** `AdminCatalogPanel.qml` (only self-reference in `qmldir`), `WorkspaceStateBanner.qml` Platform copy (only self-reference, other modules have separate copies that are used), `MasterDetailLayout.qml` (only self-reference in `qmldir`), `SettingsOverviewSections.qml` (only self-reference in `qmldir`).
