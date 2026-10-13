from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import date
from typing import Protocol

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.reads.financials.finance_overview_reader import (
    FinanceOverviewReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_performance_reader import (
    FinancePerformanceReader,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class EarnedValueReadAuthority(Protocol):
    def get_earned_value(
        self,
        project_id: str,
        as_of: date | None = None,
        baseline_id: str | None = None,
    ) -> object: ...


class BaselineVarianceReadAuthority(Protocol):
    def list_baselines(self, project_id: str) -> Sequence[object]: ...

    def list_variance_records(
        self,
        baseline_id: str,
        *,
        expected_project_id: str | None = None,
    ) -> Sequence[object]: ...


from src.core.modules.project_management.application.financials.analytics.performance.cost_phasing import (
    CostPhasingQueries,
)
from src.core.modules.project_management.application.financials.analytics.performance.evm import (
    EvmQueries,
)
from src.core.modules.project_management.application.financials.analytics.performance.reports import (
    ReportsQueries,
)
from src.core.modules.project_management.application.financials.analytics.performance.variance import (
    VarianceQueries,
)


class ProjectFinancePerformanceQuery(
    EvmQueries,
    VarianceQueries,
    CostPhasingQueries,
    ReportsQueries,
    ProjectManagementModuleGuardMixin,
):
    """Permission-gated read orchestration for the four Performance surfaces."""

    def __init__(
        self,
        *,
        performance_reader: FinancePerformanceReader,
        overview_reader: FinanceOverviewReader,
        earned_value_authority: EarnedValueReadAuthority,
        baseline_variance_authority: BaselineVarianceReadAuthority,
        tenant_context_service: TenantContextService,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._performance_reader = performance_reader
        self._overview_reader = overview_reader
        self._earned_value_authority = earned_value_authority
        self._baseline_variance_authority = baseline_variance_authority
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def _authorize_finance(self, project_id: str, operation_label: str) -> None:
        require_permission(self._user_session, "finance.read", operation_label=operation_label)
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label=operation_label,
        )

    def _read_basis(self, project_id: str, as_of_date: date):
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="read Performance authority basis"
        )
        basis = self._overview_reader.read_overview_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            as_of=as_of_date,
        )
        if basis is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        return basis

__all__ = ["ProjectFinancePerformanceQuery"]
