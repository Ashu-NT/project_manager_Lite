from __future__ import annotations

from dataclasses import dataclass

from core.platform.access.authorization import filter_scope_rows, require_scope_permission
from core.platform.auth.authorization import require_permission
from core.platform.auth.session import UserSessionContext, UserSessionPrincipal
from core.platform.authorization import SessionAuthorizationEngine, get_authorization_engine, set_authorization_engine


@dataclass
class _ScopeRow:
    scope_id: str


class _AllowAllAuthorizationEngine:
    def has_permission(self, user_session, permission_code, *, resource=None, context=None) -> bool:
        return True

    def has_any_permission(self, user_session, permission_codes, *, resource=None, context=None) -> bool:
        return True

    def is_admin_session(self, user_session) -> bool:
        return True

    def has_scope_permission(
        self,
        user_session,
        scope_type: str,
        scope_id: str,
        permission_code: str,
        *,
        resource=None,
        context=None,
    ) -> bool:
        return True

    def scope_ids_for(self, user_session, scope_type: str, permission_code: str, *, resource=None, context=None) -> set[str]:
        return {"scope-a", "scope-b"}

    def is_scope_restricted(self, user_session, scope_type: str, *, resource=None, context=None) -> bool:
        return False

    def filter_scope_rows(
        self,
        rows,
        user_session,
        *,
        scope_type: str,
        permission_code: str,
        scope_id_getter,
        resource_type: str | None = None,
        context=None,
    ):
        return list(rows)


def test_session_authorization_engine_filters_restricted_scope_rows():
    engine = SessionAuthorizationEngine()
    session = UserSessionContext()
    session.set_principal(
        UserSessionPrincipal(
            user_id="user-1",
            username="restricted-user",
            display_name=None,
            role_names=frozenset({"inventory_manager"}),
            permissions=frozenset({"inventory.read"}),
            scoped_access={"storeroom": {"scope-a": frozenset({"inventory.read"})}},
        )
    )

    rows = [_ScopeRow("scope-a"), _ScopeRow("scope-b")]

    filtered = engine.filter_scope_rows(
        rows,
        session,
        scope_type="storeroom",
        permission_code="inventory.read",
        scope_id_getter=lambda row: row.scope_id,
    )

    assert [row.scope_id for row in filtered] == ["scope-a"]


def test_authorization_helpers_delegate_to_shared_engine_override():
    previous_engine = get_authorization_engine()
    set_authorization_engine(_AllowAllAuthorizationEngine())
    try:
        require_permission(None, "audit.read", operation_label="view audit log")
        require_scope_permission(
            None,
            "project",
            "project-1",
            "task.read",
            operation_label="view project tasks",
        )
        rows = filter_scope_rows(
            [_ScopeRow("scope-a"), _ScopeRow("scope-b")],
            None,
            scope_type="storeroom",
            permission_code="inventory.read",
            scope_id_getter=lambda row: row.scope_id,
        )
        assert [row.scope_id for row in rows] == ["scope-a", "scope-b"]
    finally:
        set_authorization_engine(previous_engine)
