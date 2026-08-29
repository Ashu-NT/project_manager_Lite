"""ProjectManagementFinancialsDesktopApi — thin financial desktop facade."""

from __future__ import annotations
from datetime import date

from src.core.modules.project_management.application.financials import (
    FinancialConfigurationService,
    FinanceService,
    ProjectCommitmentService,
    ProjectBillingPreparationService,
    ProjectBillingProfileService,
    ProjectCostEntryService,
    ProjectFinanceWorkspaceQuery,
    ProjectFinancePerformanceQuery,
)
from src.core.modules.project_management.contracts.reads.financials.sorting import (
    normalize_cost_entry_sort,
    normalize_commitment_sort,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_budget_facts import (
    FinancePageRequest,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_forecast_facts import (
    ForecastLineRequest,
    ForecastVersionRequest,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_rate_facts import (
    RateCardRequest,
    RateLineRequest,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_change_facts import (
    FinancialChangeImpactQuery,
    FinancialChangeRequestQuery,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_billing_facts import (
    AccountingStatusQuery,
    BillingPreparationLineQuery,
    BillingPreparationQuery,
    BillingScheduleQuery,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_lookup_facts import (
    FinanceLookupPageFacts,
    FinanceLookupQuery,
    ManualActualCostCodeQuery,
)
from src.core.modules.project_management.contracts.reads.pagination import (
    normalize_offset_for_total,
)
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.modules.project_management.infrastructure.reporting.api import (
    generate_excel_report,
    generate_pdf_report,
)

from src.core.modules.project_management.api.desktop.financials.models.commitments import (
    FinancialCommitmentLinePageDto,
    FinancialCommitmentSummaryDto,
)
from src.core.modules.project_management.api.desktop.financials.models.forecasts import FinancialForecastWorkspaceDto
from src.core.modules.project_management.api.desktop.financials.models.options import (
    FinancialLookupOptionDto,
    FinancialLookupPageDto,
)
from src.core.modules.project_management.api.desktop.financials.models.snapshots import (
    FinancialOverviewDto,
)
from src.core.modules.project_management.api.desktop.financials.models.configuration import (
    FinancialConfigurationWorkspaceDto,
)
from src.core.modules.project_management.api.desktop.financials.models.rates import (
    FinancialRateWorkspaceDto,
)
from src.core.modules.project_management.api.desktop.financials.models.changes import (
    FinancialChangeWorkspaceDto,
)
from src.core.modules.project_management.api.desktop.financials.models.billing_workspace import (
    FinancialAccountingStatusPageDto,
    FinancialBillingReadWorkspaceDto,
)
from src.core.modules.project_management.api.desktop.financials.models.billing import (
    FinancialBillingPreparationDto,
    FinancialBillingPreparationLineDto,
    FinancialBillingProfileDto,
    FinancialBillingScheduleLineDto,
    FinancialCommercialProjectionDto,
)
from src.core.modules.project_management.api.desktop.financials.models.performance import (
    FinancialCostPhasingDto,
    FinancialEvmDto,
    FinancialReportsDto,
    FinancialVarianceWorkspaceDto,
)
from src.core.modules.project_management.api.desktop.financials.commands.cost_entries import (
    FinancialCreateManualActualCommand,
    FinancialDecideActualCommand,
    FinancialPostActualCommand,
    FinancialReverseActualCommand,
    FinancialUpdateActualDraftCommand,
    FinancialVersionedActualCommand,
)
from src.core.modules.project_management.api.desktop.financials.commands.configuration import (
    FinancialCreateCostCodeCommand,
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
from src.core.modules.project_management.api.desktop.financials.builders.commitment_builder import (
    build_commitment_line_dto,
    build_commitment_summary_dto,
)
from src.core.modules.project_management.api.desktop.financials.serializers.cost_entry_serializer import (
    serialize_cost_entry,
)
from src.core.modules.project_management.api.desktop.financials.serializers.snapshot_serializer import (
    empty_overview,
    serialize_overview,
)
from src.core.modules.project_management.api.desktop.financials.serializers.configuration_serializer import (
    serialize_finance_budget_workspace,
    serialize_finance_setup_workspace,
    serialize_finance_planned_cost_workspace,
)
from src.core.modules.project_management.api.desktop.financials.serializers.forecast_workspace_serializer import (
    serialize_finance_forecast_workspace,
)
from src.core.modules.project_management.api.desktop.financials.serializers.rate_workspace_serializer import (
    serialize_finance_rate_workspace,
)
from src.core.modules.project_management.api.desktop.financials.serializers.change_workspace_serializer import (
    serialize_finance_change_workspace,
)
from src.core.modules.project_management.api.desktop.financials.serializers.billing_workspace_serializer import (
    serialize_finance_billing_workspace,
)
from src.core.modules.project_management.api.desktop.financials.serializers.accounting_status_serializer import (
    serialize_accounting_status_page,
)
from src.core.modules.project_management.api.desktop.financials.serializers.billing_serializer import (
    serialize_billing_preparation,
    serialize_billing_preparation_line,
    serialize_billing_profile,
    serialize_billing_schedule_line,
    serialize_commercial_projection,
)
from src.core.modules.project_management.api.desktop.financials.serializers.performance_serializer import (
    serialize_cost_phasing,
    serialize_performance_evm,
    serialize_performance_reports,
    serialize_performance_variance,
)


class ProjectManagementFinancialsDesktopApi:
    def __init__(
        self,
        *,
        finance_service: FinanceService | None = None,
        finance_workspace_query: ProjectFinanceWorkspaceQuery | None = None,
        finance_performance_query: ProjectFinancePerformanceQuery | None = None,
        financial_configuration_service: FinancialConfigurationService | None = None,
        cost_entry_service: ProjectCostEntryService | None = None,
        commitment_service: ProjectCommitmentService | None = None,
        billing_profile_service: ProjectBillingProfileService | None = None,
        billing_preparation_service: ProjectBillingPreparationService | None = None,
        reporting_service: ReportingService | None = None,
    ) -> None:
        self._finance_service = finance_service
        self._finance_workspace_query = finance_workspace_query
        self._finance_performance_query = finance_performance_query
        self._financial_configuration_service = financial_configuration_service
        self._cost_entry_service = cost_entry_service
        self._commitment_service = commitment_service
        self._billing_profile_service = billing_profile_service
        self._billing_preparation_service = billing_preparation_service
        self._reporting_service = reporting_service

    def active_scope_ids(self) -> tuple[str, str]:
        query = self._require_finance_workspace_query()
        return query.active_scope_ids()

    def search_finance_projects(
        self, *, search: str = "", page: int = 1, page_size: int = 25
    ) -> FinancialLookupPageDto:
        facts = self._require_finance_workspace_query().search_finance_projects(
            request=FinanceLookupQuery(search=search, page=page, page_size=page_size)
        )
        return _serialize_lookup_page(facts)

    def resolve_finance_project(self, project_id: str) -> FinancialLookupOptionDto | None:
        fact = self._require_finance_workspace_query().resolve_finance_project(project_id)
        return _serialize_lookup_option(fact)

    def search_manual_actual_projects(
        self, *, search: str = "", page: int = 1, page_size: int = 25
    ) -> FinancialLookupPageDto:
        facts = self._require_finance_workspace_query().search_manual_actual_projects(
            request=FinanceLookupQuery(search=search, page=page, page_size=page_size)
        )
        return _serialize_lookup_page(facts)

    def resolve_manual_actual_project(
        self, project_id: str
    ) -> FinancialLookupOptionDto | None:
        fact = self._require_finance_workspace_query().resolve_manual_actual_project(
            project_id
        )
        return _serialize_lookup_option(fact)

    def search_manual_actual_tasks(
        self,
        project_id: str,
        *,
        search: str = "",
        page: int = 1,
        page_size: int = 25,
    ) -> FinancialLookupPageDto:
        facts = self._require_finance_workspace_query().search_manual_actual_tasks(
            project_id,
            request=FinanceLookupQuery(search=search, page=page, page_size=page_size),
        )
        return _serialize_lookup_page(facts)

    def resolve_manual_actual_task(
        self, project_id: str, task_id: str
    ) -> FinancialLookupOptionDto | None:
        fact = self._require_finance_workspace_query().resolve_manual_actual_task(
            project_id, task_id
        )
        return _serialize_lookup_option(fact)

    def search_manual_actual_cost_codes(
        self,
        project_id: str,
        *,
        search: str = "",
        page: int = 1,
        page_size: int = 25,
        effective_on: date | None = None,
    ) -> FinancialLookupPageDto:
        facts = self._require_finance_workspace_query().search_manual_actual_cost_codes(
            project_id,
            request=ManualActualCostCodeQuery(
                search=search,
                page=page,
                page_size=page_size,
                effective_on=effective_on,
            ),
        )
        return _serialize_lookup_page(facts)

    def resolve_manual_actual_cost_code(
        self,
        project_id: str,
        cost_code_id: str,
        *,
        effective_on: date | None = None,
    ) -> FinancialLookupOptionDto | None:
        fact = self._require_finance_workspace_query().resolve_manual_actual_cost_code(
            project_id,
            cost_code_id,
            effective_on=effective_on,
        )
        return _serialize_lookup_option(fact)

    def get_manual_actual_defaults(
        self, project_id: str
    ) -> FinancialManualActualOptionsDto:
        if not project_id:
            return FinancialManualActualOptionsDto()
        defaults = self._require_finance_workspace_query().get_manual_actual_defaults(
            project_id
        )
        return FinancialManualActualOptionsDto(
            currency_code=defaults.currency_code,
        )

    def create_cost_code(
        self, command: FinancialCreateCostCodeCommand
    ) -> FinancialCostCodeOptionDescriptor:
        service = self._require_financial_configuration_service()
        cost_code = service.create_cost_code(
            code=command.code,
            name=command.name,
            description=command.description,
            available_to_project_id=command.project_id,
        )
        return FinancialCostCodeOptionDescriptor(
            value=cost_code.id,
            label=f"{cost_code.code} - {cost_code.name}",
        )

    def list_cost_entries(
        self,
        project_id: str,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
        sort_key: str = "metaText",
        sort_direction: str = "desc",
    ) -> FinancialCostEntryPageDto:
        sort = normalize_cost_entry_sort(key=sort_key, direction=sort_direction)
        if not project_id or self._cost_entry_service is None:
            return FinancialCostEntryPageDto(
                offset=offset,
                limit=limit,
                sort_key=sort.key,
                sort_direction=sort.direction.value,
            )
        entries, total = self._cost_entry_service.list_for_project(
            project_id,
            status=status,
            offset=offset,
            limit=limit,
            sort_key=sort.key,
            sort_direction=sort.direction.value,
        )
        normalized_offset = normalize_offset_for_total(
            offset=offset,
            limit=limit,
            total=total,
        )
        if normalized_offset != offset:
            entries, total = self._cost_entry_service.list_for_project(
                project_id,
                status=status,
                offset=normalized_offset,
                limit=limit,
                sort_key=sort.key,
                sort_direction=sort.direction.value,
            )
        return FinancialCostEntryPageDto(
            items=tuple(serialize_cost_entry(entry) for entry in entries),
            total=total,
            offset=normalized_offset,
            limit=limit,
            sort_key=sort.key,
            sort_direction=sort.direction.value,
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

    def get_finance_overview(self, project_id: str) -> FinancialOverviewDto:
        if not project_id or self._finance_service is None:
            return empty_overview(project_id=project_id)
        return serialize_overview(
            project_id,
            self._finance_service.get_finance_overview(project_id),
        )

    def get_commitment_summary(self, project_id: str) -> FinancialCommitmentSummaryDto:
        facts = self._require_finance_service().get_finance_overview(project_id)
        return build_commitment_summary_dto(
            project_id,
            facts=facts,
        )

    def list_commitments(
        self,
        project_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
        sort_key: str = "metaText",
        sort_direction: str = "desc",
    ) -> FinancialCommitmentLinePageDto:
        sort = normalize_commitment_sort(key=sort_key, direction=sort_direction)
        if not project_id or self._commitment_service is None:
            return FinancialCommitmentLinePageDto(
                offset=offset,
                limit=limit,
                sort_key=sort.key,
                sort_direction=sort.direction.value,
            )
        lines, total = self._commitment_service.list_for_project(
            project_id,
            offset=offset,
            limit=limit,
            sort_key=sort.key,
            sort_direction=sort.direction.value,
        )
        normalized_offset = normalize_offset_for_total(
            offset=offset,
            limit=limit,
            total=total,
        )
        if normalized_offset != offset:
            lines, total = self._commitment_service.list_for_project(
                project_id,
                offset=normalized_offset,
                limit=limit,
                sort_key=sort.key,
                sort_direction=sort.direction.value,
            )
        return FinancialCommitmentLinePageDto(
            items=tuple(build_commitment_line_dto(line) for line in lines),
            total=total,
            offset=normalized_offset,
            limit=limit,
            sort_key=sort.key,
            sort_direction=sort.direction.value,
        )

    def get_forecast_workspace(
        self,
        project_id: str,
        *,
        selected_forecast_id: str = "",
        version_page: int = 1,
        line_page: int = 1,
        page_size: int = 50,
        version_sort_key: str = "revision",
        version_sort_direction: str = "desc",
        line_sort_key: str = "title",
        line_sort_direction: str = "asc",
        version_search: str = "",
        version_status: str = "",
        generation_mode: str = "",
        line_search: str = "",
        line_source_type: str = "",
    ) -> FinancialForecastWorkspaceDto:
        if not project_id or self._finance_workspace_query is None:
            return FinancialForecastWorkspaceDto()
        facts = self._finance_workspace_query.get_forecast_workspace(
            project_id,
            selected_forecast_id=selected_forecast_id,
            version_request=ForecastVersionRequest(
                page=version_page,
                page_size=page_size,
                sort_key=version_sort_key,
                sort_direction=version_sort_direction,
                search=version_search,
                status=version_status,
                generation_mode=generation_mode,
            ),
            line_request=ForecastLineRequest(
                page=line_page,
                page_size=page_size,
                sort_key=line_sort_key,
                sort_direction=line_sort_direction,
                search=line_search,
                source_type=line_source_type,
            ),
        )
        return serialize_finance_forecast_workspace(
            facts,
            version_search=version_search,
            version_status=version_status,
            generation_mode=generation_mode,
            line_search=line_search,
            line_source_type=line_source_type,
        )

    def get_rate_workspace(
        self,
        project_id: str,
        *,
        selected_rate_card_id: str = "",
        card_page: int = 1,
        line_page: int = 1,
        page_size: int = 50,
        card_sort_key: str = "title",
        card_sort_direction: str = "asc",
        line_sort_key: str = "title",
        line_sort_direction: str = "asc",
        card_search: str = "",
        card_scope: str = "",
        card_status: str = "",
        line_search: str = "",
        line_rate_type: str = "",
        line_status: str = "",
        line_effective_status: str = "",
        as_of: date | None = None,
    ) -> FinancialRateWorkspaceDto:
        if not project_id or self._finance_workspace_query is None:
            return FinancialRateWorkspaceDto()
        facts = self._finance_workspace_query.get_rate_workspace(
            project_id,
            selected_rate_card_id=selected_rate_card_id,
            card_request=RateCardRequest(
                page=card_page,
                page_size=page_size,
                sort_key=card_sort_key,
                sort_direction=card_sort_direction,
                search=card_search,
                scope=card_scope,
                status=card_status,
            ),
            line_request=RateLineRequest(
                page=line_page,
                page_size=page_size,
                sort_key=line_sort_key,
                sort_direction=line_sort_direction,
                search=line_search,
                rate_type=line_rate_type,
                status=line_status,
                effective_status=line_effective_status,
                as_of=as_of,
            ),
        )
        return serialize_finance_rate_workspace(
            facts,
            card_search=card_search,
            card_scope=card_scope,
            card_status=card_status,
            line_search=line_search,
            line_rate_type=line_rate_type,
            line_status=line_status,
            line_effective_status=line_effective_status,
            as_of=as_of,
        )

    def get_accounting_statuses(
        self,
        project_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        sort_key: str = "metaText",
        sort_direction: str = "desc",
        search: str = "",
    ) -> FinancialAccountingStatusPageDto:
        if not project_id:
            return FinancialAccountingStatusPageDto()
        facts = self._require_finance_workspace_query().get_accounting_statuses(
            project_id,
            request=AccountingStatusQuery(
                page=page,
                page_size=page_size,
                sort_key=sort_key,
                sort_direction=sort_direction,
                search=search,
            ),
        )
        return serialize_accounting_status_page(facts)

    def get_billing_read_workspace(
        self,
        project_id: str,
        *,
        selected_preparation_id: str = "",
        schedule_page: int = 1,
        preparation_page: int = 1,
        line_page: int = 1,
        page_size: int = 50,
        schedule_sort_key: str = "supportingText",
        schedule_sort_direction: str = "asc",
        preparation_sort_key: str = "metaText",
        preparation_sort_direction: str = "desc",
        line_sort_key: str = "metaText",
        line_sort_direction: str = "asc",
        schedule_search: str = "",
        schedule_status: str = "",
        schedule_source_state: str = "",
        preparation_search: str = "",
        preparation_status: str = "",
        preparation_method: str = "",
        preparation_approval_status: str = "",
        preparation_delivery_state: str = "",
        preparation_correction_state: str = "",
        line_search: str = "",
        line_source_type: str = "",
        line_source_state: str = "",
    ) -> FinancialBillingReadWorkspaceDto:
        if not project_id or self._finance_workspace_query is None:
            return FinancialBillingReadWorkspaceDto()
        facts = self._finance_workspace_query.get_billing_read_workspace(
            project_id,
            selected_preparation_id=selected_preparation_id,
            schedule_request=BillingScheduleQuery(
                page=schedule_page,
                page_size=page_size,
                sort_key=schedule_sort_key,
                sort_direction=schedule_sort_direction,
                search=schedule_search,
                status=schedule_status,
                source_state=schedule_source_state,
            ),
            preparation_request=BillingPreparationQuery(
                page=preparation_page,
                page_size=page_size,
                sort_key=preparation_sort_key,
                sort_direction=preparation_sort_direction,
                search=preparation_search,
                status=preparation_status,
                billing_method=preparation_method,
                approval_status=preparation_approval_status,
                delivery_state=preparation_delivery_state,
                correction_state=preparation_correction_state,
            ),
            line_request=BillingPreparationLineQuery(
                page=line_page,
                page_size=page_size,
                sort_key=line_sort_key,
                sort_direction=line_sort_direction,
                search=line_search,
                source_type=line_source_type,
                source_state=line_source_state,
            ),
        )
        return serialize_finance_billing_workspace(
            facts,
            schedule_search=schedule_search,
            schedule_status=schedule_status,
            schedule_source_state=schedule_source_state,
            preparation_search=preparation_search,
            preparation_status=preparation_status,
            preparation_method=preparation_method,
            preparation_approval_status=preparation_approval_status,
            preparation_delivery_state=preparation_delivery_state,
            preparation_correction_state=preparation_correction_state,
            line_search=line_search,
            line_source_type=line_source_type,
            line_source_state=line_source_state,
        )

    def get_change_workspace(
        self,
        project_id: str,
        *,
        selected_change_id: str = "",
        change_page: int = 1,
        impact_page: int = 1,
        page_size: int = 50,
        change_sort_key: str = "metaText",
        change_sort_direction: str = "desc",
        impact_sort_key: str = "metaText",
        impact_sort_direction: str = "asc",
        change_search: str = "",
        change_status: str = "",
        change_approval_status: str = "",
        change_applied_state: str = "",
        impact_search: str = "",
        impact_type: str = "",
        impact_applied_state: str = "",
    ) -> FinancialChangeWorkspaceDto:
        if not project_id or self._finance_workspace_query is None:
            return FinancialChangeWorkspaceDto()
        facts = self._finance_workspace_query.get_change_workspace(
            project_id,
            selected_change_id=selected_change_id,
            change_request=FinancialChangeRequestQuery(
                page=change_page,
                page_size=page_size,
                sort_key=change_sort_key,
                sort_direction=change_sort_direction,
                search=change_search,
                status=change_status,
                approval_status=change_approval_status,
                applied_state=change_applied_state,
            ),
            impact_request=FinancialChangeImpactQuery(
                page=impact_page,
                page_size=page_size,
                sort_key=impact_sort_key,
                sort_direction=impact_sort_direction,
                search=impact_search,
                impact_type=impact_type,
                applied_state=impact_applied_state,
            ),
        )
        return serialize_finance_change_workspace(
            facts,
            change_search=change_search,
            change_status=change_status,
            change_approval_status=change_approval_status,
            change_applied_state=change_applied_state,
            impact_search=impact_search,
            impact_type=impact_type,
            impact_applied_state=impact_applied_state,
        )

    def get_performance_evm(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
        baseline_id: str | None = None,
    ) -> FinancialEvmDto:
        if not project_id or self._finance_performance_query is None:
            return FinancialEvmDto()
        return serialize_performance_evm(
            self._finance_performance_query.get_evm(
                project_id,
                as_of_date=as_of_date,
                baseline_id=baseline_id,
            )
        )

    def get_performance_variance(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
        selected_baseline_id: str | None = None,
    ) -> FinancialVarianceWorkspaceDto:
        if not project_id or self._finance_performance_query is None:
            return FinancialVarianceWorkspaceDto()
        return serialize_performance_variance(
            self._finance_performance_query.get_variance(
                project_id,
                as_of_date=as_of_date,
                selected_baseline_id=selected_baseline_id,
            )
        )

    def get_cost_phasing(
        self,
        project_id: str,
        *,
        date_from: date,
        date_to: date,
        granularity: str = "month",
    ) -> FinancialCostPhasingDto:
        if not project_id or self._finance_performance_query is None:
            return FinancialCostPhasingDto(
                date_from=date_from,
                date_to=date_to,
                granularity=granularity,
            )
        return serialize_cost_phasing(
            self._finance_performance_query.get_cost_phasing(
                project_id,
                date_from=date_from,
                date_to=date_to,
                granularity=granularity,
            )
        )

    def get_performance_reports(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
    ) -> FinancialReportsDto:
        if not project_id or self._finance_performance_query is None:
            return FinancialReportsDto()
        return serialize_performance_reports(
            self._finance_performance_query.get_reports(
                project_id,
                as_of_date=as_of_date,
            )
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

    def get_financial_setup_workspace(
        self, project_id: str
    ) -> FinancialConfigurationWorkspaceDto:
        if not project_id or self._finance_workspace_query is None:
            return FinancialConfigurationWorkspaceDto()
        return serialize_finance_setup_workspace(
            self._finance_workspace_query.get_setup_workspace(project_id)
        )

    def get_budget_workspace(
        self,
        project_id: str,
        *,
        selected_budget_id: str = "",
        version_page: int = 1,
        line_page: int = 1,
        page_size: int = 50,
        version_sort_key: str = "revision",
        version_sort_direction: str = "desc",
        line_sort_key: str = "metaText",
        line_sort_direction: str = "desc",
        search: str = "",
        status: str = "",
    ) -> FinancialConfigurationWorkspaceDto:
        if not project_id or self._finance_workspace_query is None:
            return FinancialConfigurationWorkspaceDto()
        return serialize_finance_budget_workspace(
            self._finance_workspace_query.get_budget_workspace(
                project_id,
                selected_budget_id=selected_budget_id,
                version_request=FinancePageRequest(
                    page=version_page,
                    page_size=page_size,
                    sort_key=version_sort_key,
                    sort_direction=version_sort_direction,
                    search=search,
                    status=status,
                ),
                line_request=FinancePageRequest(
                    page=line_page,
                    page_size=page_size,
                    sort_key=line_sort_key,
                    sort_direction=line_sort_direction,
                    search=search,
                ),
            )
        )

    def get_planned_cost_workspace(
        self,
        project_id: str,
        *,
        selected_version_id: str = "",
        version_page: int = 1,
        line_page: int = 1,
        page_size: int = 50,
        version_sort_key: str = "revision",
        version_sort_direction: str = "desc",
        line_sort_key: str = "title",
        line_sort_direction: str = "asc",
        search: str = "",
        status: str = "",
    ) -> FinancialConfigurationWorkspaceDto:
        if not project_id or self._finance_workspace_query is None:
            return FinancialConfigurationWorkspaceDto()
        return serialize_finance_planned_cost_workspace(
            self._finance_workspace_query.get_planned_cost_workspace(
                project_id,
                selected_version_id=selected_version_id,
                version_request=FinancePageRequest(
                    page=version_page,
                    page_size=page_size,
                    sort_key=version_sort_key,
                    sort_direction=version_sort_direction,
                    search=search,
                    status=status,
                ),
                line_request=FinancePageRequest(
                    page=line_page,
                    page_size=page_size,
                    sort_key=line_sort_key,
                    sort_direction=line_sort_direction,
                    search=search,
                ),
            )
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

    def get_commercial_projection(
        self, project_id: str
    ) -> FinancialCommercialProjectionDto:
        if not project_id or self._reporting_service is None:
            return FinancialCommercialProjectionDto()
        return serialize_commercial_projection(
            self._reporting_service.get_project_commercial_projection(project_id)
        )

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

    def _require_finance_workspace_query(self) -> ProjectFinanceWorkspaceQuery:
        if self._finance_workspace_query is None:
            raise RuntimeError("Project Finance workspace query is not connected.")
        return self._finance_workspace_query


def _serialize_lookup_option(fact) -> FinancialLookupOptionDto | None:
    if fact is None:
        return None
    return FinancialLookupOptionDto(value=fact.id, label=fact.label)


def _serialize_lookup_page(facts: FinanceLookupPageFacts) -> FinancialLookupPageDto:
    return FinancialLookupPageDto(
        items=tuple(
            FinancialLookupOptionDto(value=item.id, label=item.label)
            for item in facts.items
        ),
        total=facts.total,
        page=facts.page,
        page_size=facts.page_size,
        has_more=facts.has_more,
    )


__all__ = ["ProjectManagementFinancialsDesktopApi"]
