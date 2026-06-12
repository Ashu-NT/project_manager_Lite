"""Dashboard analytics — burndown, EVM, and performance analysis."""
from src.core.modules.project_management.application.dashboard.analytics.burndown import DashboardBurndownMixin
from src.core.modules.project_management.application.dashboard.analytics.evm import DashboardEvmMixin
__all__ = ["DashboardBurndownMixin", "DashboardEvmMixin"]
