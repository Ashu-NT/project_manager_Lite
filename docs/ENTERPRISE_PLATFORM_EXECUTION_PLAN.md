# Enterprise Platform Execution Plan

## Objective

Evolve the current project management app into a modular enterprise platform without losing the PM capability already built.

Initial target modules:

- `project_management`
- `maintenance_management`
- `qhse`
- `payroll`

This migration must preserve the current PM workflows while introducing platform-level shared services, module boundaries, and future licensing hooks.

## Non-Negotiable Safeguards

- Keep the current PM module working during every phase.
- Do not delete or rewrite working PM services until compatibility wrappers exist.
- Prefer additive changes first, moves later.
- Keep all existing tests for PM, enterprise PM, and shell navigation passing at each phase.
- Treat `auth`, `access`, `audit`, `approval`, `attachments`, `notifications`, and module entitlement as platform concerns.

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
    maintenance_management/
    qhse/
    payroll/

infra/
  platform/
  modules/
    project_management/
    maintenance_management/
    qhse/
    payroll/

ui/
  platform/
    shell/
  modules/
    project_management/
    maintenance_management/
    qhse/
    payroll/
```

Why this structure is preferred:

- it preserves the current layered architecture that already works
- it avoids a destabilizing top-level rewrite
- it makes shared enterprise concerns clearly platform-owned
- it lets the current PM capability become `project_management` without deleting working code

### Shared Platform Capabilities

- identity and RBAC
- module catalog and entitlement
- organization, site, department, employee master data
- approvals and workflow
- audit log
- notifications and inbox
- documents and attachments
- shared timesheets
- shared reporting primitives

### Business Modules

- `project_management`: current PM app promoted as Module 1
- `maintenance_management`: assets, work orders, preventive maintenance, downtime
- `qhse`: incidents, inspections, audits, CAPA, permits, compliance
- `payroll`: approved time intake, payroll preparation, approval, export

## Concrete Execution Order

### Phase 0: Protect What Exists

Status: start here

1. Write the migration plan into the repo.
2. Introduce a module catalog service with PM as the only enabled production module.
3. Keep current PM workspaces and services mapped to that module without changing behavior.
4. Add tests that prove the app still boots as a PM app while becoming module-aware.

### Phase 1: Platform Spine

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

1. Define PM as a named business module in code and docs.
2. Introduce module-owned workspace metadata for PM.
3. Gradually group PM-specific code under a PM module namespace while keeping compatibility imports.
4. Keep shared services outside the PM namespace.

Exit criteria:

- current PM app is explicitly treated as `project_management`
- no PM workspace depends on future module code

### Phase 3: Shared Time and Employee Model

1. Extract timesheet and employee concepts so they can be consumed by PM, Maintenance, and Payroll.
2. Define canonical entities:
   - `employee`
   - `site`
   - `department`
   - `timesheet_period`
   - `work_entry`
3. Keep PM resource planning intact while preparing shared time intake.

Exit criteria:

- PM time approval still works
- payroll and maintenance can later consume approved time from the same platform

### Phase 4: Maintenance Module Skeleton

1. Add module scaffold only:
   - service package
   - UI workspace registration
   - placeholder dashboard/work orders
2. Add core entities:
   - asset
   - work order
   - maintenance plan
3. Connect to shared employee, approval, document, and audit services.

Exit criteria:

- maintenance exists as a separate module
- no PM code regression

### Phase 5: QHSE Module Skeleton

1. Add incidents, inspections, audits, and CAPA domain types.
2. Allow QHSE records to link to project, site, asset, or work order.
3. Reuse platform approvals, documents, notifications, and audit logging.

Exit criteria:

- QHSE is independently modeled
- cross-module linkage is explicit, not hardcoded inside PM

### Phase 6: Payroll Preparation Module

1. Start with payroll preparation and export, not full statutory payroll for every country.
2. Consume approved time from PM and Maintenance.
3. Add payroll periods, run state, approval, exception handling, and export.
4. Keep country-specific tax logic behind adapters if later expanded.

Exit criteria:

- payroll is module-based
- no duplication of timesheet logic

### Phase 7: Commercial Module Enablement

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

## First Execution Slice

This phase is intentionally low risk and starts immediately:

1. Add a platform module catalog service.
2. Register `project_management` as enabled.
3. Register `maintenance_management`, `qhse`, and `payroll` as planned.
4. Expose module state through the service graph.
5. Make the main shell display module context while keeping current PM behavior.
6. Add tests for module catalog and shell awareness.

## Follow-Up After This Slice

Next recommended implementation step:

1. Add persistent module entitlement storage.
2. Separate platform workspaces from PM workspaces in shell metadata.
3. Extract timesheet ownership from PM into a shared platform service boundary.
4. Start moving low-risk shared UI infrastructure such as the shell into `ui/platform/` with compatibility wrappers.
