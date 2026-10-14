from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from src.core.platform.application.security.auth import (
    AuthenticationHandler,
    AuthSessionCommandHandler,
    AuthSessionQueryHandler,
    AuthTransactionScope,
    AuthValidationPolicy,
    UserAdministrationCommandHandler,
    UserRegistrationHandler,
)
from src.core.platform.application.security.auth.credentials.authentication_transactions import (
    AuthenticationTransactions,
)
from src.core.platform.application.security.auth.session.principal_builder import (
    PrincipalBuilder,
)
from src.core.platform.application.security.auth.session.session_lifecycle import (
    AuthSessionLifecycle,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.security.auth import (
    AuthSession,
    Permission,
    Role,
    RolePermissionBinding,
    UserAccount,
)
from src.core.platform.domain.security.auth.user import (
    normalize_auth_session_timeout_override,
)
from src.core.platform.infrastructure.composition.dependencies.security.auth import (
    build_auth_query_handler,
)
from src.core.platform.infrastructure.persistence.uow.security.auth_unit_of_work import (
    SqlAlchemyAuthUnitOfWorkFactory,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.time.system_clock import SystemClock


class _FakeNestedTransaction:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakeSession:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.rollback_calls = 0

    def begin_nested(self) -> _FakeNestedTransaction:
        return _FakeNestedTransaction()

    def flush(self) -> None:
        return None

    def close(self) -> None:
        return None

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


class _FakeUserRepo:
    def __init__(self) -> None:
        self._rows: dict[str, UserAccount] = {}

    def add(self, user: UserAccount) -> None:
        self._rows[user.id] = user

    def update(self, user: UserAccount) -> None:
        self._rows[user.id] = user

    def get(self, user_id: str) -> UserAccount | None:
        return self._rows.get(user_id)

    def get_by_username(self, username: str) -> UserAccount | None:
        for row in self._rows.values():
            if row.username == username:
                return row
        return None

    def get_by_federated_identity(
        self,
        identity_provider: str,
        federated_subject: str,
    ) -> UserAccount | None:
        for row in self._rows.values():
            if row.identity_provider == identity_provider and row.federated_subject == federated_subject:
                return row
        return None

    def list_all(self) -> list[UserAccount]:
        return list(self._rows.values())


class _FakeRoleRepo:
    def __init__(self) -> None:
        self._viewer = Role.create(name="viewer", description="Viewer")
        self._rows = {self._viewer.id: self._viewer}

    def add(self, role: Role) -> None:
        self._rows[role.id] = role

    def get(self, role_id: str) -> Role | None:
        return self._rows.get(role_id)

    def get_by_name(self, name: str) -> Role | None:
        for row in self._rows.values():
            if row.name == name:
                return row
        return None

    def list_all(self) -> list[Role]:
        return list(self._rows.values())


class _FakePermissionRepo:
    def add(self, permission) -> None:
        return None

    def get(self, permission_id: str):
        return None

    def get_by_code(self, code: str):
        return None

    def list_all(self) -> list[object]:
        return []


class _FakeRolePermissionRepo:
    def add(self, binding) -> None:
        return None

    def delete(self, role_id: str, permission_id: str) -> None:
        return None

    def exists(self, role_id: str, permission_id: str) -> bool:
        return False

    def list_permission_ids(self, role_id: str) -> list[str]:
        return []


class _FakeAuthSessionRepo:
    def __init__(self) -> None:
        self._rows: dict[str, AuthSession] = {}

    def add(self, auth_session: AuthSession) -> None:
        self._rows[auth_session.id] = auth_session

    def update(self, auth_session: AuthSession) -> None:
        self._rows[auth_session.id] = auth_session

    def get(self, session_id: str) -> AuthSession | None:
        return self._rows.get(session_id)

    def list_by_user(self, user_id: str) -> list[AuthSession]:
        return [row for row in self._rows.values() if row.user_id == user_id]

    def persist_context(
        self,
        session_id: str,
        *,
        last_active_tenant_id: str | None,
        last_active_organization_id: str | None,
        updated_at: datetime,
    ) -> bool:
        auth_session = self._rows.get(session_id)
        if auth_session is None:
            return False
        auth_session.last_active_tenant_id = last_active_tenant_id
        auth_session.last_active_organization_id = last_active_organization_id
        auth_session.updated_at = updated_at
        return True

    def touch_validation(
        self,
        session_id: str,
        *,
        validated_at: datetime,
        throttle_seconds: int = 60,
    ) -> bool:
        auth_session = self._rows.get(session_id)
        if auth_session is None:
            return False
        auth_session.last_validated_at = validated_at
        auth_session.updated_at = validated_at
        return True

AUTH = "src.core.platform.application.security.auth"


class _NoopAudit:
    def add_atomic_security_audit(self, **_kwargs) -> None:
        return None

    def add_atomic_system_security_audit(self, **_kwargs) -> None:
        return None

    def add_atomic_auth_event(self, **_kwargs) -> None:
        return None


class _OpenTargetUsers:
    def require_target_user_in_active_tenant(self, *_args, **_kwargs) -> str:
        return ""

    def require_actor_active_tenant(self, *_args, **_kwargs) -> str:
        return ""

    def is_platform_operator(self) -> bool:
        return True


class _NoSod:
    def enforce(self, _role_names) -> None:
        return None


def _make_auth_handlers(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    for module in ("commands.registration", "commands.user_administration"):
        monkeypatch.setattr(f"src.core.platform.application.security.auth.{module}.require_permission", lambda *args, **kwargs: None)
    for module in ("commands.user_administration", "commands.sessions", "queries.sessions"):
        monkeypatch.setattr(
            f"src.core.platform.application.security.auth.{module}.require_any_permission", lambda *args, **kwargs: None
        )
    monkeypatch.setattr(
        "src.core.platform.application.security.auth.commands.registration.hash_password",
        lambda raw_password: f"hash::{raw_password}",
    )
    monkeypatch.setattr(
        "src.core.platform.application.security.auth.commands.authentication.verify_password",
        lambda raw_password, password_hash: password_hash == f"hash::{raw_password}",
    )

    user_repo = _FakeUserRepo()
    role_repo = _FakeRoleRepo()
    auth_session_repo = _FakeAuthSessionRepo()
    auth_queries = build_auth_query_handler(
        user_repo=user_repo,
        role_repo=role_repo,
        permission_repo=_FakePermissionRepo(),
        role_permission_repo=_FakeRolePermissionRepo(),
        role_binding_repo=None,
    )
    tx = AuthTransactionScope(
        session=_FakeSession(),
        uow_factory=SqlAlchemyAuthUnitOfWorkFactory(),
        transactional_dispatcher=InProcessTransactionalEventDispatcher(),
        post_commit_bus=InProcessPostCommitEventBus(),
        tenant_context_service=None,
    )
    audit = _NoopAudit()
    target_users = _OpenTargetUsers()
    principals = PrincipalBuilder(
        auth_queries=auth_queries,
        auth_session_repo=auth_session_repo,
        tenant_context_service=None,
    )
    lifecycle = AuthSessionLifecycle(
        user_repo=user_repo,
        auth_session_repo=auth_session_repo,
        user_session=None,
        principals=principals,
    )
    account_change = dict(
        tx=tx,
        auth_queries=auth_queries,
        user_repo=user_repo,
        user_session=None,
        target_users=target_users,
        audit=audit,
        lifecycle=lifecycle,
    )
    return SimpleNamespace(
        registration=UserRegistrationHandler(
            tx=tx,
            clock=SystemClock(),
            auth_queries=auth_queries,
            user_repo=user_repo,
            role_repo=role_repo,
            role_binding_repo=None,
            security_audit_repo=None,
            user_session=None,
            tenant_context_service=None,
            user_tenant_repo=None,
            validation_policy=AuthValidationPolicy(),
            audit=audit,
            sod=_NoSod(),
            target_users=target_users,
        ),
        user_administration=UserAdministrationCommandHandler(**account_change),
        session_commands=AuthSessionCommandHandler(
            tx=tx,
            auth_queries=auth_queries,
            user_repo=user_repo,
            auth_session_repo=auth_session_repo,
            user_session=None,
            target_users=target_users,
            audit=audit,
            lifecycle=lifecycle,
            principals=principals,
        ),
        session_queries=AuthSessionQueryHandler(
            auth_queries=auth_queries,
            auth_session_repo=auth_session_repo,
            user_session=None,
            target_users=target_users,
        ),
        authentication=AuthenticationHandler(
            user_repo=user_repo,
            transactions=AuthenticationTransactions(
                tx=tx,
                user_repo=user_repo,
                auth_session_repo=auth_session_repo,
                user_session=None,
                tenant_context_service=None,
                principals=principals,
                lifecycle=lifecycle,
                audit=audit,
            ),
        ),
    )


def test_user_account_dto_normalizes_and_validates_fields():
    user = UserAccount.create(
        "  Alice.Admin  ",
        "  hash-value  ",
        display_name="  Alice Admin  ",
        email="  USER.Name@Example.COM  ",
        identity_provider="  AzureAD  ",
        federated_subject="  oidc-user-1  ",
        session_timeout_minutes_override="30",
        must_change_password="1",
    )

    assert user.username == "alice.admin"
    assert user.password_hash == "hash-value"
    assert user.display_name == "Alice Admin"
    assert user.email == "user.name@example.com"
    assert user.identity_provider == "azuread"
    assert user.federated_subject == "oidc-user-1"
    assert user.session_timeout_minutes_override == 30
    assert user.must_change_password is True
    assert user.created_at is not None
    assert user.updated_at is not None

    with pytest.raises(ValidationError) as exc_email:
        UserAccount.create(
            "alice",
            "hash",
            email="not-an-email",
        )
    assert exc_email.value.code == "INVALID_EMAIL"

    with pytest.raises(ValidationError) as exc_federated:
        UserAccount.create(
            "alice",
            "hash",
            identity_provider="azuread",
        )
    assert exc_federated.value.code == "FEDERATED_IDENTITY_INCOMPLETE"

    with pytest.raises(ValidationError) as exc_timeout:
        normalize_auth_session_timeout_override("2")
    assert exc_timeout.value.code == "AUTH_SESSION_TIMEOUT_INVALID"


def test_auth_session_dto_normalizes_and_validates_fields():
    auth_session = AuthSession.create(
        user_id="  user-1  ",
        session_revision="2",
        auth_method="  Password  ",
        expires_at=datetime(2026, 7, 26, 9, 30, 0),
        device_label="  Office Laptop  ",
        last_active_tenant_id="  tenant-1  ",
        last_active_organization_id="  org-1  ",
    )

    assert auth_session.user_id == "user-1"
    assert auth_session.session_revision == 2
    assert auth_session.auth_method == "password"
    assert auth_session.device_label == "Office Laptop"
    assert auth_session.last_active_tenant_id == "tenant-1"
    assert auth_session.last_active_organization_id == "org-1"
    assert auth_session.expires_at is not None
    assert auth_session.expires_at.tzinfo is not None

    with pytest.raises(ValidationError) as exc_expires:
        AuthSession.create(
            user_id="user-1",
            session_revision=1,
            auth_method="password",
            expires_at=None,
        )
    assert exc_expires.value.code == "AUTH_SESSION_EXPIRES_AT_INVALID"


def test_auth_rbac_dtos_normalize_and_validate_fields():
    role = Role.create(
        name="  TENANT_ADMIN  ",
        description="  Tenant-level administrator  ",
        is_system="0",
        tenant_id="  tenant-1  ",
    )
    permission = Permission.create(
        code="  AUDIT.READ  ",
        description="  Read audit logs  ",
    )
    role_permission = RolePermissionBinding.create(
        role_id="  role-1  ",
        permission_id="  permission-1  ",
    )

    assert role.name == "tenant_admin"
    assert role.description == "Tenant-level administrator"
    assert role.is_system is False
    assert role.tenant_id == "tenant-1"
    assert permission.code == "audit.read"
    assert permission.description == "Read audit logs"
    assert role_permission.role_id == "role-1"
    assert role_permission.permission_id == "permission-1"

    role.name = "  VIEWER  "
    assert role.name == "viewer"

    with pytest.raises(ValidationError) as exc_role:
        Role.create(name=" ", description="x")
    assert exc_role.value.code == "AUTH_ROLE_NAME_REQUIRED"

    with pytest.raises(ValidationError) as exc_permission:
        Permission.create(code=" ", description="x")
    assert exc_permission.value.code == "AUTH_PERMISSION_CODE_REQUIRED"

    with pytest.raises(ValidationError) as exc_permission_id:
        RolePermissionBinding.create(role_id="role-1", permission_id=" ")
    assert exc_permission_id.value.code == "PERMISSION_ID_REQUIRED"


def test_auth_service_uses_entity_validation_for_user_and_session_models(
    monkeypatch: pytest.MonkeyPatch,
):
    auth = _make_auth_handlers(monkeypatch)

    user = auth.registration.register_user(
        "  Alice  ",
        "StrongPass123",
        display_name="  Alice Admin  ",
        email="  USER.Name@Example.COM  ",
        role_names=[],
        must_change_password=True,
        identity_provider="  AzureAD  ",
        federated_subject="  oidc-user-1  ",
        session_timeout_minutes_override="30",
    )

    assert user.username == "alice"
    assert user.display_name == "Alice Admin"
    assert user.email == "user.name@example.com"
    assert user.identity_provider == "azuread"
    assert user.federated_subject == "oidc-user-1"
    assert user.session_timeout_minutes_override == 30
    assert user.must_change_password is True

    updated = auth.user_administration.update_user_profile(
        user.id,
        username="  Alice-Prime  ",
        display_name="  Alice Prime  ",
        email="  ALICE.PRIME@EXAMPLE.COM  ",
    )
    assert updated.username == "alice-prime"
    assert updated.display_name == "Alice Prime"
    assert updated.email == "alice.prime@example.com"

    policy_user = auth.session_commands.set_user_session_policy(
        user.id,
        session_timeout_minutes_override="45",
    )
    assert policy_user.session_timeout_minutes_override == 45

    authenticated = auth.authentication.authenticate(
        "alice-prime",
        "StrongPass123",
        device_label="  Office Laptop  ",
    )
    assert authenticated.last_login_device_label == "Office Laptop"
    assert authenticated.last_login_auth_method == "password"
    assert authenticated.active_session_id is not None

    sessions = auth.session_queries.list_user_sessions(user.id)
    assert len(sessions) == 1
    assert sessions[0].device_label == "Office Laptop"
    assert sessions[0].auth_method == "password"
    assert sessions[0].session_revision == authenticated.session_revision

    with pytest.raises(ValidationError) as exc_email:
        auth.registration.register_user(
            "invalid-email-user",
            "StrongPass123",
            email="not-an-email",
        )
    assert exc_email.value.code == "INVALID_EMAIL"
