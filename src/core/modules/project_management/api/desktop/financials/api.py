"""ProjectManagementFinancialsDesktopApi â€” thin financial desktop facade."""

from __future__ import annotations

from datetime import UTC, date, datetime

from src.core.modules.project_management.api.desktop.financials.models.cost_entries import (
    FinancialCostCodeOptionDescriptor,
    FinancialManualActualOptionsDto,
)
from src.core.modules.project_management.api.desktop.financials.models.options import (
    FinancialLookupOptionDto,
    FinancialLookupPageDto,
)
from src.core.modules.project_management.application.financials import (
    FinanceSnapshotQueryHandler,
    ProjectBillingPreparationQueryHandler,
    ProjectBillingProfileQueryHandler,
    ProjectCommitmentQueryHandler,
    ProjectCostEntryQueryHandler,
    ProjectFinancePerformanceQuery,
    ProjectFinanceWorkspaceQuery,
)
from src.core.modules.project_management.application.financials.analytics.performance.dto.responses.reports import (
    FinancialReportsDto,
)
from src.core.modules.project_management.application.financials.budgets.dto.commands.budget_lifecycle import (
    FinancialCreateBudgetSuccessorCommand,
    FinancialCreateBudgetVersionCommand,
    FinancialUpdateBudgetCommand,
    FinancialVersionedBudgetCommand,
)
from src.core.modules.project_management.application.financials.budgets.dto.commands.budget_lines import (
    FinancialAddBudgetLineCommand,
    FinancialDeleteBudgetLineCommand,
    FinancialUpdateBudgetLineCommand,
)
from src.core.modules.project_management.application.financials.budgets.dto.responses.mutations import (
    FinancialBudgetLineMutationDto,
    FinancialBudgetMutationDto,
)
from src.core.modules.project_management.application.financials.configuration.dto.commands.cost_codes import (
    FinancialChangeCostCodeStatusCommand,
    FinancialCostCodeRestrictionCommand,
    FinancialCreateCostCodeCommand,
    FinancialUpdateCostCodeCommand,
)
from src.core.modules.project_management.application.financials.configuration.dto.commands.financial_profile import (
    FinancialTransitionProfileCommand,
    FinancialUpdateProfileCommand,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.commands.actual_posting import (
    FinancialPostActualCommand,
    FinancialReverseActualCommand,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.commands.actual_review import (
    FinancialDecideActualCommand,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.commands.manual_actuals import (
    FinancialCreateManualActualCommand,
    FinancialUpdateActualDraftCommand,
    FinancialVersionedActualCommand,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.responses.approval import (
    FinancialCostEntryApprovalDto,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.responses.cost_entry import (
    CostEntryResponse,
)
from src.core.modules.project_management.application.financials.financial_changes.dto.commands.change_draft import (
    FinancialCreateChangeCommand,
    FinancialUpdateChangeCommand,
)
from src.core.modules.project_management.application.financials.financial_changes.dto.commands.change_impacts import (
    FinancialChangeImpactCommand,
    FinancialRemoveChangeImpactCommand,
    FinancialUpdateChangeImpactCommand,
)
from src.core.modules.project_management.application.financials.financial_changes.dto.commands.change_submission import (
    FinancialSubmitChangeCommand,
)
from src.core.modules.project_management.application.financials.financial_changes.dto.responses.mutations import (
    FinancialChangeMutationDto,
)
from src.core.modules.project_management.application.financials.forecasts.dto.commands.forecast_generation import (
    FinancialGenerateForecastCommand,
)
from src.core.modules.project_management.application.financials.forecasts.dto.commands.forecast_lifecycle import (
    FinancialVersionedForecastCommand,
)
from src.core.modules.project_management.application.financials.forecasts.dto.responses.mutations import (
    FinancialForecastMutationDto,
)
from src.core.modules.project_management.application.financials.governance.command_boundary import (
    FinanceGovernanceCommandBoundary,
)
from src.core.modules.project_management.application.financials.integration.dto.responses.posting_failures import (
    FinancialPostingFailurePageDto,
)
from src.core.modules.project_management.application.financials.invoicing.dto.commands.billing_preparation import (
    FinancialCreateBillingPreparationCommand,
    FinancialVersionedBillingPreparationCommand,
)
from src.core.modules.project_management.application.financials.invoicing.dto.commands.billing_profile import (
    FinancialActivateBillingProfileCommand,
    FinancialCreateBillingProfileCommand,
)
from src.core.modules.project_management.application.financials.invoicing.dto.commands.billing_schedule import (
    FinancialAddBillingScheduleLineCommand,
    FinancialMarkBillingScheduleLineReadyCommand,
)
from src.core.modules.project_management.application.financials.invoicing.dto.commands.billing_sources import (
    FinancialAddApprovedTimeBillingSourceCommand,
    FinancialAddCostPlusBillingSourceCommand,
    FinancialAddFixedPriceBillingSourceCommand,
    FinancialRemoveDraftBillingLineCommand,
)
from src.core.modules.project_management.application.financials.invoicing.dto.responses.billing import (
    FinancialBillingPreparationLineDto,
    FinancialBillingPreparationResponse,
    FinancialBillingProfileDto,
    FinancialBillingScheduleLineDto,
)
from src.core.modules.project_management.application.financials.rate_cards.dto.commands.rate_cards import (
    FinancialCreateRateCardCommand,
    FinancialUpdateRateCardCommand,
    FinancialVersionedRateCardCommand,
)
from src.core.modules.project_management.application.financials.rate_cards.dto.commands.rate_lines import (
    FinancialAddRateLineCommand,
    FinancialUpdateRateLineCommand,
    FinancialVersionedRateLineCommand,
)
from src.core.modules.project_management.application.financials.rate_cards.dto.responses.mutations import (
    FinancialRateMutationDto,
)
from src.core.modules.project_management.application.financials.revenue.dto.responses.commercial_response import (
    FinancialCommercialProjectionDto,
)
from src.core.modules.project_management.application.reporting import (
    ProfitabilityReportBuilder,
)
from src.core.modules.project_management.contracts.reads.financials.budgets.models.budget_facts import (
    BudgetVersionPageFacts,
    FinanceBudgetWorkspaceFacts,
    FinancePageFacts,
    FinancePageRequest,
)
from src.core.modules.project_management.contracts.reads.financials.configuration.models.setup_facts import (
    FinanceSetupCostCodeQuery,
    FinanceSetupRestrictionQuery,
    FinanceSetupWorkspaceFacts,
)
from src.core.modules.project_management.contracts.reads.financials.financial_changes.models.change_facts import (
    FinanceChangeWorkspaceFacts,
    FinancialChangeImpactQuery,
    FinancialChangeRequestQuery,
)
from src.core.modules.project_management.contracts.reads.financials.forecasts.models.forecast_facts import (
    FinanceForecastWorkspaceFacts,
    ForecastLineRequest,
    ForecastVersionRequest,
)
from src.core.modules.project_management.contracts.reads.financials.integration.models.integration_facts import (
    ApprovedTimePostingFailureQuery,
)
from src.core.modules.project_management.contracts.reads.financials.invoicing.models.billing_facts import (
    AccountingStatusFact,
    AccountingStatusQuery,
    BillingPreparationLineQuery,
    BillingPreparationQuery,
    BillingScheduleQuery,
    BillingSourceQuery,
    BillingSourceOptionFact,
    FinanceBillingWorkspaceFacts,
)
from src.core.modules.project_management.contracts.reads.financials.lookups.models.lookup_facts import (
    FinanceLookupPageFacts,
    FinanceLookupQuery,
    ManualActualCostCodeQuery,
)
from src.core.modules.project_management.contracts.reads.financials.overview.models.overview_facts import (
    FinanceOverviewFacts,
)
from src.core.modules.project_management.contracts.reads.financials.performance.models.performance_facts import (
    CostPhasingFacts,
    PerformanceEvmFact,
    PerformanceVarianceFacts,
)
from src.core.modules.project_management.contracts.reads.financials.planned_costs.models.planned_cost_facts import (
    FinancePlannedCostWorkspaceFacts,
)
from src.core.modules.project_management.contracts.reads.financials.rate_cards.models.rate_facts import (
    FinanceRateWorkspaceFacts,
    RateCardRequest,
    RateLineRequest,
)
from src.core.modules.project_management.contracts.reads.financials.revenue.models.availability import (
    CommercialMetricAvailability,
    CommercialMetricUnavailableReason,
)
from src.core.modules.project_management.contracts.reads.financials.shared.sorting import (
    normalize_commitment_sort,
    normalize_cost_entry_sort,
)
from src.core.modules.project_management.infrastructure.reporting.export_runtime import (
    ProjectReportSources,
    generate_excel_report,
    generate_pdf_report,
)
from src.core.modules.project_management.application.financials.cost.entries.dto.responses.page import CostEntryPage
from src.core.modules.project_management.application.financials.commitments.dto.responses.lines import CommitmentPage
from src.core.platform.common.exceptions import ConfigurationError, ValidationError


class ProjectManagementFinancialsDesktopApi:
    def __init__(
        self,
        *,
        finance_snapshot_query: FinanceSnapshotQueryHandler | None = None,
        finance_workspace_query: ProjectFinanceWorkspaceQuery | None = None,
        finance_performance_query: ProjectFinancePerformanceQuery | None = None,
        finance_governance_commands: FinanceGovernanceCommandBoundary | None = None,
        cost_entry_query: ProjectCostEntryQueryHandler | None = None,
        commitment_query: ProjectCommitmentQueryHandler | None = None,
        billing_profile_query: ProjectBillingProfileQueryHandler | None = None,
        billing_preparation_query: ProjectBillingPreparationQueryHandler | None = None,
        report_sources: ProjectReportSources | None = None,
        profitability_report: ProfitabilityReportBuilder | None = None,
    ) -> None:
        self._finance_snapshot_query = finance_snapshot_query
        self._finance_workspace_query = finance_workspace_query
        self._finance_performance_query = finance_performance_query
        self._finance_governance_commands = finance_governance_commands
        self._cost_entry_query = cost_entry_query
        self._commitment_query = commitment_query
        self._billing_profile_query = billing_profile_query
        self._billing_preparation_query = billing_preparation_query
        self._report_sources = report_sources
        self._profitability_report = profitability_report

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

    def search_rate_resources(
        self,
        project_id: str,
        *,
        search: str = "",
        page: int = 1,
        page_size: int = 25,
    ) -> FinancialLookupPageDto:
        facts = self._require_finance_workspace_query().search_rate_resources(
            project_id,
            request=FinanceLookupQuery(
                search=search, page=page, page_size=page_size
            ),
        )
        return _serialize_lookup_page(facts)

    def search_rate_departments(
        self,
        project_id: str,
        *,
        search: str = "",
        page: int = 1,
        page_size: int = 25,
    ) -> FinancialLookupPageDto:
        facts = self._require_finance_workspace_query().search_rate_departments(
            project_id,
            request=FinanceLookupQuery(
                search=search, page=page, page_size=page_size
            ),
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

    def search_manual_actual_resources(
        self,
        project_id: str,
        *,
        search: str = "",
        page: int = 1,
        page_size: int = 25,
    ) -> FinancialLookupPageDto:
        facts = self._require_finance_workspace_query().search_manual_actual_resources(
            project_id,
            request=FinanceLookupQuery(search=search, page=page, page_size=page_size),
        )
        return _serialize_lookup_page(facts)

    def resolve_manual_actual_resource(
        self, project_id: str, resource_id: str
    ) -> FinancialLookupOptionDto | None:
        fact = self._require_finance_workspace_query().resolve_manual_actual_resource(
            project_id, resource_id
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

    def search_budget_tasks(
        self, project_id: str, *, search: str = "", page: int = 1, page_size: int = 25
    ) -> FinancialLookupPageDto:
        facts = self._require_finance_workspace_query().search_budget_tasks(
            project_id,
            request=FinanceLookupQuery(search=search, page=page, page_size=page_size),
        )
        return _serialize_lookup_page(facts)

    def resolve_budget_task(
        self, project_id: str, task_id: str
    ) -> FinancialLookupOptionDto | None:
        return _serialize_lookup_option(
            self._require_finance_workspace_query().resolve_budget_task(
                project_id, task_id
            )
        )

    def search_budget_cost_codes(
        self, project_id: str, *, search: str = "", page: int = 1, page_size: int = 25
    ) -> FinancialLookupPageDto:
        facts = self._require_finance_workspace_query().search_budget_cost_codes(
            project_id,
            request=ManualActualCostCodeQuery(
                search=search, page=page, page_size=page_size, effective_on=datetime.now(UTC).astimezone().date()
            ),
        )
        return _serialize_lookup_page(facts)

    def resolve_budget_cost_code(
        self, project_id: str, cost_code_id: str
    ) -> FinancialLookupOptionDto | None:
        return _serialize_lookup_option(
            self._require_finance_workspace_query().resolve_budget_cost_code(
                project_id, cost_code_id, effective_on=datetime.now(UTC).astimezone().date()
            )
        )

    def search_financial_change_target_lines(
        self,
        project_id: str,
        change_id: str,
        impact_type: str,
        *,
        search: str = "",
        page: int = 1,
        page_size: int = 25,
    ) -> FinancialLookupPageDto:
        return _serialize_lookup_page(
            self._require_finance_workspace_query().search_financial_change_target_lines(
                project_id,
                change_id,
                impact_type,
                request=FinanceLookupQuery(
                    search=search, page=page, page_size=page_size
                ),
            )
        )

    def resolve_financial_change_target_line(
        self, project_id: str, change_id: str, impact_type: str, line_id: str
    ) -> FinancialLookupOptionDto | None:
        return _serialize_lookup_option(
            self._require_finance_workspace_query().resolve_financial_change_target_line(
                project_id, change_id, impact_type, line_id
            )
        )

    def search_forecast_tasks(
        self, project_id: str, *, search: str = "", page: int = 1, page_size: int = 25
    ) -> FinancialLookupPageDto:
        return _serialize_lookup_page(
            self._require_finance_workspace_query().search_forecast_tasks(
                project_id,
                request=FinanceLookupQuery(search=search, page=page, page_size=page_size),
            )
        )

    def search_forecast_cost_codes(
        self,
        project_id: str,
        *,
        search: str = "",
        page: int = 1,
        page_size: int = 25,
        effective_on: date | None = None,
    ) -> FinancialLookupPageDto:
        return _serialize_lookup_page(
            self._require_finance_workspace_query().search_forecast_cost_codes(
                project_id,
                request=ManualActualCostCodeQuery(
                    search=search,
                    page=page,
                    page_size=page_size,
                    effective_on=effective_on,
                ),
            )
        )

    def search_forecast_risks(
        self, project_id: str, *, search: str = "", page: int = 1, page_size: int = 25
    ) -> FinancialLookupPageDto:
        return _serialize_lookup_page(
            self._require_finance_workspace_query().search_forecast_risks(
                project_id,
                request=FinanceLookupQuery(search=search, page=page, page_size=page_size),
            )
        )

    def search_setup_cost_codes(
        self,
        project_id: str,
        *,
        search: str = "",
        page: int = 1,
        page_size: int = 25,
        assignment_state: str = "",
        active_only: bool = True,
    ) -> FinancialLookupPageDto:
        return _serialize_lookup_page(
            self._require_finance_workspace_query().search_setup_cost_codes(
                project_id,
                request=FinanceLookupQuery(search=search, page=page, page_size=page_size),
                assignment_state=assignment_state,
                active_only=active_only,
            )
        )

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
        commands = self._require_finance_governance_commands()
        cost_code = commands.cost_code(
            lambda service: service.create_cost_code(command),
        )
        return FinancialCostCodeOptionDescriptor(
            value=cost_code.id,
            label=f"{cost_code.code} - {cost_code.name}",
        )

    def update_financial_profile(self, command: FinancialUpdateProfileCommand) -> None:
        self._require_finance_governance_commands().financial_profile(
            lambda service: service.configure_profile(command),
        )

    def transition_financial_profile(
        self, command: FinancialTransitionProfileCommand
    ) -> None:
        self._require_finance_governance_commands().financial_profile(
            lambda service: service.transition_profile(command),
        )

    def update_cost_code(self, command: FinancialUpdateCostCodeCommand) -> None:
        self._require_finance_governance_commands().cost_code(
            lambda service: service.update_cost_code(command)
        )

    def change_cost_code_status(
        self, command: FinancialChangeCostCodeStatusCommand
    ) -> None:
        def mutate(service):
            operation = service.activate_cost_code if command.activate else service.deactivate_cost_code
            return operation(command)

        self._require_finance_governance_commands().cost_code(mutate)

    def add_cost_code_restriction(
        self, command: FinancialCostCodeRestrictionCommand
    ) -> None:
        self._require_finance_governance_commands().cost_code(
            lambda service: service.add_project_cost_code(command),
        )

    def remove_cost_code_restriction(
        self, command: FinancialCostCodeRestrictionCommand
    ) -> None:
        self._require_finance_governance_commands().cost_code(
            lambda service: service.remove_project_cost_code(command),
        )

    def list_cost_entries(
        self,
        project_id: str,
        *,
        status: str | None = None,
        source_module: str | None = None,
        offset: int = 0,
        limit: int = 50,
        sort_key: str = "metaText",
        sort_direction: str = "desc",
    ) -> CostEntryPage:
        if not project_id or self._cost_entry_query is None:
            sort = normalize_cost_entry_sort(key=sort_key, direction=sort_direction)
            return CostEntryPage(offset=offset, limit=limit, sort_key=sort.key, sort_direction=sort.direction.value)
        return self._cost_entry_query.list_page_for_project(
            project_id, status=status, source_module=source_module, offset=offset, limit=limit,
            sort_key=sort_key, sort_direction=sort_direction,
        )

    def list_approved_time_posting_failures(
        self,
        project_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        sort_key: str = "updated",
        sort_direction: str = "desc",
        status: str = "",
    ) -> FinancialPostingFailurePageDto:
        result = self._require_finance_workspace_query().list_approved_time_posting_failures(
            project_id,
            request=ApprovedTimePostingFailureQuery(
                page=page,
                page_size=page_size,
                sort_key=sort_key,
                sort_direction=sort_direction,
                status=status,
            ),
        )
        return result

    def create_manual_actual(
        self, command: FinancialCreateManualActualCommand
    ) -> CostEntryResponse:
        entry = self._require_finance_governance_commands().cost_entry(lambda commands: commands.create_manual_entry(command))
        return entry

    def update_actual_draft(
        self, command: FinancialUpdateActualDraftCommand
    ) -> CostEntryResponse:
        entry = self._require_finance_governance_commands().cost_entry(lambda commands: commands.update_draft(command))
        return entry

    def delete_actual_draft(self, command: FinancialVersionedActualCommand) -> None:
        self._require_finance_governance_commands().cost_entry(lambda commands: commands.delete_draft(command))

    def submit_actual(
        self, command: FinancialVersionedActualCommand
    ) -> CostEntryResponse:
        return self._require_finance_governance_commands().cost_entry(
            lambda commands: commands.submit(command)
        )

    def approve_actual(
        self, command: FinancialDecideActualCommand
    ) -> FinancialCostEntryApprovalDto:
        result = self._require_finance_governance_commands().cost_entry_review(lambda commands: commands.approve(command))
        return result

    def reject_actual(
        self, command: FinancialDecideActualCommand
    ) -> CostEntryResponse:
        return self._require_finance_governance_commands().cost_entry_review(
            lambda commands: commands.reject(command)
        )

    def post_actual(self, command: FinancialPostActualCommand) -> CostEntryResponse:
        return self._require_finance_governance_commands().cost_entry_posting(
            lambda commands: commands.post(command)
        )

    def reverse_actual(
        self, command: FinancialReverseActualCommand
    ) -> CostEntryResponse:
        return self._require_finance_governance_commands().cost_entry_posting(
            lambda commands: commands.reverse(command)
        )


    def get_finance_overview(self, project_id: str) -> FinanceOverviewFacts | None:
        if not project_id or self._finance_snapshot_query is None:
            return None
        return self._finance_snapshot_query.get_finance_overview(project_id)

    def get_commitment_summary(self, project_id: str) -> FinanceOverviewFacts:
        return self._require_finance_snapshot_query().get_finance_overview(project_id)

    def list_commitments(
        self,
        project_id: str,
        *,
        offset: int = 0,
        limit: int = 50,
        sort_key: str = "metaText",
        sort_direction: str = "desc",
        exposure: str = "",
    ) -> CommitmentPage:
        if not project_id or self._commitment_query is None:
            sort = normalize_commitment_sort(key=sort_key, direction=sort_direction)
            return CommitmentPage(offset=offset, limit=limit, sort_key=sort.key, sort_direction=sort.direction.value)
        return self._commitment_query.list_page_for_project(
            project_id, exposure=exposure, offset=offset, limit=limit,
            sort_key=sort_key, sort_direction=sort_direction,
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
    ) -> FinanceForecastWorkspaceFacts:
        if not project_id or self._finance_workspace_query is None:
            return FinanceForecastWorkspaceFacts(
                selected_forecast_id="",
                selected_forecast=None,
                versions=FinancePageFacts((), 0, 1, 50, "revision", "desc"),
                lines=FinancePageFacts((), 0, 1, 50, "title", "asc"),
            )
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
        return facts

    def generate_forecast(
        self, command: FinancialGenerateForecastCommand
    ) -> FinancialForecastMutationDto:
        result = self._require_finance_governance_commands().forecast_generation(
            lambda service: service.generate_draft(command),
        )
        return result

    def submit_forecast(
        self, command: FinancialVersionedForecastCommand
    ) -> FinancialForecastMutationDto:
        forecast = self._require_finance_governance_commands().forecast_lifecycle(
            lambda service: service.submit_forecast(command)
        )
        return forecast

    def request_forecast_approval(
        self, command: FinancialVersionedForecastCommand
    ) -> FinancialForecastMutationDto:
        result = self._require_finance_governance_commands().forecast_approval(
            lambda service: service.request_forecast_approval(command)
        )
        return result

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
    ) -> FinanceRateWorkspaceFacts:
        if not project_id or self._finance_workspace_query is None:
            return FinanceRateWorkspaceFacts(
                selected_rate_card_id="",
                selected_rate_card=None,
                cards=FinancePageFacts((), 0, 1, 50, "title", "asc"),
                lines=FinancePageFacts((), 0, 1, 50, "title", "asc"),
            )
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
        return facts

    def create_rate_card(
        self, command: FinancialCreateRateCardCommand
    ) -> FinancialRateMutationDto:
        card = self._require_finance_governance_commands().rate_card(
            lambda service: service.create_rate_card(command)
        )
        return card

    def update_rate_card(
        self, command: FinancialUpdateRateCardCommand
    ) -> FinancialRateMutationDto:
        card = self._require_finance_governance_commands().rate_card(
            lambda service: service.update_rate_card(command)
        )
        return card

    def deactivate_rate_card(
        self, command: FinancialVersionedRateCardCommand
    ) -> FinancialRateMutationDto:
        card = self._require_finance_governance_commands().rate_card(
            lambda service: service.deactivate_rate_card(command)
        )
        return card

    def add_rate_line(
        self, command: FinancialAddRateLineCommand
    ) -> FinancialRateMutationDto:
        line = self._require_finance_governance_commands().rate_line(
            lambda service: service.create_line(command)
        )
        return line

    def update_rate_line(
        self, command: FinancialUpdateRateLineCommand
    ) -> FinancialRateMutationDto:
        line = self._require_finance_governance_commands().rate_line(
            lambda service: service.update_line(command)
        )
        return line

    def deactivate_rate_line(
        self, command: FinancialVersionedRateLineCommand
    ) -> FinancialRateMutationDto:
        line = self._require_finance_governance_commands().rate_line(
            lambda service: service.deactivate_line(command)
        )
        return line


    def get_accounting_statuses(
        self,
        project_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
        sort_key: str = "metaText",
        sort_direction: str = "desc",
        search: str = "",
    ) -> FinancePageFacts[AccountingStatusFact]:
        if not project_id:
            return FinancePageFacts((), 0, page, page_size, sort_key, sort_direction)
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
        return facts

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
    ) -> FinanceBillingWorkspaceFacts:
        if not project_id or self._finance_workspace_query is None:
            return FinanceBillingWorkspaceFacts(
                profile=None, selected_preparation_id="", selected_preparation=None,
                schedule=FinancePageFacts((), 0, schedule_page, page_size, schedule_sort_key, schedule_sort_direction),
                preparations=FinancePageFacts((), 0, preparation_page, page_size, preparation_sort_key, preparation_sort_direction),
                lines=FinancePageFacts((), 0, line_page, page_size, line_sort_key, line_sort_direction),
            )
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
        return facts

    def list_eligible_billing_sources(
        self, project_id: str, preparation_id: str, *, page: int = 1,
        page_size: int = 50, sort_key: str = "source_date",
        sort_direction: str = "asc", search: str = "",
    ) -> FinancePageFacts[BillingSourceOptionFact]:
        if not project_id or not preparation_id or self._finance_workspace_query is None:
            return FinancePageFacts((), 0, page, page_size, sort_key, sort_direction)
        facts = self._finance_workspace_query.list_eligible_billing_sources(
            project_id,
            preparation_id,
            request=BillingSourceQuery(
                page=page, page_size=page_size, sort_key=sort_key,
                sort_direction=sort_direction, search=search,
            ),
        )
        return facts

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
    ) -> FinanceChangeWorkspaceFacts:
        if not project_id or self._finance_workspace_query is None:
            return FinanceChangeWorkspaceFacts(
                selected_change_id="",
                selected_change=None,
                changes=FinancePageFacts((), 0, 1, 50, "metaText", "desc"),
                impacts=FinancePageFacts((), 0, 1, 50, "metaText", "asc"),
            )
        return self._finance_workspace_query.get_change_workspace(
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

    def create_financial_change(
        self, command: FinancialCreateChangeCommand
    ) -> FinancialChangeMutationDto:
        change = self._require_finance_governance_commands().financial_change(
            lambda service: service.create_change(command),
        )
        return change

    def update_financial_change(
        self, command: FinancialUpdateChangeCommand
    ) -> FinancialChangeMutationDto:
        change = self._require_finance_governance_commands().financial_change(
            lambda service: service.update_change(command)
        )
        return change

    def add_financial_change_impact(
        self, command: FinancialChangeImpactCommand
    ) -> FinancialChangeMutationDto:
        result = self._require_finance_governance_commands().financial_change(
            lambda handler: handler.add_impact(command)
        )
        return result

    def update_financial_change_impact(
        self, command: FinancialUpdateChangeImpactCommand
    ) -> FinancialChangeMutationDto:
        result = self._require_finance_governance_commands().financial_change(
            lambda handler: handler.update_impact(command)
        )
        return result

    def remove_financial_change_impact(
        self, command: FinancialRemoveChangeImpactCommand
    ) -> FinancialChangeMutationDto:
        change = self._require_finance_governance_commands().financial_change(
            lambda service: service.remove_impact(command)
        )
        return change

    def submit_financial_change(
        self, command: FinancialSubmitChangeCommand
    ) -> FinancialChangeMutationDto:
        change = self._require_finance_governance_commands().financial_change_submission(
            lambda service: service.submit_change(command)
        )
        return change





    def get_performance_evm(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
        baseline_id: str | None = None,
    ) -> PerformanceEvmFact | None:
        if not project_id or self._finance_performance_query is None:
            return None
        return self._finance_performance_query.get_evm(
                project_id,
                as_of_date=as_of_date,
                baseline_id=baseline_id,
        )

    def get_performance_variance(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
        selected_baseline_id: str | None = None,
    ) -> PerformanceVarianceFacts | None:
        if not project_id or self._finance_performance_query is None:
            return None
        return self._finance_performance_query.get_variance(
                project_id,
                as_of_date=as_of_date,
                selected_baseline_id=selected_baseline_id,
        )

    def get_cost_phasing(
        self,
        project_id: str,
        *,
        date_from: date,
        date_to: date,
        granularity: str = "month",
        as_of_date: date | None = None,
    ) -> CostPhasingFacts | None:
        if not project_id or self._finance_performance_query is None:
            return None
        return self._finance_performance_query.get_cost_phasing(
                project_id,
                date_from=date_from,
                date_to=date_to,
                granularity=granularity,
                as_of_date=as_of_date,
        )

    def get_performance_reports(
        self,
        project_id: str,
        *,
        as_of_date: date | None = None,
    ) -> FinancialReportsDto:
        if not project_id or self._finance_performance_query is None:
            return FinancialReportsDto()
        return self._finance_performance_query.get_reports(
                project_id,
                as_of_date=as_of_date,
            )

    def export_financial_report(
        self,
        project_id: str,
        output_path: str,
        *,
        report_format: str,
        baseline_id: str | None = None,
    ) -> str:
        if self._report_sources is None:
            raise ConfigurationError("Project management reporting service is not connected.")
        if report_format == "xlsx":
            result = generate_excel_report(
                self._report_sources,
                project_id,
                output_path,
                finance_snapshot_query=self._require_finance_snapshot_query(),
                baseline_id=baseline_id or None,
            )
        elif report_format == "pdf":
            result = generate_pdf_report(
                self._report_sources,
                project_id,
                output_path,
                finance_snapshot_query=self._require_finance_snapshot_query(),
                baseline_id=baseline_id or None,
            )
        else:
            raise ValidationError("Financial report format must be 'xlsx' or 'pdf'.", code="FINANCIAL_REPORT_FORMAT_INVALID")
        return str(result)

    def get_financial_setup_workspace(
        self,
        project_id: str,
        *,
        cost_code_page: int = 1,
        restriction_page: int = 1,
        page_size: int = 50,
        cost_code_search: str = "",
        cost_code_status: str = "",
        cost_code_assignment: str = "",
        restriction_search: str = "",
        cost_code_sort_key: str = "code",
        cost_code_sort_direction: str = "asc",
        restriction_sort_key: str = "code",
        restriction_sort_direction: str = "asc",
    ) -> FinanceSetupWorkspaceFacts | None:
        if not project_id or self._finance_workspace_query is None:
            return None
        return self._finance_workspace_query.get_setup_workspace(
            project_id,
            cost_code_request=FinanceSetupCostCodeQuery(
                page=cost_code_page,
                page_size=page_size,
                search=cost_code_search,
                status=cost_code_status,
                assignment_state=cost_code_assignment,
                sort_key=cost_code_sort_key,
                sort_direction=cost_code_sort_direction,
            ),
            restriction_request=FinanceSetupRestrictionQuery(
                page=restriction_page,
                page_size=page_size,
                search=restriction_search,
                sort_key=restriction_sort_key,
                sort_direction=restriction_sort_direction,
            ),
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
    ) -> FinanceBudgetWorkspaceFacts:
        if not project_id or self._finance_workspace_query is None:
            return FinanceBudgetWorkspaceFacts(
                selected_budget_id="",
                versions=BudgetVersionPageFacts((), 0, 1, 50, "revision", "desc"),
                lines=FinancePageFacts((), 0, 1, 50, "metaText", "desc"),
            )
        return self._finance_workspace_query.get_budget_workspace(
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

    def create_budget_version(
        self, command: FinancialCreateBudgetVersionCommand
    ) -> FinancialBudgetMutationDto:
        budget = self._require_finance_governance_commands().budget_lifecycle(
            lambda service: service.create_budget(command),
        )
        return budget

    def create_budget_successor(
        self, command: FinancialCreateBudgetSuccessorCommand
    ) -> FinancialBudgetMutationDto:
        budget = self._require_finance_governance_commands().budget_lifecycle(
            lambda service: service.create_successor(command)
        )
        return budget

    def update_budget(
        self, command: FinancialUpdateBudgetCommand
    ) -> FinancialBudgetMutationDto:
        budget = self._require_finance_governance_commands().budget_lifecycle(
            lambda service: service.update_budget_header(command)
        )
        return budget

    def delete_budget(self, command: FinancialVersionedBudgetCommand) -> None:
        self._require_finance_governance_commands().budget_lifecycle(
            lambda service: service.delete_budget(command)
        )

    def add_budget_line(
        self, command: FinancialAddBudgetLineCommand
    ) -> FinancialBudgetLineMutationDto:
        line = self._require_finance_governance_commands().budget_lines(
            lambda service: service.add_line(command)
        )
        return line

    def update_budget_line(
        self, command: FinancialUpdateBudgetLineCommand
    ) -> FinancialBudgetLineMutationDto:
        line = self._require_finance_governance_commands().budget_lines(
            lambda service: service.update_line(command)
        )
        return line

    def delete_budget_line(self, command: FinancialDeleteBudgetLineCommand) -> None:
        self._require_finance_governance_commands().budget_lines(
            lambda service: service.delete_line(command)
        )

    def submit_budget(
        self, command: FinancialVersionedBudgetCommand
    ) -> FinancialBudgetMutationDto:
        budget = self._require_finance_governance_commands().budget_lifecycle(
            lambda service: service.submit_budget(command)
        )
        return budget

    def request_budget_approval(
        self, command: FinancialVersionedBudgetCommand
    ) -> FinancialBudgetMutationDto:
        result = self._require_finance_governance_commands().budget_approval(
            lambda service: service.request_budget_approval(command)
        )
        return result

    def close_budget(
        self, command: FinancialVersionedBudgetCommand
    ) -> FinancialBudgetMutationDto:
        budget = self._require_finance_governance_commands().budget_lifecycle(
            lambda service: service.close_budget(command)
        )
        return budget





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
    ) -> FinancePlannedCostWorkspaceFacts:
        if not project_id or self._finance_workspace_query is None:
            return FinancePlannedCostWorkspaceFacts(
                selected_version_id="",
                versions=FinancePageFacts((), 0, 1, 50, "revision", "desc"),
                lines=FinancePageFacts((), 0, 1, 50, "title", "asc"),
            )
        return self._finance_workspace_query.get_planned_cost_workspace(
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

    def create_billing_profile(
        self, command: FinancialCreateBillingProfileCommand
    ) -> FinancialBillingProfileDto:
        profile = self._require_finance_governance_commands().billing_profile(lambda commands: commands.create_profile(command))
        return profile

    def activate_billing_profile(
        self, command: FinancialActivateBillingProfileCommand
    ) -> FinancialBillingProfileDto:
        profile = self._require_finance_governance_commands().billing_profile(lambda commands: commands.activate_profile(command))
        return profile

    def add_billing_schedule_line(
        self, command: FinancialAddBillingScheduleLineCommand
    ) -> FinancialBillingScheduleLineDto:
        line = self._require_finance_governance_commands().billing_schedule(lambda commands: commands.add_schedule_line(command))
        return line

    def mark_billing_schedule_line_ready(
        self, command: FinancialMarkBillingScheduleLineReadyCommand
    ) -> FinancialBillingScheduleLineDto:
        line = self._require_finance_governance_commands().billing_schedule(lambda commands: commands.mark_schedule_line_ready(command))
        return line

    def create_billing_preparation(
        self, command: FinancialCreateBillingPreparationCommand
    ) -> FinancialBillingPreparationResponse:
        preparation = self._require_finance_governance_commands().billing_preparation(lambda commands: commands.create_preparation(command))
        return preparation

    def add_fixed_price_billing_source(
        self, command: FinancialAddFixedPriceBillingSourceCommand
    ) -> FinancialBillingPreparationLineDto:
        line = self._require_finance_governance_commands().billing_source(lambda commands: commands.add_fixed_price_source(command))
        return line

    def add_approved_time_billing_source(
        self, command: FinancialAddApprovedTimeBillingSourceCommand
    ) -> FinancialBillingPreparationLineDto:
        line = self._require_finance_governance_commands().billing_source(lambda commands: commands.add_approved_time_source(command))
        return line

    def add_cost_plus_billing_source(
        self, command: FinancialAddCostPlusBillingSourceCommand
    ) -> FinancialBillingPreparationLineDto:
        line = self._require_finance_governance_commands().billing_source(lambda commands: commands.add_cost_plus_source(command))
        return line

    def remove_draft_billing_line(
        self, command: FinancialRemoveDraftBillingLineCommand
    ) -> FinancialBillingPreparationResponse:
        preparation = self._require_finance_governance_commands().billing_source(lambda commands: commands.remove_draft_line(command))
        return preparation

    def cancel_draft_billing_preparation(
        self, command: FinancialVersionedBillingPreparationCommand
    ) -> FinancialBillingPreparationResponse:
        preparation = self._require_finance_governance_commands().billing_preparation(lambda commands: commands.cancel_draft_preparation(command))
        return preparation

    def submit_billing_preparation(
        self, command: FinancialVersionedBillingPreparationCommand
    ) -> FinancialBillingPreparationResponse:
        preparation = self._require_finance_governance_commands().billing_submission(lambda commands: commands.submit_preparation(command))
        return preparation

    def request_billing_delivery(
        self, command: FinancialVersionedBillingPreparationCommand
    ) -> FinancialBillingPreparationResponse:
        # The outbound project_billing_preparation.v1 payload isn't surfaced here -- PM
        # requests delivery of its own evidence, it doesn't deliver or record what
        # Accounting did with it.
        self._require_finance_governance_commands().accounting_handoff(
            lambda commands: commands.request(command.preparation_id, expected_row_version=command.expected_version)
        )
        preparation = self._require_billing_preparation_query().get_preparation(command.preparation_id)
        return preparation

    def get_commercial_projection(
        self, project_id: str, *, as_of_date: date | None = None
    ) -> FinancialCommercialProjectionDto:
        if not project_id or self._profitability_report is None:
            reason = CommercialMetricUnavailableReason.PROJECT_NOT_SELECTED if not project_id else CommercialMetricUnavailableReason.QUERY_NOT_CONNECTED
            return FinancialCommercialProjectionDto(
                revenue_availability=CommercialMetricAvailability.UNAVAILABLE,
                margin_availability=CommercialMetricAvailability.UNAVAILABLE,
                percent_availability=CommercialMetricAvailability.UNAVAILABLE,
                revenue_reason=reason, margin_reason=reason, percent_reason=reason,
            )
        resolved_as_of = as_of_date or datetime.now(UTC).astimezone().date()
        return self._profitability_report.get_project_commercial_projection(
                project_id, as_of_date=resolved_as_of
            )


    def _require_billing_profile_query(self) -> ProjectBillingProfileQueryHandler:
        if self._billing_profile_query is None:
            raise ConfigurationError("Project billing profile service is not connected.")
        return self._billing_profile_query

    def _require_billing_preparation_query(self) -> ProjectBillingPreparationQueryHandler:
        if self._billing_preparation_query is None:
            raise ConfigurationError("Project billing preparation service is not connected.")
        return self._billing_preparation_query

    def _require_finance_governance_commands(
        self,
    ) -> FinanceGovernanceCommandBoundary:
        if self._finance_governance_commands is None:
            raise ConfigurationError("Project Finance governance command boundary is not connected.")
        return self._finance_governance_commands

    def _require_finance_snapshot_query(self) -> FinanceSnapshotQueryHandler:
        if self._finance_snapshot_query is None:
            raise ConfigurationError("Project management finance service is not connected.")
        return self._finance_snapshot_query

    def _require_finance_workspace_query(self) -> ProjectFinanceWorkspaceQuery:
        if self._finance_workspace_query is None:
            raise ConfigurationError("Project Finance workspace query is not connected.")
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
