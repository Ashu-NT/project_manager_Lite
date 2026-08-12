"""ProjectManagementFinancialsDesktopApi — thin financial desktop facade."""

from __future__ import annotations
from datetime import date

from src.core.modules.project_management.application.financials import (
    FinancialConfigurationService,
    FinancialChangeService,
    FinanceService,
    ForecastVersionService,
    ProjectCommitmentService,
    ProjectBillingPreparationService,
    ProjectBillingProfileService,
    ProjectCostEntryService,
    ProjectFinanceWorkspaceQuery,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import BaselineService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.modules.project_management.infrastructure.reporting.api import (
    generate_excel_report,
    generate_pdf_report,
)

from src.core.modules.project_management.api.desktop.financials.models.commitments import (
    FinancialCommitmentLinePageDto,
    FinancialCommitmentSummaryDto,
)
from src.core.modules.project_management.api.desktop.financials.models.forecasts import FinancialForecastDto
from src.core.modules.project_management.api.desktop.financials.models.lifecycle import (
    FinancialBaselineVarianceDto,
    FinancialChangeDto,
    FinancialChangeImpactDto,
    FinancialForecastLineDto,
    FinancialForecastVersionDto,
)
from src.core.modules.project_management.api.desktop.financials.models.options import (
    FinancialProjectOptionDescriptor,
    FinancialTaskOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.financials.models.snapshots import FinancialSnapshotDto
from src.core.modules.project_management.api.desktop.financials.models.configuration import (
    FinancialConfigurationWorkspaceDto,
)
from src.core.modules.project_management.api.desktop.financials.models.billing import (
    FinancialBillingPreparationDto,
    FinancialBillingPreparationLineDto,
    FinancialBillingProfileDto,
    FinancialBillingScheduleLineDto,
    FinancialBillingWorkspaceDto,
)
from src.core.modules.project_management.api.desktop.financials.commands.cost_entries import (
    FinancialCreateManualActualCommand,
    FinancialDecideActualCommand,
    FinancialPostActualCommand,
    FinancialReverseActualCommand,
    FinancialUpdateActualDraftCommand,
    FinancialVersionedActualCommand,
)
from src.core.modules.project_management.api.desktop.financials.commands.billing import (
    FinancialActivateBillingProfileCommand,
    FinancialAddApprovedTimeBillingSourceCommand,
    FinancialAddBillingScheduleLineCommand,
    FinancialAddCostPlusBillingSourceCommand,
    FinancialAddFixedPriceBillingSourceCommand,
    FinancialCreateBillingPreparationCommand,
    FinancialCreateBillingProfileCommand,
    FinancialMarkBillingScheduleLineReadyCommand,
    FinancialVersionedBillingPreparationCommand,
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
    build_baseline_variance_workspace,
)
from src.core.modules.project_management.api.desktop.financials.serializers.lifecycle_serializer import (
    serialize_financial_change,
    serialize_financial_change_impact,
    serialize_forecast_line,
    serialize_forecast_version,
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
from src.core.modules.project_management.api.desktop.financials.serializers.billing_serializer import (
    serialize_billing_preparation,
    serialize_billing_preparation_line,
    serialize_billing_profile,
    serialize_billing_schedule_line,
)


class ProjectManagementFinancialsDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        finance_service: FinanceService | None = None,
        baseline_service: BaselineService | None = None,
        finance_workspace_query: ProjectFinanceWorkspaceQuery | None = None,
        financial_configuration_service: FinancialConfigurationService | None = None,
        cost_entry_service: ProjectCostEntryService | None = None,
        commitment_service: ProjectCommitmentService | None = None,
        forecast_version_service: ForecastVersionService | None = None,
        financial_change_service: FinancialChangeService | None = None,
        billing_profile_service: ProjectBillingProfileService | None = None,
        billing_preparation_service: ProjectBillingPreparationService | None = None,
        reporting_service: ReportingService | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._finance_service = finance_service
        self._baseline_service = baseline_service
        self._finance_workspace_query = finance_workspace_query
        self._financial_configuration_service = financial_configuration_service
        self._cost_entry_service = cost_entry_service
        self._commitment_service = commitment_service
        self._forecast_version_service = forecast_version_service
        self._financial_change_service = financial_change_service
        self._billing_profile_service = billing_profile_service
        self._billing_preparation_service = billing_preparation_service
        self._reporting_service = reporting_service

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
    ) -> FinancialForecastDto:
        currency = self._project_currency(project_id)
        return build_forecast_dto(
            project_id,
            snapshot=self._require_finance_service().get_finance_snapshot(project_id),
            currency=currency,
        )

    def get_commitment_summary(self, project_id: str) -> FinancialCommitmentSummaryDto:
        currency = self._project_currency(project_id)
        return build_commitment_summary_dto(
            project_id,
            snapshot=self._require_finance_service().get_finance_snapshot(project_id),
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

    def list_forecast_versions(
        self, project_id: str
    ) -> tuple[FinancialForecastVersionDto, ...]:
        if not project_id or self._forecast_version_service is None:
            return ()
        return tuple(
            serialize_forecast_version(item)
            for item in self._forecast_version_service.list_forecasts(project_id)
        )

    def list_forecast_lines(
        self, project_id: str, forecast_id: str
    ) -> tuple[FinancialForecastLineDto, ...]:
        if not project_id or not forecast_id or self._forecast_version_service is None:
            return ()
        versions = self._forecast_version_service.list_forecasts(project_id)
        if not any(item.id == forecast_id for item in versions):
            return ()
        return tuple(
            serialize_forecast_line(item)
            for item in self._forecast_version_service.list_lines(forecast_id)
        )

    def list_financial_changes(
        self, project_id: str
    ) -> tuple[FinancialChangeDto, ...]:
        if not project_id or self._financial_change_service is None:
            return ()
        return tuple(
            serialize_financial_change(item)
            for item in self._financial_change_service.list_changes(project_id)
        )

    def list_financial_change_impacts(
        self, project_id: str, change_id: str
    ) -> tuple[FinancialChangeImpactDto, ...]:
        if not project_id or not change_id or self._financial_change_service is None:
            return ()
        changes = self._financial_change_service.list_changes(project_id)
        if not any(item.id == change_id for item in changes):
            return ()
        return tuple(
            serialize_financial_change_impact(item)
            for item in self._financial_change_service.list_impacts(change_id)
        )

    def get_baseline_variance(
        self, project_id: str, baseline_id: str | None = None
    ) -> FinancialBaselineVarianceDto:
        return build_baseline_variance_workspace(
            project_id,
            selected_baseline_id=baseline_id,
            baseline_service=self._baseline_service,
        )

    def export_financial_report(
        self,
        project_id: str,
        output_path: str,
        *,
        report_format: str,
        baseline_id: str | None = None,
    ) -> str:
        if self._reporting_service is None:
            raise RuntimeError("Project management reporting service is not connected.")
        if report_format == "xlsx":
            result = generate_excel_report(
                self._reporting_service,
                project_id,
                output_path,
                finance_service=self._require_finance_service(),
                baseline_id=baseline_id or None,
            )
        elif report_format == "pdf":
            result = generate_pdf_report(
                self._reporting_service,
                project_id,
                output_path,
                finance_service=self._require_finance_service(),
                baseline_id=baseline_id or None,
            )
        else:
            raise ValueError("Financial report format must be 'xlsx' or 'pdf'.")
        return str(result)

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

    def get_billing_workspace(
        self, project_id: str, *, preparation_page: int = 1, page_size: int = 50
    ) -> FinancialBillingWorkspaceDto:
        if (
            not project_id
            or self._billing_profile_service is None
            or self._billing_preparation_service is None
        ):
            return FinancialBillingWorkspaceDto()
        profile = self._billing_profile_service.get_profile(project_id)
        schedule = self._billing_profile_service.list_schedule(project_id) if profile else []
        page = max(1, int(preparation_page))
        bounded_size = max(1, min(int(page_size), 200))
        if profile:
            preparations, preparation_total = (
                self._billing_preparation_service.list_preparations(
                    project_id,
                    offset=(page - 1) * bounded_size,
                    limit=bounded_size,
                )
            )
            latest_events = self._billing_preparation_service.list_latest_external_events(
                project_id, tuple(item.id for item in preparations)
            )
        else:
            preparations, preparation_total, latest_events = [], 0, {}
        preparation_rows = [
            serialize_billing_preparation(
                preparation, latest_external_event=latest_events.get(preparation.id)
            )
            for preparation in preparations
        ]
        return FinancialBillingWorkspaceDto(
            profile=serialize_billing_profile(profile),
            schedule_lines=tuple(
                serialize_billing_schedule_line(line) for line in schedule
            ),
            preparations=tuple(preparation_rows),
            preparation_page=page,
            preparation_page_size=bounded_size,
            preparation_total=preparation_total,
        )

    def create_billing_profile(
        self, command: FinancialCreateBillingProfileCommand
    ) -> FinancialBillingProfileDto:
        profile = self._require_billing_profile_service().create_profile(
            command.project_id,
            contract_reference=command.contract_reference,
            contract_value=command.contract_value,
            customer_party_id=command.customer_party_id,
            external_customer_reference=command.external_customer_reference,
            purchase_order_reference=command.purchase_order_reference,
            cost_plus_markup_percent=command.cost_plus_markup_percent,
            payment_terms_days=command.payment_terms_days,
            retention_years=command.retention_years,
        )
        return serialize_billing_profile(profile)

    def activate_billing_profile(
        self, command: FinancialActivateBillingProfileCommand
    ) -> FinancialBillingProfileDto:
        profile = self._require_billing_profile_service().activate_profile(
            command.project_id, expected_row_version=command.expected_version
        )
        return serialize_billing_profile(profile)

    def add_billing_schedule_line(
        self, command: FinancialAddBillingScheduleLineCommand
    ) -> FinancialBillingScheduleLineDto:
        line = self._require_billing_profile_service().add_schedule_line(
            command.project_id,
            name=command.name,
            amount=command.amount,
            due_date=command.due_date,
            task_id=command.task_id,
            acceptance_reference=command.acceptance_reference,
        )
        return serialize_billing_schedule_line(line)

    def mark_billing_schedule_line_ready(
        self, command: FinancialMarkBillingScheduleLineReadyCommand
    ) -> FinancialBillingScheduleLineDto:
        line = self._require_billing_profile_service().mark_schedule_line_ready(
            command.line_id, expected_row_version=command.expected_version
        )
        return serialize_billing_schedule_line(line)

    def create_billing_preparation(
        self, command: FinancialCreateBillingPreparationCommand
    ) -> FinancialBillingPreparationDto:
        preparation = self._require_billing_preparation_service().create_preparation(
            command.project_id,
            preparation_number=command.preparation_number,
            period_start=command.period_start,
            period_end=command.period_end,
            idempotency_key=command.idempotency_key,
            correction_of_preparation_id=command.correction_of_preparation_id,
        )
        return serialize_billing_preparation(preparation)

    def add_fixed_price_billing_source(
        self, command: FinancialAddFixedPriceBillingSourceCommand
    ) -> FinancialBillingPreparationLineDto:
        line = self._require_billing_preparation_service().add_fixed_price_source(
            command.preparation_id,
            schedule_line_id=command.schedule_line_id,
            expected_row_version=command.expected_version,
        )
        return serialize_billing_preparation_line(line)

    def add_approved_time_billing_source(
        self, command: FinancialAddApprovedTimeBillingSourceCommand
    ) -> FinancialBillingPreparationLineDto:
        line = self._require_billing_preparation_service().add_approved_time_source(
            command.preparation_id,
            time_entry_id=command.time_entry_id,
            expected_row_version=command.expected_version,
        )
        return serialize_billing_preparation_line(line)

    def add_cost_plus_billing_source(
        self, command: FinancialAddCostPlusBillingSourceCommand
    ) -> FinancialBillingPreparationLineDto:
        line = self._require_billing_preparation_service().add_cost_plus_source(
            command.preparation_id,
            cost_entry_id=command.cost_entry_id,
            expected_row_version=command.expected_version,
        )
        return serialize_billing_preparation_line(line)

    def submit_billing_preparation(
        self, command: FinancialVersionedBillingPreparationCommand
    ) -> FinancialBillingPreparationDto:
        preparation = self._require_billing_preparation_service().submit_preparation(
            command.preparation_id, expected_row_version=command.expected_version
        )
        return serialize_billing_preparation(preparation)

    def request_billing_delivery(
        self, command: FinancialVersionedBillingPreparationCommand
    ) -> FinancialBillingPreparationDto:
        # request_delivery() returns the outbound project_billing_preparation.v1
        # payload for a future Accounting publisher/worker to transmit -- that
        # payload is not surfaced here. Only PM's own preparation-state DTO is
        # returned, matching every other command on this facade; PM requests
        # delivery of its own evidence, it does not itself deliver or record
        # what Accounting did with it (see record_external_outcome, which is
        # deliberately not exposed on this desktop surface).
        service = self._require_billing_preparation_service()
        service.request_delivery(
            command.preparation_id, expected_row_version=command.expected_version
        )
        preparation = service.get_preparation(command.preparation_id)
        return serialize_billing_preparation(preparation)

    def _project_currency(self, project_id: str) -> str | None:
        if not project_id or self._financial_configuration_service is None:
            return None
        profile = self._financial_configuration_service.get_profile(project_id)
        return str(profile.currency_code or "").strip().upper() or None

    def _require_cost_entry_service(self) -> ProjectCostEntryService:
        if self._cost_entry_service is None:
            raise RuntimeError("Project cost-entry service is not connected.")
        return self._cost_entry_service

    def _require_billing_profile_service(self) -> ProjectBillingProfileService:
        if self._billing_profile_service is None:
            raise RuntimeError("Project billing profile service is not connected.")
        return self._billing_profile_service

    def _require_billing_preparation_service(self) -> ProjectBillingPreparationService:
        if self._billing_preparation_service is None:
            raise RuntimeError("Project billing preparation service is not connected.")
        return self._billing_preparation_service

    def _require_financial_configuration_service(
        self,
    ) -> FinancialConfigurationService:
        if self._financial_configuration_service is None:
            raise RuntimeError("Project financial configuration service is not connected.")
        return self._financial_configuration_service

    def _require_finance_service(self) -> FinanceService:
        if self._finance_service is None:
            raise RuntimeError("Project management finance service is not connected.")
        return self._finance_service


__all__ = ["ProjectManagementFinancialsDesktopApi"]
