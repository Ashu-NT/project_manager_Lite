"""ProjectService.bulk_set_status() must persist the same per-project audit/
activity/event work as set_status(), but for every selected project inside
ONE UnitOfWork/commit instead of one per project (same reasoning as
OrganizationService.bulk_activate_organizations())."""

from __future__ import annotations

from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.infrastructure.persistence.uow.projects.project_unit_of_work import (
    SqlAlchemyProjectUnitOfWorkFactory,
)


def _count_uow_creations(factory_cls):
    counts = {"create": 0}
    real_create = factory_cls.create

    def counting_create(self, *args, **kwargs):
        counts["create"] += 1
        return real_create(self, *args, **kwargs)

    factory_cls.create = counting_create

    def restore():
        factory_cls.create = real_create

    return counts, restore


def test_bulk_set_status_updates_every_project_in_one_transaction(services) -> None:
    project_service = services["project_service"]
    projects = [
        project_service.create_project(f"Bulk status project {i}", "")
        for i in range(3)
    ]
    project_ids = [p.id for p in projects]

    counts, restore = _count_uow_creations(SqlAlchemyProjectUnitOfWorkFactory)
    try:
        results = project_service.bulk_set_status(project_ids, ProjectStatus.ACTIVE)
    finally:
        restore()

    assert counts["create"] == 1, (
        f"bulk-updating {len(project_ids)} projects opened {counts['create']} "
        "UnitOfWork(s) instead of exactly 1"
    )
    assert [p.status for p in results] == [ProjectStatus.ACTIVE] * 3
    for project_id in project_ids:
        reloaded = project_service.get_project(project_id)
        assert reloaded.status == ProjectStatus.ACTIVE
