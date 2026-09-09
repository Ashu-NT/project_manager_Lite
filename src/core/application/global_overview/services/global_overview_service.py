from __future__ import annotations

import logging

from src.core.application.global_overview.contracts.action_center import (
    ActionCenterContext,
    ActionCenterContribution,
)
from src.core.application.global_overview.contracts.module_summary import (
    ModuleSummaryContributor,
    ModuleSummaryDto,
)
from src.core.application.global_overview.contracts.overview import (
    AttentionSummaryDto,
    GlobalOverviewContextDto,
)
from src.core.application.global_overview.services.action_center_service import ActionCenterService
from src.core.application.global_overview.services.activity_visibility import is_activity_visible
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.application.platform_runtime.platform_runtime_service import (
    PlatformRuntimeApplicationService,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.history.activity.activity_entry import ActivityEntry
from src.core.platform.domain.security.auth.session import UserSessionContext

logger = logging.getLogger(__name__)

_OPERATION_LABEL = "view the global overview"


class GlobalOverviewService:
    """Cross-module orchestration for the Global Overview landing page.

    Depends only on application services, the generic ActionCenterService, and
    ModuleSummaryContributor abstractions -- never on a concrete PM (or other
    module) application class. Each public method computes its own answer
    independently: none of them share mutable build state, so one dependency
    failing (e.g. Activity) never prevents the others from succeeding.
    """

    def __init__(
        self,
        *,
        tenant_context_service: TenantContextService,
        platform_runtime_application_service: PlatformRuntimeApplicationService,
        activity_service: ActivityService,
        action_center_service: ActionCenterService,
        module_summary_contributors: tuple[ModuleSummaryContributor, ...],
        user_session: UserSessionContext,
    ) -> None:
        self._tenant_context_service = tenant_context_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._activity_service = activity_service
        self._action_center_service = action_center_service
        self._module_summary_contributors = module_summary_contributors
        self._user_session = user_session

    def get_context(self) -> GlobalOverviewContextDto:
        scope = self._tenant_context_service.require_organization_context(
            operation_label=_OPERATION_LABEL
        )
        organization_name = scope.organization.display_name if scope.organization else ""
        return GlobalOverviewContextDto(
            tenant_name=scope.tenant.display_name,
            organization_name=organization_name,
            # UserSessionPrincipal carries only a set of role_names, with no
            # canonical/primary/display role -- inventing a "highest privilege"
            # or "first role" precedence would be a fabricated business rule,
            # so this stays None until a real canonical role concept exists.
            role_label=None,
        )

    def get_attention_summary(self) -> AttentionSummaryDto:
        context = self._build_action_center_context()
        return self._action_center_service.build(context, preview_limit=0).summary

    def list_action_center(self, *, limit: int = 50) -> ActionCenterContribution:
        context = self._build_action_center_context()
        return self._action_center_service.build(context, preview_limit=limit)

    def list_module_summaries(self) -> tuple[ModuleSummaryDto, ...]:
        context = self._build_action_center_context()
        summaries: list[ModuleSummaryDto] = []
        for contributor in self._module_summary_contributors:
            try:
                summary = contributor.get_summary(context)
            except Exception:
                # A contributor's own accessibility/availability determination
                # failed -- fail closed and omit its card rather than let one
                # module break the whole Overview page. A contributor whose
                # area is accessible but whose live metric alone fails is
                # expected to catch that itself and still return a DTO with a
                # degraded summary_text (see the Platform/PM contributors).
                logger.exception(
                    "Module summary contributor failed module=%s",
                    type(contributor).__name__,
                )
                continue
            if summary is not None:
                summaries.append(summary)
        # Sorted by module_code so contributor registration order can never
        # change the rendered order.
        return tuple(sorted(summaries, key=lambda summary: summary.module_code))

    def list_recent_activity(self, *, limit: int = 50) -> tuple[ActivityEntry, ...]:
        entries = self._activity_service.list_recent(limit=limit)
        accessible_module_codes = frozenset(
            module.code
            for module in self._platform_runtime_application_service.list_accessible_modules()
        )
        return tuple(
            entry
            for entry in entries
            if is_activity_visible(entry.module, accessible_module_codes=accessible_module_codes)
        )

    def _build_action_center_context(self) -> ActionCenterContext:
        scope = self._tenant_context_service.require_organization_context(
            operation_label=_OPERATION_LABEL
        )
        principal = self._user_session.principal
        if principal is None:
            raise BusinessRuleError(
                f"Authentication is required to {_OPERATION_LABEL}.",
                code="AUTHENTICATION_REQUIRED",
            )
        return ActionCenterContext(
            user_id=principal.user_id,
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
        )


__all__ = ["GlobalOverviewService"]
