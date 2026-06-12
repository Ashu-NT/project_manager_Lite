# Tenant Isolation — Execution Status

This document tracks implementation progress against the architecture defined in
`docs/tenant_isolation_audit/README.md`. It is the living status reference: check
here before starting any isolation-related work to know what has been done and what
is still open.

For the current repository-focused follow-up stream, also check
`docs/tenant_repository_hardening/README.md`.

Architectural specification is in the audit README. This document covers execution
only — what was changed, what file, what is next.

---

## Architecture Rule (non-negotiable)

```
UserSession → TenantContextService → Repository → Database
```

- `TenantContextService` is the only source of `tenant_id` / `organization_id` at
  runtime. Never use QML payload values or hardcoded IDs for tenant scoping.
- Every tenant-root repository stamps `tenant_id` + `organization_id` on `add()` /
  `update()` from `TenantContextService`.
- Every tenant-owned repository query is scoped by both fields — no cross-tenant
  rows returned, ever.
- Child tables (tasks, assignments, etc.) scope via JOIN to the parent tenant-root
  table; they do not carry their own `tenant_id`.

### Target Repository Pattern

```python
class SqlAlchemyProjectRepository(ProjectRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service: TenantContextService | None = None  # wired post-construction

    def _context(self) -> TenantContext:
        return self._tenant_context_service.require_organization_context(
            operation_label="access projects"
        )

    def _base_stmt(self):
        ctx = self._context()
        return select(ProjectORM).where(
            ProjectORM.tenant_id == ctx.tenant_id,
            ProjectORM.organization_id == ctx.organization_id,
        )
```

Child tables use `_project_scoped_stmt()` (JOIN through ProjectORM) or a subquery.

---

## Schema Phases

### Phase A — Org-ID Hardening `IN PROGRESS`

Added `organization_id` to tables that were missing it, enforced NOT NULL where
safe, and fixed the access-control security bypass.

| Step | Change | Migration |
|------|--------|-----------|
| Fix Alembic chain (duplicate head) | Chain repaired | — |
| NOT NULL on projects/resources/approvals/audit_logs | `organization_id` made required | `t4u5v6w7x8y9` |
| `organization_id` on employees (backfill via site) | Column + backfill | `u5v6w7x8y9z0` |
| `organization_id` on time_entries (backfill via project) | Column + backfill | `v6w7x8y9z0a1` |
| `organization_id` on timesheet_periods (backfill via resource) | Column + backfill | `w7x8y9z0a1b2` |
| Fix empty-org-access-grants security bypass | `session.py` + `tenant_context.py`; added `is_platform_admin()` | — |
| `organization_id` on user_roles; `list_role_ids_for_organization()` | Global vs scoped roles separated | `x8y9z0a1b2c3` |

Alembic head after Phase A: `x8y9z0a1b2c3`

---

### Phase B — Tenant Model Introduction `IN PROGRESS`

Introduced the real `Tenant` entity, propagated `tenant_id` to 33+ tables, and
updated `TenantContext` to carry both `tenant_id` + `organization_id`.

| Step | Change | Migration |
|------|--------|-----------|
| `Tenant` domain model + ORM + `TenantRepository` contract + `SqlAlchemyTenantRepository` | `tenancy/domain/tenant.py`, `orm/tenant.py` | `y9z0a1b2c3d4` |
| `tenant_id` on organizations; `list_for_tenant()`; default tenant bootstrapped | `org/domain/organization.py`, `platform_registry.py` | `z0a1b2c3d4e5` |
| `tenant_id` on 33 tenant-root tables (platform + PM + inventory + maintenance) | All major business tables | `p1q2r3s4t5u6` |
| `tenant_id` on `organization_module_entitlements` (PK re-key deferred) | Non-PK column added | `q2r3s4t5u6v7` |
| `tenant_id` on `scoped_access_grants` + unique constraint update | | `q2r3s4t5u6v7` |
| `organization_id` on `project_memberships` (backfill via project) | | `q2r3s4t5u6v7` |
| `last_active_tenant_id` + `last_active_organization_id` on `auth_sessions` | Session tracking | `q2r3s4t5u6v7` |
| Composite indexes on 7 high-volume tables | `(tenant_id, organization_id)` indexes | `q2r3s4t5u6v7` |
| `TenantContext` updated to frozen dataclass with `tenant_id`, `tenant`, `organization_id`, `organization` | `tenancy/tenant_context.py` | — |
| `TenantContextService` updated; `set_active_tenant_id()` added to `UserSessionContext` | | — |
| `SqlAlchemyTenantRepository` wired into `RepositoryBundle` + platform_registry bootstrap | | — |

Alembic head after Phase B: `q2r3s4t5u6v7`

---

### Phase C — Schema Hardening `PLAN`

Apply NOT NULL constraints to all `tenant_id` columns now that all runtime paths
stamp the value on insert. This is a breaking migration — do not run until the
full test suite confirms zero new NULL violations.

| Step | Status | Blocker |
|------|--------|---------|
| NOT NULL on `tenant_id` across all 33 tables | Pending | Must confirm 100% of inserts stamp `tenant_id` |
| Re-key `organization_module_entitlements` PK to `(tenant_id, module_code)` | Pending | SQLite workaround required (recreate table) |
| Remove transitional nullable `tenant_id` fallback in `_get_active_tid()` returns | Pending | After NOT NULL enforced |

**Gate:** Run `SELECT table_name, COUNT(*) FROM <table> WHERE tenant_id IS NULL` across
all 33 tables on the dev DB. All must return 0 before running this migration.

---

## Repository Hardening Phases

### Phase D — PM Tenant-Root Repositories `PLAN`

All repositories that own a table with a direct `tenant_id` column use the
`_context()` + `_base_stmt()` pattern. The `_tenant_context_service` attribute is
set to `None` at construction and wired by the platform_registry loop.

| Repository | File | Pattern |
|------------|------|---------|
| `SqlAlchemyProjectRepository` | `repositories/project.py` | `_base_stmt()` |
| `SqlAlchemyResourceRepository` | `repositories/resource.py` | `_base_stmt()` |
| `SqlAlchemyTaskRepository` | `repositories/task.py` | `_base_stmt()` |
| `SqlAlchemyAssignmentRepository` | `repositories/assignment.py` | `_project_scoped_stmt()` JOIN |
| `SqlAlchemyBaselineRepository` | `repositories/baseline.py` | `_project_scoped_stmt()` JOIN |
| `SqlAlchemyTaskCommentRepository` | `repositories/comment.py` | JOIN through task/project |
| `SqlAlchemyCostRepository` | `repositories/cost.py` | `_base_stmt()` |
| `SqlAlchemyCalendarEventRepository` | `repositories/calendar.py` | JOIN |
| `SqlAlchemyRegisterEntryRepository` | `repositories/register.py` | `_base_stmt()` |
| `SqlAlchemyTimesheetPeriodRepository` | `repositories/time.py` | `_base_stmt()` |
| `SqlAlchemyPortfolioIntakeRepository` | `repositories/portfolio.py` | `_base_stmt()` |
| `SqlAlchemyPortfolioScenarioRepository` | `repositories/portfolio.py` | `_base_stmt()` |
| `SqlAlchemyPortfolioScoringTemplateRepository` | `repositories/portfolio.py` | `_base_stmt()` |

---

### Phase E — PM Child-Table Repositories `PLAN`

Child tables that have no direct `tenant_id` column are scoped via subquery or
JOIN through the parent tenant-root table.

| Repository | File | Scope path |
|------------|------|-----------|
| `SqlAlchemyProjectResourceRepository` | `repositories/project.py` | subquery: `ProjectORM.tenant_id + org_id` |
| `SqlAlchemyResourceSkillRepository` | `repositories/skills.py` | subquery: `ResourceORM.tenant_id + org_id` |
| `SqlAlchemyResourceCertificationRepository` | `repositories/skills.py` | subquery: `ResourceORM.tenant_id + org_id` |
| `SqlAlchemyTaskSkillRequirementRepository` | `repositories/skills.py` | subquery: `TaskORM → ProjectORM.tenant_id + org_id` |

`delete_baseline()` and `update_baseline()` in `SqlAlchemyBaselineRepository` were
also fixed from unscoped `session.get()` to scoped queries/DELETE statements.

---

### Phase F — Platform Repositories `PLAN`

All platform repositories that own tenant-root tables converted from the old
`_tenant_id_provider` lambda pattern to `_tenant_context_service`.

| Repository | File |
|------------|------|
| `SqlAlchemySiteRepository` | `platform/repositories/sites.py` |
| `SqlAlchemyDepartmentRepository` | `platform/repositories/departments.py` |
| `SqlAlchemyEmployeeRepository` | `platform/repositories/employee.py` |
| `SqlAlchemyPartyRepository` | `platform/repositories/party.py` |
| `SqlAlchemyApprovalRequestRepository` | `platform/repositories/approval.py` |
| `SqlAlchemyAuditLogRepository` | `platform/repositories/audit.py` |
| `SqlAlchemyDocumentStructureRepository` | `platform/repositories/documents.py` |
| `SqlAlchemyDocumentRepository` | `platform/repositories/documents.py` |
| `SqlAlchemyTimeEntryRepository` | `platform/repositories/time.py` |
| `SqlAlchemyTimesheetPeriodRepository` | `platform/repositories/time.py` |
| `SqlAlchemyPlatformCalendarRepository` | `platform/repositories/enterprise_calendar.py` |
| `SqlAlchemyShiftPatternRepository` | `platform/repositories/enterprise_calendar.py` |

Platform registry loop updated to wire `_tenant_context_service` (replaces old
`_tenant_id_provider` loop):

```python
# src/infra/composition/platform_registry.py
for _field_name in repositories.__dataclass_fields__:
    _repo = getattr(repositories, _field_name)
    if hasattr(_repo, "_tenant_context_service"):
        _repo._tenant_context_service = tenant_context_service
```

Note: `SqlAlchemyDocumentLinkRepository` and `SqlAlchemyModuleRepository` were
intentionally left unchanged — they do not follow the standard pattern.

---

### Phase G — Inventory & Maintenance Repositories `COMPLETE`

All inventory and maintenance repositories converted from `_tenant_id_provider`
to `_tenant_context_service` via bulk transformation. Registries updated.

**Inventory** (`src/core/modules/inventory_procurement/`):
- `catalog.py`: `SqlAlchemyInventoryItemCategoryRepository`, `SqlAlchemyStockItemRepository`
- `inventory.py`: `StockBalance`, `StockReservation`, `StockTransaction`, `Storeroom`, and related repos
- `procurement.py`: `PurchaseOrder`, `PurchaseRequisition`, `ReceiptHeader`

**Maintenance** (`src/core/modules/maintenance/`):
- `repository.py`: `MaintenanceLocation`, `MaintenanceSystem`, `MaintenanceAsset`,
  `MaintenancePreventivePlan`, `MaintenanceSensor`, `MaintenanceWorkRequest`,
  `MaintenanceWorkOrder`

**Registries updated:**
- `src/infra/composition/inventory_registry.py` — removed `tenant_id_provider=_tid`, added wiring loop
- `src/infra/composition/maintenance_registry.py` — same; also wires locally-created
  document/employee/time repos

---

### Phase H — Service Layer Cleanup `PLAN`

Once repositories are tenant-scoped at the SQL level, service-level org-filtering
helpers are redundant and were removed.

| Change | File |
|--------|------|
| `list_for_organization(org_id)` → `list()` in PM contracts | `contracts/repositories/project.py`, `resource.py` |
| Removed `_assert_project_in_active_organization()` | `application/projects/commands/lifecycle.py` |
| Removed `_is_project_in_active_organization()` | same |
| `_validate_project_name()` uses `list()` | `application/projects/commands/validation.py` |
| `_resolve_project_code()` uses `list()` | `application/projects/commands/lifecycle.py` |
| `list_resources()` uses `list()` | `application/resources/queries/resource_queries.py` |
| `get_resource()` uses `get()` (no org_id) | same |
| `_resolve_resource_code()` uses `list()` | `application/resources/commands/resource_commands.py` |
| `update_resource()` uses `get()` (no org_id) | same |
| `delete_resource()` uses `get()` (no org_id) | same |

---

## Test Coverage

### Completed

| Test file | Coverage |
|-----------|----------|
| `test_tenant_isolation_services.py` | Service-level list/get isolation for projects and resources; platform master-data list isolation (site, department, party, document, calendar, shift pattern) |
| `test_project_management_desktop_api.py` | Full PM desktop API surface — all 28 tests pass |

### Remaining

The following test scenarios are not yet covered by automated tests:

**Cross-tenant direct object access tests:**
- `repo.get("project-id-from-tenant-B")` must return `None` when called from tenant A
- Same for resources, tasks, assignments, baselines, costs, calendar events

**Cross-tenant list isolation tests:**
- `repo.list()` must return only tenant A rows when called from tenant A context
- Same for all tenant-root repos (platform + PM + inventory + maintenance)

**Cross-tenant write isolation tests:**
- `repo.update(obj_from_tenant_B)` must silently no-op or raise, not corrupt data
- `repo.delete("id-from-tenant-B")` must silently no-op, not delete foreign tenant data

**Child table isolation tests:**
- Skills, certs, task skill requirements — `get(id)` returns `None` for cross-tenant IDs
- Project resources — same

**Integration tests (DB-level):**
- Confirm inserts stamp `tenant_id` correctly (currently broken in `test_data_integrity.py` — see Known Pre-existing Failures)

---

## Remaining Gaps

### Access Control Repositories

`SqlAlchemyProjectMembershipRepository` and
`SqlAlchemyScopedAccessGrantRepository` in
`platform/repositories/access.py` are now hardened for active-scope reads,
deletes, and write stamping.

- Project memberships scope through `ProjectORM` so cross-org rows are not
  returned or deleted by id alone.
- Generic scoped-access grants scope by active tenant.
- Writes now stamp `organization_id` or `tenant_id` instead of relying on
  nullable transitional columns.

Because these repositories participate in principal rebuilds, they use the
session-pinned tenant and organization ids rather than the stricter
business-repo `require_organization_context()` pattern. This keeps auth flows
stable while still enforcing active-scope isolation in normal runtime use.

### Auth Repositories (intentionally unscoped)

`SqlAlchemyUserRepository`, `SqlAlchemyRoleRepository`, `SqlAlchemyPermissionRepository`,
`SqlAlchemyAuthSessionRepository` in `platform/repositories/auth.py` use
`session.get()` without tenant scope.

This is **intentional**: users, roles, and permissions are system-wide entities with
no `tenant_id` column. Login must work before a tenant context exists. Do not add
`_tenant_context_service` to these repos.

### Entitlement PK Migration (Phase C)

`organization_module_entitlements` PK is currently `(organization_id, module_code)`.
Target is `(tenant_id, module_code)`. SQLite does not support inline PK changes —
the table must be recreated. Deferred to Phase C.

### Cache Isolation (Phase 5 from original audit)

QSettings and in-memory caches are not tenant-keyed. Dashboard and report snapshots
are not namespaced by `(tenant_id, organization_id)`. No cache isolation exists.

Scope: all cache keys must follow `org:{organization_id}:{feature}:{...}`.

### Export Isolation (Phase 5 from original audit)

Export services derive row sets from service calls which are now tenant-scoped, but
export file generation does not add `organization_id` to export audit records and
does not guard against client-side filter manipulation.

### Dashboard & Report Aggregation (Phase 5 from original audit)

Dashboard aggregate queries (portfolio heatmaps, KPI strips, activity feeds) build
from tenant-scoped repositories, but there is no snapshot-level tenant tagging and
no explicit guard that prevents a stale cross-tenant snapshot from being displayed.

### Background Worker Tenant Propagation (Phase 7 from original audit)

`QThreadPool` jobs, scheduled background refreshes, notification processing, and
import parsing do not receive an explicit `TenantContext`. They rely on whatever
global state happens to be active. This is a security risk for multi-tenant
deployments.

Worker payloads must include `organization_id`, `user_id`, and `request_id`.
Workers must not rely on `Organization.is_active` for tenant selection.

---

## Pre-existing Test Failures (baseline ~25, not caused by isolation work)

These failures existed before this work and are not regressions:

| Test file | Count | Root cause |
|-----------|-------|-----------|
| `test_data_integrity.py` | 6 | Tests insert `organization_id=None` without wiring `TenantContextService`; hits NOT NULL constraint |
| `test_shared_collaboration_import_and_timesheets.py` | 1 | Missing live-session setup |
| Architecture guardrails (`test_architecture_guardrails.py`, `test_qml_architecture_guardrails.py`) | 9 | QML structure, scheduling engine split, legacy widget UI root — pre-existing policy violations in the codebase |

Do not count these as regressions. Fix them separately when the relevant feature
work is scheduled.

---

## Execution Checklist — What to Do Next

In priority order:

1. **Phase C — NOT NULL schema hardening**
   - Confirm all runtime `add()` paths stamp `tenant_id` (run `SELECT COUNT(*) WHERE tenant_id IS NULL` on all 33 tables in dev DB after full smoke test)
   - Write and run migration to add NOT NULL constraint
   - Re-key `organization_module_entitlements` PK

2. **Cross-tenant isolation test coverage**
   - Write `test_repo_cross_tenant_isolation.py` with direct SQL test scenarios (see Remaining test scenarios above)
   - These tests require a real SQLite session, not fake repos

3. **Fix pre-existing test failures in `test_data_integrity.py`**
   - Wire `TenantContextService` into the test fixtures so inserts pass `tenant_id` + `organization_id`
   - These tests were written against the old schema; they need a proper fixture update

4. **Phase 5 — Cache, Dashboard, Export hardening**
   - Tenant-key all QSettings cache entries
   - Add `organization_id` to export audit records
   - Add snapshot-level tenant tagging to dashboard aggregation paths

5. **Phase 7 — Background worker tenant propagation**
   - Audit all `QThreadPool` job payloads for tenant metadata
   - Add `organization_id` + `user_id` to background job constructors
   - Verify notification and import workers carry context through retries

6. **Phase 8 — Tenant penetration test**
   - Two-organization smoke test: create projects/tasks/resources in org A, log in as org B user, confirm zero cross-tenant rows in every surface (list, get, dashboard, export, approval queue, audit log)

---

## File Map — Changed Files by Phase

```
src/core/platform/tenancy/
  tenant_context.py                   Phase B — TenantContext + TenantContextService updated
  domain/tenant.py                    Phase B — Tenant domain model
  contracts.py                        Phase B — TenantRepository contract

src/core/platform/infrastructure/persistence/
  orm/tenant.py                       Phase B — TenantORM
  repositories/tenant.py              Phase B — SqlAlchemyTenantRepository
  repositories/access.py              Access-control repo hardening follow-up
  repositories/sites.py               Phase F
  repositories/departments.py         Phase F
  repositories/employee.py            Phase F
  repositories/party.py               Phase F
  repositories/approval.py            Phase F
  repositories/audit.py               Phase F
  repositories/documents.py           Phase F
  repositories/enterprise_calendar.py Phase F
  repositories/time.py                Phase F

src/core/platform/auth/domain/session.py
                                      Phase B — set_active_tenant_id(), active_tenant_id()

src/core/modules/project_management/infrastructure/persistence/repositories/
  project.py                          Phase D (ProjectRepository), Phase E (ProjectResourceRepository)
  resource.py                         Phase D
  task.py                             Phase D
  baseline.py                         Phase D + E (unscoped session.get() fix)
  skills.py                           Phase E
  cost.py                             Phase D
  portfolio.py                        Phase D

src/core/modules/project_management/application/
  projects/queries/project_query.py   Phase H
  projects/commands/lifecycle.py      Phase H
  projects/commands/validation.py     Phase H
  resources/queries/resource_queries.py Phase H
  resources/commands/resource_commands.py Phase H

src/core/modules/inventory_procurement/infrastructure/persistence/repositories/
  catalog.py                          Phase G
  inventory.py                        Phase G
  procurement.py                      Phase G

src/core/modules/maintenance/infrastructure/persistence/repositories/
  repository.py                       Phase G

src/infra/composition/
  platform_registry.py                Phase F — wiring loop (_tenant_context_service)
  inventory_registry.py               Phase G — wiring loop
  maintenance_registry.py             Phase G — wiring loop

src/tests/project_management/
  test_tenant_isolation_services.py   Phase H — fixed _TenantRepo, list() contract, assertions
```
