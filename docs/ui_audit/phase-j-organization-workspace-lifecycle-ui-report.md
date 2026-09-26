# Phase J — Organization Workspace Lifecycle UI — Report

Scope: the Organization workspace UI/UX built on top of the already-complete
and already-green Organization backend lifecycle migration (`OrganizationStatus`
ACTIVE/INACTIVE/ARCHIVED; `activate_organization` / `deactivate_organization` /
`archive_organization` and their bulk variants). No backend lifecycle
architecture was redesigned or modified in this phase — every UI change below
is a consumer of the existing, already-verified service-layer contract.

## 1. Summary of what changed

- **List** (`OrganizationsWorkspacePage.qml` + `OrganizationsColumnConfig.js`):
  recommended columns (Organization / Code / Status / Country-Location),
  presenter-owned StatusChip tone, a server-side "Status: All/Active/Inactive/
  Archived" toolbar filter, and three explicit bulk actions (Activate /
  Deactivate / Archive) added to the existing `BulkActionBar`, alongside the
  pre-existing Change Property / Assign Modules actions.
- **Detail header** (`AdminOrganizationDetailPage.qml` + a new opt-in capability
  on the shared `SectionDetailPage.qml`): organization name, a StatusChip
  lifecycle badge, a `CODE · Location` identity line, a standalone Edit
  button, and an "Actions ▾" menu — visible across every detail section, not
  just Overview.
- **Actions menu** (new shared `ActionsMenuButton.qml`): per-status content
  (`Edit organization` + divider + the transitions valid from the current
  status), with the whole menu omitted for ARCHIVED since no transition out
  of it is valid.
- **Edit/Create**: reconfirmed lifecycle-free (the "Enabled" checkbox removed
  earlier stays removed; new structural tests assert neither command
  dataclass can carry a lifecycle field going forward).
- **Confirmations**: Deactivate and Archive route through the existing shared
  `App.Controls.ConfirmationDialog`, with wording matched to actual backend
  behavior (see §6-7 below); Activate applies immediately with toast-style
  feedback, per the spec's lower-risk guidance.
- **Bulk actions**: routed through the existing `bulk_activate_organizations`
  / `bulk_deactivate_organizations` / `bulk_archive_organizations` service
  methods (one UnitOfWork per batch, not a loop); an invalid mixed selection
  fails the whole batch with a clear error rather than partially applying.
- **Docs**: `component-guidelines.md` gained a new "§35 Entity Lifecycle
  State" section documenting the reusable pattern, with Organization named
  as the reference implementation.

## 2. Files touched

**New:**
- `src/ui_qml/shared/qml/App/Widgets/ActionsMenuButton.qml` — shared "Actions ▾" overflow menu.
- `src/tests/ui_qml/platform/controllers/test_organization_lifecycle_ui_phase_j.py` — new behavioral tests (§9).

**Shared components extended (backward-compatible, opt-in only):**
- `src/ui_qml/shared/qml/App/Widgets/SectionDetailPage.qml` — `statusLabel`/`statusTone`/`subtitleLine`/`menuActions`/`menuTriggerLabel`/`menuActionTriggered`, all inert by default.
- `src/ui_qml/platform/qml/Platform/Components/AdminEntityWorkspace.qml` — `filterContent` default-property passthrough to its internal `TableToolbar`.

**Organization-specific:**
- `src/ui_qml/platform/qml/workspaces/organizations/OrganizationsWorkspacePage.qml`
- `src/ui_qml/platform/qml/workspaces/organizations/AdminOrganizationDetailPage.qml`
- `src/ui_qml/platform/qml/workspaces/organizations/OrganizationsColumnConfig.js`
- `src/ui_qml/platform/presenters/organizations/organization_catalog_presenter.py`
- `src/ui_qml/platform/controllers/organizations/organization_controller.py`
- `src/ui_qml/platform/controllers/organizations/actions.py`
- `src/ui_qml/platform/controllers/overview/admin_console_controller.py` + `signal_binder.py` (facade delegation for the new status-filter property/slot and the three bulk slots)
- `src/ui_qml/platform/view_models/common/workspace.py` — `PlatformWorkspaceActionItemViewModel.status_label` type broadened to `str | dict[str, str]` (backward compatible; every other consumer keeps passing a plain string).

**Tests updated for the new contract:**
- `test_organization_bulk_actions.py`, `test_organization_detail_overview_qml.py`, `test_qml_platform_presenters_catalog_admin.py`, `test_visual_qa_organizations.py`.

## 3. List — ERP reference design

Columns are now `Organization | Code | Status | Country / Location` visible
by default (city/country-code/legal-name/etc. remain available, hidden by
default, via the existing column customizer — never removed). `Country /
Location` merges city + country into one string server-side (presenter), not
two separate always-visible columns, per "do not overload the table."

**Deferred, not built this phase (documented deviation):** SITES and
EMPLOYEES count columns, and an UPDATED timestamp column. Both need new
backend surface — a batched per-tenant Sites/Employees count reader (no
existing primitive returns counts for many organizations in one query; doing
it per-row would be an N+1 query pattern) and a net-new `updated_at` column
+ migration (no timestamp exists on `Organization` today). Neither is
required by the acceptance checklist in the closeout spec; both are real,
bounded follow-up work, not silently dropped scope.

The status filter (`Status: All/Active/Inactive/Archived`) is a plain
`AppControls.ComboBox` placed in `AdminEntityWorkspace`'s toolbar via the new
`filterContent` slot, wired end-to-end to `list_organizations_page(status=...)`
— confirmed server-side (not a client-side re-filter) by
`test_status_filter_is_applied_server_side`.

Status tone is explicit and presenter-owned:
`{"label": "Active", "tone": "success"}` / `{"label": "Inactive", "tone":
"neutral"}` / `{"label": "Archived", "tone": "neutral"}`. `DataTable`/
`StatusChip` already special-cased this `{label, tone}` shape before this
phase (see `data_table_model.py`'s `_to_display` — the comment there
literally names this as the intended mechanism); Organization is simply the
first consumer to use it for a master-data list, since `PlatformWorkspaceAction
ItemViewModel.status_label`'s type was widened (`str | dict[str, str]`) to
allow it without touching the many other consumers still passing plain
strings.

## 4. Detail header

`SectionDetailPage` (shared by ~10 Platform admin entities) gained the
`statusLabel`/`statusTone`/`subtitleLine`/`menuActions` opt-in properties
described in §1, all defaulting to empty/inert. Every other consumer was
re-verified unchanged (§10). Organization Detail is the reference/pilot
consumer; the pattern is documented in `component-guidelines.md §35` for
future entities to adopt the same way.

## 5. Actions menu

`ActionsMenuButton.qml` (new, generic, modeled on the existing
`NavOverflowMenu` accessibility pattern — anchored popup, `Accessible.role:
Accessible.MenuItem`, full keyboard activation) renders:

- ACTIVE: `Edit organization` / ── / `Deactivate organization` / `Archive organization`
- INACTIVE: `Edit organization` / ── / `Activate organization` / `Archive organization`
- ARCHIVED: the whole menu trigger is **omitted** — the backend's own
  transition guard (`OrganizationService._require_valid_organization_
  transition`) accepts zero transitions out of ARCHIVED, so there is nothing
  valid to offer; showing a menu whose only content duplicates the
  standalone Edit button would be a "disabled fake command" in spirit.

**Intentional deviation from the literal spec mockup:** the spec's §2 mockup
shows a standalone `[Edit]` button next to `[Actions ▾]`, while §3's mockup
shows `Edit organization` as the *first line inside* the Actions menu. Both
are implemented (the standalone button, so Edit stays a one-click action;
plus the same command inside the menu, so a keyboard/menu-first user reaches
it there too) rather than guessing which one was meant to be dropped.

Enabled/disabled state on every item reflects `canWrite` (the existing
`settings.manage` permission check), never invented client-side policy —
QML mirrors the backend's transition table for UX quality only; the backend
re-validates unconditionally on every call.

## 6. Deactivate confirmation

```
Deactivate organization?

Acme Germany GmbH will no longer be available for new operational activity.
Existing records and historical information will remain available according
to permissions. If this organization is currently selected, the active
organization context will be cleared.

[Cancel] [Deactivate organization]
```

Matches actual backend behavior: `deactivate_organization` clears the
caller's active-organization context via `TenantContextService` when the
transition target isn't ACTIVE (verified in the earlier backend phase); it
does not touch Sites/Departments/Employees, so the dialog makes no claim
about them.

## 7. Archive confirmation

```
Archive organization?

Acme Germany GmbH will be removed from normal operational use and retained
for historical reference. This action cannot be reversed through the normal
Organization workspace. Existing business history will be preserved.

[Cancel] [Archive organization]
```

"Cannot be reversed" is verified against the actual transition guard:
`_require_valid_organization_transition` rejects every transition where the
current status is ARCHIVED, unconditionally — archive is a true terminal
state today, not a UI approximation of one.

Both dialogs reuse the existing `App.Controls.ConfirmationDialog` — no new
dialog component was built — and are wired identically from three call
sites: the list's `InspectorPanel` quick action, the list's bulk action bar,
and the detail page's Actions menu.

## 8. Activate

Applies immediately (no confirmation), consistent with "lower risk" —
`activateOrganization`/`bulkActivateOrganizations` call straight through
with success-toast feedback via the existing `run_mutation` pattern already
used by every other admin mutation in this codebase.

## 9. Tests

**New this phase** (`test_organization_lifecycle_ui_phase_j.py`, all passing):
- `test_status_filter_is_applied_server_side`
- `test_status_label_carries_explicit_presenter_owned_tone`
- `test_bulk_archive_routes_through_the_canonical_bulk_service_method` (incl. the terminal-state rejection case)
- `test_provision_and_update_commands_carry_no_lifecycle_field` (structural — asserts the field doesn't exist, not just that it's unused)

**Extended** (`test_organization_detail_overview_qml.py`, all passing):
- `test_active_organization_header_badge_and_actions_menu`
- `test_inactive_organization_actions_menu_offers_activate_not_deactivate`
- `test_archived_organization_has_no_lifecycle_actions_in_the_menu`
- `test_detail_page_loads_with_no_console_errors_for_every_lifecycle_status` — real QML-engine load per status, scanning Qt's message handler for ReferenceError/TypeError/unknown-icon-name. **This test caught a real bug during this phase**: the header rework called an undefined `_joinNonEmpty()` (a helper that existed in the list page but was never defined in the detail page) — a property-only assertion would have missed it, since QML silently leaves a failed binding at its default (empty string) instead of raising. Fixed by adding the same local helper to the detail page.

**Fixed (pre-existing, now-stale test expectations from the earlier backend migration)**: two more stray `statusLabel == "Enabled"/"Active"` string assertions surfaced by the wider regression run below (`test_qml_platform_presenters_catalog_admin.py`, and the bulk-actions payload-based `applyBulkOrganizationStatus` calls) — both updated to the current contract.

**Regression, this phase (all passing unless noted):**
- `src/tests/ui_qml/platform/*` + `src/tests/ui_qml/shell/*`: 502/502
- `src/tests/ui_qml/shared/test_qml_status_chip_consumers_load.py`: 24/24 (proves the `SectionDetailPage` extension didn't regress any of its other ~10 consumers)
- `src/tests/platform/application` + `domain` + `infrastructure`: 950/954 — **4 pre-existing failures, confirmed unrelated**: `test_admin_overview_shows_real_breakdown_cards_not_placeholder`, `test_admin_overview_never_lists_full_employee_collection`, `test_admin_overview_never_lists_full_master_data_collections`, `test_admin_overview_user_metrics_match_rollup_not_full_list` — all four fail on a missing `"Users"` key in the Admin Overview's "Identity And Workforce" section, in code this phase never touched (`admin_console_controller.py`'s diff is additive-only: new organization-status-filter property/slot and three bulk-action slots, nothing in `adminOverview()`/`_overview_presenter`). Two of these four were already flagged as pre-existing in the prior (backend) phase's closeout.
- `test_visual_qa_organizations.py`: 2/2 (light + dark), extended this phase with mixed-status and status-filtered captures (§10).

## 10. Responsive / visual QA — mechanism and method

Reused the existing scene-graph offscreen-capture harness
(`test_visual_qa_organizations.py`, the same `grabToImage()`-against-a-real-
window mechanism as Phase I's navigation shell QA) rather than building a
new one. Captured: page 1 at three breakpoints (1600×1000, 1366×768, narrow
1000×800) × two themes; page 2 (pagination); a no-results empty state; a
mixed-status row set (one Active + one Inactive + one Archived organization
together); and an Archived-only filtered view — 14 PNGs total, light + dark.

**Findings:**
- No clipping, overlap, or collision at any breakpoint in either theme. At
  the narrow breakpoint the lower-priority columns (Country/Location)
  correctly hide via the existing `hideBelow` mechanism while Organization/
  Code/Status/toolbar/pagination remain fully usable — no unusable
  compression.
- The Active row's StatusChip renders with a distinctly different
  (green-toned) border/fill than the Inactive and Archived rows in both
  themes — the intended tone differentiation is visually present even
  before considering label text. Inactive and Archived correctly render
  identically to each other (both `neutral`), matching the spec's own
  suggested semantics, not a missed distinction.
- **Known, pre-existing environment limitation (same one Phase I documented
  and left as a test-environment gap, not a shell defect)**: the `offscreen`
  QPA platform on this machine has zero registered font families, so every
  `Text`/`Label` renders as empty space — exact wording, truncation
  behavior, and text-driven layout (e.g. the header's `CODE · Location`
  line) could not be pixel-verified this way. That content is instead
  covered by the passing string-assertion tests in §9 (`_headerSubtitle`,
  `_orgStatus`, menu item labels), which check exact text, not rendered
  pixels.
- **Not captured as screenshots this phase**: the Organization Detail page
  (header badge/menu) and the Deactivate/Archive confirmation dialogs. Both
  were instead verified through real QML-engine loads with per-status
  property assertions and zero-console-error scans (§9) — a narrower but
  still real verification, not a claim of pixel-level visual QA for those
  two surfaces. Extending the screenshot harness to drive row-selection and
  dialog-open state was judged lower value than the property/console-error
  tests already covering the exact same logic, given the font-rendering gap
  above would limit what a screenshot of them could additionally prove.

## 11. Accessibility

- `ActionsMenuButton` items carry `Accessible.role: Accessible.MenuItem`,
  `Accessible.name` from the item label, and `Return`/`Enter`/`Space`
  keyboard activation — the same contract as the pre-existing
  `NavOverflowMenu` it was modeled on.
- The lifecycle badge is a `StatusChip`: status is communicated by visible
  text ("Active"/"Inactive"/"Archived") plus tone/color together, never
  color alone.
- `ConfirmationDialog` (reused, not new) already names the destructive
  action explicitly on its confirm button (`"Deactivate organization"` /
  `"Archive organization"`, not a generic "Confirm"), and is a modal
  `Popup`, which Qt Quick Controls already gives standard focus-trap/restore
  behavior.
- Table rows and the status-filter `ComboBox` use existing, already-
  accessible shared controls (`DataTable`, `AppControls.ComboBox`) — no new
  custom input widget was introduced for keyboard users to relearn.

## 12. Acceptance checklist

1. List uses Active/Inactive/Archived consistently — ✅
2. Status filtering works server-side — ✅ (`test_status_filter_is_applied_server_side`)
3. Detail header communicates lifecycle clearly — ✅ (badge + code/location line)
4. No Enabled checkbox/toggle remains — ✅ (reconfirmed; structural test added)
5. Lifecycle commands live in Actions — ✅
6. Confirmation dialogs correctly describe real consequences — ✅ (wording matched to verified backend behavior, §6-7)
7. Create/Edit forms cannot accidentally modify lifecycle — ✅ (structural test: the field doesn't exist on either command)
8. Current-context invalidation works after deactivate/archive — ✅ (backend behavior, reconfirmed; not re-implemented in QML)
9. Switchers contain only operationally eligible organizations — ✅ (existing `TenantContextService`/switcher tests, unchanged this phase)
10. Historical inactive/archived organizations remain admin-visible — ✅ (status filter defaults to "All"; only excluded from the *switcher*, never from the admin list)
11. Activity/Audit use the new lifecycle vocabulary — ✅ (backend, already verified in the prior phase's test suite — not re-implemented here)
12. Responsive/light/dark QA — ✅ for the list (§10); detail page/dialogs verified by property + console-error assertions rather than screenshots (§10, documented limitation)
13. Shared components remain canonical — ✅ (`SectionDetailPage`/`AdminEntityWorkspace` extended in place, opt-in only; `ActionsMenuButton` is a new *shared* widget, not an Organization-specific one)
14. Relevant tests are green — ✅ (§9), with 4 confirmed-pre-existing/unrelated failures documented, not hidden

## 13. Explicit non-scope this phase

- No backend lifecycle architecture change (per the closeout instruction) — confirmed zero production changes outside `src/ui_qml/*`.
- Sites/Employees count columns and an Updated-timestamp column — deferred, needs new backend read/schema surface (§3).
- A repo-wide `admin["metrics"]`/"Identity And Workforce" bug — pre-existing, unrelated, left untouched (§9).
