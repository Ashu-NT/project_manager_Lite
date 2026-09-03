from __future__ import annotations

import pytest

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


# ---------------------------------------------------------------------------
# §14: reading an already-bootstrapped organization is mutation-free, permanently.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# §15: first bootstrap creates exactly one default template, atomically audited, with the
# correct typed event and exactly one ViewInvalidation target after dedupe; a second identical
# read is then mutation-free.
# ---------------------------------------------------------------------------


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

    # The bootstrap UoW commits on its OWN fresh session (a separate connection from the shared
    # `services["session"]`, which already opened a read transaction via the `_scoring_template_
    # repo.list()` check above) -- end that transaction so the next read observes the other
    # session's commit rather than a stale snapshot.
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


# ---------------------------------------------------------------------------
# §16: a failure during the (rare) bootstrap write rolls back the whole transaction -- zero
# partial template set, zero postcommit events, zero ViewInvalidation.
# ---------------------------------------------------------------------------


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


def test_concurrent_first_bootstrap_can_produce_two_active_defaults_recorded_debt(services):
    portfolio = services["portfolio_service"]
    assert portfolio._scoring_template_repo.list() == []

    # Two independent UoWs, each opening its OWN fresh session against the same database --
    # reproduces two concurrent processes/sessions both discovering "no templates exist yet".
    uow_a = portfolio._uow_factory.create(context=portfolio._new_context())
    uow_b = portfolio._uow_factory.create(context=portfolio._new_context())

    events_a: list = []
    events_b: list = []
    portfolio._ensure_scoring_templates(uow=uow_a, events=events_a)
    portfolio._ensure_scoring_templates(uow=uow_b, events=events_b)

    for event in events_a:
        uow_a.record_event(event)
    uow_a.commit()
    for event in events_b:
        uow_b.record_event(event)
    uow_b.commit()

    final = portfolio._scoring_template_repo.list()
    assert len(final) == 2, (
        "characterizes the known, recorded race: no DB constraint prevents a duplicate default "
        "when two sessions bootstrap concurrently -- both created their own default template"
    )
    assert sum(1 for template in final if template.is_active) == 2, (
        "both defaults land is_active=True -- the app-level 'exactly one active' invariant is "
        "only enforced within a single transaction's own view, not across concurrent ones"
    )
    # Activating either duplicate directly is a true no-op (both are ALREADY active -- correct
    # §20 no-op semantics, not a bug), so it does NOT by itself clean up the sibling. The real
    # recovery path is creating (or activating) any OTHER template, which deactivates every
    # currently-active row, including both duplicates at once.
    winner, loser = final[0], final[1]
    no_op = portfolio.activate_scoring_template(winner.id)
    assert no_op.is_active is True
    still_active_sibling = portfolio._scoring_template_repo.get(loser.id)
    assert still_active_sibling.is_active is True, (
        "activating an already-active duplicate is a no-op -- it does not self-heal the race"
    )

    portfolio.create_scoring_template(name="P42-FIX recovery template", activate=True)

    reloaded_winner = portfolio._scoring_template_repo.get(winner.id)
    reloaded_loser = portfolio._scoring_template_repo.get(loser.id)
    assert reloaded_winner.is_active is False
    assert reloaded_loser.is_active is False


def test_legacy_portfolio_signal_still_absent():
    from src.core.shared.events.domain_events import domain_events

    assert not hasattr(domain_events, "portfolio_changed")
