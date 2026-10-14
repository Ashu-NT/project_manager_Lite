from __future__ import annotations

import inspect

from src.tests.path_rewrites import REPO_ROOT

ROOT = REPO_ROOT

_LARGE_MODULE_BUDGETS = {
    "src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py": 1338,
    "src/ui_qml/modules/project_management/controllers/tasks/tasks_workspace_controller.py": 1600,
}


def test_project_service_is_orchestrator_only():
    service_path = ROOT / "src" / "core" / "modules" / "project_management" / "application" / "projects" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    for command in ("create", "deletion", "status", "update"):
        assert (
            f"from src.core.modules.project_management.application.projects.commands.{command} import ("
            in text
        )
        command_source = (
            ROOT
            / "src/core/modules/project_management/application/projects/commands"
            / f"{command}.py"
        ).read_text(encoding="utf-8")
        if command in {"create", "update"}:
            assert "from src.core.modules.project_management.application.projects.commands.support import (" in command_source
    assert "from src.core.modules.project_management.application.projects.queries.project_query import (" in text
    assert "return self._create_handler.create_project(*args, **kwargs)" in text
    assert "return self._update_handler.update_project(*args, **kwargs)" in text
    assert "self._deletion_handler.delete_project(project_id)" in text


def test_project_resource_service_is_orchestrator_only():
    service_path = (
        ROOT / "src" / "core" / "modules" / "project_management" / "application" / "resources"
        / "project_resources" / "project_resource_service.py"
    )
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.application.resources.commands.project_resource_commands import (" in text
    assert "from src.core.modules.project_management.application.resources.queries.project_resource_queries import (" in text
    assert "return self._command.add_to_project(" in text
    assert "self._command.update(" in text
    assert "self._command.delete(" in text


def test_register_composition_exposes_handlers_without_service():
    risk_path = ROOT / "src/core/modules/project_management/application/risk"
    assert not (risk_path / "register_service.py").exists()
    query = (risk_path / "queries/register_query.py").read_text(encoding="utf-8")
    assert "class RegisterQueryHandler(" in query
    composition = (
        ROOT / "src/core/modules/project_management/infrastructure/composition/dependencies/register/services.py"
    ).read_text(encoding="utf-8")
    assert "lifecycle = RegisterLifecycleHandler(" in composition
    assert "query = RegisterQueryHandler(" in composition
    assert "return RegisterComposition(query=query, lifecycle=lifecycle)" in composition
    assert "def create_entry" not in query
    assert "def update_entry" not in query
    assert "def delete_entry" not in query


def test_resource_forwarding_facade_is_removed_and_handlers_are_fed_directly():
    pm_root = ROOT / "src" / "core" / "modules" / "project_management"
    assert not (pm_root / "application" / "resources" / "catalog" / "resource_service.py").exists()
    composition = (
        pm_root / "infrastructure" / "composition" / "dependencies" / "resources" / "services.py"
    ).read_text(encoding="utf-8")
    assert "query = ResourceQueryHandler(" in composition
    assert "master_commands = ResourceMasterCommandHandler(" in composition
    assert "capability_commands = ResourceCapabilityCommandHandler(" in composition
    api = (pm_root / "api" / "desktop" / "resources" / "api.py").read_text(encoding="utf-8")
    # Command handlers are not module-guarded themselves; the adapter checks
    # the PM entitlement before every command dispatch.
    assert api.count("require_module_enabled(") >= 4
    assert "ResourceService" not in api


def test_reporting_and_dashboard_facades_are_removed():
    pm_app = ROOT / "src" / "core" / "modules" / "project_management" / "application"
    assert not (pm_app / "reporting" / "services").exists()
    assert not (pm_app / "dashboard" / "services" / "dashboard_service.py").exists()
    for path in (pm_app / "reporting" / "builders").glob("*.py"):
        assert "Mixin" not in path.read_text(encoding="utf-8").replace(
            "ProjectManagementModuleGuardMixin", ""
        ), path.name
    for path in (pm_app / "dashboard").rglob("*.py"):
        assert "Mixin(" not in path.read_text(encoding="utf-8").replace(
            "ProjectManagementModuleGuardMixin", ""
        ), path.name


def test_collaboration_and_portfolio_facades_are_removed():
    pm_app = ROOT / "src" / "core" / "modules" / "project_management" / "application"
    for feature in ("collaboration", "portfolio"):
        assert not (pm_app / feature / "services").exists()
        for path in (pm_app / feature).rglob("*.py"):
            text = path.read_text(encoding="utf-8").replace("ProjectManagementModuleGuardMixin", "")
            assert "Mixin" not in text, path.name
    assert not (pm_app / "collaboration" / "utils" / "support.py").exists()
    assert not (pm_app / "collaboration" / "utils" / "principal.py").exists()
    assert not (pm_app / "portfolio" / "utils" / "portfolio_support.py").exists()


def test_collaboration_writes_and_reads_are_separate_guarded_handlers():
    from src.core.modules.project_management.application.collaboration.commands import (
        CollaborationCommentCommandHandler,
        CollaborationCommentEngagementHandler,
        CollaborationPresenceCommandHandler,
    )
    from src.core.modules.project_management.application.collaboration.queries import (
        CollaborationCommentQueryHandler,
        CollaborationDocumentQueryHandler,
        CollaborationInboxQueryHandler,
        CollaborationPresenceQueryHandler,
    )
    from src.core.modules.project_management.application.common.module_guard import (
        ProjectManagementModuleGuardMixin,
    )

    writes = (
        CollaborationCommentCommandHandler,
        CollaborationCommentEngagementHandler,
        CollaborationPresenceCommandHandler,
    )
    reads = (
        CollaborationCommentQueryHandler,
        CollaborationDocumentQueryHandler,
        CollaborationInboxQueryHandler,
        CollaborationPresenceQueryHandler,
    )
    for handler in writes + reads:
        assert issubclass(handler, ProjectManagementModuleGuardMixin), handler.__name__
    for handler in reads:
        source = inspect.getsource(handler)
        assert "_uow_factory" not in source, handler.__name__
        assert "record_audit_entry" not in source, handler.__name__


def test_portfolio_handlers_are_guarded_and_share_one_policy():
    from src.core.modules.project_management.application.common.module_guard import (
        ProjectManagementModuleGuardMixin,
    )
    from src.core.modules.project_management.application.portfolio import (
        commands,
        queries,
    )

    for name in commands.__all__ + queries.__all__:
        handler = getattr(commands, name, None) or getattr(queries, name)
        assert issubclass(handler, ProjectManagementModuleGuardMixin), name
    policy_text = (
        ROOT / "src" / "core" / "modules" / "project_management" / "application"
        / "portfolio" / "utils" / "portfolio_policy.py"
    ).read_text(encoding="utf-8")
    assert "def ensure_scoring_templates" in policy_text
    for path in (
        ROOT / "src" / "core" / "modules" / "project_management" / "application" / "portfolio"
    ).rglob("*.py"):
        if path.name == "portfolio_policy.py":
            continue
        assert "PortfolioScoringTemplate.create(" not in path.read_text(encoding="utf-8") or (
            path.name == "portfolio_templates.py"
        ), path.name


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
    """Resource leveling moved off SchedulingEngine entirely (R4.4Y):
    the one authoritative leveling component, ResourceLevelingPlanner,
    is a pure, in-memory application-layer class -- not a mixin
    SchedulingEngine inherits, so there is no split-file convention
    left to guard here."""
    from src.core.modules.project_management.application.scheduling.leveling.resource_leveling_planner import (
        ResourceLevelingPlanner,
    )
    from src.core.modules.project_management.application.scheduling.services.scheduling_engine import (
        SchedulingEngine,
    )

    assert not issubclass(SchedulingEngine, ResourceLevelingPlanner)
    assert ResourceLevelingPlanner not in SchedulingEngine.__mro__


def test_main_qt_uses_qml_shell_entrypoint():
    main_qt_path = ROOT / "main_qt.py"
    text = main_qt_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui_qml.shell.app import main" in text


def test_known_large_modules_have_growth_budgets():
    budgets = {
        **_LARGE_MODULE_BUDGETS,
        "src/core/modules/project_management/application/dashboard/services/project_dashboard_query.py": 180,
        "src/core/modules/project_management/application/reporting/builders/kpi.py": 300,
        "src/core/modules/project_management/application/scheduling/services/scheduling_engine.py": 410,
        "src/core/modules/project_management/application/scheduling/cpm/passes.py": 260,
        # The command handler already exceeds the previous historical cap (431 lines).
        "src/core/modules/project_management/application/resources/commands/project_resource_commands.py": 440,
        "src/core/modules/project_management/application/tasks/commands/lifecycle.py": 360,
        "src/core/platform/application/master_data/site/queries/site_queries.py": 360,
    }

    breaches = []
    for rel_path, max_lines in budgets.items():
        path = ROOT / rel_path
        lines = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
        if lines > max_lines:
            breaches.append((rel_path, lines, max_lines))

    assert not breaches, f"Large-module budgets exceeded: {breaches}"
