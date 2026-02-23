"""Compatibility wrapper for DashboardService and dashboard DTOs."""

from core.services.dashboard.service import (
    DashboardService,
    DashboardData,
    DashboardEVM,
    UpcomingTask,
    BurndownPoint,
)

__all__ = [
    "DashboardService",
    "DashboardData",
    "DashboardEVM",
    "UpcomingTask",
    "BurndownPoint",
]
