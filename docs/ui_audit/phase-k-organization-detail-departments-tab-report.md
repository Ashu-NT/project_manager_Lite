# Phase K — Organization Detail Child Workspaces + Inspector — Departments Report

Sequence: Sites → **Departments** → Employees → Documents → Inspector → scoped-routing fix → combined regression/visual QA/docs. This report covers **Departments only**, built as the second vertical slice using Sites as the reference pattern (per the closeout directive: "After Sites, inspect what is genuinely duplicated and extract only reusable, domain-neutral infrastructure"). Nothing here touches Organization Overview, Organization lifecycle, or any other Organization Detail tab's data.

## 1. Investigation findings (before any code was written)

- **Department's backend was structurally identical to Site's pre-fix state**: `DepartmentService`/`DepartmentRepository` resolved every read from `TenantContextService`'s session-active organization only (`active_organization(service)` / `TenantScopedRepositorySupport`), with no explicit-`organization_id` read path, no pagination, and no server-side search — the exact same gap already fixed for Sites.
- **Department lifecycle is also a plain boolean (`is_active`)** — a 2-state Active/Inactive model, not Organization's 3-state ACTIVE/INACTIVE/ARCHIVED. Same tone map shape as Sites, kept as its own separate `_DEPARTMENT_STATUS_TONE` dict (not shared/conflated with Site's).
- `DepartmentRepository.list_for_organization(organization_id, *, active_only=None)` already existed at the repository level, exactly as it did for Sites before the fix — reused as the basis for the new tenant-scoped, paginated method rather than writing a new query from scratch.
- **`DepartmentDto` was silently dropping `created_at`/`updated_at`** even though both exist on the domain `Department` dataclass and the ORM (`departments.py` ORM has non-nullable `created_at`/`updated_at` columns) — fixed by exposing them, same as `SiteDto`.
- **Domain relationships confirmed by reading the ORM directly, not assumed**: `DepartmentORM.site_id` is a nullable FK to `sites.id` (a department belongs to **at most one** site, not many) and `DepartmentORM.parent_department_id` is a nullable, self-referencing FK to `departments.id` (a department has at most one parent — a tree, not a DAG). Both are already exactly how the existing (session-active-org-only) Departments workspace and `DepartmentEditorDialog` model them — no relationship was reshaped for UI convenience.
- **`manager_employee_id` name resolution is a real, explicitly deferred gap** (see §6) — resolving it would require Employee lookup infrastructure equivalent to the Site/Department lookups built for this slice, which is a distinct entity type not yet given the same tenant-scoped-lookup treatment. Reported here rather than silently left as a raw ID or invented as a new field.

## 2. Backend change (approved scope, exactly as specified)

New, **read-only**, additive methods — zero changes to any existing method's behavior or signature:

- `DepartmentRepository.list_page_for_organization_in_tenant(organization_id, tenant_id, *, page, page_size, search, active_only)` (contract + `SqlAlchemyDepartmentRepository` implementation) — tenant + organization filtered directly from caller-supplied IDs, bypassing `TenantScopedRepositorySupport`'s active-organization gate entirely (same pattern as `SqlAlchemySiteRepository`'s equivalent method). Paginated, searchable (name/code/department type/cost center), `active_only` filterable.
- `DepartmentService.list_departments_page_for_organization(organization_id, *, page, page_size, search, active_only)`: requires `department.read`/`settings.manage` permission (`require_department_read_access`, identical to `list_departments()`); resolves the caller's tenant; looks up the target organization via `OrganizationRepository.get_for_tenant(organization_id, tenant_id)` — raises `NotFoundError` if it doesn't belong to that tenant; applies `filter_scope_rows` (`scope_type="department"`, `permission_code="department.read"`) for department-level scope permissions. Never checks the *organization's own* lifecycle status, so inactive/archived organizations' department history stays readable. `create_department`/`update_department`/`toggle_department_active` are completely untouched — mutations still resolve via `active_organization(self)`, the existing domain rule.
- `DepartmentDto`/`DepartmentPageDto` (+ `PlatformDepartmentDesktopApi.list_departments_page_for_organization`): DTO layer exposing the above, plus the `created_at`/`updated_at` fix.
- `DepartmentPage` dataclass (`items`/`total`/`filtered_total`/`page`/`page_size`) mirrors `SitePage` exactly.

## 3. Tests proving the required scenarios (all passing)

`src/tests/platform/application/test_department_organization_scoped_read.py` (5/5):
1. `test_viewing_a_non_active_organization_returns_its_own_departments_correctly` — active session org is B, request A's departments, get exactly A's 2 departments.
2. `test_no_leakage_from_the_active_organization_into_the_viewed_organization` — B's own departments never include A's.
3. `test_cross_tenant_organization_id_is_rejected_not_visible` — a genuinely different tenant's organization/department (raw ORM rows, real FK-linked tenant, tenant/organization each committed in their own transaction to satisfy SQLite FK-insertion ordering) → `NotFoundError`.
4. `test_inactive_and_archived_organizations_still_have_readable_department_history` — deactivate then archive the organization; department history remains readable both times.
5. `test_mutation_paths_still_use_the_active_organization_not_the_viewed_one` — `create_department()` while active in B always lands in B, unaffected by any read call naming A.

`src/tests/ui_qml/platform/presenters/test_organization_detail_departments_tab.py` (2/2, real `QQmlApplicationEngine` load, no mocks):
- `test_departments_tab_loads_real_paginated_data_for_a_non_active_organization` — loads the real `AdminOrganizationDetailPage.qml` with a fully-wired controller, switches to the Departments tab, and confirms real paginated org-A data appears while the session's active org is B, zero console errors, and that `_canCreateDepartment` is correctly `false`.
- `test_departments_tab_controller_slot_applies_status_filter_server_side` — the exact controller slot the Status ComboBox calls, exercised through the full Controller → Presenter → Desktop API → Service chain.

## 4. QML: the Departments tab itself

`AdminOrganizationDetailPage.qml`'s Departments section was replaced (Employees/Documents remain the old client-side-filtered minimal table — their turn is next):

- `PlatformComponents.AdminEntityWorkspace` (same stack Sites/Organizations use) — no new table mechanism.
- Default columns: **Department, Code, Site, Status**. Optional (via the existing Columns selector, off by default): Type, Parent Department, Cost Center, Created, Updated.
- `siteName` and `parentDepartmentName` are resolved via cheap in-memory joins in the presenter (`_site_lookup_for_organization`/`_department_lookup_for_organization`), each paginating through up to 2,000 records (20 pages × 100) of the *same organization's* tenant-scoped Site/Department pages — not the old active-org-only `_site_lookup()` (which would have silently resolved the wrong organization's site names when viewing a non-active organization). `manager_employee_id` is **not** resolved to a name — see §6.
- A `Status: All/Active/Inactive` `ComboBox` in the toolbar, calling the new tenant-scoped method server-side.
- Own local pagination/search/filter state (`_departmentsPage`/`_departmentsPageSize`/`_departmentsSearch`/`_departmentsStatusFilter`), independent of the global Departments workspace's own state.
- Row activation opens the real `AdminDepartmentDetailPage.qml` (the exact component the standalone Departments workspace uses) nested within the tab, with a working Back action.
- True-empty ("No departments yet. Add the first department for this organization.") vs. filtered-no-results ("No departments match your current filters.") states, via `AdminEntityWorkspace`'s existing mechanism.
- The existing `Connections` block (already wired for Sites) now also re-fetches this tab's page whenever the global departments catalog changes (`onDepartmentsChanged`).

**Shared-component changes:**
- `PlatformDepartmentCatalogPresenter._serialize_department`'s `status_label` is now the explicit `{"label", "tone"}` dict shape (matching Site's Phase K pattern) instead of a plain string — this also gives the **pre-existing standalone Departments workspace** a real StatusChip tone it didn't have before. Two QML consumers of the old plain-string shape were fixed for this (`DepartmentsWorkspacePage.qml`'s Inspector, `AdminDepartmentDetailPage.qml`'s header) — both re-verified via the regression run in §7.

## 5. Permissions and the create-action decision

Identical reasoning to Sites (§5 of the Sites report): "+ New Department" is enabled only when **both** `canWrite` **and** the organization being viewed is the caller's actual session-active organization (`_canCreateDepartment = canWrite && _isViewingActiveOrganization`, reusing the same `_isViewingActiveOrganization` computed property Sites already defined). `create_department()` keeps using the active-organization domain rule unchanged; creating from a non-active organization's tab is gated off rather than silently landing in the wrong organization or requiring a new create path out of this phase's scope. Viewing stays fully available regardless.

## 5a. Mid-slice structural refactor: per-section QML files

`AdminOrganizationDetailPage.qml` crossed ~1160 lines with Sites and Departments both inline (Employees/Documents still to come). Per the user's explicit direction, extracted every section's markup into `workspaces/organizations/sections/` **before** starting Employees, while only two tabs had real logic — the smallest, lowest-risk point to do it:

- `OrganizationOverviewSection.qml`, `OrganizationSitesSection.qml`, `OrganizationDepartmentsSection.qml`, `OrganizationSimpleListSection.qml` (shared Employees/Documents placeholder, to be deleted once each gets its own real tab), `OrganizationActivitySection.qml`.
- Each section is now a presentational component with explicit `property`/`signal` surfaces — no implicit access to the orchestrator's `detailRoot` scope (mirrors how `AdminSiteDetailPage.qml`/`AdminDepartmentDetailPage.qml` already work as separate files). `AdminOrganizationDetailPage.qml` now owns only identity/lifecycle, per-tab state, and data fetching; it dropped from ~1250 lines to ~600.
- One real bug caught by this refactor before it shipped: a custom `signal statusFilterChanged(string value)` silently collided with the QML-auto-generated property-change signal for `property string statusFilter` (`Type ... unavailable` / `Duplicate signal name` at QML-load time, not qmllint noise) — renamed to `statusFilterRequested` in both the Sites and Departments sections. Caught by the real `QQmlApplicationEngine` load tests, not by inspection.
- Verified via the same real-engine load tests in §3 plus the broader regression in §7 — the refactor produced no behavior change, only a structural one.

## 6. Known gaps / explicitly deferred (not silently dropped)

- **`manager_employee_id` → manager name** is not resolved. Unlike `siteName`/`parentDepartmentName` (same entity type as the tab itself, so the tenant-scoped page endpoint already built for this slice could be reused directly), Employee is a different entity whose own tenant-scoped read doesn't exist yet — that's exactly the next vertical slice. Showing a raw ID would be worse than omitting it, so the column is left off entirely rather than either inventing a partial lookup or blocking this slice on Employees being done first.
- **Departments/Employees count columns**: no batched, N+1-free per-department reader exists (same gap already noted for Sites).
- **Department Detail's own internal cross-links** (Employees/Calendar/Documents/Audit tabs) are inert when `AdminDepartmentDetailPage.qml` is opened from inside Organization Detail — only its own "Edit"/"Set Active/Inactive"/"Refresh" toolbar actions are wired in this nested context, identical to the Sites slice's limitation. Re-routing is the already-scheduled scoped-routing fix step.
- **`deptCalendarAssignment`/`calendarSourceChain`** are not passed into the nested `AdminDepartmentDetailPage` from this tab (default to empty), so its Calendar tab shows "no assignment" regardless of the department's real calendar. Same category of nested-nested-nested nested-nested cross-link limitation as above, not specific to this slice.
- **Pixel-level visual QA** for the Departments tab specifically was not attempted for the same reason documented in the Sites report §6 (`grabToImage()` needs a `QQuickWindow`-backed root) — deferred to the combined visual QA pass.

## 7. Regression

- `test_department_organization_scoped_read.py`: 5/5
- `test_organization_detail_departments_tab.py`: 2/2
- `test_department_platform_foundation.py`, `test_shared_master_reuse_access.py`: unaffected, still passing
- `test_organization_detail_sites_tab.py`, `test_visual_qa_organizations.py`, `test_detail_view_tracker.py`: still passing after the section-file refactor (8/8 combined)
- `test_organization_detail_overview_qml.py`, `test_organization_bulk_actions.py`, `test_organization_lifecycle_ui_phase_j.py`, `test_organization_pagination_controller.py`, `test_organization_activity_presentation.py`, `test_organization_legal_address_contact_presenter.py`, `test_organization_view_invalidation_qt_cutover.py`: 38/38, confirming the section-file refactor didn't disturb Organization Overview/Actions/lifecycle
- Full `src/tests/platform/application` + `src/tests/platform/api` and full `src/tests/ui_qml/platform` batches: run as part of this slice's closeout (results reported in the follow-up message once the background runs complete)
- One pre-existing, unrelated failure reconfirmed: `test_qmllint_no_longer_reports_qobject_controller_member_warnings` fails on `PlatformWorkspacePage.qml` (a file untouched this session, and by every session touching Organization Detail) — not caused by this slice.

## 8. Acceptance status for Departments specifically

Tenant-scoped explicit-org read ✅ · read-only ✅ · tenant-membership enforced ✅ · existing permission rules applied ✅ · not active-org-gated ✅ · mutation scoping unchanged ✅ · repository capability reused, no duplicate query path ✅ · server-side search/filter/pagination ✅ · inactive/archived organizations remain readable ✅ · not made operationally selectable ✅ · tests for all 5 required scenarios ✅ · real TableToolbar/DataTable/TablePaginationBar/Columns reuse ✅ · true-empty vs. no-results ✅ · create action ✅ (with the active-org gating in §5) · row activation to real Department Detail ✅ · permissions ✅ · real Site/hierarchy semantics preserved (single site, single parent, not flattened) ✅.

Not yet done (by design, sequenced later): Employees/Documents tabs, Inspector redesign, scoped-routing fix for Related Actions/Key Statistics, combined visual QA, and documentation update.
