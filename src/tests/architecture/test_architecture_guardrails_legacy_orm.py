from __future__ import annotations

import ast
from pathlib import Path

from src.tests.path_rewrites import REPO_ROOT

ROOT = REPO_ROOT


def _python_files(root: Path):
    for path in root.rglob("*.py"):
        if "dist" in path.parts:
            continue
        if path.name == "resources_rc.py":
            continue
        yield path


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
    assert not (ROOT / "ui" / "platform" / "settings").exists()


def test_legacy_platform_shared_ui_package_is_removed():
    assert not (ROOT / "ui" / "platform" / "shared").exists()


def test_legacy_platform_control_ui_package_is_removed():
    assert not (ROOT / "ui" / "platform" / "control").exists()


def test_legacy_platform_admin_ui_package_is_removed():
    assert not (ROOT / "ui" / "platform" / "admin").exists()


def test_composition_imports_focused_persistence_adapters():
    repo_path = ROOT / "src" / "infra" / "composition" / "repositories.py"
    text = repo_path.read_text(encoding="utf-8", errors="ignore")

    assert not (ROOT / "src" / "infra" / "persistence" / "db" / "platform").exists()
    assert "from infra.platform.db.repositories import" not in text
    assert "from infra.platform.db.mappers import" not in text
    assert "from src.core.modules.project_management.infrastructure.persistence.repositories.task import" in text
    assert "from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import" in text
    assert "from src.core.platform.infrastructure.persistence.repositories.master_data.department.departments import" in text
    assert "from src.core.platform.infrastructure.persistence.repositories.master_data.employee.employee import" in text
    assert "from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import" in text
    assert "from src.core.platform.infrastructure.persistence.repositories.master_data.site.sites import" in text
    assert "from src.core.platform.infrastructure.persistence.repositories.time_management.time.time import" in text


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
        ROOT / "src" / "core" / "modules" / "project_management" / "infrastructure" / "persistence" / "repositories" / "cost.py",
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
    assert "import src.core.modules.maintenance.infrastructure.persistence.orm.models" in package_text
    assert "import src.core.modules.maintenance.infrastructure.persistence.orm.preventive_runtime_models" in package_text
    platform_orm_modules = (
        "tenant.modules.modules", "time_management.time.time", "security.auth.auth", "events.notifications.notification", "history.audit.audit_entry", "approval.approval", "data_operations.runtime_tracking.runtime_tracking",
        "master_data.employee.employee", "master_data.site.sites", "master_data.department.departments",
        "master_data.org.org", "master_data.documents.documents", "master_data.party.party",
    )
    for module in platform_orm_modules:
        assert f"import src.core.platform.infrastructure.persistence.orm.{module}" in package_text
    for module in ("project", "resource", "task", "cost", "baseline", "register", "collaboration", "portfolio"):
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
    qmltypes_path = ROOT / "src" / "ui_qml" / "shell" / "qml" / "Shell" / "Controllers" / "plugins.qmltypes"
    text = qmldir_path.read_text(encoding="utf-8", errors="ignore")
    qmltypes_text = qmltypes_path.read_text(encoding="utf-8", errors="ignore")

    assert "module Shell.Controllers" in text
    assert "ShellLoginController" in qmltypes_text


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

    assert "from src.core.platform.contract.time_management.time.contracts import TimeEntryRepository, TimesheetPeriodRepository" in text
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


def test_legacy_rbac_runtime_dependencies_are_removed():
    runtime_roots = (
        ROOT / "src" / "core",
        ROOT / "src" / "api",
        ROOT / "src" / "ui_qml",
        ROOT / "src" / "infra" / "composition",
        ROOT / "src" / "infra" / "platform",
        ROOT / "tools",
    )
    forbidden_tokens = (
        "AuthorizationMigrationMode",
        "authorization_migration_mode",
        "PM_AUTHORIZATION_MIGRATION_MODE",
        "RBAC-TRANSITION-ONLY",
        "UserRoleORM",
        "UserRoleRepository",
        "ProjectMembershipRepository",
        "ScopedAccessGrantRepository",
        "project_membership_repo",
        "scoped_access_repo",
    )
    violations: list[tuple[str, str]] = []

    for root in runtime_roots:
        for path in root.rglob("*.py"):
            source = path.read_text(encoding="utf-8", errors="ignore")
            for token in forbidden_tokens:
                if token in source:
                    violations.append((str(path.relative_to(ROOT)), token))

    env_path = ROOT / ".env"
    if env_path.exists():
        env_text = env_path.read_text(encoding="utf-8", errors="ignore")
        if "PM_AUTHORIZATION_MIGRATION_MODE" in env_text:
            violations.append((".env", "PM_AUTHORIZATION_MIGRATION_MODE"))

    assert not violations, f"Legacy RBAC runtime dependencies remain: {violations}"


def test_dormant_http_transport_is_removed_for_desktop_only_product():
    http_root = ROOT / "src" / "api" / "http"
    assert not http_root.exists() or not list(http_root.rglob("*.py"))


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


def test_platform_calendar_does_not_import_project_management_at_module_scope():
    """
    The Enterprise Calendar resolver/assignment service intentionally take
    PM-owned repositories as `Any`-typed constructor params and import the
    concrete PM types *inside* method bodies (not at module scope) so the
    platform module never gains a hard, top-level dependency on
    project_management. This guards that boundary as the codebase evolves.
    """
    calendar_roots = [
        ROOT / "src" / "core" / "platform" / "domain" / "time_management" / "calendar",
        ROOT / "src" / "core" / "platform" / "contract" / "time_management" / "calendar",
        ROOT / "src" / "core" / "platform" / "application" / "time_management" / "calendar",
        ROOT / "src" / "core" / "platform" / "infrastructure" / "persistence" / "mappers" / "time_management" / "calendar",
        ROOT / "src" / "core" / "platform" / "infrastructure" / "persistence" / "orm" / "time_management" / "calendar",
        ROOT / "src" / "core" / "platform" / "infrastructure" / "persistence" / "repositories" / "time_management" / "calendar",
        ROOT / "src" / "core" / "platform" / "api" / "desktop" / "time_management" / "calendar",
    ]
    violations: list[tuple[str, str]] = []

    for calendar_root in calendar_roots:
        for path in _python_files(calendar_root):
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
            for node in tree.body:
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.name
                        if name == "src.core.modules.project_management" or name.startswith(
                            "src.core.modules.project_management."
                        ):
                            violations.append((str(path.relative_to(ROOT)), name))
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if mod == "src.core.modules.project_management" or mod.startswith(
                        "src.core.modules.project_management."
                    ):
                        violations.append((str(path.relative_to(ROOT)), mod))

    assert not violations, f"Platform calendar module imports project_management at module scope: {violations}"
