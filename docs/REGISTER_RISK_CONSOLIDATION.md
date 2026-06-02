# Register & Risk Workspace Consolidation

**Date:** 2026-05-31  
**Status:** Implemented  
**Decision:** Risk is not a standalone workspace. Risk is an entry type within the unified Register workspace.

---

## 1. Discovery Report

### Architecture Finding: Already Unified at the Backend

The discovery revealed that Risk and Register were **already sharing the same backend** before this consolidation:

| Layer | Before | After |
|---|---|---|
| Domain model | `RegisterEntry` with `entry_type` (RISK, ISSUE, CHANGE) | Unchanged |
| Database table | `register_entries` (single table) | Unchanged |
| Controller class | `ProjectManagementRegisterWorkspaceController` (shared) | Unchanged |
| Presenter class | `ProjectRegisterWorkspacePresenter` with `workspace_mode` | Unchanged |
| Desktop API | `ProjectManagementRegisterDesktopApi` | Unchanged |

The only duplication was at the **QML workspace layer**:
- `RiskWorkspacePage.qml` (~380 lines) vs `RegisterWorkspacePage.qml` (610 lines) — ~95% identical
- `RiskDetailPanel.qml` (322 lines) — richer than `RegisterDetailPanel.qml` (175 lines)
- Both used the **same dialogs**: `RegisterEntryEditorDialog` (parameterized) and `RegisterDialogHost` (parameterized)

### Duplicates Identified

| File | Status |
|---|---|
| `workspaces/risk/RiskWorkspacePage.qml` | **Removed** |
| `workspaces/risk/RiskWorkspace.qml` | **Removed** |
| `workspaces/risk/RiskDetailPanel.qml` | **Merged into RegisterDetailPanel** |
| `"risk"` in workspace descriptors | **Removed** (no longer a nav item) |
| `"risk"` in routes | **Removed** |
| `"risk"` in ShellDrawer icon map | **Removed** |

### Shared Components (No Change — Already Reused)

| Component | Already reused by both? |
|---|---|
| `RegisterDialogHost.qml` | ✓ — parameterized via `typeFieldVisible`, `fixedTypeValue`, `entryLabel` |
| `RegisterEntryEditorDialog.qml` | ✓ — same dialog, different config |
| `RegisterDetailSection.qml` | ✓ |
| `RegisterUrgentSection.qml` | ✓ |
| `AppWidgets.DataTable` | ✓ |
| `AppWidgets.KpiStrip` | ✓ |
| `AppWidgets.TableToolbar` | ✓ |
| `AppWidgets.TablePaginationBar` | ✓ |
| `AppWidgets.BulkActionBar` | ✓ |

---

## 2. Target Architecture

```
Project Management
└── Register (unified master workspace)
    ├── [All Entries]  → setTypeFilter("all")
    ├── [Risks]        → setTypeFilter("RISK")
    ├── [Issues]       → setTypeFilter("ISSUE")
    └── [Changes]      → setTypeFilter("CHANGE")
```

Type navigation tabs replace the "Views" popup and make type selection first-class.

---

## 3. Files Changed

### Removed
- `src/ui_qml/modules/project_management/qml/workspaces/risk/RiskWorkspacePage.qml`
- `src/ui_qml/modules/project_management/qml/workspaces/risk/RiskWorkspace.qml`
- `src/ui_qml/modules/project_management/qml/workspaces/risk/RiskDetailPanel.qml`

### Modified
| File | Change |
|---|---|
| `src/core/modules/project_management/api/desktop/workspaces.py` | Removed "risk" descriptor; updated "register" descriptor summary |
| `src/ui_qml/modules/project_management/routes.py` | Removed "risk" from QML file map |
| `src/ui_qml/shell/qml/ShellDrawer.qml` | Removed "project_management.risk" icon mapping |
| `src/ui_qml/modules/project_management/qml/workspaces/register/RegisterWorkspacePage.qml` | Added type navigation tabs; removed Views popup; unified columns |
| `src/ui_qml/modules/project_management/qml/workspaces/register/RegisterDetailPanel.qml` | Added Risk-specific Impact section; added ActivityFeed to Links |

---

## 4. Domain Model — Entry Types

Current domain types (no DB migration needed):

| Type | Enum Value | Description |
|---|---|---|
| Risk | `RISK` | Project delivery risk with probability, impact, and mitigation |
| Issue | `ISSUE` | Active blocker or problem requiring resolution |
| Change | `CHANGE` | Scope, schedule, or cost change request |

Future types (require DB migration — `ALTER TABLE register_entries` enum extension):

| Type | Enum Value | Description |
|---|---|---|
| Decision | `DECISION` | Formal project decision with rationale |
| Assumption | `ASSUMPTION` | Recorded assumption with validation status |
| Lesson | `LESSON` | Post-project or interim lesson learned |

---

## 5. Type Navigation Design

The consolidated Register workspace uses a tab strip to filter by entry type:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Register                                                                   │
├────────────────────────────────────────────────────────────────────────────┤
│ KPI STRIP                                                                  │
│ Total Open | Overdue | High / Critical | Risks | Issues | Changes          │
├────────────────────────────────────────────────────────────────────────────┤
│ TYPE TABS                                                                  │
│ [All Entries] [Risks] [Issues] [Changes]                                   │
├────────────────────────────────────────────────────────────────────────────┤
│ TableToolbar                                                               │
│ Search | Filter (Project/Status/Severity) | Customize | Refresh | Export  │
├────────────────────────────────────────────────────────────────────────────┤
│ DataTable                                                                  │
├────────────────────────────────────────────────────────────────────────────┤
│ TablePaginationBar                                                         │
└────────────────────────────────────────────────────────────────────────────┘
```

**Tab behavior:**
- Active tab calls `workspaceController.setTypeFilter(value)` on click
- When a specific type tab is active: dialog uses `typeFieldVisible=false`, `fixedTypeValue=TYPE`
- When "All Entries" is active: dialog uses `typeFieldVisible=true`
- Create button label changes: "New Risk" / "New Issue" / "New Change" / "New Entry"

---

## 6. Detail Page Design

The unified detail panel conditionally shows type-specific sections:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ContextualActionToolbar                                                    │
├────────────────────────────────────────────────────────────────────────────┤
│ Details                                                                    │
│ (Always: title, description, owner, due date, severity, status)           │
├────────────────────────────────────────────────────────────────────────────┤
│ Impact                                                                     │
│ RISK:   Probability | Impact | Risk Score | Residual Risk | Mitigation     │
│ ISSUE:  Impact description | Resolution target                             │
│ CHANGE: Schedule impact | Cost impact | Approval status                    │
├────────────────────────────────────────────────────────────────────────────┤
│ Response                                                                   │
│ Urgent Review Queue (top priority items in same project scope)             │
├────────────────────────────────────────────────────────────────────────────┤
│ Links                                                                      │
│ Activity Feed (audit history)                                              │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Backward Compatibility

| Scenario | Handling |
|---|---|
| `project_management.risk` route | Route removed; data accessible via Register → Risks tab |
| `pmCatalog.riskWorkspace` property | Kept in context.py (returns registerWorkspace); no behavioral change needed |
| Existing RISK entries in DB | Fully preserved — same table, same domain model |
| Risk exports | Work via Register workspace with RISK type filter active |

---

## 8. Follow-up Recommendations

### High Priority
- [ ] Add **DECISION**, **ASSUMPTION**, **LESSON** entry types — requires Alembic migration extending the `entry_type` enum
- [ ] Populate the **Impact** section for ISSUE and CHANGE types (current state: shows fields from state dict but field names may not be set by presenter)
- [ ] Add type-count badges to tabs: `Risks (12)` from controller metrics

### Medium Priority
- [ ] Type-specific columns: when Risks tab is active, show Probability/Impact/Risk Score columns instead of generic columns
- [ ] Presenter: populate `probabilityLabel`, `impactLabel`, `riskScore`, `mitigationStrategy`, `residualRiskLabel` in the serialized entry `state` dict
- [ ] Permission scope: add `register.risk.read`, `register.issue.read`, `register.change.read` as finer-grained entitlements

### Low Priority
- [ ] Add inline type badge to the detail page header (show "RISK" / "ISSUE" / "CHANGE" chip next to title)
- [ ] Export: make CSV/Excel export include entry type column when exporting "All Entries"
- [ ] Bulk actions: allow type-specific bulk update (e.g., "Set all selected risks to Mitigated")
