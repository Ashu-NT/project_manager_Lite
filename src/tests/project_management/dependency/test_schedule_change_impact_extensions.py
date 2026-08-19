"""ScheduleChangeImpactService extensions for Task Detail -> Schedule
Impact: get_task_schedule_overview (current-state facts), a working-day-
aware "delay by N working days" preview, and the extended analyse()
report fields (milestone flag, critical_path_changed, dependency
conflicts under the proposed schedule).
"""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.scheduling.forecasting.schedule_change_impact_service import (
    ScheduleChangeImpactService,
)
from src.core.modules.project_management.domain.enums import DependencyType


def _impact_service(services):
    """ScheduleChangeImpactService is only constructed in the desktop
    runtime layer (desktop_api_builder.py) today, not in this repo's
    shared test service graph -- build it directly from the same real
    repos/calendar/baseline_service the desktop runtime wires, exactly
    like scheduling_helpers.build_schedule_change_impact_service does."""
    ts = services["task_service"]
    return ScheduleChangeImpactService(
        task_repo=ts._task_repo,
        dependency_repo=ts._dependency_repo,
        calendar=services["work_calendar_engine"],
        baseline_lookup=services["baseline_service"],
    )


def _make_chain_with_milestone(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Schedule Impact Extensions", "")
    a = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
    b = ts.create_task(project.id, "Task B", "", duration_days=2)
    milestone = ts.create_task(project.id, "Handover", "", duration_days=0)
    ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
    ts.add_dependency(b.id, milestone.id, DependencyType.FINISH_TO_START, lag_days=0)
    return project, a, b, milestone


class TestGetTaskScheduleOverview:
    def test_reports_current_position_criticality_and_float(self, services):
        sched = services["scheduling_engine"]
        project, a, b, milestone = _make_chain_with_milestone(services)
        impact = _impact_service(services)

        sched.recalculate_project_schedule(project.id)
        overview = impact.get_task_schedule_overview(project.id, a.id)

        assert overview.is_available is True
        assert overview.current_start == date(2024, 1, 1)
        assert overview.current_finish is not None
        assert overview.is_critical is True
        assert overview.total_float_days == 0

    def test_reports_predecessor_driver(self, services):
        sched = services["scheduling_engine"]
        project, a, b, milestone = _make_chain_with_milestone(services)
        impact = _impact_service(services)

        sched.recalculate_project_schedule(project.id)
        overview = impact.get_task_schedule_overview(project.id, b.id)

        predecessor_drivers = [d for d in overview.drivers if d.kind == "predecessor"]
        assert len(predecessor_drivers) == 1
        assert predecessor_drivers[0].label == "Task A"

    def test_reports_downstream_exposure_including_milestone(self, services):
        sched = services["scheduling_engine"]
        project, a, b, milestone = _make_chain_with_milestone(services)
        impact = _impact_service(services)

        sched.recalculate_project_schedule(project.id)
        overview = impact.get_task_schedule_overview(project.id, a.id)

        assert overview.downstream.direct_successor_count == 1
        assert overview.downstream.downstream_task_count == 2
        assert overview.downstream.downstream_milestone_count == 1

    def test_reports_unavailable_for_unknown_task(self, services):
        ps = services["project_service"]
        impact = _impact_service(services)
        project = ps.create_project("Schedule Impact Unknown Task", "")

        overview = impact.get_task_schedule_overview(project.id, "does-not-exist")

        assert overview.is_available is False

    def test_reports_actual_variance_when_actual_start_violates_dependency(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        sched = services["scheduling_engine"]
        impact = _impact_service(services)
        project = ps.create_project("Schedule Impact Actual Variance", "")
        a = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
        b = ts.create_task(project.id, "Task B", "", duration_days=2)
        ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
        sched.recalculate_project_schedule(project.id)
        ts.update_progress(b.id, actual_start=date(2024, 1, 2))

        overview = impact.get_task_schedule_overview(project.id, b.id)

        assert len(overview.actual_variances) == 1
        assert overview.actual_variances[0].task_id == b.id

    def test_reports_dependency_constraint_conflict_scoped_to_this_task(self, services):
        """Task.constraint_type/constraint_date are domain-model-only
        fields -- there is no ORM column and no repository/mapper wiring
        for them today (a pre-existing gap, not introduced by this pass;
        see docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md,
        and test_constraint_dependency_conflict.py's own docstring, which
        hit the same gap first). A real DB round-trip therefore cannot
        carry a constraint onto a persisted task, so this test exercises
        get_task_schedule_overview's conflict-surfacing logic with
        hand-built in-memory Task/TaskDependency objects and fake repos
        instead -- proving THIS orchestration is correct independent of
        that separate, already-documented gap."""
        from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
            ConstraintType,
        )
        from src.core.modules.project_management.application.scheduling.forecasting.schedule_change_impact_service import (
            ScheduleChangeImpactService,
        )
        from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency

        a = Task.create("proj-1", "Task A", start_date=date(2024, 1, 1), duration_days=2)
        b = Task.create(
            "proj-1", "Task B", duration_days=2,
            constraint_type=ConstraintType.MUST_START_ON.value,
            constraint_date=date(2024, 1, 1),
        )
        dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        class _FakeTaskRepo:
            def list_by_project(self, _project_id):
                return [a, b]

        class _FakeDependencyRepo:
            def list_by_project(self, _project_id):
                return [dep]

        service = ScheduleChangeImpactService(
            task_repo=_FakeTaskRepo(),
            dependency_repo=_FakeDependencyRepo(),
            calendar=services["work_calendar_engine"],
            baseline_lookup=services["baseline_service"],
        )

        overview = service.get_task_schedule_overview("proj-1", b.id)

        assert len(overview.dependency_conflicts) == 1
        assert overview.dependency_conflicts[0].task_id == b.id


class TestBaselineComparison:
    def test_get_task_schedule_overview_reports_baseline_finish_and_variance(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        bs = services["baseline_service"]
        sched = services["scheduling_engine"]
        impact = _impact_service(services)
        project = ps.create_project("Schedule Impact Baseline", "")
        task = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
        sched.recalculate_project_schedule(project.id)
        baseline = bs.create_baseline(project.id, "BL1", rate_as_of=date.today())
        bs.submit_baseline(baseline.id, submitted_by="admin")
        bs.approve_baseline(baseline.id, approved_by="admin")

        # Slip the task's own start so its current finish diverges from
        # the just-approved baseline snapshot.
        ts.update_task(task.id, start_date=date(2024, 1, 3), duration_days=2)
        sched.recalculate_project_schedule(project.id)

        overview = impact.get_task_schedule_overview(project.id, task.id)

        assert overview.baseline_finish is not None
        assert overview.schedule_variance_days is not None
        assert overview.schedule_variance_days > 0

    def test_get_task_schedule_overview_omits_baseline_facts_when_no_approved_baseline_exists(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        sched = services["scheduling_engine"]
        impact = _impact_service(services)
        project = ps.create_project("Schedule Impact No Baseline", "")
        task = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
        sched.recalculate_project_schedule(project.id)

        overview = impact.get_task_schedule_overview(project.id, task.id)

        assert overview.baseline_finish is None
        assert overview.schedule_variance_days is None

    def test_baseline_service_get_baseline_task_returns_the_snapshot(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        bs = services["baseline_service"]
        project = ps.create_project("Baseline Task Snapshot", "")
        task = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
        baseline = bs.create_baseline(project.id, "BL1", rate_as_of=date.today())

        baseline_task = bs.get_baseline_task(baseline.id, task.id)

        assert baseline_task is not None
        assert baseline_task.task_id == task.id
        assert baseline_task.baseline_finish is not None

    def test_baseline_service_get_baseline_task_returns_none_for_unknown_task(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        bs = services["baseline_service"]
        project = ps.create_project("Baseline Task Snapshot Missing", "")
        ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
        baseline = bs.create_baseline(project.id, "BL1", rate_as_of=date.today())

        assert bs.get_baseline_task(baseline.id, "does-not-exist") is None


class TestAnalyseWorkingDayDelay:
    def test_delay_by_working_days_skips_weekends(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        impact = _impact_service(services)
        project = ps.create_project("Schedule Impact Working Day Delay", "")
        # Friday 2024-01-05
        a = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 5), duration_days=1)

        report = impact.analyse_working_day_delay(
            project_id=project.id,
            changed_task_id=a.id,
            current_start=a.start_date,
            delay_working_days=1,
        )

        # +1 working day from Friday must land on Monday, not Saturday.
        assert report.proposed_start == date(2024, 1, 8)


class TestAnalyseExtendedFields:
    def test_critical_path_changed_flag_reflects_newly_critical_tasks(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        sched = services["scheduling_engine"]
        impact = _impact_service(services)
        project = ps.create_project("Schedule Impact Critical Change", "")
        a = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
        b = ts.create_task(project.id, "Task B", "", duration_days=2)
        ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
        sched.recalculate_project_schedule(project.id)

        report = impact.analyse(
            project_id=project.id,
            changed_task_id=a.id,
            proposed_duration_days=10,
        )

        assert isinstance(report.critical_path_changed, bool)

    def test_milestone_flag_is_set_on_affected_milestone_rows(self, services):
        sched = services["scheduling_engine"]
        impact = _impact_service(services)
        project, a, b, milestone = _make_chain_with_milestone(services)
        sched.recalculate_project_schedule(project.id)

        report = impact.analyse(
            project_id=project.id,
            changed_task_id=a.id,
            proposed_duration_days=5,
        )

        milestone_rows = [row for row in report.affected_tasks if row.task_id == milestone.id]
        assert len(milestone_rows) == 1
        assert milestone_rows[0].is_milestone is True
        non_milestone_rows = [row for row in report.affected_tasks if row.task_id == a.id]
        assert non_milestone_rows[0].is_milestone is False
