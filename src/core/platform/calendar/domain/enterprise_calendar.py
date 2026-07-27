"""Enterprise calendar domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone as dt_timezone
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


class CalendarType(str, Enum):
    GLOBAL = "GLOBAL"
    SITE = "SITE"
    DEPARTMENT = "DEPARTMENT"
    EMPLOYEE = "EMPLOYEE"
    PROJECT = "PROJECT"
    RESOURCE = "RESOURCE"


class ExceptionType(str, Enum):
    HOLIDAY = "HOLIDAY"
    SHUTDOWN = "SHUTDOWN"
    VACATION = "VACATION"
    SICK_LEAVE = "SICK_LEAVE"
    TRAINING = "TRAINING"
    MEETING = "MEETING"
    NON_WORKING = "NON_WORKING"
    EXTRA_WORKING = "EXTRA_WORKING"
    REDUCED_HOURS = "REDUCED_HOURS"
    OVERTIME = "OVERTIME"
    MAINTENANCE_WINDOW = "MAINTENANCE_WINDOW"
    SITE_CLOSED = "SITE_CLOSED"


class ImpactType(str, Enum):
    UNAVAILABLE = "UNAVAILABLE"
    REDUCED_CAPACITY = "REDUCED_CAPACITY"
    EXTRA_CAPACITY = "EXTRA_CAPACITY"
    WORKING = "WORKING"
    INFORMATION_ONLY = "INFORMATION_ONLY"


class RecurringEventType(str, Enum):
    MEETING = "MEETING"
    TRAINING = "TRAINING"
    ADMIN = "ADMIN"
    MAINTENANCE = "MAINTENANCE"
    UNAVAILABLE = "UNAVAILABLE"
    ON_CALL = "ON_CALL"
    OVERTIME_WINDOW = "OVERTIME_WINDOW"
    SHIFT_BLOCK = "SHIFT_BLOCK"


class PatternType(str, Enum):
    STANDARD = "STANDARD"
    DAY_SHIFT = "DAY_SHIFT"
    NIGHT_SHIFT = "NIGHT_SHIFT"
    TWO_SHIFT = "TWO_SHIFT"
    THREE_SHIFT = "THREE_SHIFT"
    ROTATING = "ROTATING"
    FOUR_ON_FOUR_OFF = "FOUR_ON_FOUR_OFF"
    CUSTOM = "CUSTOM"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


_VALID_CALENDAR_TYPES = {item.value for item in CalendarType}
_VALID_EXCEPTION_TYPES = {item.value for item in ExceptionType}
_VALID_IMPACT_TYPES = {item.value for item in ImpactType}
_VALID_RECURRING_EVENT_TYPES = {item.value for item in RecurringEventType}
_VALID_PATTERN_TYPES = {item.value for item in PatternType}
_VALID_APPROVAL_STATUSES = {item.value for item in ApprovalStatus}

_IMPACT_TYPE_ALIASES = {
    "NON_WORKING": ImpactType.UNAVAILABLE.value,
}
_RECURRING_EVENT_TYPE_ALIASES = {
    "SHIFT": RecurringEventType.SHIFT_BLOCK.value,
}
_PATTERN_TYPE_ALIASES = {
    "FIXED": PatternType.STANDARD.value,
}


def _normalize_optional_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValidationError("Calendar dates must be valid dates.", code="CALENDAR_DATE_INVALID")
    return value


def _normalize_required_date(value: object, *, message: str, code: str) -> date:
    normalized = _normalize_optional_date(value)
    if normalized is None:
        raise ValidationError(message, code=code)
    return normalized


def _normalize_optional_time(value: object) -> time | None:
    if value in (None, ""):
        return None
    if not isinstance(value, time):
        raise ValidationError("Calendar times must be valid times.", code="CALENDAR_TIME_INVALID")
    return value


def _normalize_required_time(value: object, *, message: str, code: str) -> time:
    normalized = _normalize_optional_time(value)
    if normalized is None:
        raise ValidationError(message, code=code)
    return normalized


def _normalize_optional_datetime(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Calendar timestamps must be valid datetimes.",
            code="CALENDAR_TIMESTAMP_INVALID",
        )
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=dt_timezone.utc)
    return value.astimezone(dt_timezone.utc)


def _normalize_optional_float(
    value: object,
    *,
    code: str,
    message: str,
) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(message, code=code) from exc


def _normalize_non_negative_float(
    value: object,
    *,
    code: str,
    message: str,
) -> float | None:
    normalized = _normalize_optional_float(value, code=code, message=message)
    if normalized is not None and normalized < 0:
        raise ValidationError(message, code=code)
    return normalized


def _normalize_int(value: object, *, default: int = 0) -> int:
    try:
        return int(value if value not in (None, "") else default)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Calendar numeric values must be integers.",
            code="CALENDAR_INTEGER_INVALID",
        ) from exc


def _normalize_positive_int(value: object, *, code: str, message: str) -> int:
    normalized = _normalize_int(value, default=1)
    if normalized < 1:
        raise ValidationError(message, code=code)
    return normalized


def _normalize_non_negative_int(value: object, *, code: str, message: str) -> int:
    normalized = _normalize_int(value, default=0)
    if normalized < 0:
        raise ValidationError(message, code=code)
    return normalized


def _normalize_required_choice(
    value: object,
    *,
    valid_values: set[str],
    aliases: dict[str, str] | None,
    empty_message: str,
    invalid_message: str,
    code: str,
) -> str:
    normalized = normalize_required_text(
        value,
        message=empty_message,
        code=code,
    ).upper()
    if aliases is not None:
        normalized = aliases.get(normalized, normalized)
    if normalized not in valid_values:
        raise ValidationError(
            invalid_message.format(value=normalized),
            code=code,
        )
    return normalized


def _normalize_optional_scope_type(value: object) -> str | None:
    normalized = normalize_optional_text(value).lower()
    return normalized or None


def _normalize_optional_free_text(value: object) -> str | None:
    normalized = normalize_optional_text(value)
    return normalized or None


@validated_dataclass
class PlatformCalendar:
    id: str
    organization_id: str
    code: str
    name: str
    calendar_type: str
    timezone: str = "UTC"
    description: str | None = None
    base_calendar_id: str | None = None
    scope_type: str | None = None
    scope_id: str | None = None
    locale: str | None = None
    is_default: bool = False
    is_active: bool = True
    effective_from: date | None = None
    effective_to: date | None = None
    priority: int = 0
    version: int = 1
    created_by: str | None = None
    created_at: datetime | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None

    @field_validator("organization_id", mode="before")
    @classmethod
    def _validate_organization_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization ID is required.",
            code="CALENDAR_ORGANIZATION_REQUIRED",
        )

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar code is required.",
            code="CALENDAR_CODE_REQUIRED",
        ).upper()

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar name is required.",
            code="CALENDAR_NAME_REQUIRED",
        )

    @field_validator("calendar_type", mode="before")
    @classmethod
    def _validate_calendar_type(cls, value: object) -> str:
        return _normalize_required_choice(
            value,
            valid_values=_VALID_CALENDAR_TYPES,
            aliases=None,
            empty_message="Calendar type is required.",
            invalid_message=(
                "Invalid calendar_type '{value}'. "
                f"Valid values: {sorted(_VALID_CALENDAR_TYPES)}"
            ),
            code="CALENDAR_TYPE_INVALID",
        )

    @field_validator("timezone", mode="before")
    @classmethod
    def _normalize_timezone(cls, value: object) -> str:
        return normalize_optional_text(value) or "UTC"

    @field_validator("description", "locale", "created_by", "updated_by", mode="before")
    @classmethod
    def _normalize_optional_text_fields(cls, value: object) -> str | None:
        return _normalize_optional_free_text(value)

    @field_validator("base_calendar_id", "scope_id", mode="before")
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("scope_type", mode="before")
    @classmethod
    def _normalize_scope_type(cls, value: object) -> str | None:
        return _normalize_optional_scope_type(value)

    @field_validator("effective_from", "effective_to", mode="before")
    @classmethod
    def _validate_dates(cls, value: object) -> date | None:
        return _normalize_optional_date(value)

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, value: object) -> int:
        return _normalize_int(value, default=0)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return _normalize_positive_int(
            value,
            code="CALENDAR_VERSION_INVALID",
            message="Calendar version must be positive.",
        )

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object) -> datetime | None:
        return _normalize_optional_datetime(value)

    @model_validator(mode="after")
    def _validate_effective_range(self) -> "PlatformCalendar":
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_from > self.effective_to
        ):
            raise ValidationError(
                "effective_from must be before effective_to.",
                code="CALENDAR_EFFECTIVE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        organization_id: str,
        code: str,
        name: str,
        calendar_type: str,
        *,
        timezone: str = "UTC",
        description: str | None = None,
        base_calendar_id: str | None = None,
        scope_type: str | None = None,
        scope_id: str | None = None,
        locale: str | None = None,
        is_default: bool = False,
        effective_from: date | None = None,
        effective_to: date | None = None,
        priority: int = 0,
        created_by: str | None = None,
    ) -> "PlatformCalendar":
        now = datetime.now(dt_timezone.utc)
        return PlatformCalendar(
            id=generate_id(),
            organization_id=organization_id,
            code=code,
            name=name,
            calendar_type=calendar_type,
            timezone=timezone,
            description=description,
            base_calendar_id=base_calendar_id,
            scope_type=scope_type,
            scope_id=scope_id,
            locale=locale,
            is_default=is_default,
            is_active=True,
            effective_from=effective_from,
            effective_to=effective_to,
            priority=priority,
            version=1,
            created_by=created_by,
            created_at=now,
            updated_by=created_by,
            updated_at=now,
        )


@validated_dataclass
class CalendarWorkingRule:
    id: str
    calendar_id: str
    weekday: int
    is_working_day: bool = True
    start_time: time | None = None
    end_time: time | None = None
    break_start_time: time | None = None
    break_end_time: time | None = None
    break_minutes: int = 0
    hours_override: float | None = None
    shift_code: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    priority: int = 0

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar working rule ID is required.",
            code="CALENDAR_RULE_ID_REQUIRED",
        )

    @field_validator("calendar_id", mode="before")
    @classmethod
    def _validate_calendar_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar ID is required.",
            code="CALENDAR_RULE_CALENDAR_REQUIRED",
        )

    @field_validator("weekday", mode="before")
    @classmethod
    def _validate_weekday(cls, value: object) -> int:
        if value in (None, ""):
            raise ValidationError(
                "weekday must be between 0 and 6.",
                code="CALENDAR_RULE_WEEKDAY_INVALID",
            )
        normalized = _normalize_int(value, default=0)
        if normalized not in range(7):
            raise ValidationError(
                "weekday must be between 0 and 6.",
                code="CALENDAR_RULE_WEEKDAY_INVALID",
            )
        return normalized

    @field_validator("start_time", "end_time", "break_start_time", "break_end_time", mode="before")
    @classmethod
    def _validate_times(cls, value: object) -> time | None:
        return _normalize_optional_time(value)

    @field_validator("break_minutes", mode="before")
    @classmethod
    def _validate_break_minutes(cls, value: object) -> int:
        return _normalize_non_negative_int(
            value,
            code="CALENDAR_RULE_BREAK_MINUTES_INVALID",
            message="break_minutes must be non-negative.",
        )

    @field_validator("hours_override", mode="before")
    @classmethod
    def _validate_hours_override(cls, value: object) -> float | None:
        return _normalize_non_negative_float(
            value,
            code="CALENDAR_RULE_HOURS_OVERRIDE_INVALID",
            message="hours_override must be non-negative.",
        )

    @field_validator("shift_code", mode="before")
    @classmethod
    def _normalize_shift_code(cls, value: object) -> str | None:
        return _normalize_optional_free_text(value)

    @field_validator("effective_from", "effective_to", mode="before")
    @classmethod
    def _validate_dates(cls, value: object) -> date | None:
        return _normalize_optional_date(value)

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, value: object) -> int:
        return _normalize_int(value, default=0)

    @model_validator(mode="after")
    def _validate_ranges(self) -> "CalendarWorkingRule":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        ):
            raise ValidationError(
                "start_time must be before end_time.",
                code="CALENDAR_RULE_TIME_RANGE_INVALID",
            )
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValidationError(
                "effective_to must be after effective_from.",
                code="CALENDAR_RULE_EFFECTIVE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        calendar_id: str,
        weekday: int,
        *,
        is_working_day: bool = True,
        start_time: time | None = None,
        end_time: time | None = None,
        break_start_time: time | None = None,
        break_end_time: time | None = None,
        break_minutes: int = 0,
        hours_override: float | None = None,
        shift_code: str | None = None,
        effective_from: date | None = None,
        effective_to: date | None = None,
        priority: int = 0,
    ) -> "CalendarWorkingRule":
        return CalendarWorkingRule(
            id=generate_id(),
            calendar_id=calendar_id,
            weekday=weekday,
            is_working_day=is_working_day,
            start_time=start_time,
            end_time=end_time,
            break_start_time=break_start_time,
            break_end_time=break_end_time,
            break_minutes=break_minutes,
            hours_override=hours_override,
            shift_code=shift_code,
            effective_from=effective_from,
            effective_to=effective_to,
            priority=priority,
        )

    def compute_hours(self) -> float:
        if not self.is_working_day:
            return 0.0
        if self.hours_override is not None:
            return self.hours_override
        if self.start_time and self.end_time:
            start_min = self.start_time.hour * 60 + self.start_time.minute
            end_min = self.end_time.hour * 60 + self.end_time.minute
            total_min = max(0, end_min - start_min - self.break_minutes)
            return total_min / 60.0
        return 8.0


@validated_dataclass
class CalendarException:
    id: str
    calendar_id: str
    exception_date: date
    exception_type: str
    name: str
    impact_type: str
    scope_type: str | None = None
    scope_id: str | None = None
    description: str | None = None
    start_time: time | None = None
    end_time: time | None = None
    hours_override: float | None = None
    priority: int = 0
    approval_status: str = "APPROVED"
    approved_by: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None

    @field_validator("calendar_id", mode="before")
    @classmethod
    def _validate_calendar_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar ID is required.",
            code="CALENDAR_EXCEPTION_CALENDAR_REQUIRED",
        )

    @field_validator("exception_date", mode="before")
    @classmethod
    def _validate_exception_date(cls, value: object) -> date:
        return _normalize_required_date(
            value,
            message="Exception date is required.",
            code="CALENDAR_EXCEPTION_DATE_REQUIRED",
        )

    @field_validator("exception_type", mode="before")
    @classmethod
    def _validate_exception_type(cls, value: object) -> str:
        return _normalize_required_choice(
            value,
            valid_values=_VALID_EXCEPTION_TYPES,
            aliases=None,
            empty_message="Exception type is required.",
            invalid_message=(
                "Invalid exception_type '{value}'. "
                f"Valid: {sorted(_VALID_EXCEPTION_TYPES)}"
            ),
            code="CALENDAR_EXCEPTION_TYPE_INVALID",
        )

    @field_validator("name", mode="before")
    @classmethod
    def _validate_exception_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Exception name is required.",
            code="CALENDAR_EXCEPTION_NAME_REQUIRED",
        )

    @field_validator("impact_type", mode="before")
    @classmethod
    def _validate_impact_type(cls, value: object) -> str:
        return _normalize_required_choice(
            value,
            valid_values=_VALID_IMPACT_TYPES,
            aliases=_IMPACT_TYPE_ALIASES,
            empty_message="Impact type is required.",
            invalid_message=(
                "Invalid impact_type '{value}'. "
                f"Valid: {sorted(_VALID_IMPACT_TYPES)}"
            ),
            code="CALENDAR_IMPACT_TYPE_INVALID",
        )

    @field_validator("scope_type", mode="before")
    @classmethod
    def _normalize_scope_type(cls, value: object) -> str | None:
        return _normalize_optional_scope_type(value)

    @field_validator("scope_id", mode="before")
    @classmethod
    def _normalize_scope_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("description", "approved_by", "created_by", "updated_by", mode="before")
    @classmethod
    def _normalize_optional_text_fields(cls, value: object) -> str | None:
        return _normalize_optional_free_text(value)

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def _validate_times(cls, value: object) -> time | None:
        return _normalize_optional_time(value)

    @field_validator("hours_override", mode="before")
    @classmethod
    def _validate_hours_override(cls, value: object) -> float | None:
        return _normalize_non_negative_float(
            value,
            code="CALENDAR_EXCEPTION_HOURS_INVALID",
            message="hours_override must be non-negative.",
        )

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, value: object) -> int:
        return _normalize_int(value, default=0)

    @field_validator("approval_status", mode="before")
    @classmethod
    def _validate_approval_status(cls, value: object) -> str:
        return _normalize_required_choice(
            value,
            valid_values=_VALID_APPROVAL_STATUSES,
            aliases=None,
            empty_message="Approval status is required.",
            invalid_message=(
                "Invalid approval_status '{value}'. "
                f"Valid: {sorted(_VALID_APPROVAL_STATUSES)}"
            ),
            code="CALENDAR_APPROVAL_STATUS_INVALID",
        )

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object) -> datetime | None:
        return _normalize_optional_datetime(value)

    @model_validator(mode="after")
    def _validate_time_window(self) -> "CalendarException":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        ):
            raise ValidationError(
                "Exception end_time must be after start_time.",
                code="CALENDAR_EXCEPTION_TIME_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        calendar_id: str,
        exception_date: date,
        exception_type: str,
        name: str,
        impact_type: str,
        *,
        scope_type: str | None = None,
        scope_id: str | None = None,
        description: str | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
        hours_override: float | None = None,
        priority: int = 0,
        approval_status: str = "APPROVED",
        created_by: str | None = None,
    ) -> "CalendarException":
        now = datetime.now(dt_timezone.utc)
        return CalendarException(
            id=generate_id(),
            calendar_id=calendar_id,
            exception_date=exception_date,
            exception_type=exception_type,
            name=name,
            impact_type=impact_type,
            scope_type=scope_type,
            scope_id=scope_id,
            description=description,
            start_time=start_time,
            end_time=end_time,
            hours_override=hours_override,
            priority=priority,
            approval_status=approval_status,
            created_by=created_by,
            created_at=now,
            updated_by=created_by,
            updated_at=now,
        )

    def compute_hours(self) -> float:
        if self.hours_override is not None:
            return self.hours_override
        if self.start_time and self.end_time:
            start_min = self.start_time.hour * 60 + self.start_time.minute
            end_min = self.end_time.hour * 60 + self.end_time.minute
            return max(0, end_min - start_min) / 60.0
        return 0.0


@validated_dataclass
class CalendarRecurringEvent:
    id: str
    calendar_id: str
    title: str
    event_type: str
    recurrence_rule: str
    start_time: time
    end_time: time
    impact_type: str
    effective_from: date
    scope_type: str | None = None
    scope_id: str | None = None
    capacity_impact_percent: float | None = None
    effective_to: date | None = None
    is_active: bool = True
    priority: int = 0

    @field_validator("calendar_id", mode="before")
    @classmethod
    def _validate_calendar_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar ID is required.",
            code="RECURRING_EVENT_CALENDAR_REQUIRED",
        )

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Recurring event title is required.",
            code="RECURRING_EVENT_TITLE_REQUIRED",
        )

    @field_validator("event_type", mode="before")
    @classmethod
    def _validate_event_type(cls, value: object) -> str:
        return _normalize_required_choice(
            value,
            valid_values=_VALID_RECURRING_EVENT_TYPES,
            aliases=_RECURRING_EVENT_TYPE_ALIASES,
            empty_message="Event type is required.",
            invalid_message=(
                "Invalid event_type '{value}'. "
                f"Valid: {sorted(_VALID_RECURRING_EVENT_TYPES)}"
            ),
            code="RECURRING_EVENT_TYPE_INVALID",
        )

    @field_validator("recurrence_rule", mode="before")
    @classmethod
    def _validate_recurrence_rule(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Recurrence rule is required.",
            code="RECURRING_EVENT_RULE_REQUIRED",
        )

    @field_validator("start_time", mode="before")
    @classmethod
    def _validate_start_time(cls, value: object) -> time:
        return _normalize_required_time(
            value,
            message="Recurring event start_time is required.",
            code="RECURRING_EVENT_START_TIME_REQUIRED",
        )

    @field_validator("end_time", mode="before")
    @classmethod
    def _validate_end_time(cls, value: object) -> time:
        return _normalize_required_time(
            value,
            message="Recurring event end_time is required.",
            code="RECURRING_EVENT_END_TIME_REQUIRED",
        )

    @field_validator("impact_type", mode="before")
    @classmethod
    def _validate_impact_type(cls, value: object) -> str:
        return _normalize_required_choice(
            value,
            valid_values=_VALID_IMPACT_TYPES,
            aliases=_IMPACT_TYPE_ALIASES,
            empty_message="Impact type is required.",
            invalid_message=(
                "Invalid impact_type '{value}'. "
                f"Valid: {sorted(_VALID_IMPACT_TYPES)}"
            ),
            code="RECURRING_EVENT_IMPACT_TYPE_INVALID",
        )

    @field_validator("effective_from", mode="before")
    @classmethod
    def _validate_effective_from(cls, value: object) -> date:
        return _normalize_required_date(
            value,
            message="effective_from is required.",
            code="RECURRING_EVENT_EFFECTIVE_FROM_REQUIRED",
        )

    @field_validator("scope_type", mode="before")
    @classmethod
    def _normalize_scope_type(cls, value: object) -> str | None:
        return _normalize_optional_scope_type(value)

    @field_validator("scope_id", mode="before")
    @classmethod
    def _normalize_scope_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("capacity_impact_percent", mode="before")
    @classmethod
    def _validate_capacity_impact_percent(cls, value: object) -> float | None:
        return _normalize_non_negative_float(
            value,
            code="RECURRING_EVENT_CAPACITY_IMPACT_INVALID",
            message="capacity_impact_percent must be non-negative.",
        )

    @field_validator("effective_to", mode="before")
    @classmethod
    def _validate_effective_to(cls, value: object) -> date | None:
        return _normalize_optional_date(value)

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, value: object) -> int:
        return _normalize_int(value, default=0)

    @model_validator(mode="after")
    def _validate_event_window(self) -> "CalendarRecurringEvent":
        if self.end_time <= self.start_time:
            raise ValidationError(
                "start_time must be before end_time.",
                code="RECURRING_EVENT_TIME_RANGE_INVALID",
            )
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValidationError(
                "effective_to must be after effective_from.",
                code="RECURRING_EVENT_DATE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        calendar_id: str,
        title: str,
        event_type: str,
        recurrence_rule: str,
        start_time: time,
        end_time: time,
        impact_type: str,
        effective_from: date,
        *,
        scope_type: str | None = None,
        scope_id: str | None = None,
        capacity_impact_percent: float | None = None,
        effective_to: date | None = None,
        priority: int = 0,
    ) -> "CalendarRecurringEvent":
        return CalendarRecurringEvent(
            id=generate_id(),
            calendar_id=calendar_id,
            title=title,
            event_type=event_type,
            recurrence_rule=recurrence_rule,
            start_time=start_time,
            end_time=end_time,
            impact_type=impact_type,
            effective_from=effective_from,
            scope_type=scope_type,
            scope_id=scope_id,
            capacity_impact_percent=capacity_impact_percent,
            effective_to=effective_to,
            is_active=True,
            priority=priority,
        )

    def duration_hours(self) -> float:
        start_min = self.start_time.hour * 60 + self.start_time.minute
        end_min = self.end_time.hour * 60 + self.end_time.minute
        return max(0, end_min - start_min) / 60.0


@validated_dataclass
class ShiftPattern:
    id: str
    organization_id: str
    code: str
    name: str
    pattern_type: str
    timezone: str = "UTC"
    description: str | None = None
    rotation_cycle_days: int | None = None
    is_active: bool = True

    @field_validator("organization_id", mode="before")
    @classmethod
    def _validate_organization_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization ID is required.",
            code="SHIFT_PATTERN_ORGANIZATION_REQUIRED",
        )

    @field_validator("code", mode="before")
    @classmethod
    def _validate_code(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Shift pattern code is required.",
            code="SHIFT_PATTERN_CODE_REQUIRED",
        ).upper()

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Shift pattern name is required.",
            code="SHIFT_PATTERN_NAME_REQUIRED",
        )

    @field_validator("pattern_type", mode="before")
    @classmethod
    def _validate_pattern_type(cls, value: object) -> str:
        return _normalize_required_choice(
            value,
            valid_values=_VALID_PATTERN_TYPES,
            aliases=_PATTERN_TYPE_ALIASES,
            empty_message="Pattern type is required.",
            invalid_message=(
                "Invalid pattern_type '{value}'. "
                f"Valid: {sorted(_VALID_PATTERN_TYPES)}"
            ),
            code="SHIFT_PATTERN_TYPE_INVALID",
        )

    @field_validator("timezone", mode="before")
    @classmethod
    def _normalize_timezone(cls, value: object) -> str:
        return normalize_optional_text(value) or "UTC"

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: object) -> str | None:
        return _normalize_optional_free_text(value)

    @field_validator("rotation_cycle_days", mode="before")
    @classmethod
    def _validate_rotation_cycle_days(cls, value: object) -> int | None:
        if value in (None, ""):
            return None
        return _normalize_positive_int(
            value,
            code="SHIFT_PATTERN_ROTATION_INVALID",
            message="rotation_cycle_days must be positive.",
        )

    @staticmethod
    def create(
        organization_id: str,
        code: str,
        name: str,
        pattern_type: str,
        *,
        timezone: str = "UTC",
        description: str | None = None,
        rotation_cycle_days: int | None = None,
    ) -> "ShiftPattern":
        return ShiftPattern(
            id=generate_id(),
            organization_id=organization_id,
            code=code,
            name=name,
            pattern_type=pattern_type,
            timezone=timezone,
            description=description,
            rotation_cycle_days=rotation_cycle_days,
            is_active=True,
        )


@validated_dataclass
class ShiftPatternDay:
    id: str
    shift_pattern_id: str
    day_offset: int
    is_working_day: bool = True
    start_time: time | None = None
    end_time: time | None = None
    break_minutes: int = 0
    hours: float | None = None
    shift_label: str | None = None

    @field_validator("shift_pattern_id", mode="before")
    @classmethod
    def _validate_shift_pattern_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Shift pattern ID is required.",
            code="SHIFT_PATTERN_DAY_PATTERN_REQUIRED",
        )

    @field_validator("day_offset", mode="before")
    @classmethod
    def _validate_day_offset(cls, value: object) -> int:
        return _normalize_non_negative_int(
            value,
            code="SHIFT_PATTERN_DAY_OFFSET_INVALID",
            message="day_offset must be >= 0.",
        )

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def _validate_times(cls, value: object) -> time | None:
        return _normalize_optional_time(value)

    @field_validator("break_minutes", mode="before")
    @classmethod
    def _validate_break_minutes(cls, value: object) -> int:
        return _normalize_non_negative_int(
            value,
            code="SHIFT_PATTERN_BREAK_MINUTES_INVALID",
            message="break_minutes must be non-negative.",
        )

    @field_validator("hours", mode="before")
    @classmethod
    def _validate_hours(cls, value: object) -> float | None:
        return _normalize_non_negative_float(
            value,
            code="SHIFT_PATTERN_DAY_HOURS_INVALID",
            message="hours must be non-negative.",
        )

    @field_validator("shift_label", mode="before")
    @classmethod
    def _normalize_shift_label(cls, value: object) -> str | None:
        return _normalize_optional_free_text(value)

    @model_validator(mode="after")
    def _validate_time_window(self) -> "ShiftPatternDay":
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        ):
            raise ValidationError(
                "start_time must be before end_time.",
                code="SHIFT_PATTERN_DAY_TIME_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        shift_pattern_id: str,
        day_offset: int,
        *,
        is_working_day: bool = True,
        start_time: time | None = None,
        end_time: time | None = None,
        break_minutes: int = 0,
        hours: float | None = None,
        shift_label: str | None = None,
    ) -> "ShiftPatternDay":
        return ShiftPatternDay(
            id=generate_id(),
            shift_pattern_id=shift_pattern_id,
            day_offset=day_offset,
            is_working_day=is_working_day,
            start_time=start_time,
            end_time=end_time,
            break_minutes=break_minutes,
            hours=hours,
            shift_label=shift_label,
        )


@validated_dataclass
class SiteCalendarAssignment:
    id: str
    site_id: str
    calendar_id: str
    effective_from: date | None = None
    effective_to: date | None = None
    is_default: bool = False
    priority: int = 0

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Site calendar assignment ID is required.",
            code="SITE_CALENDAR_ASSIGNMENT_ID_REQUIRED",
        )

    @field_validator("site_id", mode="before")
    @classmethod
    def _validate_site_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Site ID is required.",
            code="SITE_CALENDAR_ASSIGNMENT_SITE_REQUIRED",
        )

    @field_validator("calendar_id", mode="before")
    @classmethod
    def _validate_calendar_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar ID is required.",
            code="SITE_CALENDAR_ASSIGNMENT_CALENDAR_REQUIRED",
        )

    @field_validator("effective_from", "effective_to", mode="before")
    @classmethod
    def _validate_dates(cls, value: object) -> date | None:
        return _normalize_optional_date(value)

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, value: object) -> int:
        return _normalize_int(value, default=0)

    @model_validator(mode="after")
    def _validate_effective_range(self) -> "SiteCalendarAssignment":
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValidationError(
                "effective_to must be after effective_from.",
                code="SITE_CALENDAR_ASSIGNMENT_DATE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        site_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> "SiteCalendarAssignment":
        return SiteCalendarAssignment(
            id=generate_id(),
            site_id=site_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )


@validated_dataclass
class DepartmentCalendarAssignment:
    id: str
    department_id: str
    calendar_id: str
    effective_from: date | None = None
    effective_to: date | None = None
    is_default: bool = False
    priority: int = 0

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Department calendar assignment ID is required.",
            code="DEPARTMENT_CALENDAR_ASSIGNMENT_ID_REQUIRED",
        )

    @field_validator("department_id", mode="before")
    @classmethod
    def _validate_department_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Department ID is required.",
            code="DEPARTMENT_CALENDAR_ASSIGNMENT_DEPARTMENT_REQUIRED",
        )

    @field_validator("calendar_id", mode="before")
    @classmethod
    def _validate_calendar_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar ID is required.",
            code="DEPARTMENT_CALENDAR_ASSIGNMENT_CALENDAR_REQUIRED",
        )

    @field_validator("effective_from", "effective_to", mode="before")
    @classmethod
    def _validate_dates(cls, value: object) -> date | None:
        return _normalize_optional_date(value)

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, value: object) -> int:
        return _normalize_int(value, default=0)

    @model_validator(mode="after")
    def _validate_effective_range(self) -> "DepartmentCalendarAssignment":
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValidationError(
                "effective_to must be after effective_from.",
                code="DEPARTMENT_CALENDAR_ASSIGNMENT_DATE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        department_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> "DepartmentCalendarAssignment":
        return DepartmentCalendarAssignment(
            id=generate_id(),
            department_id=department_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )


@validated_dataclass
class EmployeeCalendarAssignment:
    id: str
    employee_id: str
    calendar_id: str
    effective_from: date | None = None
    effective_to: date | None = None
    is_default: bool = False
    priority: int = 0

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Employee calendar assignment ID is required.",
            code="EMPLOYEE_CALENDAR_ASSIGNMENT_ID_REQUIRED",
        )

    @field_validator("employee_id", mode="before")
    @classmethod
    def _validate_employee_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Employee ID is required.",
            code="EMPLOYEE_CALENDAR_ASSIGNMENT_EMPLOYEE_REQUIRED",
        )

    @field_validator("calendar_id", mode="before")
    @classmethod
    def _validate_calendar_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar ID is required.",
            code="EMPLOYEE_CALENDAR_ASSIGNMENT_CALENDAR_REQUIRED",
        )

    @field_validator("effective_from", "effective_to", mode="before")
    @classmethod
    def _validate_dates(cls, value: object) -> date | None:
        return _normalize_optional_date(value)

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, value: object) -> int:
        return _normalize_int(value, default=0)

    @model_validator(mode="after")
    def _validate_effective_range(self) -> "EmployeeCalendarAssignment":
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValidationError(
                "effective_to must be after effective_from.",
                code="EMPLOYEE_CALENDAR_ASSIGNMENT_DATE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        employee_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> "EmployeeCalendarAssignment":
        return EmployeeCalendarAssignment(
            id=generate_id(),
            employee_id=employee_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )


__all__ = [
    "ApprovalStatus",
    "CalendarException",
    "CalendarRecurringEvent",
    "CalendarType",
    "CalendarWorkingRule",
    "DepartmentCalendarAssignment",
    "EmployeeCalendarAssignment",
    "ExceptionType",
    "ImpactType",
    "PatternType",
    "PlatformCalendar",
    "RecurringEventType",
    "ShiftPattern",
    "ShiftPatternDay",
    "SiteCalendarAssignment",
]
