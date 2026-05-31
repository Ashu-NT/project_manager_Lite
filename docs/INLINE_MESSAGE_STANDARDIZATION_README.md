# InlineMessage Standard — Developer Convention & Follow-up Guide

**Date:** 2026-05-31
**Status:** Convention reference (living doc)
**Applies to:** All QML workspaces, detail pages, and dialogs.
**See also:** `INLINE_MESSAGE_AUDIT.md` (current state), `INLINE_MESSAGE_STANDARDIZATION_PLAN.md` (rollout).

This is the single source of truth for **where messages go and which widget to use**. Read this before touching message UI in any workspace.

---

## 1. The One Widget

Always use `AppWidgets.InlineMessage`. Never create a module-local variant (`LocalInlineMessage`, `ProjectInlineMessage`, `DialogErrorLabel`, etc.).

```qml
AppWidgets.InlineMessage {
    Layout.fillWidth: true       // or: width: parent.width  (non-layout parents)
    visible: <scoped condition>
    tone:    "danger"            // info | success | warning | danger
    message: <text>
    // optional: actionLabel: "Retry"; onActionClicked: controller.refresh()
}
```

Tones use `Theme.AppTheme` colors automatically. `visible:false` collapses height to 0 — safe in layouts.

---

## 2. The Three Scopes (do not mix)

| Scope | Shows | Placement | Gate |
|---|---|---|---|
| **List** | load/refresh/export/bulk/filter feedback for the table | After KPI strip / LoadingOverlay, **above** `TableToolbar` | `!_detailOpen` |
| **Detail** | selected-record actions: updated, saved, assignment added, section load error | Directly **below** `ContextualActionToolbar`, inside `SectionDetailPage` | `_detailOpen` (or the detail section's own visibility) |
| **Dialog** | validation + submit errors; success if the dialog stays open | Inside the dialog shell | handled by `EntityDialog` |

**Golden rules:**
- A list action's result shows on the **list only**. A detail action's result shows on the **detail only**. Never let one leak into the other → that is the entire point of the `_detailOpen` gate.
- Dialog validation/submit errors appear **inside the modal**, never only on the workspace behind it.
- Only one message visible per scope at a time: success is gated on `error.length === 0`.

---

## 3. Reference Implementation

`modules/project_management/qml/workspaces/projects/ProjectsWorkspacePage.qml` is the canonical example. Copy from it. It shows both list-scoped and detail-scoped pairs and the LoadingOverlay usage.

### List-scoped pair
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

### Detail-scoped pair (inside SectionDetailPage, below the toolbar)
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

### WorkspaceStateBanner (alternative list-scope, used by Platform & Maintenance)
```qml
ModuleWidgets.WorkspaceStateBanner {
    Layout.fillWidth: true
    isLoading:       controller ? controller.isLoading : false
    isBusy:          controller ? controller.isBusy : false
    errorMessage:    controller ? controller.errorMessage : ""
    feedbackMessage: controller ? controller.feedbackMessage : ""
}
```
Keep the banner for **list-level** state. Do not also show the same text in a detail/dialog scope.

---

## 4. Dialogs — standardized

All dialogs extend `AppWidgets.EntityDialog`, which renders messages internally (priority **error > feedback > info**) and disables buttons while `busy`.

### Submit contract (important — fixes silent close-on-invalid)
The Primary button calls `root.submitDialog()` **if the dialog defines one**, otherwise it falls back to `accept()`. Submit must **not** auto-close — closing is owned by the host so validation/backend errors stay visible:

```qml
AppWidgets.EntityDialog {
    id: root
    signal submitted(var payload)
    onRejected: root.close()           // Cancel/Esc close

    function submitDialog() {           // ← Primary button calls THIS
        if (nameField.text.trim().length === 0) {
            root.errorMessage = "Name is required."   // stay OPEN, show inline
            return
        }
        root.errorMessage = ""
        root.submitted(buildPayload())  // host runs controller, then closes on success
    }
}
```

Host pattern (closes only on success, keeps open + shows error on failure):
```qml
function _handleResult(dialog, result) {
    if (!result || result.ok === false)
        dialog.errorMessage = String((result && (result.error || result.message)) || "Operation failed.")
    else { dialog.errorMessage = ""; dialog.close() }
}
onSubmitted: function(p) { root._handleResult(editorDialog, controller.createX(p)) }
```

> ⚠️ **Never put validation in `onAccepted`.** Qt's `Dialog.accept()` closes the dialog *then* emits `accepted()`, so the form is already gone — the user sees no error. Use `submitDialog()` as above.

```qml
AppWidgets.EntityDialog {
    id: dialog
    title:        "Edit Item"
    busy:         controller ? controller.isBusy : false
    errorMessage: dialog._validationMessage      // local validation OR controller error
    // feedbackMessage: "Saved" — only if the dialog stays open after save

    // form fields...
}
```
**Do:** set `errorMessage` on validation failure and on backend save failure. Clear it when the user edits the offending field. **Don't:** rely on a workspace banner to surface a dialog's validation error.

---

## 5. Controller Contract

Every workspace controller exposes (read-only, QML-bound):

| Property | Type | Meaning |
|---|---|---|
| `errorMessage` | str | Current error (danger). Empty = none. |
| `feedbackMessage` | str | Current success (success). Empty = none. |
| `isLoading` | bool | Initial/load fetch in progress. |
| `isBusy` | bool | Mutating action in progress (disables buttons, shows spinner). |
| `sectionErrors` | dict | *(some PM controllers)* per-section load errors for detail sections. |

Scoping is done **in QML** via `_detailOpen` — there are **no** separate `listMessage`/`detailMessage` controller properties, and we are **not** adding any (keeps controller APIs stable; additive-only repo rule). The same `errorMessage`/`feedbackMessage` is shown in whichever scope is currently active.

> The controller is responsible for clearing `errorMessage`/`feedbackMessage` when context changes (e.g. opening a different record, closing a dialog) so stale messages don't linger across scopes.

---

## 6. Checklist for a New / Edited Workspace

- [ ] List-scoped danger + success pair present, gated `!_detailOpen`, above `TableToolbar`.
- [ ] If the page has a detail/SectionDetailPage: detail-scoped pair present, gated `_detailOpen`, below `ContextualActionToolbar`.
- [ ] Every form dialog extends `EntityDialog` and sets `errorMessage` on validation/backend failure.
- [ ] No module-local message widget; only `AppWidgets.InlineMessage`.
- [ ] No duplicate text across scopes; success gated on empty error.
- [ ] `python main_qt.py` boots with no QML warnings or binding loops.
- [ ] Trigger a list action, a detail action, and an invalid dialog submit — each message lands in the correct scope and clears on context change.

---

## 7. Anti-patterns (rejected in review)

- ❌ Hardcoded `Label { color: "#8B1E1E" }` for errors → use InlineMessage `tone: "danger"`.
- ❌ Dialog validation shown only on the workspace behind the modal.
- ❌ Detail-action success shown on the list page (and vice-versa).
- ❌ Two messages showing the same text simultaneously (banner + inline).
- ❌ New per-module InlineMessage subclasses.
