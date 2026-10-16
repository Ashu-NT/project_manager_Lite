"""Project command normalization, shared by transport-neutral use cases."""

from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.platform.common.exceptions import ValidationError


def project_status(value: str | ProjectStatus | None) -> ProjectStatus:
    if isinstance(value, ProjectStatus):
        return value
    normalized = str(value or ProjectStatus.PLANNED.value).strip().upper()
    try:
        return ProjectStatus(normalized)
    except ValueError as exc:
        raise ValidationError(
            f"Unsupported project status: {normalized}.", code="PROJECT_STATUS_INVALID"
        ) from exc
