"""Phase 0A.2 tests — Portfolio write rollback hardening
(docs/pm_modernization/CQRS/project_management_cqrs_existing_state_audit.md, §18 Phase 0A.2).

Before this phase, every Portfolio command method committed with no `try/except` at all: a
repository failure or a commit failure left whatever the ORM session happened to be holding, with
no guarantee the shared, long-lived `Session` (§10 of the plan) would still be usable for the next
operation in the same process. This phase wraps each method's mutate+commit step in
`try/except Exception: session.rollback(); raise`, matching the established pattern already used
elsewhere in this module (e.g. `CostService`/`_apply_cost_add_decision`).

These tests exercise the real composition graph (the `services` fixture) so that "the shared
Session remains usable after a failed write" is tested against the actual production session, not
a fake.
"""

from __future__ import annotations

import pytest


class _Boom(RuntimeError):
    """Distinguishable forced-failure marker, so a test can never accidentally pass by
    catching some other, unrelated exception."""


def _boom(*_args, **_kwargs):
    raise _Boom("forced failure for Phase 0A.2 rollback test")


# ---------------------------------------------------------------------------
# Per-method fixtures: each returns (invoke, repo, repo_method_name, count_fn)
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

    return invoke, portfolio._dependency_repo, "add", lambda: len(portfolio._dependency_repo.list())


def _intake_case(services):
    portfolio = services["portfolio_service"]
    counter = {"n": 0}

    def invoke():
        counter["n"] += 1
        return portfolio.create_intake_item(
            title=f"Intake {counter['n']}",
            sponsor_name="Sponsor",
        )

    return invoke, portfolio._intake_repo, "add", lambda: len(portfolio._intake_repo.list())


def _scenario_case(services):
    portfolio = services["portfolio_service"]
    counter = {"n": 0}

    def invoke():
        counter["n"] += 1
        return portfolio.create_scenario(name=f"Scenario {counter['n']}")

    return invoke, portfolio._scenario_repo, "add", lambda: len(portfolio._scenario_repo.list())


def _template_case(services):
    portfolio = services["portfolio_service"]
    # Pre-seed the lazily-created default template so each invoke() below adds exactly one row —
    # _ensure_scoring_templates() (out of this phase's scope) auto-creates "Balanced PMO" as a
    # side effect of the *first* call in a repo with no templates at all.
    portfolio._ensure_scoring_templates()
    counter = {"n": 0}

    def invoke():
        counter["n"] += 1
        return portfolio.create_scoring_template(name=f"Template {counter['n']}")

    return invoke, portfolio._scoring_template_repo, "add", lambda: len(portfolio._scoring_template_repo.list())


_CREATE_CASES = {
    "create_project_dependency": _dependency_case,
    "create_intake_item": _intake_case,
    "create_scenario": _scenario_case,
    "create_scoring_template": _template_case,
}


@pytest.fixture(params=list(_CREATE_CASES))
def create_case(request, services):
    build = _CREATE_CASES[request.param]
    invoke, repo, repo_method, count = build(services)
    return request.param, services, invoke, repo, repo_method, count


# ---------------------------------------------------------------------------
# 1 & 3. A forced repository failure triggers rollback; no partial row survives.
# ---------------------------------------------------------------------------


def test_repository_failure_triggers_rollback_with_no_partial_row(create_case, monkeypatch):
    _name, services, invoke, repo, repo_method, count = create_case
    before = count()
    monkeypatch.setattr(repo, repo_method, _boom)

    with pytest.raises(_Boom):
        invoke()

    assert count() == before


# ---------------------------------------------------------------------------
# 2 & 3. A forced commit failure triggers rollback; no partial row survives.
# ---------------------------------------------------------------------------


def test_commit_failure_triggers_rollback_with_no_partial_row(create_case, monkeypatch):
    _name, services, invoke, repo, repo_method, count = create_case
    before = count()
    monkeypatch.setattr(services["session"], "commit", _boom)

    with pytest.raises(_Boom):
        invoke()

    monkeypatch.undo()
    assert count() == before


# ---------------------------------------------------------------------------
# 4. No portfolio_changed event is emitted after either failure.
# ---------------------------------------------------------------------------


def test_no_portfolio_changed_event_after_repository_failure(create_case, monkeypatch):
    _name, services, invoke, repo, repo_method, _count = create_case
    from src.core.shared.events.domain_events import domain_events

    emitted: list[str] = []
    domain_events.portfolio_changed.connect(emitted.append)
    monkeypatch.setattr(repo, repo_method, _boom)

    with pytest.raises(_Boom):
        invoke()

    assert emitted == []


def test_no_portfolio_changed_event_after_commit_failure(create_case, monkeypatch):
    _name, services, invoke, repo, repo_method, _count = create_case
    from src.core.shared.events.domain_events import domain_events

    emitted: list[str] = []
    domain_events.portfolio_changed.connect(emitted.append)
    monkeypatch.setattr(services["session"], "commit", _boom)

    with pytest.raises(_Boom):
        invoke()

    assert emitted == []


# ---------------------------------------------------------------------------
# 5. The shared Session remains usable after the rollback.
# ---------------------------------------------------------------------------


def test_session_remains_usable_after_repository_failure(create_case, monkeypatch):
    _name, services, invoke, repo, repo_method, count = create_case
    before = count()
    monkeypatch.setattr(repo, repo_method, _boom)
    with pytest.raises(_Boom):
        invoke()
    monkeypatch.undo()

    created = invoke()

    assert created is not None
    assert count() == before + 1


def test_session_remains_usable_after_commit_failure(create_case, monkeypatch):
    _name, services, invoke, repo, repo_method, count = create_case
    before = count()
    monkeypatch.setattr(services["session"], "commit", _boom)
    with pytest.raises(_Boom):
        invoke()
    monkeypatch.undo()

    created = invoke()

    assert created is not None
    assert count() == before + 1


# ---------------------------------------------------------------------------
# 6. Successful behavior and existing DTO output are unchanged for the non-failure path.
# ---------------------------------------------------------------------------


def test_successful_write_is_unaffected_by_the_rollback_wrapper(create_case):
    _name, services, invoke, repo, repo_method, count = create_case
    from src.core.shared.events.domain_events import domain_events

    emitted: list[str] = []
    domain_events.portfolio_changed.connect(emitted.append)
    before = count()

    created = invoke()

    assert created is not None
    assert count() == before + 1
    assert emitted == [created.id]


# ---------------------------------------------------------------------------
# activate_scoring_template / update_intake_item / update_scenario / remove_project_dependency —
# the six named methods above cover every "create" write; these cover the remaining "update"/
# "delete" writes with the same failure-injection shape, using update()/delete() instead of add().
# ---------------------------------------------------------------------------


def test_update_scoring_template_rolls_back_on_repository_failure(services, monkeypatch):
    # _deactivate_other_templates() (called before this phase's new try block, and out of this
    # phase's scope per §18) also calls scoring_template_repo.update — for `first`, the template
    # being deactivated. To exercise this phase's own rollback wrapper specifically (the
    # candidate=second update inside activate_scoring_template's try block) without that earlier,
    # unrelated call tripping the same forced failure, the boom is targeted to `second`'s id only;
    # `first`'s deactivation is left to execute for real, so the assertion below also proves that a
    # failure on the transaction's *second* write correctly rolls back its *first* write too.
    portfolio = services["portfolio_service"]
    first = portfolio.create_scoring_template(name="Rollback Template A", activate=True)
    second = portfolio.create_scoring_template(name="Rollback Template B", activate=False)
    original_update = portfolio._scoring_template_repo.update

    def _boom_for_second(obj, *args, **kwargs):
        if obj.id == second.id:
            raise _Boom("forced failure for Phase 0A.2 rollback test")
        return original_update(obj, *args, **kwargs)

    monkeypatch.setattr(portfolio._scoring_template_repo, "update", _boom_for_second)

    with pytest.raises(_Boom):
        portfolio.activate_scoring_template(second.id)

    monkeypatch.undo()
    reloaded_first = portfolio._scoring_template_repo.get(first.id)
    reloaded_second = portfolio._scoring_template_repo.get(second.id)
    assert reloaded_first.is_active is True
    assert reloaded_second.is_active is False


def test_update_scoring_template_rolls_back_on_commit_failure_and_session_stays_usable(
    services, monkeypatch
):
    portfolio = services["portfolio_service"]
    first = portfolio.create_scoring_template(name="Rollback Template C", activate=True)
    second = portfolio.create_scoring_template(name="Rollback Template D", activate=False)
    monkeypatch.setattr(services["session"], "commit", _boom)

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
    monkeypatch.setattr(portfolio._intake_repo, "update", _boom)

    with pytest.raises(_Boom):
        portfolio.update_intake_item(item.id, title="Changed Title")

    monkeypatch.undo()
    reloaded = portfolio._intake_repo.get(item.id)
    assert reloaded.title == "Rollback Intake"


def test_update_scenario_rolls_back_on_repository_failure(services, monkeypatch):
    portfolio = services["portfolio_service"]
    scenario = portfolio.create_scenario(name="Rollback Scenario")
    monkeypatch.setattr(portfolio._scenario_repo, "update", _boom)

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
    monkeypatch.setattr(portfolio._dependency_repo, "delete", _boom)

    with pytest.raises(_Boom):
        portfolio.remove_project_dependency(dependency.id)

    monkeypatch.undo()
    assert portfolio._dependency_repo.get(dependency.id) is not None
