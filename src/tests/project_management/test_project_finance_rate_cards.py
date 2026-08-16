from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.core.modules.project_management.domain.financials.rate_cards import (
    ProjectRateCard,
    RateCardLine,
    RateLineOrigin,
    RateModifier,
    RateType,
)
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError


def _line(**overrides) -> RateCardLine:
    values = dict(
        tenant_id="tenant-a",
        organization_id="org-a",
        rate_card_id="card-1",
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("50"),
        rate_currency="USD",
        resource_id="resource-1",
    )
    values.update(overrides)
    return RateCardLine.create(**values)


def test_rate_card_line_domain_validation() -> None:
    line = _line()
    assert line.rate_type == RateType.COST
    assert line.origin == RateLineOrigin.CONFIGURED
    assert line.is_effective_on(date(2026, 1, 1))

    dated = _line(
        resource_id="resource-1",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 6, 30),
    )
    assert dated.is_effective_on(date(2026, 3, 1))
    assert not dated.is_effective_on(date(2026, 7, 1))

    with pytest.raises(ValidationError, match="supplied together"):
        _line(resource_id="resource-1", customer_party_id="cust-1")

    with pytest.raises(ValidationError, match="also identify a resource"):
        _line(
            resource_id=None,
            role="engineer",
            customer_party_id="cust-1",
            contract_reference="ctr-1",
        )

    with pytest.raises(ValidationError, match="never both"):
        _line(resource_id="resource-1", role="engineer")

    with pytest.raises(ValidationError, match="must match a resource"):
        _line(resource_id=None)

    with pytest.raises(ValidationError, match="cannot be before its start"):
        _line(
            resource_id="resource-1",
            effective_from=date(2026, 6, 1),
            effective_to=date(2026, 1, 1),
        )

    with pytest.raises(ValidationError, match="cannot be negative"):
        _line(resource_id="resource-1", rate_amount=Decimal("-1"))

    with pytest.raises(ValidationError):
        _line(resource_id="resource-1", rate_type="invalid")


def test_rate_card_line_specificity_dimension_count() -> None:
    one_dim = _line(resource_id=None, role="engineer")
    two_dim = _line(resource_id=None, role="engineer", skill_code="python")
    three_dim = _line(
        resource_id=None, role="engineer", skill_code="python", department_id="dept-1"
    )
    assert one_dim.specificity_dimension_count == 1
    assert two_dim.specificity_dimension_count == 2
    assert three_dim.specificity_dimension_count == 3


def test_project_rate_card_scope() -> None:
    org_wide = ProjectRateCard.create(
        tenant_id="tenant-a", organization_id="org-a", name="Org Rates"
    )
    assert org_wide.is_organization_wide
    project_scoped = replace(org_wide, project_id="project-1")
    assert not project_scoped.is_organization_wide


def test_get_or_create_legacy_card_is_idempotent(services) -> None:
    from sqlalchemy import select

    from src.core.modules.project_management.infrastructure.persistence.orm.rate_cards import (
        ProjectRateCardORM,
    )
    from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_cards import (
        SqlAlchemyProjectRateCardRepository,
    )

    session = services["session"]
    repo = SqlAlchemyProjectRateCardRepository(session)
    tenant_id, organization_id = _context_ids(services)

    first = repo.get_or_create_legacy_card(
        tenant_id=tenant_id, organization_id=organization_id, currency_code="USD"
    )
    assert first.is_legacy
    session.flush()

    second = repo.get_or_create_legacy_card(
        tenant_id=tenant_id, organization_id=organization_id, currency_code="USD"
    )
    assert second.id == first.id

    count = session.execute(
        select(ProjectRateCardORM).where(
            ProjectRateCardORM.tenant_id == tenant_id,
            ProjectRateCardORM.organization_id == organization_id,
            ProjectRateCardORM.card_kind == "legacy",
        )
    ).all()
    assert len(count) == 1


def _create_project_and_resource(services, *, name: str) -> tuple[str, str]:
    project = services["project_service"].create_project(
        f"{name} project", financial_currency_code="USD"
    )
    resource = services["resource_service"].create_resource(
        f"{name} resource",
        role="engineer",
        hourly_rate=0.0,
    )
    return project.id, resource.id


def _context_ids(services) -> tuple[str, str]:
    user_session = services["user_session"]
    return user_session.stored_active_tenant_id(), user_session.stored_active_organization_id()


def test_resolver_fails_closed_when_no_rate_card_exists(services) -> None:
    _project_id, resource_id = _create_project_and_resource(services, name="fail-closed")
    resolver = services["rate_card_resolver"]
    tenant_id, organization_id = _context_ids(services)
    with pytest.raises(BusinessRuleError, match="No applicable"):
        resolver.resolve(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=None,
            resource_id=resource_id,
            rate_type=RateType.COST,
            as_of=date.today(),
            unit="HOUR",
        )


def test_resolver_prefers_project_override_over_organization_line(services) -> None:
    project_id, resource_id = _create_project_and_resource(services, name="precedence")
    rate_card_service = services["rate_card_service"]
    resolver = services["rate_card_resolver"]
    tenant_id, organization_id = _context_ids(services)

    org_card = rate_card_service.create_rate_card(name="Org Rates")
    rate_card_service.create_line(
        org_card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("40"),
        rate_currency="USD",
        resource_id=resource_id,
    )
    org_snapshot = resolver.resolve(
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=project_id,
        resource_id=resource_id,
        rate_type=RateType.COST,
        as_of=date.today(),
        unit="HOUR",
    )
    assert org_snapshot.precedence_level == 4
    assert org_snapshot.monetary_rate.money.amount == Decimal("40")

    project_card = rate_card_service.create_rate_card(name="Project Rates", project_id=project_id)
    rate_card_service.create_line(
        project_card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("65"),
        rate_currency="USD",
        resource_id=resource_id,
    )
    project_snapshot = resolver.resolve(
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=project_id,
        resource_id=resource_id,
        rate_type=RateType.COST,
        as_of=date.today(),
        unit="HOUR",
    )
    assert project_snapshot.precedence_level == 2
    assert project_snapshot.monetary_rate.money.amount == Decimal("65")

    # Organization-wide line is still what a DIFFERENT project sees.
    other_project_id, _ = _create_project_and_resource(services, name="other-project")
    other_snapshot = resolver.resolve(
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=other_project_id,
        resource_id=resource_id,
        rate_type=RateType.COST,
        as_of=date.today(),
        unit="HOUR",
    )
    assert other_snapshot.precedence_level == 4


def test_resolver_never_crosses_cost_and_billing_rate_types(services) -> None:
    _project_id, resource_id = _create_project_and_resource(services, name="rate-type")
    rate_card_service = services["rate_card_service"]
    resolver = services["rate_card_resolver"]
    tenant_id, organization_id = _context_ids(services)

    card = rate_card_service.create_rate_card(name="Org Rates")
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.BILLING,
        unit="HOUR",
        rate_amount=Decimal("120"),
        rate_currency="USD",
        resource_id=resource_id,
    )
    with pytest.raises(BusinessRuleError, match="No applicable"):
        resolver.resolve(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=None,
            resource_id=resource_id,
            rate_type=RateType.COST,
            as_of=date.today(),
            unit="HOUR",
        )
    billing_snapshot = resolver.resolve(
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=None,
        resource_id=resource_id,
        rate_type=RateType.BILLING,
        as_of=date.today(),
        unit="HOUR",
    )
    assert billing_snapshot.monetary_rate.money.amount == Decimal("120")


def test_reject_overlap_catches_cross_card_duplicates_in_the_same_scope(services) -> None:
    # Overlap prevention must compare across every card sharing the same
    # scope (here: the same project), not just siblings within one card —
    # otherwise two independently-managed cards could each define a
    # conflicting "engineer" line and neither creation would be rejected.
    project_id, _resource_id = _create_project_and_resource(services, name="cross-card")
    rate_card_service = services["rate_card_service"]

    first_card = rate_card_service.create_rate_card(name="Card A", project_id=project_id)
    rate_card_service.create_line(
        first_card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("55"),
        rate_currency="USD",
        role="engineer",
    )
    second_card = rate_card_service.create_rate_card(name="Card B", project_id=project_id)
    with pytest.raises(BusinessRuleError, match="overlapping effective window"):
        rate_card_service.create_line(
            second_card.id,
            rate_type=RateType.COST,
            unit="HOUR",
            rate_amount=Decimal("60"),
            rate_currency="USD",
            role="engineer",
        )


def test_resolver_raises_on_ambiguous_equal_specificity_different_dimensions(services) -> None:
    # Two DIFFERENT selection keys (role-only vs skill-only) never trip the
    # overlap check (different shape), but can still tie in specificity
    # count (1 each) against a resource that satisfies both — this is the
    # genuine resolver-level ambiguity the equal-specificity check exists
    # for, distinct from the create-time overlap check above.
    project_id, resource_id = _create_project_and_resource(services, name="ambiguous")
    services["resource_service"].add_resource_skill(resource_id, "python", "Python")
    rate_card_service = services["rate_card_service"]
    resolver = services["rate_card_resolver"]
    tenant_id, organization_id = _context_ids(services)

    card = rate_card_service.create_rate_card(name="Project Rates", project_id=project_id)
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("55"),
        rate_currency="USD",
        role="engineer",
    )
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("60"),
        rate_currency="USD",
        skill_code="python",
    )
    with pytest.raises(BusinessRuleError, match="equal specificity"):
        resolver.resolve(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            resource_id=resource_id,
            rate_type=RateType.COST,
            as_of=date.today(),
            unit="HOUR",
        )


def test_overlapping_same_selection_key_lines_are_rejected(services) -> None:
    project_id, resource_id = _create_project_and_resource(services, name="overlap")
    rate_card_service = services["rate_card_service"]

    card = rate_card_service.create_rate_card(name="Project Rates", project_id=project_id)
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("50"),
        rate_currency="USD",
        resource_id=resource_id,
    )
    with pytest.raises(BusinessRuleError, match="overlapping effective window"):
        rate_card_service.create_line(
            card.id,
            rate_type=RateType.COST,
            unit="HOUR",
            rate_amount=Decimal("70"),
            rate_currency="USD",
            resource_id=resource_id,
        )


def test_resolver_requires_customer_and_contract_together(services) -> None:
    _project_id, resource_id = _create_project_and_resource(services, name="cust-contract")
    resolver = services["rate_card_resolver"]
    tenant_id, organization_id = _context_ids(services)
    with pytest.raises(ValidationError, match="supplied together"):
        resolver.resolve(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=None,
            resource_id=resource_id,
            rate_type=RateType.COST,
            as_of=date.today(),
            unit="HOUR",
            customer_party_id="cust-1",
        )


def test_resolver_raises_when_requested_modifier_not_configured(services) -> None:
    _project_id, resource_id = _create_project_and_resource(services, name="no-modifier")
    rate_card_service = services["rate_card_service"]
    resolver = services["rate_card_resolver"]
    tenant_id, organization_id = _context_ids(services)

    card = rate_card_service.create_rate_card(name="Org Rates")
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("50"),
        rate_currency="USD",
        resource_id=resource_id,
    )
    with pytest.raises(BusinessRuleError, match="no overtime multiplier configured"):
        resolver.resolve(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=None,
            resource_id=resource_id,
            rate_type=RateType.COST,
            as_of=date.today(),
            unit="HOUR",
            modifier=RateModifier.OVERTIME,
        )


def test_resolver_applies_a_single_modifier_and_snapshot_is_immutable(services) -> None:
    _project_id, resource_id = _create_project_and_resource(services, name="modifier")
    rate_card_service = services["rate_card_service"]
    resolver = services["rate_card_resolver"]
    tenant_id, organization_id = _context_ids(services)

    card = rate_card_service.create_rate_card(name="Org Rates")
    rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("50"),
        rate_currency="USD",
        resource_id=resource_id,
        overtime_multiplier=Decimal("1.5"),
    )
    snapshot = resolver.resolve(
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=None,
        resource_id=resource_id,
        rate_type=RateType.COST,
        as_of=date.today(),
        unit="HOUR",
        modifier=RateModifier.OVERTIME,
    )
    assert snapshot.monetary_rate.money.amount == Decimal("75.0")
    assert snapshot.modifiers_applied == {"overtime": Decimal("1.5")}
    with pytest.raises(TypeError):
        snapshot.modifiers_applied["overtime"] = Decimal("2")
    with pytest.raises(Exception):
        snapshot.modifier_applied = None


def _legacy_lines_for_resource(services, resource_id: str) -> list[RateCardLine]:
    from sqlalchemy import select

    from src.core.modules.project_management.infrastructure.persistence.mappers.rate_cards import (
        rate_card_line_from_orm,
    )
    from src.core.modules.project_management.infrastructure.persistence.orm.rate_cards import (
        RateCardLineORM,
    )

    session = services["session"]
    rows = session.execute(
        select(RateCardLineORM).where(
            RateCardLineORM.resource_id == resource_id,
            RateCardLineORM.origin == RateLineOrigin.LEGACY_SEEDED.value,
        )
    ).scalars().all()
    return [rate_card_line_from_orm(row) for row in rows]


def test_create_resource_seeds_legacy_rate_line_with_real_effective_from(services) -> None:
    resource = services["resource_service"].create_resource(
        "Seeded Dev", role="Developer", hourly_rate=90.0, currency_code="usd"
    )
    lines = _legacy_lines_for_resource(services, resource.id)
    assert len(lines) == 1
    assert lines[0].effective_from is not None
    assert lines[0].effective_from == date.today()
    assert lines[0].rate_amount == Decimal("90.0")
    assert lines[0].is_active


def test_create_resource_with_zero_rate_seeds_no_line(services) -> None:
    resource = services["resource_service"].create_resource(
        "Zero Rate Dev", role="Developer", hourly_rate=0.0
    )
    assert _legacy_lines_for_resource(services, resource.id) == []


def test_update_resource_requires_expected_version_for_rate_change(services) -> None:
    resource_service = services["resource_service"]
    resource = resource_service.create_resource(
        "Version Required Dev", role="Developer", hourly_rate=90.0
    )
    with pytest.raises(ValidationError) as exc:
        resource_service.update_resource(
            resource.id, hourly_rate=100.0, effective_on=date.today()
        )
    assert exc.value.code == "RESOURCE_RATE_VERSION_REQUIRED"


def test_update_resource_defaults_rate_change_effective_date_from_service_clock(
    services,
) -> None:
    resource_service = services["resource_service"]
    resource = resource_service.create_resource(
        "Effective On Required Dev", role="Developer", hourly_rate=90.0
    )
    effective_on = resource_service._clock.today()

    resource_service.update_resource(
        resource.id,
        hourly_rate=100.0,
        expected_version=resource.version,
    )

    replacement = next(
        line
        for line in _legacy_lines_for_resource(services, resource.id)
        if line.rate_amount == Decimal("100.0")
    )
    assert replacement.effective_from == effective_on


def test_update_resource_ignores_unchanged_rate_fields_for_rate_policy(services) -> None:
    resource_service = services["resource_service"]
    resource = resource_service.create_resource(
        "Unchanged Rate Dev", role="Developer", hourly_rate=90.0, currency_code="usd"
    )

    updated = resource_service.update_resource(
        resource.id,
        name="Renamed Unchanged Rate Dev",
        hourly_rate=90.0,
        currency_code="USD",
        expected_version=resource.version,
    )

    assert updated.name == "Renamed Unchanged Rate Dev"
    assert len(_legacy_lines_for_resource(services, resource.id)) == 1


def test_update_resource_same_day_positive_to_positive_deactivates_and_replaces(
    services,
) -> None:
    resource_service = services["resource_service"]
    resource = resource_service.create_resource(
        "Same Day Dev", role="Developer", hourly_rate=90.0
    )
    today = date.today()
    updated = resource_service.update_resource(
        resource.id,
        hourly_rate=110.0,
        expected_version=resource.version,
        effective_on=today,
    )
    lines = _legacy_lines_for_resource(services, updated.id)
    assert len(lines) == 2
    old_line = next(line for line in lines if line.rate_amount == Decimal("90.0"))
    new_line = next(line for line in lines if line.rate_amount == Decimal("110.0"))
    assert old_line.is_active is False
    assert new_line.is_active is True
    assert new_line.effective_from == today
    assert new_line.effective_to is None


def test_update_resource_later_date_positive_to_positive_closes_and_opens(services) -> None:
    resource_service = services["resource_service"]
    resource = resource_service.create_resource(
        "Later Date Dev", role="Developer", hourly_rate=90.0
    )
    later = date.today() + timedelta(days=10)
    resource_service.update_resource(
        resource.id,
        hourly_rate=120.0,
        expected_version=resource.version,
        effective_on=later,
    )
    lines = _legacy_lines_for_resource(services, resource.id)
    old_line = next(line for line in lines if line.rate_amount == Decimal("90.0"))
    new_line = next(line for line in lines if line.rate_amount == Decimal("120.0"))
    assert old_line.effective_to == later - timedelta(days=1)
    assert old_line.is_active
    assert new_line.effective_from == later
    assert new_line.effective_to is None


def test_update_resource_backdated_raises(services) -> None:
    resource_service = services["resource_service"]
    resource = resource_service.create_resource(
        "Backdate Dev", role="Developer", hourly_rate=90.0
    )
    earlier = date.today() - timedelta(days=10)
    with pytest.raises(BusinessRuleError, match="backdated"):
        resource_service.update_resource(
            resource.id,
            hourly_rate=120.0,
            expected_version=resource.version,
            effective_on=earlier,
        )


def test_update_resource_positive_to_zero_deactivates_with_no_replacement(services) -> None:
    resource_service = services["resource_service"]
    resource = resource_service.create_resource(
        "Retiring Dev", role="Developer", hourly_rate=90.0
    )
    today = date.today()
    resource_service.update_resource(
        resource.id, hourly_rate=0.0, expected_version=resource.version, effective_on=today
    )
    lines = _legacy_lines_for_resource(services, resource.id)
    assert len(lines) == 1
    assert lines[0].is_active is False


def test_update_resource_zero_to_zero_touches_no_rate_line(services) -> None:
    resource_service = services["resource_service"]
    resource = resource_service.create_resource(
        "Still Zero Dev", role="Developer", hourly_rate=0.0
    )
    resource_service.update_resource(
        resource.id, hourly_rate=0.0, expected_version=resource.version, effective_on=date.today()
    )
    assert _legacy_lines_for_resource(services, resource.id) == []


def test_update_resource_currency_only_change_goes_through_supersession(services) -> None:
    resource_service = services["resource_service"]
    resource = resource_service.create_resource(
        "Currency Change Dev", role="Developer", hourly_rate=80.0, currency_code="eur"
    )
    today = date.today()
    resource_service.update_resource(
        resource.id,
        currency_code="usd",
        expected_version=resource.version,
        effective_on=today,
    )
    lines = _legacy_lines_for_resource(services, resource.id)
    assert len(lines) == 2
    old_line = next(line for line in lines if line.rate_currency == "EUR")
    new_line = next(line for line in lines if line.rate_currency == "USD")
    assert old_line.is_active is False
    assert new_line.is_active is True
    assert new_line.rate_amount == Decimal("80.0")
