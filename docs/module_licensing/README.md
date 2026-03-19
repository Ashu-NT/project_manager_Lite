# Module Licensing Execution Plan

## Objective

Introduce a real module licensing model for the enterprise platform without breaking the current PM application, and without forcing a full API or multi-tenant rewrite first.

This licensing model needs to support:

- a mandatory `Platform Base`
- optional paid modules per client
- shell visibility based on enabled modules
- backend checks based on the same entitlement rules
- a future move to organization or tenant-specific entitlements

## Current Reality

The repo already has a lightweight product catalog:

- `project_management` is enabled by default
- `inventory_procurement`, `maintenance_management`, `qhse`, and `hr_management` are present as planned modules

What it does not yet have:

- a distinction between `licensed` and `enabled`
- platform-base capability modeling
- a path from single-install defaults to client-specific entitlements
- shell filtering that is explicitly driven by entitlement state

## Target Licensing Model

There are four distinct concepts and we should keep them separate:

1. `Installed`
   The code exists in the product build.
2. `Licensed`
   The client has paid for the module.
3. `Enabled`
   The module is turned on in the runtime.
4. `Accessible`
   The current user is allowed to use it based on RBAC and scope rules.

For now, this repo is still a single-install application, so Phase 1 will implement `install-wide entitlements`.
Later, the same model will be persisted per organization or tenant.

## Product Split

### Platform Base

Platform Base is always active and should not be sold as a business module.

Initial platform capabilities:

- `users`
- `access`
- `audit`
- `approvals`
- `employees`
- `documents`
- `inbox`
- `notifications`
- `settings`

### Business Modules

- `project_management`
- `inventory_procurement`
- `maintenance_management`
- `qhse`
- `hr_management`

## Technical Model

### Catalog Layer

The catalog describes what the product supports:

- module code
- label
- description
- product stage
- primary capabilities

### Entitlement Layer

The entitlement state describes what a given client can use:

- module code
- licensed
- enabled
- product stage
- visible in shell
- accessible in runtime

### Capability Layer

Capabilities represent shared platform functionality and module-owned feature sets.

Examples:

- platform capability: `employees`
- module capability: `projects`
- module capability: `payroll_runs`

## Implementation Phases

### Phase 1: Install-Wide Entitlements

Status: completed

Goal:

- evolve the existing module catalog into a richer entitlement-aware service
- keep configuration install-wide for now
- avoid database persistence until the runtime contract is stable

Concrete work:

1. Add platform-base capability definitions.
2. Add module entitlement snapshots over the existing catalog.
3. Distinguish `licensed`, `enabled`, `available`, and `planned`.
4. Expose helper methods for shell and later backend guards.
5. Gate Project Management workspaces through the entitlement service.
6. Update Platform Home to speak in licensing language.
7. Add focused tests for entitlement state and module-aware workspace gating.

Exit criteria:

- the platform knows which modules are licensed and enabled
- PM workspaces can be hidden when PM is not enabled
- Platform Base remains visible regardless of business modules

### Phase 2: Persistent Local Entitlements

Status: completed

Goal:

- move entitlement state from config-only behavior into the application database

Concrete work:

1. Add module entitlement ORM models and repositories.
2. Store the current install profile in the database.
3. Add a small admin surface for enabling licensed modules locally.
4. Keep env-based overrides for support and test scenarios.

Exit criteria:

- licensing state survives restarts
- shell and backend read from one source of truth

### Phase 3: Backend Enforcement

Status: completed

Goal:

- ensure disabled modules are blocked below the UI

Concrete work:

1. Add module guard helpers at the application or service boundary.
2. Enforce module access in PM entry services.
3. Keep platform-base services available independently.
4. Add a thin runtime-facing entitlement service so shell, UI, and future API callers do not depend directly on the catalog implementation.
5. Make platform tabs degrade gracefully when a dependent business module is disabled.
6. Emit audit events when module configuration changes.

Exit criteria:

- disabled modules cannot be reached by direct service calls
- audit trail captures licensing changes

### Phase 4: Organization or Tenant-Specific Entitlements

Status: completed for the desktop/runtime implementation; hosted web/server adoption is deferred

Goal:

- prepare for hosted multi-client deployments

Concrete work:

1. Introduce organization or tenant records.
   Status: completed
2. Attach module entitlements to that boundary.
   Status: completed for the active-organization runtime path
3. Move shell, backend, and future API checks to the current organization context.
   Status: completed for the desktop/runtime application seam; hosted web adoption is deferred
4. Support `trial`, `suspended`, and `expired` states.
   Status: completed for the local runtime and admin flow
5. Add a platform admin workflow for provisioning organizations with an initial licensed module mix.
   Status: completed for the desktop/runtime admin flow; hosted web adoption is deferred
6. Expose the same organization provisioning and entitlement rules through an API-facing transport boundary.
   Status: completed for the transport adapter layer; concrete web server/router adoption is deferred

Exit criteria:

- different clients can run different module mixes on the same hosted platform

## Shell Rules

- `Platform` stays visible at all times.
- Business modules are driven by entitlement state.
- Platform Home should show:
  - Platform Base summary
  - active licensed modules
  - available modules
  - planned modules
- Disabled or unavailable modules should not require UI code duplication to hide.

## Backend Rules

- shell visibility is not enough
- service or application-level guards must eventually enforce the same module state
- shared platform capabilities remain available even if no business module is enabled

## Deferred Follow-Up

Web/server delivery is intentionally deferred for now.

When that work resumes, the remaining licensing follow-up is:

1. wrap the existing transport adapter with a concrete web server/router layer
2. reuse the same application-layer and transport contracts instead of introducing separate web-only licensing rules
