"""Financial desktop API — modular enterprise package."""

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.api.desktop.financials.commands.create_cost_item import FinancialCreateCommand
from src.core.modules.project_management.api.desktop.financials.commands.update_cost_item import FinancialUpdateCommand
from src.core.modules.project_management.api.desktop.financials.factories.financials_api_factory import (
    build_project_management_financials_desktop_api,
)
from src.core.modules.project_management.api.desktop.financials.models import (
    BaselineVarianceRecordDto,
    FinancialAnalyticsRowDto,
    FinancialCommitmentSummaryDto,
    FinancialCostItemDto,
    FinancialCostTypeDescriptor,
    FinancialForecastDto,
    FinancialLedgerRowDto,
    FinancialPeriodRowDto,
    FinancialProjectOptionDescriptor,
    FinancialSnapshotDto,
    FinancialTaskOptionDescriptor,
    ProjectProcurementCommitmentSummary,
    ProjectRequisitionDesktopDto,
)

__all__ = [
    "BaselineVarianceRecordDto",
    "FinancialAnalyticsRowDto",
    "FinancialCommitmentSummaryDto",
    "FinancialCostItemDto",
    "FinancialCostTypeDescriptor",
    "FinancialCreateCommand",
    "FinancialForecastDto",
    "FinancialLedgerRowDto",
    "FinancialPeriodRowDto",
    "FinancialProjectOptionDescriptor",
    "FinancialSnapshotDto",
    "FinancialTaskOptionDescriptor",
    "FinancialUpdateCommand",
    "ProjectManagementFinancialsDesktopApi",
    "ProjectProcurementCommitmentSummary",
    "ProjectRequisitionDesktopDto",
    "build_project_management_financials_desktop_api",
]
