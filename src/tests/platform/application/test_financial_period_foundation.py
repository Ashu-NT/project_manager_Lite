from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.api.desktop.finance.models import (
    FinancialPeriodCreateCommand,
    FinancialPeriodTransitionCommand,
    FinancialPeriodUpdateCommand,
)
from src.core.platform.application.finance import FinancialPeriodQueryHandler
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.domain.finance import FinancialPeriod, FinancialPeriodStatus
from src.tests.ui_runtime_helpers import login_as, register_and_login


def _create_period(service, *, code: str = "FY26-P01", period_number: int = 1):
    return service.create_period(
        code=code,
        name=f"Fiscal 2026 period {period_number}",
        fiscal_year=2026,
        period_number=period_number,
        start_date=date(2026, period_number, 1),
        end_date=date(2026, period_number, 28),
    )


def test_financial_period_domain_enforces_range_metadata_and_one_way_lifecycle() -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    period = FinancialPeriod.create(
        tenant_id="tenant-a",
        organization_id="org-a",
        code="fy26-p01",
        name="January 2026",
        fiscal_year=2026,
        period_number=1,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        actor_id="user-a",
        now=now,
    )

    assert period.code == "FY26-P01"
    assert period.contains(date(2026, 1, 31))
    assert period.accepts_normal_posting

    period.close(actor_id="controller-a", now=now)
    assert period.status == FinancialPeriodStatus.CLOSED
    with pytest.raises(BusinessRuleError) as posting:
        period.require_normal_posting()
    assert posting.value.code == "FINANCIAL_PERIOD_POSTING_BLOCKED"

    period.lock(actor_id="controller-b", now=now)
    assert period.status == FinancialPeriodStatus.LOCKED
    with pytest.raises(BusinessRuleError) as edit:
        period.update_definition(actor_id="user-a", now=now, name="Changed")
    assert edit.value.code == "FINANCIAL_PERIOD_NOT_EDITABLE"

    with pytest.raises(ValidationError) as invalid_range:
        replace(
            period,
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
        )
    assert invalid_range.value.code == "FINANCIAL_PERIOD_DATE_RANGE_INVALID"


def test_financial_period_handlers_enforce_overlap_concurrency_audit_and_posting(services) -> None:
    commands = services["financial_period_commands"]
    queries = services["financial_period_queries"]
    period = _create_period(commands)

    assert queries.require_open_period_for_date(date(2026, 1, 10)).id == period.id
    with pytest.raises(BusinessRuleError) as overlap:
        commands.create_period(
            code="FY26-P01B",
            name="Overlapping period",
            fiscal_year=2026,
            period_number=2,
            start_date=date(2026, 1, 15),
            end_date=date(2026, 2, 15),
        )
    assert overlap.value.code == "FINANCIAL_PERIOD_OVERLAP"

    updated = commands.update_period(
        period.id,
        expected_version=period.version,
        name="January close cycle",
        end_date=date(2026, 1, 31),
    )
    assert updated.version == 2
    with pytest.raises(ConcurrencyError) as stale:
        commands.update_period(
            period.id,
            expected_version=1,
            name="Stale change",
        )
    assert stale.value.code == "STALE_WRITE"

    closed = commands.close_period(period.id, expected_version=updated.version)
    assert closed.status == FinancialPeriodStatus.CLOSED
    assert closed.version == 3
    with pytest.raises(BusinessRuleError) as blocked:
        queries.require_open_period_for_date(date(2026, 1, 10))
    assert blocked.value.code == "FINANCIAL_PERIOD_POSTING_BLOCKED"

    locked = commands.lock_period(period.id, expected_version=closed.version)
    assert locked.status == FinancialPeriodStatus.LOCKED
    assert locked.version == 4
    assert not hasattr(commands, "reopen_period")

    entries = services["enterprise_audit_service"].list_recent(
        entity_type="financial_period"
    )
    operations = {entry.operation for entry in entries if entry.entity_id == period.id}
    assert operations == {
        "financial_period.create",
        "financial_period.update",
        "financial_period.close",
        "financial_period.lock",
    }


def test_financial_period_repository_isolates_active_organization(services) -> None:
    commands = services["financial_period_commands"]
    queries = services["financial_period_queries"]
    original = services["tenant_context_service"].get_active_organization()
    first = _create_period(commands)
    second_organization = services["organization_commands"].create_organization(
        organization_code="FIN2",
        display_name="Second finance organization",
        timezone_name="UTC",
        base_currency="EUR",
    )

    services["tenant_context_service"].set_active_organization(second_organization.id)
    try:
        assert queries.list_periods() == []
        with pytest.raises(NotFoundError):
            queries.get_period(first.id)
        with pytest.raises(NotFoundError):
            commands.close_period(first.id, expected_version=first.version)
        with pytest.raises(BusinessRuleError) as missing:
            queries.require_open_period_for_integration(date(2026, 1, 10))
        assert missing.value.code == "FINANCIAL_PERIOD_NOT_CONFIGURED"
        second = _create_period(commands)
        assert second.code == first.code
        assert second.organization_id == second_organization.id
        assert queries.require_open_period_for_integration(date(2026, 1, 10)).id == second.id
    finally:
        services["tenant_context_service"].set_active_organization(original.id)

    assert [period.id for period in queries.list_periods()] == [first.id]


def test_financial_period_mutation_requires_finance_manage(services) -> None:
    commands = services["financial_period_commands"]
    register_and_login(
        services,
        username_prefix="period-project-manager",
        role_names=("project_manager",),
    )
    try:
        with pytest.raises(BusinessRuleError) as denied:
            _create_period(commands)
        assert denied.value.code == "PERMISSION_DENIED"
    finally:
        login_as(services, "admin", "ChangeMe123!")


def test_financial_period_desktop_api_exposes_typed_lifecycle_and_errors(services) -> None:
    api = build_desktop_api_registry(services).platform_financial_periods
    created = api.create_period(
        FinancialPeriodCreateCommand(
            code="FY26-P01",
            name="January 2026",
            fiscal_year=2026,
            period_number=1,
            start_date="2026-01-01",
            end_date="2026-01-31",
        )
    )

    assert created.ok
    assert created.data is not None
    assert created.data.accepts_normal_posting
    updated = api.update_period(
        FinancialPeriodUpdateCommand(
            period_id=created.data.id,
            expected_version=created.data.version,
            name="January close cycle",
        )
    )
    assert updated.ok and updated.data is not None
    closed = api.close_period(
        FinancialPeriodTransitionCommand(
            period_id=updated.data.id,
            expected_version=updated.data.version,
        )
    )
    assert closed.ok and closed.data is not None
    assert closed.data.status == "closed"
    assert not closed.data.accepts_normal_posting

    invalid = api.create_period(
        FinancialPeriodCreateCommand(
            code="FY26-P02",
            name="Invalid date",
            fiscal_year=2026,
            period_number=2,
            start_date="not-a-date",
            end_date="2026-02-28",
        )
    )
    assert not invalid.ok
    assert invalid.error is not None
    assert invalid.error.code == "FINANCIAL_PERIOD_DATE_INVALID"

    invalid_status = api.list_periods(status="archived")
    assert not invalid_status.ok
    assert invalid_status.error is not None
    assert invalid_status.error.code == "FINANCIAL_PERIOD_STATUS_INVALID"


def test_financial_period_handler_authorities_are_disjoint(services) -> None:
    commands = services["financial_period_commands"]
    queries = services["financial_period_queries"]
    assert commands._period_repo is queries._period_repo
    assert commands._session is services["session"]
    for name in ("create_period", "update_period", "close_period", "lock_period"):
        assert hasattr(commands, name)
        assert not hasattr(queries, name)
    for name in (
        "list_periods", "get_period", "require_open_period_for_date",
        "require_open_period_for_integration",
    ):
        assert hasattr(queries, name)
        assert not hasattr(commands, name)
    assert not hasattr(queries, "_session")
    assert not hasattr(queries, "_enterprise_audit_service")


def test_trusted_period_query_bypasses_read_permission_not_posting_policy(services) -> None:
    commands = services["financial_period_commands"]
    period = _create_period(commands)
    queries = FinancialPeriodQueryHandler(period_repo=commands._period_repo)
    with pytest.raises(BusinessRuleError) as denied:
        queries.require_open_period_for_date(date(2026, 1, 10))
    assert denied.value.code == "PERMISSION_DENIED"
    assert queries.require_open_period_for_integration(date(2026, 1, 10)).id == period.id
    with pytest.raises(ValidationError) as invalid:
        queries.require_open_period_for_integration(datetime(2026, 1, 10, tzinfo=UTC))
    assert invalid.value.code == "FINANCIAL_PERIOD_DATE_INVALID"
    with pytest.raises(BusinessRuleError) as missing:
        queries.require_open_period_for_integration(date(2026, 2, 10))
    assert missing.value.code == "FINANCIAL_PERIOD_NOT_CONFIGURED"
    closed = commands.close_period(period.id, expected_version=period.version)
    with pytest.raises(BusinessRuleError) as blocked:
        queries.require_open_period_for_integration(date(2026, 1, 10))
    assert blocked.value.code == "FINANCIAL_PERIOD_POSTING_BLOCKED"
    commands.lock_period(period.id, expected_version=closed.version)
    with pytest.raises(BusinessRuleError) as locked:
        queries.require_open_period_for_integration(date(2026, 1, 10))
    assert locked.value.code == "FINANCIAL_PERIOD_POSTING_BLOCKED"


def test_financial_period_queries_do_not_complete_caller_transaction(services, monkeypatch) -> None:
    period = _create_period(services["financial_period_commands"])
    queries = services["financial_period_queries"]

    def forbidden(*args, **kwargs):
        raise AssertionError("Queries must not complete the caller's transaction")

    monkeypatch.setattr(services["session"], "commit", forbidden)
    monkeypatch.setattr(services["session"], "rollback", forbidden)
    assert queries.get_period(period.id).id == period.id
    assert queries.list_periods(fiscal_year=2026, status="open")[0].id == period.id
    assert queries.require_open_period_for_date(date(2026, 1, 10)).id == period.id
    assert queries.require_open_period_for_integration(date(2026, 1, 10)).id == period.id
