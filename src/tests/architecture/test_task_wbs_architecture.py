from __future__ import annotations

from pathlib import Path

from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM


PM_ROOT = Path("src/core/modules/project_management")
TASK_DESKTOP_API = PM_ROOT / "api/desktop/tasks/api.py"
SCHEDULING_MAPPER = Path(
    "src/ui_qml/modules/project_management/presenters/scheduling/record_mappers.py"
)
WBS_MIGRATION = Path(
    "src/infra/persistence/migrations/versions/k9l0m1n2o3p4_add_task_owned_wbs.py"
)


def test_task_orm_owns_the_only_project_wbs_hierarchy() -> None:
    table = TaskORM.__table__
    constraint_names = {constraint.name for constraint in table.constraints}

    assert {"parent_task_id", "wbs_code", "sort_order"}.issubset(table.c.keys())
    assert "fk_tasks_wbs_same_project_parent" in constraint_names
    assert "uq_tasks_project_wbs_code" in constraint_names
    assert "ck_tasks_wbs_parent_not_self" in constraint_names

    domain_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in PM_ROOT.rglob("*.py")
        if "tests" not in path.parts
    )
    assert "class WorkPackage" not in domain_source


def test_task_wbs_migration_is_independent_and_reversible() -> None:
    source = WBS_MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "k9l0m1n2o3p4"' in source
    assert 'down_revision = "j8k9l0m1n2o3"' in source
    assert "def downgrade()" in source
    assert "_backfill_root_wbs" in source


def test_desktop_bulk_mutations_use_canonical_atomic_task_commands() -> None:
    source = TASK_DESKTOP_API.read_text(encoding="utf-8")

    assert "service.set_tasks_status(" in source
    assert "service.delete_tasks(" in source
    assert 'getattr(service, "set_tasks_status"' not in source
    assert 'getattr(service, "delete_tasks"' not in source


def test_scheduling_uses_canonical_wbs_instead_of_synthetic_codes() -> None:
    source = SCHEDULING_MAPPER.read_text(encoding="utf-8")

    assert '"wbs": item.wbs_code or "-"' in source
    assert 'f"1.{row_index' not in source
