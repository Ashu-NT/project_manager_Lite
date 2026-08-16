"""R3.3: Portfolio scalable collection query contract.

Covers the server-side pagination added for the three collections classified
SCALABLE (intake, heatmap, dependencies) and the bounded Top-N analytical
projection added for Heatmap's global pressure ranking. See
docs/pm_modernization/qml_redesign for the full classification record.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from src.core.modules.project_management.domain.portfolio import PortfolioIntakeStatus
from src.core.modules.project_management.infrastructure.persistence.orm.portfolio import (
    PortfolioIntakeItemORM,
)
from src.tests.project_management._sql_measurement_helpers import measure_sql


def _active_scope(services):
    return services["portfolio_service"]._tenant_context_service.require_active_scope_ids(
        operation_label="test scoping"
    )


def _seed_intake_rows(services, count: int, *, title_prefix: str = "Intake") -> None:
    scope = _active_scope(services)
    now = datetime.now(timezone.utc)
    rows = [
        PortfolioIntakeItemORM(
            id=f"{title_prefix.lower()}-{index:05d}",
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            title=f"{title_prefix} {index:05d}",
            sponsor_name="PMO",
            summary="",
            requested_budget=Decimal("1000"),
            requested_capacity_percent=10.0,
            target_start_date=None,
            strategic_score=3,
            value_score=3,
            urgency_score=3,
            risk_score=3,
            scoring_template_id="",
            scoring_template_name="Balanced PMO",
            strategic_weight=3,
            value_weight=2,
            urgency_weight=2,
            risk_weight=1,
            status=PortfolioIntakeStatus.PROPOSED.value,
            created_at=now,
            updated_at=now,
            version=1,
        )
        for index in range(count)
    ]
    services["session"].add_all(rows)
    services["session"].flush()


# ── Intake: authoritative server pagination ─────────────────────────────


def test_intake_page_reaches_page_two_and_total_is_authoritative(services) -> None:
    _seed_intake_rows(services, 25)
    portfolio = services["portfolio_service"]

    page1 = portfolio.list_intake_items_page(page=1, page_size=10, sort_key="title", sort_direction="asc")
    page2 = portfolio.list_intake_items_page(page=2, page_size=10, sort_key="title", sort_direction="asc")
    page3 = portfolio.list_intake_items_page(page=3, page_size=10, sort_key="title", sort_direction="asc")

    assert page1.total == 25
    assert page2.total == 25
    assert page3.total == 25
    assert len(page1.items) == 10
    assert len(page2.items) == 10
    assert len(page3.items) == 5
    ids_seen = {item.id for item in (*page1.items, *page2.items, *page3.items)}
    assert len(ids_seen) == 25, "pages must not overlap or skip rows"


def test_intake_filter_applies_before_pagination(services) -> None:
    scope = _active_scope(services)
    now = datetime.now(timezone.utc)
    approved = PortfolioIntakeItemORM(
        id="intake-approved-1",
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        title="Approved Item",
        sponsor_name="PMO",
        status=PortfolioIntakeStatus.APPROVED.value,
        created_at=now,
        updated_at=now,
    )
    services["session"].add(approved)
    services["session"].flush()
    _seed_intake_rows(services, 5, title_prefix="Proposed")

    portfolio = services["portfolio_service"]
    result = portfolio.list_intake_items_page(status=PortfolioIntakeStatus.APPROVED, page=1, page_size=10)

    assert result.total == 1
    assert [item.id for item in result.items] == ["intake-approved-1"]


def test_intake_sort_is_stable_with_id_tiebreaker(services) -> None:
    scope = _active_scope(services)
    now = datetime.now(timezone.utc)
    # Same title on every row -> only the id tiebreaker can produce a
    # deterministic order.
    rows = [
        PortfolioIntakeItemORM(
            id=f"tie-{index}",
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            title="Duplicate Title",
            sponsor_name="PMO",
            status=PortfolioIntakeStatus.PROPOSED.value,
            created_at=now,
            updated_at=now,
        )
        for index in range(3)
    ]
    services["session"].add_all(rows)
    services["session"].flush()

    portfolio = services["portfolio_service"]
    first = portfolio.list_intake_items_page(sort_key="title", sort_direction="asc", page=1, page_size=10)
    second = portfolio.list_intake_items_page(sort_key="title", sort_direction="asc", page=1, page_size=10)

    assert [item.id for item in first.items] == [item.id for item in second.items]
    assert [item.id for item in first.items] == sorted(item.id for item in first.items)


def test_intake_tenant_scope_is_enforced(services, session) -> None:
    from src.core.platform.infrastructure.persistence.orm.master_data.org.org import OrganizationORM

    scope = _active_scope(services)
    other_org = OrganizationORM(
        id="other-org-intake-scope",
        organization_code="other-org-intake-scope",
        display_name="Other Org",
        tenant_id=scope.tenant_id,
    )
    session.add(other_org)
    session.flush()
    now = datetime.now(timezone.utc)
    session.add(
        PortfolioIntakeItemORM(
            id="intake-other-org",
            tenant_id=scope.tenant_id,
            organization_id=other_org.id,
            title="Other Org Intake",
            sponsor_name="PMO",
            status=PortfolioIntakeStatus.PROPOSED.value,
            created_at=now,
            updated_at=now,
        )
    )
    session.flush()
    _seed_intake_rows(services, 3, title_prefix="Own")

    portfolio = services["portfolio_service"]
    result = portfolio.list_intake_items_page(page=1, page_size=50)

    assert result.total == 3
    assert "intake-other-org" not in {item.id for item in result.items}


# ── Intake: focused ~10k-row scale characterization ─────────────────────


def test_intake_page_scales_to_ten_thousand_rows_without_full_materialization(services) -> None:
    """Proves the LIMIT/OFFSET pagination mechanism shared by all three
    SCALABLE Portfolio collections: only the requested page is materialized
    and the query count stays fixed regardless of total row count."""
    _seed_intake_rows(services, 10_000)
    portfolio = services["portfolio_service"]

    with measure_sql(services["session"]) as stats:
        page = portfolio.list_intake_items_page(page=1, page_size=25, sort_key="title", sort_direction="asc")
    assert page.total == 10_000
    assert len(page.items) == 25
    # A COUNT + a SELECT ... LIMIT/OFFSET plus fixed per-call authorization
    # overhead -- flat regardless of the 10,000-row table, never one query
    # (or one row-materialization) per row.
    assert stats.total_statements < 10

    with measure_sql(services["session"]) as stats_deep:
        deep_page = portfolio.list_intake_items_page(
            page=400, page_size=25, sort_key="title", sort_direction="asc"
        )
    assert deep_page.total == 10_000
    assert len(deep_page.items) == 25
    assert deep_page.items[0].title == "Intake 09975"
    # Reaching page 400 costs the same query count as page 1 -- proof the
    # server never walks/fetches the skipped rows in Python.
    assert stats_deep.total_statements == stats.total_statements


# ── Heatmap: authoritative server pagination + bounded Top-N ────────────


def _seed_projects_with_financial_profile(services, count: int, *, late_task_count: int = 0):
    """Minimal projects (+ the financial profile Heatmap's reader inner-joins
    on) via the real project service, so CPM/finance computation behaves
    normally. late_task_count of the seeded projects get one overdue task to
    push their pressure score up for Top-N ranking assertions."""
    today = date.today()
    projects = []
    for index in range(count):
        project = services["project_service"].create_project(
            f"Heatmap Scale Project {index:03d}",
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=30),
            financial_currency_code="EUR",
        )
        projects.append(project)
        if index < late_task_count:
            services["task_service"].create_task(
                project.id,
                "Overdue task",
                start_date=today - timedelta(days=20),
                duration_days=5,
            )
    return projects


def test_heatmap_page_paginates_authoritatively_and_covers_all_projects(services) -> None:
    projects = _seed_projects_with_financial_profile(services, 5)
    portfolio = services["portfolio_service"]

    page1 = portfolio.list_portfolio_heatmap_page(page=1, page_size=2, sort_key="projectName", sort_direction="asc")
    page2 = portfolio.list_portfolio_heatmap_page(page=2, page_size=2, sort_key="projectName", sort_direction="asc")
    page3 = portfolio.list_portfolio_heatmap_page(page=3, page_size=2, sort_key="projectName", sort_direction="asc")

    assert page1.total == len(projects)
    seen_ids = {row.project_id for row in (*page1.items, *page2.items, *page3.items)}
    assert seen_ids == {p.id for p in projects}
    # Ascending project-name order must actually be honored, not just requested.
    names = [row.project_name for row in (*page1.items, *page2.items, *page3.items)]
    assert names == sorted(names)


def test_heatmap_page_rejects_pressure_as_a_sortable_key(services) -> None:
    _seed_projects_with_financial_profile(services, 3)
    portfolio = services["portfolio_service"]

    # pressureScore/pressureLabel are display-only on the paginated browse --
    # requesting them as a sort key must fall back to the SQL-authoritative
    # default rather than silently re-sorting the page locally in Python.
    page = portfolio.list_portfolio_heatmap_page(
        page=1, page_size=10, sort_key="pressureScore", sort_direction="desc"
    )
    names = [row.project_name for row in page.items]
    assert names == sorted(names), "unsupported sort key must fall back to projectName, not pressure"


def test_top_at_risk_projects_ranks_full_scope_before_truncating(services) -> None:
    from src.core.modules.project_management.application.portfolio.queries.portfolio_executive import (
        TOP_AT_RISK_PROJECTS_LIMIT,
    )

    # More projects than the Top-N bound, with the LAST few (alphabetically)
    # made the highest-pressure ones -- if Top-N were derived from a
    # paginated/name-sorted page instead of the full scope, it would miss them.
    total = TOP_AT_RISK_PROJECTS_LIMIT + 4
    projects = _seed_projects_with_financial_profile(services, total, late_task_count=0)
    today = date.today()
    hot_projects = projects[-3:]
    for project in hot_projects:
        services["task_service"].create_task(
            project.id,
            "Overdue task",
            start_date=today - timedelta(days=20),
            duration_days=5,
        )

    portfolio = services["portfolio_service"]
    top = portfolio.list_top_at_risk_projects()

    assert len(top) == TOP_AT_RISK_PROJECTS_LIMIT
    top_ids = {row.project_id for row in top}
    assert {p.id for p in hot_projects}.issubset(top_ids)


def test_top_at_risk_projects_is_independent_of_heatmap_page_size(services) -> None:
    _seed_projects_with_financial_profile(services, 6, late_task_count=2)
    portfolio = services["portfolio_service"]

    before = portfolio.list_top_at_risk_projects()
    portfolio.list_portfolio_heatmap_page(page=1, page_size=1)
    portfolio.list_portfolio_heatmap_page(page=2, page_size=1)
    after = portfolio.list_top_at_risk_projects()

    assert [row.project_id for row in before] == [row.project_id for row in after]


# ── Dependencies: authoritative server pagination ───────────────────────


def test_dependencies_page_paginates_and_total_is_authoritative(services) -> None:
    projects = _seed_projects_with_financial_profile(services, 6)
    portfolio = services["portfolio_service"]
    for predecessor, successor in zip(projects, projects[1:]):
        portfolio.create_project_dependency(
            predecessor_project_id=predecessor.id,
            successor_project_id=successor.id,
            summary="chain",
        )

    total_deps = len(projects) - 1
    page1 = portfolio.list_project_dependencies_page(page=1, page_size=2)
    page2 = portfolio.list_project_dependencies_page(page=2, page_size=2)

    assert page1.total == total_deps
    assert page2.total == total_deps
    ids_seen = {item.dependency_id for item in (*page1.items, *page2.items)}
    assert len(ids_seen) == min(total_deps, 4)


def test_dependencies_page_search_filters_before_pagination(services) -> None:
    projects = _seed_projects_with_financial_profile(services, 3)
    portfolio = services["portfolio_service"]
    portfolio.create_project_dependency(
        predecessor_project_id=projects[0].id,
        successor_project_id=projects[1].id,
        summary="uniquely-searchable-token",
    )
    portfolio.create_project_dependency(
        predecessor_project_id=projects[1].id,
        successor_project_id=projects[2].id,
        summary="unrelated",
    )

    result = portfolio.list_project_dependencies_page(search_text="uniquely-searchable-token", page=1, page_size=10)

    assert result.total == 1
    assert result.items[0].summary == "uniquely-searchable-token"


def test_dependencies_page_rejects_pressure_as_a_sortable_key(services) -> None:
    projects = _seed_projects_with_financial_profile(services, 3)
    portfolio = services["portfolio_service"]
    portfolio.create_project_dependency(
        predecessor_project_id=projects[0].id,
        successor_project_id=projects[1].id,
    )
    portfolio.create_project_dependency(
        predecessor_project_id=projects[1].id,
        successor_project_id=projects[2].id,
    )

    page = portfolio.list_project_dependencies_page(sort_key="pressureLabel", sort_direction="desc", page=1, page_size=10)
    # Falls back to the default (updatedAt) rather than raising or silently
    # local-sorting by the unsupported computed field.
    assert page.total == 2


# ── R3.4 groundwork: desktop API pagination pass-through ────────────────


def test_desktop_api_intake_page_passes_through_and_serializes(services) -> None:
    from src.core.modules.project_management.api.desktop import (
        build_project_management_portfolio_desktop_api,
    )

    _seed_intake_rows(services, 15)
    api = build_project_management_portfolio_desktop_api(portfolio_service=services["portfolio_service"])

    page1 = api.list_intake_items_page(page=1, page_size=10, sort_key="title", sort_direction="asc")
    page2 = api.list_intake_items_page(page=2, page_size=10, sort_key="title", sort_direction="asc")

    assert page1.total == 15
    assert len(page1.items) == 10
    assert len(page2.items) == 5
    assert all(item.title.startswith("Intake") for item in page1.items)


def test_desktop_api_heatmap_page_and_top_at_risk_are_distinct(services) -> None:
    from src.core.modules.project_management.api.desktop import (
        build_project_management_portfolio_desktop_api,
    )

    projects = _seed_projects_with_financial_profile(services, 3)
    api = build_project_management_portfolio_desktop_api(portfolio_service=services["portfolio_service"])

    page = api.list_heatmap_page(page=1, page_size=25, sort_key="projectName", sort_direction="asc")
    top_at_risk = api.list_top_at_risk_projects()

    assert page.total == len(projects)
    assert {row.project_id for row in page.items} == {p.id for p in projects}
    assert len(top_at_risk) == len(projects)  # fewer projects than the top_n bound


def test_desktop_api_dependencies_page_serializes_project_labels(services) -> None:
    from src.core.modules.project_management.api.desktop import (
        build_project_management_portfolio_desktop_api,
    )

    projects = _seed_projects_with_financial_profile(services, 2)
    portfolio = services["portfolio_service"]
    portfolio.create_project_dependency(
        predecessor_project_id=projects[0].id,
        successor_project_id=projects[1].id,
        summary="api-level check",
    )
    api = build_project_management_portfolio_desktop_api(portfolio_service=services["portfolio_service"])

    page = api.list_dependencies_page(page=1, page_size=10)

    assert page.total == 1
    assert page.items[0].predecessor_project_name == projects[0].name
    assert page.items[0].successor_project_name == projects[1].name
