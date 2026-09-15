# Platform &amp; Project Management — Current-State UI/UX Audit

**Type:** Read-only audit. No implementation, no redesign.
**Scope:** Platform (`src/ui_qml/platform/`) and Project Management (`src/ui_qml/modules/project_management/`), plus the shell navigation architecture and shared QML component library both depend on.
**Method:** Four parallel deep-read investigations (Platform; PM Projects+Tasks; PM remaining workspaces; Shell nav + shared components; cross-cutting leak/duplication/visual/accessibility sweep), synthesized here. Every finding is labeled **VERIFIED** (the investigating agent read the cited file) or **INFERRED** (deduced, not line-read) as it was reported.
**Repository state:** starting HEAD `6a6f147af9b7c6e2c15255f764cf5201b5e592cc`, ending HEAD identical, `git status` clean throughout — no files were modified.

---

## 1. Executive summary

Platform and Project Management are both **fully implemented, non-trivial, production-shaped** areas — this audit found no large placeholder pages in either module, and only two genuinely placeholder *behaviors* buried inside otherwise-real pages (Platform Control's "Views" popup; a hardcoded hidden Settings-runtime coupling). The architecture is consistently layered (Domain → Application service → `Desktop*Api` → Presenter → Controller → QML) across both modules, and a real, working, single-source-of-truth navigation-accessibility mechanism (`NavigationAccessibilityCoordinator` → `PlatformRuntimeApplicationService.list_accessible_modules()`) now correctly gates the top-level "Project Management" nav entry, Global Overview's module card, and Global Overview's Quick Actions from one shared call.

That said, three systemic problems recur across almost every page in both modules and should shape any future blueprint:

1. **Raw exception leaks.** Nearly every workspace's *data-refresh* error path (and most workspaces' *mutation* error path too) falls through to `self._set_error_message(str(exc))` with no sanitization. Only PM Financials' mutation path is properly hardened and regression-tested (`test_financials_mutation_error_boundary.py`); PM Resources' mutation path is the second-best. Every other mutation path (Portfolio, Scheduling, Review Queue, Register, Collaboration, self-service Timesheets, Projects, Tasks) and literally every refresh path in both modules is unguarded.
2. **Zero accessibility markers in either module's own QML.** `Accessible.role`/`Accessible.name`/`activeFocusOnTab` appear in 4 of 63 shared-library files (`ModuleCard`, `InfoTip`, partially `GroupedNavigationRail`, `ActionCenterRow` — all outside Platform/PM), and in **0 of the 24 interactive files found directly inside Platform or PM**. The gap is systemic, not isolated, because it's inherited from shared components too: `DataTable` (49 total consumers) and the live `RecordListCard.qml` (3 PM consumers) both have zero accessibility support.
3. **Inconsistent permission gating at the UI layer.** Only 3 of PM's 11 workspaces (Projects' import gate, Scheduling's baseline-approve gate, Resources' skills/create gate) actually check a `PMCapabilityController` flag in QML, despite the controller exposing 6 flags. Register's edit/delete are hardcoded `enabled: true`; Collaboration's approve/reject check only row *data state*, not the `approval.decide`-backed `canApprovePmRequest` flag that Scheduling's near-identical baseline-approval action does check. This is not a security hole (server-side enforcement is separate and unverified-but-presumed-present) but it is a real UX/consistency defect: the same class of action is gated differently depending on which workspace you're in.

Two structural findings matter most for the requested future two-level navigation:
- **Level 1 (global) navigation is real, registry-backed, and accessibility-filtered** (`QmlRoute`/`QmlRouteRegistry`/`NavigationAccessibilityCoordinator`). It currently exposes exactly 3 entries: Overview, Platform, Project Management.
- **Level 2 (per-module) navigation is NOT unified.** Platform and PM each hand-roll their own internal destination list (`PlatformNavigation.qml`'s `_allDestinations` array vs. `PMWorkspaceNavigationController.navigationItems`), with no shared schema, no shared registry, different content-instantiation strategies (Platform: eager/always-alive; PM: lazy `Loader`, cached after first visit), and — critically — **Platform's internal nav uses a completely separate, non-converged permission-gating mechanism** (`PlatformNavigation.qml`'s hardcoded per-destination `requiredPermissions` array checked via `hasAnyPermission()`) from the shell-level `NavigationAccessibilityCoordinator`. A code comment in `module_access_policy.py` explicitly documents this as a known, deliberately-deferred convergence, not an accident. Any future two-level nav design must either converge these or explicitly accept two policy layers (module-visibility vs. within-module-destination-visibility) as a permanent, intentional split.

Platform is the stronger reference implementation for CRUD/master-data/admin patterns: its 10 "flat entity" pages (Organizations, Sites, Departments, Employees, Parties, Calendars, Users, Documents, Structures) share one exceptionally consistent architecture (`AdminEntityWorkspace` list + `InspectorPanel` + `Admin*DetailPage` + `AdminDialogHost`). PM is broader and less uniform — Financials, Portfolio, Scheduling, and Timesheets each follow genuinely different page shapes appropriate to their domain, but that variety comes with real inconsistency cost (see §7–§9). PM's Projects and Tasks workspaces are the two most fully-realized "list → inspector → detail-with-lazy-sections" pages in the entire codebase and are the best PM reference candidates, despite three specific inconsistencies between the two of them (§7–§9, §14).

---

## 2. Current Platform architecture

### 2.1 Route map (VERIFIED)

Platform contributes exactly **one** shell-level route:

| route_id | title | qml_path | `appears_in_navigation` |
|---|---|---|---|
| `platform.workspace` | "Platform" | `src/ui_qml/platform/qml/workspace/PlatformWorkspace.qml` | True |

`PlatformWorkspace.qml` is a one-line pass-through (`PlatformWorkspacePage {}`). Everything else lives *inside* this one route as client-side navigation.

### 2.2 Navigation tree (as-built)

```
Platform (route: platform.workspace)
├── Overview                                        [no permission gate]
├── Organization  (nav group)
│   ├── Organizations                                [settings.manage]
│   ├── Sites                                         [settings.manage, site.read]
│   ├── Departments                                    [settings.manage, department.read]
│   ├── Employees                                       [employee.read]
│   └── Parties                                          [settings.manage, party.read]
├── Calendars                                        [task.read]              (ungrouped)
├── Identity & Access  (nav group)
│   ├── Users                                        [auth.manage | auth.read | access.manage | security.manage]
│   └── Access  (nav label "Access", page title "Roles & Access")            [access.manage]
├── Documents  (nav group)
│   ├── Documents                                    [settings.manage]
│   └── Structures  (page title "Document Structures")                       [settings.manage]
├── Control  (nav group)
│   ├── Approvals                                    [approval.request, approval.decide]
│   └── Audit                                        [audit.read]
├── Settings                                         [settings.manage] — internal sidebar: Runtime / Module Entitlements / Integration Capabilities / Diagnostics
└── Tenant Administration  (nav label; page title "Tenant Management")        [platform.admin, INFERRED gap — see §14]
```

All 15 destination ids in `PlatformNavigation.qml` map 1:1 to a visible surface in `PlatformWorkspacePage.qml` — no dead nav entries, no nav entry missing a surface. All 15 are instantiated **eagerly as always-alive siblings** inside one `Item`, toggled by `visible:` (not lazy `Loader`-gated) — the opposite strategy from PM (§3.2).

### 2.3 Page inventory (VERIFIED — condensed; full per-page detail, including exact controller/presenter/Desktop-API file paths, empty-state copy, and loading-state copy, was captured by the source investigation and is summarized here)

| Page | Pattern | Controller | Desktop API | Status |
|---|---|---|---|---|
| Overview | KPI/section overview, hardcoded clickable-metric whitelist | n/a (reads sub-controllers) | `PlatformRuntimeDesktopApi` + 6 entity APIs | IMPLEMENTED |
| Organizations / Sites / Departments / Employees / Parties / Calendars / Users / Documents / Structures | `AdminEntityWorkspace` list + `InspectorPanel` + `Admin*DetailPage` + `AdminDialogHost` (identical skeleton, 9 pages) | `Platform*Controller` per entity (e.g. `organization_controller.py::PlatformOrganizationController`) | `Platform*DesktopApi` per entity | IMPLEMENTED (all 9) |
| Access ("Roles & Access") | Two internal tabs: Scope Access (`AdminEntityWorkspace`) + Account Security (raw `DataTable`) | `access_workspace_controller.py::PlatformAdminAccessWorkspaceController` | `PlatformAccessDesktopApi` + `PlatformUserDesktopApi` | IMPLEMENTED. Explicitly documented as an R5.2 consolidation of 3 previously-separate patterns. |
| Control (Approvals + Audit) | One page, `activePanel` alias | `control_workspace_controller.py::PlatformControlWorkspaceController` | `PlatformApprovalDesktopApi`, `PlatformEnterpriseAuditDesktopApi` | IMPLEMENTED, with an embedded **PLACEHOLDER**: the "Views" popup (5 saved-view rows: "Pending Only," "Rejected," "Recent Decisions," "High Risk," "My Reviews") only closes the popup on click — no filter is actually applied. |
| Settings | 4-section internal sidebar: Runtime, Module Entitlements, Integration Capabilities, Diagnostics | `settings_workspace_controller.py::PlatformSettingsWorkspaceController` | `PlatformRuntimeDesktopApi` + `IntegrationCapabilityDesktopApi` | IMPLEMENTED. Runtime section's Theme/Density controls write to the **shell-wide** `shellModel`, not a Platform-scoped setting — an information-architecture anomaly (app-wide preference living inside one module's Settings). |
| Tenant Administration / Tenant Management | List + create dialog + per-row switch | `tenant_switcher_controller.py::TenantSwitcherController` (doubles as ContextBar's switcher) | `PlatformTenantDesktopApi` | IMPLEMENTED. **No `_is_accessible()`/`WORKSPACE_PERMISSIONS` server-side-style pre-gate** the way Access/Control/Settings have — relies only on nav-hiding + button `enabled:` (INFERRED defense-in-depth gap). |

### 2.4 Common cross-page behavior (the 9 flat-entity pages)

- **Primary action**: "New {Entity}." **Secondary**: Refresh, column Customize.
- **List/table**: `AppWidgets.DataTable` + Python `DynamicTableModel`; single-click → `InspectorPanel`; double-click/Activate → full detail page.
- **Loading**: `InlineMessage` (tone "info"), `"Loading..."` / `"Saving changes..."`.
- **Empty state**: entity-specific curated copy, e.g. `"No organizations are available yet."`, `"No sites are available yet."`, `"No calendars available."`
- **Error state**: curated fallback only when `result.error is None`; when an error *is* present, `result.error.message` is passed through **verbatim**. The one confirmed severe instance of raw leakage is Support/Diagnostics (§13).
- **Permission gating**: a nav-level client-side gate (`PlatformNavigation._isVisible`) *and* a separate page-level `_canWrite`/`_canManageX` binding — both explicitly documented in code comments as **UX-only optimizations**; the backend enforces independently regardless (fail-open-at-UI, fail-closed-at-server posture).
- **Tenant/org scope**: centralized in `ContextBar` (tenant + organization switchers) inside `PlatformWorkspacePage.qml`, not per-page; switching triggers `refreshAllWorkspaces()` + `refreshCurrentPermissions()`.

### 2.5 Major issues found in Platform

| Issue | Evidence | Severity |
|---|---|---|
| Label inconsistency: nav "Access" vs. page title "Roles & Access"; nav "Tenant Administration" vs. page title "Tenant Management" | `PlatformNavigation.qml` vs. `AccessWorkspacePage.qml`/`TenantManagementWorkspacePage.qml` | Low — cosmetic, but visible to every admin user |
| Placeholder "Views" popup inside a real page | `ControlWorkspacePage.qml:444-480` | Medium — looks functional, does nothing |
| Orphaned component `Platform/Widgets/RecordListCard.qml` | imported once (`SettingsWorkspacePage.qml:13`) but never instantiated; 95%-identical to PM's live `RecordListCard.qml` | Low (dead code), but a real duplication signal — see §14 |
| Raw exception leak in Support/Diagnostics | `src/core/platform/api/desktop/support/support.py` — `str(exc)` in `get_paths()` (121), `export_diagnostics_to()` (261), `create_incident_report()` (305), `install_available_update()` (386), `list_activity()` (216) | Medium |
| Settings' theming controls are shell-wide, filed under a Platform module page | `SettingsRuntimeSection.qml` writes `shellModel` | Low/structural — relevant to the future Settings-area decision (§13, §18) |
| Overview's clickable-KPI map is a hardcoded whitelist | `PlatformWorkspacePage.qml:175-182` — only 6 metric labels are wired clickable | Low |
| Tenant Administration has no explicit `_is_accessible()` gate unlike its siblings | `tenant_switcher_controller.py` (INFERRED) | Low/Medium |
| No test file found asserting the RecordListCard dead-code state, the Views-popup placeholder, or the Support leak | see §15 | — |

No dead top-level pages, no orphaned routes, and no evidence of a leftover pre-R4/R5 monolithic admin console — the old `AdminConsolePage.qml` was genuinely deleted, not left behind (confirmed via code-comment cross-references and absence on disk).

---

## 3. Current Project Management architecture

### 3.1 Route map (VERIFIED)

PM contributes **one** navigable shell route plus 10 non-navigable "compatibility bridge" routes (kept for old deep-link ids, excluded from the drawer):

| route_id | `appears_in_navigation` | qml_path |
|---|---|---|
| `project_management.workspace` | **True** | `qml/workspace/ProjectManagementWorkspace.qml` → `ProjectManagementWorkspacePage.qml` |
| `project_management.{dashboard,portfolio,projects,tasks,scheduling,resources,financials,register,collaboration,timesheets}` | False (×10) | `qml/workspace/compatibility/*Route.qml` |

**Gap**: `review_queue` is the only one of PM's 11 internal workspace keys with **no** compatibility route at all — not deep-linkable, unlike all 10 siblings (`routes.py:11-22`, `navigation.py:31-35`).

### 3.2 Navigation tree (as-built)

```
Project Management (shell route, single entry)
 └─ Internal nav rail (PmWorkspaceNavigation.qml, GroupedNavigationRail — same shared widget Platform uses)
     ├─ Overview        → dashboard workspace key   (destination "overview")
     ├─ Portfolio        → portfolio                 (destination "portfolio")
     ├─ Work
     │    ├─ Projects       (see §3.3)
     │    ├─ Tasks          (see §3.3)
     │    ├─ Planning       → scheduling workspace key    (nav label "Planning" ≠ key "scheduling")
     │    └─ Timesheets      → resource_timesheets workspace key (self-service; nav label "Timesheets")
     ├─ Workload Management
     │    ├─ Resources       → resources
     │    └─ Review Queue    → workspace key "timesheets" folder (⚠ folder-name swap, see §14) — NOT route-addressable
     ├─ Finance
     │    └─ Finance         → financials workspace key (nav label "Finance" ≠ key "financials")
     └─ Governance
          ├─ Register        → register
          └─ Collaboration   → collaboration
```

Rendering: a `Repeater` over 11 `{key, file}` pairs, each behind a `Loader` gated `active: root._activatedKeys[key] === true` — **lazy-load-once-then-cache**, the opposite of Platform's eager-always-alive strategy (§2.2).

### 3.3 Page inventory (condensed; Projects/Tasks were audited at full per-page depth matching Platform's — same field list: route, title, QML tree, controller, presenter, Desktop API, actions, states, permission, scope, status)

| Workspace | Pattern | Controller (headline) | Desktop API (headline) | Status |
|---|---|---|---|---|
| **Projects** | List (`TableToolbar`+`DataTable`+pagination+`BulkActionBar`) + `InspectorPanel` (side panel) + `SectionDetailPage` (5 sections: Overview/Tasks/Resources/Risks/Activity) + `dialogs/` | `ProjectManagementProjectsWorkspaceController` | `ProjectManagementProjectsDesktopApi` | IMPLEMENTED |
| **Tasks** | Same skeleton as Projects **minus the InspectorPanel** (row-select only selects, no side preview) + `SectionDetailPage` (8 sections: Details/Assignments/Skills/Dependencies/Time/Schedule Impact/Activity/Discussion) + richest dialog set (7) in PM | `ProjectManagementTasksWorkspaceController` (most sub-controller-decomposed in PM: exposes `assignmentsController`, `dependenciesController` etc. directly to QML) | `ProjectManagementTasksDesktopApi` (largest single-workspace API surface besides Financials) | IMPLEMENTED |
| **Overview/Dashboard** | Pure read-only KPI/analytics landing page; no list/detail pattern at all | `ProjectManagementDashboardWorkspaceController` | `ProjectManagementDashboardDesktopApi` | IMPLEMENTED. **Zero `run_mutation` calls anywhere** — genuinely read-only. |
| **Portfolio** | Tab strip (`DetailTabBar`: Executive/Heatmap/Intake/Scenarios/Capacity/Dependencies) + `SectionDetailPage` drill-in from Heatmap | `ProjectManagementPortfolioWorkspaceController` | `ProjectManagementPortfolioDesktopApi` | IMPLEMENTED |
| **Planning/Scheduling (incl. Baseline review)** | Custom panel tab strip (Overview/Gantt/Resource Leveling/Diagnostics/**Baselines**/Calendars/Activity Feed) + `NavOverflowMenu` for overflow | `ProjectManagementSchedulingWorkspaceController` (largest controller besides Financials: 20+ submodules) | `ProjectManagementSchedulingDesktopApi` | IMPLEMENTED. Baseline review (`SchedulingBaselinesPanel.qml`) is fully built: Save/Submit/Approve/Reject/Delete, Approve/Reject gated on `canApproveBaseline` (`baseline.approve`) — one of only 3 PM workspaces with real capability gating (§7 of exec summary). |
| **Resources** | Identical skeleton to Projects/Tasks: `TableToolbar`+`DataTable`+`InspectorPanel`+`SectionDetailPage` (Overview/Skills/Availability/Projects/Assignments/Activity) | `ProjectManagementResourcesWorkspaceController` | `ProjectManagementResourcesDesktopApi` | IMPLEMENTED. **Best-hardened mutation path in all of PM** (4/4 `run_mutation` calls use `safe_errors=True`). |
| **Review Queue** | List (`DataTable`) + `TimesheetReviewInspector` + decision dialog | `ProjectManagementTimesheetsWorkspaceController` (exposed as `pmCatalog.reviewQueueWorkspace`) — lives in folder `qml/workspaces/timesheets/` | `ProjectManagementTimesheetsDesktopApi` (shared with self-service Timesheets) | IMPLEMENTED. Approve/Reject/Lock/Unlock gated only by data state, **no capability check**. |
| **Timesheets (self-service)** | Structurally distinct: bare `Item` root (not `WorkspaceFrame`), flat table + dialogs, **no** InspectorPanel/detail drill-in — lives in folder `qml/workspaces/resource_timesheets/` | `ProjectManagementResourceTimesheetsController` (exposed as `pmCatalog.timesheetsWorkspace`) | `ProjectManagementTimesheetsDesktopApi` | IMPLEMENTED |
| **Finance (Budgets/Costs/Billing/Forecasts/Rate Cards)** | Structurally unique: **no list landing page** — always in `SectionDetailPage` detail mode, scoped by a persistent project picker. Sections: Overview, Planning (budgets/planned costs/forecast), Costs (actuals/posting failures/commitments/rates), Performance (EVM/variance/cost phasing/reports), Commercial (billing/profitability/accounting), Controls | `ProjectManagementFinancialsWorkspaceController` (**largest** controller/API surface in PM, ~1800-line Desktop API, 100+ methods) | `ProjectManagementFinancialsDesktopApi` | IMPLEMENTED. **Best-hardened mutation path in the whole codebase**: every one of ~40 mutation methods funnels through one helper with `safe_errors=True` + a dedicated regression test (`test_financials_mutation_error_boundary.py`). Refresh path still leaks, however (§14). |
| **Register** | List (`DataTable`+`BulkActionBar`) + `SectionDetailPage` (Details/Impact/Response/Links) | `ProjectManagementRegisterWorkspaceController` | `ProjectManagementRegisterDesktopApi` (backed by `application/risk/RegisterService`) | IMPLEMENTED. Edit/Delete hardcoded `enabled: true` — **no capability gate at all**. |
| **Collaboration** | Custom tab strip (Inbox/Mentions/**Approvals**/Activity) → shared `DataTable` or `ActivityFeed` → `SectionDetailPage` | `ProjectManagementCollaborationWorkspaceController` | `ProjectManagementCollaborationDesktopApi` | IMPLEMENTED. Approve/Reject gated only by row state, **not** the `canApprovePmRequest` capability that exists specifically for this — inconsistent with Scheduling's baseline approval. |

### 3.4 Major issues found in PM

| Issue | Evidence | Severity |
|---|---|---|
| Review Queue has no shell/compatibility route — not deep-linkable, unlike all 10 sibling workspaces | `routes.py`, `navigation.py:31-35` | Medium |
| Folder-name / nav-item-name swap: `qml/workspaces/timesheets/` implements **Review Queue**; `qml/workspaces/resource_timesheets/` implements **Timesheets** | `ProjectManagementWorkspacePage.qml:86-88` | Medium — actively confusing for future contributors |
| 6 dead `*Workspace.qml` wrapper files, never imported by namespace anywhere (Dashboard/Portfolio/Scheduling/Register/Collaboration/Financials) | zero grep hits for their qmldir import path | Low (dead code) |
| Raw exception leak on the **refresh/load** path in essentially every workspace | Financials (`financials_refresh_mixin.py:257-266`), Portfolio (`portfolio_workspace_controller.py:397-399`), Resources (`resources_workspace_controller.py:605-606`), Register (`register_workspace_controller.py:281-282`), Review Queue (`review_queue_controller.py:98-99`, `refresh_service.py:52-54`), Collaboration (`refresh_service.py:59-61`), Scheduling (`scheduling_state_loader.py:104-106`) | **High** — this is the single most pervasive defect found in the entire audit |
| Raw exception leak on the **mutation** path everywhere except Financials and Resources | Portfolio (`mutation_handler.py`), Scheduling (`mutation_handler.py` + `leveling_actions.py`, the latter with an even-worse manual `try/except`), Review Queue (`mutation_handler.py`), Register (`register_mutation_handler.py` + `register_bulk_handler.py`), Collaboration (`mutation_handler.py`), self-service Timesheets (`resource_timesheets_controller.py`, 3/3 calls), Projects (0/9 call sites use `safe_errors=True`), Tasks (0/20 call sites) | **High** |
| Inconsistent capability gating: only Projects (import), Scheduling (baseline approve), Resources (skills/create) check `PMCapabilityController` in QML; Register and Collaboration do not, despite equivalent actions existing | see §3.3 rows | Medium |
| Structural inconsistencies between Projects and Tasks specifically | InspectorPanel present/absent; native `FileDialog` vs. dedicated `TasksExportDialog`; `pmNavigation` deep-link wiring present only in Tasks; detail-section naming "Overview" (Projects) vs. "Details" (Tasks) for the equivalent first section | Medium |
| Timesheets (self-service) uses a bare `Item` root instead of the `WorkspaceFrame` convention every other PM page follows | `ResourceTimesheetsPage.qml:12` | Low/Medium |

### 3.5 Test coverage gaps specific to the leak pattern

Only Financials has a dedicated `test_financials_mutation_error_boundary.py` proving a raw DB error doesn't leak. **No equivalent test exists for Portfolio, Scheduling, Review Queue, Register, Collaboration, self-service Timesheets, Projects, or Tasks** — meaning the pervasive leak pattern in §3.4 is not only unfixed but also unguarded by any regression test that would catch a regression or confirm a future fix.

---

## 4. Shell/navigation architecture

### 4.1 Level 1 (global) — real, registry-backed, VERIFIED end-to-end

`src/ui_qml/shell/routes.py` (`QmlRoute`) → `platform/routes.py` + `modules/project_management/routes.py` → `shell/qml_registry.py` (`QmlRouteRegistry`, raises on duplicate ids) → `shell/navigation.py` (`NavigationItemViewModel`, `filter_navigation_items()`, `is_navigation_item_accessible()`) → `shell/navigation_accessibility.py` (`NavigationAccessibilityCoordinator`) → `shell/context.py` (`ShellContext.navigationItems`) → `shell/qml/ShellDrawer.qml` (pure renderer, zero accessibility logic of its own).

**Today this chain exposes exactly 3 navigable entries: Overview, Platform, Project Management.** `_ALWAYS_AVAILABLE_MODULE_CODES = frozenset({"shell", "platform"})` means Overview and Platform are never filtered; only Project Management (and any future `EnterpriseModule`) is gated by `list_accessible_modules()`.

### 4.2 The accessibility policy is genuinely converged across 3 consumers (VERIFIED)

| Consumer | Call site |
|---|---|
| Shell top-level nav filtering | `navigation_accessibility_presenter.py:22` |
| Global Overview PM module card | `pm_module_overview_contributor.py:53-58` (`_is_accessible`) |
| Global Overview Quick Actions | `global_overview_service.py:108-126` → `global_overview_presenter.py:245-254` |

All three call `PlatformRuntimeApplicationService.list_accessible_modules()` → `is_module_accessible()` → `MODULE_PERMISSION_PREFIXES` (`module_access_policy.py`). This part of the architecture is a real, working single source of truth — not aspirational.

### 4.3 Level 2 (per-module) — NOT unified, and Platform's is NOT converged onto the level-1 policy

- **Platform's internal nav** (`PlatformNavigation.qml`, 15 destinations) carries its **own separate, hardcoded** per-destination `requiredPermissions` array, checked via `PlatformWorkspaceCatalog.hasAnyPermission()` — a different code path from `module_access_policy.py` entirely. A comment in `module_access_policy.py` explicitly flags this as a known, deliberately-deferred convergence: *"Existing QML navigation (`PlatformNavigation.qml`) still carries its own inline destination→permission mapping and has not been converged onto this policy — that convergence is a pending frontend step, not done here."*
- **PM's internal nav** (`PMWorkspaceNavigationController.navigationItems`, 11 destinations) is a third, independent hardcoded list with no permission gating logic visible in this audit at all (workspace-level accessibility for PM's own destinations was not found gated by anything analogous to Platform's `requiredPermissions`).
- Neither module's internal nav is backed by anything resembling the level-1 `QmlRoute`/`QmlRouteRegistry` schema — there is no unified "route" concept spanning both levels today.
- **Content-instantiation strategy differs**: Platform eagerly instantiates all 15 destination pages as always-alive siblings; PM lazily instantiates via `Loader{active: ...}`, caching after first visit.

### 4.4 `scopeChanged` — a real, working pub/sub fan-out (VERIFIED)

Emitters (wired in `app.py`): `TenantSwitcherController.tenantSwitched` (Platform-owned) and the shell-owned `OrganizationSwitcherController.organizationSwitched`. Subscribers (independent, self-registered): `NavigationAccessibilityCoordinator.refresh`, `NotificationsController._on_scope_changed`, `GlobalOverviewController._on_scope_changed`. `ShellContext.setNavigationItems()` additionally redirects the current route to `shell.home` if it becomes inaccessible after a refresh — a real safety net, not aspirational.

**Note**: there appear to be **two separate organization-switcher-shaped controllers** in the running app — Platform's own (`platformCatalog.organizationSwitcher`, used by `PlatformWorkspacePage`'s `ContextBar`) and the shell-owned one (`organizationSwitcherController`, used by `ShellHeader.qml`). Whether this is intentional (two independent UI surfaces, same underlying data) or a latent duplication was **not fully resolved** in this pass — flagged as a follow-up question (§23).

### 4.5 No breadcrumbs anywhere (VERIFIED — zero grep hits, both for the word and for any hierarchical trail UI)

The only "where am I" affordances today are `ShellHeader.qml`'s current-route-title + module-label pill, and `ShellDrawer.qml`'s active-route highlight (accent background + 3px left bar). Neither Platform's nor PM's internal navigation has any drill-down breadcrumb either — PM's `openEntity(workspace_key, entity_id, section_id)` drill-down state exists in the controller (`routeState`) but is never surfaced as a breadcrumb trail in QML.

### 4.6 Responsive/collapse behavior

`Theme.AppTheme.narrowLayoutBreakpoint = 1280` drives **both** `ShellDrawer.qml`'s auto-collapse **and** `GroupedNavigationRail`'s `autoCollapseAtNarrowWidth` (used by both Platform's and PM's internal rails) — meaning below 1280px width, the top-level drawer *and* whichever module's internal rail collapse to icon-only **simultaneously**, which can leave very little horizontal room for content on a genuinely narrow window. A **separate**, unrelated breakpoint set (`overviewNarrowWidthBreakpoint=1024`, `overviewCompactWidthBreakpoint=1440`, `overviewCompactHeightBreakpoint=820`, via `layoutClassFor()`) is used only by `OverviewWorkspace.qml`, not shared with the drawer or either module's internal nav.

### 4.7 Route-selection call chain (QML click → re-render)

`ShellDrawer.qml` row click → `shellModel.selectRoute(routeId)` (`ShellContext.selectRoute`, validates against the **currently filtered** `known_route_ids` — so a stale/accessibility-filtered route id cannot be selected even by an old click) → `currentRouteIdChanged`/`currentRouteSourceChanged` → `MainWindow.qml`'s `asynchronous: true` `Loader` re-sources → `Loader.onLoaded` duck-types the new root item and assigns `shellModel`/`platformCatalog`/`pmCatalog`/`globalOverviewController` if those properties exist.

---

## 5. Shared UI component inventory

63 files under `src/ui_qml/shared/qml/App/{Widgets,Controls,Layouts}` (plus `Theme/`, `Icons/`, `Models/`).

**Ready to serve as design-system primitives largely as-is**: `WorkspaceFrame`, `PageHeader`, `EntityDialog` (+ `DialogActionFooter`, `CenteredDialog`), `PrimaryButton`/`SecondaryButton`, `SearchField`, `ModuleCard` (best accessibility example in the whole library), `InfoTip` (second-best accessibility example), `GroupedNavigationRail`, `FormField`, `SectionHeading`, `ContextualActionToolbar`.

**Need work before new modules (Inventory, Procurement, Accounting, Payroll, QHSE, HR) safely build on them**:

| Component | Consumers | Problem |
|---|---|---|
| `DataTable.qml` | 49 total (7 Platform + 42 PM) | Zero `Accessible.role`/`Accessible.name`; partial keyboard (Up/Down/Return only, no Left/Right/Home/End); one hardcoded `color: "white"` bypassing theme tokens. Highest-leverage fix in the codebase given consumer count. |
| `StatusChip.qml` | 8 Platform + 15 PM | Bakes in ~35 hardcoded, PM/procurement-shaped status strings directly into its own classification logic rather than accepting a caller-supplied tone. A future module with different status vocabulary either gets silently miscategorized as `"neutral"` or must shoehorn its statuses into this list. |
| `InlineMessage.qml` | 23 Platform + 45 PM | No alert/live-region accessibility semantics despite being the app's single standard error/validation-feedback surface (used by `FormField` and `EntityDialog` both). |
| Every bare `Rectangle`+`MouseArea` "button" | `TableToolbar`'s filter/customize/views buttons, `TablePaginationBar`'s prev/next, `NavOverflowMenu`, `ContextBar`'s chips | Not keyboard-focusable or screen-reader-exposed at all (not real `Control` subclasses, unlike `PrimaryButton`/`SecondaryButton` which get this for free). |
| `SlideOverPanel.qml` | 1 consumer (Notifications) | No Escape-to-close, no focus trap/return — immature relative to `EntityDialog`'s pattern; risky to promote as *the* standard drawer before hardening. |

**Confirmed dead components** (zero instantiations anywhere): `FilterBar.qml`, `AppDivider.qml`, `RecordDetailPage.qml`, `SectionAnchor.qml` (referenced only in comments), and `SectionHeader.qml` — the last is a particular risk because it's a near-name-collision with the very-much-alive `SectionHeading.qml` (22 Platform + 24 PM consumers); a future contributor could easily instantiate the wrong one by typo.

**Four competing "there are more destinations than fit" patterns coexist** with no documented guidance on which to use when: `GroupedNavigationRail` (rail w/ collapsible groups), `NavOverflowMenu` (overflow popup, PM-only today), `DetailTabBar` (tab strip, PM-only today, no `Accessible.PageTabList` semantics, no keyboard left/right cycling), and `SectionNavigationRail` (private to `SectionDetailPage`, not independently reusable despite living in the shared folder).

**Platform-vs-PM own-QML accessibility (cross-cutting audit, VERIFIED)**: 0 of 63 shared files outside the 4 listed above carry any `Accessible.*` marker; and **0 of 24 interactive files found directly inside Platform or PM's own QML** (9 Platform, 15 PM) carry any accessibility marker either — including the 2 PM files that do have `Keys.onPressed` keyboard handling (`ActualLifecycleDialog.qml`, `SchedulingGanttRowsViewport.qml`), which still lack `Accessible.role`/`Accessible.name`.

---

## 6. Page-family matrix

| Family | Best current example | Weakest current example | Notes |
|---|---|---|---|
| 1. Overview / Dashboard | Global Overview (`shell/qml/OverviewWorkspace.qml`, out of this audit's scope but the de facto reference) — within scope, PM Dashboard (pure read, well-composed KPI/analytics page, zero mutation surface) | Platform Overview (hardcoded clickable-KPI whitelist, only 6 of N metrics wired) | |
| 2. List / Register | PM Register, PM Resources, PM Projects, all 9 Platform flat-entity pages | PM Timesheets self-service (flat table, no inspector/detail, structurally isolated) | Platform's 9-page consistency is the strongest evidence base for a `ListPage` pattern |
| 3. Detail / Object Workspace | PM Projects/Tasks `SectionDetailPage` (lazy per-section loading, 5–8 sections) | PM Register detail (Details/Impact/Response/Links — thinner, less consistent action set) | |
| 4. Master Data | Platform's 9 `AdminEntityWorkspace` pages (Organizations/Sites/Departments/Employees/Parties/Calendars/Users/Documents/Structures) | — | This family is Platform's strongest, most reusable pattern in the entire audit |
| 5. Form / Create / Edit | Platform's `AdminDialogHost` + `EntityDialog` pattern; PM's per-workspace `*EditorDialog` family | PM `DocumentLinkEditorDialog.qml` / `CalendarAssignmentDialog.qml` (raw "Entity Type"/"Entity ID"/"Module Code" free-text fields — see §14) | |
| 6. Work Queue / Review Queue | PM Review Queue (Approve/Reject/Lock/Unlock, decision dialog) | — (no capability gating is the weak point, not the pattern itself) | |
| 7. Planning / Scheduling | PM Scheduling (Gantt + Baselines + Leveling + Diagnostics tab family) | — | Most sophisticated PM page; also has the worst raw-exception leak (`leveling_actions.py`'s manual try/except) |
| 8. Finance / Analytical | PM Financials (always-detail-mode, persistent project selector, best-hardened mutation path in the codebase) | — | Financials is structurally unique — no list landing page at all |
| 9. Configuration | Platform Settings (Runtime/Module Entitlements/Integration Capabilities/Diagnostics) | — | |
| 10. Audit / History | Platform Control → Audit tab | — | |
| 11. Documents | Platform Documents + Document Structures | — | |
| 12. Dialog / Drawer | `EntityDialog` (focus management, error-slot prioritization) | `SlideOverPanel` (1 consumer, no Escape, no focus trap) | |
| 13. Empty / Disabled / No-access state | `PermissionState.qml` (lock icon + curated message) vs. `EmptyState.qml` (no-data) — both exist, both used consistently | — | |

---

## 7. Table/list comparison

Both modules' list pages funnel through the **same** shared skeleton (`TableToolbar` → `DataTable` → `TablePaginationBar` → optional `BulkActionBar`), which is a genuine strength — there is really only **one** canonical table/list pattern in the codebase, not several competing ones. Divergence shows up in the surrounding chrome, not the table itself:

| Aspect | Platform (9 entity pages) | PM Projects/Resources/Register | PM Tasks | PM Timesheets (self-service) |
|---|---|---|---|---|
| Row selection | Single-click → `InspectorPanel` | Single-click → `InspectorPanel` | Single-click selects only, **no InspectorPanel** | No inspector at all |
| Row activation | Double-click/Enter → detail page | Same | Same | N/A (no detail page) |
| Export | Not found in the 9 entity pages | Native `FileDialog` (Projects) | Dedicated `TasksExportDialog.qml` | N/A |
| Bulk actions | Not present | `BulkActionBar` (Delete/Change Property) | Same | N/A |
| Filters | Not deeply audited per-page | Modal `*FilterPopup.qml` (own file per workspace — 4 near-identical copies: Projects/Resources/Tasks/Timesheets) | Same pattern | Same pattern |
| Pagination | Not confirmed used (Topic B, INFERRED — Platform has no `TablePaginationBar` consumer at all per the shared-component audit) | Server-side, `TablePaginationBar` | Same | Same |

**Distinct table/list patterns**: effectively **one** (`TableToolbar`+`DataTable`+`TablePaginationBar`), consistently applied. The real duplication is at the *filter popup* and *dialog host* layer (4 `*FilterPopup.qml`, 6 `*DialogHost.qml`, 8 `*WorkspaceState.qml` files across PM workspaces — confirmed structurally similar but not literal clones; a legitimate extraction candidate, not urgent).

---

## 8. Form/editing comparison

- **Dialog vs. full-page form**: both modules default to **dialog** (`EntityDialog`) for create/edit; PM Financials is the exception — full-page detail-mode editing for complex financial objects (Budget Version, Forecast, Rate Card) rather than a dialog.
- **Field layout / labels / help text**: `FormField.qml` is the standard wrapper in both modules (17 Platform + 34 PM consumers) — genuinely one shared standard, not competing styles.
- **Validation / required fields**: routed through `InlineMessage` inside `EntityDialog`'s prioritized error slot — consistent.
- **Save/cancel position**: standardized by `EntityDialog`'s footer (destructive / spacer / busy spinner / cancel / primary) — consistent across every consumer.
- **Dirty-state handling / confirmation**: `EntityDialog` has real focus-return-on-close handling; `ConfirmationDialog` (the lighter sibling used for destructive-action confirms) does **not** have the same focus management — a real, if minor, inconsistency between the two dialog primitives.
- **Success/failure feedback**: consistent `InlineMessage` (danger/success tones), **except** that the underlying *content* of failure messages is inconsistently sanitized (§3.4, §14 — the raw-exception-leak problem is a forms/editing-adjacent issue as much as a table one, since it surfaces in the exact same `InlineMessage` slot).
- **The one confirmed form-content leak**: `DocumentLinkEditorDialog.qml` forces the user to hand-type "Entity Type," "Entity ID," and "Module Code" as raw free-text fields rather than domain-labeled pickers — the clearest concrete instance in the whole audit of implementation vocabulary leaking into a form.

**Verdict**: Platform and PM genuinely follow **one** form standard (`EntityDialog`+`FormField`+`InlineMessage`), not several competing ones — this is one of the strongest consistency findings in the audit.

---

## 9. Detail-page comparison

| | Platform (Organization/Site/Department/Employee/User/Document) | PM (Project/Task/Resource/Timesheet-period/Finance objects) |
|---|---|---|
| Page header | `WorkspaceFrame`/`PageHeader` title+subtitle | Same |
| Breadcrumb | None (§4.5) | None |
| Status | Present per-entity (INFERRED, not itemized per-field in this pass) | `StatusChip` throughout |
| Actions | Edit/Delete/entity-specific (e.g. Calendar has no "toggle active" because no backend method exists — explicitly *omitted* rather than faked, a positive signal) | Edit/Delete + rich per-domain actions (e.g. Task: move WBS, progress, dependency edit/remove) |
| Tabs/sections | `AdminEntityDetailPage` fixed shell, cross-links to related entities (Site→Departments/Employees/Audit) | `SectionDetailPage` with **lazy-loaded** sections (5 for Projects, 8 for Tasks, 4 for Register) |
| Side panels | `InspectorPanel` (list-page preview, not a detail-page feature) | Same |
| Related entities | Explicit `navigateToDestination`/`relatedRecordRequested` signal cross-links (Sites↔Departments↔Employees↔Audit) | Present within `SectionDetailPage` sections (e.g. Task's Dependencies section) |
| History/activity | Routed to Platform's shared Audit workspace (`"Entity-level audit detail is routed through the shared Platform audit workspace"` — echoed near-verbatim across 4 admin detail pages) | Per-workspace Activity section (own data, not centralized) |

**Strongest existing detail-page pattern**: PM's Projects/Tasks `SectionDetailPage` (lazy section loading is a genuine engineering strength — sections don't fetch data until opened) combined with Platform's `AdminEntityDetailPage`'s cross-linking convention. A future standard `DetailPage` pattern should combine: `SectionDetailPage`'s lazy-section mechanism + Platform's cross-link signal convention + a resolved decision on whether "Overview" or "Details" is the canonical first-section name (currently inconsistent even within PM, Projects vs. Tasks).

---

## 10. Visual consistency findings

- **Zero hardcoded hex colors** in either Platform or PM QML (VERIFIED, full-tree grep, both trees clean) — dark-mode support is real and centralized via `Theme.AppTheme` tokens throughout.
- **Density support is systemic**, not per-component — every shared widget reads `AppTheme.densityMode`-derived row/toolbar/header heights rather than hardcoding pixel sizes.
- **Spacing/radius literal counts are comparable between the two modules** (Platform: 105 spacing/radius + 20 margin/padding literals across ~43/8 files; PM: 114 + 20 across ~49/15 files) — most are hairline (`0`–`4`px) and low-severity. The **non-hairline, token-worthy offenders**:
  - Platform: `TenantManagementWorkspacePage.qml:161` (`radius: 4`, should be `radiusSm`), `SettingsSidebarNav.qml:141` (`radius: 4`, same), `SettingsSidebarNav.qml`'s nav-row insets (9 raw margin values: 14/9/4/6/8/3px), `AccessSecurityPanel.qml` (15 literals), `ControlWorkspacePage.qml` (13 literals).
  - PM: `SchedulingWorkspacePage.qml:170` (`radius: 8`, should be `radiusMd`), `ProjectsOverviewSection.qml` (11× `spacing: 2` repeated per field — a systemic micro-pattern, not one-off), `PortfolioDetailPanel.qml`/`RegisterDetailPanel.qml` (6 each).
- **PM's literal-spacing pattern skews toward a repeated `spacing: 2` micro-gap** across every `*OverviewSection.qml`/`*DetailPanel.qml`; **Platform's skews toward larger, more clearly-token-worthy values (8/9/14px) concentrated in 3 files.**
- Where Platform and PM already match: button hierarchy (`PrimaryButton`/`SecondaryButton`), form field layout (`FormField`), dialog shell (`EntityDialog`), table chrome (`DataTable`/`TableToolbar`), color tokens (both 100% token-driven).
- Where they visibly diverge: tab-strip usage (PM uses `DetailTabBar` in 6 places; Platform uses none — its "tabs" are really the always-visible sibling-page-switching pattern), pagination (`TablePaginationBar` is PM-only per the shared-component consumer count — 0 Platform files), `KpiStrip` (2 Platform vs. 11 PM), `LoadingOverlay` (0 Platform vs. 10 PM — Platform appears to render busy state differently, not verified in depth).

---

## 11. Responsive findings

- `narrowLayoutBreakpoint = 1280` drives **simultaneous** collapse of the top-level `ShellDrawer` *and* whichever module's internal `GroupedNavigationRail` — below 1280px both collapse to icon-only at once, which could leave a narrow content area with two collapsed rails eating edge space rather than one adapting first (INFERRED risk, not visually confirmed in this pass — no rendering was performed in this audit).
- `DataTable.qml` has its own independent per-column `hideBelow` width threshold, decoupled from both breakpoint systems.
- `InspectorPanel`'s side-vs-compact-popup switch (used by Projects/Resources/Register/Review Queue) is gated on `Theme.AppTheme.inspectorWidth + 720`-ish thresholds (per-page, not globally centralized) — reasonable but means the exact narrow-mode behavior is implemented per-consumer rather than once.
- **No page-level responsive test exists for either module** (§15) — so responsive behavior at 1366×768 or narrower could not be verified in this pass beyond reading breakpoint definitions; actual rendered behavior at those widths was **not tested** (out of scope for a read-only static-code audit — flagged for a follow-up visual pass).
- Global Overview's separate breakpoint set (`overviewNarrowWidthBreakpoint`/`overviewCompactWidthBreakpoint`/`overviewCompactHeightBreakpoint`) is scoped only to itself — neither Platform nor PM's own pages use it, so there is no shared "page content responsive" convention beyond the shell-chrome-level `narrowLayoutBreakpoint`.

---

## 12. Accessibility findings

**Systemic, not isolated.** Summary from the cross-cutting audit (VERIFIED grep):

| Marker | Platform | PM |
|---|---|---|
| `Accessible.*` (any) | 0 files | 0 files |
| `activeFocusOnTab` | 0 | 0 |
| `Keys.onPressed` | 0 | 2 files (focus-trap Tab/Backtab in a dialog; Home/End in the Gantt viewport) — neither carries `Accessible.role`/`Accessible.name` either |
| Interactive files (`MouseArea`/`TapHandler` w/ `onClicked`/`onTapped`) | 9 | 15 |

**24 interactive files total, 0 with any accessibility marker.** Two concrete widely-reused components make the propagation mechanism explicit: the **live** `ProjectManagement/Widgets/RecordListCard.qml` (used by 3 unrelated PM workspaces — Register, Activity Log, Projects Risks — none of which individually add accessibility, all three inherit the gap from the shared component) and Platform's `SettingsSidebarNav.qml` (used by every Settings sub-page). The shared-library components that *do* have real accessibility (`ModuleCard`, `InfoTip`, partially `GroupedNavigationRail`) live **outside** Platform/PM, in `shell/`/`shared/` — meaning the accessibility discipline established elsewhere in the codebase (documented in this engagement's own Phase 6E/6F/6G work on `OrganizationSwitcher.qml`, `NotificationBell.qml`, `ActionCenterRow.qml`) has **not yet propagated** into either the Platform admin console or the PM workspaces.

**Highest-leverage fix targets** (by consumer count): `DataTable.qml` (49 consumers), the live `RecordListCard.qml` (3 consumers, but a clean single-file fix), `SettingsSidebarNav.qml` (every Settings page).

No color-only status meaning was flagged as a *new* finding (StatusChip pairs color with text label throughout, per its consistent usage pattern) — the accessibility gap here is entirely about keyboard/screen-reader access, not color contrast per se (contrast itself was not independently measured in this pass).

---

## 13. Settings/Support functionality already present

All of it lives inside Platform's **Settings → Diagnostics** destination, backed by `PlatformSupportWorkspaceController`/`PlatformSupportDesktopApi`. This is a single, coherent, already-productionized bundle — not scattered or half-built.

| Item | Current location | Backend | User-facing? | Prod-ready? | Judgment |
|---|---|---|---|---|---|
| Release/update channel, auto-check, install | `support/sections/AdminSupportReleasePanel.qml` | `PlatformSupportDesktopApi.save_settings/check_for_updates/install_available_update` | Yes | Yes (Windows-only install path is explicitly surfaced, not silently swallowed) | Future app-level **Settings** |
| Runtime/version info | `AdminSupportRuntimePanel.qml` | same DTO | Yes | Yes | Future **Settings** |
| Log/app-data paths | `AdminSupportPathsPanel.qml` | `get_paths()` | Yes | Yes | Future **Help & Support** |
| Diagnostics bundle export | `AdminSupportDiagnosticsPanel.qml` | `export_diagnostics_to()` | Yes | Yes | Future **Help & Support** |
| Incident reporting | same panel | `create_incident_report()` | Yes | Yes | Future **Help & Support** |
| Support activity feed | `AdminSupportActivityPanel.qml` | `list_activity(trace_id=...)` | Yes | Yes | Future **Help & Support** |
| Theme Mode / Density | `SettingsRuntimeSection.qml` | writes shell-wide `shellModel`, not Platform-scoped | Yes | Yes | Future app-level **Settings** — arguably shouldn't have been under "Platform" at all |
| Module Entitlements / Integration Capabilities | `SettingsModulesSection.qml`/`SettingsIntegrationsSection.qml` | `PlatformRuntimeDesktopApi`/`IntegrationCapabilityDesktopApi` | Yes | Yes | Stays in **Platform** — tenant/org licensing is a genuine Platform admin concern |

**Confirmed issue**: `PlatformSupportDesktopApi` (`support.py`) returns raw `str(exc)` from bare `except Exception` blocks in 5 methods — the one severe, confirmed instance of the raw-exception-leak pattern found in Platform (PM has the same pattern pervasively; see §3.4/§14). **Access-gate gap**: `PlatformSupportWorkspaceController` has no `_is_accessible()` override of its own — it's currently protected only incidentally (nested inside Settings, which *is* gated `settings.manage`); if Diagnostics/Support is ever split into its own top-level destination, it will need an explicit gate of its own.

**Nothing here is placeholder or non-functional** — every Settings/Support item is a real, working feature.

---

## 14. Duplication/legacy findings

| Finding | Evidence | Verdict |
|---|---|---|
| `RecordListCard.qml` exists twice — once in Platform (`Platform/Widgets/`), once in PM (`ProjectManagement/Widgets/`) — 95% line-identical | Platform's copy imported once (`SettingsWorkspacePage.qml:13`) but never instantiated; PM's copy is live (3 consumers) | Platform's copy: **dead code / LEGACY CANDIDATE**. Real cross-module duplication opportunity: converge on one shared `App.Widgets` component. |
| PM per-workspace `*FilterPopup.qml` (×4), `*ListPage.qml` (×5), `*DialogHost.qml` (×6), `*WorkspaceState.qml` (×8) | Confirmed same skeleton hand-copied per workspace (150–250 lines each), not literal clones — field counts and domain logic genuinely differ | Structural duplication, legitimate future extraction candidate, **not urgent** (not interchangeable drop-ins without parameterization work) |
| 6 dead `*Workspace.qml` wrapper files in PM (Dashboard/Portfolio/Scheduling/Register/Collaboration/Financials) | Zero grep hits for their qmldir namespace import anywhere in the tree | **LEGACY CANDIDATE**, safe-to-remove pending confirmation nothing external still imports by qmldir type |
| Platform's own `qmldir`-registered components (`AdminEntityDetailPage`, `AdminEntityWorkspace`, `AdminDetailTableSection`, `PlatformNavigation`, `CalendarAssignmentDialog`, `AdminDialogHost`, `ActivityLogSection`) | All confirmed actively instantiated in multiple pages via spot-check | No further dead components found beyond `RecordListCard` |
| `qml_registry.py`'s full route list | Every `qml_path` file exists on disk; no orphaned/missing routes; `QmlRouteRegistry.register()` raises on duplicate ids so duplicates are structurally impossible | Clean |
| Two independent `WorkspaceControllerBase` classes (Platform's own vs. PM's own) | Not diffed line-by-line — could be legitimate per-module architecture consistent with the repo's own layer-first convention, or could be a convergence opportunity | **INFERRED, flagged as follow-up, not a confirmed finding** |
| Domain/UI boundary leaks | Literal `"QML"` in `FinancialsEvmSection.qml:85`; `DocumentLinkEditorDialog.qml` (3 raw fields: Entity Type/Entity ID/Module Code); `CalendarAssignmentDialog.qml` ("Entity" label); `ControlWorkspacePage.qml` filter fields (borderline, admin-only technical screen); `AdminEntityDetailPage.qml`'s default `"Entity-level audit detail is routed through the shared Platform audit workspace"` copy echoed near-verbatim across 4 admin detail pages | Concentrated, not widespread — no raw UUIDs, permission codes, module codes, or exception class names found rendered anywhere |
| Internal (non-registry) Platform router (`PlatformWorkspace.qml`/`PlatformNavigation.qml`) was not exhaustively checked for orphans the way the level-1 registry was | — | **INFERRED, flagged as follow-up** (out of this pass's grep-based method) |

---

## 15. Test coverage findings

**Platform** (`src/tests/ui_qml/platform/`): strong controller/presenter unit coverage (7 controller test files, 8 presenter test files, 5 adapter test files, 1 context test, 1 route test). One real QML-level smoke test exists at shell scope (`test_registered_qml_routes_load_offscreen`), which transitively construction-tests every Platform page since they're all eagerly instantiated — real but shallow (proves no crash on load, nothing about behavior).

**Confirmed gaps (Platform)**: no light/dark theme test scoped to any Platform page; no responsive/breakpoint test; no accessibility test scoped to Platform; no per-page table/form/detail interaction test through actual QML (only through the presenter/controller layer in isolation); no scope-switching UI test through the real `ContextBar`/`PlatformNavigation` QML; no test for Access's tri-permission gating at the QML layer; no test for the Control "Views" popup no-op; no test asserting the Support/Diagnostics raw-exception-leak is or isn't guarded.

**PM**: broad presenter/controller test coverage per-workspace (itemized per area in §3), plus a genuinely strong Gantt-specific test suite (7 files covering read contract, viewport, time axis, dependencies, semantic visualization, hardening, closure) and one true regression test for the leak pattern (`test_financials_mutation_error_boundary.py`, Financials only).

**Confirmed gaps (PM)**: no mutation-error-boundary test exists for Scheduling, Portfolio, Register, Collaboration, or Review Queue — precisely the areas confirmed missing `safe_errors=True` (§3.4); no dedicated `test_*baseline*.py` file (baseline coverage folded into general scheduling tests, so isolated approve/reject/status-transition coverage can't be confirmed without reading test bodies); no route test asserting Review Queue's missing-route gap is intentional rather than accidental.

---

## 16. Current-state Platform tree

```
Platform
├── Overview
├── Organization
│   ├── Organizations
│   ├── Sites
│   ├── Departments
│   ├── Employees
│   └── Parties
├── Calendars
├── Identity & Access
│   ├── Users
│   └── Access ("Roles & Access")
├── Documents
│   ├── Documents
│   └── Structures ("Document Structures")
├── Control
│   ├── Approvals
│   └── Audit
├── Settings
│   ├── Runtime            (incl. app-wide Theme/Density — see §2.5, §13)
│   ├── Module Entitlements
│   ├── Integration Capabilities
│   └── Diagnostics        (= all current "Support" functionality — see §13)
└── Tenant Administration ("Tenant Management")
```

## 17. Current-state PM tree

```
Project Management
├── Overview (dashboard)
├── Portfolio
├── Work
│   ├── Projects
│   ├── Tasks
│   ├── Planning (scheduling — incl. Gantt, Resource Leveling, Diagnostics, Baselines, Calendars, Activity Feed)
│   └── Timesheets (self-service — resource_timesheets folder)
├── Workload Management
│   ├── Resources
│   └── Review Queue (⚠ no shell route — timesheets folder)
├── Finance (financials — always-detail-mode: Overview/Planning/Costs/Performance/Commercial/Controls)
└── Governance
    ├── Register
    └── Collaboration (Inbox/Mentions/Approvals/Activity)
```

---

## 18. Proposed future Platform context tree

Base: the user's given target tree, cross-checked against §16's real inventory. Every leaf below is either **EXISTING** (matches current code as-is), **MOVE/REORGANIZE** (real functionality, different placement), **MERGE** (consolidating something that's currently split or duplicated), **FUTURE** (not yet built), or **REMOVE/DEPRECATE** (dead code / placeholder found in this audit).

```
Platform
├── Overview                              EXISTING
├── Organization
│   ├── Organizations                     EXISTING
│   ├── Sites                             EXISTING
│   ├── Departments                       EXISTING
│   ├── Employees                         EXISTING
│   └── Parties                           EXISTING
├── Identity & Access
│   ├── Users                             EXISTING
│   └── Access                            EXISTING (resolve nav-label/title mismatch: "Access" vs "Roles & Access")
├── Documents
│   ├── Documents                         EXISTING
│   └── Structures                        EXISTING
├── Control
│   ├── Approvals                         EXISTING (REMOVE/DEPRECATE the placeholder "Views" popup, or implement it for real)
│   └── Audit                             EXISTING
├── (Calendars)                           MOVE/REORGANIZE — currently ungrouped at the top level; the target tree doesn't list it explicitly. Candidate: fold under Organization (it's an org-scoped master-data concept) pending a product decision (§22).
└── Tenant Administration                 EXISTING (resolve nav-label/title mismatch: "Tenant Administration" vs "Tenant Management"; add an explicit access gate to match its siblings)

[Settings — separate top-level area per the target IA]
├── Runtime / General                     MOVE from Platform→Settings — MERGE the shell-wide Theme/Density controls here too (they're app-wide, not Platform-scoped, today)
├── Module Entitlements                   stays conceptually Platform-owned (tenant/org licensing) but EXISTING code is already a clean unit — MOVE the destination, not the logic
└── Integration Capabilities              same as above — MOVE the destination

[Help & Support — separate top-level area per the target IA]
├── Diagnostics / Paths / Export          MOVE from Platform Settings→Diagnostics (EXISTING, fully built — §13)
├── Incident Reporting                    MOVE (EXISTING)
└── Support Activity                      MOVE (EXISTING)
```

**No large new product capability is proposed here** — every leaf above already exists in working code today; this is a reorganization/relabeling map, not a feature-invention list, per the audit rules.

## 19. Proposed future PM context tree

```
Project Management
├── Overview                              EXISTING (dashboard)
├── Portfolio                             EXISTING
├── Work
│   ├── Projects                          EXISTING
│   ├── Tasks                             EXISTING
│   ├── Planning                          EXISTING (scheduling)
│   └── Timesheets                        EXISTING (self-service; MOVE/REORGANIZE — align its root QML onto WorkspaceFrame for consistency with siblings, per §3.4)
├── Workload Management
│   ├── Resources                         EXISTING
│   └── Review Queue                      EXISTING but MOVE/REORGANIZE at the plumbing level: needs its own shell/compatibility route (currently the only one of 11 workspaces without one — §3.1) and its folder should be renamed to match (currently lives in the `timesheets/` folder, swapped with self-service Timesheets — §3.4/§14)
├── Finance                               EXISTING (financials)
└── Governance
    ├── Register                          EXISTING (add capability gating to match its siblings, or explicitly decide it shouldn't have one — §3.4)
    └── Collaboration                     EXISTING (align Approve/Reject's capability gate with Scheduling's baseline-approval pattern — §3.4)
```

**MERGE candidate (not in the tree above, a cross-cutting recommendation, not a page move)**: the 4 `*FilterPopup.qml` / 6 `*DialogHost.qml` / 8 `*WorkspaceState.qml` per-workspace duplicate families (§6, §14) are candidates for a shared generic base once a second design pass is ready to invest in the parameterization work — not urgent enough to block the navigation reorganization above.

**REMOVE/DEPRECATE**: the 6 dead `*Workspace.qml` wrapper files (Dashboard/Portfolio/Scheduling/Register/Collaboration/Financials) and Platform's dead `RecordListCard.qml` copy.

---

## 20. Recommended shared page-pattern system

| Pattern | Purpose | Platform reference | PM reference | Shared components already available | Gaps before standardization |
|---|---|---|---|---|---|
| **DashboardPage** | Read-only KPI/analytics landing | Platform Overview | PM Overview/Dashboard | `KpiStrip`, `OverviewMetricTile`, `LoadingOverlay` | Platform's clickable-KPI map is hardcoded per-page; needs a generalized "metric → destination" contract |
| **ListPage** | Search/filter/paginate/select a collection | Any of Platform's 9 `AdminEntityWorkspace` pages | PM Resources/Register/Projects | `TableToolbar`, `DataTable`, `TablePaginationBar`, `BulkActionBar` | `DataTable` needs accessibility work first (§5); filter-popup pattern needs generalizing (currently 4 hand-copied instances) |
| **DetailPage** | Drill into one object, lazy-loaded sections | Platform `AdminEntityDetailPage` (cross-link convention) | PM `SectionDetailPage` (lazy sections) | `SectionDetailPage`, `InspectorPanel`, `ContextualActionToolbar` | Section-naming convention unresolved ("Overview" vs "Details"); no breadcrumb exists at all |
| **MasterDataPage** | CRUD over a simple entity | Any Platform entity page | PM Register (closest PM equivalent) | `AdminEntityWorkspace`, `EntityDialog`, `FormField` | This is Platform's strongest pattern — PM should adopt it more consistently, not the reverse |
| **FormPage** (dialog-based) | Create/edit an object | `AdminDialogHost`+`EntityDialog` | Per-workspace `*EditorDialog` | `EntityDialog`, `FormField`, `DialogActionFooter` | Raw-field leaks in 2 specific dialogs need fixing before calling this "the" standard (§13/§14) |
| **WorkQueuePage** | Review/approve/reject a queue of pending items | Platform Control → Approvals | PM Review Queue, PM Collaboration → Approvals | `DataTable`, decision dialogs | Capability-gating is inconsistent (3 different approve/reject implementations, only 1 properly gated — §3.4) |
| **ConfigurationPage** | Settings-shaped toggles/values | Platform Settings | — (PM has no direct equivalent) | `SettingsSidebarNav`-style internal nav | — |
| **AuditPage** | Read-only history/activity trail | Platform Control → Audit | PM's per-workspace Activity sections (decentralized, not unified) | `ActivityFeed` | PM's activity data is per-workspace, not centralized like Platform's — a real architectural difference, not just a UI one |
| **EmptyStatePage** | No-data / no-access | — | — | `EmptyState.qml`, `PermissionState.qml` | Already consistent — no gaps found |

---

## 21. Recommended modernization order

**P0 — architecture / navigation blocker**
- Decide the level-2 navigation convergence question (§4.3): does the future two-level nav model require Platform's internal `PlatformNavigation.qml` permission-gating to converge onto `module_access_policy.py`, or is a permanent two-layer split (module-visibility vs. within-module-destination-visibility) the intended design? This decision gates almost everything else about how "Context Navigation Tree" gets built for both modules.
- Resolve Review Queue's missing route (§3.1/§3.4) before any nav restructuring, since deep-linking is presumably a requirement of any real two-level nav.

**P1 — shared pattern blocker**
- Harden `DataTable.qml` (accessibility + full keyboard) before onboarding new modules — 49 consumers means this is the single highest-leverage shared-component fix (§5).
- Decouple `StatusChip.qml` from its hardcoded status vocabulary before Inventory/Procurement/Accounting/Payroll/QHSE/HR can safely use it (§5).
- Fix the raw-exception-leak pattern on the *refresh* path everywhere, and the *mutation* path everywhere except Financials/Resources (§3.4/§14) — this is both a UX defect and a potential information-disclosure concern, and it's the single most pervasive finding in the whole audit.

**P2 — high-value user-facing modernization**
- Converge PM's capability-gating inconsistency (Register/Collaboration should match Scheduling's/Resources' pattern, or a product decision should explicitly say they don't need gating).
- Resolve the Projects-vs-Tasks structural inconsistencies (§3.4) — these are PM's two flagship pages and should be the most consistent pair in the module.
- Split Platform's Settings/Support bundle into the target Settings / Help & Support areas (§13/§18) — the functionality is already complete; this is pure reorganization.

**P3 — cleanup / polish**
- Remove the 6 dead PM `*Workspace.qml` wrapper files and Platform's dead `RecordListCard.qml` (§14).
- Fix the 2 confirmed domain/UI boundary leaks (`DocumentLinkEditorDialog.qml`, `CalendarAssignmentDialog.qml`) and the literal `"QML"` string in `FinancialsEvmSection.qml` (§14).
- Resolve label inconsistencies (Access/"Roles & Access", Tenant Administration/"Tenant Management", nav-label-vs-workspace-key mismatches in PM) (§2.5/§3.2).
- Address the non-hairline hardcoded spacing/radius literals in the worst-offender files (§10).

**P4 — future work**
- Extract the PM per-workspace `*FilterPopup`/`*ListPage`/`*DialogHost`/`*WorkspaceState` duplication into a generic parameterized base (§6/§14) — real but not urgent, since the current files are functionally correct, just not DRY.
- Consolidate the 4 competing secondary-navigation patterns (`GroupedNavigationRail`/`NavOverflowMenu`/`DetailTabBar`/`SectionNavigationRail`) into documented guidance (§5).
- Harden `SlideOverPanel.qml` (Escape-to-close, focus trap) before promoting it as the standard drawer pattern (§5).

---

## 22. Risks / architecture concerns

- **The raw-exception-leak pattern is pervasive enough that it may already be leaking sensitive data in production** (DB error text, internal identifiers) on any transient backend failure during a page refresh, in nearly every PM workspace and in Platform's Support/Diagnostics area. This is the single largest risk surfaced by this audit and should be treated as higher priority than any navigation/IA work.
- **Two independent, non-converged permission-gating mechanisms exist at the navigation layer** (§4.3). If a future two-level nav redesign only updates one of them, the other will silently continue enforcing (or failing to enforce) the old rules — a real risk of the two drifting further apart rather than converging, unless explicitly addressed as part of the redesign.
- **No accessibility foundation exists in either module's own code.** Building new modules (Inventory, Procurement, etc.) on top of the current shared components without first hardening `DataTable`/`InlineMessage`/the bare-`Rectangle`-button pattern will propagate the gap to every future module rather than closing it.
- **PM's structural variety (Financials' no-list-landing-page design, Timesheets' bare-`Item` root, Dashboard's pure-read shape) is domain-appropriate but makes "one PM page pattern" harder to define than "one Platform page pattern."** Any future `WorkQueuePage`/`ConfigurationPage`/etc. standard should be validated against Financials and Timesheets specifically, not just against the more uniform Projects/Tasks/Resources trio.
- **Two org-switcher-shaped controllers were found and not fully reconciled** (§4.4) — worth resolving before any navigation-layer redesign touches organization switching, to avoid building on top of an unresolved duplication.

---

## 23. Open questions requiring product decision

1. Should Platform's internal (level-2) navigation permission-gating converge onto `module_access_policy.py`, or is the current two-layer split (module-level vs. destination-level) the intended permanent design?
2. Where should Calendars live in the target Platform tree — the given target tree doesn't list it explicitly; is it Organization-scoped master data, its own top-level item, or does it move elsewhere?
3. Is the Settings/Help & Support split proposed in §18 correct, or should Module Entitlements/Integration Capabilities move to Help & Support instead of staying in Platform?
4. Should Review Queue and self-service Timesheets be renamed/swapped at the folder level to match their nav labels (§3.4/§14), and does that require a route-id change with backward-compat implications?
5. Is the two-org-switcher-controller situation (§4.4) intentional (two genuinely separate UI surfaces) or should they converge onto one shell-owned controller?
6. Should PM's per-workspace Activity sections be unified into one centralized activity source (matching Platform's "routed to the shared Audit workspace" convention), or is per-workspace activity data intentional?
7. What is the acceptable scope/cost for backfilling `safe_errors=True` and accessibility markers across the codebase — should this be done incrementally per-workspace as each is touched for the nav redesign, or as a dedicated remediation pass before the redesign begins?

---

## 24. Exact files to inspect first in the next design phase

**Navigation/architecture decision (P0):**
- `src/ui_qml/platform/qml/Platform/Components/PlatformNavigation.qml`
- `src/ui_qml/modules/project_management/controllers/common/pm_workspace_navigation_controller.py`
- `src/core/platform/application/platform_runtime/module_access_policy.py`
- `src/ui_qml/shell/navigation_accessibility.py`, `src/ui_qml/shell/navigation.py`, `src/ui_qml/shell/context.py`
- `src/ui_qml/modules/project_management/routes.py`, `src/ui_qml/modules/project_management/navigation.py` (Review Queue route gap)

**Shared component hardening (P1):**
- `src/ui_qml/shared/qml/App/Widgets/DataTable.qml`
- `src/ui_qml/shared/qml/App/Widgets/StatusChip.qml`
- `src/ui_qml/shared/qml/App/Widgets/InlineMessage.qml`
- `src/ui_qml/shared/qml/App/Widgets/TableToolbar.qml`, `TablePaginationBar.qml` (bare-button accessibility)

**Raw-exception-leak remediation (P1):**
- `src/ui_qml/modules/project_management/controllers/common/mutation_runner.py`
- Every `*_refresh_mixin.py` / `*refresh_service.py` / `*_state_loader.py` cited in §3.4
- `src/core/platform/api/desktop/support/support.py`
- `src/tests/ui_qml/project_management/controllers/test_financials_mutation_error_boundary.py` (template for the fix's regression tests)

**Capability-gating consistency (P2):**
- `src/ui_qml/modules/project_management/controllers/common/pm_capability_controller.py`
- `src/ui_qml/modules/project_management/qml/workspaces/register/RegisterWorkspaceState.qml`
- `src/ui_qml/modules/project_management/qml/workspaces/collaboration/CollaborationWorkspaceState.qml`

**Settings/Support split (P2):**
- `src/ui_qml/platform/qml/settings/SettingsWorkspacePage.qml` and its `sections/` (Runtime/Modules/Integrations/Diagnostics)
- `src/ui_qml/platform/qml/settings/sections/SettingsRuntimeSection.qml` (shell-wide Theme/Density coupling)

**Duplication cleanup (P3):**
- `src/ui_qml/platform/qml/Platform/Widgets/RecordListCard.qml` vs. `src/ui_qml/modules/project_management/qml/ProjectManagement/Widgets/RecordListCard.qml`
- The 6 dead `*Workspace.qml` files (Dashboard/Portfolio/Scheduling/Register/Collaboration/Financials)
- `src/ui_qml/platform/qml/documents/dialogs/DocumentLinkEditorDialog.qml`, `src/ui_qml/platform/qml/Platform/Dialogs/CalendarAssignmentDialog.qml`

**Projects/Tasks consistency (P2):**
- `src/ui_qml/modules/project_management/qml/workspaces/projects/ProjectsWorkspacePage.qml` vs. `.../tasks/TasksWorkspacePage.qml`

---

## Repository state confirmation

- **Starting HEAD:** `6a6f147af9b7c6e2c15255f764cf5201b5e592cc`
- **Ending HEAD:** `6a6f147af9b7c6e2c15255f764cf5201b5e592cc` (unchanged)
- **`git status`:** clean throughout
- **Confirmed: no files in the repository were modified, moved, renamed, or created by this audit** other than this report document itself, written at the user's explicit request after the audit's analysis was complete.
