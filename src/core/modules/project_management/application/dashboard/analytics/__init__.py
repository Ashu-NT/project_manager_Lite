"""Dashboard analytics — burndown and EVM widgets."""
from src.core.modules.project_management.application.dashboard.analytics.burndown import (
    DashboardBurndownBuilder,
)
from src.core.modules.project_management.application.dashboard.analytics.evm import (
    DashboardEvmWidget,
)

__all__ = ["DashboardBurndownBuilder", "DashboardEvmWidget"]
