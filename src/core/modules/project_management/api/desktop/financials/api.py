"""ProjectManagementFinancialsDesktopApi — thin financial desktop facade."""

from __future__ import annotations
from datetime import date

from src.core.modules.project_management.application.financials import (
    FinancialConfigurationService,
    FinanceService,
    ForecastCostService,
    ProjectCommitmentService,
    ProjectCostEntryService,
    ProjectFinanceWorkspaceQuery,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import BaselineService
from src.core.modules.project_management.application.tasks import TaskService

from src.core.modules.project_management.api.desktop.financials.models.commitments import (
    FinancialCommitmentLinePageDto,
    FinancialCommitmentSummaryDto,
)
from src.core.modules.project_management.api.desktop.financials.models.forecasts import FinancialForecastDto
from src.core.modules.project_management.api.desktop.financials.models.baseline_variance import BaselineVarianceRecordDto
from src.core.modules.project_management.api.desktop.financials.models.options import (
    FinancialProjectOptionDescriptor,
    FinancialTaskOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.financials.models.snapshots import FinancialSnapshotDto
from src.core.modules.project_management.api.desktop.financials.models.configuration import (
    FinancialConfigurationWorkspaceDto,
)
from src.core.modules.project_management.api.desktop.financials.commands.cost_entries import (
    FinancialCreateManualActualCommand,
    FinancialDecideActualCommand,
    FinancialPostActualCommand,
    FinancialReverseActualCommand,
    FinancialUpdateActualDraftCommand,
    FinancialVersionedActualCommand,
)
from src.core.modules.project_management.api.desktop.financials.models.cost_entries import (
    FinancialCostCodeOptionDescriptor,
    FinancialCostEntryApprovalDto,
    FinancialCostEntryDto,
    FinancialCostEntryPageDto,
    FinancialManualActualOptionsDto,
)
from src.core.modules.project_management.api.desktop.financials.builders.option_builder import (
    build_project_options,
    build_task_options,
)
from src.core.modules.project_management.api.desktop.financials.builders.forecast_builder import (
    build_forecast_dto,
)
from src.core.modules.project_management.api.desktop.financials.builders.commitment_builder import (
    build_commitment_line_dto,
    build_commitment_summary_dto,
)
from src.core.modules.project_management.api.desktop.financials.builders.baseline_variance_builder import (
    build_baseline_variance,
)
from src.core.modules.project_management.api.desktop.financials.serializers.cost_entry_serializer import (
    serialize_cost_entry,
)
from src.core.modules.project_management.api.desktop.financials.serializers.snapshot_serializer import (
    empty_snapshot,
    serialize_snapshot,
)
from src.core.modules.project_management.api.desktop.financials.serializers.configuration_serializer import (
    serialize_finance_configuration_workspace,
)


class ProjectManagementFinancialsDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        finance_service: FinanceService | None = None,
        forecast_service: ForecastCostService | None = None,
        baseline_service: BaselineService | None = None,
        finance_workspace_query: ProjectFinanceWorkspaceQuery | None = None,
        financial_configuration_service: FinancialConfigurationService | None = None,
        cost_entry_service: ProjectCostEntryService | None = None,
        commitment_service: ProjectCommitmentService | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._finance_service = finance_service
        self._forecast_service = forecast_service
        self._baseline_service = baseline_service
        self._finance_workspace_query = finance_workspace_query
        self._financial_configuration_service = financial_configuration_service
        self._cost_entry_service = cost_entry_service
        self._commitment_service = commitment_service

    def list_projects(self) -> tuple[FinancialProjectOptionDescriptor, ...]:
        return build_project_options(self._project_service)

    def list_tasks(self, project_id: str) -> tuple[FinancialTaskOptionDescriptor, ...]:
        return build_task_options(project_id, self._task_service)

    def get_manual_actual_options(
        self, project_id: str, *, effective_on: date | None = None
    ) -> FinancialManualActualOptionsDto:
        if not project_id:
            return FinancialManualActualOptionsDto()
        if self._financial_configuration_service is None:
            return FinancialManualActualOptionsDto(
                currency_code=self._project_currency(project_id) or ""
            )
        service = self._financial_configuration_service
        profile = service.get_profile(project_id)
        codes = service.list_available_cost_codes(
            project_id, effective_on=effective_on
        )
        return FinancialManualActualOptionsDto(
            currency_code=profile.currency_code,
            cost_codes=tuple(
                FinancialCostCodeOptionDescriptor(
                    value=code.id,
                    label=f"{code.code} - {code.name}",
                )
                for code in codes
            ),
        )

    def list_cost_entries(
        self,
        project_id: str,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> FinancialCostEntryPageDto:
        if not project_id or self._cost_entry_service is None:
            return FinancialCostEntryPageDto(offset=offset, limit=limit)
        entries, total = self._cost_entry_service.list_for_project(
            project_id, status=status, offset=offset, limit=limit
        )
        return FinancialCostEntryPageDto(
            items=tuple(serialize_cost_entry(entry) for entry in entries),
            total=total,
            offset=offset,
            limit=limit,
        )

    def create_manual_actual(
        self, command: FinancialCreateManualActualCommand
    ) -> FinancialCostEntryDto:
        entry = self._require_cost_entry_service().create_manual_entry(
            project_id=command.project_id,
            command_id=command.command_id,
            description=command.description,
            amount=command.amount,
            currency_code=command.currency_code,
            transaction_date=command.transaction_date,
            cost_code_id=command.cost_code_id,
            entry_kind=command.entry_kind,
            task_id=command.task_id,
            resource_id=command.resource_id,
        )
        return serialize_cost_entry(entry)

    def update_actual_draft(
        self, command: FinancialUpdateActualDraftCommand
    ) -> FinancialCostEntryDto:
        entry = self._require_cost_entry_service().update_draft(
            command.entry_id,
            expected_version=command.expected_version,
            description=command.description,
            amount=command.amount,
            currency_code=command.currency_code,
            transaction_date=command.transaction_date,
            cost_code_id=command.cost_code_id,
            task_id=command.task_id,
            resource_id=command.resource_id,
        )
        return serialize_cost_entry(entry)

    def delete_actual_draft(self, command: FinancialVersionedActualCommand) -> None:
        self._require_cost_entry_service().delete_draft(
            command.entry_id, expected_version=command.expected_version
        )

    def submit_actual(
        self, command: FinancialVersionedActualCommand
    ) -> FinancialCostEntryDto:
        return serialize_cost_entry(
            self._require_cost_entry_service().submit(
                command.entry_id, expected_version=command.expected_version
            )
        )

    def approve_actual(
        self, command: FinancialDecideActualCommand
    ) -> FinancialCostEntryApprovalDto:
        result = self._require_cost_entry_service().approve(
            command.entry_id,
            expected_version=command.expected_version,
            notes=command.notes,
        )
        return FinancialCostEntryApprovalDto(
            outcome=result.outcome.value,
            entry_id=result.entry_id,
            project_id=result.project_id,
            status=result.status.value,
            row_version=result.row_version,
            approval_request_id=result.approval_request_id or "",
        )

    def reject_actual(
        self, command: FinancialDecideActualCommand
    ) -> FinancialCostEntryDto:
        return serialize_cost_entry(
            self._require_cost_entry_service().reject(
                command.entry_id,
                expected_version=command.expected_version,
                notes=command.notes,
            )
        )

    def post_actual(self, command: FinancialPostActualCommand) -> FinancialCostEntryDto:
        return serialize_cost_entry(
            self._require_cost_entry_service().post(
                command.entry_id,
                expected_version=command.expected_version,
                posting_date=command.posting_date,
                exchange_rate=command.exchange_rate,
                exchange_rate_date=command.exchange_rate_date,
                exchange_rate_source=command.exchange_rate_source,
                exchange_rate_captured_at=command.exchange_rate_captured_at,
            )
        )

    def reverse_actual(
        self, command: FinancialReverseActualCommand
    ) -> FinancialCostEntryDto:
        return serialize_cost_entry(
            self._require_cost_entry_service().reverse(
                command.entry_id,
                expected_version=command.expected_version,
                command_id=command.command_id,
                posting_date=command.posting_date,
                reason=command.reason,
            )
        )

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
            forecast_service=self._require_forecast_service(),
            currency=currency,
        )

    def get_commitment_summary(self, project_id: str) -> FinancialCommitmentSummaryDto:
        currency = self._project_currency(project_id)
        return build_commitment_summary_dto(
            project_id,
            forecast_service=self._require_forecast_service(),
            currency=currency,
        )

    def list_commitments(
        self, project_id: str, *, offset: int = 0, limit: int = 50
    ) -> FinancialCommitmentLinePageDto:
        if not project_id or self._commitment_service is None:
            return FinancialCommitmentLinePageDto(offset=offset, limit=limit)
        lines, total = self._commitment_service.list_for_project(
            project_id, offset=offset, limit=limit
        )
        return FinancialCommitmentLinePageDto(
            items=tuple(build_commitment_line_dto(line) for line in lines),
            total=total,
            offset=offset,
            limit=limit,
        )

    def build_baseline_variance(self, project_id: str) -> tuple[BaselineVarianceRecordDto, ...]:
        return build_baseline_variance(project_id, self._baseline_service)

    def get_configuration_workspace(
        self,
        project_id: str,
        *,
        budget_line_page: int = 1,
        rate_line_page: int = 1,
        planned_cost_line_page: int = 1,
        page_size: int = 50,
    ) -> FinancialConfigurationWorkspaceDto:
        if not project_id or self._finance_workspace_query is None:
            return FinancialConfigurationWorkspaceDto()
        return serialize_finance_configuration_workspace(
            self._finance_workspace_query.get(
                project_id,
                budget_line_page=budget_line_page,
                rate_line_page=rate_line_page,
                planned_cost_line_page=planned_cost_line_page,
                page_size=page_size,
            )
        )

    def _project_currency(self, project_id: str) -> str | None:
        if not project_id or self._financial_configuration_service is None:
            return None
        profile = self._financial_configuration_service.get_profile(project_id)
        return str(profile.currency_code or "").strip().upper() or None

    def _require_cost_entry_service(self) -> ProjectCostEntryService:
        if self._cost_entry_service is None:
            raise RuntimeError("Project cost-entry service is not connected.")
        return self._cost_entry_service

    def _require_financial_configuration_service(
        self,
    ) -> FinancialConfigurationService:
        if self._financial_configuration_service is None:
            raise RuntimeError("Project financial configuration service is not connected.")
        return self._financial_configuration_service

    def _require_forecast_service(self) -> ForecastCostService:
        if self._forecast_service is None:
            raise RuntimeError("Project management forecast service is not connected.")
        return self._forecast_service


__all__ = ["ProjectManagementFinancialsDesktopApi"]
