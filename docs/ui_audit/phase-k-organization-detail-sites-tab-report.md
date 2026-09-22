# Phase K — Organization Detail Child Workspaces + Inspector — Sites Report

Sequence (per the closeout directive): Sites → Departments → Employees → Documents → Inspector → scoped-routing fix → combined regression/visual QA/docs. This report covers **Sites only** — the reference vertical slice. Nothing here touches Organization Overview, Organization lifecycle, or any other Organization Detail tab.

## 1. Investigation findings (before any code was written)

- **Site lifecycle is a plain boolean (`is_active`), not a 3-state enum.** A separate `status` free-text field exists on `Site` but is not an enum, has no `SITE_STATUS_*` constants, is reset to `""` whenever `is_active` toggles, and is used only as an arbitrary sub-label + search term. Do not conflate it with Organization's ACTIVE/INACTIVE/ARCHIVED. The Sites tab's Status column and filter are Active/Inactive (2-state), not 3-state.
- **Systemic backend gap, not specific to Sites**: `SiteService`/`DepartmentService`/`EmployeeService`/`DocumentService` all resolve their query scope from `TenantContextService`'s *session-active* organization, never from an explicit `organization_id` argument — even though the repository layer one level down (`list_for_organization(organization_id, ...)`) already accepts one. Practical effect: before this phase, opening Organization Detail for any organization other than the user's currently-active one silently showed **empty** Sites/Departments/Employees/Documents data (the existing client-side filter had nothing correct to filter, since the underlying global list itself never included the viewed organization's rows). This blocked "reference quality" for any organization other than the active one.
- **Precedent already exists** for the correct fix: `OrganizationService.get_organization_statistics(organization_id)` and `OrganizationRepository.get_for_tenant`/`SiteRepository.get_for_tenant` already do tenant-scoped (not active-org-scoped) reads for an arbitrary organization/record. The new Sites read method mirrors this exact, already-reviewed pattern.
- **`SiteDto` was silently dropping `created_at`/`updated_at`** even though both exist on the domain `Site` dataclass and the ORM. Fixed by exposing them — no new persistence field invented.
- No Department/Employee-per-Site count reader exists anywhere (only a tenant-wide, active-org-only rollup). Building one is real, bounded backend work, not covered by this slice — see §6.
- `AdminSiteDetailPage.qml` and the shared `AdminEntityWorkspace`/`InspectorPanel`/`TableToolbar`/`DataTable`/`TablePaginationBar` stack already exist and are exactly what the standalone Sites workspace uses — reused as-is, nothing new built.

## 2. Backend change (approved scope, exactly as specified)

New, **read-only**, additive methods — zero changes to any existing method's behavior or signature:

- `SiteRepository.list_page_for_organization_in_tenant(organization_id, tenant_id, *, page, page_size, search, active_only)` (contract + `SqlAlchemySiteRepository` implementation) — tenant + organization filtered directly from caller-supplied IDs, bypassing `TenantScopedRepositorySupport`'s active-organization gate entirely (same pattern as the pre-existing `get_for_tenant`). Paginated, searchable (name/code/city/country), `active_only` filterable.
- `SiteService.list_sites_page_for_organization(organization_id, *, page, page_size, search, active_only)`: requires `site.read`/`settings.manage` permission (`_require_site_read_access`, identical to `list_sites()`); resolves the caller's tenant; looks up the target organization via `OrganizationRepository.get_for_tenant(organization_id, tenant_id)` — raises `NotFoundError` if it doesn't belong to that tenant (this is what makes a cross-tenant ID "rejected/not visible", not a special-cased check); applies `filter_scope_rows` for site-level scope permissions, identical to `list_sites()`. Never checks the *organization's own* lifecycle status, so inactive/archived organizations' site history stays readable. `create_site`/`update_site`/`toggle_site_active` are completely untouched — mutations still resolve via `self._active_organization()`, the existing domain rule.
- `SiteDto`/`SitePageDto` (+ `PlatformSiteDesktopApi.list_sites_page_for_organization`): DTO layer exposing the above, plus the `created_at`/`updated_at` fix.

## 3. Tests proving the required scenarios (all passing)

`src/tests/platform/application/test_site_organization_scoped_read.py` (5/5):
1. `test_viewing_a_non_active_organization_returns_its_own_sites_correctly` — active session org is B, request A's sites, get exactly A's 2 sites.
2. `test_no_leakage_from_the_active_organization_into_the_viewed_organization` — B's own sites never include A's.
3. `test_cross_tenant_organization_id_is_rejected_not_visible` — a genuinely different tenant's organization/site (raw ORM rows, real FK-linked tenant) → `NotFoundError`.
4. `test_inactive_and_archived_organizations_still_have_readable_site_history` — deactivate then archive the organization; site history remains readable both times.
5. `test_mutation_paths_still_use_the_active_organization_not_the_viewed_one` — `create_site()` while active in B always lands in B, unaffected by any read call naming A.

`src/tests/ui_qml/platform/presenters/test_organization_detail_sites_tab.py` (2/2, real `QQmlApplicationEngine` load, no mocks):
- `test_sites_tab_loads_real_paginated_data_for_a_non_active_organization` — loads the real `AdminOrganizationDetailPage.qml` with a fully-wired controller, switches to the Sites tab, and confirms real paginated org-A data appears while the session's active org is B, zero console errors (`ReferenceError`/`TypeError`/unknown-icon-name/etc.), and that `_canCreateSite` is correctly `false` (see §5).
- `test_sites_tab_controller_slot_applies_status_filter_server_side` — the exact controller slot the Status ComboBox calls, exercised through the full Controller → Presenter → Desktop API → Service chain.

## 4. QML: the Sites tab itself

`AdminOrganizationDetailPage.qml`'s Sites section was replaced (the Departments/Employees/Documents sections are untouched, still the old client-side-filtered minimal table — their turn is next):

- `PlatformComponents.AdminEntityWorkspace` (the same TableToolbar + DataTable + TablePaginationBar + Columns-selector stack Organizations itself uses) — not a new table mechanism.
- Default columns: **Site, Code, Location ("city, country"), Status**. Optional (via the existing Columns selector, off by default): Country, Time Zone, Created, Updated.
- A `Status: All/Active/Inactive` `ComboBox` in the toolbar (via `AdminEntityWorkspace`'s `filterContent` slot, the same mechanism the Organizations list's own status filter uses), calling the new tenant-scoped method server-side — confirmed by test 4 above, not a client-side re-filter.
- Own local pagination/search/filter state (`_sitesPage`/`_sitesPageSize`/`_sitesSearch`/`_sitesStatusFilter`), independent of the (also-still-present, unchanged) global Sites workspace's own state.
- Row activation opens the real `AdminSiteDetailPage.qml` (the exact component the standalone Sites workspace uses) nested within the tab, with a working Back action.
- True-empty ("No sites yet. Add the first operational site for this organization.") vs. filtered-no-results ("No sites match your current filters.") states, via `AdminEntityWorkspace`'s existing mechanism — not new copy invented ad hoc.
- A `Connections` block re-fetches this tab's page whenever the global sites catalog changes (e.g. after using the "+ New Site" dialog), so the tab stays live without polling.

**Shared-component changes (both additive, zero behavior change for existing consumers, verified against all 24 `test_qml_status_chip_consumers_load.py` pages + the full architecture-guardrail-adjacent regression run in §7):**
- `DynamicTableModel.set_rows()` (in `data_table_model.py`) is now also a `@Slot`, so a QML page with no Python controller in between (like this tab) can push rows into it directly while still going through the sort-tracking-safe path. (In practice the tab binds `rows:` directly, since it doesn't yet wire column-header sorting — noted as a minor, accepted limitation, not a regression versus the prior simplistic table, which had no sorting either.)
- `AdminEntityWorkspace.filterContent` (from the Organization Detail Phase J work) is reused here as-is, not modified further.
- `PlatformSiteCatalogPresenter._serialize_site`'s `status_label` is now the explicit `{"label", "tone"}` dict shape (matching the Organization presenter's own Phase J pattern) instead of a plain string — this also gives the **pre-existing standalone Sites workspace** a real StatusChip tone it didn't have before. Two QML consumers of the old plain-string shape were fixed for this (`SitesWorkspacePage.qml`'s Inspector, `AdminSiteDetailPage.qml`'s header) — both re-verified via the regression run in §7.

## 5. Permissions and the create-action decision

"+ New Site" is enabled only when **both** `canWrite` (the existing `settings.manage` check) **and** the organization being viewed is the caller's actual session-active organization (`platformCatalog.organizationSwitcher.activeOrganizationId === this organization's id`). Reasoning: per the closeout directive, `create_site()` must keep using the active-organization domain rule unchanged — so creating from a *non-active* organization's Sites tab would silently create the record in the wrong organization. Rather than either weakening that mutation rule or building a new explicit-organization create path (out of this phase's approved scope), the create action is simply gated off when it would produce a wrong or confusing result. Viewing stays fully available regardless. This is a product-level judgment call, not a backend constraint — flagged here explicitly per "report before adding."

## 5a. Real-device visual QA fix (found by the user's own manual testing, not by the automated harness)

Direct testing surfaced a real layout defect the automated (offscreen, no live window) tests could not catch: the Sites section had a **fixed 640px height**, which on a tall viewport left dead space below the pagination footer (footer wasn't pinned to the actual bottom of the visible area) and on a short/narrow viewport pushed the footer out of view entirely. `AdminEntityWorkspace` is a full-panel component (fixed pagination footer, internal `DataTable` scrolling) — it needs to fill the page's *actual* available height, not an arbitrary constant. Fixed by binding the section's height to `SectionDetailPage.contentViewportHeight` (a property that already existed for exactly this purpose) instead of `640`, with a `420`px floor for very short windows. Re-verified against the full existing regression suite (see §7) after the fix; no live-window recheck was possible in this environment, so the user's re-confirmation on their machine is the closing verification step for this specific fix.

A second observation (horizontal scrolling not visibly appearing) was investigated in the `DataTable.qml` source: the column-width algorithm (`_colWidth`/`_columnBaseWidth`) correctly refuses to shrink columns below their declared `minWidth`, and the horizontal `ScrollBar` (`policy: ScrollBar.AsNeeded`) is wired to appear whenever total column width exceeds the viewport — the mechanism itself looks correct on inspection, and may simply be an auto-hide/fade scrollbar style that isn't visible in a static screenshot until hovered or dragged (standard Qt Quick Controls behavior). Since the height bug above could plausibly have been distorting the table's actual rendered width too, this needs a re-check on a real window after the height fix before treating it as a separate defect.

## 6. Known gaps / explicitly deferred (not silently dropped)

- **Departments/Employees count columns**: no batched, N+1-free per-site reader exists anywhere in the codebase today (`get_site_rollup_summary` is tenant-wide and active-org-only). Not built this slice; would need new aggregate-reader work, out of "Sites vertical slice" scope as directed.
- **Site Detail's own internal cross-links** (Manage Departments/Employees, Calendar assignment) are inert when `AdminSiteDetailPage.qml` is opened from inside Organization Detail — only its own "Edit"/"Set Active/Inactive"/"Refresh" toolbar actions are wired in this nested context. Re-routing those cross-links to this organization's own scoped tabs is exactly the "scoped-routing fix" step already scheduled later in the sequence, not specific to Sites.
- **Site Detail's own "Edit" action** is not yet wired when nested here (its `actionRequested("edit")` has no dialog host reachable from this depth without a larger signal-plumbing change); editing a site's full profile from the global Sites workspace remains available. Flagged as a fast-follow, not required by this slice's acceptance list.
- **Pixel-level visual QA** for the Sites tab specifically was attempted and removed — `grabToImage()` needs a `QQuickWindow`-backed root, which a standalone page load doesn't have; reaching it needs real shell navigation, planned for the combined visual QA pass once all four tabs exist. The tab is instead verified end-to-end (zero console errors, correct data, correct gating) by real `QQmlApplicationEngine` loads.

## 7. Regression

- `test_site_organization_scoped_read.py`: 5/5
- `test_organization_detail_sites_tab.py`: 2/2
- `test_site_platform_foundation.py`, `test_employee_department_site_filtered_listing.py`: unaffected, still passing
- `test_organization_detail_overview_qml.py`, `test_organization_bulk_actions.py`, `test_organization_lifecycle_ui_phase_j.py` (Phase J's own tests): still passing, confirming this Sites work didn't disturb Organization Overview/Actions/lifecycle
- `test_qml_status_chip_consumers_load.py`: 24/24 (proves the presenter/QML status-tone changes didn't regress any other entity's pages)
- `test_admin_workspace_eager_refresh_gating.py`, `test_admin_code_generation.py`: still passing
- Full `src/tests/platform` and `src/tests/ui_qml/platform` batches: run as part of this slice's closeout (see follow-up message for results)

## 8. Acceptance status for Sites specifically

Tenant-scoped explicit-org read ✅ · read-only ✅ · tenant-membership enforced ✅ · existing permission rules applied ✅ · not active-org-gated ✅ · mutation scoping unchanged ✅ · repository capability reused, no duplicate query path ✅ · server-side search/filter/pagination ✅ · inactive/archived organizations remain readable ✅ · not made operationally selectable ✅ · tests for all 5 required scenarios ✅ · real TableToolbar/DataTable/TablePaginationBar/Columns reuse ✅ · true-empty vs. no-results ✅ · create action ✅ (with the active-org gating in §5) · row activation to real Site Detail ✅ · permissions ✅.

Not yet done (by design, sequenced later): Departments/Employees/Documents tabs, Inspector redesign, scoped-routing fix for Related Actions/Key Statistics, combined visual QA, and documentation update — all pending per the agreed sequence.
