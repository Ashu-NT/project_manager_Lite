from datetime import date, datetime, timedelta
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_portfolio_desktop_api,
    build_project_management_scheduling_desktop_api,
)
from src.core.modules.project_management.domain.enums import (
    DependencyType,
    ProjectStatus,
    TaskStatus,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioProjectDependency,
    PortfolioProjectDependencyView,
    PortfolioRecentAction,
    PortfolioScenario,
    PortfolioScenarioComparison,
    PortfolioScenarioEvaluation,
    PortfolioScoringTemplate,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.tasks.task import Task


def test_project_management_scheduling_desktop_api_supports_schedule_calendar_and_baselines() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    task_service = _FakeTaskService()
    task_a = task_service.create_task(
        project_id=project.id,
        name="Cable Pull",
        description="Primary feeder cable installation.",
        start_date=date(2026, 5, 3),
        duration_days=4,
        priority=90,
        deadline=date(2026, 5, 7),
    )
    task_b = task_service.create_task(
        project_id=project.id,
        name="Punchlist Closeout",
        description="Commissioning closeout walkdown.",
        start_date=date(2026, 5, 8),
        duration_days=2,
        priority=50,
        deadline=date(2026, 5, 9),
    )
    scheduling_engine = _FakeSchedulingEngine(
        task_service=task_service,
        critical_task_ids={task_a.id},
    )
    work_calendar_service = _FakeWorkCalendarService()
    work_calendar_engine = _FakeWorkCalendarEngine(work_calendar_service)
    baseline_service = _FakeBaselineService()
    reporting_service = _FakeReportingService()
    api = build_project_management_scheduling_desktop_api(
        project_service=project_service,
        task_service=task_service,
        scheduling_engine=scheduling_engine,
        work_calendar_service=work_calendar_service,
        work_calendar_engine=work_calendar_engine,
        baseline_service=baseline_service,
        reporting_service=reporting_service,
    )

    assert api.list_projects()[0].label == "Plant Upgrade"
    assert api.get_calendar_snapshot().working_days[0].label == "Mon"

    calendar_stub = api.update_calendar(
        SimpleNamespace(working_days=(0, 1, 2, 3, 4, 5), hours_per_day=10.0)
    )
    assert calendar_stub is not None

    holiday_stub = api.add_holiday(
        SimpleNamespace(holiday_date=date(2026, 5, 1), name="Labor Day")
    )
    assert holiday_stub is not None

    calculation = api.calculate_working_days(
        SimpleNamespace(start_date=date(2026, 5, 4), working_days=3)
    )

    assert calculation.result_date == date(2026, 5, 7)

    schedule = api.list_schedule(project.id)

    assert schedule[0].name == "Cable Pull"
    assert schedule[0].is_critical is True
    assert schedule[1].total_float_days == 2

    created_a = api.create_baseline(
        SimpleNamespace(project_id=project.id, name="Original Plan")
    )
    created_b = api.create_baseline(
        SimpleNamespace(project_id=project.id, name="Weekly Freeze")
    )
    baseline_options = api.list_baselines(project.id)

    assert created_a.value in {option.value for option in baseline_options}
    assert baseline_options[0].value == created_a.value

    comparison_rows = api.compare_baselines(
        project_id=project.id,
        baseline_a_id=created_a.value,
        baseline_b_id=created_b.value,
        include_unchanged=False,
    )

    assert comparison_rows[0].task_name == "Cable Pull"
    assert comparison_rows[0].start_shift_days == 1

    api.delete_holiday(getattr(holiday_stub, "id", ""))
    api.delete_baseline(created_a.value)

    assert api.get_calendar_snapshot().holidays == ()
    assert [option.value for option in api.list_baselines(project.id)] == [created_b.value]


def test_project_management_portfolio_desktop_api_mutates_portfolio_records() -> None:
    project_service = _FakeProjectService()
    project_alpha = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
        planned_budget=250000.0,
        currency="eur",
    )
    project_beta = project_service.create_project(
        name="Warehouse Retrofit",
        description="Upgrade lighting and controls.",
        planned_budget=120000.0,
        currency="eur",
    )
    project_service.update_project(project_alpha.id, status=ProjectStatus.ACTIVE)
    project_service.update_project(project_beta.id, status=ProjectStatus.ON_HOLD)
    portfolio_service = _FakePortfolioService(project_service)
    api = build_project_management_portfolio_desktop_api(
        project_service=project_service,
        portfolio_service=portfolio_service,
    )

    assert [option.label for option in api.list_projects()] == [
        "Plant Upgrade",
        "Warehouse Retrofit",
    ]
    assert api.list_intake_statuses()[0].value == "PROPOSED"
    assert api.list_dependency_types()[0].label == "Finish -> Start"

    created_template = api.create_scoring_template(
        SimpleNamespace(
            name="Balanced PMO",
            summary="Weighted intake rubric for governance.",
            strategic_weight=3,
            value_weight=2,
            urgency_weight=2,
            risk_weight=1,
            activate=True,
        )
    )
    created_intake = api.create_intake_item(
        SimpleNamespace(
            title="Packaging Line Expansion",
            sponsor_name="Operations Director",
            summary="Capacity uplift on the secondary line.",
            requested_budget=180000.0,
            requested_capacity_percent=40.0,
            target_start_date=date(2026, 6, 1),
            strategic_score=5,
            value_score=4,
            urgency_score=3,
            risk_score=2,
            scoring_template_id=created_template.id,
            status="APPROVED",
        )
    )
    created_scenario = api.create_scenario(
        SimpleNamespace(
            name="Q3 Balanced Plan",
            budget_limit=500000.0,
            capacity_limit_percent=280.0,
            project_ids=(project_alpha.id,),
            intake_item_ids=(created_intake.id,),
            notes="Protect active execution first.",
        )
    )
    comparison_scenario = api.create_scenario(
        SimpleNamespace(
            name="Aggressive Expansion",
            budget_limit=650000.0,
            capacity_limit_percent=340.0,
            project_ids=(project_alpha.id, project_beta.id),
            intake_item_ids=(created_intake.id,),
            notes="Bring forward more intake if labor opens up.",
        )
    )

    listed_templates = api.list_templates()
    listed_intake = api.list_intake_items(status="APPROVED")
    evaluation = api.evaluate_scenario(created_scenario.id)
    comparison = api.compare_scenarios(created_scenario.id, comparison_scenario.id)
    dependency = api.create_project_dependency(
        SimpleNamespace(
            predecessor_project_id=project_alpha.id,
            successor_project_id=project_beta.id,
            dependency_type="FS",
            summary="Warehouse cutover depends on line shutdown lessons learned.",
        )
    )

    assert listed_templates[0].is_active is True
    assert listed_intake[0].title == "Packaging Line Expansion"
    assert evaluation.scenario_name == "Q3 Balanced Plan"
    assert evaluation.status_label == "Within limits"
    assert comparison.added_project_names == ("Warehouse Retrofit",)
    assert dependency.summary == "Warehouse cutover depends on line shutdown lessons learned."
    assert api.list_heatmap()[0].pressure_label in {"Stable", "Watch", "Hot"}
    assert api.list_recent_actions(limit=5)[0].action_label == "Dependency created"

    api.remove_project_dependency(dependency.dependency_id)

    assert api.list_dependencies() == ()


class _FakeProjectService:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._next_id = 1

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def create_project(
        self,
        *,
        name: str,
        description: str = "",
        status: "ProjectStatus | None" = None,
        client_name: str | None = None,
        client_contact: str | None = None,
        planned_budget: float | None = None,
        currency: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Project:
        project = Project(
            id=f"proj-{self._next_id}",
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            status=status if status is not None else ProjectStatus.PLANNED,
            client_name=client_name,
            client_contact=client_contact,
            planned_budget=planned_budget,
            currency=(currency or "").strip().upper() or None,
            version=1,
        )
        self._next_id += 1
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

    def update_project(
        self,
        project_id: str,
        *,
        expected_version: int | None = None,
        name: str | None = None,
        description: str | None = None,
        status: ProjectStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        client_name: str | None = None,
        client_contact: str | None = None,
        planned_budget: float | None = None,
        currency: str | None = None,
    ) -> Project:
        project = self._projects[project_id]
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if status is not None:
            project.status = status
        if start_date is not None:
            project.start_date = start_date
        if end_date is not None:
            project.end_date = end_date
        if client_name is not None:
            project.client_name = client_name
        if client_contact is not None:
            project.client_contact = client_contact
        if planned_budget is not None:
            project.planned_budget = planned_budget
        if currency is not None:
            project.currency = (currency or "").strip().upper() or None
        project.version += 1
        return project

    def set_status(self, project_id: str, status: ProjectStatus) -> None:
        self._projects[project_id].status = status
        self._projects[project_id].version += 1

    def delete_project(self, project_id: str) -> None:
        del self._projects[project_id]


class _FakeTaskService:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._next_id = 1

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return [task for task in self._tasks.values() if task.project_id == project_id]

    def create_task(
        self,
        *,
        project_id: str,
        name: str,
        code: str = "",
        description: str = "",
        start_date: date | None = None,
        duration_days: int | None = None,
        priority: int = 0,
        deadline: date | None = None,
    ) -> Task:
        task = Task(
            id=f"task-{self._next_id}",
            project_id=project_id,
            name=name,
            code=code,
            description=description,
            start_date=start_date,
            end_date=_derive_end_date(start_date, duration_days),
            duration_days=duration_days,
            priority=priority,
            deadline=deadline,
        )
        self._next_id += 1
        self._tasks[task.id] = task
        return task

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        task.status = status
        task.version += 1


class _FakeSchedulingEngine:
    def __init__(self, *, task_service: _FakeTaskService, critical_task_ids: set[str]) -> None:
        self._task_service = task_service
        self._critical_task_ids = critical_task_ids

    def recalculate_project_schedule(self, project_id: str, *, persist: bool = True) -> dict[str, SimpleNamespace]:
        result: dict[str, SimpleNamespace] = {}
        for task in self._task_service.list_tasks_for_project(project_id):
            total_float_days = 0 if task.id in self._critical_task_ids else 2
            result[task.id] = SimpleNamespace(
                task=task,
                earliest_start=task.start_date,
                earliest_finish=task.end_date,
                latest_start=task.start_date if total_float_days == 0 else date.fromordinal(task.start_date.toordinal() + total_float_days),
                latest_finish=task.end_date if total_float_days == 0 else date.fromordinal(task.end_date.toordinal() + total_float_days),
                total_float_days=total_float_days,
                is_critical=task.id in self._critical_task_ids,
                deadline=task.deadline,
                late_by_days=0 if task.id in self._critical_task_ids else 1,
            )
        return result


class _FakeWorkCalendarService:
    def __init__(self) -> None:
        self._working_days = {0, 1, 2, 3, 4}
        self._hours_per_day = 8.0
        self._holidays: dict[str, SimpleNamespace] = {}
        self._next_holiday_id = 1

    def get_calendar(self) -> SimpleNamespace:
        return SimpleNamespace(working_days=set(self._working_days), hours_per_day=self._hours_per_day)

    def set_working_days(self, working_days: set[int], hours_per_day: float | None = None):
        self._working_days = set(working_days)
        if hours_per_day is not None:
            self._hours_per_day = hours_per_day
        return self.get_calendar()

    def list_holidays(self) -> list[SimpleNamespace]:
        return list(self._holidays.values())

    def add_holiday(self, holiday_date: date, name: str = "") -> SimpleNamespace:
        holiday = SimpleNamespace(id=f"holiday-{self._next_holiday_id}", date=holiday_date, name=name)
        self._next_holiday_id += 1
        self._holidays[holiday.id] = holiday
        return holiday

    def delete_holiday(self, holiday_id: str) -> None:
        del self._holidays[holiday_id]


class _FakeWorkCalendarEngine:
    def __init__(self, work_calendar_service: _FakeWorkCalendarService) -> None:
        self._service = work_calendar_service

    def add_working_days(self, start_date: date, working_days: int) -> date:
        current = start_date
        added = 0
        while added < working_days:
            current = date.fromordinal(current.toordinal() + 1)
            if self.is_working_day(current):
                added += 1
        return current

    def is_working_day(self, target_date: date) -> bool:
        holiday_dates = {holiday.date for holiday in self._service.list_holidays()}
        return (
            target_date.weekday() in self._service.get_calendar().working_days
            and target_date not in holiday_dates
        )


class _FakeBaselineService:
    def __init__(self) -> None:
        self._baselines_by_project: dict[str, list[SimpleNamespace]] = {}
        self._next_id = 1

    def list_baselines(self, project_id: str) -> list[SimpleNamespace]:
        return list(self._baselines_by_project.get(project_id, []))

    def create_baseline(self, project_id: str, name: str = "Baseline") -> SimpleNamespace:
        baseline = SimpleNamespace(
            id=f"base-{self._next_id}",
            project_id=project_id,
            name=name,
            created_at=date(2026, 5, self._next_id),
        )
        self._next_id += 1
        self._baselines_by_project.setdefault(project_id, []).append(baseline)
        return baseline

    def delete_baseline(self, baseline_id: str) -> None:
        for project_id, baselines in self._baselines_by_project.items():
            self._baselines_by_project[project_id] = [b for b in baselines if b.id != baseline_id]


class _FakeReportingService:
    def compare_baselines(
        self,
        *,
        project_id: str,
        baseline_a_id: str,
        baseline_b_id: str,
        include_unchanged: bool = False,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            rows=[
                SimpleNamespace(
                    task_id="task-1",
                    task_name="Cable Pull",
                    change_type="CHANGED",
                    baseline_a_start=date(2026, 5, 2),
                    baseline_a_finish=date(2026, 5, 5),
                    baseline_b_start=date(2026, 5, 3),
                    baseline_b_finish=date(2026, 5, 6),
                    start_shift_days=1,
                    finish_shift_days=1,
                    duration_delta_days=0,
                    planned_cost_delta=1200.0,
                )
            ]
        )


class _FakePortfolioService:
    def __init__(self, project_service: _FakeProjectService) -> None:
        self._project_service = project_service
        self._templates: dict[str, PortfolioScoringTemplate] = {}
        self._intake_items: dict[str, PortfolioIntakeItem] = {}
        self._scenarios: dict[str, PortfolioScenario] = {}
        self._dependencies: dict[str, PortfolioProjectDependency] = {}
        self._actions: list[PortfolioRecentAction] = []

    def list_scoring_templates(self) -> list[PortfolioScoringTemplate]:
        return list(self._templates.values())

    def create_scoring_template(
        self,
        *,
        name: str,
        summary: str = "",
        strategic_weight: int = 3,
        value_weight: int = 2,
        urgency_weight: int = 2,
        risk_weight: int = 1,
        activate: bool = False,
    ) -> PortfolioScoringTemplate:
        if activate:
            for existing in self._templates.values():
                existing.is_active = False
        template = PortfolioScoringTemplate(
            id=f"tpl-{len(self._templates) + 1}",
            name=name,
            summary=summary,
            strategic_weight=strategic_weight,
            value_weight=value_weight,
            urgency_weight=urgency_weight,
            risk_weight=risk_weight,
            is_active=activate,
            created_at=datetime(2026, 5, 1, 9, 0),
            updated_at=datetime(2026, 5, 1, 9, 0),
        )
        self._templates[template.id] = template
        self._append_action("Template created", "Portfolio", summary or name)
        return template

    def activate_scoring_template(self, template_id: str) -> PortfolioScoringTemplate:
        for existing in self._templates.values():
            existing.is_active = existing.id == template_id
        template = self._templates[template_id]
        self._append_action("Template activated", "Portfolio", template.name)
        return template

    def list_intake_items(self, *, status: PortfolioIntakeStatus | None = None) -> list[PortfolioIntakeItem]:
        rows = list(self._intake_items.values())
        if status is not None:
            rows = [row for row in rows if row.status == status]
        return rows

    def create_intake_item(
        self,
        *,
        title: str,
        sponsor_name: str,
        summary: str = "",
        requested_budget: float = 0.0,
        requested_capacity_percent: float = 0.0,
        target_start_date: date | None = None,
        strategic_score: int = 3,
        value_score: int = 3,
        urgency_score: int = 3,
        risk_score: int = 3,
        scoring_template_id: str | None = None,
        status: PortfolioIntakeStatus = PortfolioIntakeStatus.PROPOSED,
    ) -> PortfolioIntakeItem:
        template = (
            self._templates.get(str(scoring_template_id or "").strip())
            if scoring_template_id
            else next((row for row in self._templates.values() if row.is_active), None)
        )
        item = PortfolioIntakeItem(
            id=f"intake-{len(self._intake_items) + 1}",
            title=title,
            sponsor_name=sponsor_name,
            summary=summary,
            requested_budget=requested_budget,
            requested_capacity_percent=requested_capacity_percent,
            target_start_date=target_start_date,
            strategic_score=strategic_score,
            value_score=value_score,
            urgency_score=urgency_score,
            risk_score=risk_score,
            scoring_template_id=template.id if template is not None else "",
            scoring_template_name=template.name if template is not None else "Balanced PMO",
            strategic_weight=getattr(template, "strategic_weight", 3),
            value_weight=getattr(template, "value_weight", 2),
            urgency_weight=getattr(template, "urgency_weight", 2),
            risk_weight=getattr(template, "risk_weight", 1),
            status=status,
            created_at=datetime(2026, 5, 1, 10, 0),
            updated_at=datetime(2026, 5, 1, 10, 0),
            version=1,
        )
        self._intake_items[item.id] = item
        self._append_action("Intake created", "Portfolio", item.title)
        return item

    def list_scenarios(self) -> list[PortfolioScenario]:
        return list(self._scenarios.values())

    def create_scenario(
        self,
        *,
        name: str,
        budget_limit: float | None = None,
        capacity_limit_percent: float | None = None,
        project_ids: list[str] | None = None,
        intake_item_ids: list[str] | None = None,
        notes: str = "",
    ) -> PortfolioScenario:
        scenario = PortfolioScenario(
            id=f"scn-{len(self._scenarios) + 1}",
            name=name,
            budget_limit=budget_limit,
            capacity_limit_percent=capacity_limit_percent,
            project_ids=list(project_ids or []),
            intake_item_ids=list(intake_item_ids or []),
            notes=notes,
            created_at=datetime(2026, 5, 2, 9, 0),
            updated_at=datetime(2026, 5, 2, 9, 0),
        )
        self._scenarios[scenario.id] = scenario
        self._append_action("Scenario saved", "Portfolio", scenario.name)
        return scenario

    def evaluate_scenario(self, scenario_id: str) -> PortfolioScenarioEvaluation:
        scenario = self._scenarios[scenario_id]
        selected_projects = [
            self._project_service.get_project(project_id)
            for project_id in scenario.project_ids
        ]
        selected_items = [
            self._intake_items[item_id]
            for item_id in scenario.intake_item_ids
            if item_id in self._intake_items
        ]
        project_budget = sum(
            float(getattr(project, "planned_budget", 0.0) or 0.0)
            for project in selected_projects
            if project is not None
        )
        intake_budget = sum(float(item.requested_budget or 0.0) for item in selected_items)
        total_budget = project_budget + intake_budget
        total_capacity = sum(float(item.requested_capacity_percent or 0.0) for item in selected_items)
        capacity_limit = scenario.capacity_limit_percent
        available_capacity = max(float(capacity_limit or 0.0) - total_capacity, 0.0)
        over_budget = scenario.budget_limit is not None and total_budget > float(scenario.budget_limit)
        over_capacity = capacity_limit is not None and total_capacity > float(capacity_limit)
        return PortfolioScenarioEvaluation(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            selected_projects=len([p for p in selected_projects if p is not None]),
            selected_intake_items=len(selected_items),
            total_budget=total_budget,
            budget_limit=scenario.budget_limit,
            total_capacity_percent=total_capacity,
            capacity_limit_percent=capacity_limit,
            available_capacity_percent=available_capacity,
            intake_composite_score=sum(item.composite_score for item in selected_items),
            over_budget=over_budget,
            over_capacity=over_capacity,
            summary="Within limits" if not over_budget and not over_capacity else "Escalation required",
        )

    def compare_scenarios(self, base_scenario_id: str, candidate_scenario_id: str) -> PortfolioScenarioComparison:
        base = self._scenarios[base_scenario_id]
        candidate = self._scenarios[candidate_scenario_id]
        base_eval = self.evaluate_scenario(base_scenario_id)
        candidate_eval = self.evaluate_scenario(candidate_scenario_id)
        base_project_ids = set(base.project_ids)
        candidate_project_ids = set(candidate.project_ids)
        base_intake_ids = set(base.intake_item_ids)
        candidate_intake_ids = set(candidate.intake_item_ids)
        return PortfolioScenarioComparison(
            base_scenario_id=base.id,
            base_scenario_name=base.name,
            candidate_scenario_id=candidate.id,
            candidate_scenario_name=candidate.name,
            base_evaluation=base_eval,
            candidate_evaluation=candidate_eval,
            budget_delta=candidate_eval.total_budget - base_eval.total_budget,
            capacity_delta_percent=candidate_eval.total_capacity_percent - base_eval.total_capacity_percent,
            intake_score_delta=candidate_eval.intake_composite_score - base_eval.intake_composite_score,
            selected_projects_delta=candidate_eval.selected_projects - base_eval.selected_projects,
            selected_intake_items_delta=candidate_eval.selected_intake_items - base_eval.selected_intake_items,
            added_project_names=[
                self._project_service.get_project(pid).name
                for pid in sorted(candidate_project_ids - base_project_ids)
                if self._project_service.get_project(pid) is not None
            ],
            removed_project_names=[
                self._project_service.get_project(pid).name
                for pid in sorted(base_project_ids - candidate_project_ids)
                if self._project_service.get_project(pid) is not None
            ],
            added_intake_titles=[
                self._intake_items[iid].title
                for iid in sorted(candidate_intake_ids - base_intake_ids)
                if iid in self._intake_items
            ],
            removed_intake_titles=[
                self._intake_items[iid].title
                for iid in sorted(base_intake_ids - candidate_intake_ids)
                if iid in self._intake_items
            ],
            summary="Candidate scenario increases scope and portfolio demand.",
        )

    def list_portfolio_heatmap(self) -> list[PortfolioExecutiveRow]:
        rows: list[PortfolioExecutiveRow] = []
        for project in self._project_service.list_projects():
            pressure_label = "Hot" if project.status == ProjectStatus.ON_HOLD else "Stable"
            rows.append(
                PortfolioExecutiveRow(
                    project_id=project.id,
                    project_name=project.name,
                    project_status=project.status.value,
                    late_tasks=1 if pressure_label == "Hot" else 0,
                    critical_tasks=1,
                    peak_utilization_percent=118.0 if pressure_label == "Hot" else 92.0,
                    cost_variance=-8500.0 if pressure_label == "Hot" else 2500.0,
                    pressure_score=90 if pressure_label == "Hot" else 40,
                    pressure_label=pressure_label,
                )
            )
        return rows

    def list_project_dependencies(self) -> list[PortfolioProjectDependencyView]:
        rows: list[PortfolioProjectDependencyView] = []
        for dependency in self._dependencies.values():
            predecessor = self._project_service.get_project(dependency.predecessor_project_id)
            successor = self._project_service.get_project(dependency.successor_project_id)
            rows.append(
                PortfolioProjectDependencyView(
                    dependency_id=dependency.id,
                    predecessor_project_id=dependency.predecessor_project_id,
                    predecessor_project_name=getattr(predecessor, "name", dependency.predecessor_project_id),
                    predecessor_project_status=getattr(getattr(predecessor, "status", None), "value", "PLANNED"),
                    successor_project_id=dependency.successor_project_id,
                    successor_project_name=getattr(successor, "name", dependency.successor_project_id),
                    successor_project_status=getattr(getattr(successor, "status", None), "value", "PLANNED"),
                    dependency_type=dependency.dependency_type,
                    summary=dependency.summary,
                    pressure_label="Watch",
                    created_at=dependency.created_at,
                )
            )
        return rows

    def create_project_dependency(
        self,
        *,
        predecessor_project_id: str,
        successor_project_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        summary: str = "",
    ) -> PortfolioProjectDependency:
        dependency = PortfolioProjectDependency(
            id=f"dep-{len(self._dependencies) + 1}",
            predecessor_project_id=predecessor_project_id,
            successor_project_id=successor_project_id,
            dependency_type=dependency_type,
            summary=summary,
            created_at=datetime(2026, 5, 3, 8, 45),
            updated_at=datetime(2026, 5, 3, 8, 45),
        )
        self._dependencies[dependency.id] = dependency
        self._append_action(
            "Dependency created",
            getattr(self._project_service.get_project(predecessor_project_id), "name", predecessor_project_id),
            summary or dependency.id,
        )
        return dependency

    def remove_project_dependency(self, dependency_id: str) -> None:
        self._dependencies.pop(dependency_id, None)
        self._append_action("Dependency removed", "Portfolio", dependency_id)

    def list_recent_pm_actions(self, *, limit: int = 12) -> list[PortfolioRecentAction]:
        return list(reversed(self._actions[-limit:]))

    def _append_action(self, action_label: str, project_name: str, summary: str) -> None:
        self._actions.append(
            PortfolioRecentAction(
                occurred_at=datetime(2026, 5, 3, 9, len(self._actions)),
                project_name=project_name,
                actor_username="alex",
                action_label=action_label,
                summary=summary,
            )
        )


def _derive_end_date(start_date: date | None, duration_days: int | None) -> date | None:
    if start_date is None or duration_days is None:
        return None
    return start_date + timedelta(days=max(duration_days - 1, 0))
