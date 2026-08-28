from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
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
from src.core.modules.project_management.contracts.reads.financials.models.finance_performance_facts import (
    CostPhasingFacts,
    CostPhasingQuery,
    PerformanceEvmFact,
    PerformanceReportDefinitionFact,
    PerformanceReportsFacts,
    PerformanceVarianceFacts,
    PerformanceVarianceMetricFact,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


logger = logging.getLogger(__name__)


class EarnedValueReadAuthority(Protocol):
    def get_earned_value(
        self,
        project_id: str,
        as_of: date | None = None,
        baseline_id: str | None = None,
    ) -> object: ...


class BaselineVarianceReadAuthority(Protocol):
    def list_baselines(self, project_id: str) -> list[object]: ...

    def list_variance_records(
        self,
        baseline_id: str,
        *,
        expected_project_id: str | None = None,
    ) -> list[object]: ...


class ProjectFinancePerformanceQuery(ProjectManagementModuleGuardMixin):
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

    def get_evm(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
        baseline_id: str | None = None,
    ) -> PerformanceEvmFact:
        self._authorize_finance(project_id, "view earned value performance")
        resolved_as_of = as_of_date or date.today()
        basis = self._read_basis(project_id, resolved_as_of)
        try:
            metrics = self._earned_value_authority.get_earned_value(
                project_id,
                as_of=resolved_as_of,
                baseline_id=baseline_id,
            )
        except BusinessRuleError as exc:
            if str(getattr(exc, "code", "")) == "PERMISSION_DENIED":
                raise
            return self._unavailable_evm(
                project_id=project_id,
                as_of_date=resolved_as_of,
                basis=basis,
                availability=self._evm_availability(exc),
                reason=str(exc),
                baseline_id=baseline_id,
            )
        except Exception as exc:  # R6E owns replacement of the current calculator.
            logger.exception(
                "PM Performance EVM calculation unavailable project=%s as_of=%s",
                project_id,
                resolved_as_of,
            )
            return self._unavailable_evm(
                project_id=project_id,
                as_of_date=resolved_as_of,
                basis=basis,
                availability="calculator_error",
                reason="Earned value is temporarily unavailable.",
                baseline_id=baseline_id,
            )

        etc = self._optional_float(getattr(metrics, "ETC", None))
        return PerformanceEvmFact(
            project_id=project_id,
            as_of_date=resolved_as_of,
            availability="available" if etc is not None else "forecast_unavailable",
            unavailable_reason=(
                "" if etc is not None else "No approved Forecast exists for this as-of date; ETC, EAC, and VAC are unavailable."
            ),
            baseline_id=str(getattr(metrics, "baseline_id", "") or "") or None,
            budget_revision=basis.approved_budget_revision,
            forecast_revision=basis.approved_forecast_revision,
            forecast_as_of=basis.approved_forecast_as_of,
            currency_code=basis.currency_code,
            bac=self._optional_float(getattr(metrics, "BAC", None)),
            pv=self._optional_float(getattr(metrics, "PV", None)),
            ev=self._optional_float(getattr(metrics, "EV", None)),
            ac=self._optional_float(getattr(metrics, "AC", None)),
            cv=None,
            sv=None,
            cpi=self._optional_float(getattr(metrics, "CPI", None)),
            spi=self._optional_float(getattr(metrics, "SPI", None)),
            etc=etc,
            eac=self._optional_float(getattr(metrics, "EAC", None)),
            vac=self._optional_float(getattr(metrics, "VAC", None)),
            tcpi_bac=self._optional_float(getattr(metrics, "TCPI_to_BAC", None)),
            tcpi_eac=self._optional_float(getattr(metrics, "TCPI_to_EAC", None)),
            notes=str(getattr(metrics, "notes", "") or ""),
        )

    def get_variance(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
        selected_baseline_id: str | None = None,
    ) -> PerformanceVarianceFacts:
        self._authorize_finance(project_id, "view finance variance")
        resolved_as_of = as_of_date or date.today()
        basis = self._read_basis(project_id, resolved_as_of)
        baselines = tuple(
            item
            for item in self._baseline_variance_authority.list_baselines(project_id)
            if str(getattr(getattr(item, "status", ""), "value", getattr(item, "status", "")))
            in {"approved", "superseded"}
        )
        selected = next(
            (item for item in baselines if getattr(item, "id", "") == selected_baseline_id),
            None,
        )
        selected = selected or next(
            (
                item
                for item in baselines
                if str(getattr(getattr(item, "status", ""), "value", getattr(item, "status", "")))
                == "approved"
            ),
            baselines[0] if baselines else None,
        )
        records = (
            tuple(
                sorted(
                    self._baseline_variance_authority.list_variance_records(
                        str(getattr(selected, "id")),
                        expected_project_id=project_id,
                    ),
                    key=lambda row: abs(Decimal(getattr(row, "cost_variance", 0) or 0)),
                    reverse=True,
                )
            )
            if selected is not None
            else ()
        )
        vac = basis.variance_at_completion
        revision = self._revision_label(
            basis.approved_budget_revision,
            basis.approved_forecast_revision,
        )
        metrics = (
            PerformanceVarianceMetricFact(
                metric_code="vac",
                display_name="Variance at Completion (VAC)",
                value=vac,
                currency_code=basis.currency_code,
                unit="money",
                sign_convention="Positive is favorable remaining Budget; negative is projected overrun.",
                as_of_date=resolved_as_of,
                source_revision=revision,
                availability="available" if vac is not None else "forecast_unavailable",
                unavailable_reason="No approved Forecast exists for this as-of date." if vac is None else "",
            ),
            PerformanceVarianceMetricFact(
                metric_code="budget_pressure",
                display_name="Budget Pressure",
                value=None if vac is None else -vac,
                currency_code=basis.currency_code,
                unit="money",
                sign_convention="Positive is projected overrun; negative is favorable headroom.",
                as_of_date=resolved_as_of,
                source_revision=revision,
                availability="available" if vac is not None else "forecast_unavailable",
                unavailable_reason="No approved Forecast exists for this as-of date." if vac is None else "",
            ),
            PerformanceVarianceMetricFact(
                metric_code="period_actual_vs_planned",
                display_name="Period Actual vs Planned",
                value=None,
                currency_code=basis.currency_code,
                unit="money",
                sign_convention="Positive means period Actual exceeds period Planned.",
                as_of_date=resolved_as_of,
                source_revision="Select a bounded Cost Phasing period",
                availability="period_required",
                unavailable_reason="A bounded comparison period is required; no value is inferred here.",
            ),
            PerformanceVarianceMetricFact(
                metric_code="schedule_variance",
                display_name="EVM Schedule Variance",
                value=None,
                currency_code=basis.currency_code,
                unit="money",
                sign_convention="Positive is ahead of the cost-loaded baseline schedule.",
                as_of_date=resolved_as_of,
                source_revision="EVM authority",
                availability="evm_required",
                unavailable_reason="Review the EVM subsection; baseline movement below is plan-to-plan history, not EVM SV.",
            ),
        )
        return PerformanceVarianceFacts(
            project_id=project_id,
            as_of_date=resolved_as_of,
            currency_code=basis.currency_code,
            budget_revision=basis.approved_budget_revision,
            forecast_revision=basis.approved_forecast_revision,
            forecast_as_of=basis.approved_forecast_as_of,
            selected_baseline_id=("" if selected is None else str(getattr(selected, "id"))),
            selected_baseline_label=(
                ""
                if selected is None
                else f"{getattr(selected, 'name', 'Baseline')} v{getattr(selected, 'version', '')}"
            ),
            compared_baseline_id=(
                ""
                if not records
                else str(getattr(records[0], "superseded_baseline_id", "") or "")
            ),
            baseline_versions=baselines,
            baseline_records=records,
            metrics=metrics,
        )

    def get_cost_phasing(
        self,
        project_id: str,
        *,
        date_from: date,
        date_to: date,
        granularity: str = "month",
    ) -> CostPhasingFacts:
        self._authorize_finance(project_id, "view project cost phasing")
        normalized_granularity = str(granularity or "").strip().lower()
        if normalized_granularity not in {"month", "quarter"}:
            raise BusinessRuleError(
                "Cost Phasing granularity must be month or quarter.",
                code="COST_PHASING_GRANULARITY_INVALID",
            )
        if date_from > date_to:
            raise BusinessRuleError(
                "Cost Phasing start date must not be after its end date.",
                code="COST_PHASING_RANGE_INVALID",
            )
        month_span = (date_to.year - date_from.year) * 12 + date_to.month - date_from.month
        if month_span > 36:
            raise BusinessRuleError(
                "Cost Phasing range cannot exceed 36 months.",
                code="COST_PHASING_RANGE_TOO_LARGE",
            )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project cost phasing"
        )
        facts = self._performance_reader.read_cost_phasing(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            query=CostPhasingQuery(
                date_from=date_from,
                date_to=date_to,
                granularity=normalized_granularity,
            ),
        )
        if facts is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        return facts

    def get_reports(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
    ) -> PerformanceReportsFacts:
        require_permission(
            self._user_session,
            "report.view",
            operation_label="view project finance reports",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "report.view",
            operation_label="view project finance reports",
        )
        self._authorize_finance(project_id, "view project finance report basis")
        resolved_as_of = as_of_date or date.today()
        basis = self._read_basis(project_id, resolved_as_of)
        return PerformanceReportsFacts(
            project_id=project_id,
            as_of_date=resolved_as_of,
            currency_code=basis.currency_code,
            budget_revision=basis.approved_budget_revision,
            forecast_revision=basis.approved_forecast_revision,
            forecast_as_of=basis.approved_forecast_as_of,
            definitions=(
                PerformanceReportDefinitionFact(
                    report_code="project_finance_xlsx",
                    display_name="Project Finance Workbook",
                    formats=("xlsx",),
                    authority_label="Authoritative Finance reads with permission-filtered report sections",
                ),
                PerformanceReportDefinitionFact(
                    report_code="project_finance_pdf",
                    display_name="Project Finance Report",
                    formats=("pdf",),
                    authority_label="Authoritative Finance reads with permission-filtered report sections",
                ),
            ),
        )

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

    @staticmethod
    def _optional_float(value: object) -> float | None:
        return None if value is None else float(value)

    @staticmethod
    def _evm_availability(exc: BusinessRuleError) -> str:
        return {
            "NO_BASELINE": "baseline_unavailable",
            "BASELINE_EMPTY": "baseline_unavailable",
            "ACTUAL_COST_INCOMPLETE": "actual_cost_unavailable",
        }.get(str(getattr(exc, "code", "")), "prerequisite_unavailable")

    @staticmethod
    def _revision_label(
        budget_revision: int | None,
        forecast_revision: int | None,
    ) -> str:
        return (
            f"Budget r{budget_revision if budget_revision is not None else 'N/A'} / "
            f"Forecast r{forecast_revision if forecast_revision is not None else 'N/A'}"
        )

    @staticmethod
    def _unavailable_evm(
        *,
        project_id: str,
        as_of_date: date,
        basis: object,
        availability: str,
        reason: str,
        baseline_id: str | None,
    ) -> PerformanceEvmFact:
        return PerformanceEvmFact(
            project_id=project_id,
            as_of_date=as_of_date,
            availability=availability,
            unavailable_reason=reason,
            baseline_id=baseline_id,
            budget_revision=getattr(basis, "approved_budget_revision", None),
            forecast_revision=getattr(basis, "approved_forecast_revision", None),
            forecast_as_of=getattr(basis, "approved_forecast_as_of", None),
            currency_code=str(getattr(basis, "currency_code", "") or ""),
            bac=None,
            pv=None,
            ev=None,
            ac=None,
            cv=None,
            sv=None,
            cpi=None,
            spi=None,
            etc=None,
            eac=None,
            vac=None,
            tcpi_bac=None,
            tcpi_eac=None,
            notes="",
        )


__all__ = ["ProjectFinancePerformanceQuery"]
