from __future__ import annotations

from dataclasses import replace

import pytest

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth.session import UserSessionContext


def test_explicit_history_reads_require_organization_membership_and_permission(services) -> None:
    organizations = services["organization_service"]
    context = services["tenant_context_service"]
    activity = services["activity_service"]
    audit = services["enterprise_audit_service"]

    allowed = organizations.create_organization(
        organization_code="HIST-ALLOWED",
        display_name="History Allowed",
        timezone_name="UTC",
        base_currency="USD",
    )
    denied = organizations.create_organization(
        organization_code="HIST-DENIED",
        display_name="History Denied",
        timezone_name="UTC",
        base_currency="USD",
    )
    context.set_active_organization(allowed.id)

    original_session = context._user_session
    principal = services["user_session"].principal
    assert principal is not None
    restricted_session = UserSessionContext()
    restricted_session.set_principal(
        replace(
            principal,
            role_names=frozenset(),
            permissions=principal.permissions | frozenset({"activity.read", "audit.read"}),
            scoped_access={
                "organization": {
                    allowed.id: frozenset({"activity.read", "audit.read"}),
                }
            },
            active_organization_id=allowed.id,
        )
    )
    context._user_session = restricted_session
    try:
        assert activity.list_recent_page_for_organization(allowed.id).items is not None
        assert isinstance(audit.list_recent_for_organization_id(allowed.id), list)
        with pytest.raises(BusinessRuleError, match="Permission denied"):
            activity.list_recent_page_for_organization(denied.id)
        with pytest.raises(BusinessRuleError, match="Permission denied"):
            audit.list_recent_for_organization_id(denied.id)
        with pytest.raises(BusinessRuleError, match="Organization is required"):
            activity.list_recent_page_for_organization(" ")
    finally:
        context._user_session = original_session


def test_explicit_audit_read_requires_audit_permission_in_member_organization(services) -> None:
    organizations = services["organization_service"]
    context = services["tenant_context_service"]
    org = organizations.create_organization(
        organization_code="HIST-SCOPE-ONLY",
        display_name="History Scope Only",
        timezone_name="UTC",
        base_currency="USD",
    )
    context.set_active_organization(org.id)
    original_session = context._user_session
    principal = services["user_session"].principal
    assert principal is not None
    restricted_session = UserSessionContext()
    restricted_session.set_principal(
        replace(
            principal,
            role_names=frozenset(),
            permissions=principal.permissions | frozenset({"activity.read", "audit.read"}),
            scoped_access={"organization": {org.id: frozenset({"activity.read"})}},
            active_organization_id=org.id,
        )
    )
    context._user_session = restricted_session
    try:
        with pytest.raises(BusinessRuleError, match="Permission denied"):
            services["enterprise_audit_service"].list_recent_for_organization_id(org.id)
        with pytest.raises(BusinessRuleError, match="Permission denied"):
            services["enterprise_audit_service"].list_recent()
    finally:
        context._user_session = original_session
