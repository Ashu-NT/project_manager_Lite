from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.infrastructure.persistence.reads.financials import (
    SqlAlchemyFinanceSnapshotReader,
)
from src.infra.persistence.orm.base import Base


def _seed_multi_source_project(services) -> str:
    project = services["project_service"].create_project(
        "Phase One Finance Reader",
        start_date=date(2024, 1, 1),
        planned_budget=10000.0,
        currency="EUR",
    )
    tasks = [
        services["task_service"].create_task(
            project.id,
            f"Reader Task {index}",
            start_date=date(2024, 1, 1 + index),
            duration_days=2,
        )
        for index in range(2)
    ]
    for index, task in enumerate(tasks):
        resource = services["resource_service"].create_resource(
            f"Reader Resource {index}",
            "Engineer",
            hourly_rate=50.0 + index * 10,
            currency_code="EUR",
            rate_effective_on=date(2024, 1, 1),
        )
        project_resource = services["project_resource_service"].add_to_project(
            project_id=project.id,
            resource_id=resource.id,
            planned_hours=10.0,
            hourly_rate=50.0 + index * 10,
            currency_code="EUR",
        )
        assignment = services["task_service"].assign_project_resource(
            task_id=task.id,
            project_resource_id=project_resource.id,
            allocation_percent=100.0,
        )
        services["task_service"].set_assignment_hours(assignment.id, 2.0 + index)

    for index, amount in enumerate((100.0, 250.0)):
        services["cost_service"].add_cost_item(
            project_id=project.id,
            task_id=tasks[index].id,
            description=f"Reader Cost {index}",
            planned_amount=amount,
            committed_amount=amount / 2,
            actual_amount=amount / 4,
            cost_type=CostType.MATERIAL,
            incurred_date=date(2024, 1, 20),
            currency_code="EUR",
        )
    return project.id


def test_reader_returns_immutable_primitive_facts_without_aggregate_multiplication(
    services,
) -> None:
    project_id = _seed_multi_source_project(services)
    finance = services["finance_service"]
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test finance reader"
    )

    facts = finance._finance_snapshot_reader.read_facts(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        project_id=project_id,
        as_of=date(2024, 1, 31),
    )

    assert facts is not None
    assert is_dataclass(facts)
    assert facts.cost_item_count == 2
    assert len(facts.project_resources) == 2
    assert len(facts.assignments) == 2
    assert len(facts.resources) == 2
    assert sum(row.positive_planned for row in facts.cost_aggregates) == 350.0
    projected_values = (
        facts.project,
        *facts.tasks,
        *facts.cost_items,
        *facts.cost_aggregates,
        *facts.project_resources,
        *facts.assignments,
        *facts.resources,
    )
    assert all(not isinstance(value, Base) for value in projected_values)
    assert all(field.name != "planned_cost" for field in fields(facts))


def test_reader_fails_closed_for_wrong_tenant_or_organization(services) -> None:
    project_id = _seed_multi_source_project(services)
    reader = services["finance_service"]._finance_snapshot_reader
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="test finance reader isolation"
    )

    assert reader.read_facts(
        tenant_id="wrong-tenant",
        organization_id=scope.organization_id,
        project_id=project_id,
        as_of=date(2024, 1, 31),
    ) is None
    assert reader.read_facts(
        tenant_id=scope.tenant_id,
        organization_id="wrong-organization",
        project_id=project_id,
        as_of=date(2024, 1, 31),
    ) is None


def test_runtime_desktop_api_uses_the_concrete_finance_reader(services, monkeypatch) -> None:
    project_id = _seed_multi_source_project(services)
    finance = services["finance_service"]
    reader = finance._finance_snapshot_reader
    assert isinstance(reader, SqlAlchemyFinanceSnapshotReader)

    calls = 0
    original = reader.read_facts

    def counted_read_facts(**kwargs):
        nonlocal calls
        calls += 1
        return original(**kwargs)

    monkeypatch.setattr(reader, "read_facts", counted_read_facts)
    registry = build_desktop_api_registry(services)
    dto = registry.project_management_financials.get_finance_snapshot(project_id)

    assert calls == 1
    assert dto.project_id == project_id
    assert dto.planned > 0.0
