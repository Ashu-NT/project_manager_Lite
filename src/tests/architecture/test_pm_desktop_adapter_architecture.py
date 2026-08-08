from __future__ import annotations

import ast
from pathlib import Path

from src.tests.path_rewrites import REPO_ROOT


DESKTOP_ROOT = REPO_ROOT / "src/core/modules/project_management/api/desktop"
APPLICATION_ROOTS = (
    REPO_ROOT / "src/core/modules/project_management/application",
    REPO_ROOT / "src/core/platform/application",
)
DOMAIN_ROOTS = (
    REPO_ROOT / "src/core/modules/project_management/domain",
    REPO_ROOT / "src/core/platform/domain",
)
FORBIDDEN_REPOSITORY_IMPORT_PREFIXES = (
    "src.core.modules.project_management.contracts.repositories",
    "src.core.modules.project_management.infrastructure.persistence",
    "src.infra.modules.project_management.persistence",
)

# DA0 transition register. Every entry must be removed with its DA1 runtime fix.
KNOWN_REPOSITORY_IMPORTS: set[str] = set()
KNOWN_PRIVATE_COLLABORATOR_ACCESS: set[str] = set()
KNOWN_APPLICATION_CONSTRUCTION = {
    "src/core/modules/project_management/api/desktop/scheduling/builders/constraint_builder.py:"
    "src.core.modules.project_management.application.scheduling.cpm.constraint_validator."
    "ConstraintValidator",
}
KNOWN_PRIVATE_MODULE_IMPORTS = {
    "src/core/modules/project_management/api/desktop/common/financial_formatting.py:"
    "src.core.platform.finance.money._decimal",
    "src/core/modules/project_management/api/desktop/dashboard/builders/"
    "operational_table_builder.py:"
    "src.core.platform.api.desktop.approval._approval_labels",
}


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*.py") if path.is_file()))


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _imports(tree: ast.AST) -> tuple[tuple[str, str], ...]:
    imports: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(
                (alias.asname or alias.name.split(".")[-1], alias.name)
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.extend(
                (alias.asname or alias.name, f"{node.module}.{alias.name}")
                for alias in node.names
            )
    return tuple(imports)


def _repository_imports_for_tree(path_label: str, tree: ast.AST) -> set[str]:
    violations: set[str] = set()
    for _local_name, qualified_name in _imports(tree):
        module_name = qualified_name.rsplit(".", 1)[0]
        for prefix in FORBIDDEN_REPOSITORY_IMPORT_PREFIXES:
            if module_name == prefix or module_name.startswith(f"{prefix}."):
                violations.add(f"{path_label}:{module_name}")
    return violations


def _repository_import_violations() -> set[str]:
    violations: set[str] = set()
    for path in _python_files(DESKTOP_ROOT):
        violations.update(_repository_imports_for_tree(_relative(path), _tree(path)))
    return violations


def _private_access_for_tree(path_label: str, tree: ast.AST) -> set[str]:
    violations: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, str)
            and node.args[1].value.startswith("_")
            and not node.args[1].value.startswith("__")
        ):
            violations.add(f"{path_label}:{node.args[1].value}")
        elif (
            isinstance(node, ast.Attribute)
            and node.attr.startswith("_")
            and not node.attr.startswith("__")
            and not (isinstance(node.value, ast.Name) and node.value.id in {"self", "cls"})
        ):
            violations.add(f"{path_label}:{node.attr}")
    return violations


def _private_collaborator_violations() -> set[str]:
    violations: set[str] = set()
    for path in _python_files(DESKTOP_ROOT):
        violations.update(_private_access_for_tree(_relative(path), _tree(path)))
    return violations


def _application_construction_for_tree(path_label: str, tree: ast.AST) -> set[str]:
    violations: set[str] = set()
    application_imports = {
        local_name: qualified_name
        for local_name, qualified_name in _imports(tree)
        if ".application." in qualified_name
    }
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        qualified_name = application_imports.get(node.func.id)
        if qualified_name:
            violations.add(f"{path_label}:{qualified_name}")
    return violations


def _application_construction_violations() -> set[str]:
    violations: set[str] = set()
    for path in _python_files(DESKTOP_ROOT):
        violations.update(_application_construction_for_tree(_relative(path), _tree(path)))
    return violations


def _private_modules_for_tree(path_label: str, tree: ast.AST) -> set[str]:
    violations: set[str] = set()
    for _local_name, qualified_name in _imports(tree):
        module_name = qualified_name.rsplit(".", 1)[0]
        if any(
            part.startswith("_") and not part.startswith("__")
            for part in module_name.split(".")
        ):
            violations.add(f"{path_label}:{module_name}")
    return violations


def _private_module_import_violations() -> set[str]:
    violations: set[str] = set()
    for path in _python_files(DESKTOP_ROOT):
        violations.update(_private_modules_for_tree(_relative(path), _tree(path)))
    return violations


def _desktop_import_violations(root: Path) -> set[str]:
    violations: set[str] = set()
    for path in _python_files(root):
        for _local_name, qualified_name in _imports(_tree(path)):
            if ".api.desktop." in qualified_name or qualified_name.endswith(".api.desktop"):
                violations.add(f"{_relative(path)}:{qualified_name}")
    return violations


def test_desktop_adds_no_repository_or_persistence_imports() -> None:
    assert _repository_import_violations() == KNOWN_REPOSITORY_IMPORTS


def test_desktop_adds_no_private_collaborator_access() -> None:
    assert _private_collaborator_violations() == KNOWN_PRIVATE_COLLABORATOR_ACCESS


def test_desktop_adds_no_application_object_construction() -> None:
    assert _application_construction_violations() == KNOWN_APPLICATION_CONSTRUCTION


def test_desktop_adds_no_private_module_imports() -> None:
    assert _private_module_import_violations() == KNOWN_PRIVATE_MODULE_IMPORTS


def test_application_and_domain_do_not_import_desktop_adapters() -> None:
    violations: set[str] = set()
    for root in (*APPLICATION_ROOTS, *DOMAIN_ROOTS):
        violations.update(_desktop_import_violations(root))
    assert violations == set()


def test_dead_financial_procurement_desktop_projection_stays_deleted() -> None:
    financials_root = DESKTOP_ROOT / "financials"
    api_source = (financials_root / "api.py").read_text(encoding="utf-8")

    assert "list_project_requisitions" not in api_source
    assert "get_project_procurement_commitments" not in api_source
    assert not (financials_root / "models/procurement.py").exists()
    assert not (financials_root / "serializers/procurement_serializer.py").exists()


def test_dead_pm_calendar_mutation_surface_stays_deleted() -> None:
    scheduling_root = DESKTOP_ROOT / "scheduling"
    api_source = (scheduling_root / "api.py").read_text(encoding="utf-8")
    adapter_source = (
        scheduling_root / "services/calendar_adapter_service.py"
    ).read_text(encoding="utf-8")
    package_source = (scheduling_root / "__init__.py").read_text(encoding="utf-8")

    for symbol in (
        "update_calendar",
        "add_holiday",
        "delete_holiday",
        "SchedulingCalendarUpdateCommand",
        "SchedulingHolidayCreateCommand",
    ):
        assert symbol not in api_source
        assert symbol not in package_source
    for helper in (
        "update_platform_calendar_working_days",
        "add_platform_holiday",
        "delete_platform_holiday",
    ):
        assert helper not in adapter_source
    assert not (scheduling_root / "commands/calendar_commands.py").exists()


def test_resource_rate_and_certification_policy_stays_out_of_adapters() -> None:
    resource_api_source = (DESKTOP_ROOT / "resources/api.py").read_text(encoding="utf-8")
    importer_source = (
        REPO_ROOT
        / "src/core/modules/project_management/infrastructure/importers/resources/csv/"
        "resource_csv_importer.py"
    ).read_text(encoding="utf-8")
    certification_source = (
        DESKTOP_ROOT / "resources/serializers/certification_serializer.py"
    ).read_text(encoding="utf-8")

    for source in (resource_api_source, importer_source):
        for policy_token in (
            "hourly_rate_changed",
            "currency_changed",
            "rate_affecting_change",
            "effective_on=date.today",
        ):
            assert policy_token not in source
    assert "status_on(today)" in certification_source
    assert "expiry < today" not in certification_source
    assert "(expiry - today).days" not in certification_source


def test_scheduling_lifecycle_and_calendar_policy_stays_with_its_owners() -> None:
    scheduling_root = DESKTOP_ROOT / "scheduling"
    baseline_source = (
        scheduling_root / "formatters/baseline_formatter.py"
    ).read_text(encoding="utf-8")
    schedule_source = (
        scheduling_root / "serializers/schedule_serializer.py"
    ).read_text(encoding="utf-8")
    calendar_source = (
        scheduling_root / "services/calendar_adapter_service.py"
    ).read_text(encoding="utf-8")

    for token in (
        'status_val == "draft"',
        'status_val == "submitted"',
    ):
        assert token not in baseline_source
    assert "baseline.can_submit" in baseline_source
    assert "baseline.can_approve" in baseline_source
    assert "baseline.can_reject" in baseline_source

    assert "task.remaining_duration_days" in schedule_source
    assert "scheduling_utils" not in schedule_source
    assert not (scheduling_root / "utils/scheduling_utils.py").exists()

    assert "_default_platform_calendar_id" not in calendar_source
    assert 'list_calendars(calendar_type="GLOBAL")' not in calendar_source
    assert "get_default_calendar()" in calendar_source


def test_register_triage_policy_stays_out_of_desktop_adapters() -> None:
    register_root = DESKTOP_ROOT / "register"
    builder_source = (
        register_root / "builders/entry_list_builder.py"
    ).read_text(encoding="utf-8")
    serializer_source = (
        register_root / "serializers/entry_serializer.py"
    ).read_text(encoding="utf-8")
    query_source = (
        REPO_ROOT
        / "src/core/modules/project_management/application/risk/queries/register_query.py"
    ).read_text(encoding="utf-8")

    assert "sorted(" not in builder_source
    assert "severity_rank" not in builder_source
    assert "is_overdue(" not in builder_source
    assert "entry.is_overdue_on(date.today())" in serializer_source
    assert ".triage_key(" in query_source
    assert not (register_root / "utils/register_status_utils.py").exists()


def test_da0_scanners_detect_synthetic_violations() -> None:
    path_label = "synthetic.py"
    repository_tree = ast.parse(
        "from src.core.modules.project_management.contracts.repositories.task "
        "import TaskRepository"
    )
    assert _repository_imports_for_tree(path_label, repository_tree)

    private_tree = ast.parse('repo = getattr(service, "_repo", None)')
    assert _private_access_for_tree(path_label, private_tree) == {
        "synthetic.py:_repo"
    }

    construction_tree = ast.parse(
        "from src.core.modules.project_management.application.tasks import TaskService\n"
        "service = TaskService()"
    )
    assert _application_construction_for_tree(path_label, construction_tree) == {
        "synthetic.py:src.core.modules.project_management.application.tasks.TaskService"
    }

    private_module_tree = ast.parse(
        "from src.core.platform.api.desktop.approval._labels import label"
    )
    assert _private_modules_for_tree(path_label, private_module_tree) == {
        "synthetic.py:src.core.platform.api.desktop.approval._labels"
    }
