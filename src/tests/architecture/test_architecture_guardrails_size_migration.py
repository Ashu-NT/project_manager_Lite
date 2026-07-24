from __future__ import annotations

import ast
from pathlib import Path

from src.tests.path_rewrites import REPO_ROOT

ROOT = REPO_ROOT

_LARGE_MODULE_BUDGETS = {
    "src/core/modules/maintenance/infrastructure/persistence/mappers/mapper.py": 1203,
    "src/core/modules/maintenance/infrastructure/persistence/repositories/repository.py": 2410,
    "src/core/modules/maintenance/infrastructure/persistence/orm/models.py": 1330,
    "src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py": 1338,
    "src/ui_qml/modules/project_management/controllers/tasks/tasks_workspace_controller.py": 1600,
    "src/tests/project_management/test_project_management_desktop_api.py": 3390,
    "src/tests/project_management/test_qml_project_management_presenters.py": 2420,
    "src/tests/project_management/test_repository_tenant_hardening.py": 1300,
    "src/tests/platform/test_qml_platform_presenters.py": 2510,
}


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())


def _python_files(root: Path):
    for path in root.rglob("*.py"):
        if "dist" in path.parts:
            continue
        if path.name == "resources_rc.py":
            continue
        yield path


def _migration_metadata():
    versions_root = ROOT / "src" / "infra" / "persistence" / "migrations" / "versions"
    revisions: dict[str, Path] = {}
    duplicates: dict[str, list[Path]] = {}
    down_revisions: dict[str, tuple[str, ...]] = {}

    for path in sorted(versions_root.glob("*.py")):
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
        revision = None
        raw_down_revision = None

        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Name):
                    continue
                if target.id == "revision":
                    revision = ast.literal_eval(node.value)
                elif target.id == "down_revision":
                    raw_down_revision = ast.literal_eval(node.value)

        if not revision:
            continue

        if revision in revisions:
            duplicates.setdefault(revision, [revisions[revision]]).append(path)
        else:
            revisions[revision] = path

        if raw_down_revision is None:
            down_revisions[revision] = ()
        elif isinstance(raw_down_revision, str):
            down_revisions[revision] = (raw_down_revision,)
        else:
            down_revisions[revision] = tuple(str(item) for item in raw_down_revision)

    return revisions, duplicates, down_revisions


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


def test_alembic_revisions_are_unique():
    _, duplicates, _ = _migration_metadata()
    duplicate_details = {
        revision: [str(path.relative_to(ROOT)).replace("\\", "/") for path in paths]
        for revision, paths in duplicates.items()
    }
    assert not duplicate_details, f"Duplicate Alembic revisions found: {duplicate_details}"


def test_alembic_migration_graph_has_single_head():
    revisions, _, down_revisions = _migration_metadata()
    referenced_revisions = {
        down_revision
        for parent_revisions in down_revisions.values()
        for down_revision in parent_revisions
    }
    heads = sorted(revision for revision in revisions if revision not in referenced_revisions)
    assert len(heads) == 1, f"Alembic migration graph must have exactly one head, found: {heads}"


def test_alembic_op_add_column_does_not_inline_foreign_keys():
    versions_root = ROOT / "src" / "infra" / "persistence" / "migrations" / "versions"
    offenders: list[str] = []

    for path in sorted(versions_root.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr == "add_column"
                and isinstance(func.value, ast.Name)
                and func.value.id == "op"
            ):
                continue
            for arg in node.args[1:]:
                if not (
                    isinstance(arg, ast.Call)
                    and (
                        (isinstance(arg.func, ast.Attribute) and arg.func.attr == "Column")
                        or (isinstance(arg.func, ast.Name) and arg.func.id == "Column")
                    )
                ):
                    continue
                if any(
                    isinstance(sub, ast.Call)
                    and isinstance(sub.func, ast.Attribute)
                    and sub.func.attr == "ForeignKey"
                    for sub in arg.args
                ):
                    offenders.append(str(path.relative_to(ROOT)).replace("\\", "/"))
                    break

    assert not offenders, (
        "SQLite-targeted Alembic migrations must not inline ForeignKey() inside "
        f"op.add_column(...): {sorted(offenders)}"
    )


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


def test_pm_task_controllers_do_not_spawn_background_workers():
    tasks_controller_root = (
        ROOT / "src" / "ui_qml" / "modules" / "project_management" / "controllers" / "tasks"
    )
    forbidden_tokens = ("QThreadPool", "QRunnable")
    violations: list[tuple[str, str]] = []

    for path in _python_files(tasks_controller_root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in forbidden_tokens:
            if token in text:
                relative_path = str(path.relative_to(ROOT)).replace("\\", "/")
                violations.append((relative_path, token))

    assert not violations, (
        "PM task controllers must stay on the shared main-thread service path; "
        f"background worker usage found: {violations}"
    )


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
