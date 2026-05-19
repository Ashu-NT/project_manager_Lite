from __future__ import annotations

import ast
from pathlib import Path

from tests.path_rewrites import REPO_ROOT

ROOT = REPO_ROOT

_LARGE_MODULE_BUDGETS = {
    "src/core/modules/maintenance/infrastructure/persistence/mappers/mapper.py": 1203,
    "src/core/modules/maintenance/infrastructure/persistence/repositories/repository.py": 1489,
    "src/infra/persistence/orm/maintenance/models.py": 1283,
    "src/ui_qml/modules/project_management/presenters/tasks_workspace_presenter.py": 1335,
    "src/ui_qml/modules/project_management/controllers/tasks/tasks_workspace_controller.py": 1600,
    "src/tests/project_management/test_project_management_desktop_api.py": 2990,
    "src/tests/project_management/test_qml_project_management_presenters.py": 2185,
    "src/tests/architecture/test_architecture_guardrails.py": 1500,
    "src/tests/platform/test_qml_platform_presenters.py": 2452,
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
        "from src.core.modules.project_management.domain.identifiers import generate_id",
        "from src.core.platform.common.service_base import ServiceBase",
    )
    checked_roots = (
        ROOT / "core" / "platform",
        ROOT / "src" / "core" / "modules" / "inventory_procurement",
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
        "src.core.modules.project_management.access.policy",
        "core.modules.project_management.services.project",
        "src.core.modules.project_management.application.projects",
        "src.core.modules.project_management.application.resources",
    )
    checked_files = (
        ROOT / "src" / "core" / "platform" / "access" / "application" / "access_control_service.py",
        ROOT / "src" / "ui_qml" / "platform" / "controllers" / "admin" / "access_workspace_controller.py",
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
    platform_bundle_path = ROOT / "src" / "infra" / "composition" / "platform_registry.py"
    source = platform_bundle_path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)
    forbidden_import_targets = (
        "src.core.modules.project_management.access.policy",
        "src.core.modules.inventory_procurement.access.policy",
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
    project_bundle_path = ROOT / "src" / "infra" / "composition" / "project_registry.py"
    inventory_bundle_path = ROOT / "src" / "infra" / "composition" / "inventory_registry.py"
    project_text = project_bundle_path.read_text(encoding="utf-8", errors="ignore")
    inventory_text = inventory_bundle_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.access.policy import" in project_text
    assert 'scope_type="project"' in project_text
    assert "from src.core.modules.inventory_procurement.access.policy import" in inventory_text
    assert 'scope_type="storeroom"' in inventory_text


def test_legacy_widget_ui_roots_are_removed():
    assert not (ROOT / "ui").exists()
    assert not (ROOT / "src" / "ui").exists()



def test_runtime_code_does_not_import_legacy_widget_ui():
    violations: list[tuple[str, str]] = []
    checked_paths = [ROOT / "main_qt.py"]
    checked_paths.extend(
        path
        for path in _python_files(ROOT / "src")
        if "tests" not in path.parts
    )

    for path in checked_paths:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name == "ui" or name.startswith("ui."):
                        violations.append((str(path.relative_to(ROOT)), name))
                    if name == "src.ui" or name.startswith("src.ui."):
                        violations.append((str(path.relative_to(ROOT)), name))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "ui" or mod.startswith("ui."):
                    violations.append((str(path.relative_to(ROOT)), mod))
                if mod == "src.ui" or mod.startswith("src.ui."):
                    violations.append((str(path.relative_to(ROOT)), mod))

    assert not violations, f"Runtime code imports legacy widget UI: {violations}"

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

    legacy_from = "from " + "infra.platform"
    legacy_import = "import " + "infra.platform"
    violations: list[str] = []
    for root in (ROOT / "src", ROOT / "infra" / "modules"):
        for path in _python_files(root):
            if path == Path(__file__):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if legacy_from in text or legacy_import in text:
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
        ROOT / "src" / "core" / "modules" / "inventory_procurement" / "infrastructure" / "persistence" / "mappers" / "catalog.py",
        ROOT / "src" / "core" / "modules" / "inventory_procurement" / "infrastructure" / "persistence" / "mappers" / "inventory.py",
        ROOT / "src" / "core" / "modules" / "inventory_procurement" / "infrastructure" / "persistence" / "mappers" / "procurement.py",
        ROOT / "src" / "core" / "modules" / "inventory_procurement" / "infrastructure" / "persistence" / "repositories" / "catalog.py",
        ROOT / "src" / "core" / "modules" / "inventory_procurement" / "infrastructure" / "persistence" / "repositories" / "inventory.py",
        ROOT / "src" / "core" / "modules" / "inventory_procurement" / "infrastructure" / "persistence" / "repositories" / "procurement.py",
    ]

    for path in checked_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "from src.core.modules.inventory_procurement.infrastructure.persistence.orm." in text
        assert "from src.infra.persistence.orm.platform.models import" not in text
        assert "from src.infra.persistence.orm.inventory_procurement.models import" not in text


def test_orm_package_root_loads_all_model_packages():
    package_path = ROOT / "src" / "infra" / "persistence" / "orm" / "__init__.py"
    migration_env_path = ROOT / "src" / "infra" / "persistence" / "migrations" / "env.py"
    package_text = package_path.read_text(encoding="utf-8", errors="ignore")
    migration_env_text = migration_env_path.read_text(encoding="utf-8", errors="ignore")

    assert not (ROOT / "src" / "infra" / "persistence" / "orm" / "platform").exists()
    assert "from src.infra.persistence.orm.base import Base" in package_text
    assert "import src.infra.persistence.orm.maintenance.models" in package_text
    assert "import src.infra.persistence.orm.maintenance.preventive_runtime_models" in package_text
    platform_orm_modules = ("org", "documents", "party", "modules", "time", "auth", "access", "audit", "approval", "runtime_tracking")
    for module in platform_orm_modules:
        assert f"import src.core.platform.infrastructure.persistence.orm.{module}" in package_text
    for module in ("project", "resource", "task", "cost_calendar", "baseline", "register", "collaboration", "portfolio"):
        assert f"import src.core.modules.project_management.infrastructure.persistence.orm.{module}" in package_text
    for module in ("catalog", "inventory", "procurement"):
        assert f"import src.core.modules.inventory_procurement.infrastructure.persistence.orm.{module}" in package_text
    assert "from src.infra.persistence.orm import Base" in migration_env_text
    assert "import src.infra.persistence.orm" in migration_env_text


def test_legacy_inventory_persistence_and_reporting_packages_are_removed():
    removed = [
        ROOT / "infra" / "modules" / "inventory_procurement" / "db",
        ROOT / "src" / "infra" / "persistence" / "orm" / "inventory_procurement",
        ROOT / "core" / "modules" / "inventory_procurement" / "reporting",
        ROOT / "core" / "modules" / "inventory_procurement" / "services" / "reporting",
    ]

    for path in removed:
        assert not path.exists()


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


def test_qml_shell_controller_module_is_registered():
    qmldir_path = ROOT / "src" / "ui_qml" / "shell" / "qml" / "Shell" / "Controllers" / "qmldir"
    text = qmldir_path.read_text(encoding="utf-8", errors="ignore")

    assert "module Shell.Controllers" in text
    assert "ShellLoginController" in text



def test_qml_platform_controller_packages_exist():
    for rel_path in (
        "src/ui_qml/platform/controllers/admin/access_workspace_controller.py",
        "src/ui_qml/platform/controllers/control/control_workspace_controller.py",
        "src/ui_qml/platform/controllers/settings/settings_workspace_controller.py",
        "src/ui_qml/platform/controllers/common/workspace_controller_base.py",
    ):
        assert (ROOT / rel_path).exists()



def test_qml_module_workspace_roots_exist():
    for rel_path in (
        "src/ui_qml/modules/project_management/qml/workspaces",
        "src/ui_qml/modules/inventory_procurement/qml/workspaces",
        "src/ui_qml/modules/maintenance/qml/workspaces",
    ):
        assert (ROOT / rel_path).is_dir()

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
    service_path = ROOT / "src" / "core" / "modules" / "project_management" / "application" / "projects" / "service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.application.projects.commands.lifecycle import (" in text
    assert "from src.core.modules.project_management.application.projects.queries.project_query import (" in text
    assert "def create_project" not in text
    assert "def update_project" not in text
    assert "def delete_project" not in text


def test_project_resource_service_is_orchestrator_only():
    service_path = (
        ROOT
        / "src"
        / "core"
        / "modules"
        / "project_management"
        / "application"
        / "resources"
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
        ROOT
        / "src"
        / "core"
        / "modules"
        / "project_management"
        / "application"
        / "risk"
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
        ROOT
        / "src"
        / "core"
        / "modules"
        / "project_management"
        / "application"
        / "resources"
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
        ROOT
        / "src"
        / "core"
        / "modules"
        / "project_management"
        / "application"
        / "financials"
        / "cost_service.py"
    )
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.application.financials.commands.cost_lifecycle import (" in text
    assert "from src.core.modules.project_management.application.financials.queries.cost_query import (" in text
    assert "from src.core.modules.project_management.application.financials.cost_support import (" in text
    assert "class CostService(" in text
    assert "def add_cost_item" not in text
    assert "def update_cost_item" not in text
    assert "def delete_cost_item" not in text
    assert "def get_project_cost_summary" not in text


def test_collaboration_service_is_orchestrator_only():
    service_path = ROOT / "src" / "core" / "modules" / "project_management" / "application" / "tasks" / "collaboration_service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    for snippet in (
        "from src.core.modules.project_management.application.tasks.commands.collaboration_comments import (",
        "CollaborationCommentCommandMixin,",
        "from src.core.modules.project_management.application.tasks.commands.collaboration_presence import (",
        "CollaborationPresenceCommandMixin,",
        "from src.core.modules.project_management.application.tasks.queries.collaboration_inbox import (",
        "CollaborationInboxQueryMixin,",
        "from src.core.modules.project_management.application.tasks.collaboration_support import (",
        "CollaborationSupportMixin,",
    ):
        assert snippet in text
    assert "class CollaborationService(" in text
    assert "def post_comment" not in text
    assert "def list_notifications" not in text
    assert "def list_active_presence" not in text

def test_portfolio_service_is_orchestrator_only():
    service_path = ROOT / "src" / "core" / "modules" / "project_management" / "application" / "projects" / "portfolio_service.py"
    text = service_path.read_text(encoding="utf-8", errors="ignore")

    for snippet in (
        "from src.core.modules.project_management.application.projects.commands.portfolio_dependencies import",
        "PortfolioDependencyCommandMixin,",
        "from src.core.modules.project_management.application.projects.queries.portfolio_executive import",
        "PortfolioExecutiveQueryMixin,",
        "from src.core.modules.project_management.application.projects.portfolio_support import",
        "PortfolioSupportMixin,",
        "from src.core.modules.project_management.application.projects.commands.portfolio_templates import",
        "PortfolioTemplateCommandMixin,",
    ):
        assert snippet in text
    assert "class PortfolioService(" in text
    assert "def create_intake_item" not in text
    assert "def compare_scenarios" not in text
    assert "def list_portfolio_heatmap" not in text


def test_scheduling_engine_is_orchestrator_only():
    engine_path = (
        ROOT
        / "src"
        / "core"
        / "modules"
        / "project_management"
        / "application"
        / "scheduling"
        / "engine.py"
    )
    text = engine_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.application.scheduling.graph import (" in text
    assert "build_project_dependency_graph," in text
    assert "from src.core.modules.project_management.application.scheduling.passes import (" in text
    assert "run_backward_pass," in text
    assert "run_forward_pass," in text
    assert "from src.core.modules.project_management.application.scheduling.results import (" in text
    assert "build_schedule_result," in text
    assert "import heapq" not in text


def test_scheduling_leveling_is_split_from_engine():
    engine_path = (
        ROOT
        / "src"
        / "core"
        / "modules"
        / "project_management"
        / "application"
        / "scheduling"
        / "engine.py"
    )
    text = engine_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.core.modules.project_management.application.scheduling.leveling_service import (" in text
    assert "ResourceLevelingMixin," in text
    assert "class SchedulingEngine(ResourceLevelingMixin)" in text


def test_main_qt_uses_qml_shell_entrypoint():
    main_qt_path = ROOT / "main_qt.py"
    text = main_qt_path.read_text(encoding="utf-8", errors="ignore")

    assert "from src.ui_qml.shell.app import main" in text



def test_known_large_modules_have_growth_budgets():
    budgets = {
        **_LARGE_MODULE_BUDGETS,
        "src/core/modules/project_management/infrastructure/reporting/service.py": 180,
        "src/core/modules/project_management/application/scheduling/engine.py": 360,
        "src/core/modules/project_management/application/scheduling/passes.py": 260,
        "src/core/modules/project_management/application/resources/commands/project_resource_commands.py": 320,
        "src/core/modules/project_management/application/tasks/commands/lifecycle.py": 320,
        "src/core/platform/org/application/site_service.py": 340,
        "src/core/platform/org/application/department_service.py": 410,
    }

    breaches = []
    for rel_path, max_lines in budgets.items():
        path = ROOT / rel_path
        lines = _line_count(path)
        if lines > max_lines:
            breaches.append((rel_path, lines, max_lines))

    assert not breaches, f"Large-module budgets exceeded: {breaches}"
