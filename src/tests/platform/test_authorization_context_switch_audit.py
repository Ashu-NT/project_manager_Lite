from __future__ import annotations

import json
import logging

import pytest
from sqlalchemy import func, select

from src.core.modules.maintenance.application.common.scope_authorization import (
    deny_maintenance_scope_access,
)
from src.core.platform.access.authorization import require_scope_permission
from src.core.platform.auth.authorization import (
    authorization_denied,
    require_permission,
)
from src.core.platform.auth.domain.session import (
    UserSessionContext,
    UserSessionPrincipal,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
    AuditEntryORM,
)
from src.core.platform.application.tenant.tenancy.context_policy import SaaSTenantContextPolicy
from src.infra.platform.operational_support import bind_trace_id


def _principal(
    *,
    permissions: frozenset[str] = frozenset(),
    tenant_id: str = "tenant-a",
    organization_id: str | None = "organization-a",
    scoped_access: dict[str, dict[str, frozenset[str]]] | None = None,
) -> UserSessionPrincipal:
    return UserSessionPrincipal(
        user_id="user-a",
        username="audited-user",
        display_name="Audited User",
        role_names=frozenset({"viewer"}),
        permissions=permissions,
        scoped_access=scoped_access or {},
        session_id="session-a",
        active_tenant_id=tenant_id,
        active_organization_id=organization_id,
    )


def _audit_rows(
    session,
    operation: str,
    *,
    actor_id: str | None = None,
) -> list[AuditEntryORM]:
    stmt = select(AuditEntryORM).where(AuditEntryORM.operation == operation)
    if actor_id is not None:
        stmt = stmt.where(AuditEntryORM.actor_id == actor_id)
    return list(
        session.execute(
            stmt.order_by(AuditEntryORM.timestamp)
        ).scalars()
    )


def test_permission_denial_emits_scoped_redacted_event() -> None:
    events = []
    user_session = UserSessionContext(
        security_denial_listener=events.append,
    )
    user_session.set_principal(_principal())

    with pytest.raises(BusinessRuleError) as exc:
        require_permission(
            user_session,
            "finance.export",
            operation_label="export finance report",
        )

    assert exc.value.code == "PERMISSION_DENIED"
    assert len(events) == 1
    event = events[0]
    assert event.operation == "authorization.denied"
    assert event.reason_code == "PERMISSION_DENIED"
    assert event.required_permissions == ("finance.export",)
    assert event.actor_user_id == "user-a"
    assert event.session_id == "session-a"
    assert event.tenant_id == "tenant-a"
    assert event.organization_id == "organization-a"
    assert not hasattr(event, "password")
    assert not hasattr(event, "submitted_value")


def test_denial_audit_failure_never_changes_denial_to_allow(
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _fail(_event) -> None:
        raise RuntimeError("audit unavailable")

    user_session = UserSessionContext(security_denial_listener=_fail)
    user_session.set_principal(_principal())

    with caplog.at_level(logging.CRITICAL):
        with pytest.raises(BusinessRuleError) as exc:
            require_permission(
                user_session,
                "security.manage",
                operation_label="change security policy",
            )

    assert exc.value.code == "PERMISSION_DENIED"
    assert "Security denial audit persistence failed" in caplog.text


def test_scope_denial_records_target_scope_without_changing_error() -> None:
    events = []
    user_session = UserSessionContext(
        security_denial_listener=events.append,
    )
    user_session.set_principal(
        _principal(
            permissions=frozenset({"project.read"}),
            scoped_access={
                "project": {
                    "project-a": frozenset({"project.read"}),
                }
            },
        )
    )

    with pytest.raises(BusinessRuleError) as exc:
        require_scope_permission(
            user_session,
            "project",
            "project-b",
            "project.read",
            operation_label="view project",
        )

    assert exc.value.code == "PERMISSION_DENIED"
    assert len(events) == 1
    event = events[0]
    assert event.operation == "authorization.scope.denied"
    assert event.target_scope_type == "project"
    assert event.target_scope_id == "project-b"
    assert event.required_permissions == ("project.read",)


def test_post_gate_denial_preserves_code_and_records_one_typed_event() -> None:
    events = []
    user_session = UserSessionContext(
        security_denial_listener=events.append,
    )
    user_session.set_principal(_principal())

    with pytest.raises(BusinessRuleError) as exc:
        authorization_denied(
            user_session,
            message="The target user is outside the active tenant.",
            code="USER_CROSS_TENANT_DENIED",
            operation_label="change a tenant user",
            target_scope_type="user",
            target_scope_id="user-b",
            operation="authorization.membership.denied",
        )

    assert exc.value.code == "USER_CROSS_TENANT_DENIED"
    assert str(exc.value) == "The target user is outside the active tenant."
    assert len(events) == 1
    event = events[0]
    assert event.operation == "authorization.membership.denied"
    assert event.reason_code == "USER_CROSS_TENANT_DENIED"
    assert event.target_scope_type == "user"
    assert event.target_scope_id == "user-b"


def test_maintenance_scope_denial_uses_shared_post_gate_boundary() -> None:
    events = []
    user_session = UserSessionContext(
        security_denial_listener=events.append,
    )
    user_session.set_principal(_principal())

    with pytest.raises(BusinessRuleError) as exc:
        deny_maintenance_scope_access(
            user_session,
            operation_label="view an unanchored work order",
            message="Permission denied for unanchored work order.",
        )

    assert exc.value.code == "PERMISSION_DENIED"
    assert len(events) == 1
    event = events[0]
    assert event.operation == "authorization.resource_scope.denied"
    assert event.reason_code == "PERMISSION_DENIED"
    assert event.target_scope_type == "maintenance"
    assert event.target_scope_id is None


def test_composed_denial_writer_persists_scope_and_trace(services) -> None:
    user_session = services["user_session"]
    current = user_session.principal
    assert current is not None

    with bind_trace_id("trace-authorization-denial"):
        with pytest.raises(BusinessRuleError) as exc:
            require_permission(
                user_session,
                "never.granted",
                operation_label="exercise production denial writer",
            )

    assert exc.value.code == "PERMISSION_DENIED"
    rows = _audit_rows(
        services["session"],
        "authorization.denied",
        actor_id=current.user_id,
    )
    assert len(rows) == 1
    row = rows[0]
    metadata = json.loads(row.metadata_json)
    assert row.tenant_id == user_session.stored_active_tenant_id()
    assert row.organization_id == user_session.stored_active_organization_id()
    assert row.request_id == "trace-authorization-denial"
    assert row.source == "authorization"
    assert row.severity == "high"
    assert metadata["outcome"] == "denied"
    assert metadata["required_permissions"] == ["never.granted"]


def test_tenant_switch_success_is_audited_and_idempotent(services) -> None:
    tenant_context = services["tenant_context_service"]
    tenant_admin = services["tenant_admin_service"]
    user_session = services["user_session"]
    current = user_session.principal
    assert current is not None
    old_tenant_id = current.active_tenant_id
    target = tenant_admin.create_tenant(
        "AUDIT-SWITCH",
        "Audited Switch Tenant",
    )

    tenant_context.switch_to_tenant(target.id)

    assert user_session.active_tenant_id() == target.id
    rows = _audit_rows(
        services["session"],
        "auth.context.tenant.switched",
        actor_id=current.user_id,
    )
    assert len(rows) == 1
    row = rows[0]
    metadata = json.loads(row.metadata_json)
    assert row.tenant_id == target.id
    assert row.field == "tenant_id"
    assert row.old_value == old_tenant_id
    assert row.new_value == target.id
    assert metadata["outcome"] == "success"

    tenant_context.switch_to_tenant(target.id)

    assert len(
        _audit_rows(
            services["session"],
            "auth.context.tenant.switched",
            actor_id=current.user_id,
        )
    ) == 1


def test_organization_switch_success_is_tenant_scoped(services) -> None:
    organization_service = services["organization_service"]
    tenant_context = services["tenant_context_service"]
    user_session = services["user_session"]
    current = user_session.principal
    assert current is not None
    old_organization_id = current.active_organization_id
    target = organization_service.create_organization(
        organization_code="AUDIT-ORG",
        display_name="Audited Organization",
        is_active=True,
    )

    tenant_context.set_active_organization(target.id)

    assert user_session.active_organization_id() == target.id
    rows = _audit_rows(
        services["session"],
        "auth.context.organization.switched",
        actor_id=current.user_id,
    )
    assert len(rows) == 1
    row = rows[0]
    metadata = json.loads(row.metadata_json)
    assert row.tenant_id == user_session.active_tenant_id()
    assert row.organization_id == target.id
    assert row.field == "organization_id"
    assert row.old_value == old_organization_id
    assert row.new_value == target.id
    assert metadata["switch_type"] == "organization"
    assert metadata["outcome"] == "success"


def test_context_audit_failure_rolls_back_persisted_session_and_principal(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = services["auth_service"]
    tenant_context = services["tenant_context_service"]
    tenant_admin = services["tenant_admin_service"]
    user_session = services["user_session"]
    target = tenant_admin.create_tenant(
        "AUDIT-ROLLBACK",
        "Audit Rollback Tenant",
    )
    user = auth.authenticate("admin", "ChangeMe123!")
    session_id = user.active_session_id
    assert session_id is not None
    user_session.set_principal(
        auth.build_principal(user, session_id=session_id)
    )
    previous = user_session.principal
    assert previous is not None
    previous_tenant_id = previous.active_tenant_id
    previous_organization_id = previous.active_organization_id

    def _fail(*_args, **_kwargs) -> None:
        raise RuntimeError("context audit unavailable")

    monkeypatch.setattr(
        auth._security_audit_repo,
        "add_for_tenant",
        _fail,
    )

    with pytest.raises(BusinessRuleError) as exc:
        tenant_context.switch_to_tenant(target.id)

    assert exc.value.code == "CONTEXT_SWITCH_AUDIT_UNAVAILABLE"
    assert user_session.principal == previous
    persisted = auth._auth_session_repo.get(session_id)
    assert persisted is not None
    assert persisted.last_active_tenant_id == previous_tenant_id
    assert (
        persisted.last_active_organization_id
        == previous_organization_id
    )
    assert services["session"].scalar(
        select(func.count())
        .select_from(AuditEntryORM)
        .where(
            AuditEntryORM.operation
            == "auth.context.tenant.switched"
        )
    ) == 0


def test_tenant_switch_denial_is_durable_and_preserves_reason(services) -> None:
    auth = services["auth_service"]
    tenant_admin = services["tenant_admin_service"]
    tenant_context = services["tenant_context_service"]
    user_session = services["user_session"]
    target = tenant_admin.create_tenant(
        "ZZZ-AUDIT-DENIED",
        "Denied Switch Tenant",
    )
    user = auth.onboard_tenant_user(
        username="context-denied-user",
        raw_password="StrongPass123!",
    )
    user_session.set_principal(auth.build_principal(user))
    current_tenant_id = user_session.active_tenant_id()
    membership_ids = auth._user_tenant_repo.list_tenant_ids_for_user(user.id)
    assert current_tenant_id is not None
    assert current_tenant_id != target.id
    assert target.id not in membership_ids
    assert "platform.admin" not in user_session.principal.permissions

    with pytest.raises(BusinessRuleError) as exc:
        tenant_context.switch_to_tenant(target.id)

    assert exc.value.code == "TENANT_ACCESS_DENIED"
    assert user_session.active_tenant_id() == current_tenant_id
    rows = _audit_rows(
        services["session"],
        "auth.context.tenant.switch.denied",
        actor_id=user.id,
    )
    assert len(rows) == 1
    metadata = json.loads(rows[0].metadata_json)
    assert rows[0].tenant_id == current_tenant_id
    assert metadata["outcome"] == "denied"
    assert metadata["reason_code"] == "TENANT_ACCESS_DENIED"
    assert metadata["target_scope_type"] == "tenant"
    assert metadata["target_scope_id"] == target.id


def test_saas_switch_requires_audited_committer(services) -> None:
    tenant_context = services["tenant_context_service"]
    tenant_admin = services["tenant_admin_service"]
    user_session = services["user_session"]
    target = tenant_admin.create_tenant(
        "AUDIT-REQUIRED",
        "Audit Required Tenant",
    )
    previous = user_session.principal
    tenant_context._context_policy = SaaSTenantContextPolicy()
    tenant_context.set_context_switch_committer(None)

    with pytest.raises(BusinessRuleError) as exc:
        tenant_context.switch_to_tenant(target.id)

    assert exc.value.code == "CONTEXT_SWITCH_AUDIT_REQUIRED"
    assert user_session.principal == previous


def test_saas_context_lookup_requires_authentication_before_target_lookup(
    services,
) -> None:
    tenant_context = services["tenant_context_service"]
    user_session = services["user_session"]
    tenant_context._context_policy = SaaSTenantContextPolicy()
    user_session.clear()

    with pytest.raises(BusinessRuleError) as tenant_exc:
        tenant_context.set_active_tenant("nonexistent-tenant")
    with pytest.raises(BusinessRuleError) as organization_exc:
        tenant_context.set_active_organization("nonexistent-organization")

    assert tenant_exc.value.code == "AUTHENTICATION_REQUIRED"
    assert organization_exc.value.code == "AUTHENTICATION_REQUIRED"
