# Cross-Module Integration Layer — Architecture Plan

**Created:** 2026-05-26  
**Branch:** refactor/safe-start  
**Author:** Claude Code (Integration Architecture Task)

---

## 1. Architecture Audit Findings

### 1.1 Existing Platform-owned master data ✅

| Concept | Table | Service |
|---------|-------|---------|
| Organization | organizations | OrganizationService |
| Site | sites | SiteService |
| Department | departments | DepartmentService |
| Employee | employees | EmployeeService |
| User | users | AuthService |
| Party (Vendor/Customer/Contractor) | parties | PartyService |
| Document | documents + document_links | DocumentService, DocumentIntegrationService |
| Approval Queue | approval_requests | ApprovalService |
| Audit Log | audit_entries | AuditService |
| Module Entitlements | module_entitlements | ModuleCatalogService |

All master data is Platform-owned. ✅ No duplication found in PM or Inventory.

---

### 1.2 Existing cross-module Platform FKs ✅

These FKs already exist in the ORM and point to Platform-owned tables:

| Table | Column | References |
|-------|--------|-----------|
| inventory_storerooms | site_id | sites.id ✅ |
| inventory_storerooms | manager_party_id | parties.id ✅ |
| inventory_purchase_orders | site_id | sites.id ✅ |
| inventory_purchase_orders | supplier_party_id | parties.id ✅ |
| inventory_purchase_orders | approval_request_id | approval_requests.id ✅ |
| inventory_purchase_requisitions | requesting_site_id | sites.id ✅ |
| inventory_purchase_requisitions | requester_user_id | users.id ✅ |
| inventory_purchase_requisitions | approval_request_id | approval_requests.id ✅ |
| inventory_receipt_headers | supplier_party_id | parties.id ✅ |
| inventory_receipt_headers | received_by_user_id | users.id ✅ |
| inventory_reorder_policies | preferred_supplier_party_id | parties.id ✅ |

**PM module** — ProjectORM has no organization_id, site_id, or client_party_id FK yet.  
See Section 5 (Future Work) for PM→Platform FK roadmap.

---

### 1.3 Existing soft-reference fields (partial) ⚠️

These soft-reference fields existed before this task, but had no snapshot columns:

| Table | Existing columns | Status |
|-------|-----------------|--------|
| inventory_stock_reservations | source_reference_type, source_reference_id | ✅ existed |
| inventory_stock_transactions | reference_type, reference_id | ✅ existed |
| inventory_purchase_requisitions | source_reference_type, source_reference_id | ✅ existed |

**Missing (now added by this task):** `source_module`, `source_entity_type`, `source_code_snapshot`, `source_title_snapshot`, `source_status_snapshot` on reservations and requisitions.

---

### 1.4 Entitlement system ✅

| Service | Location | API |
|---------|----------|-----|
| ModuleCatalogService | src/core/platform/modules/ | is_enabled(code), is_licensed(code), get_entitlement(code) |
| ModuleRuntimeService | src/application/runtime/entitlement_runtime.py | wraps catalog service |
| Module codes | DEFAULT_ENTERPRISE_MODULES | project_management, inventory_procurement, maintenance_management, qhse, hr_management |

No `ModuleRegistry` with capability-level methods existed before this task.

---

### 1.5 Cross-module imports audit ⚠️

Found legitimate cross-module wiring at the composition layer:
- `src/infra/composition/app_container.py` — imports all modules into ServiceGraph (correct, this is the DI root)
- `src/api/desktop/runtime.py` — DesktopApiRegistry assembles all module APIs (correct)
- `src/api/desktop/platform/audit.py` — imports PM services for audit context enrichment (acceptable at API layer)

No hard imports of one module inside another module's domain/application layer found. ✅

---

## 2. What Was Implemented (This Task)

### 2.1 Integration Domain Layer ✅ DONE

**Files created:**

```
src/core/platform/integration/
├── __init__.py
├── cross_module_reference.py   CrossModuleReference + ResolvedReference value objects
├── module_registry.py          ModuleRegistry — capability-aware entitlement facade
└── resolver.py                 IntegrationResolver — resolves refs for display
```

#### ModuleRegistry API

```python
module_registry.is_module_enabled("inventory_procurement")  # → bool
module_registry.has_capability("inventory.reservations.create")  # → bool
module_registry.can_open_reference("project_management", "task")  # → bool
module_registry.can_create_reference("inventory_procurement", "reservation")  # → bool
module_registry.can_use_integration(
    "project_management", "inventory_procurement", "material_demand"
)  # → bool (checks both modules enabled + integration rule)
module_registry.capability_snapshot()  # → dict[str, bool] for QML binding
```

Supported module IDs: `platform`, `project_management`, `inventory_procurement`,
`maintenance_management`, `qhse`, `hr_management`

Supported integration pairs:
- project_management ↔ inventory_procurement: `material_demand`, `source_reference`
- inventory_procurement ↔ maintenance_management: `source_reference`
- maintenance_management → inventory_procurement: `material_demand`

#### CrossModuleReference shape

```python
CrossModuleReference(
    module_id="project_management",
    entity_type="task",
    entity_id="task_123",
    code_snapshot="TASK-0032",
    title_snapshot="Replace pump seal",
    status_snapshot="Open",
)
```

#### ResolvedReference shape (for QML)

```python
{
    "moduleId": "project_management",
    "entityType": "task",
    "entityId": "task_123",
    "codeSnapshot": "TASK-0032",
    "titleSnapshot": "Replace pump seal",
    "statusSnapshot": "Open",
    "moduleEnabled": True,         # or False if PM not licensed
    "sourceAvailable": True,       # False if record was deleted
    "routeAvailable": True,
    "canOpen": True,               # moduleEnabled AND routeAvailable
    "disabledReason": "",          # "Module not enabled" | "Source unavailable" | ""
    "route": "project_management.tasks",  # shell route_id for navigation
    "displayTitle": "Replace pump seal",
    "displaySubtitle": "TASK-0032",
    "displayStatus": "Open",
}
```

#### IntegrationResolver.from_soft_reference() — ORM helper

```python
# In any serializer — extract ORM soft fields:
ref = IntegrationResolver.from_soft_reference(
    source_module=orm_row.source_module,
    source_entity_type=orm_row.source_entity_type,
    source_entity_id=orm_row.source_reference_id,
    source_code_snapshot=orm_row.source_code_snapshot,
    source_title_snapshot=orm_row.source_title_snapshot,
    source_status_snapshot=orm_row.source_status_snapshot,
)
# Returns None if no link is set (all three identity fields must be non-empty)
```

---

### 2.2 Snapshot Fields — ORM + Migration ✅ DONE

**ORM models updated:**
- `StockReservationORM` — added `source_module`, `source_entity_type`, `source_code_snapshot`, `source_title_snapshot`, `source_status_snapshot`
- `PurchaseRequisitionORM` — same five columns

**Migration file:**
```
src/infra/persistence/migrations/versions/
    g0h1i2j3k4l5_add_cross_module_reference_snapshots.py
```
- Revision: `g0h1i2j3k4l5`
- Down revision: `c6d7e8f9a0b1` (inventory foundation tables)
- Uses `batch_alter_table` + `if_not_exists` for safe idempotent execution
- Adds index on `source_module` for both tables

---

### 2.3 IntegrationCapabilityDesktopApi ✅ DONE

```
src/api/desktop/integration/
├── __init__.py
└── capability_api.py   IntegrationCapabilityDesktopApi + build_integration_capability_api()
```

Exposes to controllers/presenters:
- `is_module_enabled(module_id)` → bool
- `has_capability(capability_id)` → bool
- `can_use_integration(source, target, capability)` → bool
- `capability_snapshot()` → dict[str, bool]
- `resolve_reference(ref)` → dict (QML-safe)
- `resolve_soft_reference(source_module, entity_type, entity_id, ...)` → dict

---

### 2.4 ServiceGraph + DesktopApiRegistry Wiring ✅ DONE

**app_container.py:**
- `ServiceGraph.module_registry: ModuleRegistry` — new field
- `ServiceGraph.integration_resolver: IntegrationResolver` — new field
- `build_service_graph()` now constructs both using platform's `ModuleRuntimeService`

**runtime.py:**
- `DesktopApiRegistry.integration_capability: IntegrationCapabilityDesktopApi` — new field
- `build_desktop_api_registry()` reads `module_registry` from services dict, or builds a fallback registry if not present (defensive, never crashes)

---

### 2.5 QML Capability Slots ✅ DONE

**platform/context.py** — `PlatformWorkspaceCatalog` gains:

```qml
// In any QML workspace:
import Platform.Controllers 1.0

// Check module availability
platformCatalog.isModuleEnabled("inventory_procurement")  // → bool
platformCatalog.hasCapability("inventory.reservations.create")  // → bool
platformCatalog.canUseIntegration("project_management", "inventory_procurement", "material_demand")

// Get all capability flags at once (bind to a local property)
platformCatalog.capabilitySnapshot()
// Returns: {
//   isPlatformEnabled: true,
//   isProjectManagementEnabled: true/false,
//   isInventoryProcurementEnabled: true/false,
//   isMaintenanceEnabled: true/false,
//   canPmLinkInventory: true/false,
//   canInventoryLinkPm: true/false,
//   canInventoryLinkMaintenance: true/false,
//   canMaintenanceLinkInventory: true/false,
// }

// Resolve a soft reference for display
var resolved = platformCatalog.resolveSoftReference(
    "project_management",   // source_module
    "task",                 // source_entity_type
    "task_abc",             // source_entity_id
    "TASK-0032",            // code_snapshot
    "Replace pump seal",    // title_snapshot
    "Open"                  // status_snapshot
)
// Returns resolved dict — always safe, never crashes
// resolved.canOpen → true if PM enabled, false + disabledReason if not
```

---

## 3. Connection Map — Current State

### 3.1 Platform → All Modules ✅

```
Platform.Site     → StoreroomORM.site_id            (FK, implemented)
Platform.Site     → PurchaseOrderORM.site_id         (FK, implemented)
Platform.Party    → PurchaseOrderORM.supplier_party_id (FK, implemented)
Platform.Party    → StoreroomORM.manager_party_id    (FK, implemented)
Platform.Party    → ReorderPolicyORM.preferred_supplier_party_id (FK, implemented)
Platform.User     → StockReservationORM.requested_by_user_id (FK, implemented)
Platform.User     → StockTransactionORM.performed_by_user_id (FK, implemented)
Platform.User     → PurchaseRequisitionORM.requester_user_id (FK, implemented)
Platform.User     → ReceiptHeaderORM.received_by_user_id (FK, implemented)
Platform.Approval → PurchaseOrderORM.approval_request_id (FK, implemented)
Platform.Approval → PurchaseRequisitionORM.approval_request_id (FK, implemented)
```

### 3.2 Optional Module References ✅ (schema ready, service wiring TODO)

```
StockReservationORM
    source_module          → "project_management" | "maintenance_management" | ...
    source_entity_type     → "task" | "work_order" | ...
    source_reference_id    → entity ID in source module
    source_code_snapshot   → e.g., "TASK-0032"
    source_title_snapshot  → e.g., "Replace pump seal"
    source_status_snapshot → e.g., "Open"

PurchaseRequisitionORM
    source_module          → "inventory_procurement" | "project_management" | ...
    source_entity_type     → "shortage" | "reservation" | "task" | ...
    source_reference_id    → entity ID
    source_code_snapshot   → snapshot label
    source_title_snapshot  → snapshot title
    source_status_snapshot → snapshot status
```

### 3.3 Resolution Layer ✅

```
IntegrationResolver.from_soft_reference()   → CrossModuleReference | None
IntegrationResolver.resolve_reference()     → ResolvedReference
IntegrationResolver.display_reference()     → dict (QML-safe)
IntegrationResolver.resolve_missing_source() → ResolvedReference with sourceAvailable=False
```

---

## 4. Validation Scenarios

| Scenario | Expected behavior | Status |
|----------|------------------|--------|
| Platform only | All Platform services work, no cross-module actions shown | ✅ registry returns False for optional modules |
| PM only | PM works, inventory/maintenance actions hidden | ✅ isInventoryProcurementEnabled → False |
| Inventory only | Inventory works, PM source refs show snapshot-only (no Open button) | ✅ canOpen → False + disabledReason |
| Procurement only | Same as Inventory (both in inventory_procurement module code) | ✅ |
| PM + Inventory | PM tasks can create reservations, inventory can show PM source | ✅ canPmLinkInventory → True |
| Inventory + Procurement | Full requisition/PO flow, receipts post stock movements | ✅ same module code |
| PM + Inventory + Procurement | Full demand→reserve→requisition→PO→receipt flow | ✅ |
| Maintenance + Inventory | WO material requirements can link to inventory | ✅ canMaintenanceLinkInventory → True |
| All modules | Everything enabled, all integration links active | ✅ |
| Source record deleted | snapshot text shown, canOpen=False, disabledReason="Source unavailable" | ✅ resolve_missing_source() |
| Module disabled after data entry | Historical snapshots readable, Open button disabled | ✅ canOpen respects module_enabled |

---

## 5. Remaining Work

### Phase 6 — PM→Platform FKs ✅ COMPLETE (2026-05-26)

ProjectORM now has Platform FKs:
- `organization_id` → organizations.id
- `site_id` → sites.id
- `client_party_id` → parties.id (nullable)
- `manager_user_id` → users.id (nullable)

Migration: `h1i2j3k4l5m6_add_project_platform_fks` (down_revision: g0h1i2j3k4l5)

Updated: `Project` domain model, `ProjectORM`, `project_to_orm`/`project_from_orm` mappers,
`ProjectDesktopDto`, `ProjectCreateCommand`, `ProjectUpdateCommand`, `ProjectLifecycleMixin.create_project()`
and `update_project()`.

### Phase 7 — Service-level integration wiring ✅ COMPLETE (2026-05-26)

Snapshot fields now flow through the full stack for both reservation and requisition creation:

**StockReservation** — new fields: `source_module`, `source_entity_type`, `source_code_snapshot`,
`source_title_snapshot`, `source_status_snapshot`

**PurchaseRequisition** — same 5 new snapshot fields added

Updated: domain models, ORM mappers (both inventory + procurement), `ReservationService.create_reservation()`,
`ProcurementLifecycleMixin.create_requisition()` and `update_requisition()`,
`InventoryReservationCreateCommand`, `InventoryRequisitionCreateCommand`, `InventoryRequisitionUpdateCommand`,
`InventoryReservationDesktopDto`, `InventoryRequisitionDesktopDto`,
`serialize_reservation()`, `serialize_requisition()`.

### Phase 8 — QML capability-aware UI ✅ COMPLETE (2026-05-26)

All four cross-module workspace pages now declare `property var platformCatalog` (auto-injected by
`MainWindow.qml`) and load capability snapshot on `Component.onCompleted`:

- **TasksWorkspacePage.qml** — `_caps.canPmLinkInventory` gates "Reserve Material" in `_detailActions`
- **ReservationsWorkspacePage.qml** — `platformCatalog` + `_caps` wired
- **ProcurementWorkspacePage.qml** — `platformCatalog` + `_caps` wired
- **WorkOrdersWorkspacePage.qml** — `platformCatalog` + `_caps` wired (`canMaintenanceLinkInventory`)

### Phase 9 — Audit + Approval integration enrichment (Future sprint)

`platform/audit.py` currently enriches audit with PM entity names.
Extend to also pull Inventory entity names for reservation/PO audit events.

### Phase 10 — Document links for cross-module entities (Future sprint)

`DocumentLinkORM` already supports entity_type + entity_id cross-module links.
Wire `DocumentIntegrationService` calls into:
- Reservation service (attach docs to reservation)
- PO service (attach docs to PO — partially exists)
- Maintenance WO service (already has MaintenanceDocumentService)

---

## 6. Architecture Principles Enforced

1. **Platform owns master data** — no duplication of Site/Party/User/Department in optional modules
2. **Required Platform references** = normal SQLAlchemy ForeignKey
3. **Optional module references** = soft references (source_module + source_entity_type + source_reference_id + snapshot columns)
4. **Snapshots always present** — even if source deleted or module disabled, last-known text is readable
5. **Never crash on disabled module** — ModuleRegistry.is_module_enabled() safe to call, IntegrationResolver always returns a displayable dict
6. **No circular imports** — ModuleRegistry lives in `platform/integration/` (no module-specific imports); each module's API classes can receive it as a constructor arg
7. **DI root at app_container.py** — only composition layer imports across modules

---

## 7. Files Changed in This Task

| File | Action |
|------|--------|
| src/core/platform/integration/__init__.py | Created |
| src/core/platform/integration/cross_module_reference.py | Created |
| src/core/platform/integration/module_registry.py | Created |
| src/core/platform/integration/resolver.py | Created |
| src/api/desktop/integration/__init__.py | Created |
| src/api/desktop/integration/capability_api.py | Created |
| src/infra/persistence/migrations/versions/g0h1i2j3k4l5_add_cross_module_reference_snapshots.py | Created |
| src/core/modules/inventory_procurement/infrastructure/persistence/orm/inventory.py | Modified — snapshot fields on StockReservationORM |
| src/core/modules/inventory_procurement/infrastructure/persistence/orm/procurement.py | Modified — snapshot fields on PurchaseRequisitionORM |
| src/infra/composition/app_container.py | Modified — ModuleRegistry + IntegrationResolver in ServiceGraph |
| src/api/desktop/runtime.py | Modified — IntegrationCapabilityDesktopApi in DesktopApiRegistry |
| src/ui_qml/platform/context.py | Modified — isModuleEnabled / hasCapability / capabilitySnapshot / resolveSoftReference slots on PlatformWorkspaceCatalog |
| docs/integration_plan.md | Created (this file) |
