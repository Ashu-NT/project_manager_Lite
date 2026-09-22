# Phase K — Organization Workspace — Scoped Routing Fix Report

Sequence: Sites → Departments → Employees → Documents → Inspector redesign → **scoped-routing fix** → combined regression/visual QA/docs. This is the sixth and final code-scope step: Related Actions and Key Statistics on Organization Detail's Overview must route to *this organization's own* Sites/Departments/Employees/Documents tab, never to the global, session-active-organization-only Platform workspace.

## 1. The bug, traced precisely

`OrganizationOverviewSection.qml`'s Key Statistics tiles (`OverviewMetricTile.onActivated`) and Related Actions tiles (`ActionTile.onActivated`) both emit the same single `navigateToDestination(destinationId)` signal with one of exactly four ids: `"sites"`, `"departments"`, `"employees"`, `"documents"`.

Before this fix, `AdminOrganizationDetailPage.qml` forwarded that signal completely unmodified up to its own `navigateToDestination` signal, which `OrganizationsWorkspacePage.qml` forwarded again unmodified, which `PlatformWorkspacePage.qml` handled with `root._selectDestination(destinationId)` → `platformCatalog.selectDestination(destinationId)` — the **global** Platform destination switch. Concretely: clicking the "Sites" tile while looking at Organization Detail for organization A would navigate *away* from Organization Detail entirely, into the standalone, tenant-wide Sites workspace scoped to whichever organization is the caller's *session-active* one -- silently showing organization B's sites if B, not A, happened to be active. Even when A is the active organization, the click still abandons the "I am looking at organization A's detail page" context instead of simply switching this page's own Sites tab. This matches the phase spec's explicit closing instruction: "Do not hardcode navigation policy into individual QML buttons... Related Actions/Key Statistics/Inspector metrics should route to Organization-Detail-scoped tabs, not global Platform workspaces."

## 2. The fix

`AdminOrganizationDetailPage.qml` (the orchestrator) now intercepts the Overview section's `navigateToDestination` signal:

```qml
readonly property var _sectionIndexByDestination: ({
    "sites": 1, "departments": 2, "employees": 3, "documents": 4
})
function _navigateFromOverview(destinationId) {
    const index = detailRoot._sectionIndexByDestination[destinationId]
    if (index !== undefined) {
        detailPage.scrollToSection(index)
        return
    }
    detailRoot.navigateToDestination(destinationId)
}
```

wired in place of the old direct pass-through:

```qml
onNavigateToDestination: function(destinationId) {
    detailRoot._navigateFromOverview(destinationId)
}
```

`detailPage.scrollToSection(index)` is the same call the section nav rail and Overview's "View all" activity link already use — it updates `activeSectionIndex` **and** keeps the left rail's own highlighted item in sync, exactly matching every other in-page tab switch already in this file. A destination with no local tab of its own still bubbles up through the unchanged `navigateToDestination` signal (verified by the test below with `"control_audit"`, an id genuinely outside this page's own tabs) — the fix scopes the four known child-entity ids specifically, it does not disable cross-workspace navigation from Organization Detail altogether.

This directly follows the "no hardcoded navigation policy in individual buttons" instruction: `OrganizationOverviewSection.qml` itself is completely unchanged — it still just emits a destination id, unaware of what that id means or where it routes. All routing policy lives in one place, the orchestrator, exactly as it already did for every other cross-file signal in this page.

## 3. What this does *not* change

- **The Organizations list Inspector's Key Statistics rows are not clickable, before or after this fix.** They are plain `{label, value}` text rows (see the Inspector redesign report) with no `navigateToDestination` wiring at all — there was no existing "routes to the wrong place" bug to fix there, since nothing routes there today. Making them clickable would be new functionality (turning a static row into an interactive one), not a routing correction, and is out of this step's scope. Flagged here rather than silently left ambiguous.
- Sites/Departments/Employees/Documents tab content, Inspector groups, and every other Phase K deliverable are untouched by this step.
- `_isDestinationAccessible()`'s RBAC gating of which Related Actions tiles even appear is unchanged -- this fix only changes what happens *after* an already-visible, already-permitted tile is clicked.

## 4. Test (passing)

`src/tests/ui_qml/platform/presenters/test_organization_detail_scoped_routing.py` (1/1, real `QQmlApplicationEngine` load against a fully-wired controller, no mocks):
- `test_related_actions_and_key_statistics_switch_the_local_tab_not_global_navigation` — connects a Python listener directly to the real QML `navigateToDestination` signal, then invokes `_navigateFromOverview` (the exact function both Key Statistics and Related Actions tiles call) with each of `"sites"`/`"departments"`/`"employees"`/`"documents"` and confirms: (a) `activeSectionIndex` switches to the correct local tab (1/2/3/4) each time, and (b) the signal listener captures **zero** emissions for any of the four -- proving the fix, not just asserting the tab index changed by coincidence. A final check with `"control_audit"` (a genuinely external id) confirms it still bubbles up normally, proving the fix is scoped correctly rather than disabling the signal outright.

## 5. Regression

- Full `src/tests/ui_qml/platform`: **314/314** passing (run immediately before this fix, with the Inspector redesign already in place) -- confirmed unaffected again after this fix (see the combined regression report for the final post-fix run).
- `test_organization_detail_overview_qml.py`, `test_organization_activity_presentation.py`: unaffected -- Overview's own rendering (fields, statistics, related actions visibility) is untouched, only what a click does downstream changed.
- Same pre-existing, unrelated failure as every prior step: `test_qmllint_no_longer_reports_qobject_controller_member_warnings` (untouched `PlatformWorkspacePage.qml`).

## 6. Acceptance status

Related Actions route to the local tab, not global Platform workspaces ✅ · Key Statistics tiles route to the local tab, not global Platform workspaces ✅ · navigation policy centralized in the orchestrator, not hardcoded into individual buttons (`OrganizationOverviewSection.qml` unchanged) ✅ · non-local destinations still bubble up correctly (verified, not assumed) ✅ · zero change to RBAC gating, tab content, or any other Phase K deliverable ✅ · real end-to-end QML-engine test with a genuine signal-emission assertion, not a mock ✅.

**All six code-scope steps of this phase are now complete**: Sites, Departments, Employees, Documents, Inspector redesign, scoped-routing fix. Remaining: the combined regression / visual QA / documentation pass (step 7).
