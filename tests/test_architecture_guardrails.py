from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
        lines = _line_count(path)
        if lines > 1200:
            offenders.append((str(path.relative_to(ROOT)), lines))
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


def test_cost_components_module_is_facade_only():
    components_path = ROOT / "ui" / "cost" / "components.py"
    text = components_path.read_text(encoding="utf-8", errors="ignore")

    assert "from .models import" in text
    assert "from .cost_dialogs import" in text
    assert "from .labor_dialogs import" in text
    assert "class CostTableModel" not in text
    assert "class CostEditDialog" not in text
    assert "class ResourceLaborDialog" not in text
    assert "class ResourceAssignmentsDialog" not in text


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
    tab_path = ROOT / "ui" / "support" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.platform.admin.support.ui_layout import SupportUiLayoutMixin" in text
    assert "from ui.platform.admin.support.telemetry import SupportTelemetryMixin" in text
    assert "from ui.platform.admin.support.update_flow import SupportUpdateFlowMixin" in text
    assert "from ui.platform.admin.support.diagnostics_flow import SupportDiagnosticsFlowMixin" in text
    assert "def _check_updates" not in text
    assert "def _download_and_install_update" not in text
    assert "def _export_diagnostics" not in text
    assert "def _emit_support_event" not in text


def test_infra_repositories_module_is_facade_only():
    repo_path = ROOT / "infra" / "db" / "repositories.py"
    text = repo_path.read_text(encoding="utf-8", errors="ignore")

    assert "from infra.platform.db.mappers import" in text
    assert "from infra.modules.project_management.db.repositories_project import" in text
    assert "from infra.modules.project_management.db.repositories_task import" in text
    assert "class SqlAlchemy" not in text


def test_infra_mappers_module_is_facade_only():
    mapper_path = ROOT / "infra" / "db" / "mappers.py"
    text = mapper_path.read_text(encoding="utf-8", errors="ignore")

    assert "from infra.modules.project_management.db.project.mapper import" in text
    assert "from infra.modules.project_management.db.task.mapper import" in text
    assert "from infra.modules.project_management.db.resource.mapper import" in text
    assert "from infra.modules.project_management.db.cost_calendar.mapper import" in text
    assert "from infra.modules.project_management.db.baseline.mapper import" in text
    assert "def project_to_orm" not in text
    assert "def task_to_orm" not in text
    assert "def cost_to_orm" not in text


def test_infra_repository_wrappers_delegate_to_aggregate_folder():
    wrappers = [
        "repositories_project.py",
        "repositories_task.py",
        "repositories_resource.py",
        "repositories_cost_calendar.py",
        "repositories_baseline.py",
    ]
    expected_imports = {
        "repositories_project.py": "from infra.modules.project_management.db.project.repository import",
        "repositories_task.py": "from infra.modules.project_management.db.task.repository import",
        "repositories_resource.py": "from infra.modules.project_management.db.resource.repository import",
        "repositories_cost_calendar.py": "from infra.modules.project_management.db.cost_calendar.repository import",
        "repositories_baseline.py": "from infra.modules.project_management.db.baseline.repository import",
    }
    for name in wrappers:
        text = (ROOT / "infra" / "db" / name).read_text(encoding="utf-8", errors="ignore")
        assert expected_imports[name] in text
        assert "Compatibility wrapper" in text


def test_core_models_module_is_facade_only():
    models_path = ROOT / "core" / "models.py"
    text = models_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.domain.project import" in text
    assert "from core.modules.project_management.domain.task import" in text
    assert "from core.modules.project_management.domain.resource import" in text
    assert "from core.modules.project_management.domain.cost import" in text
    assert "from core.modules.project_management.domain.calendar import" in text
    assert "from core.modules.project_management.domain.baseline import" in text
    assert "class Project(" not in text
    assert "class Task(" not in text
    assert "class Resource(" not in text


def test_theme_module_is_facade_only():
    theme_path = ROOT / "ui" / "styles" / "theme.py"
    text = theme_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.platform.shared.styles.theme_stylesheet import" in text
    assert "from ui.platform.shared.styles.theme_tokens import" in text
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
    service_path = ROOT / "core" / "services" / "auth" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.platform.auth.query import AuthQueryMixin" in text
    assert "from core.platform.auth.validation import AuthValidationMixin" in text
    assert "class AuthService(AuthQueryMixin, AuthValidationMixin)" in text
    assert "def get_user_permissions" not in text
    assert "def get_user_role_names" not in text
    assert "def _require_user" not in text
    assert "def _require_role_by_name" not in text
    assert "def _validate_password" not in text
    assert "def _validate_email" not in text
    assert "def _normalize_email" not in text


def test_project_service_is_orchestrator_only():
    service_path = ROOT / "core" / "services" / "project" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.modules.project_management.services.project.lifecycle import ProjectLifecycleMixin" in text
    assert "from core.modules.project_management.services.project.query import ProjectQueryMixin" in text
    assert "def create_project" not in text
    assert "def update_project" not in text
    assert "def delete_project" not in text


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

    assert "from infra.platform.services import build_service_dict" in text
    assert "return build_service_dict(session)" in text


def test_known_large_modules_have_growth_budgets():
    # Guardrail budgets: these files are intentionally large for now, but must not keep growing.
    budgets = {
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
        "ui/modules/project_management/task/actions.py": 220,
        "ui/modules/project_management/task/project_flow.py": 180,
        "ui/modules/project_management/task/dialogs.py": 80,
        "ui/modules/project_management/task/task_dialogs.py": 320,
        "ui/modules/project_management/task/dependency_dialogs.py": 220,
        "ui/modules/project_management/task/dependency_add_dialog.py": 220,
        "ui/modules/project_management/task/dependency_list_dialog.py": 180,
        "ui/modules/project_management/task/dependency_shared.py": 60,
        "ui/modules/project_management/task/assignment_dialogs.py": 270,
        "ui/modules/project_management/task/models.py": 120,
        "ui/modules/project_management/task/components.py": 80,
        "ui/modules/project_management/cost/tab.py": 220,
        "ui/modules/project_management/cost/components.py": 80,
        "ui/modules/project_management/cost/models.py": 180,
        "ui/modules/project_management/cost/cost_dialogs.py": 240,
        "ui/modules/project_management/cost/labor_dialogs.py": 320,
        "ui/modules/project_management/cost/project_flow.py": 180,
        "ui/modules/project_management/cost/labor_summary.py": 200,
        "ui/modules/project_management/cost/actions.py": 150,
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
        "ui/platform/shared/styles/theme.py": 80,
        "ui/platform/shared/styles/theme_tokens.py": 140,
        "ui/platform/shared/styles/theme_stylesheet.py": 340,
        "main.py": 580,
        "ui/modules/project_management/calendar/tab.py": 300,
        "ui/modules/project_management/calendar/working_time.py": 120,
        "ui/modules/project_management/calendar/holidays.py": 120,
        "ui/modules/project_management/calendar/calculator.py": 100,
        "ui/modules/project_management/calendar/project_ops.py": 130,
        "ui/platform/admin/support/tab.py": 80,
        "ui/platform/admin/support/ui_layout.py": 160,
        "ui/platform/admin/support/telemetry.py": 140,
        "ui/platform/admin/support/update_flow.py": 340,
        "ui/platform/admin/support/diagnostics_flow.py": 140,
        "ui/platform/admin/support/diagnostics_export.py": 140,
        "ui/platform/admin/support/incident_report.py": 180,
        "ui/platform/shared/incident_support.py": 120,
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
        "core/platform/common/models.py": 90,
        "core/domain/__init__.py": 70,
        "core/modules/project_management/domain/identifiers.py": 40,
        "core/modules/project_management/domain/enums.py": 90,
        "core/modules/project_management/domain/project.py": 120,
        "core/modules/project_management/domain/task.py": 180,
        "core/modules/project_management/domain/resource.py": 80,
        "core/modules/project_management/domain/cost.py": 90,
        "core/modules/project_management/domain/calendar.py": 120,
        "core/modules/project_management/domain/baseline.py": 90,
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
        "ui/platform/shared/styles/ui_config.py": 320,
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
        "infra/platform/db/repositories.py": 140,
        "infra/platform/db/mappers.py": 120,
        "infra/modules/project_management/db/project/__init__.py": 80,
        "infra/modules/project_management/db/project/mapper.py": 120,
        "infra/modules/project_management/db/project/repository.py": 140,
        "infra/modules/project_management/db/timesheet/__init__.py": 80,
        "infra/modules/project_management/db/timesheet/mapper.py": 120,
        "infra/modules/project_management/db/timesheet/repository.py": 180,
        "infra/modules/project_management/db/task/__init__.py": 80,
        "infra/modules/project_management/db/task/mapper.py": 180,
        "infra/modules/project_management/db/task/repository.py": 180,
        "infra/modules/project_management/db/resource/__init__.py": 60,
        "infra/modules/project_management/db/resource/mapper.py": 80,
        "infra/modules/project_management/db/resource/repository.py": 80,
        "infra/modules/project_management/db/cost_calendar/__init__.py": 90,
        "infra/modules/project_management/db/cost_calendar/mapper.py": 180,
        "infra/modules/project_management/db/cost_calendar/repository.py": 180,
        "infra/modules/project_management/db/baseline/__init__.py": 60,
        "infra/modules/project_management/db/baseline/mapper.py": 100,
        "infra/modules/project_management/db/baseline/repository.py": 120,
        "infra/modules/project_management/db/repositories_project.py": 100,
        "infra/modules/project_management/db/repositories_task.py": 150,
        "infra/modules/project_management/db/repositories_timesheet.py": 60,
        "infra/modules/project_management/db/repositories_resource.py": 60,
        "infra/modules/project_management/db/repositories_cost_calendar.py": 150,
        "infra/modules/project_management/db/repositories_baseline.py": 100,
    }

    breaches = []
    for rel_path, max_lines in budgets.items():
        path = ROOT / rel_path
        lines = _line_count(path)
        if lines > max_lines:
            breaches.append((rel_path, lines, max_lines))

    assert not breaches, f"Large-module budgets exceeded: {breaches}"
