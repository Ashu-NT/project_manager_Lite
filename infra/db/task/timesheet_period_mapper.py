from __future__ import annotations

from core.models import TimesheetPeriod
from infra.db.models import TimesheetPeriodORM


def timesheet_period_to_orm(period: TimesheetPeriod) -> TimesheetPeriodORM:
    return TimesheetPeriodORM(
        id=period.id,
        resource_id=period.resource_id,
        period_start=period.period_start,
        period_end=period.period_end,
        status=period.status,
        submitted_at=period.submitted_at,
        submitted_by_user_id=period.submitted_by_user_id,
        submitted_by_username=period.submitted_by_username,
        decided_at=period.decided_at,
        decided_by_user_id=period.decided_by_user_id,
        decided_by_username=period.decided_by_username,
        decision_note=period.decision_note,
        locked_at=period.locked_at,
    )


def timesheet_period_from_orm(obj: TimesheetPeriodORM) -> TimesheetPeriod:
    return TimesheetPeriod(
        id=obj.id,
        resource_id=obj.resource_id,
        period_start=obj.period_start,
        period_end=obj.period_end,
        status=obj.status,
        submitted_at=obj.submitted_at,
        submitted_by_user_id=obj.submitted_by_user_id,
        submitted_by_username=obj.submitted_by_username,
        decided_at=obj.decided_at,
        decided_by_user_id=obj.decided_by_user_id,
        decided_by_username=obj.decided_by_username,
        decision_note=obj.decision_note,
        locked_at=obj.locked_at,
    )


__all__ = ["timesheet_period_to_orm", "timesheet_period_from_orm"]
