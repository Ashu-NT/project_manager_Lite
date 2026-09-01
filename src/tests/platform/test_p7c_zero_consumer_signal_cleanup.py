
from __future__ import annotations

import glob
import inspect

from src.core.shared.events.domain_events import domain_events

_ACTIVE_FINANCE_SIGNALS = (
    "cost_entries_changed",
    "commitments_changed",
    "financial_changes_changed",
)


def _strip_strings_and_comments(source: str) -> str:
    import re

    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", source)
    no_comments = re.sub(r"#.*", "", no_docstrings)
    return no_comments


def _production_source_files():
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        yield normalized


# ---------------------------------------------------------------------------
# 1. Finance mutation hints exist only with producers and a targeted consumer
# ---------------------------------------------------------------------------


def test_finance_invalidation_signals_exist_with_producers_and_ui_consumer():
    controller_source = inspect.getsource(
        __import__(
            "src.ui_qml.modules.project_management.controllers.financials.financials_refresh_mixin",
            fromlist=["FinancialsRefreshMixin"],
        ).FinancialsRefreshMixin
    )
    production_sources = {}
    for path in _production_source_files():
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            production_sources[path] = _strip_strings_and_comments(fh.read())

    for signal_name in _ACTIVE_FINANCE_SIGNALS:
        assert hasattr(domain_events, signal_name), signal_name
        assert f"domain_events.{signal_name}" in controller_source
        producer_paths = [
            path
            for path, source in production_sources.items()
            if "/application/financials/" in path
            and f"domain_events.{signal_name}.emit" in source
        ]
        assert producer_paths, f"{signal_name} has no committed service producer"


# ---------------------------------------------------------------------------
# 2. Every remaining ApprovalPostCommitEvent resolves to a real signal + real consumer
# ---------------------------------------------------------------------------


def test_every_remaining_approval_post_commit_event_signal_name_exists_and_has_a_ui_consumer():
    import ast

    consumer_grep_cache: dict[str, bool] = {}

    def _has_ui_consumer(signal_name: str) -> bool:
        if signal_name in consumer_grep_cache:
            return consumer_grep_cache[signal_name]
        found = False
        for path in glob.glob("src/ui_qml/**/*.py", recursive=True):
            if "__pycache__" in path:
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                if f"domain_events.{signal_name}" in fh.read():
                    found = True
                    break
        consumer_grep_cache[signal_name] = found
        return found

    signal_names_found = set()
    for path in _production_source_files():
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "ApprovalPostCommitEvent(" not in source:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "ApprovalPostCommitEvent"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                signal_names_found.add(node.args[0].value)

    assert signal_names_found, "expected to find at least one ApprovalPostCommitEvent site"
    for signal_name in signal_names_found:
        assert hasattr(domain_events, signal_name), (
            f"ApprovalPostCommitEvent references non-existent signal {signal_name!r}"
        )
        assert _has_ui_consumer(signal_name), (
            f"ApprovalPostCommitEvent({signal_name!r}, ...) has no UI consumer -- emit-into-the-void"
        )


# ---------------------------------------------------------------------------
# 3. _emit_signal_safely remains -- real remaining callers confirmed
# ---------------------------------------------------------------------------


def test_emit_signal_safely_still_exists_with_real_remaining_callers():
    """§9: not removed -- `budget_apply_participant.py`/`task_apply_participant.py`/
    `baseline_apply_participant.py`/`billing_preparation_apply_participant.py`/
    `financial_change_apply_participant.py` (partially) and the two Inventory procurement
    participants still return legitimate `ApprovalPostCommitEvent` values."""
    import src.core.platform.application.approval.approval_service as approval_service_module

    source = inspect.getsource(approval_service_module)
    assert "_emit_signal_safely" in source
    assert "getattr(domain_events, signal_name" in source


# ---------------------------------------------------------------------------
# 4. Approval participant behavior: business mutation preserved, dead output gone
# ---------------------------------------------------------------------------


def test_project_cost_apply_participant_emits_scoped_post_commit_events():
    from src.core.modules.project_management.infrastructure.approval.project_cost_apply_participant import (
        ProjectCostApprovalParticipant,
    )

    for method in (ProjectCostApprovalParticipant.apply, ProjectCostApprovalParticipant.reject):
        source = inspect.getsource(method)
        assert '"cost_entries_changed"' in source
        assert "invalidation_scope(entry)" in source


def test_financial_change_apply_participant_emits_scoped_change_and_forecast_hints():
    from src.core.modules.project_management.infrastructure.approval.financial_change_apply_participant import (
        FinancialChangeApprovalParticipant,
    )

    apply_source = inspect.getsource(FinancialChangeApprovalParticipant.apply)
    assert '"financial_changes_changed"' in apply_source
    assert "invalidation_scope(change)" in apply_source
    assert "ForecastVersionChanged(" in apply_source
    assert "ForecastVersionChangeType.APPROVED" in apply_source
    assert "budgets_changed" in apply_source
    assert "tasks_changed" in apply_source

    reject_source = inspect.getsource(FinancialChangeApprovalParticipant.reject)
    assert '"financial_changes_changed"' in reject_source
    assert "invalidation_scope(change)" in reject_source


def test_real_budget_approval_still_emits_its_own_real_signal(services):
    """Approval regression: a real budget approval still produces the legitimate
    `budgets_changed` post-commit output -- proves the apply-participant edits did not disturb
    the signals that DO have real consumers."""
    from decimal import Decimal

    _login(services, "admin", "ChangeMe123!")
    project = services["project_service"].create_project(
        name=_unique("P7C Budget Project"), code=_unique("P7C-BUD"), financial_currency_code="USD"
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=_unique("P7C-CC"), name="P7C cost code"
    )
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "P7C Budget")
    budgets.add_line(
        budget.id, cost_code_id=cost_code.id, description="Line", amount=Decimal("100"),
        expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(budget.id, "admin", expected_version=budget.row_version)

    budgets_calls = []
    domain_events.budgets_changed.connect(lambda project_id: budgets_calls.append(project_id))

    budgets.approve_budget(budget.id, approved_by="admin", expected_version=budget.row_version)

    assert budgets_calls == [project.id]


# ---------------------------------------------------------------------------
# 5. Producer structure and integration-owned post-commit hints
# ---------------------------------------------------------------------------


def test_no_commit_and_emit_helper_remains_anywhere():
    """Service helpers use the concise `_commit` name; signal publication is part of commit."""
    hits = []
    for path in _production_source_files():
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "_commit_and_emit" in source:
            hits.append(path)
    assert hits == [], hits


def test_procurement_financial_dispatcher_emits_scoped_post_commit_hints():
    import src.infra.integration.procurement_financial_dispatcher as module

    source = inspect.getsource(module)
    assert "FinanceInvalidationScope" in source
    assert "commitments_changed.emit(scope)" in source
    assert "cost_entries_changed.emit(scope)" in source
    assert source.index("self._session.commit()") < source.index("self._emit_refresh(")


def test_approved_time_dispatcher_emits_scoped_post_commit_hint():
    import src.infra.integration.approved_time_dispatcher as module

    source = inspect.getsource(module)
    assert "FinanceInvalidationScope" in source
    assert "cost_entries_changed.emit" in source
    assert source.index("self._session.commit()") < source.index("self._emit_refresh(")


# ---------------------------------------------------------------------------
# 6. Final legacy signal invariant
# ---------------------------------------------------------------------------


def test_final_invariant_every_remaining_signal_has_a_production_reference():
    import dataclasses

    signal_names = [f.name for f in dataclasses.fields(domain_events)]
    reference_counts = {name: 0 for name in signal_names}
    for path in _production_source_files():
        if path == "src/core/shared/events/domain_events.py":
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = _strip_strings_and_comments(fh.read())
        for name in signal_names:
            if name in source:
                reference_counts[name] += 1

    orphaned = [name for name, count in reference_counts.items() if count == 0]
    assert orphaned == [], orphaned


def test_no_new_business_domain_event_or_replacement_signal_introduced():
    import ast

    forbidden = (
        "CostEntryChanged", "CommitmentChanged", "ForecastChanged",
        "FinancialChangeChanged", "FinanceChanged",
    )
    hits = []
    for path in _production_source_files():
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        defined = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
        if defined.intersection(forbidden):
            hits.append((path, sorted(defined.intersection(forbidden))))
    assert hits == [], hits


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))
