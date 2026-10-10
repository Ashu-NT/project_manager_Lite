from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import (
    RateCardResolver,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_service import (
    ProjectRateCardService,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_resolution_reader import (
    SqlAlchemyRateResolutionReader,
)
from src.infra.composition.modules.platform_registry import PlatformServiceBundle
from src.infra.composition.persistence.repositories import RepositoryBundle


def build_rate_card_services(
    session: Session,
    repositories: RepositoryBundle,
    platform_services: PlatformServiceBundle,
    *,
    clock: SystemClock,
) -> tuple[ProjectRateCardService, RateCardResolver]:
    rate_card_service = ProjectRateCardService(
        session=session,
        rate_card_repo=repositories.project_rate_card_repo,
        project_repo=repositories.project_repo,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
    resolver = RateCardResolver(
        reader=SqlAlchemyRateResolutionReader(session=session),
        tenant_context_service=platform_services.tenant_context_service,
        clock=clock,
    )
    return rate_card_service, resolver
