"""User-reported bugs against Task Detail -> Schedule Impact and the
Dependencies mutation refresh path:

1. A summary/parent task (has sub-tasks) always reported "not available"
   with the SAME generic message as a leaf task with no dates -- even
   when it had its own start_date set. select_leaf_tasks correctly
   excludes summary tasks from CPM (they're not independently
   scheduled), but the UI gave no way to tell that apart from "you
   haven't set a date yet." Fixed via unavailable_reason.
2/3. Adding/editing/removing a dependency did not refresh the
   Dependencies table or Schedule Impact facts for the currently
   selected task until the user left and re-entered Task Detail -- the
   shared facade_refresh only rebuilt the task list, never per-section
   detail state. Fixed via a dependency-specific facade_refresh that
   forces an immediate, targeted reload.
"""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.scheduling.forecasting.schedule_change_impact_service import (
    ScheduleChangeImpactService,
)
from src.core.modules.project_management.domain.enums import DependencyType


def _impact_service(services):
    ts = services["task_service"]
    return ScheduleChangeImpactService(
        task_repo=ts._task_repo,
        dependency_repo=ts._dependency_repo,
        calendar=services["work_calendar_engine"],
        baseline_lookup=services["baseline_service"],
    )


class TestUnavailableReason:
    def test_summary_task_with_its_own_start_date_reports_summary_task_reason(self, services):
        """The exact reported scenario: parent has a start_date set, but
        is still correctly excluded from CPM because it has a child --
        the reason must say so, not the generic "needs a start date"."""
        ps = services["project_service"]
        ts = services["task_service"]
        project = ps.create_project("Schedule Impact Summary Task", "")
        parent = ts.create_task(
            project.id, "Phase 1", "", start_date=date(2024, 1, 1), duration_days=5
        )
        ts.create_task(project.id, "Sub-task", "", parent_task_id=parent.id, duration_days=2)
        impact = _impact_service(services)

        overview = impact.get_task_schedule_overview(project.id, parent.id)

        assert overview.is_available is False
        assert overview.unavailable_reason == "summary_task"

    def test_unknown_task_id_reports_not_found_reason(self, services):
        ps = services["project_service"]
        project = ps.create_project("Schedule Impact Not Found", "")
        impact = _impact_service(services)

        overview = impact.get_task_schedule_overview(project.id, "does-not-exist")

        assert overview.is_available is False
        assert overview.unavailable_reason == "not_found"

    def test_leaf_task_reports_no_computed_date_reason_when_cpm_produces_no_entry(self, services):
        """The defensive branch for "task exists, is a genuine leaf, but
        CPM's schedule dict has no entry for it." Not reproducible
        end-to-end through run_cpm's real forward pass in practice --
        its "unanchored root" fallback patches every date-less root
        (cascading through any dependency chain) to a synthetic default
        start, so a real leaf task essentially always ends up with SOME
        computed date. Exercised directly via the injectable _run_cpm
        seam instead, matching test_schedule_impact_da5.py's convention,
        so this defensive branch has real coverage without depending on
        constructing an artificial CPM edge case."""
        from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import CPMResult

        ps = services["project_service"]
        ts = services["task_service"]
        project = ps.create_project("Schedule Impact No Computed Date", "")
        task = ts.create_task(project.id, "Untouched", "", start_date=date(2024, 1, 1), duration_days=2)
        impact = _impact_service(services)
        impact._run_cpm = lambda _calendar, _tasks_by_id, _deps: CPMResult(
            schedule={}, project_early_finish=None, critical_path_task_ids=[]
        )

        overview = impact.get_task_schedule_overview(project.id, task.id)

        assert overview.is_available is False
        assert overview.unavailable_reason == "no_computed_date"

    def test_leaf_task_with_a_start_date_is_available(self, services):
        """Regression guard: a normal leaf task with its own start_date
        must be available -- confirms the reason logic did not
        accidentally regress the common case."""
        ps = services["project_service"]
        ts = services["task_service"]
        project = ps.create_project("Schedule Impact Leaf Available", "")
        task = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
        impact = _impact_service(services)

        overview = impact.get_task_schedule_overview(project.id, task.id)

        assert overview.is_available is True
        assert overview.unavailable_reason == ""


class TestDependencyMutationRefresh:
    def test_refresh_after_dependency_mutation_reloads_dependencies_without_reactivation(self):
        from types import SimpleNamespace
        from src.ui_qml.modules.project_management.controllers.tasks.task_lazy_section_loader import (
            refresh_after_dependency_mutation,
        )

        calls: list[str] = []

        class _Presenter:
            def build_task_dependencies_state(self, **_kwargs):
                calls.append("dependencies")
                return SimpleNamespace()

            def build_task_schedule_overview_state(self, **_kwargs):
                calls.append("schedule_impact")
                return {}

            def build_task_basic_detail_state(self, **_kwargs):
                calls.append("basic_detail")
                return SimpleNamespace(selected_task_id="task-1")

        class _DependenciesCtrl:
            def _update(self, _ws):
                pass

        class _TaskList:
            def updateSelectedTaskOnly(self, _ws):
                calls.append("task_list_update")

        controller = SimpleNamespace(
            _selected_task_id="task-1",
            _selected_project_id="project-1",
            _tasks_workspace_presenter=_Presenter(),
            _dependencies_ctrl=_DependenciesCtrl(),
            _dependencies_section_loaded_for_task_id="task-1",
            _schedule_impact_section_loaded_for_task_id="task-1",
            _task_list=_TaskList(),
            _set_is_loading=lambda _v: None,
            _clear_section_error=lambda _key: None,
            _set_section_error=lambda _key, _msg: None,
            _set_schedule_impact=lambda _v: None,
        )

        # Both "already loaded for this task" gates must not block the
        # forced refresh -- that is exactly the bug being fixed.
        refresh_after_dependency_mutation(controller)

        assert "dependencies" in calls
        assert "schedule_impact" in calls
        assert "task_list_update" in calls
        assert controller._dependencies_section_loaded_for_task_id == "task-1"
        assert controller._schedule_impact_section_loaded_for_task_id == "task-1"

    def test_refresh_after_dependency_mutation_is_a_noop_with_no_selected_task(self):
        from types import SimpleNamespace
        from src.ui_qml.modules.project_management.controllers.tasks.task_lazy_section_loader import (
            refresh_after_dependency_mutation,
        )

        controller = SimpleNamespace(_selected_task_id="")

        refresh_after_dependency_mutation(controller)  # must not raise


class TestScheduleOverviewProjectIdFallback:
    """The reported live-app bug: every task showed the generic
    "needs a computed start date and a connected scheduling service"
    message regardless of its actual dates. Root cause -- the Tasks
    workspace's project_id is a project FILTER ("All Projects" leaves
    it blank), not the selected task's own project, but
    build_task_schedule_overview_state/build_task_schedule_impact_preview_state
    both bailed straight to the empty state whenever that filter was
    blank, so the backend call never even ran. Fixed by falling back
    to desktop_api.get_task(task_id).project_id, mirroring
    task_lookup.py's resolve_selected_task used by Dependencies."""

    def test_overview_resolves_task_project_id_when_filter_is_blank(self):
        from types import SimpleNamespace
        from src.ui_qml.modules.project_management.presenters.tasks.schedule_impact_builder import (
            build_task_schedule_overview_state,
        )

        calls: list[tuple[str, str]] = []

        class _DesktopApi:
            def get_task(self, task_id):
                return SimpleNamespace(id=task_id, project_id="project-real")

            def get_task_schedule_overview(self, task_id, project_id):
                calls.append((task_id, project_id))
                return SimpleNamespace(
                    is_available=False,
                    task_id=task_id,
                    unavailable_reason="no_computed_date",
                )

        state = build_task_schedule_overview_state(
            _DesktopApi(), task_id="task-1", project_id=""
        )

        assert calls == [("task-1", "project-real")]
        assert state["unavailableReason"] == "no_computed_date"

    def test_overview_uses_filter_project_id_when_present(self):
        from types import SimpleNamespace
        from src.ui_qml.modules.project_management.presenters.tasks.schedule_impact_builder import (
            build_task_schedule_overview_state,
        )

        calls: list[tuple[str, str]] = []

        class _DesktopApi:
            def get_task(self, task_id):
                raise AssertionError("must not resolve via get_task when filter is already set")

            def get_task_schedule_overview(self, task_id, project_id):
                calls.append((task_id, project_id))
                return SimpleNamespace(
                    is_available=False, task_id=task_id, unavailable_reason="not_found"
                )

        build_task_schedule_overview_state(
            _DesktopApi(), task_id="task-1", project_id="project-filter"
        )

        assert calls == [("task-1", "project-filter")]

    def test_preview_resolves_task_project_id_when_filter_is_blank(self):
        from types import SimpleNamespace
        from src.ui_qml.modules.project_management.presenters.tasks.schedule_impact_builder import (
            build_task_schedule_impact_preview_state,
        )

        calls: list[tuple[str, str]] = []

        class _DesktopApi:
            def get_task(self, task_id):
                return SimpleNamespace(id=task_id, project_id="project-real")

            def preview_task_schedule_impact(self, task_id, project_id, *, delay_working_days):
                calls.append((task_id, project_id))
                return SimpleNamespace(is_available=False, task_id=task_id)

        build_task_schedule_impact_preview_state(
            _DesktopApi(), task_id="task-1", project_id="", delay_working_days=1
        )

        assert calls == [("task-1", "project-real")]


class TestScheduleOverviewInfeasibleFlag:
    """R4.4 constraint-aware backward CPM pass: TaskScheduleOverview
    must thread CPMTaskInfo.is_infeasible through end-to-end via the
    real desktop-backed service, not just at the pure_cpm unit level
    (see test_backward_cpm_constraint_matrix.py for that coverage)."""

    def test_snlt_ceiling_infeasible_against_a_dependency_flags_overview(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        project = ps.create_project("Schedule Impact Infeasible Flag", "")
        predecessor = ts.create_task(
            project.id, "Foundation", "", start_date=date(2026, 9, 7), duration_days=3
        )
        successor = ts.create_task(
            project.id,
            "Cable Pull",
            "",
            start_date=date(2026, 9, 7),
            duration_days=2,
            constraint_type="start_no_later_than",
            constraint_date=date(2026, 9, 8),  # earlier than the FS-implied start
        )
        ts.add_dependency(
            predecessor_id=predecessor.id,
            successor_id=successor.id,
            dependency_type=DependencyType.FINISH_TO_START,
            lag_days=0,
        )
        impact = _impact_service(services)

        overview = impact.get_task_schedule_overview(project.id, successor.id)

        assert overview.is_available is True
        assert overview.total_float_days is not None and overview.total_float_days < 0
        assert overview.is_infeasible is True

    def test_feasible_task_does_not_flag_infeasible(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        project = ps.create_project("Schedule Impact Feasible Flag", "")
        task = ts.create_task(
            project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2
        )
        impact = _impact_service(services)

        overview = impact.get_task_schedule_overview(project.id, task.id)

        assert overview.is_infeasible is False


class TestScheduleImpactConflictConstraintLabel:

    def test_mso_dependency_conflict_reports_a_humanized_label_not_the_raw_enum(self, services):
        from src.core.modules.project_management.api.desktop.tasks.api import (
            ProjectManagementTasksDesktopApi,
        )
        from src.ui_qml.modules.project_management.presenters.tasks.schedule_impact_builder import (
            build_task_schedule_overview_state,
        )

        ps = services["project_service"]
        ts = services["task_service"]
        project = ps.create_project("Schedule Impact Constraint Label", "")
        predecessor = ts.create_task(
            project.id, "Foundation", "", start_date=date(2026, 9, 7), duration_days=3
        )
        successor = ts.create_task(
            project.id,
            "Cable Pull",
            "",
            start_date=date(2026, 9, 7),
            duration_days=2,
            constraint_type="must_start_on",
            # A --FS--> B implies B starts 2026-09-11; MSO overrides it to
            # an earlier date, producing exactly the dependency-conflict
            # fact whose constraint_type this test is verifying.
            constraint_date=date(2026, 9, 8),
        )
        ts.add_dependency(
            predecessor_id=predecessor.id,
            successor_id=successor.id,
            dependency_type=DependencyType.FINISH_TO_START,
            lag_days=0,
        )

        api = ProjectManagementTasksDesktopApi(
            task_service=ts,
            schedule_change_impact_service=_impact_service(services),
        )
        state = build_task_schedule_overview_state(
            api, task_id=successor.id, project_id=project.id
        )

        conflicts = [c for c in state["conflicts"] if c["taskId"] == successor.id]
        assert len(conflicts) == 1
        assert conflicts[0]["constraintTypeLabel"] == "Must Start On (MSO)"
        assert "constraintType" not in conflicts[0]


class TestPreviewDeadlineConflict:
    """The reported bug: "Preview Impact" worked for a 1 working-day
    delay but showed nothing at all for a 2+ day delay. Root cause --
    the task has a hard `deadline` constraint (distinct from end_date).
    analyse() built the proposed in-memory task copy via
    dataclasses.replace(), which re-validates the WHOLE object,
    including Task's TASK_DEADLINE_INVALID invariant (deadline must not
    be before start_date). A delay large enough to push the proposed
    start past the task's own deadline raised ValidationError deep
    inside replace() -- silently swallowed by preview_task_schedule_impact's
    bare except, so the UI just showed no preview with zero explanation.
    Fixed by detecting the conflict BEFORE replace() and returning a
    real, reportable outcome instead of crashing."""

    def test_analyse_working_day_delay_reports_deadline_conflict_instead_of_raising(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        project = ps.create_project("Schedule Impact Deadline Conflict", "")
        # Friday start, 1-day duration, deadline only a few days out --
        # a 2 working-day delay pushes the proposed start past it.
        task = ts.create_task(
            project.id,
            "Task With Deadline",
            "",
            start_date=date(2024, 1, 5),
            duration_days=1,
            deadline=date(2024, 1, 8),
        )
        impact = _impact_service(services)

        report = impact.analyse_working_day_delay(
            project_id=project.id,
            changed_task_id=task.id,
            current_start=task.start_date,
            delay_working_days=2,
        )

        assert report.blocked_by_deadline is True
        assert "deadline" in report.blocked_reason.lower()
        assert report.affected_tasks == []

    def test_analyse_working_day_delay_within_deadline_is_not_blocked(self, services):
        ps = services["project_service"]
        ts = services["task_service"]
        project = ps.create_project("Schedule Impact Deadline OK", "")
        task = ts.create_task(
            project.id,
            "Task With Deadline",
            "",
            start_date=date(2024, 1, 5),
            duration_days=1,
            deadline=date(2024, 3, 1),
        )
        impact = _impact_service(services)

        report = impact.analyse_working_day_delay(
            project_id=project.id,
            changed_task_id=task.id,
            current_start=task.start_date,
            delay_working_days=2,
        )

        assert report.blocked_by_deadline is False

    def test_preview_desktop_api_surfaces_deadline_conflict_without_raising(self, services):
        from src.core.modules.project_management.api.desktop.tasks.api import (
            ProjectManagementTasksDesktopApi,
        )

        ps = services["project_service"]
        ts = services["task_service"]
        project = ps.create_project("Schedule Impact Deadline Desktop API", "")
        task = ts.create_task(
            project.id,
            "Task With Deadline",
            "",
            start_date=date(2024, 1, 5),
            duration_days=1,
            deadline=date(2024, 1, 8),
        )
        api = ProjectManagementTasksDesktopApi(
            task_service=ts,
            schedule_change_impact_service=_impact_service(services),
        )

        dto = api.preview_task_schedule_impact(task.id, project.id, delay_working_days=2)

        assert dto.is_available is True
        assert dto.blocked_by_deadline is True
        assert dto.blocked_reason != ""

    def test_preview_builder_surfaces_deadline_conflict_as_blocked_state(self):
        from types import SimpleNamespace
        from src.ui_qml.modules.project_management.presenters.tasks.schedule_impact_builder import (
            build_task_schedule_impact_preview_state,
        )

        class _DesktopApi:
            def preview_task_schedule_impact(self, task_id, project_id, *, delay_working_days):
                return SimpleNamespace(
                    is_available=True,
                    task_id=task_id,
                    affected_count=0,
                    max_project_finish_shift_days=0,
                    requires_approval=False,
                    critical_path_changed=False,
                    conflict_count=0,
                    newly_critical_task_ids=(),
                    no_longer_critical_task_ids=(),
                    affected_tasks=(),
                    blocked_by_deadline=True,
                    blocked_reason="Proposed start 2024-01-10 would fall after this task's deadline of 2024-01-08.",
                )

        state = build_task_schedule_impact_preview_state(
            _DesktopApi(), task_id="task-1", project_id="project-1", delay_working_days=2
        )

        assert state["isAvailable"] is True
        assert state["blockedByDeadline"] is True
        assert "deadline" in state["blockedReason"].lower()
        assert state["summary"] == state["blockedReason"]
