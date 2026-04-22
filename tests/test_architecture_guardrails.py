from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

_LARGE_MODULE_BUDGETS = {
    "core/modules/maintenance_management/domain.py": 1517,
    "infra/modules/maintenance_management/db/repository.py": 1488,
    "src/infra/persistence/orm/maintenance/models.py": 1283,
    "tests/test_architecture_guardrails.py": 1280,
    "tests/test_maintenance_ui.py": 1450,
}


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())


def _python_files(root: Path):
    for path in root.rglob("*.py"):
        # Keep architecture checks focused on source/test code, not packaged artifacts.
        if "dist" in path.parts:
            continue
        yield path


def test_no_python_module_exceeds_hard_line_limit():
    offenders = []
    for path in _python_files(ROOT):
        relative_path = str(path.relative_to(ROOT)).replace("\\", "/")
        if relative_path in _LARGE_MODULE_BUDGETS:
            continue
        lines = _line_count(path)
        if lines > 1200:
            offenders.append((relative_path, lines))
    assert not offenders, f"Modules exceed hard 1200-line limit: {offenders}"


def test_core_layer_does_not_import_ui_layer():
    violations: list[tuple[str, str]] = []
    core_root = ROOT / "core"

    for path in _python_files(core_root):
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name == "ui" or name.startswith("ui."):
                        violations.append((str(path.relative_to(ROOT)), name))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "ui" or mod.startswith("ui."):
                    violations.append((str(path.relative_to(ROOT)), mod))

    assert not violations, f"Core layer imports UI layer: {violations}"


def test_shared_platform_and_inventory_do_not_depend_on_pm_identity_helpers():
    forbidden_patterns = (
        "from core.modules.project_management.domain.identifiers import generate_id",
        "from core.modules.project_management.services.common.base import ServiceBase",
    )
    checked_roots = (
        ROOT / "core" / "platform",
        ROOT / "core" / "modules" / "inventory_procurement",
    )
    violations: list[tuple[str, str]] = []

    for root in checked_roots:
        for path in _python_files(root):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for pattern in forbidden_patterns:
                if pattern in text:
                    violations.append((str(path.relative_to(ROOT)), pattern))

    assert not violations, f"Shared platform code depends on PM-only helpers: {violations}"


def test_shared_access_platform_layers_do_not_import_pm_access_code():
    forbidden_import_targets = (
        "core.modules.project_management.access.policy",
        "core.modules.project_management.services.project",
    )
    checked_files = (
        ROOT / "src" / "core" / "platform" / "access" / "application" / "access_control_service.py",
        ROOT / "src" / "ui" / "platform" / "workspaces" / "admin" / "access" / "tab.py",
    )
    violations: list[tuple[str, str]] = []

    for path in checked_files:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_import_targets:
                        violations.append((str(path.relative_to(ROOT)), alias.name))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod in forbidden_import_targets:
                    violations.append((str(path.relative_to(ROOT)), mod))

    assert not violations, f"Shared access platform code imports PM-specific access code: {violations}"


def test_platform_bundle_only_registers_platform_owned_scope_policies():
    platform_bundle_path = ROOT / "infra" / "platform" / "service_registration" / "platform_bundle.py"
    source = platform_bundle_path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)
    forbidden_import_targets = (
        "core.modules.project_management.access.policy",
        "core.modules.inventory_procurement.access.policy",
    )
    violations: list[tuple[str, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in forbidden_import_targets:
                    violations.append((str(platform_bundle_path.relative_to(ROOT)), alias.name))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod in forbidden_import_targets:
                violations.append((str(platform_bundle_path.relative_to(ROOT)), mod))

    assert not violations, f"Platform bundle imports module-owned access policies: {violations}"


def test_module_service_bundles_register_their_owned_scope_policies():
    project_bundle_path = ROOT / "infra" / "platform" / "service_registration" / "project_management_bundle.py"
    inventory_bundle_path = ROOT / "infra" / "platform" / "service_registration" / "inventory_procurement_bundle.py"
    project_text = project_bundle_path.read_text(encoding="utf-8", errors="ignore")
    inventory_text = inventory_bundle_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.access.policy import" in project_text
    assert 'scope_type="project"' in project_text
    assert "from core.modules.inventory_procurement.access.policy import" in inventory_text
    assert 'scope_type="storeroom"' in inventory_text


def test_report_tab_is_coordinator_only():
    tab_path = ROOT / "ui" / "report" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.report.project_flow import ReportProjectFlowMixin" in text
    assert "from ui.modules.project_management.report.actions import ReportActionsMixin" in text
    assert "class KPIReportDialog" not in text
    assert "class GanttPreviewDialog" not in text
    assert "class CriticalPathDialog" not in text
    assert "class ResourceLoadDialog" not in text
    assert "def load_kpis" not in text
    assert "def show_gantt" not in text
    assert "def export_excel" not in text


def test_report_dialogs_module_is_facade_only():
    dialogs_path = ROOT / "ui" / "report" / "dialogs.py"
    text = dialogs_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.report.dialog_kpi import" in text
    assert "from ui.modules.project_management.report.dialog_gantt import" in text
    assert "from ui.modules.project_management.report.dialog_critical_path import" in text
    assert "from ui.modules.project_management.report.dialog_resource_load import" in text
    assert "from ui.modules.project_management.report.dialog_evm import" in text
    assert "from ui.modules.project_management.report.dialog_performance import" in text
    assert "class KPIReportDialog" not in text
    assert "class GanttPreviewDialog" not in text
    assert "class CriticalPathDialog" not in text
    assert "class ResourceLoadDialog" not in text
    assert "class EvmReportDialog" not in text
    assert "class PerformanceVarianceDialog" not in text


def test_report_actions_module_contains_report_workflows():
    actions_path = ROOT / "ui" / "report" / "actions.py"
    text = actions_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.report.dialogs import" in text
    assert "def load_kpis" in text
    assert "def show_gantt" in text
    assert "def show_critical_path" in text
    assert "def show_resource_load" in text
    assert "def show_evm" in text
    assert "def show_performance" in text
    assert "def export_gantt_png" in text
    assert "def export_evm_png" in text
    assert "def export_excel" in text
    assert "def export_pdf" in text


def test_report_project_flow_module_contains_loading_helpers():
    flow_path = ROOT / "ui" / "report" / "project_flow.py"
    text = flow_path.read_text(encoding="utf-8", errors="ignore")

    assert "def _load_projects" in text
    assert "def _current_project_id_and_name" in text


def test_project_tab_is_coordinator_only():
    tab_path = ROOT / "ui" / "project" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.project.dialogs import" in text
    assert "from ui.modules.project_management.project.models import" in text
    assert "from ui.modules.project_management.project.resource_panel import ProjectResourcePanelMixin" in text
    assert "class ProjectEditDialog" not in text
    assert "class ProjectResourcesDialog" not in text
    assert "class ProjectResourceEditDialog" not in text
    assert "class ProjectTableModel" not in text
    assert "self.btn_project_resources" not in text


def test_project_resource_panel_inlines_assignment_controls():
    panel_path = ROOT / "ui" / "project" / "resource_panel.py"
    text = panel_path.read_text(encoding="utf-8", errors="ignore")

    assert "def _build_project_resource_panel" in text
    assert "self._project_resource_table = QTableWidget(0, 6)" in text
    assert "def _on_add_project_resource_inline" in text
    assert "def _on_edit_project_resource_inline" in text
    assert "def _on_toggle_project_resource_inline" in text


def test_project_dialogs_module_is_facade_only():
    dialogs_path = ROOT / "ui" / "project" / "dialogs.py"
    text = dialogs_path.read_text(encoding="utf-8", errors="ignore")

    assert "from .project_edit_dialog import" in text
    assert "from .project_resource_edit_dialog import" in text
    assert "class ProjectEditDialog" not in text
    assert "class ProjectResourceEditDialog" not in text


def test_project_legacy_resource_dialog_modules_removed():
    assert not (ROOT / "ui" / "project" / "project_resource_dialogs.py").exists()
    assert not (ROOT / "ui" / "project" / "project_resources_dialog.py").exists()


def test_task_tab_is_coordinator_only():
    tab_path = ROOT / "ui" / "task" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.task.project_flow import TaskProjectFlowMixin" in text
    assert "from ui.modules.project_management.task.actions import TaskActionsMixin" in text
    assert "from ui.modules.project_management.task.models import" in text
    assert "class TaskEditDialog" not in text
    assert "class TaskProgressDialog" not in text
    assert "class DependencyAddDialog" not in text
    assert "class DependencyListDialog" not in text
    assert "class AssignmentAddDialog" not in text
    assert "class AssignmentListDialog" not in text
    assert "class TaskTableModel" not in text
    assert "def create_task" not in text
    assert "def edit_task" not in text
    assert "def delete_task" not in text
    assert "def manage_dependencies" not in text
    assert "def manage_assignments" not in text
    assert "self.btn_deps" not in text


def test_task_tab_uses_horizontal_splitter_for_right_panel():
    tab_path = ROOT / "ui" / "task" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "self.main_splitter = QSplitter(Qt.Horizontal)" in text
    assert "self.main_splitter.addWidget(self.table)" in text
    assert "self.main_splitter.addWidget(self._assignment_panel)" in text


def test_task_actions_module_contains_task_workflows():
    actions_path = ROOT / "ui" / "task" / "actions.py"
    text = actions_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.task.dialogs import" in text
    assert "def create_task" in text
    assert "def edit_task" in text
    assert "def delete_task" in text
    assert "def update_progress" in text
    assert "def manage_dependencies" in text
    assert "def manage_assignments" in text


def test_task_assignment_panel_includes_inline_dependency_section():
    panel_path = ROOT / "ui" / "task" / "assignment_panel.py"
    dep_panel_path = ROOT / "ui" / "task" / "dependency_panel.py"
    text = panel_path.read_text(encoding="utf-8", errors="ignore")
    dep_text = dep_panel_path.read_text(encoding="utf-8", errors="ignore")

    assert "self.work_tabs = QTabWidget()" in text
    assert 'self.work_tabs.addTab(self._build_assignment_section(), "Assignments")' in text
    assert 'self.work_tabs.addTab(self._build_dependency_section(), "Dependencies")' in text
    assert "self.dependency_table = QTableWidget(0, 5)" in dep_text
    assert "def add_dependency_inline" in dep_text
    assert "def remove_dependency_inline" in dep_text


def test_task_project_flow_module_contains_loading_helpers():
    flow_path = ROOT / "ui" / "task" / "project_flow.py"
    text = flow_path.read_text(encoding="utf-8", errors="ignore")

    assert "def _load_projects" in text
    assert "def _current_project_id" in text
    assert "def reload_tasks" in text
    assert "def _get_selected_task" in text


def test_import_service_is_split_into_package_modules():
    package_dir = ROOT / "core" / "services" / "import_service"
    service_path = package_dir / "service.py"
    init_path = package_dir / "__init__.py"
    support_path = package_dir / "support.py"
    preview_path = package_dir / "preview.py"
    execution_path = package_dir / "execution.py"

    assert package_dir.is_dir()
    assert service_path.exists()
    assert init_path.exists()
    assert support_path.exists()
    assert preview_path.exists()
    assert execution_path.exists()
    assert not (ROOT / "core" / "services" / "import_service.py").exists()


def test_task_dependency_dialogs_module_is_facade_only():
    dialogs_path = ROOT / "ui" / "task" / "dependency_dialogs.py"
    text = dialogs_path.read_text(encoding="utf-8", errors="ignore")

    assert "from .dependency_add_dialog import" in text
    assert "from .dependency_list_dialog import" in text
    assert "from .dependency_shared import" in text
    assert "class DependencyAddDialog" not in text
    assert "class DependencyListDialog" not in text


def test_task_timesheet_dialog_module_is_facade_only():
    dialogs_path = ROOT / "ui" / "task" / "timesheet_dialog.py"
    text = dialogs_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.timesheet.dialog import" in text
    assert "class TimesheetDialog" not in text
    assert "class TimeEntryEditDialog" not in text


def test_timesheet_lifecycle_module_is_facade_only():
    lifecycle_path = ROOT / "core" / "services" / "timesheet" / "lifecycle.py"
    text = lifecycle_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.services.timesheet.entries import" in text
    assert "from core.modules.project_management.services.timesheet.periods import" in text
    assert "from core.modules.project_management.services.timesheet.query import" in text
    assert "from core.modules.project_management.services.timesheet.support import" in text
    assert "class Timesheet" not in text


def test_cost_tab_is_coordinator_only():
    tab_path = ROOT / "ui" / "cost" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.cost.models import" in text
    assert "from ui.modules.project_management.cost.project_flow import" in text
    assert "from ui.modules.project_management.cost.labor_summary import" in text
    assert "from ui.modules.project_management.cost.actions import" in text
    assert "class CostTableModel" not in text
    assert "class CostEditDialog" not in text
    assert "class ResourceLaborDialog" not in text
    assert "class ResourceAssignmentsDialog" not in text


def test_legacy_project_management_component_facades_are_removed():
    assert not (ROOT / "ui" / "cost" / "components.py").exists()
    assert not (ROOT / "ui" / "task" / "components.py").exists()


def test_dashboard_tab_is_coordinator_only():
    tab_path = ROOT / "ui" / "dashboard" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.dashboard.data_ops import" in text
    assert "from ui.modules.project_management.dashboard.portfolio_panel import DashboardPortfolioPanelMixin" in text
    assert "from ui.modules.project_management.dashboard.rendering import" in text
    assert "from ui.modules.project_management.dashboard.control_rail import DashboardControlRailMixin" in text
    assert "from ui.modules.project_management.dashboard.top_bar import DashboardTopBarMixin" in text
    assert "from ui.modules.project_management.dashboard.workqueue_button import DashboardQueueButton" in text
    assert "from ui.modules.project_management.dashboard.widgets import" in text
    assert "class KpiCard" not in text
    assert "class ChartWidget" not in text


def test_dashboard_tab_uses_panel_workspace_layout():
    tab_path = ROOT / "ui" / "dashboard" / "tab.py"
    top_bar_path = ROOT / "ui" / "dashboard" / "top_bar.py"
    control_rail_path = ROOT / "ui" / "dashboard" / "control_rail.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")
    top_bar_text = top_bar_path.read_text(encoding="utf-8", errors="ignore")
    control_rail_text = control_rail_path.read_text(encoding="utf-8", errors="ignore")

    assert "self.panel_scroll = QScrollArea()" in text
    assert "self.panel_grid = QGridLayout(self.panel_canvas)" in text
    assert "workspace_layout = QHBoxLayout(workspace)" in text
    assert "workspace_layout.addWidget(self._build_dashboard_control_sidebar())" in text
    assert "self.summary_widget = self._build_dashboard_top_bar()" in text
    assert "layout.addWidget(self.summary_widget)" in text
    assert "workspace_layout.addWidget(self.panel_scroll, 1)" in text
    assert "self._prepare_conflicts_dialog()" in text
    assert "DashboardQueueButton(\"Conflicts\", active_variant=\"danger\")" in top_bar_text
    assert "DashboardQueueButton(\"Alerts\", active_variant=\"warning\")" in top_bar_text
    assert "DashboardQueueButton(\"Upcoming\", active_variant=\"info\")" in top_bar_text
    assert "self.dashboard_control_stack = QStackedWidget()" in control_rail_text
    assert "self._set_dashboard_controls_collapsed(False)" in control_rail_text


def test_dashboard_rendering_module_is_facade_only():
    rendering_path = ROOT / "ui" / "dashboard" / "rendering.py"
    text = rendering_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.dashboard.rendering_summary import" in text
    assert "from ui.modules.project_management.dashboard.rendering_charts import" in text
    assert "from ui.modules.project_management.dashboard.rendering_evm import" in text
    assert "from ui.modules.project_management.dashboard.rendering_portfolio import" in text
    assert "from ui.modules.project_management.dashboard.rendering_professional import" in text
    assert "def _update_kpis" not in text
    assert "def _update_burndown_chart" not in text
    assert "def _update_evm" not in text
    assert "def _update_professional_panels" not in text


def test_dashboard_summary_rendering_avoids_widget_index_lookups():
    summary_path = ROOT / "ui" / "dashboard" / "rendering_summary.py"
    text = summary_path.read_text(encoding="utf-8", errors="ignore")

    assert "findChildren(" not in text
    assert ".set_value(" in text


def test_dashboard_service_is_orchestrator_only():
    service_path = ROOT / "core" / "services" / "dashboard" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.services.dashboard.alerts import" in text
    assert "from core.modules.project_management.services.dashboard.upcoming import" in text
    assert "from core.modules.project_management.services.dashboard.burndown import" in text
    assert "from core.modules.project_management.services.dashboard.evm import" in text
    assert "from core.modules.project_management.services.dashboard.portfolio import" in text
    assert "from core.modules.project_management.services.dashboard.professional import" in text
    assert "def _build_alerts" not in text
    assert "def _build_upcoming_tasks" not in text
    assert "def _build_burndown" not in text
    assert "def _interpret_evm" not in text
    assert "def _build_milestone_health" not in text


def test_finance_service_is_orchestrator_only():
    service_path = ROOT / "core" / "services" / "finance" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.services.finance.analytics import" in text
    assert "from core.modules.project_management.services.finance.cashflow import" in text
    assert "from core.modules.project_management.services.finance.ledger import" in text
    assert "from core.modules.project_management.services.finance.policy import" in text
    assert "def _manual_labor_raw_totals" not in text
    assert "def _build_cost_item_ledger_rows" not in text
    assert "def _build_computed_labor_plan_rows" not in text
    assert "def _build_computed_labor_actual_rows" not in text
    assert "def _build_source_analytics" not in text
    assert "def _build_dimension_analytics" not in text
    assert "def _build_period_cashflow" not in text


def test_resource_tab_is_coordinator_only():
    tab_path = ROOT / "ui" / "resource" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.resource.flow import ResourceFlowMixin" in text
    assert "from ui.modules.project_management.resource.actions import ResourceActionsMixin" in text
    assert "from ui.modules.project_management.resource.models import" in text
    assert "class ResourceTableModel" not in text
    assert "class ResourceEditDialog" not in text
    assert "def create_resource" not in text
    assert "def edit_resource" not in text
    assert "def delete_resource" not in text
    assert "def toggle_active" not in text


def test_resource_actions_module_contains_resource_workflows():
    actions_path = ROOT / "ui" / "resource" / "actions.py"
    text = actions_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.resource.dialogs import ResourceEditDialog" in text
    assert "def create_resource" in text
    assert "def edit_resource" in text
    assert "def delete_resource" in text
    assert "def toggle_active" in text


def test_resource_flow_module_contains_loading_helpers():
    flow_path = ROOT / "ui" / "resource" / "flow.py"
    text = flow_path.read_text(encoding="utf-8", errors="ignore")

    assert "def reload_resources" in text
    assert "def _get_selected_resource" in text


def test_calendar_tab_is_coordinator_only():
    tab_path = ROOT / "ui" / "calendar" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.modules.project_management.calendar.working_time import" in text
    assert "from ui.modules.project_management.calendar.holidays import" in text
    assert "from ui.modules.project_management.calendar.calculator import" in text
    assert "from ui.modules.project_management.calendar.project_ops import" in text
    assert "def save_calendar" not in text
    assert "def load_holidays" not in text
    assert "def run_calendar_calc" not in text
    assert "def recalc_project_schedule" not in text


def test_support_tab_is_coordinator_only():
    tab_path = ROOT / "src" / "ui" / "platform" / "workspaces" / "admin" / "support" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui.platform.workspaces.admin.support.ui_layout import SupportUiLayoutMixin" in text
    assert "from src.ui.platform.workspaces.admin.support.telemetry import SupportTelemetryMixin" in text
    assert "from src.ui.platform.workspaces.admin.support.update_flow import SupportUpdateFlowMixin" in text
    assert "from src.ui.platform.workspaces.admin.support.diagnostics_flow import SupportDiagnosticsFlowMixin" in text
    assert "def _check_updates" not in text
    assert "def _download_and_install_update" not in text
    assert "def _export_diagnostics" not in text
    assert "def _emit_support_event" not in text


def test_legacy_platform_db_facades_are_removed():
    removed = [
        ROOT / "infra" / "platform" / "db" / "repositories.py",
        ROOT / "infra" / "platform" / "db" / "repositories_org.py",
        ROOT / "infra" / "platform" / "db" / "mappers.py",
    ]

    for path in removed:
        assert not path.exists()


def test_legacy_infra_platform_runtime_package_is_removed():
    assert not (ROOT / "infra" / "platform").exists()

    violations: list[str] = []
    for root in (ROOT / "src", ROOT / "infra" / "modules"):
        for path in _python_files(root):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "from infra.platform" in text or "import infra.platform" in text:
                violations.append(str(path.relative_to(ROOT)))

    assert not violations, f"Runtime code still imports legacy infra.platform: {violations}"


def test_legacy_platform_import_export_packages_are_removed():
    removed = [
        ROOT / "core" / "platform" / "importing",
        ROOT / "core" / "platform" / "exporting",
    ]

    for path in removed:
        assert not path.exists()


def test_legacy_platform_time_package_is_removed():
    assert not (ROOT / "core" / "platform" / "time").exists()


def test_legacy_platform_auth_package_is_removed():
    assert not (ROOT / "core" / "platform" / "auth").exists()


def test_legacy_platform_authorization_package_is_removed():
    assert not (ROOT / "core" / "platform" / "authorization").exists()


def test_legacy_platform_access_package_is_removed():
    assert not (ROOT / "core" / "platform" / "access").exists()


def test_legacy_platform_modules_package_is_removed():
    assert not (ROOT / "core" / "platform" / "modules").exists()


def test_legacy_platform_org_package_is_removed():
    assert not (ROOT / "core" / "platform" / "org").exists()


def test_legacy_platform_party_package_is_removed():
    assert not (ROOT / "core" / "platform" / "party").exists()


def test_legacy_platform_approval_package_is_removed():
    assert not (ROOT / "core" / "platform" / "approval").exists()


def test_legacy_platform_documents_package_is_removed():
    assert not (ROOT / "core" / "platform" / "documents").exists()


def test_legacy_platform_notifications_package_is_removed():
    assert not (ROOT / "core" / "platform" / "notifications").exists()


def test_legacy_platform_audit_package_is_removed():
    assert not (ROOT / "core" / "platform" / "audit").exists()


def test_legacy_platform_common_package_is_removed():
    assert not (ROOT / "core" / "platform" / "common").exists()


def test_legacy_platform_data_exchange_package_is_removed():
    assert not (ROOT / "core" / "platform" / "data_exchange").exists()


def test_legacy_platform_settings_ui_package_is_removed():
    platform_dirs = {path.name for path in (ROOT / "ui" / "platform").iterdir() if path.is_dir()}
    assert "settings" not in platform_dirs


def test_legacy_platform_shared_ui_package_is_removed():
    platform_dirs = {path.name for path in (ROOT / "ui" / "platform").iterdir() if path.is_dir()}
    assert "shared" not in platform_dirs


def test_legacy_platform_control_ui_package_is_removed():
    platform_dirs = {path.name for path in (ROOT / "ui" / "platform").iterdir() if path.is_dir()}
    assert "control" not in platform_dirs


def test_legacy_platform_admin_ui_package_is_removed():
    platform_dirs = {path.name for path in (ROOT / "ui" / "platform").iterdir() if path.is_dir()}
    assert "admin" not in platform_dirs


def test_composition_imports_focused_persistence_adapters():
    repo_path = ROOT / "src" / "infra" / "composition" / "repositories.py"
    text = repo_path.read_text(encoding="utf-8", errors="ignore")

    assert not (ROOT / "src" / "infra" / "persistence" / "db" / "platform").exists()
    assert "from infra.platform.db.repositories import" not in text
    assert "from infra.platform.db.mappers import" not in text
    assert "from src.core.modules.project_management.infrastructure.persistence.repositories.task import" in text
    assert "from src.core.platform.infrastructure.persistence.repositories.auth import" in text
    assert "from src.core.platform.infrastructure.persistence.repositories.org import" in text
    assert "from src.core.platform.infrastructure.persistence.repositories.time import" in text


def test_project_management_persistence_imports_project_management_orm_models():
    assert not (ROOT / "core" / "modules" / "project_management" / "interfaces.py").exists()
    assert not (ROOT / "core" / "modules" / "project_management" / "domain" / "project.py").exists()
    assert not (ROOT / "core" / "modules" / "project_management" / "domain" / "task.py").exists()
    assert not (ROOT / "core" / "modules" / "project_management" / "domain" / "resource.py").exists()
    assert not (ROOT / "core" / "modules" / "project_management" / "domain" / "cost.py").exists()
    assert not (ROOT / "core" / "modules" / "project_management" / "domain" / "calendar.py").exists()
    assert not (ROOT / "core" / "modules" / "project_management" / "domain" / "baseline.py").exists()
    assert not (ROOT / "core" / "modules" / "project_management" / "domain" / "register.py").exists()
    assert not (ROOT / "infra" / "modules" / "project_management" / "db").exists()
    assert not (ROOT / "src" / "infra" / "persistence" / "orm" / "project_management").exists()
    assert not (ROOT / "src" / "core" / "modules" / "project_management" / "infrastructure" / "persistence" / "orm" / "models.py").exists()
    checked_files = [
        ROOT / "src" / "core" / "modules" / "project_management" / "infrastructure" / "persistence" / "repositories" / "project.py",
        ROOT / "src" / "core" / "modules" / "project_management" / "infrastructure" / "persistence" / "repositories" / "task.py",
        ROOT / "src" / "core" / "modules" / "project_management" / "infrastructure" / "persistence" / "repositories" / "resource.py",
        ROOT / "src" / "core" / "modules" / "project_management" / "infrastructure" / "persistence" / "repositories" / "baseline.py",
        ROOT / "src" / "core" / "modules" / "project_management" / "infrastructure" / "persistence" / "repositories" / "cost_calendar.py",
        ROOT / "src" / "core" / "modules" / "project_management" / "infrastructure" / "persistence" / "repositories" / "portfolio.py",
        ROOT / "src" / "core" / "modules" / "project_management" / "infrastructure" / "persistence" / "repositories" / "collaboration.py",
    ]

    for path in checked_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "from src.core.modules.project_management.infrastructure.persistence.orm.models import" not in text
        assert "from src.core.modules.project_management.infrastructure.persistence.orm." in text
        assert "from src.core.modules.project_management.infrastructure.persistence.mappers." in text
        assert "from src.infra.persistence.orm.platform.models import" not in text


def test_inventory_persistence_imports_inventory_orm_models():
    checked_files = [
        ROOT / "infra" / "modules" / "inventory_procurement" / "db" / "repository.py",
        ROOT / "infra" / "modules" / "inventory_procurement" / "db" / "mapper.py",
    ]

    for path in checked_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "from src.infra.persistence.orm.inventory_procurement.models import" in text
        assert "from src.infra.persistence.orm.platform.models import" not in text


def test_orm_package_root_loads_all_model_packages():
    package_path = ROOT / "src" / "infra" / "persistence" / "orm" / "__init__.py"
    migration_env_path = ROOT / "src" / "infra" / "persistence" / "migrations" / "env.py"
    package_text = package_path.read_text(encoding="utf-8", errors="ignore")
    migration_env_text = migration_env_path.read_text(encoding="utf-8", errors="ignore")

    assert not (ROOT / "src" / "infra" / "persistence" / "orm" / "platform").exists()
    assert "from src.infra.persistence.orm.base import Base" in package_text
    assert "import src.infra.persistence.orm.inventory_procurement.models" in package_text
    assert "import src.infra.persistence.orm.maintenance.models" in package_text
    assert "import src.infra.persistence.orm.maintenance.preventive_runtime_models" in package_text
    platform_orm_modules = ("org", "documents", "party", "modules", "time", "auth", "access", "audit", "approval", "runtime_tracking")
    for module in platform_orm_modules:
        assert f"import src.core.platform.infrastructure.persistence.orm.{module}" in package_text
    for module in ("project", "resource", "task", "cost_calendar", "baseline", "register", "collaboration", "portfolio"):
        assert f"import src.core.modules.project_management.infrastructure.persistence.orm.{module}" in package_text
    assert "from src.infra.persistence.orm import Base" in migration_env_text
    assert "import src.infra.persistence.orm" in migration_env_text


def test_legacy_infra_repository_wrappers_are_removed():
    removed = [
        ROOT / "infra" / "modules" / "project_management" / "db" / "repositories_project.py",
        ROOT / "infra" / "modules" / "project_management" / "db" / "repositories_task.py",
        ROOT / "infra" / "modules" / "project_management" / "db" / "repositories_resource.py",
        ROOT / "infra" / "modules" / "project_management" / "db" / "repositories_cost_calendar.py",
        ROOT / "infra" / "modules" / "project_management" / "db" / "repositories_baseline.py",
        ROOT / "infra" / "modules" / "project_management" / "db" / "repositories_register.py",
        ROOT / "infra" / "modules" / "project_management" / "db" / "repositories_timesheet.py",
        ROOT / "infra" / "platform" / "db" / "repositories_approval.py",
        ROOT / "infra" / "platform" / "db" / "repositories_audit.py",
        ROOT / "infra" / "platform" / "db" / "repositories_auth.py",
    ]
    for path in removed:
        assert not path.exists()


def test_legacy_common_models_facade_is_removed():
    assert not (ROOT / "core" / "platform" / "common" / "models.py").exists()
    assert not (ROOT / "core" / "models.py").exists()


def test_shared_theme_module_composes_from_formatting_slices():
    theme_path = ROOT / "src" / "ui" / "shared" / "formatting" / "theme.py"
    text = theme_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui.shared.formatting.theme_stylesheet import" in text
    assert "from src.ui.shared.formatting.theme_tokens import" in text
    assert "def set_theme_mode" in text
    assert "def apply_app_style" in text
    assert "QTableView, QTableWidget" not in text
    assert "LIGHT_THEME = {" not in text
    assert "DARK_THEME = {" not in text


def test_reporting_evm_module_is_facade_only():
    evm_path = ROOT / "core" / "services" / "reporting" / "evm.py"
    text = evm_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.services.reporting.evm_core import" in text
    assert "from core.modules.project_management.services.reporting.evm_series import" in text
    assert "def get_earned_value" not in text
    assert "def get_evm_series" not in text


def test_task_service_is_orchestrator_only():
    service_path = ROOT / "core" / "services" / "task" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.services.task.lifecycle import" in text
    assert "from core.modules.project_management.services.task.dependency import" in text
    assert "from core.modules.project_management.services.task.assignment import" in text
    assert "from core.modules.project_management.services.task.query import" in text
    assert "from core.modules.project_management.services.task.validation import" in text
    assert "def create_task" not in text
    assert "def add_dependency" not in text
    assert "def assign_resource" not in text
    assert "def query_tasks" not in text


def test_auth_service_is_orchestrator_only():
    service_path = ROOT / "src" / "core" / "platform" / "auth" / "application" / "auth_service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.platform.auth.application.auth_query import AuthQueryMixin" in text
    assert "from src.core.platform.auth.application.auth_validation import AuthValidationMixin" in text
    assert "class AuthService(AuthQueryMixin, AuthValidationMixin)" in text
    assert "def get_user_permissions" not in text
    assert "def get_user_role_names" not in text
    assert "def _require_user" not in text
    assert "def _require_role_by_name" not in text
    assert "def _validate_password" not in text
    assert "def _validate_email" not in text
    assert "def _normalize_email" not in text


def test_module_catalog_service_is_orchestrator_only():
    service_path = ROOT / "src" / "core" / "platform" / "modules" / "application" / "module_catalog_service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.platform.modules.application.module_catalog_context import (" in text
    assert "from src.core.platform.modules.application.module_catalog_mutation import (" in text
    assert "from src.core.platform.modules.application.module_catalog_query import ModuleCatalogQueryMixin" in text
    assert "class ModuleCatalogService(" in text
    assert "def list_modules" not in text
    assert "def set_module_state" not in text
    assert "def snapshot" not in text


def test_org_package_exports_services_and_contracts():
    package_path = ROOT / "src" / "core" / "platform" / "org" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.platform.org.application import (" in text
    assert "from src.core.platform.org.contracts import (" in text
    assert "from src.core.platform.org.domain import (" in text
    assert "class OrganizationService" not in text
    assert "class OrganizationRepository" not in text


def test_party_package_exports_service_and_contracts():
    package_path = ROOT / "src" / "core" / "platform" / "party" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.platform.party.application import PartyService" in text
    assert "from src.core.platform.party.contracts import PartyRepository" in text
    assert "from src.core.platform.party.domain import Party, PartyType" in text
    assert "class PartyService" not in text
    assert "class PartyRepository" not in text


def test_approval_package_exports_service_and_contracts():
    package_path = ROOT / "src" / "core" / "platform" / "approval" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.platform.approval.application import ApprovalService" in text
    assert "from src.core.platform.approval.contracts import ApprovalRepository" in text
    assert "from src.core.platform.approval.domain import ApprovalRequest, ApprovalStatus" in text
    assert "from src.core.platform.approval.policy import DEFAULT_GOVERNED_ACTIONS, is_governance_required" in text
    assert "class ApprovalService" not in text
    assert "class ApprovalRepository" not in text


def test_documents_package_exports_services_and_contracts():
    package_path = ROOT / "src" / "core" / "platform" / "documents" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.platform.documents.application import DocumentIntegrationService, DocumentService" in text
    assert "from src.core.platform.documents.contracts import (" in text
    assert "from src.core.platform.documents.domain import (" in text
    assert "class DocumentService" not in text
    assert "class DocumentRepository" not in text


def test_notifications_package_exports_event_hub():
    package_path = ROOT / "src" / "core" / "platform" / "notifications" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.platform.notifications.domain_events import DomainChangeEvent, DomainEvents, domain_events" in text
    assert "from src.core.platform.notifications.signal import Signal" in text
    assert "class DomainEvents" not in text
    assert "class Signal" not in text


def test_audit_package_exports_service_and_contracts():
    package_path = ROOT / "src" / "core" / "platform" / "audit" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.platform.audit.application import AuditService" in text
    assert "from src.core.platform.audit.contracts import AuditLogRepository" in text
    assert "from src.core.platform.audit.domain import AuditLogEntry" in text
    assert "from src.core.platform.audit.helpers import record_audit" in text
    assert "class AuditService" not in text
    assert "class AuditLogRepository" not in text


def test_common_package_exports_shared_utilities():
    package_path = ROOT / "src" / "core" / "platform" / "common" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.platform.common.exceptions import (" in text
    assert "from src.core.platform.common.ids import generate_id" in text
    assert "from src.core.platform.common.service_base import ServiceBase" in text
    assert "class ServiceBase" not in text
    assert "def generate_id" not in text


def test_data_exchange_package_exports_service():
    package_path = ROOT / "src" / "core" / "platform" / "data_exchange" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.platform.data_exchange.service import MasterDataExchangeService, MasterDataExportRequest" in text
    assert "class MasterDataExchangeService" not in text
    assert "class MasterDataExportRequest" not in text


def test_platform_settings_package_exports_store():
    package_path = ROOT / "src" / "ui" / "platform" / "settings" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui.platform.settings.main_window_store import MainWindowSettingsStore" in text
    assert "class MainWindowSettingsStore" not in text


def test_platform_control_workspace_package_exports_tabs():
    package_path = ROOT / "src" / "ui" / "platform" / "workspaces" / "control" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui.platform.workspaces.control.approvals import ApprovalControlTab, ApprovalQueuePanel" in text
    assert "from src.ui.platform.workspaces.control.audit import AuditLogTab" in text
    assert "class ApprovalControlTab" not in text


def test_platform_admin_workspace_package_exports_tabs():
    package_path = ROOT / "src" / "ui" / "platform" / "workspaces" / "admin" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui.platform.workspaces.admin.access import AccessTab" in text
    assert "from src.ui.platform.workspaces.admin.documents import DocumentAdminTab" in text
    assert "from src.ui.platform.workspaces.admin.support import SupportTab" in text
    assert "from src.ui.platform.workspaces.admin.users import UserAdminTab" in text
    assert "class AccessTab" not in text


def test_shared_dialogs_package_exports_dialog_helpers():
    package_path = ROOT / "src" / "ui" / "shared" / "dialogs" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui.shared.dialogs.async_job import (" in text
    assert "from src.ui.shared.dialogs.incident_support import (" in text
    assert "from src.ui.shared.dialogs.login_dialog import LoginDialog" in text
    assert "class LoginDialog" not in text


def test_shared_formatting_package_exports_theme_and_ui_config():
    package_path = ROOT / "src" / "ui" / "shared" / "formatting" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui.shared.formatting.formatting import (" in text
    assert "from src.ui.shared.formatting.theme import (" in text
    assert "from src.ui.shared.formatting.ui_config import CurrencyType, UIConfig" in text
    assert "class UIConfig" not in text


def test_shared_models_package_exports_runtime_helpers():
    package_path = ROOT / "src" / "ui" / "shared" / "models" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui.shared.models.deferred_call import DeferredCall" in text
    assert "from src.ui.shared.models.table_model import horizontal_header_data" in text
    assert "from src.ui.shared.models.undo import UndoCommand, UndoStack" in text
    assert "from src.ui.shared.models.worker_services import (" in text
    assert "class UndoStack" not in text


def test_shared_widgets_package_exports_widget_helpers():
    package_path = ROOT / "src" / "ui" / "shared" / "widgets" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui.shared.widgets.code_generation import CodeFieldWidget, suggest_generated_code" in text
    assert "from src.ui.shared.widgets.combo import current_data, current_data_and_text" in text
    assert "from src.ui.shared.widgets.guards import (" in text
    assert "class CodeFieldWidget" not in text


def test_platform_widgets_package_exports_admin_helpers():
    package_path = ROOT / "src" / "ui" / "platform" / "widgets" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui.platform.widgets.admin_header import build_admin_header" in text
    assert "from src.ui.platform.widgets.admin_surface import (" in text
    assert "from src.ui.platform.widgets.document_preview import (" in text
    assert "class DocumentPreviewWidget" not in text


def test_platform_dialogs_package_exports_admin_and_document_dialogs():
    package_path = ROOT / "src" / "ui" / "platform" / "dialogs" / "__init__.py"
    text = package_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui.platform.dialogs.admin import (" in text
    assert "from src.ui.platform.dialogs.documents import DocumentLinksDialog, DocumentPreviewDialog" in text
    assert "class DocumentPreviewDialog" not in text


def test_platform_common_interfaces_are_platform_only():
    interfaces_path = ROOT / "src" / "core" / "platform" / "common" / "interfaces.py"
    text = interfaces_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.platform.time.contracts import TimeEntryRepository, TimesheetPeriodRepository" in text
    assert "core.modules.project_management" not in text
    assert "class ProjectRepository" not in text
    assert "class TaskRepository" not in text
    assert "class BaselineRepository" not in text
    assert "class ProjectMembershipRepository" not in text
    assert "class ScopedAccessGrantRepository" not in text
    assert "class OrganizationRepository" not in text
    assert "class SiteRepository" not in text
    assert "class DepartmentRepository" not in text
    assert "class EmployeeRepository" not in text
    assert "class ApprovalRepository" not in text
    assert "class AuditLogRepository" not in text


def test_core_platform_does_not_import_module_contracts():
    platform_root = ROOT / "core" / "platform"
    violations: list[tuple[str, str]] = []

    for path in _python_files(platform_root):
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name == "core.modules" or name.startswith("core.modules."):
                        violations.append((str(path.relative_to(ROOT)), name))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "core.modules" or mod.startswith("core.modules."):
                    violations.append((str(path.relative_to(ROOT)), mod))

    assert not violations, f"Core platform layer imports module code directly: {violations}"


def test_project_service_is_orchestrator_only():
    service_path = ROOT / "core" / "services" / "project" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.services.project.lifecycle import ProjectLifecycleMixin" in text
    assert "from core.modules.project_management.services.project.query import ProjectQueryMixin" in text
    assert "def create_project" not in text
    assert "def update_project" not in text
    assert "def delete_project" not in text


def test_cost_service_is_orchestrator_only():
    service_path = ROOT / "core" / "modules" / "project_management" / "services" / "cost" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.services.cost.lifecycle import CostLifecycleMixin" in text
    assert "from core.modules.project_management.services.cost.query import CostQueryMixin" in text
    assert "from core.modules.project_management.services.cost.support import CostSupportMixin" in text
    assert "class CostService(" in text
    assert "def add_cost_item" not in text
    assert "def update_cost_item" not in text
    assert "def delete_cost_item" not in text
    assert "def get_project_cost_summary" not in text


def test_collaboration_service_is_orchestrator_only():
    service_path = ROOT / "core" / "modules" / "project_management" / "services" / "collaboration" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.services.collaboration.comments import CollaborationCommentMixin" in text
    assert "from core.modules.project_management.services.collaboration.inbox import CollaborationInboxMixin" in text
    assert "from core.modules.project_management.services.collaboration.presence import CollaborationPresenceMixin" in text
    assert "from core.modules.project_management.services.collaboration.support import CollaborationSupportMixin" in text
    assert "class CollaborationService(" in text
    assert "def post_comment" not in text
    assert "def list_notifications" not in text
    assert "def list_active_presence" not in text


def test_portfolio_service_is_orchestrator_only():
    service_path = ROOT / "core" / "modules" / "project_management" / "services" / "portfolio" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.services.portfolio.dependencies import PortfolioDependencyMixin" in text
    assert "from core.modules.project_management.services.portfolio.executive import PortfolioExecutiveMixin" in text
    assert "from core.modules.project_management.services.portfolio.intake import PortfolioIntakeMixin" in text
    assert "from core.modules.project_management.services.portfolio.scenarios import PortfolioScenarioMixin" in text
    assert "from core.modules.project_management.services.portfolio.support import PortfolioSupportMixin" in text
    assert "from core.modules.project_management.services.portfolio.templates import PortfolioTemplateMixin" in text
    assert "class PortfolioService(" in text
    assert "def create_intake_item" not in text
    assert "def compare_scenarios" not in text
    assert "def list_portfolio_heatmap" not in text


def test_scheduling_engine_is_orchestrator_only():
    engine_path = ROOT / "core" / "services" / "scheduling" / "engine.py"
    text = engine_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.services.scheduling.graph import build_project_dependency_graph" in text
    assert "from core.modules.project_management.services.scheduling.passes import run_backward_pass, run_forward_pass" in text
    assert "from core.modules.project_management.services.scheduling.results import build_schedule_result" in text
    assert "import heapq" not in text


def test_scheduling_leveling_is_split_from_engine():
    engine_path = ROOT / "core" / "services" / "scheduling" / "engine.py"
    text = engine_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.services.scheduling.leveling_service import ResourceLevelingMixin" in text
    assert "class SchedulingEngine(ResourceLevelingMixin)" in text


def test_main_build_services_delegates_to_service_graph():
    main_path = ROOT / "main.py"
    text = main_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.infra.composition.app_container import build_service_dict" in text
    assert "return build_service_dict(session)" in text


def test_known_large_modules_have_growth_budgets():
    # Guardrail budgets: these files are intentionally large for now, but must not keep growing.
    budgets = {
        **_LARGE_MODULE_BUDGETS,
        "core/modules/project_management/services/reporting/service.py": 180,
        "core/modules/project_management/services/reporting/evm.py": 80,
        "core/modules/project_management/services/reporting/evm_core.py": 280,
        "core/modules/project_management/services/reporting/evm_series.py": 120,
        "core/modules/project_management/services/reporting/kpi.py": 280,
        "core/modules/project_management/services/reporting/labor.py": 260,
        "ui/modules/project_management/project/tab.py": 290,
        "ui/modules/project_management/project/dialogs.py": 80,
        "ui/modules/project_management/project/project_edit_dialog.py": 240,
        "ui/modules/project_management/project/project_resource_edit_dialog.py": 240,
        "ui/modules/project_management/project/models.py": 120,
        "ui/modules/project_management/task/tab.py": 220,
        "ui/modules/project_management/task/actions.py": 260,
        "ui/modules/project_management/task/project_flow.py": 180,
        "ui/modules/project_management/task/dialogs.py": 80,
        "ui/modules/project_management/task/task_dialogs.py": 320,
        "ui/modules/project_management/task/dependency_dialogs.py": 220,
        "ui/modules/project_management/task/dependency_add_dialog.py": 220,
        "ui/modules/project_management/task/dependency_list_dialog.py": 180,
        "ui/modules/project_management/task/dependency_shared.py": 60,
        "ui/modules/project_management/task/assignment_dialogs.py": 270,
        "ui/modules/project_management/task/models.py": 120,
        "ui/modules/project_management/cost/tab.py": 220,
        "ui/modules/project_management/cost/models.py": 180,
        "ui/modules/project_management/cost/cost_dialogs.py": 240,
        "ui/modules/project_management/cost/labor_dialogs.py": 320,
        "ui/modules/project_management/cost/project_flow.py": 200,
        "ui/modules/project_management/cost/labor_summary.py": 200,
        "ui/modules/project_management/cost/actions.py": 170,
        "ui/modules/project_management/dashboard/tab.py": 285,
        "ui/modules/project_management/dashboard/widgets.py": 120,
        "ui/modules/project_management/dashboard/data_ops.py": 180,
        "ui/modules/project_management/dashboard/leveling_ops.py": 230,
        "ui/modules/project_management/dashboard/alerts_panel.py": 140,
        "ui/modules/project_management/dashboard/portfolio_panel.py": 100,
        "ui/modules/project_management/dashboard/rendering.py": 80,
        "ui/modules/project_management/dashboard/rendering_summary.py": 160,
        "ui/modules/project_management/dashboard/rendering_charts.py": 170,
        "ui/modules/project_management/dashboard/rendering_evm.py": 240,
        "ui/modules/project_management/dashboard/rendering_portfolio.py": 120,
        "ui/modules/project_management/report/tab.py": 220,
        "ui/modules/project_management/report/actions.py": 220,
        "ui/modules/project_management/report/project_flow.py": 80,
        "ui/modules/project_management/report/dialogs.py": 50,
        "ui/modules/project_management/report/dialog_helpers.py": 140,
        "ui/modules/project_management/report/dialog_kpi.py": 220,
        "ui/modules/project_management/report/dialog_gantt.py": 240,
        "ui/modules/project_management/report/dialog_critical_path.py": 220,
        "ui/modules/project_management/report/dialog_resource_load.py": 240,
        "src/ui/shared/formatting/theme.py": 80,
        "src/ui/shared/formatting/theme_tokens.py": 140,
        "src/ui/shared/formatting/theme_stylesheet.py": 340,
        "main.py": 580,
        "ui/modules/project_management/calendar/tab.py": 300,
        "ui/modules/project_management/calendar/working_time.py": 120,
        "ui/modules/project_management/calendar/holidays.py": 120,
        "ui/modules/project_management/calendar/calculator.py": 100,
        "ui/modules/project_management/calendar/project_ops.py": 130,
        "src/ui/platform/workspaces/admin/support/tab.py": 80,
        "src/ui/platform/workspaces/admin/support/ui_layout.py": 160,
        "src/ui/platform/workspaces/admin/support/telemetry.py": 140,
        "src/ui/platform/workspaces/admin/support/update_flow.py": 340,
        "src/ui/platform/workspaces/admin/support/diagnostics_flow.py": 140,
        "src/ui/platform/workspaces/admin/support/diagnostics_export.py": 140,
        "src/ui/platform/workspaces/admin/support/incident_report.py": 180,
        "src/ui/shared/dialogs/incident_support.py": 120,
        "core/modules/project_management/services/scheduling/engine.py": 360,
        "core/modules/project_management/services/scheduling/models.py": 80,
        "core/modules/project_management/services/scheduling/graph.py": 180,
        "core/modules/project_management/services/scheduling/passes.py": 260,
        "core/modules/project_management/services/scheduling/results.py": 180,
        "core/modules/project_management/services/scheduling/leveling.py": 180,
        "core/modules/project_management/services/scheduling/leveling_service.py": 280,
        "core/modules/project_management/services/scheduling/leveling_models.py": 120,
        "ui/modules/project_management/resource/tab.py": 245,
        "ui/modules/project_management/resource/actions.py": 180,
        "ui/modules/project_management/resource/flow.py": 80,
        "ui/modules/project_management/resource/models.py": 100,
        "ui/modules/project_management/resource/dialogs.py": 260,
        "core/domain/__init__.py": 70,
        "core/modules/project_management/domain/identifiers.py": 40,
        "core/modules/project_management/domain/enums.py": 90,
        "core/modules/project_management/services/dashboard/service.py": 170,
        "core/modules/project_management/services/dashboard/models.py": 120,
        "core/modules/project_management/services/dashboard/alerts.py": 180,
        "core/modules/project_management/services/dashboard/upcoming.py": 150,
        "core/modules/project_management/services/dashboard/burndown.py": 120,
        "core/modules/project_management/services/dashboard/evm.py": 160,
        "core/modules/project_management/services/dashboard/portfolio.py": 300,
        "core/modules/project_management/services/dashboard/portfolio_models.py": 100,
        "core/modules/project_management/services/finance/service.py": 220,
        "core/modules/project_management/services/finance/ledger.py": 260,
        "core/modules/project_management/services/finance/analytics.py": 160,
        "core/modules/project_management/services/finance/cashflow.py": 120,
        "core/modules/project_management/services/finance/policy.py": 120,
        "core/modules/project_management/services/finance/helpers.py": 120,
        "core/modules/project_management/services/portfolio/dependencies.py": 220,
        "core/modules/project_management/services/portfolio/service.py": 90,
        "core/modules/project_management/services/portfolio/executive.py": 120,
        "core/modules/project_management/services/portfolio/intake.py": 120,
        "core/modules/project_management/services/portfolio/scenarios.py": 240,
        "core/modules/project_management/services/portfolio/support.py": 150,
        "core/modules/project_management/services/portfolio/templates.py": 160,
        "src/ui/shared/formatting/ui_config.py": 320,
        "core/modules/project_management/services/task/service.py": 140,
        "core/modules/project_management/services/project/service.py": 90,
        "core/modules/project_management/services/project/lifecycle.py": 250,
        "core/modules/project_management/services/project/query.py": 90,
        "core/modules/project_management/services/project/validation.py": 80,
        "core/modules/project_management/services/task/lifecycle.py": 315,
        "core/modules/project_management/services/task/dependency.py": 175,
        "core/modules/project_management/services/task/assignment.py": 245,
        "core/modules/project_management/services/task/query.py": 120,
        "core/modules/project_management/services/task/validation.py": 220,
        "core/modules/project_management/services/timesheet/service.py": 90,
        "core/modules/project_management/services/timesheet/lifecycle.py": 40,
        "core/modules/project_management/services/timesheet/query.py": 100,
        "core/modules/project_management/services/timesheet/entries.py": 260,
        "core/modules/project_management/services/timesheet/periods.py": 220,
        "core/modules/project_management/services/timesheet/support.py": 240,
        "core/modules/project_management/services/cost/service.py": 80,
        "core/modules/project_management/services/cost/lifecycle.py": 240,
        "core/modules/project_management/services/cost/query.py": 60,
        "core/modules/project_management/services/cost/support.py": 110,
        "core/modules/project_management/services/collaboration/service.py": 80,
        "core/modules/project_management/services/collaboration/comments.py": 150,
        "core/modules/project_management/services/collaboration/inbox.py": 180,
        "core/modules/project_management/services/collaboration/presence.py": 130,
        "core/modules/project_management/services/collaboration/support.py": 160,
        "src/core/platform/modules/application/module_catalog_service.py": 140,
        "src/core/platform/modules/application/module_catalog_context.py": 100,
        "src/core/platform/modules/application/module_catalog_mutation.py": 190,
        "src/core/platform/modules/application/module_catalog_query.py": 135,
        "src/core/platform/modules/application/authorization.py": 40,
        "src/core/platform/modules/application/guard.py": 45,
        "src/core/platform/modules/domain/module_definition.py": 30,
        "src/core/platform/modules/domain/module_entitlement.py": 80,
        "src/core/platform/modules/domain/subscription.py": 20,
        "src/core/platform/modules/domain/defaults.py": 180,
        "src/core/platform/modules/domain/module_codes.py": 30,
        "src/core/platform/modules/contracts.py": 45,
        "src/core/platform/org/application/organization_service.py": 230,
        "src/core/platform/org/application/site_service.py": 340,
        "src/core/platform/org/application/department_service.py": 410,
        "src/core/platform/org/application/employee_service.py": 220,
        "src/core/platform/org/application/employee_support.py": 200,
        "src/core/platform/org/contracts.py": 140,
        "src/core/platform/org/support.py": 70,
        "src/core/platform/org/access_policy.py": 60,
        "src/core/modules/project_management/infrastructure/persistence/mappers/project.py": 120,
        "src/core/modules/project_management/infrastructure/persistence/repositories/project.py": 140,
        "src/core/modules/project_management/infrastructure/persistence/mappers/task.py": 180,
        "src/core/modules/project_management/infrastructure/persistence/repositories/task.py": 180,
        "src/core/modules/project_management/infrastructure/persistence/mappers/resource.py": 80,
        "src/core/modules/project_management/infrastructure/persistence/repositories/resource.py": 80,
        "src/core/modules/project_management/infrastructure/persistence/mappers/cost_calendar.py": 180,
        "src/core/modules/project_management/infrastructure/persistence/repositories/cost_calendar.py": 180,
        "src/core/modules/project_management/infrastructure/persistence/mappers/baseline.py": 100,
        "src/core/modules/project_management/infrastructure/persistence/repositories/baseline.py": 120,
    }

    breaches = []
    for rel_path, max_lines in budgets.items():
        path = ROOT / rel_path
        lines = _line_count(path)
        if lines > max_lines:
            breaches.append((rel_path, lines, max_lines))

    assert not breaches, f"Large-module budgets exceeded: {breaches}"
