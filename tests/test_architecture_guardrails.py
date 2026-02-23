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

    assert "from ui.report.dialogs import" in text
    assert "class KPIReportDialog" not in text
    assert "class GanttPreviewDialog" not in text
    assert "class CriticalPathDialog" not in text
    assert "class ResourceLoadDialog" not in text


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


def test_task_tab_is_coordinator_only():
    tab_path = ROOT / "ui" / "task" / "tab.py"
    text = tab_path.read_text(encoding="utf-8", errors="ignore")

    assert "from ui.task.dialogs import" in text
    assert "from ui.task.models import" in text
    assert "class TaskEditDialog" not in text
    assert "class TaskProgressDialog" not in text
    assert "class DependencyAddDialog" not in text
    assert "class DependencyListDialog" not in text
    assert "class AssignmentAddDialog" not in text
    assert "class AssignmentListDialog" not in text
    assert "class TaskTableModel" not in text


def test_infra_repositories_module_is_facade_only():
    repo_path = ROOT / "infra" / "db" / "repositories.py"
    text = repo_path.read_text(encoding="utf-8", errors="ignore")

    assert "from infra.db.mappers import" in text
    assert "from infra.db.repositories_project import" in text
    assert "from infra.db.repositories_task import" in text
    assert "class SqlAlchemy" not in text


def test_known_large_modules_have_growth_budgets():
    # Guardrail budgets: these files are intentionally large for now, but must not keep growing.
    budgets = {
        "core/services/reporting/service.py": 180,
        "core/services/reporting/evm.py": 450,
        "core/services/reporting/kpi.py": 280,
        "core/services/reporting/labor.py": 260,
        "ui/project/tab.py": 260,
        "ui/project/dialogs.py": 80,
        "ui/project/project_edit_dialog.py": 240,
        "ui/project/project_resource_dialogs.py": 450,
        "ui/project/models.py": 120,
        "ui/task/tab.py": 320,
        "ui/task/dialogs.py": 80,
        "ui/task/task_dialogs.py": 320,
        "ui/task/dependency_dialogs.py": 220,
        "ui/task/assignment_dialogs.py": 260,
        "ui/task/models.py": 120,
        "ui/task/components.py": 80,
        "ui/dashboard/tab.py": 830,
        "core/services/task/service.py": 720,
        "infra/db/repositories.py": 120,
        "infra/db/mappers.py": 360,
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
