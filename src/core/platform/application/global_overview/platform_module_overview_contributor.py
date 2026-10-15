from __future__ import annotations

from src.core.global_overview.contract.action_center import (
    ActionCenterContext,
)
from src.core.global_overview.contract.module_summary import (
    ModuleSummaryDto,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.port.approval.capabilities import ApprovalQueries


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

    def __init__(self, *, approval_queries: ApprovalQueries) -> None:
        self._approval_queries = approval_queries

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
            count = self._approval_queries.count_pending()
        except BusinessRuleError:
            return "Shared administration and governance"
        noun = "item" if count == 1 else "items"
        return f"{count} {noun} require attention"


__all__ = ["PlatformModuleOverviewContributor"]
