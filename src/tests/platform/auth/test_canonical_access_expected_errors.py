import ast
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.access import scope_permissions
from src.core.platform.access import authorization
from src.core.platform.application.security.authorization.enforcement import (
    permission_checks,
)
from src.core.platform.common import exceptions
from src.core.platform.common.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    ConfigurationError,
    DomainError,
)


@pytest.mark.parametrize(
    "error_type,default_code",
    [
        (AuthenticationError, "AUTHENTICATION_REQUIRED"),
        (AuthorizationError, "PERMISSION_DENIED"),
        (ConfigurationError, "CONFIGURATION_ERROR"),
    ],
)
def test_stable_codes_and_exception_chaining(error_type, default_code):
    assert error_type("safe").code == default_code
    cause = ValueError("internal evidence")
    with pytest.raises(error_type) as caught:
        try:
            raise cause
        except ValueError as exc:
            raise error_type("safe", code="SPECIFIC_CODE") from exc
    assert caught.value.code == "SPECIFIC_CODE"
    assert str(caught.value) == "safe"
    assert caught.value.__cause__ is cause
    assert isinstance(caught.value, DomainError)


def test_access_types_are_distinct_and_classified_before_business_rules():
    for error in (AuthenticationError("sign in"), AuthorizationError("denied")):
        assert isinstance(error, BusinessRuleError)
        assert not isinstance(error, ConfigurationError)
        if isinstance(error, AuthenticationError):
            category = "authentication"
        elif isinstance(error, AuthorizationError):
            category = "authorization"
        elif isinstance(error, BusinessRuleError):
            pytest.fail("specific access errors must be classified first")
        else:
            pytest.fail("unexpected hierarchy")
        assert category == (
            "authentication" if type(error) is AuthenticationError else "authorization"
        )
    assert not issubclass(AuthenticationError, AuthorizationError)
    assert not issubclass(AuthorizationError, AuthenticationError)


@pytest.mark.parametrize("allowed", [False, True])
@pytest.mark.parametrize(
    "kind", ["permission", "any_permission", "project", "any_project"]
)
def test_permission_helpers_preserve_decisions_messages_and_audit(
    monkeypatch, allowed, kind
):
    engine = Mock()
    engine.has_permission.return_value = allowed
    engine.has_any_permission.return_value = allowed
    engine.has_scope_permission.return_value = allowed
    monkeypatch.setattr(permission_checks, "get_authorization_engine", lambda: engine)
    monkeypatch.setattr(authorization, "get_authorization_engine", lambda: engine)
    audit = Mock()
    for module in (permission_checks, authorization, scope_permissions):
        monkeypatch.setattr(module, "record_authorization_denial", audit)
    session = SimpleNamespace(has_project_permission=lambda project, code: allowed)
    if kind == "permission":
        operation = lambda: permission_checks.require_permission(
            session, "read", operation_label="inspect"
        )
        message = "Permission denied for inspect. Missing 'read'."
    elif kind == "any_permission":
        operation = lambda: permission_checks.require_any_permission(
            session, ("read", "write"), operation_label="inspect"
        )
        message = "Permission denied for inspect. Missing one of 'read' or 'write'."
    elif kind == "project":
        operation = lambda: scope_permissions.require_project_permission(
            session, "p", "read", operation_label="inspect"
        )
        message = "Permission denied for inspect. Missing scoped 'read' access for project 'p'."
    else:
        operation = lambda: scope_permissions.require_any_project_permission(
            session, "p", ("read", "write"), operation_label="inspect"
        )
        message = "Permission denied for inspect. Missing one of 'read' or 'write'."
    if allowed:
        assert operation() is None
        audit.assert_not_called()
    else:
        with pytest.raises(AuthorizationError) as caught:
            operation()
        assert caught.value.code == "PERMISSION_DENIED"
        assert str(caught.value) == message
        assert caught.value.__cause__ is None
        audit.assert_called_once()
        assert audit.call_args.kwargs["reason_code"] == "PERMISSION_DENIED"


def test_post_gate_denial_preserves_code_message_audit_and_context(monkeypatch):
    audit = Mock()
    monkeypatch.setattr(permission_checks, "record_authorization_denial", audit)
    cause = ValueError("internal")
    with pytest.raises(AuthorizationError) as caught:
        try:
            raise cause
        except ValueError:
            permission_checks.authorization_denied(
                None,
                message="Scoped access denied.",
                code="PROJECT_ACCESS_DENIED",
                operation_label="inspect",
                target_scope_type="project",
                target_scope_id="p",
            )
    assert caught.value.code == "PROJECT_ACCESS_DENIED"
    assert str(caught.value) == "Scoped access denied."
    assert caught.value.__context__ is cause
    assert caught.value.__cause__ is None
    assert audit.call_args.kwargs["reason_code"] == "PROJECT_ACCESS_DENIED"


def test_canonical_errors_remain_transport_neutral():
    tree = ast.parse(Path(exceptions.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        else:
            continue
        assert all(
            not any(part in module.lower() for part in ("fastapi", "starlette", "http"))
            for module in modules
        )
    for name in exceptions.__all__:
        error_type = getattr(exceptions, name)
        error = error_type("safe")
        assert isinstance(error, DomainError)
        assert not hasattr(error, "status_code")
        assert not hasattr(error, "headers")
        assert not hasattr(error, "detail")
        assert "status_code" not in ast.unparse(tree)
