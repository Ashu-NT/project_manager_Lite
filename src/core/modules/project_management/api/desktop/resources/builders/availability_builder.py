from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.api.desktop.resources.serializers.availability_serializer import (
    serialize_resource_availability,
)


def build_resource_availability(
    resource_id: str,
    *,
    availability_service,
):
    normalized_id = str(resource_id or "").strip()
    if not normalized_id or availability_service is None:
        return None
    from_date = date.today()
    to_date = from_date + timedelta(days=90)
    try:
        report = availability_service.check_availability(
            resource_ids=[normalized_id],
            from_date=from_date,
            to_date=to_date,
        )
    except Exception:
        return None
    window = next(
        (
            item
            for item in report.resources
            if str(item.resource_id) == normalized_id
        ),
        None,
    )
    if window is None:
        return None
    return serialize_resource_availability(
        normalized_id,
        window,
        from_date=from_date,
        to_date=to_date,
    )


__all__ = ["build_resource_availability"]
