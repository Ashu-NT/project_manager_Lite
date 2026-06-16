from __future__ import annotations

from pathlib import Path

from src.tests.path_rewrites import REPO_ROOT

ROOT = REPO_ROOT

_LARGE_MODULE_BUDGETS = {
    "src/core/modules/maintenance/infrastructure/persistence/mappers/mapper.py": 1203,
    "src/core/modules/maintenance/infrastructure/persistence/repositories/repository.py": 2410,
    "src/core/modules/maintenance/infrastructure/persistence/orm/models.py": 1330,
    "src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py": 1338,
    "src/ui_qml/modules/project_management/controllers/tasks/tasks_workspace_controller.py": 1600,
}


def test_project_service_is_orchestrator_only():
    service_path = ROOT / "src" / "core" / "modules" / "project_management" / "application" / "projects" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.application.projects.commands.lifecycle import (" in text
    assert "from src.core.modules.project_management.application.projects.queries.project_query import (" in text
    assert "def create_project" not in text
    assert "def update_project" not in text
    assert "def delete_project" not in text


def test_project_resource_service_is_orchestrator_only():
    service_path = (
        ROOT / "src" / "core" / "modules" / "project_management" / "application" / "resources"
        / "project_resource_service.py"
    )
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.application.resources.commands.project_resource_commands import (" in text
    assert "from src.core.modules.project_management.application.resources.queries.project_resource_queries import (" in text
    assert "def add_to_project" not in text
    assert "def update(" not in text
    assert "def delete(" not in text


def test_register_service_is_orchestrator_only():
    service_path = (
        ROOT / "src" / "core" / "modules" / "project_management" / "application" / "risk"
        / "register_service.py"
    )
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.application.risk.commands.register_lifecycle import (" in text
    assert "from src.core.modules.project_management.application.risk.queries.register_query import (" in text
    assert "def create_entry" not in text
    assert "def update_entry" not in text
    assert "def delete_entry" not in text
    assert "def list_entries" not in text
    assert "def get_project_summary" not in text


def test_resource_service_is_orchestrator_only():
    service_path = (
        ROOT / "src" / "core" / "modules" / "project_management" / "application" / "resources"
        / "resource_service.py"
    )
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.application.resources.commands.resource_commands import (" in text
    assert "from src.core.modules.project_management.application.resources.queries.resource_queries import (" in text
    assert "def create_resource" not in text
    assert "def update_resource" not in text
    assert "def delete_resource" not in text
    assert "def list_resources" not in text
    assert "def get_resource" not in text


def test_cost_service_is_orchestrator_only():
    service_path = (
        ROOT / "src" / "core" / "modules" / "project_management" / "application" / "financials"
        / "services" / "cost_service.py"
    )
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.application.financials.costs.commands.cost_lifecycle import (" in text
    assert "from src.core.modules.project_management.application.financials.costs.queries.cost_query import (" in text
    assert "from src.core.modules.project_management.application.financials.costs.cost_support import (" in text
    assert "class CostService(" in text
    assert "def add_cost_item" not in text
    assert "def update_cost_item" not in text
    assert "def delete_cost_item" not in text
    assert "def get_project_cost_summary" not in text


def test_collaboration_service_is_orchestrator_only():
    service_path = ROOT / "src" / "core" / "modules" / "project_management" / "application" / "collaboration" / "services" / "collaboration_service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    for snippet in (
        "from src.core.modules.project_management.application.collaboration.commands.collaboration_comments import (",
        "CollaborationCommentCommandMixin,",
        "from src.core.modules.project_management.application.collaboration.commands.collaboration_presence import (",
        "CollaborationPresenceCommandMixin,",
        "from src.core.modules.project_management.application.collaboration.queries.collaboration_inbox import (",
        "CollaborationInboxQueryMixin,",
        "from src.core.modules.project_management.application.collaboration.utils.support import (",
        "CollaborationSupportMixin,",
    ):
        assert snippet in text
    assert "class CollaborationService(" in text
    assert "def post_comment" not in text
    assert "def list_notifications" not in text
    assert "def list_active_presence" not in text


def test_portfolio_service_is_orchestrator_only():
    service_path = ROOT / "src" / "core" / "modules" / "project_management" / "application" / "portfolio" / "services" / "portfolio_service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    for snippet in (
        "from src.core.modules.project_management.application.portfolio.commands.portfolio_dependencies import",
        "PortfolioDependencyCommandMixin,",
        "from src.core.modules.project_management.application.portfolio.queries.portfolio_executive import",
        "PortfolioExecutiveQueryMixin,",
        "from src.core.modules.project_management.application.portfolio.utils.portfolio_support import",
        "PortfolioSupportMixin,",
        "from src.core.modules.project_management.application.portfolio.commands.portfolio_templates import",
        "PortfolioTemplateCommandMixin,",
    ):
        assert snippet in text
    assert "class PortfolioService(" in text
    assert "def create_intake_item" not in text
    assert "def compare_scenarios" not in text
    assert "def list_portfolio_heatmap" not in text


def test_scheduling_engine_is_orchestrator_only():
    engine_path = (
        ROOT / "src" / "core" / "modules" / "project_management" / "application" / "scheduling"
        / "services" / "scheduling_engine.py"
    )
    text = engine_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.application.scheduling.cpm.graph import (" in text
    assert "build_project_dependency_graph," in text
    assert "from src.core.modules.project_management.application.scheduling.cpm.passes import (" in text
    assert "run_backward_pass," in text
    assert "run_forward_pass," in text
    assert "from src.core.modules.project_management.application.scheduling.cpm.results import (" in text
    assert "build_schedule_result," in text
    assert "import heapq" not in text


def test_scheduling_leveling_is_split_from_engine():
    engine_path = (
        ROOT / "src" / "core" / "modules" / "project_management" / "application" / "scheduling"
        / "services" / "scheduling_engine.py"
    )
    text = engine_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.application.scheduling.leveling.leveling_mixin import (" in text
    assert "ResourceLevelingMixin," in text
    assert "class SchedulingEngine(ResourceLevelingMixin)" in text


def test_main_qt_uses_qml_shell_entrypoint():
    main_qt_path = ROOT / "main_qt.py"
    text = main_qt_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui_qml.shell.app import main" in text


def test_known_large_modules_have_growth_budgets():
    budgets = {
        **_LARGE_MODULE_BUDGETS,
        "src/core/modules/project_management/infrastructure/reporting/services/reporting_service.py": 180,
        "src/core/modules/project_management/application/scheduling/services/scheduling_engine.py": 410,
        "src/core/modules/project_management/application/scheduling/cpm/passes.py": 260,
        "src/core/modules/project_management/application/resources/commands/project_resource_commands.py": 320,
        "src/core/modules/project_management/application/tasks/commands/lifecycle.py": 360,
        "src/core/platform/site/application/site_service.py": 360,
    }

    breaches = []
    for rel_path, max_lines in budgets.items():
        path = ROOT / rel_path
        lines = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
        if lines > max_lines:
            breaches.append((rel_path, lines, max_lines))

    assert not breaches, f"Large-module budgets exceeded: {breaches}"
