# ADR-001: Cross-Platform Ownership Model

- Status: accepted
- Date: 2026-03-19

## Context

The current codebase already answers most ownership questions, but the answers were spread across multiple places:

- [README.md](../../README.md)
- [ENTERPRISE_PLATFORM_EXECUTION_PLAN.md](../ENTERPRISE_PLATFORM_EXECUTION_PLAN.md)
- [maintenance_management README](../maintenance_management/README.md)
- [platform_alignment_followup README](../platform_alignment_followup/README.md)
- [defaults.py](../../core/platform/modules/defaults.py)

Before building `inventory_procurement`, the platform needs one short frozen decision that states:

- what `platform` owns
- what each business module owns
- what is shared by reference only
- what is forbidden to duplicate

The concrete reuse-readiness review for the shared masters covered by this ADR lives in [Shared Master Readiness Checklist](../platform_alignment_followup/SHARED_MASTER_READINESS_CHECKLIST.md).

The follow-on ownership clarification for `location` and `system` is frozen in [ADR-002](ADR-002-location-and-system-ownership.md).

## Decision

The governing rule is:

**share enterprise capabilities, not business ownership.**

This decision locks the current architecture direction.

## Current Implementation Status

Not everything in this ADR is already implemented.

As of 2026-03-19, the current codebase status is:

- `[x]` platform identity and access are implemented
- `[x]` platform organization references are implemented for organization, site, department, and employee
- `[x]` platform party identity is implemented
- `[x]` platform document infrastructure is implemented
- `[x]` platform approval infrastructure is implemented
- `[x]` platform audit infrastructure is implemented
- `[~]` platform notifications and inbox awareness are partially implemented through the shared event surface and PM-facing inbox/notification flows, but there is not yet a full standalone platform-owned generic inbox workflow
- `[x]` platform shared time boundary is implemented
- `[x]` platform module runtime spine is implemented
- `[x]` `project_management` is implemented as the active production business module
- `[~]` `inventory_procurement` now has an initial scaffold and shared-reference service bundle, but item, storeroom, stock, procurement, and receiving workflows are not implemented yet
- `[ ]` `maintenance_management` is not implemented yet beyond module catalog, package scaffolding, and planning blueprints
- `[ ]` `qhse` is not implemented yet beyond module catalog and package scaffolding
- `[ ]` `hr_management` is not implemented yet beyond module catalog, compatibility aliasing from legacy `payroll`, and shared platform foundations it will later consume

Shared-by-reference status today:

- `[x]` PM already consumes shared employee, site, department, documents, approvals, audit, module runtime, and shared time infrastructure
- `[x]` PM now uses shared-document linking instead of treating new collaboration attachments as PM-only metadata
- `[~]` neutral/shared-master event adoption is in place where it matters most today, but not every PM screen is moved to the neutral event layer
- `[ ]` inventory and maintenance reference-sharing rules are locked by this ADR, but those module-to-module integrations are not implemented yet because those modules are not built yet

Duplication-control status today:

- `[x]` the ownership rule is now frozen in this ADR and reflected in the main architecture docs
- `[x]` the current service graph and package layout keep shared platform capabilities out of module-local ownership
- `[~]` duplication prevention is structurally strong for the current platform plus PM runtime, but future enforcement for inventory, maintenance, QHSE, and HR will only become real as those modules are implemented

### Platform Owns

`platform` owns shared enterprise capabilities and shared reference masters:

- identity and access: auth, sessions, RBAC, permissions, access scope, module entitlement, workspace visibility
- organization reference model: organization, site, department, employee reference data
- party identity master: shared supplier, manufacturer, vendor, contractor, and service-provider identities
- document infrastructure: document metadata, storage reference, document linking, version-support plumbing
- approval infrastructure: approval request routing, assignment, decision capture, escalation plumbing
- audit and traceability infrastructure: shared audit records and status-traceability patterns
- notifications and inbox awareness: module-neutral awareness and attention routing
- shared time boundary: `work_entry`, timesheet approval boundary, and approved-time sharing
- module runtime spine: module catalog, licensing, shell visibility, shared event surface

Platform owns these once for the whole product. Business modules consume them; they do not re-implement them.

### Business Module Ownership

Business modules own their workflow truth:

- `project_management` owns projects, tasks, dependencies, schedules, resources, costs, baselines, portfolio workflows, project governance workflows, and PM collaboration context
- `inventory_procurement` owns item master, storerooms, stock balances, stock movements, reservations, requisitions, purchase orders, and receiving
- `maintenance_management` owns locations, systems, assets, components, sensors, task libraries, preventive plans, work requests, work orders, downtime, and reliability context
- `qhse` owns incidents, inspections, audits, CAPA, permits, and compliance workflow truth
- `hr_management` owns workforce and HR workflows, approved-time intake, payroll preparation, payroll runs, approval, and export

Important nuance:

- `employee`, `site`, and `department` stay platform-owned as shared reference models
- `hr_management` may own richer workforce processes over time, but it should not fork the shared reference model without a new ADR

### Shared By Reference Only

These objects may be consumed across modules, but the owning domain stays singular:

- `organization`, `site`, `department`, and `employee` are referenced by stable IDs or business keys; modules may store historical snapshots when required, but they do not own duplicate masters
- `party` is referenced by `party_id` or business key; modules own the relationship meaning, not the identity master
- `document` is referenced by `document_id` and document links; modules may describe why a document matters, but they do not own a second document library
- approvals are referenced through approval IDs and module-owned status integration; modules do not own a second approval engine
- audit records are referenced through platform audit trails; modules do not maintain separate competing audit systems
- shared time is referenced through platform time records and approved-time boundaries; modules do not maintain second authoritative timesheet engines
- once `inventory_procurement` is implemented, other modules reference item, storeroom, stock, reservation, requisition, and PO records instead of creating shadow stock masters
- once `maintenance_management` is implemented, other modules reference assets, systems, work orders, and maintenance history instead of creating shadow maintenance masters

### Forbidden To Duplicate

The following are explicitly forbidden unless a future ADR changes the rule:

- duplicating platform shared masters inside business modules
- duplicating business workflow truth inside `platform`
- creating a second employee master, site master, department master, party master, or document library inside any module
- creating a second approval, notification, inbox, audit, or timesheet engine inside any module
- creating a second item master or stock ledger outside `inventory_procurement`
- creating a second asset, work-order, or preventive-maintenance master outside `maintenance_management`
- creating a second project, task, schedule, cost, or portfolio master outside `project_management`
- creating a second incident, inspection, audit, or CAPA master outside `qhse`
- creating a second payroll or HR workflow truth outside `hr_management`
- direct cross-module schema ownership where one module writes another module's master tables as if it owned them
- letting any module quietly become a second platform

### Explicitly Allowed

The following are allowed and are not treated as forbidden duplication:

- historical snapshot fields for audit, traceability, and posted records
- generated execution records derived from templates or plans
- denormalized read models used only for UI/query performance
- import staging tables and transient synchronization buffers

These remain acceptable only when the owning system of record is still clear.

## Consequences

- `inventory_procurement` must be built as a standalone business module, not as a maintenance sub-feature and not as a platform utility
- `maintenance_management` must consume inventory, party, documents, approvals, notifications, and time through references and events
- `project_management` should keep using the shared platform services already introduced instead of carrying private copies of those capabilities
- any future exception to this ownership model requires a new ADR rather than ad hoc implementation drift
