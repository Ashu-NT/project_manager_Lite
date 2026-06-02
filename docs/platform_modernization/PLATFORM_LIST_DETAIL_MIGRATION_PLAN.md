# Platform List/Detail Migration Plan (Execution)

**Status:** In progress — Phase 0 (Admin Console restore) DONE + validated; Settings table-model defects fixed. Heavier phases (1–5) pending.
**Date:** 2026-06-02
**Branch:** refactor/safe-start
**Companion tracker:** `docs/platform_modernization/PLATFORM_LIST_DETAIL_ALIGNMENT_PLAN.md`

This document is the missing **"Platform workspace migration plan"** deliverable from the
companion tracker. It is grounded in a fresh, verified scan of the current code (not the
tracker's prior claims). It captures: (1) the PM pattern to replicate, (2) the verified
Platform current state, (3) reusable components, (4) the migration plan, (5) risks.

> **Guardrail (unchanged):** reuse the shared PM interaction pattern and shared widgets.
> Do **not** build a second list/detail, table, toolbar, inline-message, or dialog system.

---

## 0. Headline finding — Admin Console is currently BROKEN (P0 blocker)

`src/ui_qml/platform/qml/workspaces/admin/AdminConsolePage.qml` **does not compile**:

```
AdminConsolePage.qml:164:21: Syntax error
AdminWorkspace.qml:3:1: Type AdminConsolePage unavailable   (platform.admin route)
```

- The latest commit `cba47f53 "update plaform"` truncated this file from a working
  **1169 lines** (`b541e419`) to a broken **181-line fragment** — only the *tail* of the
  old right-side inspector survived. It references undeclared members (`root._detailItem`,
  `root._activeSection`, `root._selectedRowId`, `root._busy`, `root.workspaceController`)
  and undeclared functions (`openOrganizationEdit()`, `openSiteEdit()`, …) with unbalanced
  trailing braces.
- Net effect: **the entire `platform.admin` route fails to load at runtime.** The
  companion tracker's "validation complete / Organizations pilot done" status is stale —
  it predates this regression.
- The good news: every dedicated detail page (`AdminOrganizationDetailPage.qml`,
  `AdminSiteDetailPage.qml`, `AdminDepartmentDetailPage.qml`, `AdminEmployeeDetailPage.qml`,
  `AdminUserDetailPage.qml`, `AdminPartyDetailPage.qml`, `AdminDocumentsDetailPage.qml`,
  `AdminDocumentStructureDetailPage.qml`, `AdminEntityDetailPage.qml`), the modern list
  shell (`AdminEntityWorkspace.qml`), the nav (`AdminNavSidebar.qml`), the dialog host
  (`AdminDialogHost.qml`), and all eight per-entity `DynamicTableModel`s **exist and are
  well-built**. Only the orchestrating shell file is the casualty.

**Phase 0 (must precede everything): rebuild `AdminConsolePage.qml`** as a clean shell that
wires `AdminNavSidebar` → `AdminEntityWorkspace` (list, by active section) → the dedicated
`Admin*DetailPage` (detail, opened on row activation, hides the list), plus the
`AdminDialogHost`. Use `b541e419` as a reference for the controller/property wiring, but the
detail surface must route to the dedicated `*DetailPage` components (the section-aware
`SectionDetailPage` pages), **not** re-introduce the old inline right-side inspector.

---

## 1. PM pattern to replicate (discovery Phase 1 — verified)

Source of truth: `tasks` (richest), `resources`, `projects` workspaces + shared widgets.

### 1.1 Shell & list↔detail toggling
- Root = `AppLayouts.WorkspaceFrame { title; subtitle }` (binds from `controller.overview`).
- State: `property bool _detailOpen`, `property int _pendingDetailSection`,
  `readonly property var detailPage: detailPageLoader.item`, plus `_tableId`, `_columns`.
- One full-fill `Item` holds two siblings:
  - **List** `Item { visible: !_detailOpen }`
  - **Detail** `Loader { active: _detailOpen; asynchronous: true; visible: _detailOpen && status===Loader.Ready; sourceComponent: _detailPageComponent }` (z:20)
- `function _openDetail(idx){ _pendingDetailSection=idx; _detailOpen=true; if (detailPage){ detailPage.scrollToSection(idx); _loadLazySection(idx) } }`
- First open: `detailPage` is null → `SectionDetailPage.Component.onCompleted` does the initial `scrollToSection(_pendingDetailSection)` + lazy load.
- Back: detail's `ContextualActionToolbar.onBackRequested: _detailOpen=false`.

### 1.2 List page child order
`KpiStrip` → 2× `LoadingOverlay` → 2× `InlineMessage` (danger+success, gated `!_detailOpen`)
→ `TableToolbar` → `Item { DataTable(sourceModel:…) + TablePaginationBar + AnchoredPopup filters + BulkActionBar(+BulkChangePropertyPopup) }`.

### 1.3 DataTable
- Columns via `_baseColumns()` (objects `{key,label,flex,minWidth?,sortable?,type?,required?,visibleByDefault?}`), with `_applyColumnState()/_buildColumnState()` + `loadTableColumnState/saveTableColumnState(_tableId)`.
- Rows via **`sourceModel: controller.xTableModel`** (`DynamicTableModel`), not the JS `rows:` array.
- `onRowActivated: controller.activateX(id); _openDetail(0)`. (`onRowSelected` = select only.)

### 1.4 SectionDetailPage (index-based)
- Props: `open`, `title`, `isBusy`, `showHeader/showEdit/showDelete` (**PM sets all false** — the in-content `ContextualActionToolbar` owns the chrome), `sections` (list of strings or `{label,count}`), `readonly activeSectionIndex`, default `content` slot (a scrollable `Column`).
- Signals: `sectionChanged(int)`, `backRequested/editRequested/deleteRequested` (unused when header hidden).
- `scrollToSection(index)` sets the active index + emits `sectionChanged`.

### 1.5 Two action surfaces (the button rule)
- **Header `ContextualActionToolbar`** (entity-level), placed as first child of `SectionDetailPage` content, `showBack: true`, with:
  ```qml
  actions: detailPage && detailPage.activeSectionIndex === 0 ? root._overviewActions : []
  onActionTriggered: function(id){ /* edit/status/delete/... */ }
  ```
  → entity actions appear **only on Overview**; other sections show Back + title only.
- **Per-section `ContextualActionToolbar`** embedded *inside each section component* (Add/Open/Export/etc.), often two-state (idle vs row-selected), gated by section-local selection + capability flags.
- `ContextualActionToolbar` already supports dynamic `actions:[{id,label,icon,enabled,danger}]` + `actionTriggered(id)` + `showBack`/`createLabel` — **no component change required**.

### 1.6 Lazy loading (two layers)
- **QML instantiation:** one `AppWidgets.LazySectionLoader { active: _idx === _secIdx("Name"); sourceComponent: Component { … } }` per section inside the detail-panel host; only the active section instantiates. Overview is index 0 → only loader active at first paint.
- **Data fetch:** `_loadLazySection(idx)` maps section→controller load method, called from detail `Component.onCompleted` (pending section) and `onSectionChanged` (every switch).
- `AppWidgets.LazyObjectLoader { invoke("openXDialog", payload) }` for dialog hosts (defers building dialog tree).

### 1.7 InlineMessage
- List scope: danger + success, gated `!_detailOpen`.
- Detail scope: danger + success directly below header toolbar, gated `_detailOpen`.
- Optional section-local InlineMessage inside heavy sections.

### 1.8 Gating
- Cross-module: `pmCatalog.hasCapability("inventory.reservations.create")` adds/removes **sections** and toggles **action `enabled`**.
- RBAC: `pmCatalog.pmCapabilityController.can*` (`canImport`, `canManageSkills`, …) gate create/actions.

---

## 2. Platform current state (discovery Phase 2 — verified)

### 2.1 Admin Console — per entity
Shared list = `AdminEntityWorkspace.qml` (`DataTable sourceModel:` + `TableToolbar` + 3× `InlineMessage` + `TablePaginationBar`). **No KpiStrip, no BulkActionBar.** Pagination is QML-side and **hidden when a Python model is bound** (`TablePaginationBar visible: catalogModel===null`). **No `loadTableColumnState`** wired for any admin table. Controller: `PlatformAdminWorkspaceController` (+ per-entity sub-controllers, each owns a `DynamicTableModel`). Dialogs via `AdminDialogHost`.

| Entity | Detail page | Sections present today | Section-aware actions | Lazy | sourceModel (list) | Embedded related tables |
|---|---|---|---|---|---|---|
| Organizations | `AdminOrganizationDetailPage` | Overview, Runtime Scope, Audit (generic-ish 3) | ✅ | ✅ | ✅ | none (audit = placeholder copy) |
| Sites | `AdminSiteDetailPage` (most advanced; module-gated) | Overview, Departments(count), [Structures/maint], [Warehouses/inv], [Projects/PM], [Assets/maint], Documents, Audit | ✅ | ✅ | ✅ | Departments via `AdminDetailTableSection` **rows:** (client-filtered) |
| Departments | `AdminDepartmentDetailPage` | Overview, Employees(count), Users, [Projects/PM], [Warehouses/inv], Documents, Audit | ✅ | ✅ | ✅ | Employees **rows:** (client-filtered) |
| Employees | `AdminEmployeeDetailPage` | Overview, User Account, Assignments, [Timesheets/PM], [Certifications/PM], Documents, Audit | ✅ | ✅ | ✅ | **none** — all non-Overview are informational copy |
| Users | `AdminUserDetailPage` | Overview, Roles & Access(count), Sessions, Module Access(count), Audit | ✅ | ✅ | ✅ | Module Access **rows:** (array) |
| Parties | `AdminPartyDetailPage` | Overview, Contacts, [Supplier/inv], Customer Profile, [Linked Projects/PM], [Linked Procurement/inv], Documents, Audit | ✅ | ✅ | ✅ | linked sections informational |
| Documents | `AdminDocumentsDetailPage` | Overview, Revisions, Linked Entities(count), Approvals, Access, Audit | ✅ | ✅ | ✅ | Linked Entities **rows:** (array) |
| Structures | `AdminDocumentStructureDetailPage` (wraps generic `AdminEntityDetailPage`) | Overview, Classification Context, Audit (generic 3) | ✅ | ✅ | ✅ | none |
| **Roles & Access** | **none** | — only `Platform/Widgets/AccessSecurityPanel.qml` (`DataTable sourceModel: scopeGrantsTableModel` + selectors) | ❌ | ❌ | ✅ (panel) | n/a |

Controllers/presenters live under `src/ui_qml/platform/controllers/admin/` and
`src/ui_qml/platform/presenters/`. Roles&Access = `access_workspace_controller.py`
(`PlatformAdminAccessWorkspaceController`) + `access_workspace_presenter.py`
(`scopeGrantsTableModel`, `securityUsersTableModel`).

### 2.2 Control Center — `ControlWorkspacePage.qml`
- Custom in-QML **tab bar** (approvals/audit/escalations/system_events), **not** list→detail.
- `KpiStrip` ✅, `InlineMessage` ✅ (page scope only), **no LoadingOverlay**.
- Approvals: `TableToolbar` + `DataTable sourceModel: approvalQueueTableModel` + `TablePaginationBar` (**pagination cosmetic** — full model bound, slice unused; large commented-out manual block remains).
- Audit: `ActivityFeed` bound to `auditFeed.items` (the `auditFeedTableModel` exists but is unused).
- Escalations & System Events: `DataTable { rows: [] }` **placeholders** (no controller API).
- Detail = fixed 300px **right inspector** for approvals only; its `ContextualActionToolbar` has **`actions: []`**; **Approve/Reject in a hardcoded footer**; **Delegate absent** (no slot, no UI). Row activate opens `ApprovalDecisionDialog`.
- Controller `PlatformControlWorkspaceController`: `approveRequest(WithNote)`, `rejectRequest(WithNote)`, `approvalQueueTableModel`, `auditFeedTableModel`. **No** escalation/system-events/delegate APIs, **no** selected-item field model.

### 2.3 Settings — `SettingsWorkspacePage.qml`
- Custom **left sidebar** switcher (runtime/modules/defaults/integrations/security/sysinfo); **all sections built eagerly** (`visible:` toggles), no `Loader`/lazy.
- `KpiStrip` ✅, `InlineMessage` ✅ (page scope only).
- Module Entitlements: `DataTable sourceModel: moduleEntitlementsTableModel`; selection → contextual actions duplicated in **two** `ContextualActionToolbar`s (inline + inspector); `lifecycle`→`ModuleLifecycleDialog`, `licensed`→`toggleModuleLicensed`, `enabled`→`toggleModuleEnabled`. Detail = flat 288px right `Rectangle` (no sub-sections).
- Integration Capabilities: `DataTable sourceModel: integrationCapabilitiesTableModel`, read-only, no detail.
- Security/Defaults/Runtime: **static hardcoded cards** (no controller data). `AccessSecurityPanel.qml` (real RBAC UI) is **not** wired into Settings.
- **Latent defects:** dangling `sourceModel` ternaries at `SettingsWorkspacePage.qml` ~lines 629-630 and ~891-892 (leftover `? items : []` from a rows→sourceModel migration) — clean up during refactor.
- Controller `PlatformSettingsWorkspaceController`: `toggleModuleLicensed/Enabled`, `changeModuleLifecycleStatus`, `moduleEntitlementsTableModel`, `integrationCapabilitiesTableModel`. `organizationProfiles` has **no** table model. `context.hasCapability()/capabilitySnapshot()` exist but are **unused** by these pages.

---

## 3. Reusable components (inventory — confirmed)

Already used by Platform: `DataTable`, `TableToolbar`, `TablePaginationBar`, `KpiStrip`,
`InlineMessage`, `ContextualActionToolbar`, `ActivityFeed`, `StatusChip`,
`ConfirmationDialog`, `EntityDialog`-based editors, `DynamicTableModel`.

Available to adopt (from PM): `SectionDetailPage`, `LazyObjectLoader`, `LazySectionLoader`,
`LoadingOverlay`, the dialog-host pattern, the stacked list/detail page pattern,
`BulkActionBar` + `BulkChangePropertyPopup` (not yet used by Platform).

**Shared-component verdicts (no rewrites needed):**
- `ContextualActionToolbar` — already dynamic-actions + `actionTriggered(id)` capable. ✅ no change.
- `SectionDetailPage` — index-based, supports `{label,count}` sections, hidden header. ✅ no change.
- Platform should embed `SectionDetailPage` directly per detail page (as Admin already does), **not** add a new wrapper.

---

## 4. Migration plan

Ordering principle: **unblock → finish Admin → Control → Settings → harden cross-cutting → validate.**

### Phase 0 — Restore Admin Console shell (BLOCKER)
- Rebuild `AdminConsolePage.qml`: `WorkspaceFrame` hosting `AdminNavSidebar` (left) +
  a content area that, per `_activeSection`, shows `AdminEntityWorkspace` (list) and, on
  row activation, swaps to the matching dedicated `Admin*DetailPage` (detail hides list);
  include `AdminDialogHost` via `LazyObjectLoader`. Reference `b541e419` for
  controller/property wiring; route detail to the dedicated `*DetailPage` components.
- Acceptance: `platform.admin` route compiles + loads; each entity list renders; row
  activation opens its `SectionDetailPage`; list hides; back returns.

### Phase 1 — Finish Admin entities to spec
Org/Sites/Departments/Employees/Users/Parties detail pages already follow the pattern.
Remaining gap-closing:
1. **Roles & Access (largest gap):** add `AdminAccessDetailPage.qml` (SectionDetailPage:
   Overview, Permissions, Scope, Users, Sessions, Audit) + host the grants list through
   `AdminEntityWorkspace`-style list using `scopeGrantsTableModel`; section-aware actions
   (Overview: Edit Grant / Revoke / Disable; Permissions: Add/Remove; Users: Assign User;
   Sessions: Revoke Session). Reuse `access_workspace_controller.py`.
2. **Documents & Structures:** verify section sets vs target spec (Documents: Overview,
   Revisions, Linked Entities, Approvals, Access, Audit; Structures: Overview, Child
   Structures, [Locations/inv], [Assets/maint], [Projects/PM], Documents, Audit). Add the
   missing sections; keep informational copy only where no backing data exists yet.
3. **Embedded related tables → sourceModel:** migrate `AdminDetailTableSection` usages
   (Site→Departments, Department→Employees, User→Module Access, Document→Linked Entities)
   from client-filtered `rows:` to scoped `sourceModel` models where the controllers can
   expose them; otherwise document why they remain array-rows.
4. **List polish:** add `KpiStrip` to entity lists where the spec calls for it
   (Organizations totals/active/sites, etc.); wire `loadTableColumnState/save` for admin
   tables; decide server-side vs client pagination for `*TableModel` (re-enable
   `TablePaginationBar`).
5. **Consolidate** on `AdminEntityWorkspace`; retire/delete legacy `AdminCatalogGrid.qml`
   and unused `ApprovalQueueSection`/`AuditFeedSection`/`ModuleEntitlementsSection`/
   `OrganizationProfilesSection` if confirmed dead.

### Phase 2 — Control Center → panel/list/detail
- Keep the panel tab bar (Approvals/Audit/Escalations/System Events) as the top-level
  switch, but each panel becomes a PM-style list that opens a `SectionDetailPage` detail.
- **Approvals detail:** sections Overview, Request Payload, Source Reference, Decision
  History, Audit. Move Approve/Reject from the hardcoded footer into the **header
  `ContextualActionToolbar`**, Overview-only, and **add Delegate** (new controller slot
  `delegateRequest(id, …)` + presenter + desktop API method). Lazy-load non-Overview
  sections; needs a controller `selectedApproval` field model.
- **Audit detail:** sections Overview, Actor, Entity, Payload, Related Events; Overview
  actions Export Event / Open Source. Decide: keep `ActivityFeed` for the list OR switch to
  `auditFeedTableModel` DataTable (the model already exists) — recommend DataTable list +
  detail page for consistency, ActivityFeed retained for the Related Events sub-section.
- **Escalations / System Events:** require controller/presenter/desktop APIs first (today
  they are `rows: []`). Scope: add real data sources or explicitly mark deferred.
- Fix cosmetic pagination (apply paging to the model or remove the bar until paged API exists).

### Phase 3 — Settings → section/list/detail
- Replace the eager sidebar with lazy sections; fix the dangling `sourceModel` ternaries.
- **Module Entitlements:** row activation → `SectionDetailPage` (Overview, Capabilities,
  Consumers, Audit); collapse the two duplicate toolbars into one Overview-only header
  toolbar (Enable/Disable, Change Lifecycle via `ModuleLifecycleDialog`).
- **Integration Capabilities:** list → detail (Overview, Provider Module, Consumer Modules,
  Usage, Audit).
- **Security:** wire the existing `AccessSecurityPanel`/access controller instead of static
  cards, or render real policy data; **Support:** keep `ActivityFeed`/diagnostics, align to
  shared shell. **Runtime/Defaults:** structured detail (not list) is acceptable.

### Phase 4 — Cross-cutting hardening
- **Section-aware actions:** ensure every detail page binds header `actions:` to
  `activeSectionIndex===0` and embeds section toolbars elsewhere (Admin already does;
  apply to Control/Settings).
- **Lazy rules:** Overview immediate; related/Documents/Audit/module-linked sections load
  only when opened (QML loader `active:` + data dispatcher on `onSectionChanged`).
- **RBAC + entitlement:** gate sections/actions via `context.hasCapability(...)` /
  `capabilitySnapshot()` and the access controller's permission flags — **hide** (don't
  show permission-denied placeholders): Warehouses/Inventory, Projects/PM, Assets/Maint,
  Audit (audit-read perm). Admin already uses `isModuleEnabled(...)`; extend to
  Control/Settings and add permission-based gating.
- **DataTable/sourceModel:** no large QML row transforms; migrate embedded `rows:` tables to
  `sourceModel` where controllers allow.

### Phase 5 — Validation (see §6).

---

## 5. Risks

- **R0 (new):** Admin Console is broken on this branch — Phase 0 is a hard prerequisite and
  must be validated before any further Admin work. Rebuild risk: the recoverable
  `b541e419` shell is the *old inspector* design, so it must be adapted to route to the
  dedicated `*DetailPage` files rather than restored verbatim.
- Many "related" detail sections are informational copy, not real data — surfacing real
  related records requires controller/presenter additions (scope creep risk; phase it).
- Control Escalations/System Events and Delegate need **backend/desktop-API** work, not just
  QML — larger than a UI alignment.
- Moving embedded tables and Control/Settings tables to `sourceModel` may require
  controller/presenter changes (paged/scoped models), not QML-only edits.
- Settings has latent `sourceModel` ternary defects to clean up carefully (avoid changing
  behavior of the working module/integration tables).
- Section-aware actions implemented locally per section is correct; do **not** centralize
  into a new action-bar component (guardrail).
- Pagination semantics: client-side slicing vs Python paged models is inconsistent today;
  pick one direction per table and document it.

---

## 6. Validation checklist (run after each phase; full run at end)

`python main_qt.py` then verify:
- Admin Console route loads (Phase 0 unblocks this); every entity list renders.
- Row activation opens `SectionDetailPage`; list hides; `TableToolbar` not shown over detail.
- Entity actions show **only** on Overview; section actions only in their section.
- Lazy loading: only Overview loads on open; other sections load on navigation.
- `InlineMessage` present on list and detail scopes.
- RBAC hides unauthorized sections/actions; disabled-module sections hidden (no
  permission-denied placeholders).
- No QML warnings/layout warnings; no duplicate buttons; no broken dialogs.
- Offscreen compile of all changed Platform QML is `Ready`; targeted dialog/host/route
  pytest suites pass; routes offscreen-load test passes (it currently exercises Platform).

---

## 7. Execution order (summary)

1. **Phase 0** — rebuild `AdminConsolePage.qml` (unblock platform.admin). ← start here on approval
2. **Phase 1** — Roles&Access detail page + list; finish Documents/Structures sections; embedded-table sourceModel; KPI/column-state/pagination polish; retire legacy grid.
3. **Phase 2** — Control Center approvals/audit list→detail; add Delegate; escalations/events data.
4. **Phase 3** — Settings module-entitlements/integration list→detail; lazy sections; wire Security; fix ternary defects.
5. **Phase 4** — cross-cutting section-aware actions / lazy / RBAC+entitlement / sourceModel.
6. **Phase 5** — full validation + update the companion tracker statuses + post-impl summary.

---

## 8. Post-implementation summary

### Done so far (2026-06-02)
- **Phase 0 — Admin Console restored (BLOCKER cleared).** `AdminConsolePage.qml` was
  restored from last-good commit `b541e419` (the `cba47f53` truncation reverted), then
  reconciled to the current detail-page APIs: removed the stale `documentStructureCatalog`
  property and `onDocumentStructureCreateRequested` / `onDocumentStructureEditRequested`
  handlers from the Documents detail Loader (the current `AdminDocumentsDetailPage` no
  longer exposes them). Result: full nav → `AdminEntityWorkspace` list → dedicated
  `Admin*DetailPage` detail orchestration is live again.
- **Settings table-model defect fixed.** `SettingsWorkspacePage.qml` had two dangling
  ternaries (`sourceModel: ctrl ? model : null ? items : []`) that, by ternary
  associativity, bound `sourceModel` to a plain array instead of the Python table model —
  so Module Entitlements and Integration Capabilities tables weren't using their
  `DynamicTableModel`s at all. Both corrected to `sourceModel: ctrl ? ctrl.xTableModel : null`.
- **Validation:** all 21 admin + 12 settings/control QML compile `Ready`; the offscreen
  routes test (`test_qml_offscreen_loading.py`) passes — `platform.admin/control/settings`
  all load.

- **Roles & Access — list/detail added (Phase 1, partial).** The access section previously
  rendered only `AccessSecurityPanel` (assignment form + grants table + inline inspector +
  sessions). Added `AdminAccessDetailPage.qml` (SectionDetailPage: **Overview, Permissions,
  Scope, Audit** — an honest set; the access controller exposes no per-grant Users/Sessions
  breakdown, so those spec sections are intentionally omitted rather than shown empty). Wired
  **additively**: `AccessSecurityPanel` now emits `grantActivated(grantId)` on grant
  row-activation (double-click) while single-click keeps the inline inspector; the shell's
  `access` block shows the panel as the list/create surface and swaps to the detail page on
  activation (back returns). Section-aware actions: Overview = **Revoke** (→
  `accessController.removeMembership`) + Refresh; other sections = Refresh / Open Audit only.
  Detail busy/error/feedback bind to `accessController`.

### Files changed (this session)
- `src/ui_qml/platform/qml/workspaces/admin/AdminConsolePage.qml` (restored + reconciled + access list/detail wrap)
- `src/ui_qml/platform/qml/workspaces/admin/AdminAccessDetailPage.qml` (new)
- `src/ui_qml/platform/qml/Platform/Widgets/AccessSecurityPanel.qml` (added `grantActivated` signal)
- `src/ui_qml/platform/qml/workspaces/settings/SettingsWorkspacePage.qml` (2 sourceModel fixes)

### Remaining (per §4 / §7)
- [~] Phase 1 — Roles&Access detail page **DONE** (Overview/Permissions/Scope/Audit, additive grant-activation detail). Still: Documents/Structures section completeness; embedded-table `sourceModel`; KPI/column-state/pagination polish; retire legacy grid; (optional) move "Assign Access" to a create dialog + add real per-grant Users/Sessions data if backend grows
- [ ] Phase 2 — Control Center approvals/audit list→detail; add **Delegate** (needs controller/presenter/desktop-API); escalations/system-events data sources
- [ ] Phase 3 — Settings module-entitlements/integration list→detail; lazy sections; wire Security panel
- [ ] Phase 4 — cross-cutting section-aware actions / lazy / RBAC + entitlement gating
- [ ] Phase 5 — full `python main_qt.py` validation + tracker status sync

> Note: several remaining items (Delegate, Escalations/System-Events data, real related-record
> tables, RBAC gating) require **controller/presenter/desktop-API** changes, not QML-only edits —
> recommend these proceed as individually reviewed slices rather than a single blind sweep.
