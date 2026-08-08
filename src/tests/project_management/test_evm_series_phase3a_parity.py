from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.infrastructure.persistence.reads.financials import (
    SqlAlchemyEvmSeriesReader,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.tests.project_management.test_evm_series_phase3a_measurement import (
    _seed_series_project,
)


def _assert_matches_single_date_path(
    reporting,
    *,
    project_id: str,
    baseline_id: str | None,
    as_of: date,
) -> list:
    series = reporting.get_evm_series(
        project_id,
        baseline_id=baseline_id,
        as_of=as_of,
    )
    for point in series:
        expected = reporting.get_earned_value(
            project_id,
            baseline_id=baseline_id,
            as_of=point.period_end,
        )
        assert point.PV == pytest.approx(expected.PV)
        assert point.EV == pytest.approx(expected.EV)
        assert point.AC == pytest.approx(expected.AC)
        assert point.BAC == pytest.approx(expected.BAC)
        assert point.CPI == pytest.approx(expected.CPI or 0.0)
        assert point.SPI == pytest.approx(expected.SPI or 0.0)
    return series


def test_series_matches_explicit_and_latest_baseline_with_rate_change(services) -> None:
    project_id, baseline_id, as_of = _seed_series_project(services, periods=12)
    services["cost_service"].add_cost_item(
        project_id=project_id,
        description="Manual labor adjustment excluded by computed labor",
        planned_amount=900.0,
        committed_amount=600.0,
        actual_amount=300.0,
        cost_type=CostType.LABOR,
        incurred_date=date(2023, 4, 15),
        currency_code="EUR",
    )
    rate_cards = services["rate_card_service"]
    card = rate_cards.create_rate_card(name="Phase 3A dated rates", project_id=project_id)
    project_resources = services["project_resource_service"].list_by_project(project_id)
    for index, project_resource in enumerate(project_resources):
        rate_cards.create_line(
            card.id,
            rate_type=RateType.COST,
            unit="HOUR",
            rate_amount=Decimal(70 + index),
            rate_currency="EUR",
            resource_id=project_resource.resource_id,
            effective_from=date(2023, 1, 1),
            effective_to=date(2023, 6, 30),
        )
        rate_cards.create_line(
            card.id,
            rate_type=RateType.COST,
            unit="HOUR",
            rate_amount=Decimal(90 + index),
            rate_currency="EUR",
            resource_id=project_resource.resource_id,
            effective_from=date(2023, 7, 1),
        )

    explicit = _assert_matches_single_date_path(
        services["reporting_service"],
        project_id=project_id,
        baseline_id=baseline_id,
        as_of=as_of,
    )
    latest = _assert_matches_single_date_path(
        services["reporting_service"],
        project_id=project_id,
        baseline_id=None,
        as_of=as_of,
    )
    assert explicit == latest
    assert explicit[5].AC < explicit[6].AC


def test_series_matches_budget_fallback_when_baseline_cost_is_zero(services) -> None:
    start = date(2024, 1, 2)
    project = services["project_service"].create_project(
        "Phase 3A fallback",
        start_date=start,
        end_date=date(2024, 4, 30),
        planned_budget=12000.0,
        currency="EUR",
    )
    services["task_service"].create_task(
        project.id,
        "Uncosted work",
        start_date=start,
        duration_days=40,
    )
    baseline = services["baseline_service"].create_baseline(
        project.id,
        "Fallback baseline",
        rate_as_of=start,
    )
    series = _assert_matches_single_date_path(
        services["reporting_service"],
        project_id=project.id,
        baseline_id=baseline.id,
        as_of=date(2024, 3, 31),
    )
    assert series
    assert all(point.BAC == pytest.approx(12000.0) for point in series)


def test_series_preserves_no_baseline_error(services) -> None:
    project = services["project_service"].create_project(
        "Phase 3A no baseline",
        start_date=date(2024, 1, 2),
        end_date=date(2024, 3, 31),
        currency="EUR",
    )
    with pytest.raises(BusinessRuleError) as exc:
        services["reporting_service"].get_evm_series(
            project.id,
            as_of=date(2024, 2, 29),
        )
    assert exc.value.code == "NO_BASELINE"


def test_series_reader_is_runtime_composed_and_fails_closed_for_wrong_scope(
    services,
    monkeypatch,
) -> None:
    project_id, baseline_id, as_of = _seed_series_project(services, periods=3)
    reporting = services["reporting_service"]
    reader = reporting._evm_series_reader
    assert isinstance(reader, SqlAlchemyEvmSeriesReader)
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test EVM series reader isolation"
    )
    assert reader.read_facts(
        tenant_id="wrong-tenant",
        organization_id=scope.organization_id,
        project_id=project_id,
        baseline_id=baseline_id,
        as_of=as_of,
    ) is None
    assert reader.read_facts(
        tenant_id=scope.tenant_id,
        organization_id="wrong-organization",
        project_id=project_id,
        baseline_id=baseline_id,
        as_of=as_of,
    ) is None

    calls = 0
    original = reader.read_facts

    def counted_read_facts(**kwargs):
        nonlocal calls
        calls += 1
        return original(**kwargs)

    monkeypatch.setattr(reader, "read_facts", counted_read_facts)
    assert reporting.get_evm_series(
        project_id,
        baseline_id=baseline_id,
        as_of=as_of,
    )
    assert calls == 1
