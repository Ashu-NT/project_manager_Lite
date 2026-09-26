"""Dashboard widget data providers."""
from src.core.modules.project_management.application.dashboard.widgets.professional import (
    DashboardProfessionalMixin,
)
from src.core.modules.project_management.application.dashboard.widgets.register import (
    DashboardRegisterMixin,
)
from src.core.modules.project_management.application.dashboard.widgets.upcoming import (
    DashboardUpcomingMixin,
)

__all__ = ["DashboardProfessionalMixin", "DashboardRegisterMixin", "DashboardUpcomingMixin"]
