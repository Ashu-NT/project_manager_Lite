from __future__ import annotations

import pytest

from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.platform.common.exceptions import ValidationError


def test_resource_dto_normalizes_and_validates_fields():
    resource = Resource.create(
        name="  Electrical Crew  ",
        code="  res-manual-1  ",
        role="  Lead Technician  ",
        hourly_rate="95.5",
        cost_type="equipment",
        currency_code=" eur ",
        capacity_percent="110",
        address="  Site Office  ",
        contact="  crew@example.com  ",
        worker_type="external",
        employee_id="  emp-1  ",
        organization_id="  org-1  ",
    )

    assert resource.name == "Electrical Crew"
    assert resource.code == "res-manual-1"
    assert resource.role == "Lead Technician"
    assert resource.hourly_rate == pytest.approx(95.5)
    assert resource.cost_type == CostType.EQUIPMENT
    assert resource.currency_code == "EUR"
    assert resource.capacity_percent == pytest.approx(110.0)
    assert resource.address == "Site Office"
    assert resource.contact == "crew@example.com"
    assert resource.worker_type == WorkerType.EXTERNAL
    assert resource.employee_id == "emp-1"
    assert resource.organization_id == "org-1"


def test_resource_dto_rejects_invalid_local_fields():
    with pytest.raises(ValidationError) as exc_name:
        Resource.create(name="  ")
    assert exc_name.value.code == "RESOURCE_NAME_EMPTY"

    with pytest.raises(ValidationError) as exc_rate:
        Resource.create(name="Rate Check", hourly_rate=-1)
    assert exc_rate.value.code == "RESOURCE_HOURLY_RATE_INVALID"

    with pytest.raises(ValidationError) as exc_capacity:
        Resource.create(name="Capacity Check", capacity_percent=0)
    assert exc_capacity.value.code == "RESOURCE_CAPACITY_INVALID"

    with pytest.raises(ValidationError) as exc_cost_type:
        Resource.create(name="Cost Type Check", cost_type="bad-cost-type")
    assert exc_cost_type.value.code == "RESOURCE_COST_TYPE_INVALID"

    with pytest.raises(ValidationError) as exc_worker_type:
        Resource.create(name="Worker Type Check", worker_type="bad-worker-type")
    assert exc_worker_type.value.code == "RESOURCE_WORKER_TYPE_INVALID"

    with pytest.raises(ValidationError) as exc_currency:
        Resource.create(name="Currency Check", currency_code="ZZZ")
    assert exc_currency.value.code == "RESOURCE_CURRENCY_INVALID"


def test_resource_service_update_validates_final_state_and_persists_code(services):
    from datetime import date

    resource_service = services["resource_service"]

    resource = resource_service.create_resource(
        "Electrical Crew",
        role="Lead",
        hourly_rate=95.0,
        currency_code="eur",
        capacity_percent=110.0,
    )

    updated = resource_service.update_resource(
        resource.id,
        expected_version=resource.version,
        name="  Electrical Crew A  ",
        role="  Field Supervisor  ",
        currency_code="usd",
        code="RES-REN-1",
        effective_on=date.today(),
    )

    assert updated.name == "Electrical Crew A"
    assert updated.role == "Field Supervisor"
    assert updated.currency_code == "USD"
    assert updated.code == "RES-REN-1"

    reloaded = resource_service.get_resource(resource.id)
    assert reloaded is not None
    assert reloaded.code == "RES-REN-1"
