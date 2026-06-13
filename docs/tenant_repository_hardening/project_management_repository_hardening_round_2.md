# Project Management Repository Hardening Round 2

## Scope completed

This tranche hardens the remaining project-management secondary repositories and
portfolio repositories that still relied on raw ids, organization-only
transitional filters, or optional tenant context:

- `SqlAlchemyProjectResourceRepository`
- `SqlAlchemyPortfolioIntakeRepository`
- `SqlAlchemyPortfolioScenarioRepository`
- `SqlAlchemyPortfolioProjectDependencyRepository`
- `SqlAlchemyPortfolioScoringTemplateRepository`
- `SqlAlchemyResourceSkillRepository`
- `SqlAlchemyResourceCertificationRepository`
- `SqlAlchemyTaskSkillRequirementRepository`
- `SqlAlchemyProjectCalendarAssignmentRepository`
- `SqlAlchemyResourceCalendarAssignmentRepository`

## Enterprise hardening applied

- Added `ProjectManagementTenantScopedRepositorySupport` and
  `ProjectManagementParentScopedRepositorySupport` so PM repositories use the
  same scoped helper pattern already applied in platform, inventory,
  procurement, and maintenance.
- Project-resource, skill, certification, task-requirement, and PM calendar
  assignment repositories now require `TenantContextService` instead of
  allowing optional or effectively unscoped reads.
- Parent-scoped `add(...)` and `save(...)` paths now validate authoritative
  project, resource, and task ownership before writing child rows.
- `merge()`-based portfolio updates were replaced with scoped loads and
  explicit field updates so foreign ids cannot be mutated by accident.
- Portfolio intake writes now stamp or validate `organization_id` and
  `tenant_id` from the active context and use scoped optimistic updates.
- Portfolio dependency reads and deletes now scope both predecessor and
  successor projects through the active tenant and organization.
- PM calendar assignment integration tests now persist in-scope project and
  resource parents before assigning calendars, which matches the hardened
  repository contract.

## Coverage added

`src/tests/project_management/test_repository_tenant_hardening.py` now
verifies:

- remaining PM secondary repositories require `TenantContextService`
- foreign project-resource, skill, certification, requirement, calendar, and
  portfolio rows are hidden from `get(...)`
- foreign mutations no-op outside the active organization
- cross-organization writes are rejected for portfolio, project-resource, and
  parent-scoped PM child repositories

## Verification

- Focused PM repository and calendar integration verification:
  - `conda run -n pmenv python -m pytest -q src/tests/project_management/test_repository_tenant_hardening.py src/tests/project_management/test_enterprise_calendar_pm_integration.py src/tests/project_management/test_scheduling_enterprise_calendar_integration.py`
  - result: `33 passed`
- Broader PM regression verification:
  - `conda run -n pmenv python -m pytest -q src/tests/project_management/test_enterprise_pm_foundation.py src/tests/project_management/test_finance_layer_integration.py src/tests/project_management/test_currency_defaults.py src/tests/project_management/test_resource_capacity_profile.py`
  - result: `21 passed`

## Next step

- Continue with controller and settings follow-up for organization switching,
  cached state, and remaining transitional organization-aware UI behavior.
- After that, evaluate whether legacy compatibility methods like
  `get_for_organization(...)` can be simplified away once all callers use the
  scoped repository contract directly.
