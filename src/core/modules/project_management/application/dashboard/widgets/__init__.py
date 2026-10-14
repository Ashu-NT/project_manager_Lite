"""Dashboard widget data providers."""
from src.core.modules.project_management.application.dashboard.widgets.professional import (
    DashboardScheduleHealthWidget,
)
from src.core.modules.project_management.application.dashboard.widgets.register import (
    DashboardRegisterWidget,
)
from src.core.modules.project_management.application.dashboard.widgets.upcoming import (
    DashboardUpcomingWidget,
)

__all__ = ["DashboardRegisterWidget", "DashboardScheduleHealthWidget", "DashboardUpcomingWidget"]
