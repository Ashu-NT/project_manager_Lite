# Access Control Repository Hardening

Date: 2026-06-12

## Scope

This tranche hardens the access-control persistence layer that sits between
authentication, scoped authorization, and project-level collaboration features.
These repositories are a special case: they must remain usable during principal
rebuilds, so they cannot blindly call the same strict
`require_organization_context()` flow used by tenant-root business repositories.

## Completed

- Hardened `src/core/platform/infrastructure/persistence/repositories/access.py`
  so that:
  - project membership reads and deletes scope through `ProjectORM`
  - generic scoped-access grant reads and deletes scope by active tenant
  - project membership writes stamp `organization_id` from the owning project
  - generic scoped-access grant writes stamp `tenant_id` from the active tenant
  - project-scoped grant writes reject foreign or missing projects instead of
    trusting caller-supplied ids
- Added focused cross-org and cross-tenant repository coverage:
  - `src/tests/platform/test_access_repository_tenant_hardening.py`
- Tightened session-org retention in
  `src/core/platform/tenancy/tenant_context.py` so a non-admin user may keep
  working inside the org already pinned in the session, without gaining the
  ability to switch to a different org arbitrarily.
- Added small fail-closed compatibility bridges for legacy PM callers that still
  expect transitional org-filtered repository methods:
  - `src/core/modules/project_management/infrastructure/persistence/repositories/project.py`
  - `src/core/modules/project_management/infrastructure/persistence/repositories/resource.py`

## Notes

- Access repositories intentionally use raw session-pinned tenant and
  organization ids where needed during principal rebuilds. This avoids recursive
  principal validation while still applying the active scope in normal app
  execution.
- The project and resource compatibility bridges do not reopen wide reads. They
  return `[]` on organization mismatch and delegate to the already hardened
  `list()` path for the active org.

## Verification Status

- Focused access-control verification passes:
  - `src/tests/platform/test_access_repository_tenant_hardening.py`
  - `src/tests/platform/test_platform_access_scopes.py`
- Broader access and PM integration verification also passes:
  - `src/tests/platform/test_platform_control_desktop_api.py`
  - `src/tests/platform/test_enterprise_rbac_matrix.py`
  - `src/tests/project_management/test_enterprise_pm_foundation.py`
- Current output still includes existing enterprise-calendar `datetime.utcnow()`
  deprecation warnings and local Windows `.pytest_cache` warnings.
