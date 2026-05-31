# InlineMessage Standardization — Execution Plan

**Date:** 2026-05-31
**Status:** Phases 1–4 implemented & compile-validated (2026-05-31). PM verified already-compliant. Remaining: optional dialog success-feedback polish (Phase 5).

> **Correction to audit:** On direct re-read, PM **Portfolio, Timesheets, and Scheduling already have complete list + detail InlineMessage pairs** (Scheduling's detail error/success are at lines ~1575/1582; the info-tone ones are legitimate section-level messages). PM Dashboard already has danger+success. The audit agents under-reported these — no PM list/detail work was needed.
**Scope:** All QML modules — Platform, Project Management, Inventory & Procurement, Maintenance
**Inputs:** `INLINE_MESSAGE_AUDIT.md` (discovery), `INLINE_MESSAGE_STANDARDIZATION_README.md` (convention)
**Guardrails:** Reuse `AppWidgets.InlineMessage` only · additive controller changes only · preserve DialogHost/EntityDialog APIs · no binding loops · no duplicate/stale messages · validate by running `python main_qt.py`.

---

## 1. Strategy

The work is **additive and pure-QML** for the vast majority of files. We standardize on the **gold-standard scoping** already shipping in `ProjectsWorkspacePage.qml`:

- **List scope:** InlineMessage(s) gated `!_detailOpen`, reading `errorMessage` (danger) + `feedbackMessage` (success, only when error empty), placed after KPI/overlay, above `TableToolbar`. Or the module's `WorkspaceStateBanner`.
- **Detail scope:** InlineMessage(s) gated `_detailOpen` (or detail section's own visibility), placed directly below `ContextualActionToolbar` inside `SectionDetailPage`.
- **Dialog scope:** `EntityDialog.errorMessage`/`feedbackMessage` — already in place; only surface success feedback where the dialog stays open.

We do **not** add scoped controller properties (`listMessage`/`detailMessage`) — the `_detailOpen` QML gate achieves the same scoping while keeping every controller API unchanged. The biggest single win — Inventory + Maintenance detail messages — is a mechanical copy of ~8 lines per file.

---

## 2. Canonical Snippets

**List-scoped (direct):**
```qml
AppWidgets.InlineMessage {
    Layout.fillWidth: true
    visible: !root._detailOpen
        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
    tone: "danger"
    message: root.workspaceController ? root.workspaceController.errorMessage : ""
}
AppWidgets.InlineMessage {
    Layout.fillWidth: true
    visible: !root._detailOpen
        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
    tone: "success"
    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
}
```

**Detail-scoped (below ContextualActionToolbar inside SectionDetailPage):**
```qml
AppWidgets.InlineMessage {
    width: parent ? parent.width : 0
    visible: root._detailOpen
        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
    tone: "danger"
    message: root.workspaceController ? root.workspaceController.errorMessage : ""
}
AppWidgets.InlineMessage {
    width: parent ? parent.width : 0
    visible: root._detailOpen
        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
    tone: "success"
    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
}
```
> For pages without a `_detailOpen` flag (e.g. Maintenance detail *sections* rendered standalone), gate on the section's own visibility/`isBusy` host instead, and pass `errorMessage`/`feedbackMessage` into the section as properties.

**Dialog success (only where dialog stays open after save):** set `root.feedbackMessage = "..."` in the controller-completion path; EntityDialog already renders it.

---

## 3. Phased Work Breakdown

### Phase 0 — Verify & Decide (no code)
- [ ] Read `PortfolioWorkspacePage.qml` and `TimesheetsWorkspacePage.qml` fully; record list/detail compliance.
- [ ] Confirm the 4 "Open Questions" in the audit §5 with the user (Control/Settings scoping; Preventive approach; generic-vs-scoped props; read-only dashboards).
- [ ] Lock the canonical snippet into `INLINE_MESSAGE_STANDARDIZATION_README.md`.

### Phase 1 — Inventory & Procurement detail pages (highest impact) ✅ DONE
Added detail-scoped InlineMessage pair below `ContextualActionToolbar` (gated `_detailOpen`):
- [x] `catalog/CatalogWorkspacePage.qml`
- [x] `inventory/InventoryWorkspacePage.qml`
- [x] `warehouses/WarehousesWorkspacePage.qml`
- [x] `reservations/ReservationsWorkspacePage.qml`
- [x] `procurement/ProcurementWorkspacePage.qml`
- [x] `pricing/PricingWorkspacePage.qml`
- [x] `movements/StockMovementsWorkspacePage.qml` — added success-tone list message.
- [x] `dashboard/` — verified already has danger+success; no change needed.

### Phase 2 — Maintenance detail sections ✅ DONE
Added detail-scoped pair as first child of `SectionDetailPage`, gated on `detailPage.open`:
- [x] `assets/AssetsWorkspacePage.qml` (before `AssetLibraryDetailSection`)
- [x] `work_orders/WorkOrdersWorkspacePage.qml` (before `WorkOrderDetailSection`)
- [x] `work_requests/WorkRequestsWorkspacePage.qml` (before `WorkRequestDetailSection`)
- [x] `preventive/PreventiveWorkspacePage.qml` — **no change**: tabbed `StackLayout` already covered by the workspace-level `WorkspaceStateBanner`; a second message would duplicate it. Banner is the correct single scope (same call as the Platform consoles).
- [ ] `dashboard/` full-page LoadingOverlay placement — deferred (cosmetic, not a message-scope issue).

### Phase 3 — Project Management touch-ups ✅ NONE NEEDED (verified compliant)
- [x] Dashboard — already has danger+success + LoadingOverlay.
- [x] Scheduling — already has detail danger/success (lines ~1575/1582) + section info messages.
- [x] Portfolio / Timesheets — already have full list + detail pairs.
- [ ] Detail sections rendering `sectionErrors` locally — optional, lower priority; parent detail banner already surfaces. Left as-is.

### Phase 4 — Platform ✅ DONE
- [x] Control/Settings — keep global banner (intentional for aggregate consoles); documented.
- [x] `AdminSupportSection.qml` — added danger + success InlineMessages (controller already sets `errorMessage`/`feedbackMessage`); busy message now hides when an error is present.

### Phase 5 — Dialog success feedback (cosmetic, cross-module)
- [ ] For dialogs that remain open after a save/validation round-trip, surface `feedbackMessage` (EntityDialog already renders it). Skip dialogs that close on success.

### Phase 6 — Validation & sign-off
- [x] Headless QML compile-check (offscreen `QQmlComponent`) of all 11 edited files: **all parse clean.** (Warehouses' `InventoryDialogHost is not a type` is a pre-existing cross-directory file-local component artifact present on unmodified HEAD too — not introduced here.)
- [ ] `python main_qt.py` — interactive boot + per-module walk (run by user; PySide6 GUI not driven headlessly here).
- [ ] Walk each module: list action → list message only; detail action → detail message only; dialog invalid → error inside modal.
- [ ] Confirm no stale messages after dialog close / detail back-navigation.
- [ ] Update `MEMORY.md` pointer + this plan's status.

---

## 4. Risk & Mitigation

| Risk | Mitigation |
|---|---|
| Stale message persists after closing detail/dialog | Gating on `_detailOpen` hides list/detail copies automatically; verify controller clears `errorMessage`/`feedbackMessage` on context switch (Phase 6 manual check). |
| Duplicate messages (banner + inline showing same text) | Detail/dialog scopes are mutually exclusive via gating; `WorkspaceStateBanner` stays list-only. |
| Binding loops from `parent.width`/visibility | Use the exact reference idioms (`width: parent ? parent.width : 0`); no two-way bindings introduced. |
| Breaking DialogHost / EntityDialog APIs | No API changes — only add InlineMessage children / set existing message props. |
| Preventive StackLayout retrofit regresses tabs | Scope to adding one InlineMessage above tab content; no structural change. |
| Cannot run tests locally (no PySide6 in shell) | User runs `python main_qt.py`; static QML file checks + careful diff review pre-handoff. |

---

## 5. Execution Order (recommended)

`Phase 0 → 1 → 2 → 3 → 4 → 5 → 6`. Phases 1 and 2 deliver the highest UX value (the genuinely missing detail messages) and are low-risk mechanical edits. Each phase ends with a `python main_qt.py` smoke check before moving on.

---

## 6. Out of Scope

- Replacing `WorkspaceStateBanner` with raw InlineMessage (kept intentionally for list-level state).
- Migrating Preventive fully off `StackLayout` to `SectionDetailPage` (architecture change, separate effort).
- New controller message properties / serializer changes (generic props + QML gating suffice).
- Toast/snackbar transient notifications (not part of the InlineMessage standard).
