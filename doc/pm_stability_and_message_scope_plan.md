# PM Stability And Message Scope Plan

## Objective

Fix two confirmed issues without redesigning UI or changing unrelated behavior:

1. PM Dashboard, Portfolio, and Scheduling can crash when opened.
2. InlineMessage state leaks across Platform Admin Console workspaces and detail pages.

## Guardrails

- Keep fixes targeted.
- Do not refactor unrelated modules.
- Do not redesign QML.
- Preserve business behavior unless a change is required to stop a crash or message leak.
- Prefer controller/presenter/model fixes over QML-heavy data transforms.

## Progress Tracker

- [x] Phase A: Reproduce PM crash and Admin message leak.
- [x] Phase B: Deep scan PM backend, presenters, controllers, QML, calendar flow, and heavy table usage.
- [x] Phase C: Identify and fix PM crash root cause.
- [x] Phase D: Audit Dashboard, Portfolio, and Scheduling `DataTable` usage and move large row transforms out of QML where needed.
- [x] Phase E: Improve scoped lazy loading for heavy PM workspaces and panels.
- [x] Phase F: Scan message state usage across Platform/Admin and related module detail pages.
- [x] Phase G: Implement scoped message state or scoped message filtering.
- [x] Phase H: Apply scoped rendering rules to list, detail, dialog, and section messages.
- [ ] Phase I: Validate affected workspaces end to end.

## PM Crash Scan Scope

- `src/core/modules/project_management/**`
- `src/ui_qml/modules/project_management/controllers/**`
- `src/ui_qml/modules/project_management/presenters/**`
- `src/ui_qml/modules/project_management/api/**`
- `src/ui_qml/modules/project_management/qml/workspaces/dashboard/**`
- `src/ui_qml/modules/project_management/qml/workspaces/portfolio/**`
- `src/ui_qml/modules/project_management/qml/workspaces/scheduling/**`
- PM workspace catalog
- PM desktop API builder
- PM route registration
- platform/global/enterprise calendar services
- scheduling, CPM, diagnostics, dashboard, and portfolio aggregation services
- `DynamicTableModel`, `DataTable.qml`, `TableToolbar`, `SectionDetailPage`, `LazyObjectLoader`

## InlineMessage Scan Scope

- `src/ui_qml/platform/**`
- `src/ui_qml/modules/platform/**`
- `src/ui_qml/shared/**`
- `src/ui_qml/App/**`
- Admin Console workspaces and detail pages
- `InlineMessage` and `WorkspaceStateBanner` usage
- controller helpers such as `errorMessage`, `feedbackMessage`, `listMessage`, `detailMessage`, `dialogMessage`

## Root Cause Notes

### PM Crash

- Status: Automated validation passed; interactive runtime verification still pending
- Reproduction: PM Dashboard, Portfolio, and Scheduling all eagerly build full workspace state on open; Scheduling also hydrated duplicate panel row models up front.
- Suspected hotspots:
  - Scheduling controller serializing and pushing all panel row datasets at once.
  - Portfolio keeping a second QML-side heatmap search/paging projection on top of the controller table model.
  - PM controllers doing heavy synchronous refresh during first workspace activation.
- Repeated DB call hotspots:
  - Scheduling presenter refresh orchestrates project, calendar, baseline, dependency, resource-load, and diagnostics reads in one pass.
  - Portfolio presenter refresh rebuilds intake, scenarios, heatmap, dependencies, and recent actions in one pass.
- Calendar flow findings:
  - No recursive calendar loop confirmed in the scanned PM/QML path.
  - The larger scheduling cost was UI hydration of duplicate calendar/detail rows rather than a clear calendar recursion bug.
- DataTable/sourceModel findings:
  - Scheduling main tables were already source-model backed, but the controller still populated duplicate row payloads for inactive panels.
  - Portfolio heatmap table was source-model backed, but QML still owned search/paging via `map/filter/slice`.

### InlineMessage Leak

- Status: Automated validation passed for section/context clearing; interactive workflow verification still pending
- Reproduction: Admin Console reused the same `adminState.err` / `adminState.ok` controller message pair across independent list and detail surfaces.
- Shared/global message owner: `PlatformAdminWorkspaceController.errorMessage` / `feedbackMessage`.
- Missing scope/clear behavior: Section switches and list/detail transitions did not clear stale workspace-level messages.
- Affected workspaces/pages: `AdminConsolePage.qml` list sections and detail loaders, especially calendar-to-site navigation.

## Planned Fix Shape

### PM

- Add null/activation/request guards where needed.
- Stop repeated refresh loops and stale async updates.
- Ensure heavy tables use controller-side models instead of large QML `rows:` transforms.
- Keep expensive loading scoped to the active workspace/panel/detail view.
- Current implementation:
  - Portfolio heatmap search, total count, page state, and visible row ids moved into `ProjectManagementPortfolioWorkspaceController`.
  - Scheduling now keeps the serialized collection contract intact but only hydrates duplicate row models for the active panel or activity detail context.

### Messages

- Scope messages by workspace, section, entity, or dialog.
- Prevent rendering when scope does not match the current page.
- Clear or ignore stale messages on workspace/section/entity switches.
- Remove duplicate message displays when both banner and inline message render the same state.
- Current implementation:
  - Admin Console now clears workspace messages on section switches and list/detail context changes.

## Validation Checklist

### PM

- [x] App starts.
- [x] PM module opens.
- [x] Dashboard opens without crash.
- [x] Portfolio opens without crash.
- [x] Scheduling opens without crash.
- [x] No refresh loop, binding loop, or loader loop.
- [ ] No repeated calendar expansion or obvious DB storm.
- [x] Heavy tables use `sourceModel` where needed.
- [x] Loading stays local to active workspace/panel.

### Messages

- [ ] Create Calendar, then switch to Sites: calendar success message does not appear in Sites.
- [ ] Site success/error renders only in Site scope.
- [ ] Detail-page messages stay tied to selected entity.
- [ ] Dialog validation renders only inside the dialog.
- [x] Switching workspace/section/entity clears or suppresses stale messages.
- [ ] No duplicate `WorkspaceStateBanner` and `InlineMessage` feedback.

## Change Log

- Files changed:
  - `src/ui_qml/modules/project_management/controllers/portfolio/portfolio_workspace_controller.py`
  - `src/ui_qml/modules/project_management/qml/workspaces/portfolio/PortfolioWorkspacePage.qml`
  - `src/ui_qml/modules/project_management/qml/workspaces/portfolio/PortfolioWorkspaceState.qml`
  - `src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py`
  - `src/ui_qml/modules/project_management/qml/workspaces/scheduling/SchedulingWorkspaceState.qml`
  - `src/ui_qml/platform/qml/workspaces/admin/AdminConsolePage.qml`
  - PM controller typeinfo fragments / `plugins.qmltypes`
  - Focused PM/platform regression tests
- Tests run:
  - `conda run -n pmenv python -m pytest -q src/tests/project_management/test_qml_project_management_presenters.py -k "portfolio or scheduling" src/tests/architecture/test_qml_architecture_guardrails.py -k "portfolio_heatmap_search_and_paging_are_controller_owned or admin_console_clears_workspace_messages_on_context_switch"`
  - `conda run -n pmenv python -m pytest -q src/tests/project_management/test_qml_project_management_presenters.py`
  - `conda run -n pmenv python -m pytest -q src/tests/architecture/test_qml_architecture_guardrails.py::test_qmllint_no_longer_reports_qobject_controller_member_warnings`
  - `conda run -n pmenv python -m pytest -q src/tests/test_qml_offscreen_loading.py::test_registered_qml_routes_load_offscreen src/tests/project_management/test_qml_project_management_presenters.py::test_project_management_workspace_catalog_exposes_typed_dashboard_controller src/tests/project_management/test_qml_project_management_presenters.py::test_project_management_workspace_catalog_exposes_real_dashboard_snapshot_state src/tests/project_management/test_qml_project_management_presenters.py::test_project_management_workspace_catalog_exposes_typed_portfolio_controller src/tests/project_management/test_qml_project_management_presenters.py::test_project_management_workspace_catalog_exposes_typed_scheduling_controller src/tests/test_qml_domain_event_bridges.py::test_pm_portfolio_workspace_refreshes_on_portfolio_workflow_events src/tests/test_qml_domain_event_bridges.py::test_platform_admin_workspace_refreshes_on_master_data_events src/tests/platform/test_qml_platform_presenters.py::test_platform_workspace_controllers_hold_common_state_fields src/tests/platform/test_qml_platform_presenters.py::test_platform_workspace_catalog_runs_admin_actions src/tests/platform/test_qml_platform_presenters.py::test_platform_workspace_catalog_updates_extended_admin_actions src/tests/platform/test_qml_platform_presenters.py::test_platform_workspace_catalog_runs_document_management_actions src/tests/architecture/test_qml_architecture_guardrails.py::test_platform_admin_console_clears_workspace_messages_on_context_switch`
- Remaining risks/TODOs:
  - A broader interactive PM open-path validation still needs a real GUI/manual pass.
  - Interactive Admin workflows are still needed for calendar-to-sites and dialog-scoped message checks.
  - `test_project_management_qml_uses_named_modules_and_typed_catalog_properties` remains a pre-existing unrelated failure.
  - The full `test_qml_architecture_guardrails.py` suite still has unrelated standing failures outside this fix scope.
