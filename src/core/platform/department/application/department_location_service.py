from __future__ import annotations

from src.core.platform.auth.authorization import require_permission
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.site.contracts import LocationReferenceRepository

from .department_context import active_organization
from .department_validation import validate_site_id
from .department_utils import normalize_optional_text


def register_location_reference_repository(
    service,
    location_reference_repo: LocationReferenceRepository | None,
) -> None:
    service._location_reference_repo = location_reference_repo


def validate_default_location_id(
    service,
    default_location_id: str | None,
    *,
    organization_id: str,
    site_id: str | None,
) -> str | None:
    normalized = normalize_optional_text(default_location_id) or None
    if normalized is None:
        return None
    if service._location_reference_repo is None:
        raise ValidationError(
            "Maintenance location references are not available in the current runtime.",
            code="DEPARTMENT_LOCATION_REFERENCE_UNAVAILABLE",
        )
    location = service._location_reference_repo.get(normalized)
    if location is None or location.organization_id != organization_id:
        raise ValidationError(
            "Department default location must belong to the active organization.",
            code="DEPARTMENT_LOCATION_INVALID",
        )
    if site_id is not None and location.site_id != site_id:
        raise ValidationError(
            "Department default location must belong to the selected site.",
            code="DEPARTMENT_LOCATION_SITE_INVALID",
        )
    return normalized


def list_available_location_references(
    service,
    *,
    site_id: str | None = None,
    active_only: bool | None = True,
) -> list[object]:
    require_permission(
        service._user_session,
        "settings.manage",
        operation_label="list department location references",
    )
    organization = active_organization(service)
    if site_id is not None:
        validate_site_id(service, site_id, organization_id=organization.id)
    if service._location_reference_repo is None:
        return []
    return list(
        service._location_reference_repo.list_for_organization(
            organization.id,
            active_only=active_only,
            site_id=site_id,
        )
    )


__all__ = [
    "list_available_location_references",
    "register_location_reference_repository",
    "validate_default_location_id",
]
