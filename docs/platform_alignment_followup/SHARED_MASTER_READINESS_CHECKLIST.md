# Shared Master Readiness Checklist

## Purpose

This checklist turns the ownership model in [ADR-001](../architecture_decisions/ADR-001-cross-platform-ownership-model.md) into a concrete reuse-readiness review for the current shared platform masters.

The goal is not to ask whether a shared domain merely exists.

The goal is to ask whether it is ready for safe reuse by future modules such as:

- `inventory_procurement`
- `maintenance_management`
- `qhse`
- `hr_management`

## Review Criteria

Each shared domain is reviewed against the same checklist:

- canonical domain model exists
- canonical persistence exists
- business key strategy exists
- import/export behavior is understood
- service interfaces exist
- module-safe read access exists
- write ownership is constrained
- audit hooks exist
- linking/reference patterns are defined

Status legend:

- `READY`: implemented and usable for cross-module reuse now
- `PARTIAL`: implemented, but still missing an important reuse seam
- `GAP`: not yet ready for safe module reuse

## Status Snapshot

| Shared domain | Domain model | Persistence | Business key | Import / export | Service interfaces | Module-safe read | Write ownership | Audit hooks | Linking / reference | Overall reuse readiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `site` | `READY` | `READY` | `READY` | `PARTIAL` | `READY` | `GAP` | `READY` | `READY` | `PARTIAL` | `PARTIAL` |
| `department` | `READY` | `READY` | `READY` | `PARTIAL` | `READY` | `GAP` | `READY` | `READY` | `PARTIAL` | `PARTIAL` |
| `employee` | `READY` | `READY` | `READY` | `PARTIAL` | `READY` | `READY` | `READY` | `READY` | `PARTIAL` | `PARTIAL` |
| `party` | `READY` | `READY` | `READY` | `PARTIAL` | `READY` | `GAP` | `READY` | `READY` | `PARTIAL` | `PARTIAL` |
| `document infrastructure` | `READY` | `READY` | `READY` | `PARTIAL` | `READY` | `READY` | `READY` | `READY` | `READY` | `READY` |

## Domain Notes

### 1. Site

- Canonical domain model: `READY`
  - `Site` exists in `core/platform/org/domain.py` with operational metadata, lifecycle fields, and organization scoping.
- Canonical persistence: `READY`
  - `sites` exists in `infra/platform/db/models.py` with org-scoped uniqueness and repository wiring in `infra/platform/db/org/repository.py`.
- Business key strategy: `READY`
  - canonical key is `organization_id + site_code`.
- Import / export behavior: `PARTIAL`
  - admin CRUD behavior exists, but there is no shared CSV, Excel, sync, or export contract yet.
- Service interfaces: `READY`
  - `SiteRepository` exists in `core/platform/common/interfaces.py`; `SiteService` exists in `core/platform/org/site_service.py`.
- Module-safe read access: `GAP`
  - current read APIs are guarded by `settings.manage`, which is fine for admin ownership but not yet suitable for ordinary consuming modules.
- Write ownership: `READY`
  - writes are constrained to platform-admin ownership through `settings.manage`.
- Audit hooks: `READY`
  - `site.create` and `site.update` are audited.
- Linking / reference patterns: `PARTIAL`
  - `department.site_id` provides a canonical reference pattern, but broader module consumption is not yet exposed through a module-safe query seam.
  - employee and time records still carry readable site snapshots as strings.

### 2. Department

- Canonical domain model: `READY`
  - `Department` exists in `core/platform/org/domain.py` with hierarchy, cost-center, manager, and site references.
- Canonical persistence: `READY`
  - `departments` exists in `infra/platform/db/models.py` with repository wiring in `infra/platform/db/org/repository.py`.
- Business key strategy: `READY`
  - canonical key is `organization_id + department_code`.
- Import / export behavior: `PARTIAL`
  - admin CRUD exists, but there is no shared import/export contract yet.
- Service interfaces: `READY`
  - `DepartmentRepository` exists in `core/platform/common/interfaces.py`; `DepartmentService` exists in `core/platform/org/department_service.py`.
- Module-safe read access: `GAP`
  - current reads require `settings.manage`, so the shared master exists but is not yet safely queryable by ordinary consuming modules.
- Write ownership: `READY`
  - writes are constrained to platform-admin ownership through `settings.manage`.
- Audit hooks: `READY`
  - `department.create` and `department.update` are audited.
- Linking / reference patterns: `PARTIAL`
  - `site_id`, `parent_department_id`, and `manager_employee_id` define the canonical shape.
  - employee and approved-time records still keep department as a readable string snapshot rather than a canonical foreign-key reference.

### 3. Employee

- Canonical domain model: `READY`
  - `Employee` exists in `core/platform/org/domain.py`.
- Canonical persistence: `READY`
  - `employees` exists in `infra/platform/db/models.py` with repository wiring in `infra/platform/db/org/repository.py`.
- Business key strategy: `READY`
  - canonical key is `employee_code` and it is globally unique in the current implementation.
- Import / export behavior: `PARTIAL`
  - CRUD behavior exists, but there is no shared employee import/export or directory-sync contract yet.
- Service interfaces: `READY`
  - `EmployeeRepository` exists in `core/platform/common/interfaces.py`; `EmployeeService` exists in `core/platform/org/employee_service.py`.
- Module-safe read access: `READY`
  - `employee.read` gives ordinary module-safe read access, and PM already consumes that service.
- Write ownership: `READY`
  - writes are constrained through `employee.manage`.
- Audit hooks: `READY`
  - `employee.create` and `employee.update` are audited.
- Linking / reference patterns: `PARTIAL`
  - `resource.employee_id` and `department.manager_employee_id` already reference employee by ID.
  - employee still stores `department` and `site_name` as compatibility strings instead of referencing the shared `department` and `site` masters directly.

### 4. Party

- Canonical domain model: `READY`
  - `Party` exists in `core/platform/party/domain.py`.
- Canonical persistence: `READY`
  - `parties` exists in `infra/platform/db/models.py` with repository wiring in `infra/platform/db/party/repository.py`.
- Business key strategy: `READY`
  - canonical key is `organization_id + party_code`.
- Import / export behavior: `PARTIAL`
  - admin CRUD exists, but there is no shared import/export or ERP-sync contract yet.
- Service interfaces: `READY`
  - `PartyRepository` exists in `core/platform/party/interfaces.py`; `PartyService` exists in `core/platform/party/service.py`.
- Module-safe read access: `GAP`
  - current reads require `settings.manage`, so future modules do not yet have a safe non-admin read/query surface.
- Write ownership: `READY`
  - writes are constrained to platform-admin ownership through `settings.manage`.
- Audit hooks: `READY`
  - `party.create` and `party.update` are audited.
- Linking / reference patterns: `PARTIAL`
  - the intended shared reference is `party_id` or `party_code`, but there is not yet a first live consuming module proving the pattern end to end.
  - there is also no shared module-facing helper/query service yet for common party lookup workflows.

### 5. Document Infrastructure

- Canonical domain model: `READY`
  - `Document` and `DocumentLink` exist in `core/platform/documents/domain.py`.
- Canonical persistence: `READY`
  - `documents` and `document_links` exist in `infra/platform/db/models.py` with repositories in `infra/platform/db/documents/repository.py`.
- Business key strategy: `READY`
  - admin-managed documents use `organization_id + document_code`.
  - module-generated attachments use deterministic platform-generated document codes through `DocumentIntegrationService`.
- Import / export behavior: `PARTIAL`
  - admin create/update and module attachment registration are defined, but there is no bulk document import/export contract yet.
- Service interfaces: `READY`
  - `DocumentRepository`, `DocumentLinkRepository`, `DocumentService`, and `DocumentIntegrationService` all exist.
- Module-safe read access: `READY`
  - linked documents can be read safely by consuming modules through `DocumentIntegrationService.list_documents_for_entity(...)` after module-level auth has already passed.
  - PM already uses this pattern.
- Write ownership: `READY`
  - admin library writes are constrained through `settings.manage`.
  - module-owned attachment writes are constrained through `DocumentIntegrationService` plus module permission checks.
- Audit hooks: `READY`
  - document create, update, link, unlink, and linked-attachment creation are audited.
- Linking / reference patterns: `READY`
  - `document_links` defines the canonical pattern: `module_code + entity_type + entity_id + link_role`.
  - this is already reusable across PM and future modules.

## Immediate Follow-Up Needed Before Heavy Module Reuse

The most important reuse gaps are:

1. Add module-safe query/read services for `site`, `department`, and `party` so future modules do not need `settings.manage` just to read shared masters.
2. Decide and document import/export behavior for all five shared domains.
3. Add optional canonical `site_id` / `department_id` linkage to `employee` while keeping the current readable compatibility strings during transition.
4. Reuse the document integration pattern as the reference design for future shared-master module consumption.

## Decision Use

Before any new module starts depending on these shared masters:

- use this checklist to decide whether the shared domain is reusable as-is
- if a row is still `GAP` or materially `PARTIAL`, fix the shared domain before duplicating logic inside the module
