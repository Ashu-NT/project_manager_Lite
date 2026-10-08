# ADR-006: Shared identity and feature registration

Status: Accepted for Employee/PM Resource and Project client Party references (2026-10-08).

## Decision

- Platform owns Employee, Party, User-to-Employee linking, their core profiles, lifecycle, and their tenant/organization scope. It does not own or write PM Resource/Project/Finance rows.
- PM owns Resource registration and lifecycle. A person Resource may reference one active Employee by `employee_id`; the scoped unique index prevents duplicate registration. The Employee is not copied into a second Employee record. PM-owned role, capacity, rate, cost type, assignments, and project work stay on PM entities.
- PM may read Employee/Party through a scoped Platform repository/query contract. A PM command validates that a newly linked Employee or Party is active and in the correct organization. PM cannot edit the Platform profile. A deactivated Party remains a valid historical reference but cannot be newly selected.
- Project `department_id` is an optional Platform Department reference, not a PM Department copy. Absence is valid. A newly selected Department must be active and in the Project organization; deactivation does not invalidate an existing historical Project reference or block unrelated Project edits.
- User-to-Employee is a distinct Platform identity link, maintained through `link_employee_user_account` and `unlink_employee_user_account`; PM Timesheets resolve User -> Employee -> Resource without owning either User or Employee.
- PM read models prefer current Platform Employee identity for linked-resource display and current Party identity for client display. A registration-time Resource label is a fallback, not Employee profile authority. Read-side joining must be bounded and scoped, not a query per row.
- Platform domain/application/master-data composition must not import PM. PM may subscribe to Platform post-commit Employee events for its own view invalidation, but Platform must not synthesize PM Resource events or update PM Resource rows.
- The same pattern applies to future modules: the module owns its extension/registration entity and references shared Employee/Party IDs; Platform never embeds feature-specific fields or writes feature tables. A future independent service would replace local joins with a versioned read contract/event projection, without changing ownership.

## Removed reverse dependency

`_LinkedEmployeeResourceRepositoryAdapter`, the Platform linked-resource repository/event contracts, Employee UoW Resource repository, and EmployeeService's Resource synchronization were removed. Employee profile writes now commit Employee/audit/activity/event only. PM Resource registration still validates an Employee and stores its FK. PM's post-commit subscriber refreshes linked Resource views without changing the Resource version or PM financial/operational facts.

## Party boundary

PM Project uses `client_party_id` as a reference and its catalog resolves the current Party name. New Project client selections are checked against active scoped Platform Parties. PM commitments already validate active suppliers via the Platform Party repository. Party service has no PM write adapter. PM commercial billing/rate Party references need a separate command-validation review; this ADR does not claim they are all validated by the Project command check.

## Remaining migration risks

- Some older PM readers and unbounded option builders still use registration-time `Resource.name`; catalog, Resource summary/inspector, Project Resource detail, Task Assignment detail, Timesheet selector/review, Portfolio resource pool, Finance resource lookup, and User-to-Resource identity resolution have been moved to current Employee names. Financial historical-label projections and dashboard/options consumers need a semantic review before changing them: an immutable historical label must not be silently turned into mutable current identity. Further current-identity consumers should use the same scoped identity expression/read contract rather than adding profile synchronization.
- Resource master storage still has `name`, `contact`, `department_id`, and `site_id` because external resources and older PM command/read contracts use them. For Employee-backed resources these are registration-time fallbacks, not Platform truth. Removing/normalizing those columns requires a separate schema/consumer migration and must not be confused with deleting the Employee-to-Resource FK.
- Platform Approval persistence has a separately documented PM ORM dependency (R7C/Action Center work); it is not an Employee/Party master-data dependency and is not changed by this ADR.
- Cross-service deployment would require a PM-owned read projection rather than SQL joins. The current modular monolith keeps local, tenant/org-scoped joins in infrastructure only.

## Verification

`test_foundation_reference_boundaries.py` guards Platform master-data/composition import direction, Employee/External registration, Project Party selection, and optional scoped Project Department selection. `test_employee_platform_foundation.py` proves Employee edits leave PM Resource version untouched while scoped PM catalog/summary reads show current identity. Existing User-to-Employee and Timesheet identity tests continue to cover the preserved identity link.
