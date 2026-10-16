"""Portfolio adapters reuse application results rather than clone their fields."""

from dataclasses import FrozenInstanceError, replace
from decimal import Decimal

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.portfolio.dto.commands.intake import (
    PortfolioIntakeCreateCommand,
    PortfolioIntakeUpdateCommand,
)
from src.core.modules.project_management.application.portfolio.dto.commands.scoring_templates import (
    PortfolioTemplateCreateCommand,
)
from src.core.modules.project_management.application.portfolio.dto.responses.intake import (
    PortfolioIntakePageResponse,
    PortfolioIntakeResponse,
)
from src.core.modules.project_management.application.portfolio.mappers.intake import (
    map_intake_response,
)


def test_intake_results_preserve_zero_and_snapshot_domain_score(services):
    template = services["portfolio_template_commands"].create_scoring_template(
        PortfolioTemplateCreateCommand(
            name="Equal weights", strategic_weight=1, value_weight=1,
            urgency_weight=1, risk_weight=1,
        )
    )
    commands = services["portfolio_intake_commands"]
    created = commands.create_intake_item(PortfolioIntakeCreateCommand(
        title="Zero budget", sponsor_name="PMO", requested_budget=Decimal("0.00"),
        requested_capacity_percent=0, scoring_template_id=template.id,
        strategic_score=1, value_score=1, urgency_score=1, risk_score=3,
    ))
    assert isinstance(created, PortfolioIntakeResponse)
    assert created.requested_budget == Decimal("0.00")
    assert created.requested_capacity_percent == 0
    assert created.composite_score == 0
    persisted = commands._intake_repo.get(created.id)
    mapped = map_intake_response(persisted)
    # SQLite reloads these UTC columns without timezone information.
    assert mapped == replace(created, created_at=persisted.created_at, updated_at=persisted.updated_at)
    with pytest.raises(FrozenInstanceError):
        created.title = "Cannot mutate application evidence"
    updated = commands.update_intake_item(PortfolioIntakeUpdateCommand(
        item_id=created.id, title="Renamed", strategic_score=2,
    ))
    assert updated.title == "Renamed" and updated.composite_score == 1
    assert created.title == "Zero budget" and created.composite_score == 0
    listed = services["portfolio_intake_query"].list_intake_items()
    assert len(listed) == 1
    assert listed[0] == replace(updated, created_at=listed[0].created_at, updated_at=listed[0].updated_at)


def test_intake_api_returns_the_application_page_without_remapping(services, monkeypatch):
    query = services["portfolio_intake_query"]
    page = query.list_intake_items_page(sort_key="invalid", sort_direction="desc")
    assert isinstance(page, PortfolioIntakePageResponse)
    assert page.sort_key == "updatedAt"
    assert page.sort_direction == "desc"
    assert isinstance(page.items, tuple)
    monkeypatch.setattr(query, "list_intake_items_page", lambda **kwargs: page)
    api = build_desktop_api_registry(services).project_management_portfolio
    assert api.list_intake_items_page() is page
