"""Project, intake status, and dependency type option builders."""

from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.domain.portfolio import PortfolioIntakeStatus
from src.core.modules.project_management.api.desktop.portfolio.models.options import (
    PortfolioOptionDescriptor,
    PortfolioProjectOptionDescriptor,
)
from src.core.modules.project_management.api.desktop.portfolio.utils.dependency_type_utils import dependency_type_label


def build_project_options(project_service=None) -> tuple[PortfolioProjectOptionDescriptor, ...]:
    if project_service is None:
        return ()
    projects = sorted(project_service.list_projects(), key=lambda p: (p.name or "").casefold())
    return tuple(PortfolioProjectOptionDescriptor(value=p.id, label=p.name) for p in projects)


def build_intake_status_options() -> tuple[PortfolioOptionDescriptor, ...]:
    return tuple(
        PortfolioOptionDescriptor(value=s.value, label=s.value.replace("_", " ").title())
        for s in PortfolioIntakeStatus
    )


def build_dependency_type_options() -> tuple[PortfolioOptionDescriptor, ...]:
    return tuple(
        PortfolioOptionDescriptor(value=dt.value, label=dependency_type_label(dt))
        for dt in DependencyType
    )


__all__ = ["build_dependency_type_options", "build_intake_status_options", "build_project_options"]
