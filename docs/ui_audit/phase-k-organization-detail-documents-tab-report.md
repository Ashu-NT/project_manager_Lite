# Phase K — Organization Detail Child Workspaces + Inspector — Documents Report

Sequence: Sites → Departments → Employees → **Documents** → Inspector → scoped-routing fix → combined regression/visual QA/docs. This report covers **Documents only**, the fourth and final entity vertical slice. Nothing here touches Organization Overview, Organization lifecycle, or any other Organization Detail tab's data.

## 1. Investigation findings (before any code was written)

- **Document's backend had the identical systemic gap** already fixed for Sites/Departments/Employees: `DocumentService`/`DocumentRepository` resolved every read from the session-active organization only, with no explicit-`organization_id` read path, no pagination, no server-side search. Document's permission model is a plain `require_permission(user_session, "settings.manage", ...)` (matching `list_documents()`/`get_document_rollup_summary()`/`list_document_structures()` exactly) -- no `document.read`-style permission exists, and no scope-row filtering (`filter_scope_rows`) is used anywhere in `DocumentService`.
- **Document belongs directly to Organization** via a non-nullable `organization_id` FK — confirmed on `DocumentORM`. `document_structure_id` is a separate, independently-nullable FK to `document_structures.id` (a document may optionally belong to one classification structure).
- **`DocumentLink` is a genuinely separate concept from "which organization a document belongs to."** A `DocumentLink` row (`module_code`/`entity_type`/`entity_id`/`link_role`) associates a Document with a business record (e.g. a specific Project or Employee), and `DocumentLinkRepository.delete(link_id)` removes only that association row -- it never touches the `Document` row itself. The Document's actual organizational ownership is `Document.organization_id`, not a link. This confirms the spec's explicit caution ("must not accidentally turn an Organization association removal into document deletion") describes an existing, already-correct separation in the domain model -- this read-only slice does not add any link/unlink UI at all, so there was nothing to get wrong here, but the investigation is recorded for the next phase that does touch links.
- **Document genuinely has no `created_at`/`updated_at`**, same as Employee -- verified on `DocumentORM`. `uploaded_at` (non-nullable) already serves as its own real "when was this created" timestamp and is already exposed on `DocumentDto`; no gap to report or fields to add.
- **A real, non-obvious cross-organization-safety issue, found only by reading the existing standalone Documents workspace's wiring, not by symptom**: `DocumentsWorkspacePage.qml`'s nested `AdminDocumentsDetailPage` (the full detail view with document preview + linked-records table) does not render from the row's own catalog item alone, unlike Site/Department/Employee's detail pages. It depends on `workspaceController.selectDocument(id)`, which populates `selectedDocument`/`documentPreview`/`documentLinks` via `PlatformDocumentManagementPresenter.build_document_focus()` -- and that method calls `self._document_api.list_documents(active_only=None)`, i.e. `DocumentService.list_documents()`, which is **itself hard-scoped to the session's active organization**, not an explicit one. Opening the full nested detail page for a document belonging to a *non-active* organization (exactly the scenario Organization Detail's Documents tab must support) would silently resolve `build_document_focus()`'s document-id lookup against the wrong organization's document list -- `_resolve_selected_document` would either pick a different, wrong document or find none at all, either of which is a real correctness bug, not a cosmetic one. This is reported here rather than silently worked around by, e.g., duplicating the whole document-focus pipeline as a new tenant-scoped path (out of this read-only slice's scope) or shipping a broken nested detail view.

## 2. Backend change (approved scope, exactly as specified)

New, **read-only**, additive methods — zero changes to any existing method's behavior or signature:

- `DocumentRepository.list_page_for_organization_in_tenant(organization_id, tenant_id, *, page, page_size, search, active_only)` (contract + `SqlAlchemyDocumentRepository` implementation) -- tenant + organization filtered directly from caller-supplied IDs, bypassing `TenantScopedRepositorySupport`'s active-organization gate. Paginated, searchable (title/document code/file name), `active_only` filterable. `DocumentLinkRepository`/`DocumentStructureRepository` are completely untouched.
- `DocumentService.list_documents_page_for_organization(organization_id, *, page, page_size, search, active_only)`: requires `settings.manage` (matching `list_documents()` exactly); resolves the caller's tenant; looks up the target organization via `OrganizationRepository.get_for_tenant(organization_id, tenant_id)` -- raises `NotFoundError` if it doesn't belong to that tenant. Never checks the organization's own lifecycle status. `create_document`/`update_document`/`add_link`/`remove_link` are completely untouched -- mutations still resolve via `self._active_organization()`, the existing domain rule.
- `DocumentDto`/`DocumentPageDto` (+ `PlatformDocumentDesktopApi.list_documents_page_for_organization`): DTO layer exposing the above. No timestamp fields added -- see §1.
- `DocumentPage` dataclass mirrors `SitePage`/`DepartmentPage`/`EmployeePage`.

## 3. Tests proving the required scenarios (all passing)

`src/tests/platform/application/test_document_organization_scoped_read.py` (5/5):
1. `test_viewing_a_non_active_organization_returns_its_own_documents_correctly`
2. `test_no_leakage_from_the_active_organization_into_the_viewed_organization`
3. `test_cross_tenant_organization_id_is_rejected_not_visible` (raw ORM rows, tenant/organization each committed separately for SQLite FK-insertion ordering)
4. `test_inactive_and_archived_organizations_still_have_readable_document_history`
5. `test_mutation_paths_still_use_the_active_organization_not_the_viewed_one`

`src/tests/ui_qml/platform/presenters/test_organization_detail_documents_tab.py` (2/2, real `QQmlApplicationEngine` load, no mocks):
- `test_documents_tab_loads_real_paginated_data_for_a_non_active_organization` -- also asserts `_isViewingActiveOrganization` is `False` in this scenario, proving the row-activation gate (see §4) is actually armed, not merely present in the source.
- `test_documents_tab_controller_slot_applies_status_filter_server_side`

## 4. QML: the Documents tab itself

`AdminOrganizationDetailPage.qml`'s Documents section (a standalone `OrganizationDocumentsSection.qml` file, following the section-file pattern) was replaced with a real tab:

- `PlatformComponents.AdminEntityWorkspace` for the **list** -- same stack Sites/Departments/Employees/Organizations use.
- Default columns: **Document, Code, Type, Status**. Optional (off by default): Version (`businessVersionLabel`), Current (`isCurrent`), File (`fileName`). **No Structure column** -- resolving `document_structure_id` to a structure name would need the same kind of tenant-scoped lookup already built for Department's Site/Parent-Department names, but `DocumentStructureRepository` has no tenant-scoped page method yet; building one is real, bounded backend work out of this slice's scope, so the column is omitted rather than showing a raw ID or an always-empty label. Flagged as a deferred gap, not silently dropped.
- A `Status: All/Active/Inactive` `ComboBox`, calling the new tenant-scoped method server-side.
- Own local pagination/search/filter state (`_documentsPage`/`_documentsPageSize`/`_documentsSearch`/`_documentsStatusFilter`), independent of the global Documents workspace's own state.
- **Row activation to the full nested `AdminDocumentsDetailPage` is gated to only the organization the caller is both viewing AND has switched into** (`_isViewingActiveOrganization`, the same flag that already gates "+ New Document") -- directly because of the §1 finding: `selectDocument()`'s internal focus-building is itself active-org-scoped, so opening the full detail (preview + linked-records) for a document from a *different* organization than the one currently active in the caller's session would resolve the wrong document's focus state. When viewing a non-active organization, clicking a row still updates the table's own selection highlight (`onRowSelected`) but does not navigate to the detail page. This is the one place this slice's read-only list/detail split differs structurally from Sites/Departments/Employees, and it's a correctness gate, not a cosmetic restriction -- see `OrganizationDocumentsSection.qml`'s header comment for the full reasoning inline at the point of use.
- True-empty ("No documents yet...") vs. filtered-no-results ("No documents match your current filters.") states.
- The existing `Connections` block (already handling Sites/Departments/Employees) now also re-fetches this tab's page on `onDocumentsChanged`.
- "Add Link" (`create_document_link`) from within the nested detail page (only reachable when viewing the active organization, per the gate above) is wired through to the existing `AdminDialogHost.openDocumentLinkCreate(documentId)` unchanged -- no new link/unlink logic was written for this slice.

**Shared-component changes:**
- `PlatformDocumentCatalogPresenter._serialize_document`'s `status_label` is now the explicit `{"label", "tone"}` dict shape, matching Site/Department/Employee's Phase K pattern -- giving the pre-existing standalone Documents workspace a real StatusChip tone it didn't have before. Two QML consumers of the old plain-string shape were fixed (`DocumentsWorkspacePage.qml`'s Inspector, `AdminDocumentsDetailPage.qml`'s header).

## 5. Permissions and the create-action decision

Identical reasoning to Sites/Departments/Employees: "+ New Document" is enabled only when **both** `canWrite` **and** the organization being viewed is the caller's actual session-active organization (`_canCreateDocument = canWrite && _isViewingActiveOrganization`). `create_document()` keeps using the active-organization domain rule unchanged. Viewing the list stays fully available regardless of which organization is active; opening the full detail view is additionally gated per §4.

## 6. Known gaps / explicitly deferred (not silently dropped)

- **No Structure column / no tenant-scoped structure-name lookup** -- see §4. `DocumentStructureRepository` would need its own `list_page_for_organization_in_tenant`-equivalent (or at least a `get_for_tenant`-style bypass) before a Structure column could show a real name for a non-active organization's documents.
- **Row activation to the full nested detail page only works when viewing the active organization** -- see §1 and §4. Making it work universally would require either a new tenant-scoped `DocumentService` focus-building path (mirroring `build_document_focus()` but explicit-organization) or reworking `AdminDocumentsDetailPage` to not need the shared, active-org-scoped `selectDocument()` call at all. Both are real backend/UI work, correctly out of a read-only vertical slice's scope -- reported here rather than shipping a detail view that would silently show the wrong document.
- **Document Detail's own "Control"/"Audit" cross-links** are inert when opened from inside Organization Detail (only reachable for the active organization to begin with, per the gate above) -- consistent with the same limitation already documented for Sites/Departments/Employees' nested detail pages, to be addressed by the already-scheduled scoped-routing fix.
- **Pixel-level visual QA** deferred to the combined visual QA pass, same reason as the other three tabs (`grabToImage()` needs a `QQuickWindow`-backed root).

## 7. Regression

- `test_document_organization_scoped_read.py`: 5/5
- `test_organization_detail_documents_tab.py`: 2/2
- `test_document_platform_foundation.py`, `test_organization_activity_curated_feed.py`, `test_platform_admin_desktop_api.py`: unaffected, still passing
- `test_organization_detail_sites_tab.py`, `test_organization_detail_departments_tab.py`, `test_organization_detail_employees_tab.py`, `test_visual_qa_organizations.py`, `test_detail_view_tracker.py`, `test_qml_platform_presenters_catalog_admin.py`: 17/17 combined, confirming Documents didn't disturb the three prior tabs or the section-file refactor
- `test_qml_status_chip_consumers_load.py`: still passing with Document's new dict-shape status label included
- Full `src/tests/platform/application` + `src/tests/platform/api` and full `src/tests/ui_qml/platform` batches: run as part of this slice's closeout (results reported in the follow-up message)
- Same pre-existing, unrelated failure as every prior slice: `test_qmllint_no_longer_reports_qobject_controller_member_warnings` (untouched `PlatformWorkspacePage.qml`).

## 8. Acceptance status for Documents specifically

Tenant-scoped explicit-org read ✅ · read-only ✅ · tenant-membership enforced ✅ · existing permission rules applied ✅ (Document's own plain-`settings.manage` model, preserved as-is) · not active-org-gated (for the list) ✅ · mutation scoping unchanged ✅ · repository capability reused, no duplicate query path ✅ · server-side search/filter/pagination ✅ · inactive/archived organizations remain readable ✅ · not made operationally selectable ✅ · tests for all 5 required scenarios ✅ · real TableToolbar/DataTable/TablePaginationBar/Columns reuse ✅ · true-empty vs. no-results ✅ · create action ✅ (with the active-org gating in §5) · link/unlink semantics fully preserved, untouched, and verified not to alias into document deletion ✅ · row activation to real Document Detail ✅ **for the active organization**, correctly gated off otherwise with the reasoning documented inline (§4/§6) rather than left as a silent bug.

**All four Organization Detail child-workspace vertical slices (Sites, Departments, Employees, Documents) are now complete.** Not yet done (by design, sequenced next): Inspector redesign, then the scoped-routing fix for Related Actions/Key Statistics/Inspector metrics, then a combined regression/visual-QA/documentation pass across all four tabs together.
