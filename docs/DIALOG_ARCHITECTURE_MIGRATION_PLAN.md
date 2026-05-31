# Enterprise Dialog Architecture — Audit, Standardization & Migration Plan

**Date:** 2026-05-31  
**Status:** Implementation in progress  
**Scope:** All QML modules — Platform, Project Management, Inventory & Procurement, Maintenance

---

## 1. Executive Summary

A complete audit of the QML dialog layer reveals **50 application dialogs** spread across 4 modules, all extending `App.Controls.CenteredDialog`. The current implementation has 5 consistent anti-patterns that this migration resolves:

| Anti-pattern | Current | Fixed |
|---|---|---|
| Background override | Each dialog overrides CenteredDialog's layered shadow with a plain `Rectangle` | Removed — EntityDialog inherits CenteredDialog's correct background |
| Error message | Plain `AppControls.Label` with hardcoded `color: "#8B1E1E"` | Reuses `AppWidgets.InlineMessage` with `tone: "danger"` |
| No busy state | Buttons remain clickable during operations | `busy: bool` prop disables all buttons + shows spinner |
| No feedback message | No in-dialog success feedback | `feedbackMessage` prop via InlineMessage |
| Duplicated boilerplate | Every dialog repeats Flickable + ColumnLayout + footer + cancel button | Single `EntityDialog` shell owns all of this |

**Migration strategy:** Replace only the outer shell. All form fields, validation logic, payload building, and signals are preserved unchanged.

---

## 2. Discovery Results

### 2.1 QML Import Graph

```
App.Controls
├── CenteredDialog          ← base dialog (positioning + shadow)
├── ConfirmationDialog      ← extends CenteredDialog
├── DialogActionFooter      ← footer button container
├── PrimaryButton
├── SecondaryButton
├── TextField, TextArea, ComboBox, CheckBox, DateField
└── Label, RadioButton, ToggleSwitch, SearchField

App.Widgets
├── EntityDialog [NEW]      ← enterprise dialog shell (extends CenteredDialog)
├── InlineMessage           ← error/feedback/info banner (reused)
├── DataTable, TableToolbar, TablePaginationBar
├── ActivityFeed, KpiStrip, MetricCard
├── ContextualActionToolbar, BulkActionBar
├── SectionDetailPage, SectionCard, LazySectionLoader, LazyObjectLoader
├── AnchoredPopup, BulkChangePropertyPopup
└── SlideOverPanel, EmptyState, StatusChip, ProgressBar

Platform.Dialogs (11)
├── OrganizationEditorDialog
├── SiteEditorDialog
├── DepartmentEditorDialog
├── EmployeeEditorDialog
├── UserEditorDialog
├── PartyEditorDialog
├── DocumentEditorDialog
├── DocumentLinkEditorDialog
├── DocumentStructureEditorDialog
├── ApprovalDecisionDialog
└── ModuleLifecycleDialog

ProjectManagement.Dialogs (14)
├── ProjectEditorDialog
├── ProjectStatusDialog
├── ProjectsImportDialog
├── TaskEditorDialog
├── TaskProgressDialog
├── TaskAssignmentEditorDialog
├── TaskAssignmentHoursDialog
├── TaskDependencyEditorDialog
├── TaskCollaborationComposerDialog
├── ResourceEditorDialog
├── ResourceSkillEditorDialog
├── ResourceCertificationEditorDialog
├── RegisterEntryEditorDialog
└── CostItemEditorDialog

InventoryProcurement.Dialogs (13)
├── CategoryEditorDialog
├── ItemEditorDialog
├── DocumentLinkDialog
├── StoreroomEditorDialog
├── StockMovementDialog
├── StockTransferDialog
├── ReservationCreateDialog
├── ReservationIssueDialog
├── RequisitionEditorDialog
├── RequisitionLineDialog
├── PurchaseOrderEditorDialog
├── PurchaseOrderLineDialog
└── ReceiptPostDialog

Maintenance.Dialogs (12)
├── AssetEditorDialog
├── ComponentEditorDialog
├── LocationEditorDialog
├── SystemEditorDialog
├── WorkOrderEditorDialog
├── WorkOrderStatusDialog
├── WorkRequestEditorDialog
├── WorkRequestStatusDialog
├── PreventivePlanEditorDialog
├── PreventivePlanTaskEditorDialog
├── TaskTemplateEditorDialog
└── TaskStepTemplateEditorDialog
```

### 2.2 DialogHost Relationship Map

```
Platform
└── AdminConsolePage
    └── LazyObjectLoader → AdminDialogHost (17 open functions)
        ├── OrganizationEditorDialog
        ├── SiteEditorDialog
        ├── DepartmentEditorDialog
        ├── EmployeeEditorDialog
        ├── UserEditorDialog
        ├── PartyEditorDialog
        ├── DocumentEditorDialog
        ├── DocumentLinkEditorDialog
        └── DocumentStructureEditorDialog

ProjectManagement
├── ProjectsWorkspacePage
│   └── LazyObjectLoader → ProjectsDialogHost (5 functions)
│       ├── ProjectEditorDialog
│       ├── ProjectStatusDialog
│       ├── ProjectsImportDialog
│       └── ConfirmationDialog
├── TasksWorkspacePage
│   └── LazyObjectLoader → TasksDialogHost (12 functions)
│       ├── TaskEditorDialog, TaskProgressDialog
│       ├── TaskAssignmentEditorDialog, TaskAssignmentHoursDialog
│       ├── TaskDependencyEditorDialog
│       ├── TaskCollaborationComposerDialog
│       └── ConfirmationDialog (×4)
├── ResourcesWorkspacePage
│   └── LazyObjectLoader → ResourcesDialogHost (5 functions)
│       ├── ResourceEditorDialog
│       ├── ResourceSkillEditorDialog, ResourceCertificationEditorDialog
│       └── ConfirmationDialog
├── FinancialsWorkspacePage
│   └── LazyObjectLoader → FinancialsDialogHost (3 functions)
│       └── CostItemEditorDialog, ConfirmationDialog
├── SchedulingWorkspacePage
│   └── LazyObjectLoader → SchedulingDialogHost (1 function)
│       └── CenteredDialog (inline baseline creation)
└── RegisterWorkspacePage
    └── LazyObjectLoader → RegisterDialogHost (3 functions)
        └── RegisterEntryEditorDialog, ConfirmationDialog

Maintenance
├── AssetsWorkspacePage → AssetsDialogHost (8 functions)
├── WorkOrdersWorkspacePage → WorkOrdersDialogHost (3 functions)
├── WorkRequestsWorkspacePage → WorkRequestsDialogHost (3 functions)
└── PreventiveWorkspacePage → PreventiveDialogHost (8 functions)

Inventory & Procurement
├── CatalogWorkspacePage → CatalogDialogHost (5 functions)
├── InventoryWorkspacePage → InventoryDialogHost (7 functions)
├── ProcurementWorkspacePage → ProcurementDialogHost (7 functions)
└── ReservationsWorkspacePage → ReservationsDialogHost (4 functions)
```

### 2.3 Existing Reusable Components

| Component | Location | Reuse in EntityDialog |
|---|---|---|
| `CenteredDialog` | `App.Controls` | **Extends it** — keeps centering + shadow |
| `ConfirmationDialog` | `App.Controls` | Already good — no migration needed |
| `DialogActionFooter` | `App.Controls` | Used inside EntityDialog footer |
| `InlineMessage` | `App.Widgets` | Used for error/feedback/info inside EntityDialog |
| `PrimaryButton` | `App.Controls` | Used in EntityDialog footer |
| `SecondaryButton` | `App.Controls` | Used in EntityDialog footer |

---

## 3. EntityDialog — Reusable Shell Design

### Location
`src/ui_qml/shared/qml/App/Widgets/EntityDialog.qml`

### Inheritance
`EntityDialog` → `AppControls.CenteredDialog` → `Dialog` (QtQuick.Controls)

### Rationale for `App.Widgets` (not `App.Controls`)
`EntityDialog` imports `AppWidgets.InlineMessage`. If placed in `App.Controls`, it would create a circular dependency (`Controls` → `Widgets` → `Controls`). Placing it in `App.Widgets` keeps the dependency direction clean.

### Layout

```
┌──────────────────────────────────────────┐
│ Header (Dialog built-in)                 │
│   Title                                  │
├──────────────────────────────────────────┤
│ Subtitle (optional Label)                │
├──────────────────────────────────────────┤
│ InlineMessage — errorMessage  [danger]   │
│ InlineMessage — feedbackMessage [success]│
│ InlineMessage — infoMessage   [info]     │
├──────────────────────────────────────────┤
│ Flickable — scrollable content area      │
│   ColumnLayout (_formArea)               │
│     [module-specific form fields]        │
├──────────────────────────────────────────┤
│ Footer                                   │
│ [Destructive]  spacer  [spinner] [Cancel] [Primary] │
└──────────────────────────────────────────┘
```

### API

**Content:**
- `default property alias content: _formArea.data` — form fields injected here

**Header:**
- `title: string` — inherited from Dialog
- `subtitle: string` — optional description shown below title area

**Messages (priority: error > feedback > info):**
- `errorMessage: string` — danger-tone InlineMessage
- `feedbackMessage: string` — success-tone InlineMessage
- `infoMessage: string` — info-tone InlineMessage

**Busy state:**
- `busy: bool` — disables all buttons, shows BusyIndicator in footer

**Primary action:**
- `primaryText: string` (default: "Save")
- `primaryIcon: string` (default: "save")
- `primaryEnabled: bool` (default: true)
- `showPrimary: bool` (default: true)

**Secondary action (Cancel):**
- `secondaryText: string` (default: "Cancel")
- `secondaryIcon: string` (default: "close")
- `showSecondary: bool` (default: true)

**Destructive action:**
- `destructiveText: string`
- `destructiveIcon: string` (default: "delete")
- `showDestructive: bool` (default: false)
- `destructiveEnabled: bool` (default: true)

**Signals:**
- `accepted()` — primary button clicked (replaces per-dialog `onClicked: root.submitDialog()`)
- `rejected()` — cancel button clicked
- `destructiveRequested()` — destructive button clicked

---

## 4. Migration Pattern

### 4.1 Before → After (representative)

**Before (ProjectEditorDialog — current pattern across all 50 dialogs):**
```qml
AppControls.CenteredDialog {
    property string validationMessage: ""
    signal submitted(var payload)
    width: 560
    height: Math.min(680, parent ? parent.height - marginLg * 2 : 680)
    title: root.modeTitle
    closePolicy: Popup.CloseOnEscape
    onOpened: root.populateFromProject()

    background: Rectangle {           // ← REMOVED: overrides CenteredDialog shadow
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: Flickable {          // ← REMOVED: EntityDialog owns this
        contentHeight: formLayout.implicitHeight
        ColumnLayout {
            id: formLayout
            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            AppControls.Label {       // ← REMOVED: becomes subtitle: prop
                text: "Set up a project record..."
                color: Theme.AppTheme.textSecondary
            }
            AppControls.Label {       // ← REMOVED: becomes errorMessage: prop
                visible: root.validationMessage.length > 0
                text: root.validationMessage
                color: "#8B1E1E"      // hardcoded danger color
            }

            GridLayout { /* fields */ }   // ← KEPT unchanged
        }
    }

    footer: AppControls.DialogActionFooter {   // ← REMOVED: EntityDialog owns this
        Item { Layout.fillWidth: true }
        AppControls.SecondaryButton { text: "Cancel"; onClicked: root.close() }
        AppControls.PrimaryButton { text: "Save"; onClicked: root.submitDialog() }
    }
}
```

**After:**
```qml
AppWidgets.EntityDialog {
    property string validationMessage: ""
    signal submitted(var payload)
    
    title: root.modeTitle
    subtitle: "Set up a project record and delivery baseline context."
    errorMessage: root.validationMessage
    primaryText: root.modeTitle === "Create Project" ? "Create Project" : "Save Changes"
    primaryIcon: root.modeTitle === "Create Project" ? "add" : "save"
    
    onOpened: root.populateFromProject()
    onAccepted: root.submitDialog()
    onRejected: root.close()
    
    GridLayout { /* fields — unchanged */ }
}
```

**Lines reduced:** ~30 boilerplate lines removed per dialog × 50 dialogs = ~1,500 lines of duplication eliminated.

### 4.2 Platform dialog pattern (uses `mode: "create"/"edit"` instead of `modeTitle`)

Platform dialogs use `saveRequested(mode, payload)` signal and `openForCreate/openForEdit` functions. These are kept exactly as-is — only the shell is replaced.

---

## 5. File Change List

### New files
- `src/ui_qml/shared/qml/App/Widgets/EntityDialog.qml`

### Modified files (qmldir)
- `src/ui_qml/shared/qml/App/Widgets/qmldir` — add `EntityDialog 1.0 EntityDialog.qml`

### Migrated dialogs (50 files — shell replacement only)

**Platform (11)**
- `src/ui_qml/platform/qml/Platform/Dialogs/OrganizationEditorDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/SiteEditorDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/DepartmentEditorDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/EmployeeEditorDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/UserEditorDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/PartyEditorDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/DocumentEditorDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/DocumentLinkEditorDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/DocumentStructureEditorDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/ApprovalDecisionDialog.qml`
- `src/ui_qml/platform/qml/Platform/Dialogs/ModuleLifecycleDialog.qml`

**Project Management (14)**
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/ProjectEditorDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/ProjectStatusDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/ProjectsImportDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/TaskEditorDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/TaskProgressDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/TaskAssignmentEditorDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/TaskAssignmentHoursDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/TaskDependencyEditorDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/TaskCollaborationComposerDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/ResourceEditorDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/ResourceSkillEditorDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/ResourceCertificationEditorDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/RegisterEntryEditorDialog.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs/CostItemEditorDialog.qml`

**Inventory & Procurement (13)**
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/CategoryEditorDialog.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/ItemEditorDialog.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/DocumentLinkDialog.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/StoreroomEditorDialog.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/StockMovementDialog.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/StockTransferDialog.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/ReservationCreateDialog.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/ReservationIssueDialog.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/RequisitionEditorDialog.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/RequisitionLineDialog.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/PurchaseOrderEditorDialog.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/PurchaseOrderLineDialog.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs/ReceiptPostDialog.qml`

**Maintenance (12)**
- `src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs/AssetEditorDialog.qml`
- `src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs/ComponentEditorDialog.qml`
- `src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs/LocationEditorDialog.qml`
- `src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs/SystemEditorDialog.qml`
- `src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs/WorkOrderEditorDialog.qml`
- `src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs/WorkOrderStatusDialog.qml`
- `src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs/WorkRequestEditorDialog.qml`
- `src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs/WorkRequestStatusDialog.qml`
- `src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs/PreventivePlanEditorDialog.qml`
- `src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs/PreventivePlanTaskEditorDialog.qml`
- `src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs/TaskTemplateEditorDialog.qml`
- `src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs/TaskStepTemplateEditorDialog.qml`

---

## 6. Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Flickable content height regression | Low | EntityDialog sets `contentHeight: _formArea.implicitHeight` + tests |
| Dialog sizing changes (form clips) | Low | Kept same width/height constraints; height defaults to screen-safe value |
| Footer button order confusion | None | EntityDialog footer is standardized: Destructive ← spacer → spinner → Cancel → Primary |
| Platform dialog signal mismatch | None | `saveRequested(mode, payload)` signals are inside the dialog — not changed |
| Missing `onAccepted` vs `onSubmitted` | Low | All dialogs keep their internal `submitDialog()` function; `onAccepted` calls it |
| SchedulingDialogHost inline CenteredDialog | Medium | That inline dialog is migrated to use EntityDialog directly |

---

## 7. Validation Checklist

After migration, verify:

- [ ] All 50 dialogs open correctly
- [ ] Create workflow works (submit → controller slot called → dialog closes)
- [ ] Edit workflow populates fields correctly on `onOpened`
- [ ] Validation errors appear inside dialog (not as modal alerts)
- [ ] `errorMessage` shows in danger-tone InlineMessage
- [ ] Cancel closes dialog without submitting
- [ ] No broken DialogHost `invoke()` calls
- [ ] No duplicate overlay/scrim effects
- [ ] No clipped form content (Flickable scrolls when needed)
- [ ] No hardcoded `#8B1E1E` colors remain
- [ ] No `background: Rectangle {}` overrides remain
- [ ] No duplicated footer boilerplate remains
- [ ] Busy state disables buttons (where wired)
- [ ] No QML binding loop warnings
- [ ] No invisible form content (height = 0 regressions)

---

## 8. Follow-up Work (Post-Migration)

| Item | Priority | Effort |
|---|---|---|
| Wire `busy: workspaceController.isBusy` in all dialogs | High | 1 day |
| Wire `errorMessage: workspaceController.errorMessage` in all dialogs | High | 1 day |
| Wire `feedbackMessage: workspaceController.feedbackMessage` in all dialogs | Medium | 1 day |
| Add `showDestructive` delete-in-place option to editor dialogs | Medium | 2 days |
| Migrate SchedulingDialogHost inline dialog | Medium | 0.5 day |
| Migrate ReservationsDialogHost inline confirmation dialogs | Medium | 0.5 day |
| Add MFA/TOTP dialog (future auth enhancement) | Low | 1 day |
| Add `dialogSize: "small" | "standard" | "large" | "xlarge"` preset | Low | 0.5 day |

---

## 9. Implementation Log

| Date | Action | Files |
|---|---|---|
| 2026-05-31 | Discovery complete — full audit produced | (this doc) |
| 2026-05-31 | `EntityDialog.qml` created | `App.Widgets/EntityDialog.qml` |
| 2026-05-31 | `App.Widgets/qmldir` updated | +1 entry |
| 2026-05-31 | All 50 registered dialogs migrated | 50 files |
| 2026-05-31 | 6 inline dialogs migrated (SchedulingDialogHost, ReservationsDialogHost, AdminSupportSection, ProjectsDetailSection ×2, TasksDependenciesSection) | 6 files |
| 2026-05-31 | Hardcoded `#8B1E1E` color replaced with `Theme.AppTheme.danger` | TaskAssignmentEditorDialog |
| 2026-05-31 | **MIGRATION COMPLETE** — 0 remaining `AppControls.CenteredDialog` in application dialogs | — |
