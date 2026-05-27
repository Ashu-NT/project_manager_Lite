from __future__ import annotations

import ast
from pathlib import Path
import shutil
import subprocess

from src.tests.path_rewrites import REPO_ROOT

ROOT = REPO_ROOT
SRC_ROOT = ROOT / "src"
UI_QML_ROOT = SRC_ROOT / "ui_qml"
CORE_ROOT = SRC_ROOT / "core"
LEGACY_SRC_UI_ROOT = SRC_ROOT / "ui"
LEGACY_TOPLEVEL_UI_ROOT = ROOT / "ui"
PLATFORM_ADMIN_CONSOLE_CONTROLLER = (
    UI_QML_ROOT / "platform" / "controllers" / "admin" / "admin_console_controller.py"
)
STALE_PLATFORM_ADMIN_WORKSPACE_CONTROLLER = (
    UI_QML_ROOT / "platform" / "controllers" / "admin" / "admin_workspace_controller.py"
)


def _python_files(root: Path):
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        yield path


def _imports_from(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    return imports


def test_core_does_not_import_qml_or_widget_ui() -> None:
    violations: list[tuple[str, str]] = []

    for path in _python_files(CORE_ROOT):
        for imported in _imports_from(path):
            if imported == "src.ui_qml" or imported.startswith("src.ui_qml."):
                violations.append((str(path.relative_to(ROOT)), imported))
            if imported == "src.ui" or imported.startswith("src.ui."):
                violations.append((str(path.relative_to(ROOT)), imported))

    assert not violations, f"Core imports UI layers: {violations}"


def test_qml_python_layer_does_not_import_legacy_widget_ui_or_infrastructure() -> None:
    violations: list[tuple[str, str]] = []

    for path in _python_files(UI_QML_ROOT):
        for imported in _imports_from(path):
            if imported == "src.ui" or imported.startswith("src.ui."):
                violations.append((str(path.relative_to(ROOT)), imported))
            if ".infrastructure." in imported or imported.endswith(".infrastructure"):
                violations.append((str(path.relative_to(ROOT)), imported))
            if ".repositories" in imported or imported.endswith(".repositories"):
                violations.append((str(path.relative_to(ROOT)), imported))

    assert not violations, f"QML Python layer imports forbidden layers: {violations}"


def test_qml_python_layer_does_not_use_qt_widgets() -> None:
    violations: list[tuple[str, str]] = []

    for path in _python_files(UI_QML_ROOT):
        for imported in _imports_from(path):
            if imported == "PySide6.QtWidgets" or imported.startswith("PySide6.QtWidgets."):
                violations.append((str(path.relative_to(ROOT)), imported))

    assert not violations, f"QML Python layer imports QtWidgets: {violations}"


def test_module_desktop_apis_do_not_import_qml() -> None:
    violations: list[tuple[str, str]] = []

    for desktop_api_root in CORE_ROOT.glob("modules/*/api/desktop"):
        for path in _python_files(desktop_api_root):
            for imported in _imports_from(path):
                if imported == "src.ui_qml" or imported.startswith("src.ui_qml."):
                    violations.append((str(path.relative_to(ROOT)), imported))

    assert not violations, f"Module desktop APIs import QML: {violations}"


def test_qml_files_do_not_reference_repositories_or_orm() -> None:
    forbidden_snippets = (
        "repository",
        "repositories",
        "sqlalchemy",
        "sessionlocal",
        "infrastructure.persistence",
    )
    violations: list[tuple[str, str]] = []

    for path in UI_QML_ROOT.rglob("*.qml"):
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for snippet in forbidden_snippets:
            if snippet in text:
                violations.append((str(path.relative_to(ROOT)), snippet))

    assert not violations, f"QML files reference persistence concerns: {violations}"


def test_qml_files_do_not_use_parent_relative_imports() -> None:
    violations: list[str] = []

    for path in UI_QML_ROOT.rglob("*.qml"):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="ignore").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if stripped.startswith('import "') and "../" in stripped:
                violations.append(f"{path.relative_to(ROOT)}:{lineno}")

    assert not violations, f"QML files use parent relative imports: {violations}"


def test_qml_workspace_controller_properties_use_typed_controller_types() -> None:
    violations: list[str] = []

    for path in UI_QML_ROOT.rglob("*.qml"):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="ignore").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if not stripped.startswith("property QtObject "):
                continue
            if "controller" in stripped.lower():
                violations.append(f"{path.relative_to(ROOT)}:{lineno}:{stripped}")

    assert not violations, f"QML controller properties still use generic QtObject: {violations}"


def test_project_management_qml_does_not_use_generic_pm_catalog_var_binding() -> None:
    violations: list[str] = []

    for path in (UI_QML_ROOT / "modules" / "project_management").rglob("*.qml"):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="ignore").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if stripped.startswith("property var pmCatalog"):
                violations.append(f"{path.relative_to(ROOT)}:{lineno}:{stripped}")

    assert not violations, f"Project management QML still uses generic pmCatalog bindings: {violations}"


def test_platform_admin_workspace_controller_uses_split_entrypoint() -> None:
    assert PLATFORM_ADMIN_CONSOLE_CONTROLLER.exists()
    assert not STALE_PLATFORM_ADMIN_WORKSPACE_CONTROLLER.exists()


def test_project_management_projects_workspace_no_longer_uses_placeholder_page() -> None:
    projects_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "projects"
        / "ProjectsWorkspace.qml"
    )
    text = projects_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "ProjectsWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_tasks_workspace_no_longer_uses_placeholder_page() -> None:
    tasks_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "tasks"
        / "TasksWorkspace.qml"
    )
    text = tasks_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "TasksWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_scheduling_workspace_no_longer_uses_placeholder_page() -> None:
    scheduling_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "scheduling"
        / "SchedulingWorkspace.qml"
    )
    text = scheduling_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "SchedulingWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_resources_workspace_no_longer_uses_placeholder_page() -> None:
    resources_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "resources"
        / "ResourcesWorkspace.qml"
    )
    text = resources_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "ResourcesWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_financials_workspace_no_longer_uses_placeholder_page() -> None:
    financials_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "financials"
        / "FinancialsWorkspace.qml"
    )
    text = financials_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "FinancialsWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_risk_workspace_no_longer_uses_placeholder_page() -> None:
    risk_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "risk"
        / "RiskWorkspace.qml"
    )
    text = risk_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "RiskWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_register_workspace_no_longer_uses_placeholder_page() -> None:
    register_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "register"
        / "RegisterWorkspace.qml"
    )
    text = register_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "RegisterWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_collaboration_workspace_no_longer_uses_placeholder_page() -> None:
    collaboration_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "collaboration"
        / "CollaborationWorkspace.qml"
    )
    text = collaboration_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "CollaborationWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_portfolio_workspace_no_longer_uses_placeholder_page() -> None:
    portfolio_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "portfolio"
        / "PortfolioWorkspace.qml"
    )
    text = portfolio_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "PortfolioWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_timesheets_workspace_no_longer_uses_placeholder_page() -> None:
    timesheets_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "timesheets"
        / "TimesheetsWorkspace.qml"
    )
    text = timesheets_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "TimesheetsWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_inventory_pricing_workspace_no_longer_uses_placeholder_page() -> None:
    pricing_workspace = (
        UI_QML_ROOT
        / "modules"
        / "inventory_procurement"
        / "qml"
        / "workspaces"
        / "pricing"
        / "PricingWorkspace.qml"
    )
    text = pricing_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "PricingWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_dashboard_workspace_no_longer_uses_placeholder_page() -> None:
    dashboard_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "dashboard"
        / "DashboardWorkspace.qml"
    )
    text = dashboard_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "DashboardWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_assets_workspace_no_longer_uses_placeholder_page() -> None:
    assets_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "assets"
        / "AssetsWorkspace.qml"
    )
    text = assets_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "AssetsWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_reliability_workspace_no_longer_uses_placeholder_page() -> None:
    reliability_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "reliability"
        / "ReliabilityWorkspace.qml"
    )
    text = reliability_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "ReliabilityWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_planner_workspace_no_longer_uses_placeholder_page() -> None:
    planner_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "planner"
        / "PlannerWorkspace.qml"
    )
    text = planner_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "PlannerWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_work_requests_workspace_no_longer_uses_placeholder_page() -> None:
    work_requests_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "work_requests"
        / "WorkRequestsWorkspace.qml"
    )
    text = work_requests_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "WorkRequestsWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_work_orders_workspace_no_longer_uses_placeholder_page() -> None:
    work_orders_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "work_orders"
        / "WorkOrdersWorkspace.qml"
    )
    text = work_orders_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "WorkOrdersWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_preventive_workspace_no_longer_uses_placeholder_page() -> None:
    preventive_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "preventive"
        / "PreventiveWorkspace.qml"
    )
    text = preventive_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "PreventiveWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


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
        UI_QML_ROOT / "platform" / "qml" / "workspaces" / "admin" / "AdminWorkspace.qml",
        UI_QML_ROOT / "platform" / "qml" / "workspaces" / "control" / "ControlWorkspace.qml",
        UI_QML_ROOT / "platform" / "qml" / "workspaces" / "settings" / "SettingsWorkspace.qml",
        UI_QML_ROOT / "platform" / "qml" / "Platform" / "Widgets" / "AccessSecurityPanel.qml",
        UI_QML_ROOT / "platform" / "qml" / "Platform" / "Widgets" / "DocumentDetailPanel.qml",
        UI_QML_ROOT / "platform" / "qml" / "Platform" / "Dialogs" / "DocumentLinkEditorDialog.qml",
        UI_QML_ROOT / "platform" / "qml" / "Platform" / "Dialogs" / "DocumentStructureEditorDialog.qml",
        UI_QML_ROOT / "platform" / "qml" / "workspaces" / "admin" / "AdminSupportSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "projects" / "ProjectsWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "ProjectEditorDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "ProjectStatusDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "financials" / "FinancialsWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "CostItemEditorDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "resources" / "ResourcesWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "ResourceEditorDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "risk" / "RiskWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "register" / "RegisterWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "collaboration" / "CollaborationWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "PortfolioWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "PortfolioToolbarSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "PortfolioIntakeSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "PortfolioTemplatesSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "PortfolioScenariosSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "PortfolioDependenciesSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "PortfolioExecutiveSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "portfolio" / "PortfolioSummaryCard.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "RegisterEntryEditorDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "scheduling" / "SchedulingWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "scheduling" / "SchedulingCalendarSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "scheduling" / "SchedulingBaselineSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksAssignmentsSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksBulkActionsSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksCollaborationSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksDependenciesSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksDialogHost.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksTimeEntriesSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "TaskAssignmentEditorDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "TaskAssignmentHoursDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "TaskCollaborationComposerDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "TaskDependencyEditorDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "TaskEditorDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "TaskProgressDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Widgets" / "TimesheetEntriesCard.qml",
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
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Widgets" / "WorkspacePlaceholderPage.qml",
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


def test_legacy_widget_ui_roots_are_removed() -> None:
    assert not LEGACY_SRC_UI_ROOT.exists()
    assert not LEGACY_TOPLEVEL_UI_ROOT.exists()

