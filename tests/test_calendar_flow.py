from datetime import date


def test_work_calendar_and_holiday_effect(services):
    wc_s = services["work_calendar_service"]
    wc_engine = services["work_calendar_engine"]
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]

    # Set Mon-Fri as working days, 8h/day
    wc_s.set_working_days({0, 1, 2, 3, 4}, hours_per_day=8.0)

    # Add a holiday on 2023-11-08 (Wed)
    h = wc_s.add_holiday(date(2023, 11, 8), "Mid-week break")

    # Create project and one task of 3 working days starting 2023-11-07 (Tue)
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

    # Working days: Tue(7), Thu(9), Fri(10)  -> because Wed(8) is holiday
    assert info.earliest_start == date(2023, 11, 7)
    assert info.earliest_finish == date(2023, 11, 10)