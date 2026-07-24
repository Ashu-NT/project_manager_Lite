from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.shared.security import (
    Permissions,
    requires_all_permissions,
    requires_any_permission,
    requires_permission,
)


class _SessionWithPrincipal:
    def __init__(self, permissions: list[str]):
        self._permissions = set(permissions)

    def has_permission(self, code: str) -> bool:
        return code in self._permissions


class _ServiceWithPermission:
    def __init__(self, permissions: list[str]):
        self._user_session = _SessionWithPrincipal(permissions)
        self.called = False

    @requires_permission("audit.read")
    def read_audit(self) -> str:
        self.called = True
        return "ok"

    @requires_any_permission(("audit.read", "settings.manage"))
    def read_or_manage(self) -> str:
        self.called = True
        return "ok"

    @requires_all_permissions(("audit.read", "settings.manage"))
    def read_and_manage(self) -> str:
        self.called = True
        return "ok"


def test_requires_permission_allows_holder():
    svc = _ServiceWithPermission(["audit.read"])
    result = svc.read_audit()
    assert result == "ok"
    assert svc.called


def test_requires_permission_blocks_non_holder():
    svc = _ServiceWithPermission(["settings.manage"])
    with pytest.raises(BusinessRuleError):
        svc.read_audit()
    assert not svc.called


def test_requires_any_permission_allows_first_match():
    svc = _ServiceWithPermission(["audit.read"])
    result = svc.read_or_manage()
    assert result == "ok"


def test_requires_any_permission_allows_second_match():
    svc = _ServiceWithPermission(["settings.manage"])
    result = svc.read_or_manage()
    assert result == "ok"


def test_requires_any_permission_blocks_no_match():
    svc = _ServiceWithPermission(["employee.manage"])
    with pytest.raises(BusinessRuleError):
        svc.read_or_manage()


def test_requires_all_permissions_allows_when_all_held():
    svc = _ServiceWithPermission(["audit.read", "settings.manage"])
    result = svc.read_and_manage()
    assert result == "ok"


def test_requires_all_permissions_blocks_when_missing_one():
    svc = _ServiceWithPermission(["audit.read"])
    with pytest.raises(BusinessRuleError):
        svc.read_and_manage()


def test_permissions_constants_are_strings():
    assert isinstance(Permissions.AUDIT_READ, str)
    assert isinstance(Permissions.AUTH_MANAGE, str)
    assert isinstance(Permissions.TASK_MANAGE, str)


def test_requires_permission_no_session():
    class _NoSession:
        _user_session = None

        @requires_permission("audit.read")
        def action(self) -> str:
            return "ok"

    with pytest.raises(BusinessRuleError):
        _NoSession().action()
