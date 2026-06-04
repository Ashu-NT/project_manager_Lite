from src.core.modules.project_management.api.desktop.scheduling.models.schedule import SchedulingProjectOptionDescriptor


def build_project_options(project_service=None) -> tuple[SchedulingProjectOptionDescriptor, ...]:
    if project_service is None:
        return ()
    projects = sorted(project_service.list_projects(), key=lambda p: (p.name or "").casefold())
    return tuple(SchedulingProjectOptionDescriptor(value=p.id, label=p.name) for p in projects)


__all__ = ["build_project_options"]
