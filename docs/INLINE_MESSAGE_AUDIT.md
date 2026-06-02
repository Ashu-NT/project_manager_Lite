# InlineMessage Usage — Platform-Wide Audit Report

**Date:** 2026-05-31
**Status:** Discovery complete — implementation NOT started
**Scope:** All QML modules — Platform, Project Management, Inventory & Procurement, Maintenance
**Companion docs:** `INLINE_MESSAGE_STANDARDIZATION_PLAN.md` (execution), `INLINE_MESSAGE_STANDARDIZATION_README.md` (convention)
**Builds on:** `DIALOG_ARCHITECTURE_MIGRATION_PLAN.md` (EntityDialog adoption — already in progress)

---

## 1. Executive Summary

The goal is **consistent, scoped message placement** in every workspace:

- **List page** messages (load/refresh/export/bulk/filter) — near the top of the list content, gated so they show only on the list.
- **Detail page** messages (record updated, section load error, assignment added) — inside the detail page, below the contextual action toolbar.
- **Dialog** messages (validation, submit failure) — inside the dialog shell, never only behind the modal.

The audit reveals the platform is **further along than expected** because two reusable foundations already exist and are widely adopted:

| Foundation | State | Effect |
|---|---|---|
| `AppWidgets.InlineMessage` | Single shared widget (tone/message/actionLabel) | No duplicate message widgets exist anywhere — good. |
| `AppWidgets.EntityDialog` | Renders `errorMessage`/`feedbackMessage`/`infoMessage` + `busy` internally | **All ~50 dialogs are already EntityDialog-based and show errors inside the modal.** Dialog scope is essentially DONE. |
| `WorkspaceStateBanner` (×3: platform/PM/maintenance) | ColumnLayout of 3 InlineMessages driven by `isLoading`/`isBusy`/`errorMessage`/`feedbackMessage` | Standard list-level banner for Maintenance + Platform. |

**Reference implementation (gold standard):** `modules/project_management/qml/workspaces/projects/ProjectsWorkspacePage.qml` — list-scoped messages gated on `!_detailOpen`, detail-scoped messages gated on `_detailOpen`, both reading generic `errorMessage`/`feedbackMessage`, plus `LoadingOverlay` for `isLoading`/`isBusy`.

**Headline findings:**

1. **Dialogs — DONE.** Every audited dialog extends `EntityDialog`; validation/submit errors render inside the modal. Remaining work is cosmetic (a few set `errorMessage` but never surface `feedbackMessage` for "save succeeded, dialog stays open").
2. **List pages — mostly compliant.** PM, Inventory, and Maintenance list pages all carry list-scoped messages (direct InlineMessage or `WorkspaceStateBanner`). A handful of small gaps (StockMovements missing success tone; Dashboard pages error-only).
3. **Detail pages — the real gap.** **Inventory (6 detail pages) and Maintenance (4 detail sections) render NO detail-scoped InlineMessage**, even though their controllers expose `errorMessage`/`feedbackMessage`. This is the bulk of the work and is a pure-QML, additive change.
4. **Platform multi-panel pages** (Control Center, Settings) use a single global banner with no list/detail scoping — a scoping decision rather than a missing widget.
5. **Architecture outliers:** `PreventiveWorkspacePage` uses a `StackLayout`-tab layout (not `SectionDetailPage`), so it has no detail-scoped message path; `DocumentDetailPanel` is display-only.

**Controller properties:** Every workspace controller audited exposes `errorMessage`, `feedbackMessage`, `isLoading`, `isBusy`. Some PM controllers also expose `sectionErrors`. **No controller API changes are required** for the core work — the scoped split (`listMessage`/`detailMessage`) recommended in the brief is achievable purely in QML via the existing `_detailOpen` gating pattern, preserving controller APIs (per repo convention: additive only).

---

## 2. Reusable Inventory (reuse — do NOT duplicate)

| Component | Path | Role |
|---|---|---|
| `InlineMessage` | `shared/qml/App/Widgets/InlineMessage.qml` | The one message widget. `message`, `tone` (info/success/warning/danger), `actionLabel`, `actionClicked()`. |
| `EntityDialog` | `shared/qml/App/Widgets/EntityDialog.qml` | Dialog shell. `errorMessage`/`feedbackMessage`/`infoMessage` (priority error>feedback>info), `busy`. Renders InlineMessage internally. |
| `WorkspaceStateBanner` | `platform/.../Widgets`, `project_management/.../Widgets`, `maintenance/.../Widgets` | 3-InlineMessage stack for list-level state. |
| `SectionDetailPage` | `shared/qml/App/Widgets/SectionDetailPage.qml` | Detail page shell (header + section rail + content). No built-in message slot — messages are injected as first content child. |
| `ContextualActionToolbar` | `shared/qml/App/Widgets/ContextualActionToolbar.qml` | Detail toolbar. Detail messages go directly below it. |
| `LoadingOverlay` | `shared/qml/App/Widgets/LoadingOverlay.qml` | Loading/busy spinner overlay (compact + modal modes). |

**Cleanup status:** No `LocalInlineMessage`, `ProjectInlineMessage`, `DialogErrorLabel`, or other duplicates were found. Nothing to remove. `WorkspaceStateBanner` is kept for list-level state; it does **not** duplicate detail/dialog messages, so no conflict.

---

## 3. Module Audit Detail

Legend — **List**: list-scoped InlineMessage present? **Detail**: detail-scoped InlineMessage present? **Dialog**: errors shown inside the modal?

### 3.1 Platform

| File | List | Detail | Dialog | Gap / Note | Risk |
|---|---|---|---|---|---|
| `workspaces/control/ControlWorkspacePage.qml` | ✅ global (3× InlineMessage) | ⚠️ none | n/a | Multi-panel (Approvals/Audit/Events). One global banner, no list/detail scoping. | med |
| `workspaces/settings/SettingsWorkspacePage.qml` | ✅ global (3× InlineMessage) | ⚠️ none | n/a | Multi-section sidebar. Global banner only, no per-section scoping. | med |
| Admin sections (`AdminEntityWorkspace`, `AdminAuditSection`) | ✅ (3× via reusable) | n/a | n/a | Reusable section template already compliant. | low |
| `AdminSupportSection` | ⚠️ none | n/a | n/a | No error/feedback wiring observed. | low |
| `Platform/Widgets/DocumentDetailPanel.qml` | n/a | n/a (display-only) | n/a | No mutating actions → no messages needed. | low |
| 11 dialogs (`OrganizationEditorDialog` … `ModuleLifecycleDialog`) | n/a | n/a | ✅ EntityDialog | All extend EntityDialog; errors render inside modal. | low |

### 3.2 Project Management

| File | List | Detail | Dialog | Gap / Note | Risk |
|---|---|---|---|---|---|
| `projects/ProjectsWorkspacePage.qml` | ✅ (`!_detailOpen`) | ✅ (`_detailOpen`) | — | **Gold standard reference.** | — |
| `tasks/TasksWorkspacePage.qml` | ✅ | ✅ | — | Compliant. | low |
| `register/RegisterWorkspacePage.qml` | ✅ | ✅ | — | Compliant. | low |
| `resources/ResourcesWorkspacePage.qml` | ✅ | ✅ | — | Compliant (detail section delegates to parent). | low |
| `financials/FinancialsWorkspacePage.qml` | ✅ | ✅ | — | Compliant. | low |
| `collaboration/CollaborationWorkspacePage.qml` | ✅ | ✅ | — | Compliant. | low |
| `dashboard/DashboardWorkspacePage.qml` | ✅ (error) | n/a | — | `LoadingOverlay` condition omits `isBusy`/feedback guard vs reference. | med |
| `scheduling/SchedulingWorkspacePage.qml` | ✅ | ⚠️ info-only | — | `SchedulingDetailPanel` has info-tone (empty-state) only; no error/feedback binding. | med |
| `timesheets/TimesheetsWorkspacePage.qml` | ⚠️ verify | ⚠️ verify | — | Not fully read in audit — **verify in Phase 0**. | low |
| `portfolio/PortfolioWorkspacePage.qml` | ⚠️ verify | ⚠️ verify | — | Data-heavy layout — **verify in Phase 0**. | med |
| Detail panels (`Tasks/Scheduling/Resources/Financials/...DetailSection`) | n/a | ⚠️ partial | — | Receive `sectionErrors` but most don't render it locally; rely on parent. | low–med |
| 14 dialogs (`ProjectEditorDialog` … `CostItemEditorDialog`) | n/a | n/a | ✅ EntityDialog | Compliant; some set `errorMessage` but no `feedbackMessage`. | low |

### 3.3 Inventory & Procurement

| File | List | Detail | Dialog | Gap / Note | Risk |
|---|---|---|---|---|---|
| `catalog/CatalogWorkspacePage.qml` | ✅ | ❌ **missing** | — | Detail in SectionDetailPage has no InlineMessage. | **high** |
| `inventory/InventoryWorkspacePage.qml` | ✅ | ❌ **missing** | — | Same. | **high** |
| `warehouses/WarehousesWorkspacePage.qml` | ✅ | ❌ **missing** | — | Same. | **high** |
| `reservations/ReservationsWorkspacePage.qml` | ✅ | ❌ **missing** | — | Same. | **high** |
| `procurement/ProcurementWorkspacePage.qml` | ✅ | ❌ **missing** | — | Same. | **high** |
| `pricing/PricingWorkspacePage.qml` | ✅ | ❌ **missing** | — | Same. | **high** |
| `movements/StockMovementsWorkspacePage.qml` | ⚠️ error-only | n/a | — | Missing success-tone InlineMessage. | med |
| `dashboard/DashboardWorkspacePage.qml` | ⚠️ error-only | n/a | — | Read-only KPI view; error-only acceptable but inconsistent. | low |
| 13 dialogs (`CategoryEditorDialog` … `ReceiptPostDialog`) | n/a | n/a | ✅ EntityDialog | Compliant; errors render inside modal. | low |

> All 6 detail pages already wire `ContextualActionToolbar.busy` and have controllers exposing `errorMessage`/`feedbackMessage` — the fix is a pure copy-paste of the reference's two detail InlineMessages below the toolbar.

### 3.4 Maintenance

| File | List | Detail | Dialog | Gap / Note | Risk |
|---|---|---|---|---|---|
| `assets/AssetsWorkspacePage.qml` (+ `AssetLibraryDetailSection`) | ✅ (WorkspaceStateBanner) | ❌ **missing** | — | Detail section has `isBusy` but no error/feedback InlineMessage. | med |
| `work_orders/WorkOrdersWorkspacePage.qml` (+ `WorkOrderDetailSection`) | ✅ | ❌ **missing** | — | Same. | med |
| `work_requests/WorkRequestsWorkspacePage.qml` (+ `WorkRequestDetailSection`) | ✅ | ❌ **missing** | — | Same. | med |
| `preventive/PreventiveWorkspacePage.qml` (+ `PreventiveDetailSection`) | ✅ | ❌ **missing** | — | Uses `StackLayout` tabs, **not** SectionDetailPage → no detail-scoped path. | **high** |
| `dashboard/`, `planner/`, `reliability/` WorkspacePages | ✅ | n/a | — | List banner present; analytical views, no detail. Dashboard layers a full-page LoadingOverlay (review placement). | low–med |
| 12 dialogs (`WorkOrderEditorDialog` … `SystemEditorDialog`) | n/a | n/a | ✅ EntityDialog | Compliant; `errorMessage` only, no success `feedbackMessage`. | low–med |

---

## 4. Consolidated Gap Summary

| Gap class | Modules affected | Count | Effort | Risk |
|---|---|---|---|---|
| **Detail-scoped InlineMessage missing** | Inventory (6), Maintenance (4) | 10 | Low (copy reference pattern) | high |
| List page error-only / missing success tone | Inventory (StockMovements, Dashboard), PM (Dashboard) | 3 | Trivial | low–med |
| Detail panel info-only / no error binding | PM (Scheduling), PM detail sections (sectionErrors) | ~5 | Low–med | med |
| Multi-panel scoping decision | Platform (Control, Settings) | 2 | Med (design) | med |
| Architecture outlier (no SectionDetailPage) | Maintenance (Preventive) | 1 | Med | high |
| Dialog success feedback not surfaced | All modules (subset of dialogs) | many (cosmetic) | Trivial | low |
| Unverified pages | PM (Portfolio, Timesheets) | 2 | Verify-first | low |

**Dialogs (scope 3): effectively complete** thanks to EntityDialog. **Detail pages (scope 2): the primary work.** **List pages (scope 1): near-complete with small touch-ups.**

---

## 5. Open Questions for Execution (resolve in Plan Phase 0)

1. **Platform Control/Settings:** keep one global banner, or introduce `_activeSection`/`_detailOpen` scoping? (Recommendation: keep global banner for these aggregate consoles; document as intentional.)
2. **Preventive:** retrofit a detail-scoped InlineMessage into the `StackLayout` tab area, or defer until/if it migrates to SectionDetailPage? (Recommendation: add a tab-area InlineMessage now; full migration is out of scope.)
3. **Scoped controller props:** stay with generic `errorMessage`/`feedbackMessage` + QML `_detailOpen` gating (preferred — additive, no API churn), vs. add `listMessage`/`detailMessage`. (Recommendation: QML gating; matches the gold standard already shipping.)
4. **Read-only dashboards:** confirm error-only banners are intentional and document, vs. add success tone.

See `INLINE_MESSAGE_STANDARDIZATION_PLAN.md` for the phased remediation.
