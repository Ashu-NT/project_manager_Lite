from __future__ import annotations

from decimal import Decimal
from time import perf_counter

import pytest
from sqlalchemy import event, text

from src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, int(len(ordered) * 0.95) - 1)]


@pytest.mark.parametrize("resource_count", [100, 1_000, 10_000])
def test_r5b_resource_catalog_scale_measurement(services, resource_count: int) -> None:
    session = services["project_service"]._session
    user_session = services["user_session"]
    tenant_id = user_session.stored_active_tenant_id()
    organization_id = user_session.stored_active_organization_id()
    session.bulk_insert_mappings(
        ResourceORM,
        [
            {
                "id": f"r5b-perf-{resource_count}-{index:05d}",
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "resource_code": f"R5B-{resource_count}-{index:05d}",
                "name": f"Resource {index:05d}",
                "role": "Planner" if index % 2 else "Engineer",
                "hourly_rate": Decimal("0"),
                "is_active": index % 5 != 0,
                "capacity_percent": float(80 + index % 5 * 5),
                "cost_type": CostType.LABOR,
                "worker_type": WorkerType.EMPLOYEE if index % 2 else WorkerType.EXTERNAL,
                "version": 1,
            }
            for index in range(resource_count)
        ],
    )
    session.flush()

    resource_service = services["resource_service"]
    resource_service.query_catalog_page(page=1, page_size=25)
    engine = session.get_bind()
    statement_count = 0

    def count_statement(*_args, **_kwargs) -> None:
        nonlocal statement_count
        statement_count += 1

    elapsed_ms: list[float] = []
    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        for _ in range(7):
            before = perf_counter()
            page = resource_service.query_catalog_page(
                search_text="Resource",
                page=1,
                page_size=25,
                sort_key="title",
                sort_direction="asc",
            )
            elapsed_ms.append((perf_counter() - before) * 1_000.0)
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    per_query_statements = statement_count // len(elapsed_ms)
    p95_ms = _p95(elapsed_ms)
    print(
        f"R5B catalog resources={resource_count} p50_ms={sorted(elapsed_ms)[len(elapsed_ms)//2]:.2f} "
        f"p95_ms={p95_ms:.2f} statements={per_query_statements}"
    )
    assert page.filtered_total == resource_count
    assert len(page.items) == 25
    assert per_query_statements <= 4
    assert p95_ms <= 200.0


def test_r5b_resource_inspector_scale_measurement(services) -> None:
    resource = services["resource_service"].create_resource(
        name="Inspector Performance Resource",
        role="Planner",
    )
    resource_service = services["resource_service"]
    cold_started = perf_counter()
    resource_service.get_resource_inspector(resource.id)
    cold_ms = (perf_counter() - cold_started) * 1_000.0

    elapsed_ms: list[float] = []
    session = services["project_service"]._session
    engine = session.get_bind()
    statement_count = 0

    def count_statement(*_args, **_kwargs) -> None:
        nonlocal statement_count
        statement_count += 1

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        for _ in range(10):
            before = perf_counter()
            resource_service.get_resource_inspector(resource.id)
            elapsed_ms.append((perf_counter() - before) * 1_000.0)
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    p95_ms = _p95(elapsed_ms)
    per_query_statements = statement_count // len(elapsed_ms)
    print(
        f"R5B inspector p50_ms={sorted(elapsed_ms)[len(elapsed_ms)//2]:.2f} "
        f"p95_ms={p95_ms:.2f} cold_ms={cold_ms:.2f} statements={per_query_statements}"
    )
    assert per_query_statements <= 2
    assert p95_ms <= 100.0
    assert cold_ms <= 300.0


def test_r5b_resource_summary_scale_measurement(services) -> None:
    resource = services["resource_service"].create_resource(
        name="Summary Performance Resource",
        role="Planner",
    )
    resource_service = services["resource_service"]
    resource_service.get_resource_summary(resource.id)
    elapsed_ms: list[float] = []
    session = services["project_service"]._session
    engine = session.get_bind()
    statement_count = 0

    def count_statement(*_args, **_kwargs) -> None:
        nonlocal statement_count
        statement_count += 1

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        for _ in range(10):
            before = perf_counter()
            resource_service.get_resource_summary(resource.id)
            elapsed_ms.append((perf_counter() - before) * 1_000.0)
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    p95_ms = _p95(elapsed_ms)
    per_query_statements = statement_count // len(elapsed_ms)
    print(
        f"R5B summary p50_ms={sorted(elapsed_ms)[len(elapsed_ms)//2]:.2f} "
        f"p95_ms={p95_ms:.2f} statements={per_query_statements}"
    )
    assert per_query_statements <= 2
    assert p95_ms <= 300.0


def test_r5b_resource_catalog_sqlite_query_plan_evidence(services) -> None:
    session = services["project_service"]._session
    user_session = services["user_session"]
    params = {
        "tenant_id": user_session.stored_active_tenant_id(),
        "organization_id": user_session.stored_active_organization_id(),
        "pattern": "%planner%",
    }
    representative_queries = {
        "default_page": """
            SELECT id FROM resources
            WHERE tenant_id = :tenant_id AND organization_id = :organization_id
            ORDER BY is_active DESC, lower(name), id LIMIT 25
        """,
        "name_search": """
            SELECT id FROM resources
            WHERE tenant_id = :tenant_id AND organization_id = :organization_id
              AND lower(name) LIKE :pattern
            ORDER BY lower(name), id LIMIT 25
        """,
        "code_search": """
            SELECT id FROM resources
            WHERE tenant_id = :tenant_id AND organization_id = :organization_id
              AND lower(coalesce(resource_code, '')) LIKE :pattern
            ORDER BY lower(coalesce(resource_code, '')), id LIMIT 25
        """,
        "status_filter": """
            SELECT id FROM resources
            WHERE tenant_id = :tenant_id AND organization_id = :organization_id
              AND is_active = 1
            ORDER BY lower(name), id LIMIT 25
        """,
        "role_sort": """
            SELECT id FROM resources
            WHERE tenant_id = :tenant_id AND organization_id = :organization_id
            ORDER BY lower(coalesce(role, '')), id LIMIT 25
        """,
        "capacity_sort": """
            SELECT id FROM resources
            WHERE tenant_id = :tenant_id AND organization_id = :organization_id
            ORDER BY capacity_percent, id LIMIT 25
        """,
    }

    plans: dict[str, tuple[str, ...]] = {}
    for name, query in representative_queries.items():
        rows = session.execute(text(f"EXPLAIN QUERY PLAN {query}"), params).all()
        plans[name] = tuple(str(row[3]) for row in rows)

    print(f"R5B SQLite query plans={plans}")
    assert set(plans) == set(representative_queries)
    assert all(plan for plan in plans.values())
