from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from src.core.modules.maintenance.domain.enums import (
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
)


def _label_code(label: str, suffix: str) -> str:
    return f"{label.upper().replace(' ', '_')}_{suffix}"


def normalize_maintenance_code(value: object, *, label: str) -> str:
    return normalize_required_text(
        value,
        message=f"{label} is required.",
        code=_label_code(label, "REQUIRED"),
    ).upper()


def normalize_maintenance_name(value: object, *, label: str) -> str:
    return normalize_required_text(
        value,
        message=f"{label} is required.",
        code=_label_code(label, "REQUIRED"),
    )


def normalize_optional_upper_text(value: object) -> str:
    return normalize_optional_text(value).upper()


def normalize_optional_date(value: object, *, label: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = normalize_optional_text(value)
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError(
            f"{label} is invalid. Use YYYY-MM-DD.",
            code=_label_code(label, "INVALID"),
        ) from exc


def normalize_optional_datetime(
    value: object,
    *,
    message: str,
    code: str,
) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        resolved = value
    else:
        raw = normalize_optional_text(value)
        try:
            resolved = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise ValidationError(message, code=code) from exc
    if resolved.tzinfo is None or resolved.utcoffset() is None:
        return resolved.replace(tzinfo=timezone.utc)
    return resolved.astimezone(timezone.utc)


def normalize_positive_int(
    value: object,
    *,
    message: str,
    code: str,
    default: int = 1,
) -> int:
    raw = default if value in (None, "") else value
    try:
        resolved = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValidationError(message, code=code) from exc
    if resolved < 1:
        raise ValidationError(message, code=code)
    return resolved


def normalize_optional_non_negative_int(value: object, *, label: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        resolved = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"{label} is invalid.",
            code=_label_code(label, "INVALID"),
        ) from exc
    if resolved < 0:
        raise ValidationError(
            f"{label} cannot be negative.",
            code=_label_code(label, "NEGATIVE"),
        )
    return resolved


def normalize_optional_decimal(value: object, *, label: str) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        resolved = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(
            f"{label} is invalid.",
            code=_label_code(label, "INVALID"),
        ) from exc
    if resolved < 0:
        raise ValidationError(
            f"{label} cannot be negative.",
            code=_label_code(label, "NEGATIVE"),
        )
    return resolved


def normalize_criticality(value: object) -> MaintenanceCriticality:
    if isinstance(value, MaintenanceCriticality):
        return value
    raw = normalize_optional_upper_text(value) or MaintenanceCriticality.MEDIUM.value
    try:
        return MaintenanceCriticality(raw)
    except ValueError as exc:
        raise ValidationError(
            "Criticality is invalid.",
            code="MAINTENANCE_CRITICALITY_INVALID",
        ) from exc


def normalize_lifecycle_status(
    value: object,
    *,
    is_active: bool = True,
) -> MaintenanceLifecycleStatus:
    if value in (None, ""):
        return (
            MaintenanceLifecycleStatus.ACTIVE
            if is_active
            else MaintenanceLifecycleStatus.INACTIVE
        )
    if isinstance(value, MaintenanceLifecycleStatus):
        return value
    raw = normalize_optional_upper_text(value)
    try:
        return MaintenanceLifecycleStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Maintenance lifecycle status is invalid.",
            code="MAINTENANCE_STATUS_INVALID",
        ) from exc


__all__ = [
    "normalize_criticality",
    "normalize_lifecycle_status",
    "normalize_maintenance_code",
    "normalize_maintenance_name",
    "normalize_optional_date",
    "normalize_optional_datetime",
    "normalize_optional_decimal",
    "normalize_optional_identifier",
    "normalize_optional_non_negative_int",
    "normalize_optional_text",
    "normalize_optional_upper_text",
    "normalize_positive_int",
    "normalize_required_text",
]
