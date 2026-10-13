from __future__ import annotations

import pytest
from sqlalchemy import event, update

from src.core.platform.api.desktop.history.activity.activity import (
    PlatformActivityDesktopApi,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.read.history.activity_actor_reader import (
    ActivityActorKind,
)
from src.core.platform.domain.history.activity.activity_entry import ActivityEntry
from src.core.platform.infrastructure.persistence.orm.security.auth.auth import UserORM
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import (
    UserTenantORM,
)


def _scope(services):
    context = services["tenant_context_service"]
    return context.get_active_tenant_id(), context.get_active_organization().id


def test_activity_actor_projection_is_scoped_typed_and_batched(services, session):
    auth = services["auth_service"]
    employee_service = services["employee_service"]
    department = services["department_service"].create_department(
        department_code="R7G-ACTOR", name="History Actors"
    )
    human = auth.onboard_tenant_user(
        username="r7g-human", raw_password="StrongPass123!", display_name="Visible Human"
    )
    disabled = auth.onboard_tenant_user(
        username="r7g-disabled", raw_password="StrongPass123!"
    )
    service = auth.onboard_tenant_user(
        username="r7g-service", raw_password="StrongPass123!"
    )
    removed = auth.onboard_tenant_user(
        username="r7g-removed", raw_password="StrongPass123!"
    )
    employee = employee_service.create_employee(
        employee_code="R7G-EMP", full_name="Employee Identity", department_id=department.id
    )
    employee_service.link_employee_user_account(employee.id, human.id)
    auth.set_user_active(disabled.id, False)
    session.execute(update(UserORM).where(UserORM.id == service.id).values(account_type="service"))
    session.execute(
        update(UserTenantORM)
        .where(UserTenantORM.user_id == removed.id)
        .values(status="removed")
    )
    session.commit()

    tenant_id, organization_id = _scope(services)
    actor_ids = (human.id, disabled.id, service.id, removed.id, "deleted-user")
    entries = [
        ActivityEntry.create(
            action="test", entity_type="project", entity_id="project-1", module="project_management",
            actor_id=actor_id, tenant_id=tenant_id, organization_id=organization_id,
        )
        for actor_id in actor_ids
    ]
    queries: list[str] = []

    def count_user_queries(conn, cursor, statement, parameters, context, executemany):
        if "FROM users" in statement:
            queries.append(statement)

    event.listen(session.bind, "before_cursor_execute", count_user_queries)
    try:
        labels = services["activity_service"].present_actors(entries)
    finally:
        event.remove(session.bind, "before_cursor_execute", count_user_queries)

    assert len(queries) == 1
    assert labels[human.id].kind == ActivityActorKind.HUMAN
    assert labels[human.id].label == "Visible Human"
    assert labels[disabled.id].kind == ActivityActorKind.DISABLED
    assert labels[disabled.id].label == "Former user"
    assert labels[service.id].kind == ActivityActorKind.SERVICE
    assert labels[service.id].label == "Service account"
    assert labels[removed.id].kind == ActivityActorKind.DISABLED
    assert labels[removed.id].label == "Former user"
    assert labels["deleted-user"].kind == ActivityActorKind.MISSING

    foreign = services["activity_service"]._actor_reader.resolve_batch(
        tenant_id="foreign-tenant", actor_ids=(human.id,)
    )
    assert foreign == {}

    for changed in (
        ActivityEntry.create(
            action="test", entity_type="project", entity_id="project-1",
            module="project_management", actor_id=human.id,
            tenant_id="foreign-tenant", organization_id=organization_id,
        ),
        ActivityEntry.create(
            action="test", entity_type="project", entity_id="project-1",
            module="project_management", actor_id=human.id,
            tenant_id=tenant_id, organization_id="foreign-organization",
        ),
    ):
        with pytest.raises(BusinessRuleError, match="scope mismatch"):
            services["activity_service"].present_actors((entries[0], changed))


def test_activity_desktop_api_serializes_authoritative_actor_presentation(services, session):
    activity = services["activity_service"]
    entry = activity.record(
        action="project.updated", entity_type="project", entity_id="r7g-project",
        module="project_management", human_message="Project updated",
    )
    session.commit()
    tenant_id, organization_id = _scope(services)
    assert entry.tenant_id == tenant_id

    api = PlatformActivityDesktopApi(activity_service=activity)
    result = api.list_page_for_entity("project", "r7g-project", organization_id)
    assert result.ok
    assert result.data is not None
    assert result.data.filtered_total == 1
    actor = result.data.items[0]
    assert actor.actor_kind == "human"
    assert actor.actor_display
    assert actor.actor_display != actor.actor_id
