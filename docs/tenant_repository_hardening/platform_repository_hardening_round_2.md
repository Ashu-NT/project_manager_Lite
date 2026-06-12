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

## Notes

- Calendar child-table access is now scoped through the parent calendar or shift-pattern context instead of relying on raw row ids.
- Calendar assignment scoping is enforced through the assigned calendar context. Entity existence validation was intentionally not made stricter in this pass so the repo remains compatible with the current assignment-service and integration-test behavior.

## Verification Status

- Targeted syntax verification completed successfully for the changed repository and test files.
- Targeted pytest was run during implementation and surfaced follow-up fixture and assignment-compatibility issues, which were then addressed in code.
- A final confirmation pytest rerun is still recommended when tool execution quota is available again.
