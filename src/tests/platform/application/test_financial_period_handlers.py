from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.platform.application.finance import (
    FinancialPeriodCommandHandler,
    FinancialPeriodQueryHandler,
)
from src.core.platform.application.finance.commands import financial_period_command
from src.core.platform.application.finance.dto.commands.financial_periods import (
    FinancialPeriodCreateCommand,
    FinancialPeriodTransitionCommand,
    FinancialPeriodUpdateCommand,
)
from src.core.platform.application.finance.queries import financial_period_query
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    ValidationError,
)
from src.core.platform.contract.repositories.finance import FinancialPeriodRepository
from src.core.platform.domain.finance.periods import FinancialPeriod


def _period() -> FinancialPeriod:
    return FinancialPeriod.create(
        tenant_id="tenant-a", organization_id="org-a",
        code="FY26-P01", name="January", fiscal_year=2026, period_number=1,
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
        actor_id="actor-a", now=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.mark.parametrize("method", [
    "list_periods", "get_period", "require_open_period_for_date",
])
def test_interactive_queries_require_finance_read(monkeypatch, method) -> None:
    repo = Mock(spec=FinancialPeriodRepository)
    permission = Mock(side_effect=BusinessRuleError("Denied", code="PERMISSION_DENIED"))
    monkeypatch.setattr(financial_period_query, "require_permission", permission)
    queries = FinancialPeriodQueryHandler(period_repo=repo, user_session="user")
    args = {"list_periods": (), "get_period": ("id",),
            "require_open_period_for_date": (date(2026, 1, 10),)}
    with pytest.raises(BusinessRuleError, match="Denied"):
        getattr(queries, method)(*args[method])
    assert permission.call_args.args == ("user", "finance.read")
    assert not repo.mock_calls


@pytest.mark.parametrize("status", ["open", "closed", "locked"])
def test_trusted_queries_preserve_posting_policy_without_interactive_permission(
    monkeypatch, status,
) -> None:
    period = _period()
    now = datetime(2026, 1, 2, tzinfo=UTC)
    if status != "open":
        period.close(actor_id="actor-a", now=now)
    if status == "locked":
        period.lock(actor_id="actor-a", now=now)
    repo = Mock(spec=FinancialPeriodRepository)
    repo.find_for_date.return_value = period
    permission = Mock(side_effect=AssertionError("Integration must not check UI permission"))
    monkeypatch.setattr(financial_period_query, "require_permission", permission)
    queries = FinancialPeriodQueryHandler(period_repo=repo)
    if status == "open":
        assert queries.require_open_period_for_integration(date(2026, 1, 10)) is period
    else:
        with pytest.raises(BusinessRuleError) as blocked:
            queries.require_open_period_for_integration(date(2026, 1, 10))
        assert blocked.value.code == "FINANCIAL_PERIOD_POSTING_BLOCKED"
    permission.assert_not_called()
    repo.find_for_date.assert_called_once_with(date(2026, 1, 10))
    assert not hasattr(queries, "_session")
    assert not hasattr(queries, "create_period")


@pytest.mark.parametrize("invalid", [None, "2026-01-10", datetime(2026, 1, 10, tzinfo=UTC)])
def test_trusted_queries_validate_dates_before_repository_access(invalid) -> None:
    repo = Mock(spec=FinancialPeriodRepository)
    queries = FinancialPeriodQueryHandler(period_repo=repo)
    with pytest.raises(ValidationError) as error:
        queries.require_open_period_for_integration(invalid)
    assert error.value.code == "FINANCIAL_PERIOD_DATE_INVALID"
    repo.find_for_date.assert_not_called()


def _commands(monkeypatch):
    repo = Mock(spec=FinancialPeriodRepository)
    repo.overlaps.return_value = False
    session = Mock(spec=Session)
    session.begin_nested.return_value = nullcontext()
    def update_version(period, *, expected_version):
        period.version = expected_version + 1

    repo.update.side_effect = update_version
    scope = Mock()
    scope.require_active_scope_ids.return_value = SimpleNamespace(
        tenant_id="tenant-a", organization_id="org-a",
    )
    permission = Mock()
    audit, activity = Mock(), Mock()
    monkeypatch.setattr(financial_period_command, "require_permission", permission)
    monkeypatch.setattr(financial_period_command, "record_audit_entry", audit)
    monkeypatch.setattr(financial_period_command, "record_activity", activity)
    commands = FinancialPeriodCommandHandler(
        session=session, period_repo=repo, tenant_context_service=scope,
        user_session=SimpleNamespace(principal=SimpleNamespace(user_id="actor-a")),
        enterprise_audit_service=Mock(),
        now_provider=lambda: datetime(2026, 1, 2, tzinfo=UTC).replace(tzinfo=None),
    )
    return commands, repo, session, permission, audit, activity


@pytest.mark.parametrize("operation", ["close", "lock", "update"])
def test_commands_preserve_versions_scope_audit_activity_and_commit(monkeypatch, operation) -> None:
    commands, repo, session, permission, audit, activity = _commands(monkeypatch)
    period = _period()
    if operation == "lock":
        period.close(actor_id="actor-a", now=datetime(2026, 1, 1, tzinfo=UTC))
    version = period.version
    repo.get.return_value = period
    result = getattr(commands, f"{operation}_period")(
        FinancialPeriodUpdateCommand(period.id, version) if operation == "update"
        else FinancialPeriodTransitionCommand(period.id, version)
    )
    assert result.version == version + 1
    repo.lock_catalog.assert_called_once()
    repo.update.assert_called_once_with(period, expected_version=version)
    session.commit.assert_called_once()
    assert permission.call_args.args[1] == "finance.manage"
    assert audit.call_args.kwargs["operation"] == f"financial_period.{operation}"
    assert audit.call_args.kwargs["organization_id"] == "org-a"
    assert audit.call_args.kwargs["before_data"]["version"] == version
    assert audit.call_args.kwargs["after_data"]["version"] == version + 1
    assert audit.call_args.kwargs["commit"] is False
    assert audit.call_args.kwargs["fail_closed"] is True
    assert activity.call_args.kwargs["commit"] is False
    assert commands._now().tzinfo is UTC


def test_stale_commands_do_not_write_audit_or_commit(monkeypatch) -> None:
    commands, repo, session, _, audit, activity = _commands(monkeypatch)
    repo.get.return_value = _period()
    with pytest.raises(ConcurrencyError) as error:
        commands.close_period(FinancialPeriodTransitionCommand(period_id=repo.get.return_value.id, expected_version=0))
    assert error.value.code == "STALE_WRITE"
    repo.update.assert_not_called()
    audit.assert_not_called()
    activity.assert_not_called()
    session.commit.assert_not_called()


def test_command_audit_failure_prevents_commit(monkeypatch) -> None:
    commands, repo, session, _, audit, activity = _commands(monkeypatch)
    repo.get.return_value = _period()
    audit.side_effect = RuntimeError("Audit unavailable")
    with pytest.raises(RuntimeError, match="Audit unavailable"):
        commands.close_period(FinancialPeriodTransitionCommand(period_id=repo.get.return_value.id, expected_version=1))
    session.commit.assert_not_called()
    activity.assert_not_called()


def test_create_duplicate_preserves_savepoint_error_translation(monkeypatch) -> None:
    commands, repo, session, _, audit, activity = _commands(monkeypatch)
    session.begin_nested.return_value = nullcontext()
    repo.add.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    with pytest.raises(BusinessRuleError) as error:
        commands.create_period(FinancialPeriodCreateCommand(code="FY26-P01", name="January", fiscal_year=2026, period_number=1, start_date=date(2026, 1, 1).isoformat(), end_date=date(2026, 1, 31).isoformat()))
    assert error.value.code == "FINANCIAL_PERIOD_DUPLICATE"
    session.begin_nested.assert_called_once()
    repo.lock_catalog.assert_called_once()
    session.commit.assert_not_called()
    audit.assert_not_called()
    activity.assert_not_called()


def test_create_keeps_catalog_savepoint_and_audit_before_commit(monkeypatch) -> None:
    commands, repo, session, permission, audit, activity = _commands(monkeypatch)
    order = Mock()
    order.attach_mock(audit, "audit")
    order.attach_mock(activity, "activity")
    order.attach_mock(session.commit, "commit")
    period = commands.create_period(FinancialPeriodCreateCommand(code="FY26-P01", name="January", fiscal_year=2026, period_number=1, start_date=date(2026, 1, 1).isoformat(), end_date=date(2026, 1, 31).isoformat()))
    assert (period.tenant_id, period.organization_id) == ("tenant-a", "org-a")
    assert period.created_by == "actor-a"
    assert permission.call_args.args[1] == "finance.manage"
    session.begin_nested.assert_called_once()
    repo.lock_catalog.assert_called_once()
    repo.add.assert_called_once_with(period)
    session.flush.assert_called_once()
    assert [call[0] for call in order.mock_calls] == ["audit", "activity", "commit"]
    assert audit.call_args.kwargs["before_data"] is None
    assert audit.call_args.kwargs["after_data"]["version"] == period.version


def test_missing_trusted_period_is_not_configured() -> None:
    repo = Mock(spec=FinancialPeriodRepository)
    repo.find_for_date.return_value = None
    with pytest.raises(BusinessRuleError) as error:
        FinancialPeriodQueryHandler(period_repo=repo).require_open_period_for_integration(
            date(2026, 1, 10)
        )
    assert error.value.code == "FINANCIAL_PERIOD_NOT_CONFIGURED"


def test_query_catalog_validates_status_and_reports_missing_period(monkeypatch) -> None:
    from src.core.platform.common.exceptions import NotFoundError

    monkeypatch.setattr(financial_period_query, "require_permission", Mock())
    repo = Mock(spec=FinancialPeriodRepository)
    queries = FinancialPeriodQueryHandler(period_repo=repo)
    with pytest.raises(ValidationError) as invalid:
        queries.list_periods(status="invalid")
    assert invalid.value.code == "FINANCIAL_PERIOD_STATUS_INVALID"
    repo.list.assert_not_called()
    repo.get.return_value = None
    with pytest.raises(NotFoundError) as missing:
        queries.get_period("missing")
    assert missing.value.code == "FINANCIAL_PERIOD_NOT_FOUND"


@pytest.mark.parametrize("operation", ["create", "update", "close", "lock"])
def test_commands_require_finance_manage_before_repository_access(monkeypatch, operation) -> None:
    commands, repo, session, permission, audit, activity = _commands(monkeypatch)
    permission.side_effect = BusinessRuleError("Denied", code="PERMISSION_DENIED")
    command = (
        FinancialPeriodCreateCommand(
            code="FY26-P01", name="January", fiscal_year=2026, period_number=1,
            start_date="2026-01-01", end_date="2026-01-31",
        ) if operation == "create"
        else FinancialPeriodUpdateCommand("id", 1) if operation == "update"
        else FinancialPeriodTransitionCommand("id", 1)
    )
    with pytest.raises(BusinessRuleError, match="Denied"):
        getattr(commands, f"{operation}_period")(command)
    assert permission.call_args.args[1] == "finance.manage"
    assert not repo.mock_calls
    assert not session.mock_calls
    audit.assert_not_called()
    activity.assert_not_called()
