"""Dashboard rendering facade mixin."""

from ui.modules.project_management.dashboard.rendering_alerts import DashboardAlertsRenderingMixin
from ui.modules.project_management.dashboard.rendering_charts import DashboardChartsRenderingMixin
from ui.modules.project_management.dashboard.rendering_evm import DashboardEvmRenderingMixin
from ui.modules.project_management.dashboard.rendering_portfolio import DashboardPortfolioRenderingMixin
from ui.modules.project_management.dashboard.rendering_professional import DashboardProfessionalRenderingMixin
from ui.modules.project_management.dashboard.rendering_summary import DashboardSummaryRenderingMixin


class DashboardRenderingMixin(
    DashboardSummaryRenderingMixin,
    DashboardAlertsRenderingMixin,
    DashboardChartsRenderingMixin,
    DashboardEvmRenderingMixin,
    DashboardPortfolioRenderingMixin,
    DashboardProfessionalRenderingMixin,
):
    pass
