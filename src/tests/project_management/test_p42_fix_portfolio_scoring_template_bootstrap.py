from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.modules.project_management.application.portfolio.event_handlers.view_invalidation import (
    PORTFOLIO_CATEGORY,
)
from src.core.modules.project_management.application.portfolio.portfolio_events import (
    PortfolioScoringTemplateChangeType,
    PortfolioScoringTemplateChanged,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.common.exceptions import ConcurrencyError


class _Boom(RuntimeError):
    pass


def _boom(*_args, **_kwargs):
    raise _Boom("forced failure for P42-FIX bootstrap test")


def _spy_hints(services):
    hints: list = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )
    return hints


def _portfolio_hints(hints):
    return [h for h in hints if h.category == PORTFOLIO_CATEGORY]


def test_existing_template_read_performs_zero_writes_zero_audit_zero_events(services):
    portfolio = services["portfolio_service"]
    # Pre-seed for real, through the canonical command path, so "already bootstrapped" reflects
    # genuine prior state rather than a fixture shortcut.
    portfolio.create_scoring_template(name="P42-FIX pre-seed", activate=True)

    from sqlalchemy import select

    from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
        AuditEntryORM,
    )

    audit_before = services["session"].execute(select(AuditEntryORM.id)).scalars().all()
    hints = _spy_hints(services)

    templates = portfolio.list_scoring_templates()
    active = portfolio.get_active_scoring_template()

    assert len(templates) >= 1
    assert active.is_active is True
    assert _portfolio_hints(hints) == []
    audit_after = services["session"].execute(select(AuditEntryORM.id)).scalars().all()
    assert audit_after == audit_before


def test_first_bootstrap_via_query_creates_exactly_one_default_atomically(services):
    portfolio = services["portfolio_service"]
    assert portfolio._scoring_template_repo.list() == [], "fresh organization: no templates yet"
    hints = _spy_hints(services)

    templates = portfolio.list_scoring_templates()

    assert len(templates) == 1
    assert templates[0].name == portfolio.DEFAULT_TEMPLATE_NAME
    assert templates[0].is_active is True

    from sqlalchemy import select

    from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
        AuditEntryORM,
    )

    services["session"].commit()
    rows = services["session"].execute(
        select(AuditEntryORM).where(AuditEntryORM.entity_id == templates[0].id)
    ).scalars().all()
    assert [row.operation for row in rows] == ["create"]

    portfolio_hints = _portfolio_hints(hints)
    assert len(portfolio_hints) == 1, "one semantic ViewInvalidation target after dedupe"

    # Second identical read: zero further mutation, zero further audit, zero further events.
    hints_after = _spy_hints(services)
    audit_before = services["session"].execute(select(AuditEntryORM.id)).scalars().all()

    templates_again = portfolio.list_scoring_templates()

    assert len(templates_again) == 1
    assert templates_again[0].id == templates[0].id
    assert _portfolio_hints(hints_after) == []
    audit_after = services["session"].execute(select(AuditEntryORM.id)).scalars().all()
    assert audit_after == audit_before


def test_first_bootstrap_via_get_active_template_produces_the_typed_event(services):
    portfolio = services["portfolio_service"]
    assert portfolio._scoring_template_repo.list() == []
    hints = _spy_hints(services)

    active = portfolio.get_active_scoring_template()

    assert active.name == portfolio.DEFAULT_TEMPLATE_NAME
    portfolio_hints = _portfolio_hints(hints)
    assert len(portfolio_hints) == 1


def test_bootstrap_failure_on_audit_leaves_zero_partial_state(services, monkeypatch):
    portfolio = services["portfolio_service"]
    assert portfolio._scoring_template_repo.list() == []
    hints = _spy_hints(services)
    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    with pytest.raises(_Boom):
        portfolio.list_scoring_templates()

    assert portfolio._scoring_template_repo.list() == []
    assert _portfolio_hints(hints) == []


def test_bootstrap_failure_on_repository_add_leaves_zero_partial_state(services, monkeypatch):
    from src.core.modules.project_management.infrastructure.persistence.repositories.portfolio.portfolio import (
        SqlAlchemyPortfolioScoringTemplateRepository,
    )

    portfolio = services["portfolio_service"]
    assert portfolio._scoring_template_repo.list() == []
    hints = _spy_hints(services)
    monkeypatch.setattr(SqlAlchemyPortfolioScoringTemplateRepository, "add", _boom)

    with pytest.raises(_Boom):
        portfolio.get_active_scoring_template()

    monkeypatch.undo()
    assert portfolio._scoring_template_repo.list() == []
    assert _portfolio_hints(hints) == []


def test_concurrent_first_bootstrap_is_prevented_by_the_database_constraint(services):
    portfolio = services["portfolio_service"]
    assert portfolio._scoring_template_repo.list() == []
    hints = _spy_hints(services)

    uow_a = portfolio._uow_factory.create(context=portfolio._new_context())
    uow_b = portfolio._uow_factory.create(context=portfolio._new_context())

    events_a: list = []
    events_b: list = []
    winner_templates = portfolio._ensure_scoring_templates(uow=uow_a, events=events_a)
    portfolio._ensure_scoring_templates(uow=uow_b, events=events_b)

    for event in events_a:
        uow_a.record_event(event)
    uow_a.commit()

    for event in events_b:
        uow_b.record_event(event)
    with pytest.raises(IntegrityError):
        uow_b.commit()

    winner = winner_templates[0]
    final = portfolio._scoring_template_repo.list()
    assert len(final) == 1, "the database rejected the loser's duplicate -- exactly one row persisted"
    assert final[0].id == winner.id
    assert final[0].is_active is True
    assert len(_portfolio_hints(hints)) == 1, "only the winner's commit produced a ViewInvalidation hint"


def test_scoring_templates_with_bootstrap_recovers_cleanly_when_commit_loses_the_race(
    services, monkeypatch
):
    from src.core.modules.project_management.infrastructure.persistence.uow.portfolio.portfolio_unit_of_work import (
        SqlAlchemyPortfolioUnitOfWork,
    )

    portfolio = services["portfolio_service"]
    seeded = portfolio.create_scoring_template(name="Already Won The Race", activate=True)
    baseline_ids = sorted(t.id for t in portfolio._scoring_template_repo.list())
    hints = _spy_hints(services)

    real_list = portfolio._scoring_template_repo.list
    calls = {"n": 0}

    def _stale_on_first_call():
        calls["n"] += 1
        if calls["n"] == 1:
            return []
        return real_list()

    def _raise_integrity_error(self):
        raise IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed"))

    monkeypatch.setattr(portfolio._scoring_template_repo, "list", _stale_on_first_call)
    monkeypatch.setattr(SqlAlchemyPortfolioUnitOfWork, "commit", _raise_integrity_error)

    result = portfolio.list_scoring_templates()

    assert sorted(t.id for t in result) == baseline_ids, "zero new rows from the lost race"
    active = [t for t in result if t.is_active]
    assert len(active) == 1
    assert active[0].id == seeded.id
    assert _portfolio_hints(hints) == [], "the lost race produced zero ViewInvalidation hints"

    monkeypatch.undo()
    final = portfolio._scoring_template_repo.list()
    assert sorted(t.id for t in final) == baseline_ids, (
        "zero duplicate rows persisted -- the forced commit failure left zero partial state"
    )


def test_explicit_activate_conflict_maps_integrity_error_to_concurrency_error(services, monkeypatch):
    """Explicit commands (unlike idempotent bootstrap) must not silently retry a lost race --
    the loser gets the project's own ConcurrencyError, mapped from the raw IntegrityError."""
    from src.core.modules.project_management.infrastructure.persistence.uow.portfolio.portfolio_unit_of_work import (
        SqlAlchemyPortfolioUnitOfWork,
    )

    portfolio = services["portfolio_service"]
    first = portfolio.create_scoring_template(name="Alpha", activate=True)
    second = portfolio.create_scoring_template(name="Beta", activate=False)

    def _raise_integrity_error(self):
        raise IntegrityError("UPDATE", {}, Exception("UNIQUE constraint failed"))

    monkeypatch.setattr(SqlAlchemyPortfolioUnitOfWork, "commit", _raise_integrity_error)

    with pytest.raises(ConcurrencyError):
        portfolio.activate_scoring_template(second.id)

    monkeypatch.undo()
    final_active = [t for t in portfolio._scoring_template_repo.list() if t.is_active]
    assert len(final_active) == 1
    assert final_active[0].id == first.id, "the failed activation left the original active template untouched"


def test_explicit_create_with_activate_conflict_maps_integrity_error_to_concurrency_error(
    services, monkeypatch
):
    """`create_scoring_template(activate=True)` can also set is_active=True directly -- the
    same conflict-mapping contract must hold for it, not just for `activate_scoring_template`."""
    from src.core.modules.project_management.infrastructure.persistence.uow.portfolio.portfolio_unit_of_work import (
        SqlAlchemyPortfolioUnitOfWork,
    )

    portfolio = services["portfolio_service"]
    portfolio.create_scoring_template(name="Alpha", activate=True)
    before = sorted(t.id for t in portfolio._scoring_template_repo.list())

    def _raise_integrity_error(self):
        raise IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed"))

    monkeypatch.setattr(SqlAlchemyPortfolioUnitOfWork, "commit", _raise_integrity_error)

    with pytest.raises(ConcurrencyError):
        portfolio.create_scoring_template(name="Gamma", activate=True)

    monkeypatch.undo()
    after = sorted(t.id for t in portfolio._scoring_template_repo.list())
    assert after == before, "the failed create left zero partial state"
    active = [t for t in portfolio._scoring_template_repo.list() if t.is_active]
    assert len(active) == 1
    assert active[0].name == "Alpha"


def test_active_template_uniqueness_is_scoped_per_organization_not_global(services):
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    portfolio = services["portfolio_service"]

    default_org = tenant_context_service.get_active_organization()
    other_org = organization_service.create_organization(
        organization_code="P42FIX2-OPS",
        display_name="P42-FIX2 Ops",
        timezone_name="UTC",
        base_currency="USD",
        is_enabled=False,
    )

    active_default = portfolio.get_active_scoring_template()
    assert active_default.organization_id == default_org.id

    organization_service.enable_organization(other_org.id)
    tenant_context_service.set_active_organization(other_org.id)

    active_other = portfolio.get_active_scoring_template()
    assert active_other.organization_id == other_org.id
    assert active_other.id != active_default.id

    organization_service.enable_organization(default_org.id)
    tenant_context_service.set_active_organization(default_org.id)

    final_default = portfolio.get_active_scoring_template()
    assert final_default.id == active_default.id
    assert final_default.is_active is True


def test_database_rejects_a_second_active_row_via_raw_insert_bypassing_application_code(services):

    from sqlalchemy.exc import IntegrityError as _IntegrityError

    from src.core.modules.project_management.domain.portfolio import PortfolioScoringTemplate
    from src.core.modules.project_management.infrastructure.persistence.mappers.portfolio import (
        portfolio_scoring_template_to_orm,
    )

    portfolio = services["portfolio_service"]
    existing = portfolio.get_active_scoring_template()
    assert existing.is_active is True

    rogue = PortfolioScoringTemplate.create(
        organization_id=existing.organization_id,
        name="Rogue Direct Insert",
        summary="",
        strategic_weight=3,
        value_weight=2,
        urgency_weight=2,
        risk_weight=1,
        is_active=True,
    )
    orm_row = portfolio_scoring_template_to_orm(rogue)

    session = services["session"]
    session.add(orm_row)
    with pytest.raises(_IntegrityError):
        session.commit()
    session.rollback()


def test_legacy_portfolio_signal_still_absent():
    from src.core.shared.events.domain_events import domain_events

    assert not hasattr(domain_events, "portfolio_changed")
