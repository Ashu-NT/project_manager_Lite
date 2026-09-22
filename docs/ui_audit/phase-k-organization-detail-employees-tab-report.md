# Phase K — Organization Detail Child Workspaces + Inspector — Employees Report

Sequence: Sites → Departments → **Employees** → Documents → Inspector → scoped-routing fix → combined regression/visual QA/docs. This report covers **Employees only**, the third vertical slice, built directly against the section-file structure introduced during the Departments slice (`workspaces/organizations/sections/`). Nothing here touches Organization Overview, Organization lifecycle, or any other Organization Detail tab's data.

## 1. Investigation findings (before any code was written)

- **Employee's backend had the identical systemic gap** already fixed for Sites/Departments: `EmployeeService`/`EmployeeRepository` resolved every read from the session-active organization only, with no explicit-`organization_id` read path, no pagination, no server-side search.
- **Employee belongs directly to Organization** — confirmed by reading `EmployeeORM`: `organization_id` is a nullable FK straight to `organizations.id`. `department_id`/`site_id` are separate, independently-nullable FKs (`departments.id`/`sites.id`) stored **directly on Employee**, not resolved transitively through one another — an employee can have a department, a site, both, or neither, and neither relationship implies the other. This matches the spec's explicit instruction to investigate "whether Employee belongs directly to Organization, through Department, or through Site" rather than assume.
- **Employee already denormalizes `department` (name) and `site_name` onto itself** at write time (`resolve_employee_department_reference`/`resolve_employee_site_reference` in `employee_support.py`, called from `create_employee`/`update_employee`). This is a materially different shape from Department (which had to resolve `site_id`/`parent_department_id` to names via fresh lookups) — no extra in-memory joins were needed for the Employees tab's Department/Site columns.
- **Employee genuinely has no `created_at`/`updated_at` at all** — verified directly on `EmployeeORM`, not merely dropped at the DTO layer like Site/Department were. This is a real, pre-existing enterprise-data gap, not something to silently add: per "report before adding... do not invent persistence fields," no Created/Updated columns are offered on this tab, and no such columns were fabricated.
- **`employee_code` is globally unique across the whole tenant** (`UniqueConstraint`-equivalent `unique=True` directly on the column), not scoped per-organization like Site's/Department's `UniqueConstraint(organization_id, code)`. Noted as a real domain difference, not touched by this read-only slice.
- **Employee has no scope-permission row filtering** (`filter_scope_rows`) anywhere in `EmployeeService` — unlike Site/Department. The existing `list_employees()` uses a single, plain `require_permission(user_session, "employee.read", ...)` with no `settings.manage` fallback and no per-row scope check. The new tenant-scoped method mirrors this exactly rather than inventing scope-row filtering Employee doesn't otherwise have.

## 2. Backend change (approved scope, exactly as specified)

New, **read-only**, additive methods — zero changes to any existing method's behavior or signature:

- `EmployeeRepository.list_page_for_organization_in_tenant(organization_id, tenant_id, *, page, page_size, search, active_only, department_id, site_id)` (contract + `SqlAlchemyEmployeeRepository` implementation) — tenant + organization filtered directly from caller-supplied IDs, bypassing `TenantScopedRepositorySupport`'s active-organization gate. Paginated, searchable (full name/employee code/title/email), `active_only`/`department_id`/`site_id` filterable (the latter two carried through from `list_for_organization`'s existing signature, unused by the tab's UI today but preserved for API completeness).
- `EmployeeService.list_employees_page_for_organization(organization_id, *, page, page_size, search, active_only, department_id, site_id)`: requires `employee.read` (plain `require_permission`, matching `list_employees()` exactly — no scope-row filtering, since Employee has none); resolves the caller's tenant; looks up the target organization via `OrganizationRepository.get_for_tenant(organization_id, tenant_id)` — raises `NotFoundError` if it doesn't belong to that tenant. Never checks the organization's own lifecycle status. `create_employee`/`update_employee` are completely untouched — mutations still resolve via `self._active_organization_id()`, the existing domain rule.
- `EmployeeDto`/`EmployeePageDto` (+ `PlatformEmployeeDesktopApi.list_employees_page_for_organization`): DTO layer exposing the above. `EmployeeDto` was **not** changed to add `created_at`/`updated_at` — see §1, there is nothing to expose.
- `EmployeePage` dataclass mirrors `SitePage`/`DepartmentPage`.

## 3. Tests proving the required scenarios (all passing)

`src/tests/platform/application/test_employee_organization_scoped_read.py` (5/5):
1. `test_viewing_a_non_active_organization_returns_its_own_employees_correctly`
2. `test_no_leakage_from_the_active_organization_into_the_viewed_organization`
3. `test_cross_tenant_organization_id_is_rejected_not_visible` (raw ORM rows, tenant/organization each committed separately for SQLite FK-insertion ordering)
4. `test_inactive_and_archived_organizations_still_have_readable_employee_history`
5. `test_mutation_paths_still_use_the_active_organization_not_the_viewed_one`

`src/tests/ui_qml/platform/presenters/test_organization_detail_employees_tab.py` (2/2, real `QQmlApplicationEngine` load, no mocks):
- `test_employees_tab_loads_real_paginated_data_for_a_non_active_organization`
- `test_employees_tab_controller_slot_applies_status_filter_server_side`

Both files passed on first run with no fix-up iterations required, unlike the FK-ordering issue hit in the Sites slice — the pattern from that slice's fix (commit the foreign tenant/organization rows before the child entity) was applied directly this time.

## 4. QML: the Employees tab itself

`AdminOrganizationDetailPage.qml`'s Employees section (already a standalone `OrganizationEmployeesSection.qml` file per the Departments-slice refactor) was replaced with a real tab:

- `PlatformComponents.AdminEntityWorkspace` (same stack Sites/Departments/Organizations use).
- Default columns: **Employee, Code, Department, Site, Status**. Optional (off by default): Employment Type, Email. **No Title column** — `state.title` (job title) collides with the item's own top-level `title` field (full name) in `serialize_action_item`'s state-flattening rule (a key already present at the top level is never flattened from `state`), so a "Title" column bound to `key: "title"` would silently show the employee's full name twice instead of their job title. Renaming the presenter's `title` state key would touch the edit dialog and other existing consumers, which is out of this read-only slice's scope — so the column is simply omitted rather than shipping a column that shows the wrong data. Flagged here as a real, if minor, naming gap for a future pass.
- A `Status: All/Active/Inactive` `ComboBox`, calling the new tenant-scoped method server-side.
- Own local pagination/search/filter state (`_employeesPage`/`_employeesPageSize`/`_employeesSearch`/`_employeesStatusFilter`), independent of the global Employees workspace's own state.
- Row activation opens the real `AdminEmployeeDetailPage.qml` nested within the tab, with a working Back action.
- True-empty ("No employees yet...") vs. filtered-no-results ("No employees match your current filters.") states.
- The existing `Connections` block (already handling Sites/Departments) now also re-fetches this tab's page on `onEmployeesChanged`.

**Shared-component changes:**
- `PlatformEmployeeCatalogPresenter._serialize_employee`'s `status_label` is now the explicit `{"label", "tone"}` dict shape, matching Site/Department's Phase K pattern — giving the pre-existing standalone Employees workspace a real StatusChip tone it didn't have before. Two QML consumers of the old plain-string shape were fixed (`EmployeesWorkspacePage.qml`'s Inspector, `AdminEmployeeDetailPage.qml`'s header).
- A pre-existing test (`test_qml_platform_presenters_catalog_admin.py`) hard-asserted the old plain-string `"Active"` shape for a **Department** row (from the Departments-slice change) — fixed to expect the dict shape; re-verified green. No equivalent hardcoded Employee-status assertion existed elsewhere.

## 5. Permissions and the create-action decision

Identical reasoning to Sites/Departments: "+ New Employee" is enabled only when **both** `canWrite` **and** the organization being viewed is the caller's actual session-active organization (`_canCreateEmployee = canWrite && _isViewingActiveOrganization`, reusing the existing computed property). `create_employee()` keeps using the active-organization domain rule unchanged. Viewing stays fully available regardless.

## 6. Known gaps / explicitly deferred (not silently dropped)

- **No `created_at`/`updated_at`** on Employee at all (domain/ORM level, not just DTO) — a genuine enterprise-data gap, reported rather than invented. Adding these columns would be real backend/migration work, out of this read-only slice.
- **Job title is not shown as a table column** — see §4's `state.title`/top-level-`title` key collision. Job title remains visible on the row's `subtitle` (`"{employee_code} | {title}"`, unchanged from the existing presenter) and in the nested `AdminEmployeeDetailPage`'s own Overview fields.
- **Employee Detail's own internal cross-links** (User Account/Assignments/Timesheets/Certifications/Calendar/Documents/Audit tabs) are inert when opened from inside Organization Detail — only "Edit"/"Set Active/Inactive"/"Refresh" are wired in this nested context, identical to the Sites/Departments slices' limitation. Re-routing is the already-scheduled scoped-routing fix.
- **`empCalendarAssignment`/`calendarSourceChain`** are not passed into the nested `AdminEmployeeDetailPage` from this tab (default empty), so its Calendar tab shows no assignment regardless of the employee's real calendar — same category of limitation as Departments' nested Calendar tab.
- **Department/Site filter dropdowns** were not added to this tab (only Status), matching the same scope discipline already applied to the Sites/Departments tabs (which also offer only a Status filter, not a Site/Department cross-filter) rather than introducing an inconsistent richer filter set for one tab only.
- **Pixel-level visual QA** deferred to the combined visual QA pass, same reason as Sites/Departments (`grabToImage()` needs a `QQuickWindow`-backed root).

## 7. Regression

- `test_employee_organization_scoped_read.py`: 5/5
- `test_organization_detail_employees_tab.py`: 2/2
- `test_employee_platform_foundation.py`, `test_employee_department_site_filtered_listing.py`, `test_shared_master_reuse_access.py`: unaffected, still passing
- `test_organization_detail_sites_tab.py`, `test_organization_detail_departments_tab.py`, `test_visual_qa_organizations.py`, `test_detail_view_tracker.py`, `test_qml_platform_presenters_catalog_admin.py` (after its dict-shape fix): 15/15 combined, confirming Employees didn't disturb Sites/Departments/section-file refactor
- `test_qml_status_chip_consumers_load.py`: still passing with Employee's new dict-shape status label included
- Full `src/tests/platform/application` + `src/tests/platform/api` and full `src/tests/ui_qml/platform` batches: run as part of this slice's closeout (results reported in the follow-up message)
- Same pre-existing, unrelated failure as before: `test_qmllint_no_longer_reports_qobject_controller_member_warnings` (untouched `PlatformWorkspacePage.qml`).

## 8. Acceptance status for Employees specifically

Tenant-scoped explicit-org read ✅ · read-only ✅ · tenant-membership enforced ✅ · existing permission rules applied ✅ (Employee's own plain-`employee.read` model, not Site/Department's `settings.manage`-or-read pattern — preserved as-is, not homogenized) · not active-org-gated ✅ · mutation scoping unchanged ✅ · repository capability reused, no duplicate query path ✅ · server-side search/filter/pagination ✅ · inactive/archived organizations remain readable ✅ · not made operationally selectable ✅ · tests for all 5 required scenarios ✅ · real TableToolbar/DataTable/TablePaginationBar/Columns reuse ✅ · true-empty vs. no-results ✅ · create action ✅ (with the active-org gating in §5) · row activation to real Employee Detail ✅ · real Organization/Site/Department assignment model preserved (direct FKs, not flattened or forced into a transitive relationship) ✅.

Not yet done (by design, sequenced later): Documents tab, Inspector redesign, scoped-routing fix for Related Actions/Key Statistics, combined visual QA, and documentation update.
