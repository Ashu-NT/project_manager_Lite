from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.application.dashboard.analytics.evm import (
    DashboardEvmWidget,
)
from src.core.modules.project_management.application.dashboard.widgets.professional import (
    DashboardScheduleHealthWidget,
)
from src.core.modules.project_management.application.financials.earned_value.dto.responses.earned_value import (
    EarnedValueMetrics,
)


@pytest.mark.parametrize(
    "resource_id,resource_name,expected",
    [(None, None, None), (None, "Named owner", "Named owner"),
     ("resource-1", None, "Resource One"), ("unknown", None, "unknown")],
)
def test_owner_lookup_preserves_missing_names_and_id_fallback(
    resource_id, resource_name, expected
):
    result = DashboardScheduleHealthWidget.build_task_owner_map(
        [SimpleNamespace(id="task-1")],
        assignments_by_task={
            "task-1": [SimpleNamespace(
                resource_id=resource_id, resource_name=resource_name, allocation_percent=0
            )]
        },
        resource_names={"resource-1": "Resource One"},
    )

    assert result == {"task-1": expected}


@pytest.mark.parametrize(
    "baseline_id,availability,available",
    [(None, "baseline_unavailable", False), (None, "available", False),
     ("baseline-1", "baseline_unavailable", False),
     ("baseline-1", "available", True)],
)
def test_evm_requires_baseline_identity_without_discarding_zero_metrics(
    baseline_id, availability, available
):
    metrics = EarnedValueMetrics(
        as_of=date(2026, 10, 15), baseline_id=baseline_id, currency_code="USD",
        availability=availability, unavailable_reason=None,
        BAC=Decimal(0), PV=Decimal(0), EV=Decimal(0), AC=Decimal(0),
        CV=Decimal(0), SV=Decimal(0), CPI=None, SPI=None, EAC=None, ETC=None,
        VAC=None,
    )
    calls = []

    def get_earned_value(project_id, *, baseline_id):
        calls.append((project_id, baseline_id))
        return metrics

    result = DashboardEvmWidget(SimpleNamespace(get_earned_value=get_earned_value)).build(
        "project-1", baseline_id="selected-baseline"
    )

    assert calls == [("project-1", "selected-baseline")]
    if available:
        assert result is not None
        assert result.baseline_id == "baseline-1"
        assert result.BAC == result.PV == result.EV == result.AC == Decimal(0)
        assert result.CPI is result.SPI is None
    else:
        assert result is None
