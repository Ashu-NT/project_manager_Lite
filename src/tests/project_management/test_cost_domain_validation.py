from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.domain.financials.cost import CommitmentStatus, CostItem
from src.core.platform.common.exceptions import ValidationError


def test_cost_item_dto_normalizes_and_validates_fields():
    item = CostItem.create(
        project_id="  proj-1  ",
        task_id="  task-1  ",
        code="  cst-manual-1  ",
        description="  Electrical package  ",
        planned_amount="1500.5",
        cost_type="material",
        committed_amount="900",
        actual_amount="450",
        forecast_amount="1800",
        commitment_status="committed",
        vendor_reference="  PO-123  ",
        incurred_date=date(2026, 5, 4),
        currency_code=" eur ",
    )

    assert item.project_id == "proj-1"
    assert item.task_id == "task-1"
    assert item.code == "cst-manual-1"
    assert item.description == "Electrical package"
    assert item.planned_amount == pytest.approx(1500.5)
    assert item.cost_type == CostType.MATERIAL
    assert item.committed_amount == pytest.approx(900.0)
    assert item.actual_amount == pytest.approx(450.0)
    assert item.forecast_amount == pytest.approx(1800.0)
    assert item.commitment_status == CommitmentStatus.COMMITTED
    assert item.vendor_reference == "PO-123"
    assert item.incurred_date == date(2026, 5, 4)
    assert item.currency_code == "EUR"


def test_cost_item_dto_rejects_invalid_local_fields():
    with pytest.raises(ValidationError) as exc_project:
        CostItem.create(project_id=" ", description="Valid", planned_amount=10.0)
    assert exc_project.value.code == "COST_PROJECT_REQUIRED"

    with pytest.raises(ValidationError) as exc_description:
        CostItem.create(project_id="proj-1", description=" ", planned_amount=10.0)
    assert exc_description.value.code == "COST_DESCRIPTION_EMPTY"

    with pytest.raises(ValidationError) as exc_planned:
        CostItem.create(project_id="proj-1", description="Invalid", planned_amount=-1.0)
    assert exc_planned.value.code == "COST_PLANNED_AMOUNT_INVALID"

    with pytest.raises(ValidationError) as exc_committed:
        CostItem.create(
            project_id="proj-1",
            description="Invalid",
            planned_amount=10.0,
            committed_amount=-1.0,
        )
    assert exc_committed.value.code == "COST_COMMITTED_AMOUNT_INVALID"

    with pytest.raises(ValidationError) as exc_actual:
        CostItem.create(
            project_id="proj-1",
            description="Invalid",
            planned_amount=10.0,
            actual_amount=-1.0,
        )
    assert exc_actual.value.code == "COST_ACTUAL_AMOUNT_INVALID"

    with pytest.raises(ValidationError) as exc_forecast:
        CostItem.create(
            project_id="proj-1",
            description="Invalid",
            planned_amount=10.0,
            forecast_amount=-1.0,
        )
    assert exc_forecast.value.code == "COST_FORECAST_AMOUNT_INVALID"

    with pytest.raises(ValidationError) as exc_type:
        CostItem.create(
            project_id="proj-1",
            description="Invalid",
            planned_amount=10.0,
            cost_type="bad-cost-type",
        )
    assert exc_type.value.code == "COST_TYPE_INVALID"

    with pytest.raises(ValidationError) as exc_status:
        CostItem.create(
            project_id="proj-1",
            description="Invalid",
            planned_amount=10.0,
            commitment_status="bad-status",
        )
    assert exc_status.value.code == "COST_COMMITMENT_STATUS_INVALID"

    with pytest.raises(ValidationError) as exc_date:
        CostItem.create(
            project_id="proj-1",
            description="Invalid",
            planned_amount=10.0,
            incurred_date="2026-02-24",
        )
    assert exc_date.value.code == "COST_INCURRED_DATE_INVALID"

    with pytest.raises(ValidationError) as exc_currency:
        CostItem.create(
            project_id="proj-1",
            description="Invalid",
            planned_amount=10.0,
            currency_code="ZZZ",
        )
    assert exc_currency.value.code == "COST_CURRENCY_INVALID"

def test_cost_item_forecast_and_commitment_helpers_use_validated_fields():
    item = CostItem.create(
        project_id="proj-1",
        task_id="task-1",
        code="CST-0001",
        description="Manual forecast",
        planned_amount=1200.0,
        cost_type=CostType.SUBCONTRACT,
        committed_amount=700.0,
        actual_amount=250.0,
        forecast_amount=1300.0,
        commitment_status=CommitmentStatus.COMMITTED,
        vendor_reference="INV-42",
        incurred_date=date(2026, 6, 2),
        currency_code="USD",
    )

    assert item.remaining_committed == pytest.approx(450.0)
    assert item.effective_forecast == pytest.approx(1300.0)
    assert item.commitment_status == CommitmentStatus.COMMITTED
    assert item.vendor_reference == "INV-42"
    assert item.cost_type == CostType.SUBCONTRACT
    assert item.currency_code == "USD"
