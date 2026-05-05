from __future__ import annotations

import ast
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
UI_QML_ROOT = SRC_ROOT / "ui_qml"
CORE_ROOT = SRC_ROOT / "core"
LEGACY_PLATFORM_MODULE_TAB = SRC_ROOT / "ui" / "platform" / "workspaces" / "admin" / "modules" / "tab.py"
LEGACY_PLATFORM_ORGANIZATION_TAB = (
    SRC_ROOT / "ui" / "platform" / "workspaces" / "admin" / "organizations" / "tab.py"
)
LEGACY_PLATFORM_SITE_TAB = SRC_ROOT / "ui" / "platform" / "workspaces" / "admin" / "sites" / "tab.py"
LEGACY_PLATFORM_DEPARTMENT_TAB = (
    SRC_ROOT / "ui" / "platform" / "workspaces" / "admin" / "departments" / "tab.py"
)
LEGACY_PLATFORM_EMPLOYEE_TAB = (
    SRC_ROOT / "ui" / "platform" / "workspaces" / "admin" / "employees" / "tab.py"
)
LEGACY_PLATFORM_USER_TAB = SRC_ROOT / "ui" / "platform" / "workspaces" / "admin" / "users" / "tab.py"
LEGACY_PLATFORM_DOCUMENT_TAB = (
    SRC_ROOT / "ui" / "platform" / "workspaces" / "admin" / "documents" / "tab.py"
)
LEGACY_PLATFORM_PARTY_TAB = SRC_ROOT / "ui" / "platform" / "workspaces" / "admin" / "parties" / "tab.py"
LEGACY_PLATFORM_ACCESS_TAB = SRC_ROOT / "ui" / "platform" / "workspaces" / "admin" / "access" / "tab.py"
LEGACY_PLATFORM_APPROVAL_TAB = (
    SRC_ROOT / "ui" / "platform" / "workspaces" / "control" / "approvals" / "tab.py"
)
LEGACY_PLATFORM_APPROVAL_QUEUE = (
    SRC_ROOT / "ui" / "platform" / "workspaces" / "control" / "approvals" / "queue.py"
)
LEGACY_PLATFORM_AUDIT_TAB = SRC_ROOT / "ui" / "platform" / "workspaces" / "control" / "audit" / "tab.py"
LEGACY_PLATFORM_HOME_TAB = SRC_ROOT / "ui" / "shell" / "platform" / "home.py"
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


def test_qmllint_no_longer_reports_qobject_controller_member_warnings() -> None:
    qmllint_path = shutil.which("pyside6-qmllint")
    if qmllint_path is None:
        return

    import_paths = [
        str(UI_QML_ROOT / "shared" / "qml"),
        str(UI_QML_ROOT / "shell" / "qml"),
        str(UI_QML_ROOT / "platform" / "qml"),
        str(UI_QML_ROOT / "modules" / "project_management" / "qml"),
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
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "TaskEditorDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "ProjectManagement" / "Dialogs" / "TaskProgressDialog.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "timesheets" / "TimesheetsWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "timesheets" / "TimesheetsToolbarSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "timesheets" / "TimesheetsEntriesSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "timesheets" / "TimesheetsReviewSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "dashboard" / "DashboardWorkspacePage.qml",
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


def test_legacy_platform_modules_tab_uses_desktop_api_boundary() -> None:
    text = LEGACY_PLATFORM_MODULE_TAB.read_text(encoding="utf-8", errors="ignore")

    assert "PlatformRuntimeDesktopApi" in text
    assert "PlatformRuntimeApplicationService" not in text
    assert "_platform_runtime_application_service" not in text


def test_legacy_platform_organizations_tab_uses_desktop_api_boundary() -> None:
    text = LEGACY_PLATFORM_ORGANIZATION_TAB.read_text(encoding="utf-8", errors="ignore")

    assert "PlatformRuntimeDesktopApi" in text
    assert "PlatformRuntimeApplicationService" not in text
    assert "OrganizationService" not in text
    assert "_organization_service" not in text


def test_legacy_platform_home_uses_desktop_api_boundary() -> None:
    text = LEGACY_PLATFORM_HOME_TAB.read_text(encoding="utf-8", errors="ignore")

    assert "PlatformRuntimeDesktopApi" in text
    assert "PlatformRuntimeApplicationService" not in text
    assert "_platform_runtime_application_service" not in text


def test_legacy_platform_sites_tab_uses_desktop_api_boundary() -> None:
    text = LEGACY_PLATFORM_SITE_TAB.read_text(encoding="utf-8", errors="ignore")

    assert "PlatformSiteDesktopApi" in text
    assert "SiteService" not in text
    assert "_site_service" not in text


def test_legacy_platform_departments_tab_uses_desktop_api_boundary() -> None:
    text = LEGACY_PLATFORM_DEPARTMENT_TAB.read_text(encoding="utf-8", errors="ignore")

    assert "PlatformDepartmentDesktopApi" in text
    assert "PlatformSiteDesktopApi" in text
    assert "DepartmentService" not in text
    assert "SiteService" not in text
    assert "_department_service" not in text
    assert "_site_service" not in text


def test_legacy_platform_employees_tab_uses_desktop_api_boundary() -> None:
    text = LEGACY_PLATFORM_EMPLOYEE_TAB.read_text(encoding="utf-8", errors="ignore")

    assert "PlatformEmployeeDesktopApi" in text
    assert "PlatformDepartmentDesktopApi" in text
    assert "PlatformSiteDesktopApi" in text
    assert "EmployeeService" not in text
    assert "DepartmentService" not in text
    assert "SiteService" not in text
    assert "_employee_service" not in text
    assert "_department_service" not in text
    assert "_site_service" not in text


def test_legacy_platform_users_tab_uses_desktop_api_boundary() -> None:
    text = LEGACY_PLATFORM_USER_TAB.read_text(encoding="utf-8", errors="ignore")

    assert "PlatformUserDesktopApi" in text
    assert "AuthService" not in text
    assert "_auth_service" not in text


def test_legacy_platform_documents_tab_uses_desktop_api_boundary() -> None:
    text = LEGACY_PLATFORM_DOCUMENT_TAB.read_text(encoding="utf-8", errors="ignore")

    assert "PlatformDocumentDesktopApi" in text
    assert "DocumentService" not in text
    assert "_document_service" not in text


def test_legacy_platform_parties_tab_uses_desktop_api_boundary() -> None:
    text = LEGACY_PLATFORM_PARTY_TAB.read_text(encoding="utf-8", errors="ignore")

    assert "PlatformPartyDesktopApi" in text
    assert "PartyService" not in text
    assert "_party_service" not in text


def test_legacy_platform_access_tab_uses_desktop_api_boundary() -> None:
    text = LEGACY_PLATFORM_ACCESS_TAB.read_text(encoding="utf-8", errors="ignore")

    assert "PlatformAccessDesktopApi" in text
    assert "PlatformUserDesktopApi" in text
    assert "AccessControlService" not in text
    assert "AuthService" not in text
    assert "_access_service" not in text
    assert "_auth_service" not in text


def test_legacy_platform_approvals_tab_uses_desktop_api_boundary() -> None:
    tab_text = LEGACY_PLATFORM_APPROVAL_TAB.read_text(encoding="utf-8", errors="ignore")
    queue_text = LEGACY_PLATFORM_APPROVAL_QUEUE.read_text(encoding="utf-8", errors="ignore")

    assert "PlatformApprovalDesktopApi" in tab_text
    assert "ApprovalService" not in tab_text
    assert "_approval_service" not in tab_text
    assert "PlatformApprovalDesktopApi" in queue_text
    assert "ApprovalService" not in queue_text
    assert "_approval_service" not in queue_text


def test_legacy_platform_audit_tab_uses_desktop_api_boundary() -> None:
    text = LEGACY_PLATFORM_AUDIT_TAB.read_text(encoding="utf-8", errors="ignore")

    assert "PlatformAuditDesktopApi" in text
    assert "AuditService" not in text
    assert "ProjectService" not in text
    assert "TaskService" not in text
    assert "ResourceService" not in text
    assert "CostService" not in text
    assert "BaselineService" not in text
    assert "_audit_service" not in text
    assert "_project_service" not in text
