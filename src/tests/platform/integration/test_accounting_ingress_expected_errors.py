from unittest.mock import Mock

import pytest
from pydantic import SecretBytes

from src.core.platform.api.desktop.platform_runtime.runtime import (
    PlatformRuntimeDesktopApi,
)
from src.core.platform.api.desktop.support._support import execute_desktop_operation
from src.core.platform.application.integration.accounting.outcome_ingress import (
    MAX_ACCOUNTING_OUTCOME_BYTES,
    AccountingIngressAuthenticationError,
    AccountingIngressSizeError,
    AccountingOutcomeIngress,
)
from src.core.platform.common.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    ConfigurationError,
    DomainError,
    ValidationError,
)
from src.core.platform.contract.port.integration.accounting_outcomes import (
    AuthenticatedAccountingConnection,
    IngressRejectionReason,
)


def test_authentication_failure_is_canonical_safe_and_before_parsing():
    auth, consumer = Mock(), Mock()
    auth.authenticate.side_effect = RuntimeError("secret=private")
    ingress = AccountingOutcomeIngress(authenticator=auth, consumer=consumer)
    with pytest.raises(AccountingIngressAuthenticationError) as caught:
        ingress.receive(body=b"not-json", authentication=SecretBytes(b"s"))
    assert isinstance(caught.value, AuthenticationError)
    assert caught.value.code == "ACCOUNTING_INGRESS_AUTHENTICATION_FAILED"
    assert "private" not in str(caught.value)
    assert caught.value.__suppress_context__
    consumer.consume.assert_not_called()


def test_size_failure_is_canonical_and_before_authentication():
    auth, consumer = Mock(), Mock()
    ingress = AccountingOutcomeIngress(authenticator=auth, consumer=consumer)
    with pytest.raises(AccountingIngressSizeError) as caught:
        ingress.receive(
            body=b"x" * (MAX_ACCOUNTING_OUTCOME_BYTES + 1),
            authentication=SecretBytes(b"s"),
        )
    assert isinstance(caught.value, ValidationError)
    assert caught.value.code == "ACCOUNTING_INGRESS_SIZE_EXCEEDED"
    auth.authenticate.assert_not_called()
    consumer.consume.assert_not_called()


@pytest.mark.parametrize("body", [b"not-json", b'{"x":1,"x":2}', b"{}"])
def test_authenticated_malformed_payload_still_uses_finite_quarantine(body):
    auth, consumer = Mock(), Mock()
    auth.authenticate.return_value = AuthenticatedAccountingConnection(
        tenant_id="tenant",
        organization_id="org",
        adapter_id="adapter",
        connection_id="connection",
        principal_name="worker",
        authoritative_sequence=True,
    )
    consumer.consume.side_effect = lambda ingress: ingress
    ingress = AccountingOutcomeIngress(authenticator=auth, consumer=consumer)
    result = ingress.receive(body=body, authentication=SecretBytes(b"s"))
    assert result.rejection is IngressRejectionReason.MALFORMED
    assert result.outcome is None


@pytest.mark.parametrize(
    "error_type,category",
    [
        (AccountingIngressAuthenticationError, "conflict"),
        (AccountingIngressSizeError, "validation"),
    ],
)
def test_ingress_errors_use_existing_desktop_mapping(error_type, category):
    def fail():
        raise error_type()

    result = execute_desktop_operation(fail)
    assert not result.ok
    assert result.error.category == category
    assert result.error.code == error_type().code


@pytest.mark.parametrize(
    "error_type,category,default_code",
    [
        (AuthenticationError, "conflict", "AUTHENTICATION_REQUIRED"),
        (AuthorizationError, "conflict", "PERMISSION_DENIED"),
        (ConfigurationError, "domain", "CONFIGURATION_ERROR"),
    ],
)
@pytest.mark.parametrize("code", [None, "EXPLICIT_CODE"])
def test_canonical_authentication_and_configuration_serialization(
    error_type, category, default_code, code
):
    error = error_type("Safe operation message.", code=code)
    assert isinstance(error, DomainError)
    assert isinstance(error, BusinessRuleError) == (
        error_type in (AuthenticationError, AuthorizationError)
    )

    def fail():
        raise error

    result = execute_desktop_operation(fail)
    assert not result.ok
    assert result.data is None
    assert result.error.category == category
    assert result.error.code == (code or default_code)
    assert result.error.message == "Safe operation message."
    runtime_error = PlatformRuntimeDesktopApi._serialize_error(error)
    assert runtime_error.category == category
    assert runtime_error.code == (code or default_code)
    assert runtime_error.message == "Safe operation message."
