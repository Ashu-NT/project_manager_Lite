from src.core.platform.application.time_management.calendar.capacity.dto.responses.results import (
    EffectiveCalendarDto,
    ResourceCapacityDto,
    WorkingDaysResultDto,
)


def resource_capacity_response(summary) -> ResourceCapacityDto:
    return ResourceCapacityDto(
                    resource_id=summary.resource_id,
                    start=str(summary.start),
                    end=str(summary.end),
                    base_hours=summary.base_hours,
                    available_hours=summary.available_hours,
                    assigned_hours=summary.assigned_hours,
                    remaining_hours=summary.remaining_hours,
                    capacity_percent=summary.capacity_percent,
                    utilization_percent=summary.utilization_percent,
                    working_days=summary.working_days,
                    unavailable_days=summary.unavailable_days,
                    conflicts=summary.conflicts,
                    source_chain=summary.source_chain,
                )

def working_days_response(result) -> WorkingDaysResultDto:
    return WorkingDaysResultDto(
                    start_date=str(result.start_date),
                    end_date=str(result.end_date),
                    working_days=result.working_days,
                )

def effective_calendar_response(result) -> EffectiveCalendarDto:
    return EffectiveCalendarDto(
                    has_calendar=result.has_calendar,
                    calendar_id=result.calendar_id,
                    calendar_name=result.calendar_name,
                    timezone=result.timezone,
                    source_chain=list(result.source_chain),
                )
