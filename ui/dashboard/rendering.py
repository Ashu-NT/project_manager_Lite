"""Dashboard rendering facade mixin."""

from ui.dashboard.rendering_alerts import DashboardAlertsRenderingMixin
from ui.dashboard.rendering_charts import DashboardChartsRenderingMixin
from ui.dashboard.rendering_evm import DashboardEvmRenderingMixin
from ui.dashboard.rendering_summary import DashboardSummaryRenderingMixin


class DashboardRenderingMixin(
    DashboardSummaryRenderingMixin,
    DashboardAlertsRenderingMixin,
    DashboardChartsRenderingMixin,
    DashboardEvmRenderingMixin,
):
    pass
