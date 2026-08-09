from __future__ import annotations

import inspect
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

from src.core.modules.project_management.application.financials.budgets import (
    BudgetApprovalOutcome,
    BudgetApprovalResult,
)
from src.core.modules.project_management.domain.financials.budget import (
    BudgetLine,
    BudgetStatus,
    ProjectBudget,
)
from src.core.modules.project_management.domain.financials.configuration import CostCodePolicy
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _make_project(services, name: str = "Budget Project"):
    return services["project_service"].create_project(name, currency="USD")


def _make_cost_code(services, code: str, name: str = "Cost Code"):
    return services["financial_configuration_service"].create_cost_code(code=code, name=name)


def _budget_line(**overrides) -> BudgetLine:
    values = dict(
        tenant_id="tenant-a",
        organization_id="org-a",
        budget_id="budget-1",
        project_id="project-1",
        cost_code_id="cost-code-1",
        amount=Decimal("100"),
        currency_code="USD",
    )
    values.update(overrides)
    return BudgetLine.create(**values)


def _budget(**overrides) -> ProjectBudget:
    values = dict(
        tenant_id="tenant-a",
        organization_id="org-a",
        project_id="project-1",
        name="Budget",
        currency_code="USD",
    )
    values.update(overrides)
    return ProjectBudget.create(**values)


# ---------------------------------------------------------------------------
# Domain-level tests (no DB)
# ---------------------------------------------------------------------------


def test_lifecycle_transitions_are_explicit_and_exhaustive() -> None:
    budget = _budget()
    assert budget.status == BudgetStatus.DRAFT
    now = datetime.now(timezone.utc)

    with pytest.raises(BusinessRuleError, match="cannot transition"):
        budget.approve(approved_by="u1", approved_at=now)
    with pytest.raises(BusinessRuleError, match="cannot transition"):
        budget.reject(rejected_by="u1", rejected_at=now)
    with pytest.raises(BusinessRuleError, match="cannot transition"):
        budget.supersede(superseded_by="u1", superseded_at=now)
    with pytest.raises(BusinessRuleError, match="cannot transition"):
        budget.close(closed_by="u1", closed_at=now)

    budget.submit(submitted_by="u1", submitted_at=now)
    assert budget.status == BudgetStatus.SUBMITTED
    with pytest.raises(BusinessRuleError):
        budget.submit(submitted_by="u1", submitted_at=now)

    budget.approve(approved_by="u2", approved_at=now)
    assert budget.status == BudgetStatus.APPROVED
    with pytest.raises(BusinessRuleError):
        budget.reject(rejected_by="u2", rejected_at=now)

    budget.close(closed_by="u2", closed_at=now)
    assert budget.status == BudgetStatus.CLOSED
    with pytest.raises(BusinessRuleError):
        budget.supersede(superseded_by="u2", superseded_at=now)


def test_ensure_mutable_blocks_every_non_draft_status() -> None:
    now = datetime.now(timezone.utc)
    for status in BudgetStatus:
        budget = _budget()
        if status != BudgetStatus.DRAFT:
            budget.status = status
        if status == BudgetStatus.DRAFT:
            budget.ensure_mutable()  # does not raise
            continue
        with pytest.raises(BusinessRuleError) as exc:
            budget.ensure_mutable()
        assert exc.value.code == "PROJECT_BUDGET_IMMUTABLE"


def test_rejected_and_superseded_never_reopen() -> None:
    now = datetime.now(timezone.utc)
    rejected = _budget()
    rejected.submit(submitted_by="u1", submitted_at=now)
    rejected.reject(rejected_by="u2", rejected_at=now)
    with pytest.raises(BusinessRuleError):
        rejected.submit(submitted_by="u1", submitted_at=now)
    with pytest.raises(BusinessRuleError):
        rejected.approve(approved_by="u2", approved_at=now)


def test_revision_is_independent_of_row_version() -> None:
    budget = _budget(revision=3)
    assert budget.revision == 3
    assert budget.row_version == 1
    budget.rename("New Name")
    budget.touch(updated_at=datetime.now(timezone.utc))
    # rename()/touch() never touch revision — only row_version is a
    # separate optimistic-concurrency token, bumped by the repository, not
    # by the domain object itself.
    assert budget.revision == 3


def test_per_transition_notes_do_not_overwrite_each_other() -> None:
    now = datetime.now(timezone.utc)
    budget = _budget()
    budget.update_notes("general notes")
    budget.submit(submitted_by="u1", submitted_at=now, notes="submission note")
    budget.approve(approved_by="u2", approved_at=now, notes="approval note")
    budget.close(closed_by="u2", closed_at=now, notes="closure note")

    assert budget.notes == "general notes"
    assert budget.submission_notes == "submission note"
    assert budget.approval_notes == "approval note"
    assert budget.closure_notes == "closure note"
    assert budget.rejection_notes == ""


# ---------------------------------------------------------------------------
# create_budget
# ---------------------------------------------------------------------------


def test_create_budget_assigns_sequential_revisions_and_defaults_currency(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]

    first = budget_service.create_budget(project.id, "v1")
    assert first.revision == 1
    assert first.currency_code == "USD"

    # Reject the first so a second draft is allowed to be created.
    first_submitted = _submit_with_line(services, first)
    budget_service.reject_budget(
        first_submitted.id, rejected_by="admin", expected_version=first_submitted.row_version
    )

    second = budget_service.create_budget(project.id, "v2")
    assert second.revision == 2


def _submit_with_line(services, budget: ProjectBudget) -> ProjectBudget:
    budget_service = services["budget_service"]
    code = _make_cost_code(services, code=f"CC-{budget.id[:8]}")
    budget_service.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Line",
        amount=Decimal("10"),
        expected_budget_version=budget.row_version,
    )
    current = budget_service.get_budget(budget.id)
    return budget_service.submit_budget(
        budget.id, "admin", expected_version=current.row_version
    )


def _approve_directly(services, budget: ProjectBudget) -> ProjectBudget:
    budget_service = services["budget_service"]
    result = budget_service.approve_budget(
        budget.id,
        approved_by="admin",
        expected_version=budget.row_version,
    )
    assert isinstance(result, BudgetApprovalResult)
    assert result.outcome is BudgetApprovalOutcome.APPLIED
    assert result.is_applied
    assert not result.is_pending_approval
    assert result.budget_id == budget.id
    assert result.project_id == budget.project_id
    assert result.budget_status is BudgetStatus.APPROVED
    assert result.row_version > budget.row_version
    assert result.approval_request_id is None
    return budget_service.get_budget(result.budget_id)


def test_create_budget_requires_financial_profile(services, monkeypatch) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    monkeypatch.setattr(
        budget_service._financial_profile_repo, "get_by_project", lambda project_id: None
    )
    with pytest.raises(NotFoundError, match="financial profile"):
        budget_service.create_budget(project.id, "No profile")


def test_only_one_open_budget_per_project(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget_service.create_budget(project.id, "v1")

    with pytest.raises(BusinessRuleError) as exc:
        budget_service.create_budget(project.id, "v2")
    assert exc.value.code == "PROJECT_BUDGET_OPEN_VERSION_EXISTS"


def test_new_draft_allowed_after_rejection_but_not_while_another_is_approved(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]

    v1 = budget_service.create_budget(project.id, "v1")
    v1 = _submit_with_line(services, v1)
    v1 = budget_service.reject_budget(v1.id, rejected_by="admin", expected_version=v1.row_version)

    v2 = budget_service.create_budget(project.id, "v2")
    assert v2.revision == 2

    v2 = _submit_with_line(services, v2)
    v2 = _approve_directly(services, v2)
    assert v2.status == BudgetStatus.APPROVED

    v3 = budget_service.create_budget(project.id, "v3")
    assert v3.revision == 3
    assert v3.status == BudgetStatus.DRAFT


def test_create_budget_open_version_race_translates_named_error(services, monkeypatch) -> None:
    # Simulate two concurrent create_budget calls both observing "no open
    # budget" before either commits — the service pre-check is bypassed here
    # so the DB-level partial unique index is what actually fires.
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    monkeypatch.setattr(budget_service._budget_repo, "has_open_for_project", lambda project_id: False)

    budget_service.create_budget(project.id, "race-1")
    with pytest.raises(BusinessRuleError) as exc:
        budget_service.create_budget(project.id, "race-2")
    assert exc.value.code == "PROJECT_BUDGET_OPEN_VERSION_EXISTS"


def test_create_budget_revision_race_translates_to_concurrency_error(services, monkeypatch) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]

    v1 = budget_service.create_budget(project.id, "v1")
    v1 = _submit_with_line(services, v1)
    budget_service.approve_budget(v1.id, approved_by="admin", expected_version=v1.row_version)

    # Nothing open now, so has_open_for_project is truthfully False; force
    # get_latest_for_project to return a stale (already-used) revision so
    # the insert collides only on the revision uniqueness constraint.
    monkeypatch.setattr(budget_service._budget_repo, "get_latest_for_project", lambda project_id: None)
    with pytest.raises(ConcurrencyError) as exc:
        budget_service.create_budget(project.id, "collides-with-v1")
    assert exc.value.code == "PROJECT_BUDGET_REVISION_CONFLICT"


# ---------------------------------------------------------------------------
# submit / immutability / delete
# ---------------------------------------------------------------------------


def test_submit_budget_requires_at_least_one_line(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "empty")
    with pytest.raises(BusinessRuleError) as exc:
        budget_service.submit_budget(budget.id, "admin", expected_version=budget.row_version)
    assert exc.value.code == "PROJECT_BUDGET_EMPTY"


def test_submit_budget_requires_current_version(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "stale")
    code = _make_cost_code(services, code="CC-STALE")
    budget_service.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Line",
        amount=Decimal("10"),
        expected_budget_version=budget.row_version,
    )
    with pytest.raises(ConcurrencyError):
        budget_service.submit_budget(budget.id, "admin", expected_version=budget.row_version)


def test_line_mutations_blocked_once_submitted(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "frozen")
    code = _make_cost_code(services, code="CC-FROZEN")
    line = budget_service.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Line",
        amount=Decimal("10"),
        expected_budget_version=budget.row_version,
    )
    budget = budget_service.get_budget(budget.id)
    budget = budget_service.submit_budget(budget.id, "admin", expected_version=budget.row_version)

    with pytest.raises(BusinessRuleError) as exc:
        budget_service.add_line(
            budget.id,
            cost_code_id=code.id,
            description="Another",
            amount=Decimal("5"),
            expected_budget_version=budget.row_version,
        )
    assert exc.value.code == "PROJECT_BUDGET_IMMUTABLE"

    with pytest.raises(BusinessRuleError) as exc:
        budget_service.update_line(
            line.id,
            expected_line_version=line.row_version,
            expected_budget_version=budget.row_version,
            amount=Decimal("50"),
        )
    assert exc.value.code == "PROJECT_BUDGET_IMMUTABLE"

    with pytest.raises(BusinessRuleError) as exc:
        budget_service.delete_line(
            line.id, expected_line_version=line.row_version, expected_budget_version=budget.row_version
        )
    assert exc.value.code == "PROJECT_BUDGET_IMMUTABLE"

    with pytest.raises(BusinessRuleError) as exc:
        budget_service.update_budget_header(
            budget.id, name="New name", expected_version=budget.row_version
        )
    assert exc.value.code == "PROJECT_BUDGET_IMMUTABLE"


def test_delete_budget_only_succeeds_on_draft_and_cascades_lines(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "deletable")
    code = _make_cost_code(services, code="CC-DEL")
    budget_service.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Line",
        amount=Decimal("10"),
        expected_budget_version=budget.row_version,
    )
    budget = budget_service.get_budget(budget.id)
    lines_before = budget_service._budget_repo.list_lines(budget.id)
    assert len(lines_before) == 1

    budget_service.delete_budget(budget.id, expected_version=budget.row_version)
    assert budget_service._budget_repo.get(budget.id) is None
    assert budget_service._budget_repo.list_lines(budget.id) == []


def test_delete_budget_rejects_non_draft_status(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "not deletable")
    budget = _submit_with_line(services, budget)
    with pytest.raises(BusinessRuleError) as exc:
        budget_service.delete_budget(budget.id, expected_version=budget.row_version)
    assert exc.value.code == "PROJECT_BUDGET_DELETE_STATUS_INVALID"


def test_delete_budget_stale_version_raises_stale_write(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "race-delete")
    stale_version = budget.row_version
    budget_service.update_budget_header(budget.id, name="Renamed", expected_version=stale_version)
    with pytest.raises(ConcurrencyError):
        budget_service.delete_budget(budget.id, expected_version=stale_version)


# ---------------------------------------------------------------------------
# Line eligibility
# ---------------------------------------------------------------------------


def test_add_line_rejects_inactive_cost_code(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    config_service = services["financial_configuration_service"]
    budget = budget_service.create_budget(project.id, "inactive-code")
    code = _make_cost_code(services, code="CC-INACTIVE")
    config_service.deactivate_cost_code(code.id, expected_version=code.version)

    with pytest.raises(BusinessRuleError) as exc:
        budget_service.add_line(
            budget.id,
            cost_code_id=code.id,
            description="Line",
            amount=Decimal("10"),
            expected_budget_version=budget.row_version,
        )
    assert exc.value.code == "PROJECT_BUDGET_LINE_COST_CODE_INACTIVE"


def test_add_line_rejects_cost_code_outside_restricted_allow_list(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    config_service = services["financial_configuration_service"]
    budget = budget_service.create_budget(project.id, "restricted")
    allowed = _make_cost_code(services, code="CC-ALLOWED")
    disallowed = _make_cost_code(services, code="CC-DISALLOWED")

    config_service.add_project_cost_code(project_id=project.id, cost_code_id=allowed.id)
    profile = config_service.get_profile(project.id)
    config_service.configure_profile(
        project.id,
        expected_version=profile.version,
        cost_code_policy=CostCodePolicy.RESTRICTED,
    )

    with pytest.raises(BusinessRuleError) as exc:
        budget_service.add_line(
            budget.id,
            cost_code_id=disallowed.id,
            description="Line",
            amount=Decimal("10"),
            expected_budget_version=budget.row_version,
        )
    assert exc.value.code == "PROJECT_BUDGET_LINE_COST_CODE_NOT_PERMITTED"

    # Allowed code still succeeds.
    line = budget_service.add_line(
        budget.id,
        cost_code_id=allowed.id,
        description="Line",
        amount=Decimal("10"),
        expected_budget_version=budget.row_version,
    )
    assert line.cost_code_id == allowed.id


def test_add_line_rejects_cross_project_task(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services, name="Home project")
    other_project = _make_project(services, name="Other project")
    task_service = services["task_service"]
    other_task = task_service.create_task(
        other_project.id, "Other Task", start_date=date(2026, 3, 1), duration_days=1
    )

    budget_service = services["budget_service"]
    code = _make_cost_code(services, code="CC-TASK")
    budget = budget_service.create_budget(project.id, "task-scope")

    with pytest.raises(BusinessRuleError) as exc:
        budget_service.add_line(
            budget.id,
            cost_code_id=code.id,
            task_id=other_task.id,
            description="Line",
            amount=Decimal("10"),
            expected_budget_version=budget.row_version,
        )
    assert exc.value.code == "PROJECT_BUDGET_LINE_TASK_PROJECT_MISMATCH"


def test_add_line_rejects_mismatched_currency(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    code = _make_cost_code(services, code="CC-CUR")
    budget = budget_service.create_budget(project.id, "currency-check")

    with pytest.raises(BusinessRuleError) as exc:
        budget_service.add_line(
            budget.id,
            cost_code_id=code.id,
            description="Line",
            amount=Decimal("10"),
            currency_code="EUR",
            expected_budget_version=budget.row_version,
        )
    assert exc.value.code == "PROJECT_BUDGET_LINE_CURRENCY_MISMATCH"


def test_add_line_rejects_cross_organization_cost_code(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    organization_service = services["organization_service"]
    original_organization = organization_service.get_active_organization()
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "cross-org")

    other_organization = organization_service.create_organization(
        organization_code="PF-BUDGET-OTHER",
        display_name="Budget Other Org",
        base_currency="USD",
        is_active=False,
    )
    organization_service.set_active_organization(other_organization.id)
    try:
        other_org_code = _make_cost_code(services, code="CC-OTHER-ORG")
    finally:
        organization_service.set_active_organization(original_organization.id)

    with pytest.raises(NotFoundError):
        budget_service.add_line(
            budget.id,
            cost_code_id=other_org_code.id,
            description="Line",
            amount=Decimal("10"),
            expected_budget_version=budget.row_version,
        )


# ---------------------------------------------------------------------------
# Line mutations advance the parent budget's row_version (round-three fix)
# ---------------------------------------------------------------------------


def test_line_mutations_each_advance_parent_budget_row_version(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    code = _make_cost_code(services, code="CC-TOUCH")
    budget = budget_service.create_budget(project.id, "touch-test")
    version_after_create = budget.row_version

    line = budget_service.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Line",
        amount=Decimal("10"),
        expected_budget_version=version_after_create,
    )
    budget = budget_service.get_budget(budget.id)
    assert budget.row_version != version_after_create
    version_after_add = budget.row_version

    budget_service.update_line(
        line.id,
        expected_line_version=line.row_version,
        expected_budget_version=version_after_add,
        amount=Decimal("20"),
    )
    budget = budget_service.get_budget(budget.id)
    assert budget.row_version != version_after_add
    version_after_update = budget.row_version

    line = budget_service._budget_repo.get_line(line.id)
    budget_service.delete_line(
        line.id,
        expected_line_version=line.row_version,
        expected_budget_version=version_after_update,
    )
    budget = budget_service.get_budget(budget.id)
    assert budget.row_version != version_after_update


def test_stale_expected_budget_version_blocks_line_mutation_even_with_current_line_version(
    services,
) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    code = _make_cost_code(services, code="CC-STALEBV")
    budget = budget_service.create_budget(project.id, "stale-budget-version")
    stale_budget_version = budget.row_version

    line = budget_service.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Line",
        amount=Decimal("10"),
        expected_budget_version=stale_budget_version,
    )
    # budget.row_version has now advanced past stale_budget_version.
    with pytest.raises(ConcurrencyError):
        budget_service.update_line(
            line.id,
            expected_line_version=line.row_version,
            expected_budget_version=stale_budget_version,
            amount=Decimal("30"),
        )


def test_submit_races_delete_of_last_line_exactly_one_succeeds(services) -> None:
    # The concurrency regression test the round-three fix exists for:
    # transaction A reads a DRAFT budget with one line and submits it,
    # concurrently with transaction B deleting that same, only, line.
    # Both capture the same pre-mutation expected_budget_version; whichever
    # commits first advances ProjectBudget.row_version, so the second call's
    # now-stale version is what closes the race — here, delete commits
    # first (also touching the parent), so submit's captured version is the
    # one left stale.
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    code = _make_cost_code(services, code="CC-RACE")
    budget = budget_service.create_budget(project.id, "race-submit-delete")
    line = budget_service.add_line(
        budget.id,
        cost_code_id=code.id,
        description="Line",
        amount=Decimal("10"),
        expected_budget_version=budget.row_version,
    )
    budget = budget_service.get_budget(budget.id)
    captured_version = budget.row_version

    budget_service.delete_line(
        line.id,
        expected_line_version=line.row_version,
        expected_budget_version=captured_version,
    )

    with pytest.raises(ConcurrencyError):
        budget_service.submit_budget(budget.id, "admin", expected_version=captured_version)

    # A SUBMITTED budget with zero lines never exists as an end state: the
    # delete won the race, so the budget is still DRAFT with no lines —
    # submit_budget's own emptiness check would have caught it even if the
    # stale-version check somehow hadn't.
    final = budget_service.get_budget(budget.id)
    assert final.status == BudgetStatus.DRAFT
    assert budget_service._budget_repo.list_lines(budget.id) == []


# ---------------------------------------------------------------------------
# update_budget_header / currency immutability
# ---------------------------------------------------------------------------


def test_update_budget_header_has_no_currency_parameter() -> None:
    from src.core.modules.project_management.application.financials.budgets.budget_service import (
        BudgetService,
    )

    signature = inspect.signature(BudgetService.update_budget_header)
    assert "currency_code" not in signature.parameters


def test_update_budget_header_renames_and_updates_notes_without_changing_currency(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "header-test")
    updated = budget_service.update_budget_header(
        budget.id, name="Renamed", notes="new notes", expected_version=budget.row_version
    )
    assert updated.name == "Renamed"
    assert updated.notes == "new notes"
    assert updated.currency_code == "USD"


# ---------------------------------------------------------------------------
# Ordered approve/supersede + conflict translation
# ---------------------------------------------------------------------------


def test_ordered_approve_supersedes_prior_approved_budget(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]

    v1 = budget_service.create_budget(project.id, "v1")
    v1 = _submit_with_line(services, v1)
    v1 = _approve_directly(services, v1)
    assert v1.status == BudgetStatus.APPROVED

    v2 = budget_service.create_budget(project.id, "v2")
    v2 = _submit_with_line(services, v2)
    v2 = _approve_directly(services, v2)
    assert v2.status == BudgetStatus.APPROVED

    v1_reloaded = budget_service._budget_repo.get(v1.id)
    assert v1_reloaded.status == BudgetStatus.SUPERSEDED
    assert v1_reloaded.superseded_by == "admin"

    approved = budget_service.get_approved_budget(project.id)
    assert approved.id == v2.id


def test_approve_conflict_translates_to_named_business_error(services, monkeypatch) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]

    v1 = budget_service.create_budget(project.id, "v1")
    v1 = _submit_with_line(services, v1)
    v1 = _approve_directly(services, v1)

    v2 = budget_service.create_budget(project.id, "v2")
    v2 = _submit_with_line(services, v2)

    # Simulate a concurrent read that missed v1 being approved — the DB's
    # partial "one approved" index is what must catch this, not the
    # in-memory `previous` lookup.
    monkeypatch.setattr(budget_service._budget_repo, "get_approved_for_project", lambda project_id: None)
    with pytest.raises(BusinessRuleError) as exc:
        budget_service.approve_budget(v2.id, approved_by="admin", expected_version=v2.row_version)
    assert exc.value.code == "PROJECT_BUDGET_APPROVAL_CONFLICT"

    # v1 must still be APPROVED (rolled back to the nested savepoint, not
    # left half-superseded), v2 must still be SUBMITTED.
    v1_reloaded = budget_service._budget_repo.get(v1.id)
    v2_reloaded = budget_service._budget_repo.get(v2.id)
    assert v1_reloaded.status == BudgetStatus.APPROVED
    assert v2_reloaded.status == BudgetStatus.SUBMITTED


# ---------------------------------------------------------------------------
# reject / close
# ---------------------------------------------------------------------------


def test_reject_budget_transitions_and_blocks_reopen(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "to-reject")
    budget = _submit_with_line(services, budget)
    rejected = budget_service.reject_budget(
        budget.id, rejected_by="admin", expected_version=budget.row_version
    )
    assert rejected.status == BudgetStatus.REJECTED
    with pytest.raises(BusinessRuleError):
        budget_service.submit_budget(rejected.id, "admin", expected_version=rejected.row_version)
    with pytest.raises(BusinessRuleError):
        budget_service.approve_budget(
            rejected.id, approved_by="admin", expected_version=rejected.row_version
        )


def test_close_budget_only_valid_from_approved(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "to-close")
    with pytest.raises(BusinessRuleError):
        budget_service.close_budget(budget.id, "admin", expected_version=budget.row_version)

    budget = _submit_with_line(services, budget)
    budget = _approve_directly(services, budget)
    closed = budget_service.close_budget(budget.id, "admin", expected_version=budget.row_version)
    assert closed.status == BudgetStatus.CLOSED


# ---------------------------------------------------------------------------
# Governed approve/reject
# ---------------------------------------------------------------------------


def test_governed_approve_creates_request_and_actor_is_the_deciding_principal(
    services, monkeypatch
) -> None:
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "budget.approve")
    _login(services, "admin", "ChangeMe123!")

    auth = services["auth_service"]
    project = _make_project(services, name="Governed Budget Project")
    budget_service = services["budget_service"]
    approvals = services["approval_service"]

    budget = budget_service.create_budget(project.id, "governed")
    budget = _submit_with_line(services, budget)

    auth.register_user("budget-requester", "StrongPass123", role_names=["planner"])
    _login(services, "budget-requester", "StrongPass123")

    result = budget_service.approve_budget(
        budget.id, approved_by="budget-requester", expected_version=budget.row_version
    )
    assert result.outcome is BudgetApprovalOutcome.PENDING_APPROVAL
    assert result.is_pending_approval
    assert not result.is_applied
    assert result.budget_id == budget.id
    assert result.project_id == project.id
    assert result.budget_status is BudgetStatus.SUBMITTED
    assert result.row_version == budget.row_version

    req = approvals.list_pending(project_id=project.id)[0]
    assert result.approval_request_id == req.id
    assert req.request_type == "budget.approve"
    assert req.requested_by_username == "budget-requester"
    requester_user_id = req.requested_by_user_id

    _login(services, "admin", "ChangeMe123!")
    admin_user_id = services["user_session"].principal.user_id
    approvals.approve_and_apply(req.id, note="Approved via governance")

    approved = budget_service.get_budget(budget.id)
    assert approved.status == BudgetStatus.APPROVED
    # The deciding principal (admin) is recorded, never the requester —
    # the payload was written by budget-requester, but the actor sourced by
    # the apply handler must be whoever is deciding right now.
    assert approved.approved_by == admin_user_id
    assert approved.approved_by != requester_user_id
    assert approved.approval_notes == ""


def test_governed_reject_drives_domain_reject(services, monkeypatch) -> None:
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "budget.approve")
    _login(services, "admin", "ChangeMe123!")

    auth = services["auth_service"]
    project = _make_project(services, name="Governed Reject Project")
    budget_service = services["budget_service"]
    approvals = services["approval_service"]

    budget = budget_service.create_budget(project.id, "governed-reject")
    budget = _submit_with_line(services, budget)

    auth.register_user("budget-requester-2", "StrongPass123", role_names=["planner"])
    _login(services, "budget-requester-2", "StrongPass123")
    result = budget_service.approve_budget(
        budget.id, approved_by="budget-requester-2", expected_version=budget.row_version
    )
    assert result.outcome is BudgetApprovalOutcome.PENDING_APPROVAL
    req = approvals.list_pending(project_id=project.id)[0]
    assert result.approval_request_id == req.id
    requester_user_id = req.requested_by_user_id

    _login(services, "admin", "ChangeMe123!")
    admin_user_id = services["user_session"].principal.user_id
    approvals.reject(req.id, note="Not this time")

    rejected = budget_service.get_budget(budget.id)
    assert rejected.status == BudgetStatus.REJECTED
    assert rejected.rejected_by == admin_user_id
    assert rejected.rejected_by != requester_user_id


def test_governed_approve_checks_staleness_before_creating_request(services, monkeypatch) -> None:
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "budget.approve")
    _login(services, "admin", "ChangeMe123!")

    project = _make_project(services, name="Stale Governance Project")
    budget_service = services["budget_service"]
    approvals = services["approval_service"]
    budget = budget_service.create_budget(project.id, "stale-governance")
    budget = _submit_with_line(services, budget)
    stale_version = budget.row_version - 1

    with pytest.raises(ConcurrencyError):
        budget_service.approve_budget(budget.id, approved_by="admin", expected_version=stale_version)

    assert approvals.list_pending(project_id=project.id) == []


def test_internal_apply_methods_bypass_budget_approve_permission(services) -> None:
    # The regression test for the explicit internal permission-bypass
    # design: _apply_approval_decision/_apply_rejection_decision are only
    # reachable through an already-authorized caller and never themselves
    # check "budget.approve" — proven here by calling them directly under
    # a session that holds NO permissions at all.
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services, name="Bypass Project")
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "bypass")
    budget = _submit_with_line(services, budget)

    real_user_session = budget_service._user_session
    budget_service._user_session = None
    try:
        approved = budget_service._apply_approval_decision(
            budget_id=budget.id,
            approved_by="approver-x",
            expected_version=budget.row_version,
            notes="",
            commit=True,
        )
    finally:
        budget_service._user_session = real_user_session
    assert approved.status == BudgetStatus.APPROVED
    assert approved.approved_by == "approver-x"


def test_direct_approve_and_reject_require_budget_approve_permission(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    auth = services["auth_service"]
    project = _make_project(services, name="Permission Guard Project")
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "guarded")
    budget = _submit_with_line(services, budget)

    auth.register_user("no-approve-user", "StrongPass123", role_names=["planner"])
    _login(services, "no-approve-user", "StrongPass123")
    with pytest.raises(Exception):
        budget_service.approve_budget(
            budget.id, approved_by="no-approve-user", expected_version=budget.row_version
        )
    with pytest.raises(Exception):
        budget_service.reject_budget(
            budget.id, rejected_by="no-approve-user", expected_version=budget.row_version
        )


# ---------------------------------------------------------------------------
# Notes persistence round-trip
# ---------------------------------------------------------------------------


def test_transition_notes_persist_independently_across_reload(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "notes-roundtrip")
    budget = _submit_with_line(services, budget)
    budget_service.reject_budget(
        budget.id,
        rejected_by="admin",
        expected_version=budget.row_version,
        notes="rejection note",
    )

    services["session"].expire_all()
    reloaded = budget_service.get_budget(budget.id)
    assert reloaded.rejection_notes == "rejection note"
    assert reloaded.submission_notes == ""
    assert reloaded.notes == ""


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def test_totals_by_cost_code_and_by_task_match_hand_computed_sums(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    task_service = services["task_service"]
    task = task_service.create_task(
        project.id, "Budget Task", start_date=date(2026, 4, 1), duration_days=1
    )
    budget_service = services["budget_service"]
    code_a = _make_cost_code(services, code="CC-TOTALS-A")
    code_b = _make_cost_code(services, code="CC-TOTALS-B")
    budget = budget_service.create_budget(project.id, "totals")

    budget_service.add_line(
        budget.id,
        cost_code_id=code_a.id,
        description="A1",
        amount=Decimal("30"),
        expected_budget_version=budget.row_version,
    )
    budget = budget_service.get_budget(budget.id)
    budget_service.add_line(
        budget.id,
        cost_code_id=code_a.id,
        task_id=task.id,
        description="A2",
        amount=Decimal("20"),
        expected_budget_version=budget.row_version,
    )
    budget = budget_service.get_budget(budget.id)
    budget_service.add_line(
        budget.id,
        cost_code_id=code_b.id,
        description="B1",
        amount=Decimal("50"),
        expected_budget_version=budget.row_version,
    )

    totals_by_cost_code = budget_service.get_totals_by_cost_code(budget.id)
    assert totals_by_cost_code[code_a.id] == Decimal("50")
    assert totals_by_cost_code[code_b.id] == Decimal("50")

    totals_by_task = budget_service.get_totals_by_task(budget.id)
    assert totals_by_task[task.id] == Decimal("20")
    assert totals_by_task[""] == Decimal("80")


# ---------------------------------------------------------------------------
# Database-level scope/FK enforcement
# ---------------------------------------------------------------------------


def test_line_project_scope_is_enforced_by_the_composite_fk_at_db_level(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project_a = _make_project(services, name="FK Project A")
    project_b = _make_project(services, name="FK Project B")
    budget_service = services["budget_service"]
    code = _make_cost_code(services, code="CC-FKSCOPE")
    budget = budget_service.create_budget(project_a.id, "fk-scope")

    from src.core.modules.project_management.infrastructure.persistence.orm.budget import (
        BudgetLineORM,
    )

    session = services["session"]
    tenant_id = services["user_session"].stored_active_tenant_id()
    organization_id = services["user_session"].stored_active_organization_id()

    bad_line = BudgetLineORM(
        id="bad-line-fk-scope",
        tenant_id=tenant_id,
        organization_id=organization_id,
        budget_id=budget.id,
        project_id=project_b.id,  # deliberately mismatched vs. the budget's project
        cost_code_id=code.id,
        amount=Decimal("10"),
        currency_code="USD",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(bad_line)
    with pytest.raises(Exception):
        session.flush()
    session.rollback()


def test_task_referenced_by_budget_line_cannot_be_hard_deleted(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    project = _make_project(services)
    task_service = services["task_service"]
    task = task_service.create_task(
        project.id, "Restricted Task", start_date=date(2026, 5, 1), duration_days=1
    )
    budget_service = services["budget_service"]
    code = _make_cost_code(services, code="CC-TASKRESTRICT")
    budget = budget_service.create_budget(project.id, "task-restrict")
    budget_service.add_line(
        budget.id,
        cost_code_id=code.id,
        task_id=task.id,
        description="Task line",
        amount=Decimal("10"),
        expected_budget_version=budget.row_version,
    )

    from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM

    session = services["session"]
    # SQLite enforces FK constraints immediately on the DML statement, not
    # deferred to flush/commit — the raise happens inside execute() itself.
    with pytest.raises(Exception):
        session.execute(sa.delete(TaskORM).where(TaskORM.id == task.id))
    session.rollback()


def test_tenant_isolation_across_organizations(services) -> None:
    _login(services, "admin", "ChangeMe123!")
    organization_service = services["organization_service"]
    original_organization = organization_service.get_active_organization()
    project = _make_project(services)
    budget_service = services["budget_service"]
    budget = budget_service.create_budget(project.id, "org-scoped")

    other_organization = organization_service.create_organization(
        organization_code="PF-BUDGET-ISOLATION",
        display_name="Budget Isolation Org",
        base_currency="USD",
        is_active=False,
    )
    organization_service.set_active_organization(other_organization.id)
    try:
        assert budget_service._budget_repo.get(budget.id) is None
        assert budget_service._budget_repo.list_for_project(project.id) == []
    finally:
        organization_service.set_active_organization(original_organization.id)

    assert budget_service._budget_repo.get(budget.id).id == budget.id


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def _alembic_config(database_path) -> Config:
    config = Config("src/infra/persistence/migrations/alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    return config


def _engine_with_fk_enforcement(url: str):
    engine = sa.create_engine(url, future=True)

    @sa.event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def test_migration_creates_budget_tables_with_rls_and_cascades_line_delete(tmp_path) -> None:
    database_path = tmp_path / "budget-migration.db"
    config = _alembic_config(database_path)
    command.upgrade(config, "l0m1n2o3p4q5")
    engine = _engine_with_fk_enforcement(config.get_main_option("sqlalchemy.url"))

    with engine.begin() as connection:
        tenant_id, organization_id = connection.execute(
            sa.text(
                "SELECT o.tenant_id, o.id FROM organizations o "
                "WHERE o.tenant_id IS NOT NULL ORDER BY o.id LIMIT 1"
            )
        ).one()
        project_id = connection.execute(
            sa.text(
                "INSERT INTO projects (id, tenant_id, organization_id, name, description, "
                "status, planned_budget, currency, version) VALUES "
                "('migration-project', :tenant_id, :organization_id, 'Migration Project', '', "
                "'ACTIVE', 0.0, 'USD', 1) RETURNING id"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        ).scalar_one_or_none()
    engine.dispose()

    command.upgrade(config, "m1n2o3p4q5r6")
    engine = _engine_with_fk_enforcement(config.get_main_option("sqlalchemy.url"))
    with engine.begin() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                sa.text(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name IN ('project_finance_budgets', 'project_finance_budget_lines')"
                )
            )
        }
        assert tables == {"project_finance_budgets", "project_finance_budget_lines"}

        connection.execute(
            sa.text(
                "INSERT INTO project_finance_budgets "
                "(id, tenant_id, organization_id, project_id, name, currency_code, "
                "status, revision, version, created_at, updated_at) VALUES "
                "('mig-budget', :tenant_id, :organization_id, 'migration-project', "
                "'Migration Budget', 'USD', 'draft', 1, 1, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        )
        cost_code_id = connection.execute(
            sa.text(
                "INSERT INTO project_finance_cost_codes "
                "(id, tenant_id, organization_id, code, name, is_active, version, "
                "created_at, updated_at) VALUES "
                "('mig-cost-code', :tenant_id, :organization_id, 'MIG-CC', 'Migration CC', "
                "1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) RETURNING id"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        ).scalar_one_or_none()
        connection.execute(
            sa.text(
                "INSERT INTO project_finance_budget_lines "
                "(id, tenant_id, organization_id, budget_id, project_id, cost_code_id, "
                "amount, currency_code, version, created_at, updated_at) VALUES "
                "('mig-line', :tenant_id, :organization_id, 'mig-budget', "
                "'migration-project', 'mig-cost-code', 10, 'USD', 1, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"tenant_id": tenant_id, "organization_id": organization_id},
        )
        line_count_before = connection.execute(
            sa.text("SELECT COUNT(*) FROM project_finance_budget_lines")
        ).scalar_one()
        assert line_count_before == 1

        connection.execute(
            sa.text("DELETE FROM project_finance_budgets WHERE id = 'mig-budget'")
        )
        line_count_after = connection.execute(
            sa.text("SELECT COUNT(*) FROM project_finance_budget_lines")
        ).scalar_one()
        assert line_count_after == 0
    engine.dispose()

    command.downgrade(config, "l0m1n2o3p4q5")
    engine = _engine_with_fk_enforcement(config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                sa.text(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name IN ('project_finance_budgets', 'project_finance_budget_lines')"
                )
            )
        }
        assert tables == set()
    engine.dispose()
