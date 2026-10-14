from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.contract.repositories.history.audit.contracts import (
    PlatformAuditWriter,
)
from src.core.platform.domain.history.audit import AuditEntry
from src.core.platform.domain.security.auth import (
    RolePermissionBinding,
    UserAccount,
    normalize_auth_username,
)
from src.core.platform.domain.security.auth.credentials.passwords import hash_password
from src.core.platform.domain.security.authorization.roles import (
    ROLE_SCOPE_PLATFORM,
    RoleBinding,
)

PLATFORM_OWNER_ROLE = "admin"
PLATFORM_OWNER_BOOTSTRAP_PERMISSION = "platform.admin"


@dataclass(frozen=True)
class PlatformOwnerProvisioningResult:
    user_id: str
    username: str
    created: bool
from sqlalchemy.orm import Session

from src.core.platform.application.security.auth.auth_validation_policy import (
    AuthValidationPolicy,
)
from src.core.platform.application.security.auth.provisioning.default_seed_service import (
    AuthPolicySeeder,
)
from src.core.platform.contract.repositories.security.auth import (
    PermissionRepository,
    RoleBindingRepository,
    RolePermissionRepository,
    UserRepository,
)


class PlatformOwnerProvisioningHandler:
    """Operator-run provisioning of the platform owner account and its platform role binding."""

    def __init__(
        self,
        *,
        session: Session,
        user_repo: UserRepository,
        permission_repo: PermissionRepository,
        role_permission_repo: RolePermissionRepository,
        role_binding_repo: RoleBindingRepository | None,
        validation_policy: AuthValidationPolicy,
        seeder: AuthPolicySeeder,
    ) -> None:
        self._session = session
        self._user_repo = user_repo
        self._permission_repo = permission_repo
        self._role_permission_repo = role_permission_repo
        self._role_binding_repo = role_binding_repo
        self._validation_policy = validation_policy
        self._seeder = seeder

    def _find_platform_owners(
        self,
        *,
        role_id: str,
    ) -> list[UserAccount]:
        if self._role_binding_repo is None:
            raise BusinessRuleError(
                "Canonical role-binding persistence is not configured.",
                code="AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED",
            )
        owners: list[UserAccount] = []
        for binding in self._role_binding_repo.list_active_for_role(
            role_id,
            tenant_id=None,
        ):
            user = self._user_repo.get(binding.principal_id)
            if user is not None:
                owners.append(user)
        return owners

    def provision_platform_owner(
        self,
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
            with self._session.begin_nested():
                role_map = self._seeder.ensure_auth_policy_definitions()
                owner_role = role_map[PLATFORM_OWNER_ROLE]
                bootstrap_permission = self._permission_repo.get_by_code(
                    PLATFORM_OWNER_BOOTSTRAP_PERMISSION
                )
                if bootstrap_permission is None:
                    raise BusinessRuleError(
                        "Platform-owner bootstrap permission is unavailable.",
                        code="PLATFORM_OWNER_BOOTSTRAP_POLICY_MISSING",
                    )
                owners = self._find_platform_owners(role_id=owner_role.id)
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
                    if not self._role_permission_repo.exists(
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
                    if self._user_repo.get_by_username(normalized_username) is not None:
                        raise BusinessRuleError(
                            "The requested username already exists and will not be promoted.",
                            code="PLATFORM_OWNER_USERNAME_EXISTS",
                        )
                    self._validation_policy.validate_password(raw_password)
                    owner = UserAccount.create(
                        username=normalized_username,
                        password_hash=hash_password(raw_password),
                        display_name=display_name,
                        email=email,
                        is_active=True,
                        must_change_password=True,
                    )
                    self._user_repo.add(owner)
                    self._session.flush()
                    if not self._role_permission_repo.exists(
                        owner_role.id,
                        bootstrap_permission.id,
                    ):
                        self._role_permission_repo.add(
                            RolePermissionBinding.create(
                                role_id=owner_role.id,
                                permission_id=bootstrap_permission.id,
                            )
                        )
                    if self._role_binding_repo is None:
                        raise BusinessRuleError(
                            "Canonical role-binding persistence is not configured.",
                            code="AUTHORIZATION_CANONICAL_REPOSITORY_REQUIRED",
                        )
                    self._role_binding_repo.add(
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
                            category="SECURITY",
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
            self._session.commit()
            return result
        except (BusinessRuleError, ValidationError, IntegrityError):
            self._session.rollback()
            raise
        except Exception:
            self._session.rollback()
            raise


__all__ = ["PlatformOwnerProvisioningHandler"]
