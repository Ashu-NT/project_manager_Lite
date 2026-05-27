# Platform Module Modernization — Execution Plan

> **Branch:** `refactor/safe-start`  
> **Started:** 2026-05-26  
> **Completed:** 2026-05-26  
> **Status:** Done

---

## Overview

Modernize the three Platform workspaces (Admin Console, Control Center, Settings) to match
the enterprise architecture spec: per-entity columns, panel-nav tabs, ActivityFeed widget,
Security/Support sections, and full validation.

---

## Tasks

### Phase 1 — Admin Console: Entity-specific columns
**Status:** `[x] complete`

All 8 entity workspaces in `AdminConsolePage.qml` currently share a single generic
`_entityColumns` definition (`Name / Details / Status / Info`). Replace with per-entity
column sets:

| Entity | Columns |
|--------|---------|
| Organizations | Name, Code, Type, Status, Country |
| Sites | Name, Code, Organization, Type, Status |
| Departments | Name, Code, Site, Status |
| Employees | Name, Code, Department, Site, Status |
| Users | Username, Full Name, Role, Status |
| Parties | Name, Code, Type, Status |
| Documents | Title, Code, Category, Status |
| Structures | Name, Type, Status |

**Files:** `src/ui_qml/platform/qml/workspaces/admin/AdminConsolePage.qml`

---

### Phase 2 — Control Center: Panel nav tabs
**Status:** `[x] complete`

The Control Center currently stacks Approvals and Audit vertically with no way to
switch between panels.

**Required:** Tab bar with `[Approvals] [Audit] [Escalations] [System Events]` at the
top of the right/main content area. Escalations and System Events can start as
placeholder panels.

**Files:** `src/ui_qml/platform/qml/workspaces/control/ControlWorkspacePage.qml`

---

### Phase 3 — Control Center: Use AppWidgets.ActivityFeed
**Status:** `[x] complete`

The Audit panel uses a hand-rolled ListView delegate with inline timeline styling.
Replace with `AppWidgets.ActivityFeed` bound to
`root.workspaceController.auditFeed.items`.

**Files:** `src/ui_qml/platform/qml/workspaces/control/ControlWorkspacePage.qml`

---

### Phase 4 — Settings: Security section
**Status:** `[x] complete`

Currently an `EmptyState` placeholder. Add real content:
- Password policy (min length, complexity, expiry)
- Session policy (timeout, concurrent sessions)
- Approval thresholds
- RBAC defaults

Display as read-only info cards (writable controls are future scope). Use
`SectionDetailPage` or `ColumnLayout` with labeled rows.

**Files:** `src/ui_qml/platform/qml/workspaces/settings/SettingsWorkspacePage.qml`

---

### Phase 5 — Settings: Support & Diagnostics section
**Status:** `[x] complete`

Verify current state and replace placeholder with:
- Runtime version info (from `workspaceController.overview`)
- Module health summary (loaded modules, errors)
- Log level / diagnostic toggles (read-only labels for now)

**Files:** `src/ui_qml/platform/qml/workspaces/settings/SettingsWorkspacePage.qml`

---

### Phase 6 — Validation
**Status:** `[x] complete`

Run `python main_qt.py`, navigate every workspace section, and confirm:
- No QML errors in console
- All DataTables render (empty state if no data, no crash)
- Tab navigation works in Control Center
- Settings sidebar sections all load
- Admin Console all entity nav items load

---

## Completion Checklist

- [x] Phase 1: Admin entity-specific columns
- [x] Phase 2: Control Center panel nav tabs
- [x] Phase 3: Control Center ActivityFeed widget
- [x] Phase 4: Settings Security section
- [x] Phase 5: Settings Support & Diagnostics section
- [x] Phase 6: Validation run
