from __future__ import annotations

import inspect
import re
from pathlib import Path

from src.core.platform.application.approval import approval_mutation_participant
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.domain.approval.approval_request import ApprovalRequest

_SRC_CORE = Path(__file__).resolve().parents[2] / "core"


def test_approval_request_does_not_implement_records_domain_events():
    """§1/§35: Approval DomainEvents remain APPLICATION-authored (future `uow.record_event` in
    P2) -- `ApprovalRequest` itself must never implement `RecordsDomainEvents`."""
    base_names = {base.__name__ for base in ApprovalRequest.__mro__}
    assert "RecordsDomainEvents" not in base_names


### Approval-P3 legitimately implemented Approval ViewInvalidation (one mapper, one Qt
### adapter, routed via `OrganizationScope`). The phase-boundary guard that used to assert no
### `ViewInvalidationHint` producer existed yet is retired; its forward-looking replacement --
### that ONLY the `approval` mapper module produces the `approval_requests` hint, and that no
### `ApprovalApplied`/generic P6 shared adapter was introduced -- lives in
### `test_approval_view_invalidation.py`.


def test_request_change_has_no_commit_parameter():
    """§13/§38: `request_change(commit=False)` no longer exists on `ApprovalService`."""
    params = inspect.signature(ApprovalService.request_change).parameters
    assert "commit" not in params


def test_no_production_caller_passes_commit_false_to_request_change():
    """§38: production count of `request_change(..., commit=False)` callers must be ZERO --
    every former caller-owned-transaction path now calls `request_approval_using(...)` directly
    inside its own canonical UoW instead of composing into this method."""
    pattern = re.compile(r"request_change\([^)]*?commit\s*=", re.DOTALL)
    offenders = []
    for path in _SRC_CORE.rglob("*.py"):
        source = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(source):
            offenders.append(str(path))
    assert offenders == []


def _strip_strings_and_comments(source: str) -> str:
    """Drop triple-quoted docstrings, string literals, and `#` comments so a structural scan
    only sees actual code, not prose that happens to mention a forbidden call/name."""
    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", source)
    no_comments = re.sub(r"#.*", "", no_docstrings)
    return no_comments


def test_participant_never_commits_rolls_back_or_opens_a_unit_of_work():
    """§8/§11: the transaction-agnostic Approval request participant must never commit/rollback/
    open a Session/UnitOfWork/publish notifications/emit `approvals_changed` -- it operates
    strictly inside the caller's own already-open transaction."""
    source = _strip_strings_and_comments(inspect.getsource(approval_mutation_participant))
    for forbidden in (
        ".commit(",
        ".rollback(",
        "UnitOfWork(",
        "sessionmaker(",
        "approvals_changed",
        "publish_requested",
    ):
        assert forbidden not in source, (
            f"approval_mutation_participant.py must never contain {forbidden!r}"
        )


def test_participant_module_never_imports_a_concrete_sqlalchemy_unit_of_work():
    """§19: the participant must not be coupled to a concrete SQLAlchemy UoW merely to prepare
    for P2's event recording -- it takes already-constructed repo/audit-service collaborators as
    plain parameters."""
    source = _strip_strings_and_comments(inspect.getsource(approval_mutation_participant))
    for forbidden in ("SqlAlchemyUnitOfWork", "sqlalchemy", "Session"):
        assert forbidden not in source
