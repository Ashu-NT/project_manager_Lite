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

    assert "from ui.report.project_flow import ReportProjectFlowMixin" in text
    assert "from ui.report.actions import ReportActionsMixin" in text
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

    assert "from ui.report.dialog_kpi import" in text
    assert "from ui.report.dialog_gantt import" in text
    assert "from ui.report.dialog_critical_path import" in text
    assert "from ui.report.dialog_resource_load import" in text
    assert "from ui.report.dialog_evm import" in text
    assert "from ui.report.dialog_performance import" in text
    assert "class KPIReportDialog" not in text
    assert "class GanttPreviewDialog" not in text
    assert "class CriticalPathDialog" not in text
    assert "class ResourceLoadDialog" not in text
    assert "class EvmReportDialog" not in text
    assert "class PerformanceVarianceDialog" not in text


def test_report_actions_module_contains_report_workflows():
    actions_path = ROOT / "ui" / "report" / "actions.py"
    text = actions_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.report.dialogs import" in text
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

    assert "from ui.project.dialogs import" in text
    assert "from ui.project.models import" in text
    assert "class ProjectEditDialog" not in text
    assert "class ProjectResourcesDialog" not in text
    assert "class ProjectResourceEditDialog" not in text
    assert "class ProjectTableModel" not in text


def test_project_dialogs_module_is_facade_only():
    dialogs_path = ROOT / "ui" / "project" / "dialogs.py"
    text = dialogs_path.read_text(encoding="utf-8", errors="ignore")

    assert "from .project_edit_dialog import" in text
    assert "from .project_resource_dialogs import" in text
    assert "class ProjectEditDialog" not in text
    assert "class ProjectResourcesDialog" not in text
    assert "class ProjectResourceEditDialog" not in text


def test_project_resource_dialogs_module_is_facade_only():
    dialogs_path = ROOT / "ui" / "project" / "project_resource_dialogs.py"
    text = dialogs_path.read_text(encoding="utf-8", errors="ignore")

    assert "from .project_resources_dialog import" in text
    assert "from .project_resource_edit_dialog import" in text
    assert "class ProjectResourcesDialog" not in text
    assert "class ProjectResourceEditDialog" not in text


def test_task_tab_is_coordinator_only():
    tab_path = ROOT / "ui" / "task" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.task.project_flow import TaskProjectFlowMixin" in text
    assert "from ui.task.actions import TaskActionsMixin" in text
    assert "from ui.task.models import" in text
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


def test_task_actions_module_contains_task_workflows():
    actions_path = ROOT / "ui" / "task" / "actions.py"
    text = actions_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.task.dialogs import" in text
    assert "def create_task" in text
    assert "def edit_task" in text
    assert "def delete_task" in text
    assert "def update_progress" in text
    assert "def manage_dependencies" in text
    assert "def manage_assignments" in text


def test_task_project_flow_module_contains_loading_helpers():
    flow_path = ROOT / "ui" / "task" / "project_flow.py"
    text = flow_path.read_text(encoding="utf-8", errors="ignore")

    assert "def _load_projects" in text
    assert "def _current_project_id" in text
    assert "def reload_tasks" in text
    assert "def _get_selected_task" in text


def test_task_dependency_dialogs_module_is_facade_only():
    dialogs_path = ROOT / "ui" / "task" / "dependency_dialogs.py"
    text = dialogs_path.read_text(encoding="utf-8", errors="ignore")

    assert "from .dependency_add_dialog import" in text
    assert "from .dependency_list_dialog import" in text
    assert "from .dependency_shared import" in text
    assert "class DependencyAddDialog" not in text
    assert "class DependencyListDialog" not in text


def test_cost_tab_is_coordinator_only():
    tab_path = ROOT / "ui" / "cost" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.cost.models import" in text
    assert "from ui.cost.project_flow import" in text
    assert "from ui.cost.labor_summary import" in text
    assert "from ui.cost.actions import" in text
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

    assert "from ui.dashboard.data_ops import" in text
    assert "from ui.dashboard.rendering import" in text
    assert "from ui.dashboard.styles import" in text
    assert "from ui.dashboard.widgets import" in text
    assert "class KpiCard" not in text
    assert "class ChartWidget" not in text


def test_dashboard_tab_uses_splitter_layout_for_right_side_charts():
    tab_path = ROOT / "ui" / "dashboard" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "self.main_splitter = QSplitter(Qt.Horizontal)" in text
    assert "self.chart_splitter = QSplitter(Qt.Vertical)" in text
    assert "self.main_splitter.addWidget(right_panel)" in text


def test_dashboard_rendering_module_is_facade_only():
    rendering_path = ROOT / "ui" / "dashboard" / "rendering.py"
    text = rendering_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.dashboard.rendering_summary import" in text
    assert "from ui.dashboard.rendering_charts import" in text
    assert "from ui.dashboard.rendering_evm import" in text
    assert "def _update_kpis" not in text
    assert "def _update_burndown_chart" not in text
    assert "def _update_evm" not in text


def test_dashboard_summary_rendering_avoids_widget_index_lookups():
    summary_path = ROOT / "ui" / "dashboard" / "rendering_summary.py"
    text = summary_path.read_text(encoding="utf-8", errors="ignore")

    assert "findChildren(" not in text
    assert ".set_value(" in text


def test_dashboard_service_is_orchestrator_only():
    service_path = ROOT / "core" / "services" / "dashboard" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.services.dashboard.alerts import" in text
    assert "from core.services.dashboard.upcoming import" in text
    assert "from core.services.dashboard.burndown import" in text
    assert "from core.services.dashboard.evm import" in text
    assert "def _build_alerts" not in text
    assert "def _build_upcoming_tasks" not in text
    assert "def _build_burndown" not in text
    assert "def _interpret_evm" not in text


def test_resource_tab_is_coordinator_only():
    tab_path = ROOT / "ui" / "resource" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.resource.flow import ResourceFlowMixin" in text
    assert "from ui.resource.actions import ResourceActionsMixin" in text
    assert "from ui.resource.models import" in text
    assert "class ResourceTableModel" not in text
    assert "class ResourceEditDialog" not in text
    assert "def create_resource" not in text
    assert "def edit_resource" not in text
    assert "def delete_resource" not in text
    assert "def toggle_active" not in text


def test_resource_actions_module_contains_resource_workflows():
    actions_path = ROOT / "ui" / "resource" / "actions.py"
    text = actions_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.resource.dialogs import ResourceEditDialog" in text
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

    assert "from ui.calendar.working_time import" in text
    assert "from ui.calendar.holidays import" in text
    assert "from ui.calendar.calculator import" in text
    assert "from ui.calendar.project_ops import" in text
    assert "def save_calendar" not in text
    assert "def load_holidays" not in text
    assert "def run_calendar_calc" not in text
    assert "def recalc_project_schedule" not in text


def test_infra_repositories_module_is_facade_only():
    repo_path = ROOT / "infra" / "db" / "repositories.py"
    text = repo_path.read_text(encoding="utf-8", errors="ignore")

    assert "from infra.db.mappers import" in text
    assert "from infra.db.repositories_project import" in text
    assert "from infra.db.repositories_task import" in text
    assert "class SqlAlchemy" not in text


def test_infra_mappers_module_is_facade_only():
    mapper_path = ROOT / "infra" / "db" / "mappers.py"
    text = mapper_path.read_text(encoding="utf-8", errors="ignore")

    assert "from infra.db.project.mapper import" in text
    assert "from infra.db.task.mapper import" in text
    assert "from infra.db.resource.mapper import" in text
    assert "from infra.db.cost_calendar.mapper import" in text
    assert "from infra.db.baseline.mapper import" in text
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
        "repositories_project.py": "from infra.db.project.repository import",
        "repositories_task.py": "from infra.db.task.repository import",
        "repositories_resource.py": "from infra.db.resource.repository import",
        "repositories_cost_calendar.py": "from infra.db.cost_calendar.repository import",
        "repositories_baseline.py": "from infra.db.baseline.repository import",
    }
    for name in wrappers:
        text = (ROOT / "infra" / "db" / name).read_text(encoding="utf-8", errors="ignore")
        assert expected_imports[name] in text
        assert "Compatibility wrapper" in text


def test_core_models_module_is_facade_only():
    models_path = ROOT / "core" / "models.py"
    text = models_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.domain.project import" in text
    assert "from core.domain.task import" in text
    assert "from core.domain.resource import" in text
    assert "from core.domain.cost import" in text
    assert "from core.domain.calendar import" in text
    assert "from core.domain.baseline import" in text
    assert "class Project(" not in text
    assert "class Task(" not in text
    assert "class Resource(" not in text


def test_theme_module_is_facade_only():
    theme_path = ROOT / "ui" / "styles" / "theme.py"
    text = theme_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.styles.theme_stylesheet import" in text
    assert "from ui.styles.theme_tokens import" in text
    assert "def set_theme_mode" in text
    assert "def apply_app_style" in text
    assert "QTableView, QTableWidget" not in text
    assert "LIGHT_THEME = {" not in text
    assert "DARK_THEME = {" not in text


def test_reporting_evm_module_is_facade_only():
    evm_path = ROOT / "core" / "services" / "reporting" / "evm.py"
    text = evm_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.services.reporting.evm_core import" in text
    assert "from core.services.reporting.evm_series import" in text
    assert "def get_earned_value" not in text
    assert "def get_evm_series" not in text


def test_task_service_is_orchestrator_only():
    service_path = ROOT / "core" / "services" / "task" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.services.task.lifecycle import" in text
    assert "from core.services.task.dependency import" in text
    assert "from core.services.task.assignment import" in text
    assert "from core.services.task.query import" in text
    assert "from core.services.task.validation import" in text
    assert "def create_task" not in text
    assert "def add_dependency" not in text
    assert "def assign_resource" not in text
    assert "def query_tasks" not in text


def test_project_service_is_orchestrator_only():
    service_path = ROOT / "core" / "services" / "project" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.services.project.lifecycle import ProjectLifecycleMixin" in text
    assert "from core.services.project.query import ProjectQueryMixin" in text
    assert "def create_project" not in text
    assert "def update_project" not in text
    assert "def delete_project" not in text


def test_scheduling_engine_is_orchestrator_only():
    engine_path = ROOT / "core" / "services" / "scheduling" / "engine.py"
    text = engine_path.read_text(encoding="utf-8", errors="ignore")

    assert "from core.services.scheduling.graph import build_project_dependency_graph" in text
    assert "from core.services.scheduling.passes import run_backward_pass, run_forward_pass" in text
    assert "from core.services.scheduling.results import build_schedule_result" in text
    assert "import heapq" not in text


def test_main_build_services_delegates_to_service_graph():
    main_path = ROOT / "main.py"
    text = main_path.read_text(encoding="utf-8", errors="ignore")

    assert "from infra.services import build_service_dict" in text
    assert "return build_service_dict(session)" in text


def test_known_large_modules_have_growth_budgets():
    # Guardrail budgets: these files are intentionally large for now, but must not keep growing.
    budgets = {
        "core/services/reporting/service.py": 180,
        "core/services/reporting/evm.py": 80,
        "core/services/reporting/evm_core.py": 280,
        "core/services/reporting/evm_series.py": 120,
        "core/services/reporting/kpi.py": 280,
        "core/services/reporting/labor.py": 260,
        "ui/project/tab.py": 260,
        "ui/project/dialogs.py": 80,
        "ui/project/project_edit_dialog.py": 240,
        "ui/project/project_resource_dialogs.py": 80,
        "ui/project/project_resources_dialog.py": 260,
        "ui/project/project_resource_edit_dialog.py": 240,
        "ui/project/models.py": 120,
        "ui/task/tab.py": 220,
        "ui/task/actions.py": 220,
        "ui/task/project_flow.py": 180,
        "ui/task/dialogs.py": 80,
        "ui/task/task_dialogs.py": 320,
        "ui/task/dependency_dialogs.py": 220,
        "ui/task/dependency_add_dialog.py": 220,
        "ui/task/dependency_list_dialog.py": 180,
        "ui/task/dependency_shared.py": 60,
        "ui/task/assignment_dialogs.py": 270,
        "ui/task/models.py": 120,
        "ui/task/components.py": 80,
        "ui/cost/tab.py": 220,
        "ui/cost/components.py": 80,
        "ui/cost/models.py": 180,
        "ui/cost/cost_dialogs.py": 240,
        "ui/cost/labor_dialogs.py": 320,
        "ui/cost/project_flow.py": 180,
        "ui/cost/labor_summary.py": 200,
        "ui/cost/actions.py": 150,
        "ui/dashboard/tab.py": 260,
        "ui/dashboard/widgets.py": 120,
        "ui/dashboard/data_ops.py": 180,
        "ui/dashboard/rendering.py": 80,
        "ui/dashboard/rendering_summary.py": 120,
        "ui/dashboard/rendering_charts.py": 140,
        "ui/dashboard/rendering_evm.py": 240,
        "ui/report/tab.py": 220,
        "ui/report/actions.py": 220,
        "ui/report/project_flow.py": 80,
        "ui/report/dialogs.py": 50,
        "ui/report/dialog_helpers.py": 140,
        "ui/report/dialog_kpi.py": 220,
        "ui/report/dialog_gantt.py": 240,
        "ui/report/dialog_critical_path.py": 220,
        "ui/report/dialog_resource_load.py": 240,
        "ui/styles/theme.py": 80,
        "ui/styles/theme_tokens.py": 140,
        "ui/styles/theme_stylesheet.py": 340,
        "main.py": 580,
        "ui/calendar/tab.py": 300,
        "ui/calendar/working_time.py": 120,
        "ui/calendar/holidays.py": 120,
        "ui/calendar/calculator.py": 100,
        "ui/calendar/project_ops.py": 120,
        "core/services/scheduling/engine.py": 360,
        "core/services/scheduling/models.py": 80,
        "core/services/scheduling/graph.py": 180,
        "core/services/scheduling/passes.py": 260,
        "core/services/scheduling/results.py": 180,
        "ui/resource/tab.py": 220,
        "ui/resource/actions.py": 180,
        "ui/resource/flow.py": 80,
        "ui/resource/models.py": 100,
        "ui/resource/dialogs.py": 180,
        "core/models.py": 80,
        "core/domain/__init__.py": 60,
        "core/domain/identifiers.py": 40,
        "core/domain/enums.py": 90,
        "core/domain/project.py": 120,
        "core/domain/task.py": 160,
        "core/domain/resource.py": 80,
        "core/domain/cost.py": 90,
        "core/domain/calendar.py": 120,
        "core/domain/baseline.py": 90,
        "core/services/dashboard/service.py": 140,
        "core/services/dashboard/models.py": 120,
        "core/services/dashboard/alerts.py": 180,
        "core/services/dashboard/upcoming.py": 150,
        "core/services/dashboard/burndown.py": 120,
        "core/services/dashboard/evm.py": 160,
        "ui/styles/ui_config.py": 320,
        "core/services/task/service.py": 140,
        "core/services/project/service.py": 90,
        "core/services/project/lifecycle.py": 220,
        "core/services/project/query.py": 90,
        "core/services/project/validation.py": 80,
        "core/services/task/lifecycle.py": 280,
        "core/services/task/dependency.py": 140,
        "core/services/task/assignment.py": 220,
        "core/services/task/query.py": 120,
        "core/services/task/validation.py": 220,
        "infra/db/repositories.py": 120,
        "infra/db/mappers.py": 120,
        "infra/db/project/__init__.py": 80,
        "infra/db/project/mapper.py": 120,
        "infra/db/project/repository.py": 140,
        "infra/db/task/__init__.py": 80,
        "infra/db/task/mapper.py": 180,
        "infra/db/task/repository.py": 180,
        "infra/db/resource/__init__.py": 60,
        "infra/db/resource/mapper.py": 80,
        "infra/db/resource/repository.py": 80,
        "infra/db/cost_calendar/__init__.py": 90,
        "infra/db/cost_calendar/mapper.py": 180,
        "infra/db/cost_calendar/repository.py": 180,
        "infra/db/baseline/__init__.py": 60,
        "infra/db/baseline/mapper.py": 100,
        "infra/db/baseline/repository.py": 120,
        "infra/db/repositories_project.py": 100,
        "infra/db/repositories_task.py": 150,
        "infra/db/repositories_resource.py": 60,
        "infra/db/repositories_cost_calendar.py": 150,
        "infra/db/repositories_baseline.py": 100,
    }

    breaches = []
    for rel_path, max_lines in budgets.items():
        path = ROOT / rel_path
        lines = _line_count(path)
        if lines > max_lines:
            breaches.append((rel_path, lines, max_lines))

    assert not breaches, f"Large-module budgets exceeded: {breaches}"
