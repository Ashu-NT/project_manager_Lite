from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.infrastructure.persistence.reads.history.activity_actor_projection import (
    actor_labels_for_page,
)
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import (
    DepartmentORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import (
    EmployeeORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.party.party import (
    PartyORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import (
    SiteORM,
)

_REFERENCE_FIELDS = {
    "site_id": "site",
    "department_id": "department",
    "manager_user_id": "user",
    "client_party_id": "party",
}


def resolve_project_activity_labels(
    session: Session, *, tenant_id: str, organization_id: str,
    entries: Sequence[tuple[str | None, dict[str, object]]],
) -> tuple[dict[str, tuple[str, str]], dict[str, dict[str, str]]]:
    reference_ids: dict[str, set[str]] = {kind: set() for kind in _REFERENCE_FIELDS.values()}
    actor_ids = {actor_id for actor_id, _ in entries if actor_id}
    for _, details in entries:
        changes = details.get("changes")
        if not isinstance(changes, dict):
            continue
        for field_name, kind in _REFERENCE_FIELDS.items():
            change = changes.get(field_name)
            if not isinstance(change, dict):
                continue
            for value in (change.get("from"), change.get("to")):
                if isinstance(value, str) and value:
                    reference_ids[kind].add(value)

    user_ids = actor_ids | reference_ids["user"]
    actors = actor_labels_for_page(
        session, tenant_id=tenant_id, actor_ids=tuple(user_ids)
    )
    if user_ids:
        employees = session.execute(
            select(EmployeeORM.user_id, EmployeeORM.full_name)
            .where(
                EmployeeORM.user_id.in_(user_ids),
                EmployeeORM.tenant_id == tenant_id,
                EmployeeORM.organization_id == organization_id,
            )
            .order_by(EmployeeORM.id)
        ).all()
        for user_id, full_name in employees:
            current = actors.get(user_id)
            if current is not None and current[0] == "human" and full_name:
                actors[user_id] = ("human", full_name)

    labels: dict[str, dict[str, str]] = {
        "user": {user_id: actors[user_id][1] for user_id in reference_ids["user"] if user_id in actors}
    }
    for kind, orm, name_column in (
        ("site", SiteORM, SiteORM.name),
        ("department", DepartmentORM, DepartmentORM.name),
        ("party", PartyORM, PartyORM.party_name),
    ):
        ids = reference_ids[kind]
        labels[kind] = {}
        if not ids:
            continue
        labels[kind] = {
            row_id: name for row_id, name in session.execute(
                select(orm.id, name_column).where(
                    orm.id.in_(ids),
                    orm.organization_id == organization_id,
                    or_(orm.tenant_id == tenant_id, orm.tenant_id.is_(None)),
                )
            ).all()
        }
    return actors, labels


__all__ = ["resolve_project_activity_labels"]
