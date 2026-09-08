from __future__ import annotations

from pathlib import Path

from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM


PM_ROOT = Path("src/core/modules/project_management")
TASK_DESKTOP_API = PM_ROOT / "api/desktop/tasks/api.py"
SCHEDULING_MAPPER = Path(
    "src/ui_qml/modules/project_management/presenters/scheduling/leveling_builder.py"
)
WBS_MIGRATION = Path(
    "src/infra/persistence/migrations/versions/f3c89cac079d_initial_schema.py"
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
    """The original standalone `k9l0m1n2o3p4_add_task_owned_wbs` migration (with its own
    `_backfill_root_wbs` step for pre-existing rows) was folded into the squashed
    `f3c89cac079d_initial_schema` migration during a later migration-history squash -- a
    disclosed, confirmed-neutral drift (P45A-FINAL-CLOSURE item 14 / P45B-FINAL-CLEANUP), not a
    production defect. `wbs_code` is now created NOT NULL directly in the initial `tasks` table
    (no backfill step is needed for a fresh-schema column), and the WBS-owning constraints/index
    remain present and reversible in the one migration that now owns the whole schema."""
    source = WBS_MIGRATION.read_text(encoding="utf-8")

    assert "revision: str = 'f3c89cac079d'" in source
    assert "down_revision" in source and "None" in source.split("down_revision", 1)[1].split("\n", 1)[0]
    assert "def downgrade()" in source
    assert "sa.Column('wbs_code', sa.String(length=64), nullable=False)" in source
    assert "op.drop_table('tasks')" in source


def test_desktop_bulk_mutations_use_canonical_atomic_task_commands() -> None:
    source = TASK_DESKTOP_API.read_text(encoding="utf-8")

    assert "service.set_tasks_status(" in source
    assert "service.delete_tasks(" in source
    assert 'getattr(service, "set_tasks_status"' not in source
    assert 'getattr(service, "delete_tasks"' not in source


def test_scheduling_uses_canonical_wbs_instead_of_synthetic_codes() -> None:
    """The original target (`presenters/scheduling/record_mappers.py`) never owned resource-
    leveling's row mapping and has no `wbs`-keyed field of any kind -- a mapper-refactor drift
    (P45A-FINAL-CLOSURE item 14 / P45B-FINAL-CLEANUP), not a production defect. Resource
    Leveling's move rows (`leveling_builder.py`'s `_move_row`) are the actual current site that
    displays a per-task WBS code, and they read the real, Task-owned `wbs_code` field directly --
    never a synthetic `f"1.{row_index}"`-style placeholder."""
    source = SCHEDULING_MAPPER.read_text(encoding="utf-8")

    assert '"wbsCode": move.wbs_code' in source
    assert 'f"1.{row_index' not in source
