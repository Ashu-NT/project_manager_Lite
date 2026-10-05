from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from src.core.modules.project_management.contracts.reads.financials.models.finance_performance_facts import (
    PerformanceEvmFact,
    PerformanceVarianceFacts,
    PerformanceVarianceMetricFact,
)
from src.core.platform.common.exceptions import NotFoundError

logger = logging.getLogger(__name__)


class VarianceQueries:
    def get_variance(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
        selected_baseline_id: str | None = None,
    ) -> PerformanceVarianceFacts:
        self._authorize_finance(project_id, "view finance variance")
        resolved_as_of = as_of_date or datetime.now(timezone.utc).astimezone().date()
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
        if selected_baseline_id and selected is None:
            raise NotFoundError("Baseline not found.", code="BASELINE_NOT_FOUND")
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
                        str(selected.id),
                        expected_project_id=project_id,
                    ),
                    key=lambda row: abs(Decimal(getattr(row, "cost_variance", 0) or 0)),
                    reverse=True,
                )
            )
            if selected is not None
            else ()
        )
        evm = self._read_evm(
            project_id=project_id,
            as_of_date=resolved_as_of,
            basis=basis,
            baseline_id=None,
        )
        revision = self._revision_label(
            basis.approved_budget_revision,
            basis.approved_forecast_revision,
        )
        metrics = (
            self._evm_variance_metric(
                metric_code="cost_variance",
                display_name="Cost Variance (CV)",
                value=evm.cv,
                evm=evm,
                sign_convention="Positive is favorable; negative is unfavorable.",
                semantic_tooltip="Earned Value minus Actual Cost (EV - AC).",
            ),
            self._evm_variance_metric(
                metric_code="schedule_variance",
                display_name="Schedule Variance (SV)",
                value=evm.sv,
                evm=evm,
                sign_convention="Positive is ahead in earned-value terms; negative is behind.",
                semantic_tooltip="Earned Value minus Planned Value (EV - PV); this is monetary EVM variance, not schedule days.",
            ),
            self._evm_variance_metric(
                metric_code="vac",
                display_name="Variance at Completion (VAC)",
                value=evm.vac,
                evm=evm,
                sign_convention="Positive is favorable; negative is projected overrun.",
                semantic_tooltip="Budget at Completion minus Estimate at Completion (BAC - EAC).",
            ),
            self._budget_pressure_metric(
                basis=basis,
                evm=evm,
                as_of_date=resolved_as_of,
                revision=revision,
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
                favorability="unavailable",
                semantic_tooltip="Period Actual versus Planned requires the bounded Cost Phasing authority and is not inferred by Variance.",
                unavailable_reason="A bounded comparison period is required; no value is inferred here.",
            ),
        )
        return PerformanceVarianceFacts(
            project_id=project_id,
            as_of_date=resolved_as_of,
            currency_code=basis.currency_code,
            budget_revision=basis.approved_budget_revision,
            forecast_revision=basis.approved_forecast_revision,
            forecast_as_of=basis.approved_forecast_as_of,
            selected_baseline_id=("" if selected is None else str(selected.id)),
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
    def _evm_variance_metric(
        *,
        metric_code: str,
        display_name: str,
        value: Decimal | None,
        evm: PerformanceEvmFact,
        sign_convention: str,
        semantic_tooltip: str,
    ) -> PerformanceVarianceMetricFact:
        unavailable_reason = "" if value is not None else evm.unavailable_reason
        return PerformanceVarianceMetricFact(
            metric_code=metric_code,
            display_name=display_name,
            value=value,
            currency_code=evm.currency_code,
            unit="money",
            sign_convention=sign_convention,
            as_of_date=evm.as_of_date,
            source_revision="Canonical Decimal EVM",
            availability="available" if value is not None else evm.availability,
            favorability=VarianceQueries._favorable_state(value),
            semantic_tooltip=semantic_tooltip,
            unavailable_reason=unavailable_reason,
        )

    @staticmethod
    def _budget_pressure_metric(
        *,
        basis: object,
        evm: PerformanceEvmFact,
        as_of_date: date,
        revision: str,
    ) -> PerformanceVarianceMetricFact:
        approved_budget_id = getattr(basis, "approved_budget_id", None)
        if not approved_budget_id:
            value = None
            availability = "budget_unavailable"
            unavailable_reason = "No approved Budget exists for this as-of date."
        elif evm.eac is None:
            value = None
            availability = evm.availability
            unavailable_reason = evm.unavailable_reason or "EAC is unavailable."
        else:
            value = evm.eac - Decimal(str(getattr(basis, "approved_budget", "0")))
            availability = "available"
            unavailable_reason = ""
        return PerformanceVarianceMetricFact(
            metric_code="budget_pressure",
            display_name="Budget Pressure",
            value=value,
            currency_code=evm.currency_code,
            unit="money",
            sign_convention="Positive is projected pressure; negative is favorable headroom.",
            as_of_date=as_of_date,
            source_revision=revision,
            availability=availability,
            favorability=VarianceQueries._pressure_state(value),
            semantic_tooltip="Estimate at Completion minus the exact total of the approved Budget (EAC - Approved Budget).",
            unavailable_reason=unavailable_reason,
        )

    @staticmethod
    def _favorable_state(value: Decimal | None) -> str:
        if value is None:
            return "unavailable"
        if value > 0:
            return "favorable"
        if value < 0:
            return "unfavorable"
        return "on_target"

    @staticmethod
    def _pressure_state(value: Decimal | None) -> str:
        if value is None:
            return "unavailable"
        if value > 0:
            return "unfavorable"
        if value < 0:
            return "favorable"
        return "on_target"

