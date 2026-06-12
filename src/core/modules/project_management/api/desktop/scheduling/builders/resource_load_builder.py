"""Resource load view-model assembly."""

from src.core.modules.project_management.api.desktop.scheduling.models.resources import SchedulingResourceLoadDto
from src.core.modules.project_management.api.desktop.scheduling.serializers.resource_load_serializer import serialize_resource_load_row


def build_resource_load(project_id: str, reporting_service=None) -> tuple[SchedulingResourceLoadDto, ...]:
    if not project_id or reporting_service is None:
        return ()
    get_summary = getattr(reporting_service, "get_resource_load_summary", None)
    if not callable(get_summary):
        return ()
    rows = get_summary(project_id)
    return tuple(serialize_resource_load_row(row) for row in rows)


__all__ = ["build_resource_load"]
