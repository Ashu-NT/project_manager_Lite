# Phase K — Organization Workspace — Inspector Enterprise Upgrade Report

Sequence: Sites → Departments → Employees → Documents → **Inspector redesign** → scoped-routing fix → combined regression/visual QA/docs. This report covers the **Organizations list Inspector** only (the panel shown when a row is selected in the Organizations list, before opening the full Detail page) — the fifth step of the agreed sequence. Nothing here touches Organization Overview, Organization lifecycle rules, or any of the four entity tabs already delivered.

## 1. Scope and approach

The spec's Inspector redesign asked for: **Identity / Lifecycle / Location / Key Statistics / Business Context** metadata groups, a compact **~340–420px** panel width, and an **`[Open Details]` primary + `[Edit]`/`[Actions ▾]` secondary** action hierarchy.

`InspectorPanel.qml` (`App.Widgets`) is a **shared** component used by nine other workspace pages across Platform and Project Management (Sites, Departments, Employees, Documents, Users, Parties, Calendars, PM Projects/Resources/Tasks/Scheduling/Timesheet-Review). Redesigning its default rendering would have silently changed the look of every one of those pages — well outside this phase's approved scope (Organization Detail + Organizations list only). Instead, every new capability was added as an **opt-in** property that defaults to the exact prior behavior:

- `groups` (new, opt-in) — an array of `{title, rows: [{label, value}]}` groups, rendered *instead of* the flat `sections` list when non-empty. Every existing consumer keeps passing `sections` and renders exactly as before.
- `panelWidth` (new, opt-in, defaults to the existing shared `Theme.AppTheme.inspectorWidth` = 288px) — lets one consumer request a wider panel without moving the shared token (and therefore without resizing every other workspace's inspector).
- `viewDetailsPrimary` (new, opt-in, defaults to `false`) — promotes the existing "View Details" action to a full-width primary button at the top, with "Edit" demoted to a secondary button sharing the row below with a new `menuActions`-driven "Actions ▾" overflow menu. Default `false` preserves the exact prior layout (Edit primary, an optional single secondary quick-action beside it, View Details as its own secondary row below).
- `menuActions` / `menuTriggerLabel` / `menuActionTriggered` (new, opt-in) — reuses the same `{id, label, icon, danger, enabled, separator}` item shape and the same `ActionsMenuButton` component already used by `SectionDetailPage`'s header menu (Phase K's Sites/Departments/Employees/Documents detail pages, and the pre-existing Organization Detail header). Empty by default, so no other consumer gains a menu button it didn't ask for.

Only `OrganizationsWorkspacePage.qml` sets any of these new properties. Every other `InspectorPanel` consumer's QML is completely untouched.

## 2. What changed in `OrganizationsWorkspacePage.qml`

- **`_inspectorSections` (flat array) replaced by `_inspectorGroups`** (grouped array), with the exact five spec-named groups:
  - **Identity**: Code, Legal Name, Registration Number, Tax / VAT ID.
  - **Lifecycle**: Status (the organization's 3-state ACTIVE/INACTIVE/ARCHIVED value, read from the same `statusLabel` the header StatusChip already uses). No lifecycle *timestamps* exist on the `Organization` domain model (`created_at`/`activated_at`/`deactivated_at`/`archived_at` were all checked and confirmed absent) — per "report gaps, don't invent," this group intentionally stays a single row rather than fabricating history the backend doesn't track.
  - **Location**: Address, City / Postal / Country, Timezone.
  - **Key Statistics**: Sites / Departments / Employees / Documents counts — unchanged from the prior flat layout's real aggregate-query values (`organizationDetailContext`, the same call Organization Detail's Overview uses); `"0"` is still shown as real information, never hidden.
  - **Business Context**: Base Currency, Email, Phone, Website.
  - A group with every row empty (e.g. Business Context before any contact details are filled in) hides itself entirely, exactly matching the prior per-row hide-when-empty behavior, just applied one level up.
- **`_inspectorLifecycleMenuItems`** — the same rule already implemented in `AdminOrganizationDetailPage.qml`'s header menu: Active → Deactivate + Archive; Inactive → Activate + Archive; Archived → empty (a terminal state per `OrganizationService._require_valid_organization_transition` — no lifecycle items are offered-and-then-rejected).
- **`_onInspectorMenuAction(actionId)`** routes `deactivate`/`archive` through the existing `_requestSingleLifecycleConfirm()` confirmation dialog (unchanged — these remain confirmable actions, not immediate mutations) and `activate` straight through to `workspaceController.activateOrganization()` (unchanged from the prior single quick-action button's behavior).
- The `InspectorPanel` instance now sets `panelWidth: 380` (mid-point of the spec's 340–420px range), `groups: root._inspectorGroups`, `viewDetailsPrimary: true` with `viewDetailsLabel: "Open Details"`, and `menuActions: root._canWrite ? root._inspectorLifecycleMenuItems : []` — replacing the old single `secondaryActionLabel`/`showSecondaryAction` quick-action (which only ever offered one of Deactivate *or* Activate at a time) with the full Actions ▾ menu.

## 3. Tests (all passing)

`src/tests/ui_qml/platform/presenters/test_organizations_inspector_enterprise_upgrade.py` (2/2, real `QQmlApplicationEngine` load against a fully-wired `PlatformWorkspaceCatalog`, no mocks):
- `test_inspector_renders_grouped_layout_compact_width_and_lifecycle_menu` — selects a real organization, asserts the five groups appear in the correct order with correct field values (including real `"0"` aggregate counts for a brand-new organization), and that the Actions menu correctly offers exactly `["deactivate", "archive"]` for an Active organization.
- `test_inspector_menu_action_deactivate_and_archive_route_through_confirmation` — invokes `_onInspectorMenuAction("deactivate")` directly (the same call `ActionsMenuButton.onActionSelected` makes) and confirms it opens the confirmation dialog (`_pendingConfirm` populated) rather than mutating the organization immediately — the organization's status is re-read from `organization_service.list_organizations()` and confirmed still `"active"`.

## 4. Regression

- `src/tests/ui_qml/shared` (the `InspectorPanel.qml` component's own module, plus every other shared-widget test): **146/146** passing — confirms the additive changes don't disturb any other `InspectorPanel` consumer.
- `test_qml_status_chip_consumers_load.py`: **24/24** — every workspace page that renders a StatusChip (including all `InspectorPanel` consumers) still loads cleanly.
- `test_pm_r4_2_projects_inspector.py` (Project Management's own Inspector usage): **2/2** — confirms the shared-component change is safe for PM too, not just Platform.
- `test_qml_inspector_panel_swallows_own_clicks.py`: **3/3** — the panel's own click-handling behavior (unrelated to this redesign) is unaffected.
- `test_qml_platform_presenters_catalog_admin.py`, `test_visual_qa_organizations.py`, `test_organization_bulk_actions.py`, `test_organization_lifecycle_ui_phase_j.py`: **40/40** — confirms the Organizations list's own bulk actions, lifecycle dialogs, and visual QA screenshots are unaffected by the Inspector's internal restructuring.
- Full `src/tests/ui_qml/platform` batch: run as part of this step's closeout (result reported in the follow-up message).

## 5. Acceptance status

Identity / Lifecycle / Location / Key Statistics / Business Context groups ✅ · groups hide when fully empty, individual rows hide when empty (unchanged behavior) ✅ · compact 340–420px width (380px), scoped to Organizations only ✅ · `[Open Details]` primary + `[Edit]`/`[Actions ▾]` secondary hierarchy ✅ · Actions ▾ menu reuses the existing lifecycle rule and confirmation dialogs, no new mutation paths ✅ · zero visual/behavioral change to any of the other nine `InspectorPanel` consumers (Sites/Departments/Employees/Documents/Users/Parties/Calendars/PM workspaces), verified by regression, not merely by inspection ✅ · real end-to-end QML-engine tests, not mocks ✅.

Not yet done (by design, sequenced next): the Related Actions / Key Statistics / Inspector-metrics scoped-routing fix (so these all navigate to Organization Detail's own scoped tabs instead of global Platform workspaces), then the combined regression/visual-QA/documentation pass across the whole phase.
