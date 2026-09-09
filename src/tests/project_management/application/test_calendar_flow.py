"""Calendar flow tests — verifies enterprise calendar rules are respected by the scheduling engine."""

from datetime import date


def test_enterprise_calendar_holiday_blocks_scheduling_day(services):
    """
    Scheduling engine uses the enterprise calendar.
    A holiday exception on Wed 2023-11-08 means a 3-working-day task starting Tue 2023-11-07
    finishes on Fri 2023-11-10 (Tue, Thu, Fri — Wed skipped as holiday).
    """
    exc_svc = services["calendar_exception_service"]
    cal_svc = services["enterprise_calendar_service"]
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]

    # Find the global enterprise calendar (bootstrapped on startup)
    global_calendars = cal_svc.list_calendars(calendar_type="GLOBAL")
    assert global_calendars, "Global enterprise calendar must exist"
    global_cal_id = global_calendars[0].id

    # Add holiday exception on Wednesday 2023-11-08
    exc_svc.add_exception(
        global_cal_id,
        exception_date=date(2023, 11, 8),
        exception_type="HOLIDAY",
        name="Mid-week break",
        impact_type="UNAVAILABLE",
    )

    # Create project and 3-working-day task starting Tuesday 2023-11-07
    project = ps.create_project("Cal Test", "")
    pid = project.id
    t = ts.create_task(
        pid,
        "Task spanning holiday",
        start_date=date(2023, 11, 7),
        duration_days=3,
    )

    schedule = sched.recalculate_project_schedule(pid)
    info = schedule[t.id]

    # Working days: Tue(7), Thu(9), Fri(10) → Wed(8) is HOLIDAY, skipped
    assert info.earliest_start == date(2023, 11, 7)
    assert info.earliest_finish == date(2023, 11, 10)


def test_enterprise_calendar_global_working_week(services):
    """Global enterprise calendar returns Mon-Fri as working days by default."""
    shim = services["work_calendar_engine"]  # now GlobalCalendarShim

    assert shim.is_working_day(date(2026, 6, 1)) is True   # Monday
    assert shim.is_working_day(date(2026, 6, 5)) is True   # Friday
    assert shim.is_working_day(date(2026, 6, 6)) is False  # Saturday
    assert shim.is_working_day(date(2026, 6, 7)) is False  # Sunday

    # 5 working days from Monday → Friday
    assert shim.add_working_days(date(2026, 6, 1), 5) == date(2026, 6, 5)

    # working_days_between Mon–Fri = 5
    assert shim.working_days_between(date(2026, 6, 1), date(2026, 6, 5)) == 5
