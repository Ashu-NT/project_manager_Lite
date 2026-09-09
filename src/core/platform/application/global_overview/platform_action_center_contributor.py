from __future__ import annotations

from datetime import date

from src.core.application.global_overview.contracts.action_center import (
    ActionCenterContext,
    ActionCenterContribution,
    ActionCenterItemDto,
    ActionCenterSummaryDto,
)
from src.core.application.global_overview.services.ordering import sort_action_center_items
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.application.platform_runtime.platform_runtime_service import (
    PlatformRuntimeApplicationService,
)

_APPROVAL_DECIDE_PERMISSION = "approval.decide"
_EMPTY_SUMMARY = ActionCenterSummaryDto(
    all_action_items=0, reviews_and_approvals=0, assigned_work=0, submissions=0
)


class PlatformActionCenterContributor:
    """Platform's Action Center contribution: approvals awaiting a decision.

    Relevance is permission-based, not a targeted-reviewer assignment --
    ApprovalRequest has no reviewer field, so every pending approval is
    shown to every user holding approval.decide, and a user without it
    contributes zero items and a zero count, never a partially-filtered
    list. No due date is ever invented -- ApprovalRequest has none.
    """

    def __init__(
        self,
        *,
        approval_service: ApprovalService,
        platform_runtime_application_service: PlatformRuntimeApplicationService,
    ) -> None:
        self._approval_service = approval_service
        self._platform_runtime_application_service = platform_runtime_application_service

    def collect(
        self,
        context: ActionCenterContext,
        preview_limit: int,
    ) -> ActionCenterContribution:
        if not self._can_decide():
            return ActionCenterContribution(items=(), summary=_EMPTY_SUMMARY)

        exact_count = self._approval_service.count_pending()
        candidates = self._approval_service.list_pending(limit=max(preview_limit, 1))
        items = tuple(self._to_item(request) for request in candidates)
        ordered = sort_action_center_items(items, today=date.today())[:preview_limit]
        summary = ActionCenterSummaryDto(
            all_action_items=exact_count,
            reviews_and_approvals=exact_count,
            assigned_work=0,
            submissions=0,
        )
        return ActionCenterContribution(items=ordered, summary=summary)

    def _can_decide(self) -> bool:
        return (
            _APPROVAL_DECIDE_PERMISSION
            in self._platform_runtime_application_service.get_current_permissions()
        )

    @staticmethod
    def _to_item(request) -> ActionCenterItemDto:
        entity_label = request.entity_type.replace("_", " ").strip() or "request"
        return ActionCenterItemDto(
            id=request.id,
            kind="approval",
            title=f"Review {entity_label}",
            module="Platform",
            subject_type=request.entity_type,
            subject_id=request.entity_id,
            subject_display=entity_label.title(),
            action_state="awaiting_decision",
            route_id="control_approvals",
            sort_at=request.requested_at,
        )


__all__ = ["PlatformActionCenterContributor"]
