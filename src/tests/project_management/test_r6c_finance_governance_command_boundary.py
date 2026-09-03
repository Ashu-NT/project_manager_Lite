from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.application.financials.governance import (
    FinanceGovernanceCommandBoundary,
)


class _FakeUow:
    def __init__(self, *, fail_commit: bool = False) -> None:
        self._session = object()
        self.fail_commit = fail_commit
        self.commit_count = 0
        self.rollback_count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None or self.commit_count == 0:
            self.rollback_count += 1

    def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("commit unavailable")
        self.commit_count += 1


class _FakeFactory:
    def __init__(self) -> None:
        self.created: list[_FakeUow] = []
        self.fail_next_commit = False

    def create(self, *, context):
        del context
        uow = _FakeUow(fail_commit=self.fail_next_commit)
        self.fail_next_commit = False
        self.created.append(uow)
        return uow


def _boundary(
    factory: _FakeFactory, *, post_commit_action=None
) -> FinanceGovernanceCommandBoundary:
    def operations(uow):
        actions: list = []
        if post_commit_action is not None:
            actions.append(post_commit_action)
        service = SimpleNamespace(
            create=lambda project_id: SimpleNamespace(project_id=project_id)
        )
        return SimpleNamespace(
            budgets=service,
            forecast_versions=service,
            forecast_generation=service,
            financial_changes=service,
            financial_setup=service,
            post_commit_actions=actions,
            session=uow._session,
        )

    return FinanceGovernanceCommandBoundary(
        uow_factory=factory,
        operations_factory=operations,
    )


def test_each_command_uses_a_fresh_uow_and_commits_exactly_once() -> None:
    factory = _FakeFactory()
    boundary = _boundary(factory)

    boundary.budget(lambda service: service.create("project-a"))
    boundary.budget(lambda service: service.create("project-b"))

    assert len(factory.created) == 2
    assert factory.created[0]._session is not factory.created[1]._session
    assert [uow.commit_count for uow in factory.created] == [1, 1]


def test_commit_failure_rolls_back_and_runs_no_post_commit_actions() -> None:
    """P38B: `budget()` no longer has any post-commit invalidation callback of its own (typed
    Budget events are recorded pre-commit via `uow.record_event`, inside the same UoW that
    `commit()` failed to complete) -- `post_commit_actions` (the boundary's one remaining
    post-commit mechanism, used by other families such as `financial_change`) is what this proves
    must not run on a failed commit."""
    factory = _FakeFactory()
    factory.fail_next_commit = True
    calls: list[str] = []
    boundary = _boundary(factory, post_commit_action=lambda: calls.append("ran"))

    with pytest.raises(RuntimeError, match="commit unavailable"):
        boundary.budget(lambda service: service.create("project-a"))

    assert calls == []
    assert factory.created[0].rollback_count == 1


def test_post_commit_action_failure_does_not_undo_commit() -> None:
    def _failing_action():
        raise RuntimeError("post commit action unavailable")

    factory = _FakeFactory()
    boundary = _boundary(factory, post_commit_action=_failing_action)

    result = boundary.budget(lambda service: service.create("project-a"))

    assert result.project_id == "project-a"
    assert factory.created[0].commit_count == 1
    assert factory.created[0].rollback_count == 0


def test_r6c_services_and_approval_participants_do_not_own_commit_or_rollback() -> None:
    root = Path("src/core/modules/project_management")
    files = (
        root / "application/financials/budgets/budget_service.py",
        root / "application/financials/forecasts/version_service.py",
        root / "application/financials/forecasts/generation_service.py",
        root / "application/financials/financial_changes/service.py",
        root / "application/financials/configuration_service.py",
        root / "infrastructure/approval/budget_apply_participant.py",
        root / "infrastructure/approval/financial_change_apply_participant.py",
    )
    forbidden: list[str] = []
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in {"commit", "rollback"}:
                    forbidden.append(f"{path}:{node.lineno}:{node.func.attr}")

    assert forbidden == []


def test_production_composition_exposes_governed_ports(services) -> None:
    boundary = services["finance_governance_commands"]
    assert isinstance(boundary, FinanceGovernanceCommandBoundary)
    assert boundary._uow_factory is not None
    for key in (
        "budget_service",
        "forecast_version_service",
        "forecast_generation_service",
        "financial_change_service",
        "financial_configuration_service",
    ):
        assert services[key]._boundary is boundary

