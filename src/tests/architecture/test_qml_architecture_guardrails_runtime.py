from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from src.tests.path_rewrites import REPO_ROOT


ROOT = REPO_ROOT
SRC_ROOT = ROOT / "src"
UI_QML_ROOT = SRC_ROOT / "ui_qml"
LEGACY_SRC_UI_ROOT = SRC_ROOT / "ui"
LEGACY_TOPLEVEL_UI_ROOT = ROOT / "ui"


def test_qmllint_no_longer_reports_qobject_controller_member_warnings() -> None:
    qmllint_path = shutil.which("pyside6-qmllint")
    if qmllint_path is None:
        return

    import_paths = [
        str(UI_QML_ROOT / "shared" / "qml"),
        str(UI_QML_ROOT / "shell" / "qml"),
        str(UI_QML_ROOT / "platform" / "qml"),
        str(UI_QML_ROOT / "modules" / "project_management" / "qml"),
        str(UI_QML_ROOT / "modules" / "inventory_procurement" / "qml"),
        str(UI_QML_ROOT / "modules" / "maintenance" / "qml"),
    ]

    targets = [
        UI_QML_ROOT / "platform" / "qml" / "workspace" / "PlatformWorkspacePage.qml",
        UI_QML_ROOT / "platform" / "qml" / "identity_access" / "access" / "AccessSecurityPanel.qml",
        UI_QML_ROOT / "platform" / "qml" / "documents" / "DocumentDetailPanel.qml",
        UI_QML_ROOT / "platform" / "qml" / "documents" / "dialogs" / "DocumentLinkEditorDialog.qml",
        UI_QML_ROOT / "platform" / "qml" / "documents" / "dialogs" / "DocumentStructureEditorDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "projects" / "ProjectsWorkspacePage.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/projects/dialogs"
        / "ProjectEditorDialog.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/projects/dialogs"
        / "ProjectStatusDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "financials" / "FinancialsWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "financials" / "panels" / "FinancialsDetailPanel.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "financials" / "sections" / "FinancialsActualsSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "financials" / "dialogs" / "FinancialsDialogHost.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/financials/dialogs"
        / "ManualActualEditorDialog.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/financials/dialogs"
        / "ActualLifecycleDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "resources" / "ResourcesWorkspacePage.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/resources/dialogs"
        / "ResourceEditorDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "register" / "RegisterWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "collaboration" / "CollaborationWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "PortfolioWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "sections" / "PortfolioGovernanceToolbar.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "sections" / "PortfolioSummaryCard.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "tabs" / "ExecutiveTab.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "tabs" / "HeatmapTab.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "tabs" / "IntakeTab.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "tabs" / "ScenariosTab.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "tabs" / "CapacityTab.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "tabs" / "DependenciesTab.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/register/dialogs"
        / "RegisterEntryEditorDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "scheduling" / "SchedulingWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "scheduling" / "SchedulingCalendarSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "scheduling" / "SchedulingBaselineSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksAssignmentsSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksBulkActionsSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksCollaborationSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksDependenciesSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksDialogHost.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/sections/TasksTimeEntriesSection.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskAssignmentEditorDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskAssignmentPlannedHoursDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskAssignmentResponseDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskCollaborationComposerDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskCommentDeleteDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskDependencyEditorDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskEditorDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskProgressDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "timesheets" / "TimesheetsWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "timesheets" / "TimesheetsToolbarSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "timesheets" / "TimesheetsEntriesSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "timesheets" / "TimesheetsReviewSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "dashboard" / "DashboardWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "pricing" / "PricingWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "pricing" / "PricingFiltersSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "pricing" / "PricingExportsSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "pricing" / "PricingStockSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "pricing" / "PricingSupplierPricingSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "dashboard" / "DashboardWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "dashboard" / "DashboardFiltersSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "planner" / "PlannerWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "planner" / "PlannerFiltersSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "reliability" / "ReliabilityWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "reliability" / "ReliabilityFiltersSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "assets" / "AssetsWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "assets" / "AssetsFiltersSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "assets" / "AssetLibraryCatalogSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "assets" / "AssetLibraryDetailSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "assets" / "AssetsDialogHost.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "Maintenance" / "Dialogs" / "LocationEditorDialog.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "Maintenance" / "Dialogs" / "SystemEditorDialog.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "Maintenance" / "Dialogs" / "AssetEditorDialog.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "Maintenance" / "Dialogs" / "ComponentEditorDialog.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_requests" / "WorkRequestsWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_requests" / "WorkRequestsFiltersSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_requests" / "WorkRequestsCatalogSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_requests" / "WorkRequestDetailSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_requests" / "WorkRequestsDialogHost.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "Maintenance" / "Dialogs" / "WorkRequestEditorDialog.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "Maintenance" / "Dialogs" / "WorkRequestStatusDialog.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_orders" / "WorkOrdersWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_orders" / "WorkOrdersFiltersSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_orders" / "WorkOrdersCatalogSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_orders" / "WorkOrderDetailSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_orders" / "WorkOrdersDialogHost.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveMetricsSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveDetailSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveQueueSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventivePlansSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveTemplatesSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveDialogHost.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "Maintenance" / "Dialogs" / "WorkOrderEditorDialog.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "Maintenance" / "Dialogs" / "WorkOrderStatusDialog.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "Maintenance" / "Dialogs" / "PreventivePlanEditorDialog.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "Maintenance" / "Dialogs" / "PreventivePlanTaskEditorDialog.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "Maintenance" / "Dialogs" / "TaskTemplateEditorDialog.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "Maintenance" / "Dialogs" / "TaskStepTemplateEditorDialog.qml",
    ]

    command = [qmllint_path]
    for import_path in import_paths:
        command.extend(["-I", import_path])

    command.extend(str(path) for path in targets)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(ROOT),
    )

    output = "\n".join(part for part in (result.stdout, result.stderr) if part)

    assert 'type "QObject"' not in output, output


def test_project_management_portfolio_heatmap_search_and_paging_are_controller_owned() -> None:
    # R3.4: the Heatmap browse (search/page/pageSize) is now server-paginated
    # (see PortfolioService.list_portfolio_heatmap_page) and lives in its own
    # tab component rather than inline on the workspace page.
    heatmap_tab_path = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "portfolio"
        / "tabs"
        / "HeatmapTab.qml"
    )
    state_path = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "portfolio"
        / "PortfolioWorkspaceState.qml"
    )

    heatmap_tab_text = heatmap_tab_path.read_text(encoding="utf-8", errors="ignore")
    state_text = state_path.read_text(encoding="utf-8", errors="ignore")

    assert "setHeatmapSearchText" in heatmap_tab_text
    assert "setHeatmapPage(" in heatmap_tab_text
    assert "setHeatmapPageSize(" in heatmap_tab_text
    assert "pagedHeatmapRows" not in heatmap_tab_text
    assert "heatmapAllRows" not in state_text
    assert "pagedHeatmapRows" not in state_text


def test_platform_standalone_pages_clear_workspace_messages_on_context_switch() -> None:
    # R5.9: the old monolithic AdminConsolePage.qml (deleted -- its facade
    # retirement gate is documented in routes.py) called a single
    # `_clearWorkspaceMessages()` helper >=4 times across its 9 sections'
    # context switches. That responsibility is now distributed across the
    # 10 standalone Platform pages it used to host (R4's 6 + R5's 4) --
    # each clears its own controller's messages when closing its detail
    # view, which is the same underlying behavior this test always
    # verified, just no longer countable in one file.
    page_paths = [
        UI_QML_ROOT / "platform" / "qml" / "organization" / "organizations" / "OrganizationsWorkspacePage.qml",
        UI_QML_ROOT / "platform" / "qml" / "organization" / "sites" / "SitesWorkspacePage.qml",
        UI_QML_ROOT / "platform" / "qml" / "organization" / "departments" / "DepartmentsWorkspacePage.qml",
        UI_QML_ROOT / "platform" / "qml" / "organization" / "employees" / "EmployeesWorkspacePage.qml",
        UI_QML_ROOT / "platform" / "qml" / "organization" / "parties" / "PartiesWorkspacePage.qml",
        UI_QML_ROOT / "platform" / "qml" / "calendars" / "CalendarsWorkspacePage.qml",
        UI_QML_ROOT / "platform" / "qml" / "identity_access" / "users" / "UsersWorkspacePage.qml",
        UI_QML_ROOT / "platform" / "qml" / "documents" / "DocumentsWorkspacePage.qml",
        UI_QML_ROOT / "platform" / "qml" / "documents" / "DocumentStructuresWorkspacePage.qml",
        UI_QML_ROOT / "platform" / "qml" / "identity_access" / "access" / "AccessWorkspacePage.qml",
    ]

    for page_path in page_paths:
        text = page_path.read_text(encoding="utf-8", errors="ignore")
        assert "clearMessages()" in text, f"{page_path.name} does not clear workspace messages"


def test_financials_dialog_host_checks_the_real_mutation_result_contract() -> None:
    # run_mutation() (src/ui_qml/modules/project_management/controllers/common/
    # mutation_runner.py) returns {"ok": bool, "message": str}. The dialog
    # host must check those exact keys — checking "success"/"error" instead
    # left every mutation dialog unable to detect success, so it never closed
    # and always showed a spurious error even when the backend succeeded.
    host_path = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "financials"
        / "dialogs"
        / "FinancialsDialogHost.qml"
    )
    text = host_path.read_text(encoding="utf-8", errors="ignore")

    assert "result.ok" in text
    assert "result.success" not in text
    assert "result.error" not in text


def test_project_management_dashboard_load_is_qml_driven_and_selector_sync_is_guarded() -> None:
    controller_path = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "controllers"
        / "dashboard"
        / "dashboard_workspace_controller.py"
    )
    refresh_mixin_path = controller_path.with_name("dashboard_refresh_mixin.py")
    page_path = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "dashboard"
        / "DashboardWorkspacePage.qml"
    )
    selection_bar_path = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "dashboard"
        / "sections"
        / "DashboardSelectionBar.qml"
    )

    controller_text = controller_path.read_text(encoding="utf-8", errors="ignore")
    refresh_mixin_text = refresh_mixin_path.read_text(encoding="utf-8", errors="ignore")
    page_text = page_path.read_text(encoding="utf-8", errors="ignore")
    selection_bar_text = selection_bar_path.read_text(encoding="utf-8", errors="ignore")

    init_block = controller_text.split("def __init__", 1)[1].split("@Property", 1)[0]

    assert "self.refresh()" not in init_block
    assert "def load(self) -> None:" in controller_text
    assert "self._has_loaded = False" in controller_text
    assert "self._is_refreshing = False" in controller_text
    assert "def _request_domain_refresh(self) -> None:" in refresh_mixin_text
    assert "Component.onCompleted: {" in page_text
    assert "root.ensureLoaded()" in page_text
    assert "Qt.callLater(root.ensureLoaded)" in page_text
    assert "root.workspaceController.load()" in page_text
    assert "property bool syncingSelection: false" in selection_bar_text
    assert "currentIndex: root.indexForValue" not in selection_bar_text
    assert "if (projectCombo.syncingSelection)" in selection_bar_text
