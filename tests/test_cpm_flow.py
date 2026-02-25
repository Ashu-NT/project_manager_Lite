from datetime import date

from core.models import DependencyType
from core.exceptions import BusinessRuleError

def test_cpm_forward_backward_basic(services):
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]
    wc = services["work_calendar_engine"]

    # 1) Create project
    project = ps.create_project("CPM Test", "Testing CPM")
    pid = project.id

    # 2) Create three tasks
    # A: start fixed, 2 working days
    tA = ts.create_task(pid, "Task A", "Start", start_date=date(2023, 11, 6), duration_days=2)
    # B: depends FS on A, 3 days
    tB = ts.create_task(pid, "Task B", "Middle", duration_days=3)
    # C: depends FF on B, 1 day
    tC = ts.create_task(pid, "Task C", "End", duration_days=1)

    # 3) Add dependencies:
    # A -> B (FS, lag 0)
    ts.add_dependency(tA.id, tB.id, DependencyType.FINISH_TO_START, lag_days=0)
    # B -> C (FF, lag 0)
    ts.add_dependency(tB.id, tC.id, DependencyType.FINISH_TO_FINISH, lag_days=0)

    # 4) Recalculate schedule (CPM)
    schedule = sched.recalculate_project_schedule(pid)

    infoA = schedule[tA.id]
    infoB = schedule[tB.id]
    infoC = schedule[tC.id]

    # A's ES is its given start
    assert infoA.earliest_start == date(2023, 11, 6)

    # B starts the next working day after A finishes (FS, lag 0).
    assert infoB.earliest_start == wc.next_working_day(infoA.earliest_finish, include_today=False)

    # C's EF equals B's EF (FF)
    assert infoC.earliest_finish == infoB.earliest_finish

    # There is at least one critical task
    crit_tasks = [i for i in schedule.values() if i.is_critical]
    assert len(crit_tasks) >= 1

def test_cpm_cycle_detection(services):
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("Cycle Test", "")
    pid = project.id

    # Give at least one task a start_date so scheduling would work if there were no cycle
    t1 = ts.create_task(pid, "T01", start_date=date(2023, 11, 6), duration_days=1)
    t2 = ts.create_task(pid, "T02", duration_days=1)

    # t1 -> t2
    ts.add_dependency(t1.id, t2.id, DependencyType.FINISH_TO_START, lag_days=0)

    # t2 -> t1 should be rejected as a cycle
    try:
        ts.add_dependency(t2.id, t1.id, DependencyType.FINISH_TO_START, lag_days=0)
        assert False, "Expected BusinessRuleError for circular dependency"
    except BusinessRuleError:
        pass

    # Optional: CPM should now run fine (since cycle was blocked)
    schedule = sched.recalculate_project_schedule(pid)
    assert t1.id in schedule and t2.id in schedule
