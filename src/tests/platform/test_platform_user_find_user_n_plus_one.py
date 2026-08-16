"""regression guardrail for the confirmed N+1 in
PlatformUserDesktopApi._find_user (removed; formerly in
src/core/platform/api/desktop/security/auth/user.py).
"""
from __future__ import annotations

from src.core.platform.api.desktop.security.auth.models.user import (
    UserCreateCommand,
    UserPasswordResetCommand,
)
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi


def _make_users(api, n, prefix):
    ids = []
    for i in range(n):
        r = api.create_user(
            UserCreateCommand(
                username=f"{prefix}-{i}",
                password="StrongPass123",
                display_name=f"{prefix} {i}",
                email=f"{prefix}{i}@example.com",
            )
        )
        assert r.ok is True, r.error
        ids.append(r.data.id)
    return ids


def _instrument(user_repo):
    """Wrap list_all()/list_for_tenant() on this instance's class with
    counters and row-hydration totals. Returns (counts, hydrated, restore)."""
    counts = {"list_all": 0, "list_for_tenant": 0}
    hydrated = {"n": 0}
    cls = type(user_repo)
    real_list_all = cls.list_all
    real_list_for_tenant = cls.list_for_tenant

    def counting_list_all(self, *args, **kwargs):
        counts["list_all"] += 1
        rows = real_list_all(self, *args, **kwargs)
        hydrated["n"] += len(rows)
        return rows

    def counting_list_for_tenant(self, *args, **kwargs):
        counts["list_for_tenant"] += 1
        rows = real_list_for_tenant(self, *args, **kwargs)
        hydrated["n"] += len(rows)
        return rows

    cls.list_all = counting_list_all
    cls.list_for_tenant = counting_list_for_tenant

    def restore():
        cls.list_all = real_list_all
        cls.list_for_tenant = real_list_for_tenant

    return counts, hydrated, restore


def _do_writes(api, user_id):
    """Exercise all three _find_user call sites that used to exist."""
    assign_result = api.assign_role(user_id, "planner")
    assert assign_result.ok is True, assign_result.error
    revoke_result = api.revoke_role(user_id, "planner")
    assert revoke_result.ok is True, revoke_result.error
    reset_result = api.reset_password(
        UserPasswordResetCommand(user_id=user_id, new_password="EvenStronger123")
    )
    assert reset_result.ok is True, reset_result.error
    return assign_result, revoke_result, reset_result


def test_assign_revoke_reset_never_list_the_full_user_collection(services):
    api = PlatformUserDesktopApi(auth_service=services["auth_service"])
    user_repo = services["auth_service"]._user_repo

    [small_target] = _make_users(api, 1, "small")
    counts, hydrated, restore = _instrument(user_repo)
    try:
        _do_writes(api, small_target)
    finally:
        restore()
    assert counts == {"list_all": 0, "list_for_tenant": 0}, (
        "assign_role/revoke_role/reset_password must never call list_all()/"
        f"list_for_tenant() -- got {counts}"
    )
    assert hydrated["n"] == 0

    large_ids = _make_users(api, 30, "large")
    large_target = large_ids[0]
    counts, hydrated, restore = _instrument(user_repo)
    try:
        _do_writes(api, large_target)
    finally:
        restore()
    assert counts == {"list_all": 0, "list_for_tenant": 0}, (
        "the defect must not reappear once the tenant has many users -- "
        f"got {counts}"
    )
    assert hydrated["n"] == 0, (
        f"expected zero rows hydrated by a full-collection scan, got {hydrated['n']} -- "
        "the query cost must stay independent of total tenant user count"
    )


def test_assign_revoke_reset_return_the_exact_affected_user_unchanged(services):
    """Guards the desktop response shape itself, not just the query cost --
    a naive 'return None' regression would break every one of these."""
    api = PlatformUserDesktopApi(auth_service=services["auth_service"])

    [user_id] = _make_users(api, 1, "shape")
    assign_result, revoke_result, reset_result = _do_writes(api, user_id)

    assert assign_result.data.id == user_id
    assert "planner" in assign_result.data.role_names
    assert revoke_result.data.id == user_id
    assert "planner" not in revoke_result.data.role_names
    assert reset_result.data.id == user_id
    assert reset_result.data.must_change_password is True
