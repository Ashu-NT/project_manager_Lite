from __future__ import annotations


def build_calendar_create_command(payload: dict):
    from src.api.desktop.platform.models.enterprise_calendar import CalendarCreateCommand
    return CalendarCreateCommand(
        code=str(payload.get("code", "")),
        name=str(payload.get("name", "")),
        calendar_type=str(payload.get("calendarType", "GLOBAL")),
        timezone=str(payload.get("timezone", "UTC")),
        description=str(payload.get("description", "")),
        is_default=bool(payload.get("isDefault", False)),
    )


def build_calendar_update_command(payload: dict):
    from src.api.desktop.platform.models.enterprise_calendar import CalendarUpdateCommand
    return CalendarUpdateCommand(
        calendar_id=str(payload.get("calendarId", "")),
        name=str(payload.get("name", "")),
        timezone=str(payload.get("timezone", "")),
        description=str(payload.get("description", "")),
    )


def build_exception_create_command(payload: dict):
    from src.api.desktop.platform.models.enterprise_calendar import ExceptionCreateCommand
    return ExceptionCreateCommand(
        calendar_id=str(payload.get("calendarId", "")),
        exception_date=str(payload.get("exceptionDate", "")),
        exception_type=str(payload.get("exceptionType", "HOLIDAY")),
        name=str(payload.get("name", "")),
        impact_type=str(payload.get("impactType", "UNAVAILABLE")),
        description=str(payload.get("description", "")),
        hours_override=float(payload.get("hoursOverride", 0.0) or 0.0),
    )


def build_recurring_event_create_command(payload: dict):
    from src.api.desktop.platform.models.enterprise_calendar import RecurringEventCreateCommand
    return RecurringEventCreateCommand(
        calendar_id=str(payload.get("calendarId", "")),
        title=str(payload.get("title", "")),
        event_type=str(payload.get("eventType", "MEETING")),
        recurrence_rule=str(payload.get("recurrenceRule", "")),
        start_time=str(payload.get("startTime", "")),
        end_time=str(payload.get("endTime", "")),
        impact_type=str(payload.get("impactType", "UNAVAILABLE")),
        effective_from=str(payload.get("effectiveFrom", "")),
        effective_to=str(payload.get("effectiveTo", "")),
    )


def dispatch_calendar_assign(controller, payload: dict, entity_type: str):
    if controller._enterprise_calendar_api is None:
        return None
    from src.api.desktop.platform.models.enterprise_calendar import (
        DeptCalendarAssignCommand,
        EmpCalendarAssignCommand,
        ProjectCalendarAssignCommand,
        ResourceCalendarAssignCommand,
        SiteCalendarAssignCommand,
    )
    cal_id = str(payload.get("calendarId", ""))
    eff_from = str(payload.get("effectiveFrom", ""))
    eff_to = str(payload.get("effectiveTo", ""))
    entity_id = str(payload.get("entityId", ""))
    if entity_type == "site":
        return controller._enterprise_calendar_api.assign_site_calendar(
            SiteCalendarAssignCommand(
                site_id=entity_id, calendar_id=cal_id,
                effective_from=eff_from, effective_to=eff_to,
            )
        )
    if entity_type == "department":
        return controller._enterprise_calendar_api.assign_department_calendar(
            DeptCalendarAssignCommand(
                department_id=entity_id, calendar_id=cal_id,
                effective_from=eff_from, effective_to=eff_to,
            )
        )
    if entity_type == "employee":
        return controller._enterprise_calendar_api.assign_employee_calendar(
            EmpCalendarAssignCommand(
                employee_id=entity_id, calendar_id=cal_id,
                effective_from=eff_from, effective_to=eff_to,
            )
        )
    if entity_type == "project":
        return controller._enterprise_calendar_api.assign_project_calendar(
            ProjectCalendarAssignCommand(
                project_id=entity_id, calendar_id=cal_id,
                effective_from=eff_from, effective_to=eff_to,
            )
        )
    if entity_type == "resource":
        return controller._enterprise_calendar_api.assign_resource_calendar(
            ResourceCalendarAssignCommand(
                resource_id=entity_id, calendar_id=cal_id,
                effective_from=eff_from, effective_to=eff_to,
            )
        )
    return None


__all__ = [
    "build_calendar_create_command",
    "build_calendar_update_command",
    "build_exception_create_command",
    "build_recurring_event_create_command",
    "dispatch_calendar_assign",
]
