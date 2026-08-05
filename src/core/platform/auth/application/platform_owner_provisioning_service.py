from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from sqlalchemy.exc import IntegrityError

from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.auth.domain import (
    RolePermissionBinding,
    ROLE_SCOPE_PLATFORM,
    RoleBinding,
    UserAccount,
    normalize_auth_username,
)
from src.core.platform.domain.security.auth.credentials.passwords import hash_password
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError

from .default_seed_service import ensure_auth_policy_definitions

if TYPE_CHECKING:
    from .auth_service import AuthService


PLATFORM_OWNER_ROLE = "admin"
PLATFORM_OWNER_BOOTSTRAP_PERMISSION = "platform.admin"


class PlatformAuditWriter(Protocol):
    def add_platform(self, entry: AuditEntry) -> None: ...


@dataclass(frozen=True)
class PlatformOwnerProvisioningResult:
    user_id: str
    username: str
    created: bool


def _find_platform_owners(
    service: AuthService,
    *,
    role_id: str,
) -> list[UserAccount]:
    if service._role_binding_repo is None:
        raise BusinessRuleError(
            "Canonical role-binding persistence is not configured.",
            code="AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED",
        )
    owners: list[UserAccount] = []
    for binding in service._role_binding_repo.list_active_for_role(
        role_id,
        tenant_id=None,
    ):
        user = service._user_repo.get(binding.principal_id)
        if user is not None:
            owners.append(user)
    return owners


def provision_platform_owner(
    service: AuthService,
    *,
    username: str,
    raw_password: str,
    audit_writer: PlatformAuditWriter,
    display_name: str = "Platform Owner",
    email: str | None = None,
    provisioning_actor: str = "deployment",
) -> PlatformOwnerProvisioningResult:
    normalized_username = normalize_auth_username(username)
    normalized_actor = str(provisioning_actor or "").strip() or "deployment"
    try:
        with service._session.begin_nested():
            role_map = ensure_auth_policy_definitions(service)
            owner_role = role_map[PLATFORM_OWNER_ROLE]
            bootstrap_permission = service._permission_repo.get_by_code(
                PLATFORM_OWNER_BOOTSTRAP_PERMISSION
            )
            if bootstrap_permission is None:
                raise BusinessRuleError(
                    "Platform-owner bootstrap permission is unavailable.",
                    code="PLATFORM_OWNER_BOOTSTRAP_POLICY_MISSING",
                )
            owners = _find_platform_owners(service, role_id=owner_role.id)
            if len(owners) > 1:
                raise BusinessRuleError(
                    "Multiple platform owners already exist; provisioning cannot continue.",
                    code="PLATFORM_OWNER_AMBIGUOUS",
                )
            if owners:
                owner = owners[0]
                if owner.username != normalized_username:
                    raise BusinessRuleError(
                        "A platform owner already exists.",
                        code="PLATFORM_OWNER_EXISTS",
                    )
                if not service._role_permission_repo.exists(
                    owner_role.id,
                    bootstrap_permission.id,
                ):
                    raise BusinessRuleError(
                        "The existing platform owner lacks bootstrap policy "
                        "authority and requires operator recovery.",
                        code="PLATFORM_OWNER_BOOTSTRAP_AUTHORITY_MISSING",
                    )
                result = PlatformOwnerProvisioningResult(
                    user_id=owner.id,
                    username=owner.username,
                    created=False,
                )
            else:
                if service._user_repo.get_by_username(normalized_username) is not None:
                    raise BusinessRuleError(
                        "The requested username already exists and will not be promoted.",
                        code="PLATFORM_OWNER_USERNAME_EXISTS",
                    )
                service._validate_password(raw_password)
                owner = UserAccount.create(
                    username=normalized_username,
                    password_hash=hash_password(raw_password),
                    display_name=display_name,
                    email=email,
                    is_active=True,
                    must_change_password=True,
                )
                service._user_repo.add(owner)
                service._session.flush()
                if not service._role_permission_repo.exists(
                    owner_role.id,
                    bootstrap_permission.id,
                ):
                    service._role_permission_repo.add(
                        RolePermissionBinding.create(
                            role_id=owner_role.id,
                            permission_id=bootstrap_permission.id,
                        )
                    )
                if service._role_binding_repo is None:
                    raise BusinessRuleError(
                        "Canonical role-binding persistence is not configured.",
                        code="AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED",
                    )
                service._role_binding_repo.add(
                    RoleBinding.create(
                        principal_id=owner.id,
                        role_id=owner_role.id,
                        actual_scope_type=ROLE_SCOPE_PLATFORM,
                    )
                )
                audit_writer.add_platform(
                    AuditEntry.create(
                        operation="platform_owner.provision",
                        entity_type="user",
                        entity_id=owner.id,
                        module="platform",
                        actor_type="deployment",
                        actor_username=normalized_actor,
                        source="provisioning_cli",
                        severity="critical",
                        compliance_tag="SOC2",
                        metadata={
                            "username": owner.username,
                            "role_name": PLATFORM_OWNER_ROLE,
                            "bootstrap_permission_code": (
                                PLATFORM_OWNER_BOOTSTRAP_PERMISSION
                            ),
                            "must_change_password": True,
                            "provisioning_version": 2,
                        },
                    )
                )
                result = PlatformOwnerProvisioningResult(
                    user_id=owner.id,
                    username=owner.username,
                    created=True,
                )
        service._session.commit()
        return result
    except (BusinessRuleError, ValidationError, IntegrityError):
        service._session.rollback()
        raise
    except Exception:
        service._session.rollback()
        raise


__all__ = [
    "PLATFORM_OWNER_ROLE",
    "PLATFORM_OWNER_BOOTSTRAP_PERMISSION",
    "PlatformAuditWriter",
    "PlatformOwnerProvisioningResult",
    "provision_platform_owner",
]
