# Project Management Module — Enterprise Modernization Plan

> **Branch:** `refactor/safe-start`
> **Started:** 2026-05-26
> **Status:** Planning complete — execution in progress

---

## Audit Summary

The PM module is **mature and well-structured**. It must NOT be rebuilt — it must be modernized and extended.

| Component | Count | State |
|-----------|-------|-------|
| QML Workspaces (main) | 11 | Exist — need UX audit + integration wiring |
| Supporting QML files | 101+ | Exist — many need density/pattern upgrade |
| Controllers | 16 (11 workspace + 5 sub) | Exist — need capability flag exposure |
| Presenters | 12 | Exist — need Inventory/Procurement fields |
| Core Services | 17 | Exist — mature |
| Desktop APIs | 12 | Exist — need material/reservation methods |
| Dialogs | 11 | Exist — mostly good |
| Platform integrations | 14 services | Wired |
| Inventory integration | 0 | **Missing — must add** |
| Procurement integration | 0 | **Missing — must add** |
| Capability gating in QML | 0 | **Missing — must add** |

**Critical gap:** Zero integration between PM and Inventory/Procurement.
No capability checks. No material demand flow. No reservation actions.

---

## Architecture Constraints

- PM **never** imports Inventory/Procurement code directly without capability checks
- PM **never** duplicates Platform master data
- PM **must not crash** if Inventory/Procurement disabled
- All cross-module actions gated via `platformCatalog.hasCapability(id)`
- Integration flows through `IntegrationCapabilityDesktopApi`

---

## Phases

---

### PHASE 1 — Capability Wiring into PM Context
**Status:** `[x] complete`
**Files:** `src/ui_qml/modules/project_management/context.py`

Wire `integration_api` into `ProjectManagementWorkspaceCatalog` so every PM controller
can check capabilities without importing optional modules.

Changes:
- Accept `integration_api: IntegrationCapabilityDesktopApi | None` in constructor
- Expose `has_capability(id)`, `is_module_enabled(id)` as Slots on the catalog
- Store `_integration_api` and pass it to controllers that need it
- Add `capabilitySnapshot() -> dict` Slot for QML snapshot binding

---

### PHASE 2 — Material Demand API (Desktop API + Service)
**Status:** `[x] complete`
**Files:**
- `src/api/desktop/project_management/tasks.py`
- `src/core/modules/project_management/application/tasks/service.py`

Add reservation integration to Task API and service (capability-gated):

```python
def list_task_reservations(task_id, *, reservation_service=None) -> list[...]
def create_task_reservation(task_id, command, *, reservation_service=None) -> Result
def get_task_material_demand(task_id) -> MaterialDemandSummary
```

Pass `reservation_service` only if Inventory module enabled at composition time.

**Files:** `src/infra/composition/project_management_registry.py` (or equivalent)
- Inject `reservation_service` into TaskService if `inventory_reservation_service` available

---

### PHASE 3 — Procurement Visibility (Desktop API + Service)
**Status:** `[x] complete`
**Files:**
- `src/api/desktop/project_management/financials.py`
- `src/core/modules/project_management/application/financials/finance_service.py`

Add procurement cost commitment data (capability-gated):

```python
def get_project_procurement_commitments(project_id, *, purchasing_service=None) -> ProcurementCommitmentSummary
def list_project_requisitions(project_id, *, procurement_service=None) -> list[...]
```

---

### PHASE 4 — Projects Workspace Modernization
**Status:** `[x] complete`
**File:** `src/ui_qml/modules/project_management/qml/ProjectManagement/Workspaces/Projects/ProjectsWorkspacePage.qml`

Current state: needs verification — inspect for:
- Does it use KpiStrip? ✓/✗
- Does it use DataTable with pagination? ✓/✗
- Does it use ContextualActionToolbar? ✓/✗
- Does it have capability-gated Inventory/Procurement sections in detail? ✓/✗

Target columns (DataTable):
```
Project Name | Code | Organization | Site | Manager | Client | Start | Finish | Progress | Budget | Status | Health
```

Detail page sections:
- Overview, Schedule, Tasks, Resources, Financials, Risks
- Material Demand *(if `inventory.reservations.create` enabled)*
- Procurement *(if `procurement.purchase_orders.read` enabled)*
- Documents, Activity

Actions: Edit, Archive, Save Baseline, Open Schedule, Open Financials, Open Risks

---

### PHASE 5 — Tasks Workspace Modernization
**Status:** `[x] complete`
**File:** `src/ui_qml/modules/project_management/qml/ProjectManagement/Workspaces/Tasks/TasksWorkspacePage.qml`

Verify and fix:
- Bulk selection checkbox performance (no expensive JS arrays in delegates)
- BulkActionBar uses shared `AppWidgets.BulkActionBar` (not custom)
- DataTable with pagination (50/100/250 rows per page)
- Dependency editing stays in Tasks workspace only (not Scheduling)

Target columns:
```
WBS | Task | Project | Assignee | Start | Finish | Progress | Duration | Float | Status | Critical | Material Demand
```

Capability-gated:
- "Material Demand" column only visible if `inventory.stock.read` enabled
- Reservation actions in detail only if `inventory.reservations.create` enabled
- Procurement link only if `procurement.requisitions.create` enabled

Detail sections: Overview, Schedule, Dependencies, Resources, Material Demand*, Reservations*, Procurement*, Documents, Activity

---

### PHASE 6 — Scheduling Workspace Panel Architecture
**Status:** `[x] complete`
**File:** `src/ui_qml/modules/project_management/qml/ProjectManagement/Workspaces/Scheduling/SchedulingWorkspacePage.qml`

Target panel-nav architecture (one panel visible at a time):
```
[Activity & Timeline] [Diagnostics] [Resources] [Baselines] [Delays] [Calendars] [Activity Feed]
```

- KpiStrip at top (always visible)
- Panel nav tab bar
- Each panel: TableToolbar + DataTable or timeline
- Dependency editing removed from here — link to Tasks workspace

---

### PHASE 7 — Dashboard Workspace as PMO Command Center
**Status:** `[x] complete`
**File:** `src/ui_qml/modules/project_management/qml/ProjectManagement/Workspaces/Dashboard/DashboardWorkspacePage.qml`

Dashboard already has rich backing (110KB API, EVM, burndown, health cards).
Modernize UX:
- KpiStrip always visible
- Compact operational panels (schedule health, cost health, risk health, resource utilization)
- Delayed tasks DataTable
- Pending approvals DataTable
- ActivityFeed (not custom ListView)
- Remove stacked card dumps
- Add lazy loading for operational tables

---

### PHASE 8 — Resources Workspace Modernization
**Status:** `[x] complete`
**File:** `src/ui_qml/modules/project_management/qml/ProjectManagement/Workspaces/Resources/ResourcesWorkspacePage.qml`

- Reference Platform Employee entities (not standalone resource records)
- Utilization DataTable with column: Employee | Department | Site | Role | Assigned Hours | Availability | Utilization %
- Overload indicator (status chip: Overloaded / Normal / Available)
- Detail: assignments, timesheets, calendar, allocations

---

### PHASE 9 — Timesheets Workspace Modernization
**Status:** `[x] complete`
**File:** `src/ui_qml/modules/project_management/qml/ProjectManagement/Workspaces/Timesheets/TimesheetsWorkspacePage.qml`

- Route approvals through Platform Approval Queue
- Status tabs: Pending | Submitted | Approved | Rejected
- DataTable with pagination
- Detail: entries, Platform approval status, linked project/task, audit

---

### PHASE 10 — Financials Workspace Modernization
**Status:** `[x] complete`
**File:** `src/ui_qml/modules/project_management/qml/ProjectManagement/Workspaces/Financials/FinancialsWorkspacePage.qml`

- Budget vs Forecast vs Actual vs Committed columns
- Procurement commitments section *(if `procurement.purchase_orders.read` enabled)*
  - Linked requisitions
  - Linked POs
  - Committed material cost
- DataTable with pagination

---

### PHASE 11 — Portfolio Workspace Modernization
**Status:** `[x] complete`
**File:** `src/ui_qml/modules/project_management/qml/ProjectManagement/Workspaces/Portfolio/PortfolioWorkspacePage.qml`

- Portfolio KPI strip
- Governance DataTable (project list with health, budget, risk)
- Risk exposure summary
- Budget visibility
- Capacity overview
- Scenarios section (what-if)
- ActivityFeed for governance events
- Remove stacked card dumps

---

### PHASE 12 — Risks Workspace Modernization
**Status:** `[x] complete`
**File:** `src/ui_qml/modules/project_management/qml/ProjectManagement/Workspaces/Risk/RiskWorkspace.qml`

- Severity/status chips (Critical / High / Medium / Low)
- Owner linked to Platform User
- DataTable with columns: Risk | Project | Owner | Probability | Impact | Severity | Status | Due
- Detail: mitigations, linked project/task, approval/escalation, audit
- Escalation via Platform Approval Queue

---

### PHASE 13 — Collaboration Workspace Modernization
**Status:** `[x] complete`
**File:** `src/ui_qml/modules/project_management/qml/ProjectManagement/Workspaces/Collaboration/CollaborationWorkspacePage.qml`

Already has good structure (Inbox, Mentions, Approvals, Activity, Team Updates, Audit).
Modernize:
- Replace custom list delegates with `AppWidgets.ActivityFeed` where applicable
- DataTables for Approvals and Inbox (not card lists)
- Remove chat-app visual patterns
- Ensure Platform Approval Queue is the approval backend
- Detail panel: full context, activity history, audit trail

---

### PHASE 14 — Cleanup & Performance
**Status:** `[ ] pending`

- Remove duplicate task table logic across workspaces
- Remove duplicate toolbar logic
- Remove duplicate bulk action sections
- Consolidate activity feed rendering (all use AppWidgets.ActivityFeed)
- Move expensive JS transformations into presenter layer
- Verify virtualization preserved in DataTable delegates
- Remove obsolete prototype widgets

---

### PHASE 15 — Integration Testing & Validation
**Status:** `[ ] pending`

Run `python main_qt.py` and validate:
- [ ] All 11 PM workspaces load without QML errors
- [ ] Projects list loads with correct columns
- [ ] Task bulk selection is smooth (no lag)
- [ ] Pagination works in all DataTables
- [ ] Scheduling panel nav works
- [ ] Dashboard operational tables load
- [ ] Collaboration Inbox/Approvals load
- [ ] PM with Inventory enabled: reservation actions visible
- [ ] PM without Inventory: reservation actions hidden (no crash)
- [ ] PM with Procurement enabled: financial commitments visible
- [ ] PM without Procurement: no crash
- [ ] Platform approval integration works in Timesheets/Collaboration
- [ ] No duplicate contextual actions
- [ ] No QML binding loop warnings
- [ ] Module feels like enterprise PM/PPM software

---

## Capability Gate Reference

| Capability ID | Required for |
|---------------|-------------|
| `inventory.reservations.create` | Task reservation actions, Material Demand section |
| `inventory.stock.read` | Task material demand column, stock status |
| `procurement.requisitions.create` | Task procurement link, shortage → requisition |
| `procurement.purchase_orders.read` | Financials procurement commitments, PO visibility |

---

## PM → Inventory → Procurement Flow

```
Task Material Demand (always visible as field)
    ↓ [if inventory.reservations.create enabled]
Inventory Reservation creation
    ↓
Stock availability check (inventory.stock.read)
    ↓ [if shortage detected and procurement.requisitions.create enabled]
Procurement Requisition creation
    ↓ [if procurement.purchase_orders.read enabled]
PO visibility in Financials committed cost
```

---

## File Change Index

| File | Phase | Change |
|------|-------|--------|
| `src/ui_qml/modules/project_management/context.py` | 1 | Add integration_api wiring + capability Slots |
| `src/api/desktop/project_management/tasks.py` | 2 | Add reservation/material demand methods |
| `src/core/modules/project_management/application/tasks/service.py` | 2 | Add reservation integration (capability-gated) |
| `src/api/desktop/project_management/financials.py` | 3 | Add procurement commitment methods |
| `src/core/modules/project_management/application/financials/finance_service.py` | 3 | Add procurement integration |
| `src/infra/composition/project_management_registry.py` | 2,3 | Inject inventory/procurement services |
| `ProjectsWorkspacePage.qml` | 4 | Modernize columns, detail sections, capability gates |
| `TasksWorkspacePage.qml` | 5 | Bulk select perf, capability-gated columns, pagination |
| `SchedulingWorkspacePage.qml` | 6 | Panel nav architecture |
| `DashboardWorkspacePage.qml` | 7 | PMO command center UX |
| `ResourcesWorkspacePage.qml` | 8 | Platform Employee reference, utilization table |
| `TimesheetsWorkspacePage.qml` | 9 | Platform Approval routing, pagination |
| `FinancialsWorkspacePage.qml` | 10 | Procurement commitments section |
| `PortfolioWorkspacePage.qml` | 11 | Governance tables, ActivityFeed |
| `RiskWorkspace.qml` | 12 | Severity chips, Platform User owner, DataTable |
| `CollaborationWorkspacePage.qml` | 13 | ActivityFeed, DataTables, Platform Approval |
| Multiple shared components | 14 | Cleanup duplicate logic |

---

## Progress Checklist

- [ ] Phase 1: Capability wiring into PM context
- [ ] Phase 2: Material demand API + service
- [ ] Phase 3: Procurement visibility API + service
- [ ] Phase 4: Projects workspace
- [ ] Phase 5: Tasks workspace
- [ ] Phase 6: Scheduling workspace
- [ ] Phase 7: Dashboard workspace
- [ ] Phase 8: Resources workspace
- [ ] Phase 9: Timesheets workspace
- [ ] Phase 10: Financials workspace
- [ ] Phase 11: Portfolio workspace
- [ ] Phase 12: Risks workspace
- [ ] Phase 13: Collaboration workspace
- [ ] Phase 14: Cleanup & performance
- [ ] Phase 15: Validation
