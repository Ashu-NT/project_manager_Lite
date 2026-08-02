from __future__ import annotations

import pytest

from src.api.desktop.platform import (
    ApiKeyIssueCommand,
    ServicePrincipalCreateCommand,
)
from src.api.desktop.runtime import build_desktop_api_registry
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError


def test_service_principal_api_key_lifecycle_uses_canonical_authority(services):
    identity = services["service_principal_service"]
    auth = services["auth_service"]

    principal = identity.create_service_principal(
        name="Planning Integration",
        initial_role_name="viewer",
    )
    service_user = auth._user_repo.get(principal.user_id)

    assert service_user is not None
    assert service_user.account_type == "service"
    assert services["tenant_context_service"].get_active_tenant_id() == principal.tenant_id
    assert services["tenant_context_service"].get_active_organization_id() == principal.organization_id
    assert services["auth_service"].get_user_role_names(service_user.id) == {"viewer"}

    permission_code = sorted(auth.get_user_permissions(service_user.id))[0]
    issued = identity.issue_api_key(
        principal.id,
        name="Automation",
        permission_scopes=(permission_code,),
        expires_in_days=30,
    )
    assert issued.token.startswith(f"pmk_{principal.tenant_id}_")
    authenticated = identity.authenticate_api_key(issued.token)

    assert authenticated.user_id == principal.user_id
    assert authenticated.identity_provider == "api_key"
    assert authenticated.permissions == frozenset({permission_code})
    assert authenticated.session_id == issued.credential.id

    rotated = identity.rotate_api_key(issued.credential.id, expires_in_days=45)
    with pytest.raises(ValidationError) as old_key_error:
        identity.authenticate_api_key(issued.token)
    assert old_key_error.value.code == "API_KEY_REVOKED"
    assert identity.authenticate_api_key(rotated.token).user_id == principal.user_id

    disabled = identity.disable_service_principal(principal.id)
    assert disabled.status == "disabled"
    with pytest.raises(ValidationError) as disabled_error:
        identity.authenticate_api_key(rotated.token)
    assert disabled_error.value.code == "API_KEY_REVOKED"


def test_service_account_cannot_use_human_password_login(services):
    auth = services["auth_service"]
    tenant_id = services["tenant_context_service"].get_active_tenant_id()
    user = auth.register_user(
        username="service-password-denied",
        raw_password="KnownServicePassword123!",
        display_name="Service Password Denied",
        role_names=("viewer",),
        tenant_id=tenant_id,
        account_type="service",
    )

    with pytest.raises(ValidationError) as exc_info:
        auth.authenticate(user.username, "KnownServicePassword123!")
    assert exc_info.value.code == "AUTH_FAILED"


def test_api_key_permissions_cannot_exceed_service_principal(services):
    identity = services["service_principal_service"]
    principal = identity.create_service_principal(
        name="Read Only Integration",
        initial_role_name="viewer",
    )

    with pytest.raises(BusinessRuleError) as exc_info:
        identity.issue_api_key(
            principal.id,
            name="Escalated",
            permission_scopes=("platform.admin",),
        )
    assert exc_info.value.code == "API_KEY_PERMISSION_CEILING_EXCEEDED"


def test_desktop_identity_adapter_exposes_management_without_secret_hash(services):
    api = build_desktop_api_registry(services).platform_identity
    created = api.create_service_principal(
        ServicePrincipalCreateCommand(name="Desktop Integration")
    )
    assert created.ok is True
    assert created.data is not None

    permission_code = sorted(
        services["auth_service"].get_user_permissions(created.data.user_id)
    )[0]
    issued = api.issue_api_key(
        ApiKeyIssueCommand(
            service_principal_id=created.data.id,
            name="Desktop Key",
            permission_scopes=(permission_code,),
        )
    )
    assert issued.ok is True
    assert issued.data is not None
    assert issued.data.token.startswith("pmk_")
    assert not hasattr(issued.data.credential, "secret_hash")
