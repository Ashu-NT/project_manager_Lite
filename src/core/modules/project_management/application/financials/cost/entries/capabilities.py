from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
    ProjectCostEntryKind,
    ProjectCostEntryStatus,
)
from src.core.platform.domain.approval.policy import is_governance_required


@dataclass(frozen=True, slots=True)
class CostEntryActionCapabilities:
    project_visible: bool = False
    is_manual: bool = False
    can_edit: bool = False
    can_delete: bool = False
    can_submit: bool = False
    can_approve: bool = False
    can_reject: bool = False
    can_post: bool = False
    can_reverse: bool = False
    approval_action: str = ""
    read_only_reason: str = ""

    @classmethod
    def none(cls) -> "CostEntryActionCapabilities":
        """All-False default, for a caller with no computed capabilities to pass."""
        return cls()


def is_manual_actual_entry(entry: ProjectCostEntry) -> bool:
    return entry.is_manual_actual


def build_cost_entry_capabilities(
    entry: ProjectCostEntry,
    *,
    user_session,
) -> CostEntryActionCapabilities:
    """Project source-, lifecycle-, and permission-aware Actual command evidence."""

    project_visible = _has_project_permission(user_session, entry.project_id, "finance.read")
    if not project_visible:
        return CostEntryActionCapabilities()

    manual = is_manual_actual_entry(entry)
    if not manual:
        return CostEntryActionCapabilities(
            project_visible=True,
            read_only_reason="This actual is owned by its source workflow and is read-only in Project Finance.",
        )

    status = entry.status
    is_draft = status is ProjectCostEntryStatus.DRAFT
    is_submitted = status is ProjectCostEntryStatus.SUBMITTED
    actor_id = _actor_id(user_session)
    independent_decider = bool(
        actor_id and entry.submitted_by and actor_id != entry.submitted_by
    )
    governed = is_governance_required("project_cost.approve")

    can_update = _has_project_permission(
        user_session, entry.project_id, "project_cost.update_draft"
    )
    can_decide = _has_project_permission(
        user_session, entry.project_id, "project_cost.approve"
    )
    can_request = _has_project_permission(
        user_session, entry.project_id, "approval.request"
    )

    can_approve = is_submitted and (can_request if governed else can_decide and independent_decider)
    can_reject = is_submitted and not governed and can_decide and independent_decider

    reason = ""
    if is_submitted and not governed and can_decide and not independent_decider:
        reason = "The submitter cannot approve or reject their own actual."
    elif status in {ProjectCostEntryStatus.POSTED, ProjectCostEntryStatus.REVERSED}:
        reason = "Posted financial history is immutable; corrections use signed reversal evidence."

    return CostEntryActionCapabilities(
        project_visible=True,
        is_manual=True,
        can_edit=is_draft and can_update,
        can_delete=is_draft and can_update,
        can_submit=is_draft
        and _has_project_permission(user_session, entry.project_id, "project_cost.submit"),
        can_approve=can_approve,
        can_reject=can_reject,
        can_post=status is ProjectCostEntryStatus.APPROVED
        and _has_project_permission(user_session, entry.project_id, "project_cost.post"),
        can_reverse=status is ProjectCostEntryStatus.POSTED
        and entry.entry_kind is not ProjectCostEntryKind.REVERSAL
        and _has_project_permission(user_session, entry.project_id, "project_cost.reverse"),
        approval_action="request" if governed and can_approve else ("decide" if can_approve else ""),
        read_only_reason=reason,
    )


def can_create_manual_actual(*, user_session, project_id: str) -> bool:
    return _has_project_permission(user_session, project_id, "project_cost.create")


def _has_project_permission(user_session, project_id: str, permission: str) -> bool:
    if user_session is None:
        return False
    try:
        return bool(
            user_session.has_permission(permission)
            and user_session.has_project_permission(project_id, permission)
        )
    except Exception:
        return False


def _actor_id(user_session) -> str:
    try:
        principal = user_session.principal if user_session is not None else None
        return str(getattr(principal, "user_id", "") or "").strip()
    except Exception:
        return ""


__all__ = [
    "CostEntryActionCapabilities",
    "build_cost_entry_capabilities",
    "can_create_manual_actual",
    "is_manual_actual_entry",
]
