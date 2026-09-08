"""Phase 0A.2 / P42 — Portfolio write rollback hardening.

P42 converged every Portfolio command onto a single, narrow `PortfolioUnitOfWork` (a fresh
session per command, via `PortfolioService._uow_factory`), eliminating the nested/self-owned
commit hazard P40A found (`_ensure_scoring_templates()`'s own internal `session.commit()` calls)
and adding real enterprise audit (previously absent for Intake/Scenario/ScoringTemplate). This
file's ORIGINAL Phase 0A.2 intent -- "a repository or commit failure rolls back the whole write,
leaves zero partial rows, and the service stays usable for the next command" -- is preserved, but
its mechanism is rewritten: failure injection now targets the repository CLASS (so it reaches the
fresh, UoW-owned repository instance each command constructs) or `EnterpriseAuditService.record`
(simulating a failure elsewhere in the SAME transaction, after the mutation itself already
succeeded -- the exact P40A hazard shape), and `domain_events.portfolio_changed` assertions are
replaced with a `ViewInvalidationHint` spy, since the legacy Signal is deleted.
"""

from __future__ import annotations

import pytest

from src.core.modules.project_management.infrastructure.persistence.repositories.portfolio.portfolio import (
    SqlAlchemyPortfolioIntakeRepository,
    SqlAlchemyPortfolioProjectDependencyRepository,
    SqlAlchemyPortfolioScenarioRepository,
    SqlAlchemyPortfolioScoringTemplateRepository,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)


class _Boom(RuntimeError):
    """Distinguishable forced-failure marker, so a test can never accidentally pass by
    catching some other, unrelated exception."""


def _boom(*_args, **_kwargs):
    raise _Boom("forced failure for Phase 0A.2 rollback test")


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
    from src.core.modules.project_management.application.portfolio.event_handlers.view_invalidation import (
        PORTFOLIO_CATEGORY,
    )

    return [h for h in hints if h.category == PORTFOLIO_CATEGORY]


# ---------------------------------------------------------------------------
# Per-method fixtures: each returns (invoke, repo_class, repo_method_name, count_fn)
# invoke() performs one fresh write; count_fn() returns how many rows exist now.
# ---------------------------------------------------------------------------


def _dependency_case(services):
    portfolio = services["portfolio_service"]
    project_service = services["project_service"]
    project_a = project_service.create_project("Dependency Project A")
    project_b = project_service.create_project("Dependency Project B")
    counter = {"n": 0}

    def invoke():
        counter["n"] += 1
        return portfolio.create_project_dependency(
            predecessor_project_id=project_a.id,
            successor_project_id=project_b.id,
            summary=f"link-{counter['n']}",
        )

    return (
        invoke,
        SqlAlchemyPortfolioProjectDependencyRepository,
        "add",
        lambda: len(portfolio._dependency_repo.list()),
    )


def _intake_case(services):
    portfolio = services["portfolio_service"]
    counter = {"n": 0}

    def invoke():
        counter["n"] += 1
        return portfolio.create_intake_item(
            title=f"Intake {counter['n']}",
            sponsor_name="Sponsor",
        )

    return (
        invoke,
        SqlAlchemyPortfolioIntakeRepository,
        "add",
        lambda: len(portfolio._intake_repo.list()),
    )


def _scenario_case(services):
    portfolio = services["portfolio_service"]
    counter = {"n": 0}

    def invoke():
        counter["n"] += 1
        return portfolio.create_scenario(name=f"Scenario {counter['n']}")

    return (
        invoke,
        SqlAlchemyPortfolioScenarioRepository,
        "add",
        lambda: len(portfolio._scenario_repo.list()),
    )


def _template_case(services):
    portfolio = services["portfolio_service"]
    # Pre-seed the lazily-created default template so each invoke() below adds exactly one row --
    # _ensure_scoring_templates() auto-creates "Balanced PMO" as a side effect of the *first* call
    # against a repo with no templates at all. Runs through a real, disposable UoW so the bootstrap
    # itself commits normally (mirrors production: any command touching scoring templates could
    # trigger it).
    with portfolio._require_uow_factory().create(context=portfolio._new_context()) as uow:
        portfolio._ensure_scoring_templates(uow=uow, events=[])
        uow.commit()
    counter = {"n": 0}

    def invoke():
        counter["n"] += 1
        return portfolio.create_scoring_template(name=f"Template {counter['n']}")

    return (
        invoke,
        SqlAlchemyPortfolioScoringTemplateRepository,
        "add",
        lambda: len(portfolio._scoring_template_repo.list()),
    )


_CREATE_CASES = {
    "create_project_dependency": _dependency_case,
    "create_intake_item": _intake_case,
    "create_scenario": _scenario_case,
    "create_scoring_template": _template_case,
}


@pytest.fixture(params=list(_CREATE_CASES))
def create_case(request, services):
    build = _CREATE_CASES[request.param]
    invoke, repo_class, repo_method, count = build(services)
    return request.param, services, invoke, repo_class, repo_method, count


# ---------------------------------------------------------------------------
# 1 & 3. A forced repository failure triggers rollback; no partial row survives.
# ---------------------------------------------------------------------------


def test_repository_failure_triggers_rollback_with_no_partial_row(create_case, monkeypatch):
    _name, services, invoke, repo_class, repo_method, count = create_case
    before = count()
    monkeypatch.setattr(repo_class, repo_method, _boom)

    with pytest.raises(_Boom):
        invoke()

    assert count() == before


# ---------------------------------------------------------------------------
# 2 & 3. A forced failure elsewhere in the SAME transaction (enterprise audit, which now runs
# for every Portfolio sub-aggregate per P42) also triggers rollback -- this is the exact P40A
# hazard shape: the inner mutation itself already succeeded before the failure.
# ---------------------------------------------------------------------------


def test_audit_failure_triggers_rollback_with_no_partial_row(create_case, monkeypatch):
    _name, services, invoke, _repo_class, _repo_method, count = create_case
    before = count()
    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    with pytest.raises(_Boom):
        invoke()

    assert count() == before


# ---------------------------------------------------------------------------
# 4. No portfolio ViewInvalidation hint is published after either failure.
# ---------------------------------------------------------------------------


def test_no_view_invalidation_after_repository_failure(create_case, monkeypatch):
    _name, services, invoke, repo_class, repo_method, _count = create_case
    hints = _spy_hints(services)
    monkeypatch.setattr(repo_class, repo_method, _boom)

    with pytest.raises(_Boom):
        invoke()

    assert _portfolio_hints(hints) == []


def test_no_view_invalidation_after_audit_failure(create_case, monkeypatch):
    _name, services, invoke, _repo_class, _repo_method, _count = create_case
    hints = _spy_hints(services)
    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    with pytest.raises(_Boom):
        invoke()

    assert _portfolio_hints(hints) == []


# ---------------------------------------------------------------------------
# 5. The service remains usable for the next command after a failed write (each command uses its
# own fresh, disposable UoW session -- P42 -- so this is naturally true, but proved end to end).
# ---------------------------------------------------------------------------


def test_service_remains_usable_after_repository_failure(create_case, monkeypatch):
    _name, services, invoke, repo_class, repo_method, count = create_case
    before = count()
    monkeypatch.setattr(repo_class, repo_method, _boom)
    with pytest.raises(_Boom):
        invoke()
    monkeypatch.undo()

    created = invoke()

    assert created is not None
    assert count() == before + 1


def test_service_remains_usable_after_audit_failure(create_case, monkeypatch):
    _name, services, invoke, _repo_class, _repo_method, count = create_case
    before = count()
    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)
    with pytest.raises(_Boom):
        invoke()
    monkeypatch.undo()

    created = invoke()

    assert created is not None
    assert count() == before + 1


# ---------------------------------------------------------------------------
# 6. Successful behavior is unaffected: exactly one ViewInvalidation hint, non-failure path.
# ---------------------------------------------------------------------------


def test_successful_write_produces_exactly_one_portfolio_view_invalidation(create_case):
    _name, services, invoke, _repo_class, _repo_method, count = create_case
    hints = _spy_hints(services)
    before = count()

    created = invoke()

    assert created is not None
    assert count() == before + 1
    assert len(_portfolio_hints(hints)) == 1


# ---------------------------------------------------------------------------
# activate_scoring_template / update_intake_item / update_scenario / remove_project_dependency --
# the four "create" cases above cover every "create" write; these cover the remaining "update"/
# "delete" writes with the same failure-injection shape.
# ---------------------------------------------------------------------------


def test_activate_scoring_template_rolls_back_both_writes_on_repository_failure(services, monkeypatch):
    """`activate_scoring_template` mutates TWO rows in the same transaction (the newly-activated
    template and the previously-active one, via `_deactivate_other_templates`) -- P42's UoW makes
    both genuinely atomic. Forcing the SECOND write (the target) to fail must roll back the FIRST
    (the deactivation) too -- proving real cross-sub-aggregate-row atomicity, not two independent
    commits that merely happen to run in sequence."""
    portfolio = services["portfolio_service"]
    first = portfolio.create_scoring_template(name="Rollback Template A", activate=True)
    second = portfolio.create_scoring_template(name="Rollback Template B", activate=False)
    original_update = SqlAlchemyPortfolioScoringTemplateRepository.update

    def _boom_for_second(self, obj, *args, **kwargs):
        if obj.id == second.id:
            raise _Boom("forced failure for Phase 0A.2 rollback test")
        return original_update(self, obj, *args, **kwargs)

    monkeypatch.setattr(SqlAlchemyPortfolioScoringTemplateRepository, "update", _boom_for_second)

    with pytest.raises(_Boom):
        portfolio.activate_scoring_template(second.id)

    monkeypatch.undo()
    reloaded_first = portfolio._scoring_template_repo.get(first.id)
    reloaded_second = portfolio._scoring_template_repo.get(second.id)
    assert reloaded_first.is_active is True
    assert reloaded_second.is_active is False


def test_activate_scoring_template_rolls_back_on_audit_failure(services, monkeypatch):
    portfolio = services["portfolio_service"]
    first = portfolio.create_scoring_template(name="Rollback Template C", activate=True)
    second = portfolio.create_scoring_template(name="Rollback Template D", activate=False)
    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    with pytest.raises(_Boom):
        portfolio.activate_scoring_template(second.id)

    monkeypatch.undo()
    reloaded_first = portfolio._scoring_template_repo.get(first.id)
    assert reloaded_first.is_active is True

    activated = portfolio.activate_scoring_template(second.id)
    assert activated.is_active is True


def test_update_intake_item_rolls_back_on_repository_failure(services, monkeypatch):
    portfolio = services["portfolio_service"]
    item = portfolio.create_intake_item(title="Rollback Intake", sponsor_name="Sponsor")
    monkeypatch.setattr(SqlAlchemyPortfolioIntakeRepository, "update", _boom)

    with pytest.raises(_Boom):
        portfolio.update_intake_item(item.id, title="Changed Title")

    monkeypatch.undo()
    reloaded = portfolio._intake_repo.get(item.id)
    assert reloaded.title == "Rollback Intake"


def test_update_scenario_rolls_back_on_repository_failure(services, monkeypatch):
    portfolio = services["portfolio_service"]
    scenario = portfolio.create_scenario(name="Rollback Scenario")
    monkeypatch.setattr(SqlAlchemyPortfolioScenarioRepository, "update", _boom)

    with pytest.raises(_Boom):
        portfolio.update_scenario(scenario.id, name="Changed Name")

    monkeypatch.undo()
    reloaded = portfolio._scenario_repo.get(scenario.id)
    assert reloaded.name == "Rollback Scenario"


def test_remove_project_dependency_rolls_back_on_repository_failure(services, monkeypatch):
    portfolio = services["portfolio_service"]
    project_service = services["project_service"]
    project_a = project_service.create_project("Remove Dependency Project A")
    project_b = project_service.create_project("Remove Dependency Project B")
    dependency = portfolio.create_project_dependency(
        predecessor_project_id=project_a.id,
        successor_project_id=project_b.id,
    )
    monkeypatch.setattr(SqlAlchemyPortfolioProjectDependencyRepository, "delete", _boom)

    with pytest.raises(_Boom):
        portfolio.remove_project_dependency(dependency.id)

    monkeypatch.undo()
    assert portfolio._dependency_repo.get(dependency.id) is not None
