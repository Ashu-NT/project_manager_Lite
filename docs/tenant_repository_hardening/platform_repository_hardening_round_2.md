# Platform Repository Hardening Round 2

Date: 2026-06-12

## Scope

This tranche extends tenant and organization scoping deeper into the platform-owned persistence layer, with an emphasis on the repositories that still relied on optional context or unscoped row-id mutations.

## Completed

- Added shared repository support for required tenant plus organization context:
  - `src/core/platform/infrastructure/persistence/repositories/_tenant_scope.py`
- Hardened platform master-data and governance repositories to require active tenant context and active organization context for reads and writes:
  - `sites.py`
  - `departments.py`
  - `employee.py`
  - `party.py`
  - `documents.py`
  - `approval.py`
  - `audit.py`
  - `time.py`
- Hardened enterprise calendar repositories:
  - `PlatformCalendarRepository`
  - `CalendarWorkingRuleRepository`
  - `CalendarExceptionRepository`
  - `CalendarRecurringEventRepository`
  - `ShiftPatternRepository`
  - `CalendarAssignmentRepository`
- Updated the calendar integration test fixtures so tenant-aware repositories receive a concrete context in direct-repository test setups.
- Added focused repository hardening coverage:
  - `src/tests/platform/test_repository_tenant_hardening.py`
- Added explicit organization-mismatch guards for repository methods that accept an `organization_id` parameter, so they now return `None` or `[]` instead of silently serving active-organization data when the caller passes a different organization.

## Notes

- Calendar child-table access is now scoped through the parent calendar or shift-pattern context instead of relying on raw row ids.
- Calendar assignment scoping is enforced through the assigned calendar context. Entity existence validation was intentionally not made stricter in this pass so the repo remains compatible with the current assignment-service and integration-test behavior.
- Repository methods that take `organization_id` now fail closed on mismatches. This protects callers that pass an explicit organization filter from accidentally receiving active-organization results when the request context and method argument diverge.

## Verification Status

- Targeted syntax verification completed successfully for the changed repository and test files.
- Targeted pytest was run during implementation and surfaced follow-up fixture, seed-ordering, and assignment-count query issues, which were then addressed in code.
- Focused verification now passes for the repository hardening and related integration surfaces:
  - `src/tests/platform/test_repository_tenant_hardening.py`
  - `src/tests/platform/test_enterprise_calendar_foundation.py`
  - `src/tests/project_management/test_scheduling_enterprise_calendar_integration.py`
  - `src/tests/project_management/test_enterprise_calendar_pm_integration.py`
  - `src/tests/project_management/test_repository_tenant_hardening.py`
  - `src/tests/test_ui_settings_persistence.py`
- Current test output still includes existing datetime deprecation warnings in the enterprise calendar layer and pytest cache warnings on the local Windows workspace.
