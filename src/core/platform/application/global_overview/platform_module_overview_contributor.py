from __future__ import annotations

from src.core.application.global_overview.contracts.action_center import ActionCenterContext
from src.core.application.global_overview.contracts.module_summary import ModuleSummaryDto
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.common.exceptions import BusinessRuleError


class PlatformModuleOverviewContributor:
    """Platform's Global Overview module card.

    Platform is not an EnterpriseModule -- it has no enabled/licensed
    lifecycle, so it is never gated through `list_accessible_modules()`
    (that policy is for real EnterpriseModules only). Matching the existing
    convention that the Platform Overview destination itself requires no
    specific permission, this always returns a summary. Only the live
    metric it surfaces -- the pending-approval count, the same exact count
    `PlatformActionCenterContributor` computes -- is gated on the
    permission actually required to read it; without it, the card still
    renders, just without that figure.
    """

    def __init__(self, *, approval_service: ApprovalService) -> None:
        self._approval_service = approval_service

    def get_summary(self, context: ActionCenterContext) -> ModuleSummaryDto | None:
        return ModuleSummaryDto(
            module_code="platform",
            title="Platform",
            description=(
                "Shared administration, organizational data, access, "
                "documents, and governance."
            ),
            summary_text=self._attention_summary_text(),
            route_id="platform",
        )

    def _attention_summary_text(self) -> str:
        try:
            count = self._approval_service.count_pending()
        except BusinessRuleError:
            return "Shared administration and governance"
        noun = "item" if count == 1 else "items"
        return f"{count} {noun} require attention"


__all__ = ["PlatformModuleOverviewContributor"]
