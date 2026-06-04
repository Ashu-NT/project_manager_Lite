"""ProjectManagementFinancialsDesktopApi — thin financial desktop facade."""

from __future__ import annotations
from datetime import date

from src.core.modules.project_management.application.financials import CostService, FinanceService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import BaselineService
from src.core.modules.project_management.application.tasks import TaskService

from src.core.modules.project_management.api.desktop.financials.models.cost_items import FinancialCostItemDto
from src.core.modules.project_management.api.desktop.financials.models.commitments import FinancialCommitmentSummaryDto
from src.core.modules.project_management.api.desktop.financials.models.forecasts import FinancialForecastDto
from src.core.modules.project_management.api.desktop.financials.models.baseline_variance import BaselineVarianceRecordDto
from src.core.modules.project_management.api.desktop.financials.models.options import (
    FinancialCostTypeDescriptor,
    FinancialProjectOptionDescriptor,
    FinancialTaskOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.financials.models.procurement import (
    ProjectProcurementCommitmentSummary,
    ProjectRequisitionDesktopDto,
)
from src.core.modules.project_management.api.desktop.financials.models.snapshots import FinancialSnapshotDto
from src.core.modules.project_management.api.desktop.financials.commands.create_cost_item import FinancialCreateCommand
from src.core.modules.project_management.api.desktop.financials.commands.update_cost_item import FinancialUpdateCommand
from src.core.modules.project_management.api.desktop.financials.builders.option_builder import (
    build_cost_type_options,
    build_project_options,
    build_task_options,
)
from src.core.modules.project_management.api.desktop.financials.builders.forecast_builder import (
    build_forecast_dto,
)
from src.core.modules.project_management.api.desktop.financials.builders.commitment_builder import (
    build_commitment_summary_dto,
)
from src.core.modules.project_management.api.desktop.financials.builders.baseline_variance_builder import (
    build_baseline_variance,
)
from src.core.modules.project_management.api.desktop.financials.serializers.cost_item_serializer import serialize_cost_item
from src.core.modules.project_management.api.desktop.financials.serializers.snapshot_serializer import (
    empty_snapshot,
    serialize_snapshot,
)
from src.core.modules.project_management.api.desktop.financials.serializers.procurement_serializer import serialize_requisition
from src.core.modules.project_management.api.desktop.financials.utils.cost_type_utils import coerce_cost_type


class ProjectManagementFinancialsDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        cost_service: CostService | None = None,
        finance_service: FinanceService | None = None,
        forecast_service=None,
        procurement_service: object | None = None,
        baseline_service: BaselineService | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._cost_service = cost_service
        self._finance_service = finance_service
        self._forecast_service = forecast_service
        self._procurement_service = procurement_service
        self._baseline_service = baseline_service

    def list_projects(self) -> tuple[FinancialProjectOptionDescriptor, ...]:
        return build_project_options(self._project_service)

    def list_cost_types(self) -> tuple[FinancialCostTypeDescriptor, ...]:
        return build_cost_type_options()

    def list_tasks(self, project_id: str) -> tuple[FinancialTaskOptionDescriptor, ...]:
        return build_task_options(project_id, self._task_service)

    def list_cost_items(self, project_id: str) -> tuple[FinancialCostItemDto, ...]:
        if self._cost_service is None or not project_id:
            return ()
        task_lookup = {o.value: o.label for o in self.list_tasks(project_id)}
        items = sorted(
            self._cost_service.list_cost_items_for_project(project_id),
            key=lambda i: (i.incurred_date or date.max, (i.description or "").casefold()),
        )
        return tuple(serialize_cost_item(i, task_lookup=task_lookup) for i in items)

    def create_cost_item(self, command: FinancialCreateCommand) -> FinancialCostItemDto:
        service = self._require_cost_service()
        item = service.add_cost_item(
            command.project_id,
            description=command.description,
            planned_amount=command.planned_amount,
            task_id=command.task_id,
            cost_type=coerce_cost_type(command.cost_type),
            committed_amount=command.committed_amount,
            actual_amount=command.actual_amount,
            incurred_date=command.incurred_date,
            currency_code=command.currency_code,
            code=getattr(command, "code", ""),
        )
        task_lookup = {o.value: o.label for o in self.list_tasks(command.project_id)}
        return serialize_cost_item(item, task_lookup=task_lookup)

    def update_cost_item(self, command: FinancialUpdateCommand) -> FinancialCostItemDto:
        service = self._require_cost_service()
        item = service.update_cost_item(
            command.cost_id,
            description=command.description,
            planned_amount=command.planned_amount,
            committed_amount=command.committed_amount,
            actual_amount=command.actual_amount,
            cost_type=coerce_cost_type(command.cost_type),
            incurred_date=command.incurred_date,
            currency_code=command.currency_code,
            expected_version=command.expected_version,
            code=getattr(command, "code", ""),
        )
        task_lookup = {o.value: o.label for o in self.list_tasks(item.project_id)}
        return serialize_cost_item(item, task_lookup=task_lookup)

    def delete_cost_item(self, cost_id: str) -> None:
        self._require_cost_service().delete_cost_item(cost_id)

    def get_finance_snapshot(self, project_id: str) -> FinancialSnapshotDto:
        if not project_id:
            return empty_snapshot(project_id="")
        if self._finance_service is None:
            return empty_snapshot(
                project_id=project_id,
                notes=("Project management financials desktop API is not connected.",),
            )
        return serialize_snapshot(project_id, self._finance_service.get_finance_snapshot(project_id))

    def get_cost_forecast(
        self,
        project_id: str,
        percent_complete: float = 0.0,
        method: str = "bac_over_cpi",
        threshold_percent: float = 10.0,
    ) -> FinancialForecastDto:
        currency = self._project_currency(project_id)
        return build_forecast_dto(
            project_id, percent_complete, method, threshold_percent,
            cost_service=self._cost_service,
            forecast_service=self._forecast_service,
            currency=currency,
        )

    def get_commitment_summary(self, project_id: str) -> FinancialCommitmentSummaryDto:
        currency = self._project_currency(project_id)
        return build_commitment_summary_dto(
            project_id,
            cost_service=self._cost_service,
            forecast_service=self._forecast_service,
            currency=currency,
        )

    def list_project_requisitions(self, project_id: str) -> tuple[ProjectRequisitionDesktopDto, ...]:
        if not project_id or self._procurement_service is None:
            return ()
        list_fn = getattr(self._procurement_service, "list_requisitions", None)
        if not callable(list_fn):
            return ()
        try:
            all_reqs = list_fn(limit=500)
        except Exception:
            return ()
        project_reqs = [
            r for r in all_reqs
            if getattr(r, "source_reference_type", "") == "project"
            and getattr(r, "source_reference_id", "") == project_id
        ]
        return tuple(
            serialize_requisition(r)
            for r in sorted(project_reqs, key=lambda r: getattr(r, "needed_by_date", None) or date.max)
        )

    def get_project_procurement_commitments(self, project_id: str) -> ProjectProcurementCommitmentSummary:
        requisitions = self.list_project_requisitions(project_id)
        open_statuses = {"DRAFT", "SUBMITTED", "UNDER_REVIEW", "PARTIALLY_SOURCED"}
        approved_statuses = {"APPROVED"}
        closed_statuses = {"FULLY_SOURCED", "CLOSED"}
        cancelled_statuses = {"REJECTED", "CANCELLED"}
        return ProjectProcurementCommitmentSummary(
            project_id=project_id,
            total_requisitions=len(requisitions),
            open_count=sum(1 for r in requisitions if r.status in open_statuses),
            approved_count=sum(1 for r in requisitions if r.status in approved_statuses),
            closed_count=sum(1 for r in requisitions if r.status in closed_statuses),
            cancelled_count=sum(1 for r in requisitions if r.status in cancelled_statuses),
        )

    def build_baseline_variance(self, project_id: str) -> tuple[BaselineVarianceRecordDto, ...]:
        return build_baseline_variance(project_id, self._baseline_service)

    def _project_currency(self, project_id: str) -> str | None:
        if not project_id or self._project_service is None:
            return None
        project = self._project_service.get_project(project_id)
        if project is None:
            return None
        return (getattr(project, "currency", None) or "").strip().upper() or None

    def _require_cost_service(self) -> CostService:
        if self._cost_service is None:
            raise RuntimeError("Project management financials desktop API is not connected.")
        return self._cost_service


__all__ = ["ProjectManagementFinancialsDesktopApi"]
