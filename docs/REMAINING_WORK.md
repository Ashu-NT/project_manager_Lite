# Remaining Work — Consolidated Tracker

Generated 2026-07-24 by scanning every `.md` file under `doc/` and `docs/` (91 files) and
cross-checking their claims against the current `src/` tree. This file replaces ~62 stale,
superseded, or duplicate planning/audit/tracker documents that were deleted as part of this
cleanup. It is the single place to look for "what's not done yet."

A smaller set of substantive, still-accurate reference and active-plan documents were **kept**
(listed at the bottom of each section as "Detail:") because their per-item design detail is too
large to compress into bullets here. Everything else in `doc/`/`docs/` prior to this file was a
historical status log, a contradicted/superseded plan, or a stale documentation stub, and was
removed.

Several source docs contradicted each other or contradicted the current code (a doc claiming a
module is "skeleton only" when it's actually substantially built, or vice versa). Where this was
caught, the item below reflects the verified-against-code status, not just the doc's own claim.

---

## 1. Tenant / Multi-Tenant Isolation

**Detail:** `docs/architecture/enterprise-platform-architecture.md` (§Roadmap), `docs/ARCHITECTURE.md` (§9–10), `docs/tenant_architecture_audit/PHASE_2_HARDENING_FINDINGS.md`, `docs/tenant_repository_hardening/README.md` + `NEXT_TRANCHES.md`

### Critical / High
- No `user_tenants` membership table and no membership check in `TenantContextService.set_active_tenant()` — any authenticated user can switch into any active tenant by ID and immediately see its data.
- `OrganizationService._deactivate_other_organizations()` is not tenant-scoped (`list_all(active_only=True)` spans all tenants) — activating an org in Tenant A deactivates active orgs in every other tenant.
- Username is globally unique (not per-tenant) — two tenants can't share a username; must become `UNIQUE(username, tenant_id)`.

### Medium (from Phase 2 hardening findings, still open)
- M-1: `TenantContextService` calls unscoped `get()` instead of `get_for_tenant()` (`tenancy/tenant_context.py:126,140`).
- M-2: `UserRepository.list_all()` exposes all users cross-tenant at runtime.
- M-3: `ActivityRepository.list_recent()` has a silent except-pass scope fallback.
- M-4: Bootstrap sets `active_organization_id` before `active_tenant_id`.
- M-5: `TenantContextService.set_active_tenant()` doesn't clear `active_organization_id`.
- M-6: RBAC scope resolver for `'organization'` uses unscoped `get()`.
- M-7: `tenant_admin` role includes `tenant.create` — self-propagation risk.
- M-8: No dedicated `'tenant_access'` error category in `execute_desktop_operation`.
- M-9 / M-10: No `PlatformEvent` emitted for tenant-context switches or `assign_scope_grant()`.
- M-11: `EnterpriseCalendarResolver` captures `organization_id` at build time (stale after an org switch).
- M-12: SoD rules missing payroll self-approval and finance-unilateral-control conflicts.
- M-13: `UserSessionContext.get_active_tenant()` silently falls back to the default tenant without a membership check.

### Low
- L-1: Triplicated `_tenant_scope.py` files across PM/maintenance/inventory need consolidating into a shared base.
- L-2: `suspend_tenant` event hardcodes `old_status` instead of capturing prior state.
- L-3: Duplicate role aliases (`finance`/`finance_controller`, `maintenance_manager`/`maintenance_admin`) need consolidating.
- L-4: `list_users_for_tenant()` doesn't filter out inactive memberships.
- L-5: `TaskCollaborationStore` unread-mentions query is fully unscoped (no `tenant_id` on `TaskCommentORM`).
- Missing `PlatformEvent` emission for: role assign/revoke, `user.register`, `organization.create`, `user_tenant_membership.add`, `site.create`, `department.create`.

### Schema hardening
- `tenant_id` NOT NULL enforcement across 33 tenant-root columns (currently nullable/transitional).
- Re-key `organization_module_entitlements` PK to `(tenant_id, module_code)` (needs SQLite table recreation).
- `employees.organization_id`, `time_entries.organization_id`, `timesheet_periods.organization_id` — nullable, should be required.
- `maintenance_asset_components` and `document_links` lack a direct `tenant_id` (inconsistent with sibling tables).
- `approval_requests.project_id` and `baseline_variance_records.project_id`/`task_id` stored as plain strings, no FK.
- `ScopedAccessGrant.tenant_id` nullable for non-organization scopes — creates cross-tenant permission bleed.
- Repository constructor tightening for platform/PM repos still defaulting `_tenant_context_service = None` (e.g. `sites.py`, PM `task.py`/`collaboration.py`) — see `tenant_repository_hardening/NEXT_TRANCHES.md`.
- Non-PM contract cleanup: `list_for_organization(...)` still present across 8 platform repos and 15 inventory/procurement files — evaluate whether it can be simplified away.

### Cross-cutting / not yet built
- No automated cross-tenant isolation test suite (direct object access, list isolation, write isolation, child-table isolation) — `test_repo_cross_tenant_isolation.py` doesn't exist yet.
- Cache/QSettings keys are not tenant-keyed anywhere in `src/` (no `org:{organization_id}:...` pattern found) — dashboard/export snapshots carry no tenant/org tagging.
- Background workers (`QThreadPool` jobs, scheduled refreshes, notification/import workers) don't receive an explicit propagated `TenantContext`.
- No two-organization tenant penetration smoke test has been run.
- No `create_tenant` / `list_tenants` / `deactivate_tenant` service API, no tenant switcher UI, no tenant-level audit log, no cascade on tenant deactivation.

---

## 2. Auth, RBAC & Identity

**Detail:** `docs/ARCHITECTURE.md` (§4–7), `docs/architecture/enterprise-platform-architecture.md`, `docs/architecture_decisions/ADR-001*`, `docs/platform_alignment_followup/auth_access_scaling/README.md`

- **MFA is non-functional end-to-end** — TOTP backend is correct, but the QML login form never presents a code-entry field, so any account with MFA enabled becomes unreachable through the UI.
- Password hashing is custom PBKDF2-SHA256 (390k iterations) — recommended migration to Argon2id (memory-hard, current NIST/OWASP recommendation), with a re-hash-on-login migration path.
- Replace the custom TOTP implementation with `pyotp`.
- `is_platform_admin()` is dead code — `"platform.admin"` permission is never seeded or assigned to any role; always returns `False`.
- `user_roles` table's `UNIQUE(user_id, role_id)` constraint is missing `organization_id` — makes it impossible to assign the same role to a user in two different organizations.
- No `tenant_admin`, `org_admin`, `site_admin`, or `department_manager` roles — `admin` (superuser) is the only privileged role, an all-or-nothing model. (`docs/architecture/enterprise-platform-architecture.md` §25 claims Phases 0/1/2A–2C, incl. `tenant_admin`/`org_admin`/`user_tenants`, are ✅ complete — this contradicts the earlier narrative sections of the same doc; verify directly against `src/core/platform/` before relying on either claim.)
- `site.manage`/`site.admin`/`department.manage`/`department.admin` permissions and site/department-scoped grant assignment don't exist.
- `@requires_module` / `@requires_scope` decorators not added.
- SoD bypass is scoped to the whole `admin` role rather than a narrower `platform_admin` tier; SoD-3 through SoD-9 rules not confirmed implemented.
- No user invitation flow, no `users.lifecycle_state` enum, no session invalidation on deactivation, no self-service password reset token flow (only admin-initiated reset exists), no Suspend/Delete/Restore user service methods, no org switcher in the shell header.
- Organization lifecycle: `archive_organization()`, `soft_delete_organization()`, `OrgMergeService` not built.
- Web auth transport/middleware (ASGI/FastAPI auth layer, OIDC/hosted SSO adapters) — planned, not started.
- Richer contextual policy inputs for ABAC-style authorization decisions — planned, not started.
- Configurable (vs. fixed-list) separation-of-duties rules; broader Security-admin workflows (password reset, MFA lifecycle, federated identity ops) — in progress.
- Non-project scope rollout beyond `project`/`storeroom`/`site` (asset, maintenance-area, other operational scopes) — in progress.
- `require_module_enabled()` fails open on error instead of closed — should be inverted.
- Role/description search in the Users admin workspace — not done.

---

## 3. Platform Modernization (Admin Console / Control Center / Settings)

**Detail:** `docs/platform_modernization/PLATFORM_LIST_DETAIL_MIGRATION_PLAN.md` (current source of truth — supersedes the alignment plan's status claims), `docs/platform_modernization/PLATFORM_LIST_DETAIL_ALIGNMENT_PLAN.md`, `docs/platform_modernization/PLATFORM_CALENDAR_OWNERSHIP_MIGRATION_PLAN.md`

- Admin Console → **Documents** and **Structures**: entire list/detail workflow not started (section mapping, list/detail migration, Overview/Revisions/Linked-Entities/Approvals/Access/Audit sections, section-aware actions, lazy loading).
- Admin Console → **Roles & Access**: Overview/Permissions/Scope/Users/Sessions/Audit section build-out mostly not started (only action-wiring and lazy loading done).
- Admin Console → **Organizations**: RBAC/entitlement-driven section visibility still in progress.
- Embedded detail tables (Site→Departments, Department→Employees, User→Module Access, Document→Linked Entities) are still client-filtered `rows:` — need migration to scoped `sourceModel` (backend work required).
- Control Center → **Audit**: no row-activation-to-detail-page flow.
- Control Center → **Escalations / System Events**: blocked — `rows: []` placeholders, no controller/presenter/desktop-API backing yet.
- Control Center → **Approvals**: Delegate action doesn't exist — needs a new controller slot/presenter/desktop-API.
- Settings → **Integration Capabilities**: detail sections deferred (no per-capability field model in the controller yet).
- Settings → **Security** / **Support**: section shells not yet aligned with the shared list/detail pattern.
- Shared component verification (`ContextualActionToolbar`, `SectionDetailPage`, `DataTable`, `InlineMessage`, `BulkActionBar` for Platform) — not started as a formal pass.
- Formal lazy-loading rule set for Platform workspaces — not written.
- RBAC/entitlement gating: hide `Audit` section without `audit.read` (blocked on a backend `canViewAudit` flag); per-action `enabled` flags not yet wired to permissions.
- Column-state persistence (`loadTableColumnState`/`saveTableColumnState`) — not exposed by the admin controller.
- Full `python main_qt.py` interactive validation pass for the migrated Admin Console — not run.
- Calendar ownership migration Phase 6 (cleanup): remove stale PM-owned calendar files, update tests/architecture guardrails, run stale-import scans and backend/QML validation — all unchecked.
- PM Scheduling desktop API still owns calendar CRUD as a compatibility bridge — undecided whether to convert to a thin redirect-only contract.
- Legacy PM task-permission guard still used for the moved platform calendar service — flagged for revisit.

---

## 4. Inventory & Procurement

**Detail:** `docs/inventory_procurement/README.md`, `docs/inventory_procurement/REDESIGN_PLAN.md`

- WS-1 Dashboard: panel drill-down navigation and context bar (Org/Site/Warehouse/Module scope selectors) — pending, needs a platform filter API.
- WS-2 Catalog: row serializer enrichment, Specifications/Suppliers/Linked-Assets(Maintenance-gated)/Linked-Projects(PM-gated) sections — pending.
- WS-3 Warehouses: detail sub-sections (Bins, Stock Balances, Movements, Cycle Counts) — pending, lazy-loaded.
- WS-4 Stock Balances: row enrichment (onHand/available/reserved/reorderPoint/unitCost); Movements/Reservations sub-sections — pending.
- WS-5 Stock Movements: Platform Audit trail in detail — pending.
- WS-6 Reservations: row enrichment; Allocation and Source-demand sub-sections — pending.
- WS-7 Procurement: row enrichment; Line-items and Receipt-history sub-sections — pending.
- WS-8 Pricing: row enrichment; Price-history/Contracts sub-sections; detail view models not yet added to `pricing_workspace_controller.py` (currently synthetic client-side fields).
- Server-side pagination — not started (`totalCount = len(items)`, client-side only, everywhere).
- ActivityFeed real-data wiring (`loadDetailActivity`, `PlatformAuditDesktopApi.list_events`) — not done for any detail page.
- 18-item validation checklist for the redesign — never confirmed executed.
- **Verify before trusting:** Phase 10 of `REDESIGN_PLAN.md` claims all 35 deprecated files were deleted; at least one (`InventoryProcurement/Widgets/WorkspaceStateBanner.qml`) still exists and is still registered in its `qmldir`, modified *after* the claimed completion date. Re-audit before assuming this phase is closed.
- Richer warehouse execution: directed/bin policies, inspection flows — not built.
- Broader serial/lot lifecycle traceability beyond receipt capture — not built.
- No dedicated `application/pricing/`/`domain/pricing/` subdomain — pricing stays an API/reporting projection.
- Maintenance-side adoption of the inventory material contract (Slice 6) — not built. Note: the "blocked on Maintenance not being built" premise is outdated — Maintenance now has substantial runtime code, so this may be unblockable sooner than the doc assumes.
- Shared import/export behavior for site/department/employee/party/document-infrastructure — `PARTIAL` everywhere (admin CRUD exists, no shared CSV/Excel/sync/export contract); documents specifically have no bulk import/export contract at all.

---

## 5. Maintenance Management

**Detail:** `docs/maintenance_management/README.md`

- **Phase 3 (Inventory & Procurement integration from Maintenance's side) is entirely unbuilt**: scaffold, party-master alignment, `stock_item`/`storeroom`/`stock_balance`/`stock_transaction`/`material_reservation`/`purchase_requisition`/`purchase_order(_line)`, and the related UI workspaces.
- Preventive engine hardening: blackout-calendar/non-working-period handling, route/campaign grouping — next up, not done.
- Richer Preventive Plan authoring/revision workflow UI — pending.
- Richer Sensors registry/source-mapping admin UI; standalone Sensor Registry library workspace — not started.
- Guided Work Request intake/create forms beyond queue review; guided Work Order authoring/planning forms beyond queue/detail execution.
- Deeper field/mobile confirmation variants for technician execution.
- Domain backlog: cross-table unique business keys, template revision behavior, task-completion gate logic — undefined.
- Document/document-link services for Maintenance — unbuilt despite platform-level document plumbing existing.
- Import/export/report runtime: workbook template generator, validation services, row-level diagnostics, dry-run preview UI — all pending (only a dormant contract scaffold exists today).
- Audit coverage for status/master-data changes — status unclear.
- Optional future `Vendors` UI tab — not started.
- **Note:** `docs/architecture_decisions/ADR-001*` and a few other older docs describe Maintenance as "not implemented beyond scaffolding" — this is stale; `src/core/modules/maintenance` (143 files) and `src/ui_qml/modules/maintenance` (299 files) have real, working services (work requests, work orders, preventive, generation).
- 7 unresolved product questions: site-as-own-table vs. folded into location; unified party table vs. separate supplier/manufacturer tables; whether preventive plans default to work requests or direct work orders; default PM schedule policy (fixed vs. floating) and generation horizon; whether technician labor should use the shared time boundary from day one; inventory_procurement scaffold sequencing vs. Maintenance runtime screens.

---

## 6. Project Management Modernization

**Detail:** `docs/pm_modernization/README.md`

- `ResourceLevelingService` marked pending — likely superseded by `ResourceLevelingEngine`, needs an explicit decision to drop it.
- Tasks workspace has no native tree-table expansion (WBS is a flat filtered list with on-demand children) — a dedicated tree-table component may still be needed.
- `exportSchedule()`, `exportTasks()`, `exportResources()`, `exportFinancials()` are still stub placeholders returning "not available" (only `exportProjects()` is a real export).
- `AsyncThresholdGuard` backend exists but isn't wired into any controller — recalculate-schedule, leveling propose, forecast compute, schedule-impact preview, portfolio demand, and report renders don't yet use the classify → LoadingOverlay → background-thread → signal pattern.
- Assign Resource flow has no inline availability/skill-match preview before committing.
- Lazy-loaded sections across all 11 PM workspaces show blank content while loading — no spinner/skeleton/error state; needs uniform `LoadingOverlay`/`EmptyState`/retryable `InlineMessage`.
- RBAC-gated buttons (Submit Baseline, Approve/Reject, Apply Leveling, Import) are always visible regardless of role — not wired to `AuthorizationEngine.has_permission()`.
- Missing tests for: Phase 2 presenter methods, `previewAssignment` mapping, scoped-refresh behavior, `can*` property gating.
- `scheduling_workspace_presenter.py`, `scheduling_workspace_controller.py`, `tasks_workspace_presenter.py` still exceed the architecture test's documented line-count limits.

### PM stability & message-scope validation (`doc/pm_stability_and_message_scope_plan.md`)
- Phase I — end-to-end validation of the Dashboard/Portfolio/Scheduling crash fix and the InlineMessage scoping fix — not done; only automated checks have passed so far.
- Manual validation still needed: no repeated calendar expansion/DB storm check; Create-Calendar-then-switch-to-Sites message isolation; site success/error scoped correctly; detail-page messages tied to the selected entity; no duplicate `WorkspaceStateBanner`+`InlineMessage`.
- Two pre-existing, unrelated test failures remain outside this fix's scope (`test_project_management_qml_uses_named_modules_and_typed_catalog_properties`, and broader standing failures in `test_qml_architecture_guardrails.py`).

### Register / Risk module (`docs/REGISTER_RISK_CONSOLIDATION.md`)
- Add `DECISION`/`ASSUMPTION`/`LESSON` entry types (needs an Alembic migration extending the `entry_type` enum).
- Populate the Impact section for ISSUE and CHANGE entry types (only RISK fields are reliably populated today).
- Add type-count badges to tabs (e.g. `Risks (12)`) from controller metrics.
- Type-specific columns per active tab (Probability/Impact/Risk Score for Risks).
- Presenter should populate `probabilityLabel`, `impactLabel`, `riskScore`, `mitigationStrategy`, `residualRiskLabel`.
- Finer-grained permissions: `register.risk.read` / `register.issue.read` / `register.change.read`.
- Lower priority: inline type badge chip on the detail header, CSV/Excel export type column for "All Entries", type-specific bulk actions.

### PM data integrity (`docs/PM_DATA_INTEGRITY_AUDIT.md` + `_FOLLOWUP.md`)
- Run the health-check CLI against real/production data and clean findings *before* applying new constraints to a non-empty database (operator action, not code).
- Re-scope repository `delete`/`get`-by-id calls to also filter by `project_id` (defense-in-depth).
- Convert `BaselineVarianceRecordORM.project_id` to a real FK (currently a plain string).
- Confirm `CalendarEventRepository.list_range` is project-scoped at every call site.
- Add required-field validation + `InlineMessage` to `TaskAssignmentHoursDialog` and `ProjectStatusDialog`.
- Wire the health-check CLI into CI as a nightly/data-migration gate.

---

## 7. Shared Platform Infrastructure

**Detail:** `docs/cache_service_strategy/README.md`, `docs/platform_alignment_followup/README.md` + `import_export_report_runtime/README.md` + `SHARED_MASTER_READINESS_CHECKLIST.md`

### Cache Service (design complete, zero runtime code written)
- Shared `CacheService`, `CacheKeyBuilder`, `CachePolicyRegistry`, `CacheInvalidationService`, `DerivedSnapshotService` contracts — not built.
- Cache policy entries for low-risk platform reference data; derived snapshots for dashboards/portfolio aggregation; PM schedule/resource/financial snapshot policies; inventory balance/valuation/replenishment snapshot policies.
- Bridge Maintenance-specific events into `DomainEvents` before caching Maintenance dashboards/backlogs (named blocker).
- Wire invalidation to `domain_changed`/`shared_master_changed`/named signals plus approval/audit mutations.
- Telemetry (hit/miss, refresh duration, stale serves, invalidation counts).
- Full test suite: tenant isolation, permission-leak, invalidation, snapshot freshness, event-replay/idempotency, performance, non-blocking QML.
- Recommended first step: a pilot spike (one Platform reference cache + one PM dashboard snapshot) before expanding scope.

### Import / Export / Report Runtime
- PM adoption layer: register PM report definitions against the new shared runtimes and prove no regression — in progress.
- Real worker-side retry/cancellation execution on top of the persisted runtime control seam — not built.
- Live Maintenance handler adoption for the shared import/export/report contracts — contracts exist but are dormant, no Maintenance-side implementation yet.

### Shared master-data readiness
- Import/export contract decision needed for all five shared domains (site, department, employee, party, document infrastructure) — currently admin CRUD only, `PARTIAL` everywhere.
- Continue hardening `inventory_procurement`'s shared import/export contracts and advanced stock-control rules.
- Reuse the document-integration pattern as the reference design for future shared-master module consumers.
- Transitional/accepted-as-permanent (not TODOs, but worth knowing): employees still store `site_name` as a compatibility string; time entries keep site/department snapshot strings instead of only IDs; PM task-comment attachments use a module-local storage path pending a later slice; `site.integration_profile_id` deferred until a shared integration-profile domain exists; document storage/upload transport is still desktop-first.

---

## 8. UI/UX Cross-Cutting Work

### DataTable architecture (`docs/DATATABLE_ARCHITECTURE_MIGRATION_PLAN.md`)
- Portfolio workspace: 3 tables (heatmap, funding, risk) still use QML `.map()` transforms instead of presenter-side data.
- Collaboration workspace: multi-tab computed `rows: _currentPagedRows` needs a controller-side panel model.
- `ProcurementWorkspacePage.qml` order-lines detail table and `CollaborationDetailPanel.qml` related-items sub-table — not migrated to controller-backed models.
- `sortRequested` not wired in every DataTable (needs presenter `order_by` support).
- Export isn't unified across modules — only PM has a `table_exporter.py`.
- Column visibility/order preferences persist globally, not per `tableId`.
- No true backend/server-side pagination anywhere (`totalCount = len(items)` throughout).
- Final QML audit for stray `rows:`/`clientSideSorting: true` and for `set_rows()`-on-selection/`beginResetModel()`-on-checkbox anti-patterns — not re-run recently.

### Lazy Section Loading (`docs/LAZY_SECTION_LOADING_FEEDBACK.md`)
- Maintenance and Inventory/Procurement detail panels don't use `LazySectionLoader`/section-level lazy loading yet.
- Per-section `fallbackLoadingHeight` tuning for tall sections (e.g. activity feeds) — not done.
- Smooth height transition (`Behavior on implicitHeight`) — not done, needs profiling first (layout-thrash risk).
- Replace `InlineMessage` "Loading..." text with a compact `LoadingOverlay` for visual consistency.
- Skeleton-loading placeholders — not done, significant effort.
- Loading-message i18n — not done.
- `qmllint` CI check on `LoadingOverlay.qml`/`LazySectionLoader.qml` — not done.

### Inline Messages (`docs/INLINE_MESSAGE_STANDARDIZATION_PLAN.md` — see also the kept `_README.md` for conventions)
- Maintenance dashboard full-page `LoadingOverlay` placement — cosmetic, deferred.
- Dialog success-feedback polish (surface `feedbackMessage` for dialogs that stay open after save) — entirely not done.
- Phase 6 sign-off: interactive `python main_qt.py` boot + per-module walk, manual list/detail/dialog message-scope walk, stale-message-after-close check — none done.

### Workspace Refactoring (`docs/workspace_refactoring_plan.md`)
- Priority 1: extract `ListPage` components for financials, register, procurement, reservations, inventory, warehouses, work_requests, assets, preventive workspaces (list UI still inline in `WorkspacePage.qml`).
- Priority 2: extract `DetailPanel` components for the same workspace set.
- Priority 3: full Portfolio + Scheduling (PM) refactor — move ~15 section/component files into `sections/`/`components/`, create `PortfolioWorkspaceState.qml`/`PortfolioColumnConfig.js` and `SchedulingWorkspaceState.qml`.
- Priority 4: Dashboard workspaces (all 4 modules) + Collaboration — folders exist, no `WorkspaceState.qml`/section extraction done.
- Priority 5: Platform workspaces (Admin Console 15+ section files, Control, Settings) — folders only, sections not moved.
- Known risk: QML module cache needs clearing after moves; Warehouses' cross-folder dialog-host import path unverified at runtime; `FinancialsInsightsSection.qml` still at workspace root.
- Validation checklist (route opens, column-customizer persistence, pagination, bulk actions, dialog wiring, no broken imports/stale `qmldir`) not marked done for Phase-2 workspaces.

### UX Execution Plan (`docs/ui_ux_execution_plan.md`)
- Density mode (Compact/Comfortable/Spacious) — explicitly pending; needs a density preference on `ShellContext`/settings plus `AppTheme` density tokens wired through row/toolbar/form/sidebar/dialog spacing.
- Full validation pass (compileall, architecture/platform/PM/inventory/maintenance pytest, qmllint, offscreen dialog checks) — deferred, not confirmed executed.

### Dialog Design System (`docs/DIALOG_DESIGN_SYSTEM_AND_CODE_GENERATION.md`)
- Optionally migrate Inventory's random `INV-PO-xxxxxxxxxx` PO numbers to a meaningful sequential `PO-2026-NNNN` format — open, not done.
- Optionally extend the "required" asterisk convention to non-code labelled rows for full consistency — open, cosmetic.

---

## 9. Repo Structure / Legacy Cleanup

**Detail:** `docs/repo_structure_plan/EXECUTION_SPEC.md`, `docs/repo_structure_plan/README.md`

- HTTP transport adapters for `project_management`, `inventory_procurement`, and `maintenance` — deferred; `src/api/http/` currently only has `platform/` and `runtime.py`.
- Slice 5 (HR Management, Payroll, QHSE): only placeholder package skeletons exist; cross-module isolation architecture tests for these not written.
- Employee master-data ownership transfer from Platform to HR — unresolved.
- **Slice 6 (Legacy Path Cleanup) — entirely open**: delete remaining legacy root paths, retire `tests/path_rewrites.py` (confirmed still present — it was only relocated to `src/tests/path_rewrites.py`, never actually removed), update architecture tests to ban old imports, remove duplicate shell/module-registration transition code, update the root `README.md` for the new `src/` tree.
- Known environment blocker: interpreter outside the `pmenv` conda env fails on missing `reportlab`/`alembic` deps — unresolved as stated.
- PM QML deeper-parity gaps: dashboard dialogs/mutations, projects import/resource-assignment panels, resources utilization panels, deeper tasks parity, portfolio scoring governance/analytics, timesheets payroll-close integration.

---

## 10. Code Quality / Refactor Backlog

**Detail:** `docs/LARGE_FILES_REFACTOR_PRIORITY.md` (re-scan before trusting fully — see caveat)

- 106 files across 8 tiers still exceed the 350-effective-LOC threshold and need splitting. **Caveat: at least one entry (`auth_service.py`) is confirmed stale — it's now 221 raw lines, not the 915 effective LOC claimed — re-run the LOC scan before treating this list as authoritative.**
- Highest-impact confirmed-still-large files: `test_project_management_desktop_api.py` (3008 lines), `test_qml_platform_presenters.py` (2253), `test_qml_project_management_presenters.py` (2065), `maintenance/repositories/repository.py` (1250, confirmed), `maintenance/orm/models.py` (1155), `maintenance/mappers/mapper.py` (1022), `test_maintenance_foundation.py` (919), `test_maintenance_desktop_api.py` (901), `test_maintenance_persistence.py` (852).

---

## 11. Future / Skeleton Modules

- **QHSE** (`src/core/modules/qhse`) — confirmed skeleton only (stub `__init__.py` files).
- **HR Management** (`src/core/modules/hr_management`, aliased with `payroll`) — confirmed skeleton only; Payroll-first slice planned but not started.
- Long-term platform direction (not scheduled): full REST API layer, PostgreSQL migration, containerization/observability for a hosted/cloud deployment.

---

## 12. Documentation Debt (from this cleanup)

- `docs/section_11_data_ownership_model.md` was deleted — it described table names (`inventory_items`, `po_receipts`, `collaboration_threads`, `register_items`, `audit_logs`) that don't exist anywhere in the current schema (real names: `inventory_stock_items`, `inventory_receipt_headers`, `register_entries`, `activity_entries`/`audit_entries`). The ownership *concepts* (tenant/org/site/department/project/asset hierarchy) are still valid and are now covered by `docs/ARCHITECTURE_README.md` §2–3 — if a literal schema-ownership reference doc is wanted again, write it fresh against current table names rather than resurrecting the old one.
- The entire `docs/technical_doc/` tree (27 of 30 files) was deleted — it described a pre-rewrite `QWidget`-based UI (`ui/platform/...`, `ui/modules/...`) that no longer exists (current UI is `src/ui_qml/`), plus stale paths for `infra/`, `application/`, `api/`, and `core/services`/`core/reporting`. Only `technical_doc/installer/README.md`, `technical_doc/ci-cd/README.md`, and `technical_doc/tests/README.md` were verified accurate and kept. If per-layer technical reference docs are wanted again, regenerate them from the current `src/` tree — don't restore the deleted ones.
- `docs/architecture/enterprise-platform-architecture.md` (kept) has internally contradictory sections: its own §25 roadmap marks Phases 0–2C (tenant_admin/org_admin roles, `TenantAdminService`, `user_tenants`, `platform_events`) as ✅ complete, while earlier narrative sections (§5.5, §6.7, §9, §10, §13, §16) still describe those same things as missing. Verify directly against `src/core/platform/` rather than trusting either section at face value; the doc would benefit from a consistency pass.
- `docs/architecture_decisions/ADR-001-cross-platform-ownership-model.md` (kept) has a dated "Current Implementation Status" checklist that's stale on two points: it says Maintenance and Inventory/Procurement are "not implemented yet beyond scaffolding" — both are substantially built (see §4/§5 above). The ownership *decision* in the ADR is still valid; only its status tracker needs correcting.
- `docs/tenant_isolation_audit/README.md` was deleted — its foundational premise ("Organization is the tenant boundary," no separate Tenant entity) has been superseded by the actual Tenant/Organization split now in the code (confirmed: `src/core/platform/tenancy/domain/tenant.py` exists). Its still-open phases (5–8: dashboard/export hardening, cache/snapshot hardening, async-worker propagation, final penetration test) are folded into §1 and §7 above.
- `docs/tenant_architecture_audit/TENANT_ORG_AUDIT_REPORT.md` was deleted — it was a pre-implementation audit ("Status: Pre-implementation — no code changes made") whose recommendations (Tenant model, `tenant_id` on organizations, employee `organization_id`) have all since been implemented. `PHASE_2_HARDENING_FINDINGS.md` (kept) is the current source of truth for what's still open in this area.
- `docs/tenant_architecture_audit/PHASE_2E_REMEDIATION_REPORT.md` was deleted as a near-duplicate of `PHASE_2_HARDENING_FINDINGS.md` (kept) — same Medium/Low findings, no new information.
- 13 of 15 files under `docs/tenant_repository_hardening/` were deleted (sequential round-by-round completion logs, each one's "next step" confirmed done by the following file). `README.md` and `NEXT_TRANCHES.md` (both kept) are the accurate, current tracker pair for this workstream.
- `docs/platform_modernization/README.md` was deleted — fully superseded by `PLATFORM_LIST_DETAIL_MIGRATION_PLAN.md` (kept), which explicitly notes this doc's "in progress" status had regressed and was re-fixed.
- `docs/project_management_followup/README.md` was deleted — all 9 tracked slices are done; its remaining bullets were explicitly-accepted permanent design tradeoffs (legacy PM task-comment attachments, time-entry site/department snapshot strings, PM resources not owning department/site fields, the lightweight fallback collaboration store), not open TODOs. Worth knowing these are intentional, not gaps.

---

## How to use this file

- Each section links to the "Detail:" docs that still exist under `docs/` for full implementation-level specifics (per-workspace field lists, exact file paths, migration steps).
- When an item here is finished, delete its bullet. When a linked detail doc's tracked work is finished, fold anything still-relevant back into this file and delete the detail doc.
- Do not resurrect any of the deleted files from git history as a "reference" — they were deleted specifically because they were superseded or contradicted by current code; if historical context is needed, use `git log`.
