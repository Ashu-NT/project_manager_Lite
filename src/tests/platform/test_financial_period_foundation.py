from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.api.desktop.finance.models import (
    FinancialPeriodCreateCommand,
    FinancialPeriodTransitionCommand,
    FinancialPeriodUpdateCommand,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.finance import FinancialPeriod, FinancialPeriodStatus
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
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
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


def test_financial_period_service_enforces_overlap_concurrency_audit_and_posting(services) -> None:
    service = services["financial_period_service"]
    period = _create_period(service)

    assert service.require_open_period_for_date(date(2026, 1, 10)).id == period.id
    with pytest.raises(BusinessRuleError) as overlap:
        service.create_period(
            code="FY26-P01B",
            name="Overlapping period",
            fiscal_year=2026,
            period_number=2,
            start_date=date(2026, 1, 15),
            end_date=date(2026, 2, 15),
        )
    assert overlap.value.code == "FINANCIAL_PERIOD_OVERLAP"

    updated = service.update_period(
        period.id,
        expected_version=period.version,
        name="January close cycle",
        end_date=date(2026, 1, 31),
    )
    assert updated.version == 2
    with pytest.raises(ConcurrencyError) as stale:
        service.update_period(
            period.id,
            expected_version=1,
            name="Stale change",
        )
    assert stale.value.code == "STALE_WRITE"

    closed = service.close_period(period.id, expected_version=updated.version)
    assert closed.status == FinancialPeriodStatus.CLOSED
    assert closed.version == 3
    with pytest.raises(BusinessRuleError) as blocked:
        service.require_open_period_for_date(date(2026, 1, 10))
    assert blocked.value.code == "FINANCIAL_PERIOD_POSTING_BLOCKED"

    locked = service.lock_period(period.id, expected_version=closed.version)
    assert locked.status == FinancialPeriodStatus.LOCKED
    assert locked.version == 4
    assert not hasattr(service, "reopen_period")

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
    service = services["financial_period_service"]
    organization_service = services["organization_service"]
    original = services["tenant_context_service"].get_active_organization()
    first = _create_period(service)
    second_organization = organization_service.create_organization(
        organization_code="FIN2",
        display_name="Second finance organization",
        timezone_name="UTC",
        base_currency="EUR",
        is_enabled=True,
    )

    organization_service.enable_organization(second_organization.id)
    services["tenant_context_service"].set_active_organization(second_organization.id)
    try:
        assert service.list_periods() == []
        with pytest.raises(NotFoundError):
            service.get_period(first.id)
        second = _create_period(service)
        assert second.code == first.code
        assert second.organization_id == second_organization.id
    finally:
        organization_service.enable_organization(original.id)
        services["tenant_context_service"].set_active_organization(original.id)

    assert [period.id for period in service.list_periods()] == [first.id]


def test_financial_period_mutation_requires_finance_manage(services) -> None:
    service = services["financial_period_service"]
    register_and_login(
        services,
        username_prefix="period-project-manager",
        role_names=("project_manager",),
    )
    try:
        with pytest.raises(BusinessRuleError) as denied:
            _create_period(service)
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
