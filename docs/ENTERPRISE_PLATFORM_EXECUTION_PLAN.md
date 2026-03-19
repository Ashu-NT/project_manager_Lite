# Enterprise Platform Execution Plan

## Objective

Evolve the current project management app into a modular enterprise platform without losing the PM capability already built.

Initial target modules:

- `project_management`
- `inventory_procurement`
- `maintenance_management`
- `qhse`
- `hr_management`

This migration must preserve the current PM workflows while introducing platform-level shared services, module boundaries, and future licensing hooks.

## Non-Negotiable Safeguards

- Keep the current PM module working during every phase.
- Do not delete or rewrite working PM services until compatibility wrappers exist.
- Prefer additive changes first, moves later.
- Keep all existing tests for PM, enterprise PM, and shell navigation passing at each phase.
- Treat `auth`, `access`, `audit`, `approval`, `attachments`, `notifications`, and module entitlement as platform concerns.

## Cross-Platform Sharing Rules

This platform should be governed by one core rule:

**share enterprise capabilities, not business ownership.**

That means:

- shared capabilities live once and are reused everywhere
- business workflows stay inside the module that owns them
- module ownership is defined by business workflow truth, not by which module happens to consume the data most
- modules integrate through contracts, references, and events
- shared masters stay platform-owned unless they are explicitly designated as module-owned
- direct cross-module schema ownership and duplicated master data should be avoided
- no module should quietly become a second platform

The short frozen decision record for these ownership boundaries is `docs/architecture_decisions/ADR-001-cross-platform-ownership-model.md`.

## Platform End-State

## Recommended Repository Shape

The safest restructure for this repo is a hybrid approach:

- keep the current top-level layers
  - `core/`
  - `infra/`
  - `ui/`
- inside each layer, introduce:
  - `platform/`
  - `modules/`

Target shape:

```text
core/
  platform/
  modules/
    project_management/
    inventory_procurement/
    maintenance_management/
    qhse/
    hr_management/

infra/
  platform/
  modules/
    project_management/
    inventory_procurement/
    maintenance_management/
    qhse/
    hr_management/

ui/
  platform/
    shell/
  modules/
    project_management/
    inventory_procurement/
    maintenance_management/
    qhse/
    hr_management/
```

Why this structure is preferred:

- it preserves the current layered architecture that already works
- it avoids a destabilizing top-level rewrite
- it makes shared enterprise concerns clearly platform-owned
- it lets the current PM capability become `project_management` without deleting working code

### Shared Platform Capabilities

- identity and access: `auth`, sessions, RBAC, permissions, entitlement, and workspace visibility stay platform-owned so every module uses one access model
- organization structure: organization, site, department, and employee master data stay shared so permissions, reporting, and runtime context do not drift per module
- department ownership note: `department` starts shared; if workforce complexity later becomes HR-owned, the platform should still keep a stable reference model for all modules
- party master: platform owns party identity; modules own their operational relationships to suppliers, manufacturers, vendors, contractors, and service providers
- documents and attachments: platform owns storage, metadata, versioning support, attachment plumbing, and object-linking infrastructure
- audit and traceability: platform owns common audit format, entity and status transition traceability, and future correlation support
- approvals and workflow: platform owns approval request creation, routing, assignment, and decision infrastructure
- notifications and inbox: platform owns the awareness layer, while action screens remain module-owned
- shared timesheets: platform owns the shared time boundary so PM, Maintenance, and HR Management can consume approved time consistently
- shared reporting primitives: platform owns the reporting framework, shared filters, and export patterns

### Business Modules

- `project_management`: current PM app promoted as Module 1
- `inventory_procurement`: item master, storerooms, stock control, purchasing, and receiving
- `maintenance_management`: assets, work orders, preventive maintenance, downtime
- `qhse`: incidents, inspections, audits, CAPA, permits, compliance
- `hr_management`: employee operations, approved time intake, payroll preparation, approval, and export

## Cross-Module Integration Pattern

The implementation direction for business-module collaboration should stay explicit:

- inventory, maintenance, HR Management, and QHSE should consume shared platform capabilities without reimplementing them
- reference shared or external records by stable IDs and business keys rather than duplicating master data
- use domain events for cross-module refresh, synchronization, and awareness signals
- avoid direct table ownership crossover even when modules are tightly related
- avoid embedding inventory, HR, QHSE, or platform workflow logic inside maintenance services
- keep read and write boundaries module-owned even when UI flows deep-link across modules

The concrete implementation tracker for bringing the current codebase in line with these rules lives in `docs/platform_alignment_followup/README.md`.
The PM-specific technical follow-up tracker lives in `docs/project_management_followup/README.md`.

## Concrete Execution Order

### Phase 0: Protect What Exists

Status: completed

1. Write the migration plan into the repo.
2. Introduce a module catalog service with PM as the only enabled production module.
3. Keep current PM workspaces and services mapped to that module without changing behavior.
4. Add tests that prove the app still boots as a PM app while becoming module-aware.

### Phase 1: Platform Spine

Status: completed

1. Create platform-level packages under existing layers:
   - `core/platform/`
   - `infra/platform/`
   - `ui/platform/`
   - `core/modules/`
   - `infra/modules/`
   - `ui/modules/`
2. Move shared concerns there by compatibility-first extraction:
   - auth/session/RBAC
   - access
   - audit
   - approvals
   - attachments
   - notification/event routing
3. Add a persistent module entitlement model.
4. Add shell filtering based on enabled modules.

Exit criteria:

- PM still runs unchanged
- platform services no longer feel PM-owned
- shell knows which modules are enabled

### Phase 2: PM Becomes Module 1

Status: completed

1. Define PM as a named business module in code and docs.
2. Introduce module-owned workspace metadata for PM.
3. Gradually group PM-specific code under a PM module namespace while keeping compatibility imports.
4. Keep shared services outside the PM namespace.

Exit criteria:

- current PM app is explicitly treated as `project_management`
- no PM workspace depends on future module code

### Phase 3: Shared Time and Employee Model

Status: completed

1. Extract timesheet and employee concepts so they can be consumed by PM, Maintenance, and HR Management.
2. Define canonical entities:
   - `employee`
   - `site`
   - `department`
   - `timesheet_period`
   - `work_entry`
3. Keep PM resource planning intact while preparing shared time intake.

Progress already shipped:

- canonical shared time domain types now live under `core/platform/time`
- shared time service orchestration now exists at the platform layer with PM compatibility wrappers preserved
- canonical time persistence now lives under `infra/platform/db/time` with PM repository wrappers preserved
- work entries now carry module-neutral ownership plus employee/site/department snapshot context
- employees now include site context so PM resources and future modules can resolve shared work-entry metadata from platform records

Exit criteria:

- PM time approval still works
- HR Management and maintenance can later consume approved time from the same platform

### Phase 4: Inventory & Procurement Module Skeleton

Status: in progress

Detailed implementation blueprint: `docs/inventory_procurement/README.md`

1. Add module scaffold only:
   - service package
   - UI workspace registration
   - placeholder dashboard/items/purchasing
2. Add core entities:
   - item master
   - storeroom
   - stock balance
   - purchase requisition
   - purchase order
3. Connect to shared party master, approval, document, audit, and time services where applicable.

Exit criteria:

- inventory and procurement exist as a separate module
- no PM code regression

### Phase 5: Maintenance Module Skeleton

Status: pending

1. Add module scaffold only:
   - service package
   - UI workspace registration
   - placeholder dashboard/work orders
2. Add core entities:
   - asset
   - work order
   - maintenance plan
3. Connect to shared employee, approval, document, audit, and time services.
4. Integrate materials, reservations, issue/return, and purchase demand through the `inventory_procurement` module instead of duplicating stock ledgers inside maintenance.

Exit criteria:

- maintenance exists as a separate module
- inventory and procurement integration seams are explicit

### Phase 6: QHSE Module Skeleton

Status: pending

1. Add incidents, inspections, audits, and CAPA domain types.
2. Allow QHSE records to link to project, site, asset, or work order.
3. Reuse platform approvals, documents, notifications, and audit logging.

Exit criteria:

- QHSE is independently modeled
- cross-module linkage is explicit, not hardcoded inside PM

### Phase 7: HR Management Module (Payroll-First)

Status: pending

1. Start with payroll preparation and export inside `hr_management`, not full statutory payroll for every country.
2. Consume approved time from PM and Maintenance.
3. Add payroll periods, run state, approval, exception handling, and export.
4. Keep country-specific tax logic behind adapters if later expanded.

Exit criteria:

- HR Management is module-based
- no duplication of timesheet logic

### Phase 8: Commercial Module Enablement

Status: in progress

1. Add module entitlement persistence.
2. Hide disabled module workspaces from the shell.
3. Restrict service registration and navigation by enabled module set.
4. Add customer-facing module metadata for packaging and pricing.

Exit criteria:

- customers can buy only the modules they need
- disabled modules stay out of the runtime surface

## Exact Technical Rules

- Use additive extraction with compatibility wrappers.
- Never move a service and break imports in one step.
- Promote shared concepts before introducing cross-module dependencies.
- Keep shell navigation grouped by module and platform area.
- Avoid top-level package names that conflict with the Python standard library.

## Current Recommended Next Step

1. Start Phase 4 with the `inventory_procurement` module scaffold across `core`, `infra`, and `ui`.
2. Define item, storeroom, stock, requisition, purchase-order, and receiving seams so other modules can depend on them cleanly.
3. Start Phase 5 maintenance scaffolding with explicit material-demand integration into `inventory_procurement`.
