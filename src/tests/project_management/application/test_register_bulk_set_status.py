"""RegisterService.bulk_set_entry_status() must persist the same per-entry
audit/activity/event work as update_entry(status=...), but for every
selected entry inside ONE UnitOfWork/commit instead of one per entry (same
reasoning as OrganizationService.bulk_update_organization_currency()).

Also covers a real pre-existing bug this replaces: the old bulk-status
handler called update_entry({"id": i, "status": status}), but update_entry()
requires entryId/projectId/title and would raise on that payload -- Register's
bulk status change was silently broken before this."""

from __future__ import annotations

from src.core.modules.project_management.domain.risk.register import (
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.modules.project_management.infrastructure.persistence.uow.register.register_unit_of_work import (
    SqlAlchemyRegisterUnitOfWorkFactory,
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


def test_bulk_set_entry_status_updates_every_entry_in_one_transaction(services) -> None:
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "Bulk register project", financial_currency_code=organization.base_currency
    )
    register_service = services["register_service"]
    entries = [
        register_service.create_entry(
            project.id, entry_type=RegisterEntryType.RISK, title=f"Bulk risk {i}"
        )
        for i in range(3)
    ]
    entry_ids = [e.id for e in entries]
    assert all(e.status == RegisterEntryStatus.OPEN for e in entries)

    counts, restore = _count_uow_creations(SqlAlchemyRegisterUnitOfWorkFactory)
    try:
        results = register_service.bulk_set_entry_status(entry_ids, RegisterEntryStatus.CLOSED)
    finally:
        restore()

    assert counts["create"] == 1, (
        f"bulk-updating {len(entry_ids)} register entries opened {counts['create']} "
        "UnitOfWork(s) instead of exactly 1"
    )
    assert [e.status for e in results] == [RegisterEntryStatus.CLOSED] * 3
    for entry_id in entry_ids:
        reloaded = register_service.get_entry(entry_id)
        assert reloaded.status == RegisterEntryStatus.CLOSED
        # Untouched fields survive a status-only bulk update.
        assert reloaded.title.startswith("Bulk risk")
