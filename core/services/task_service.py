# core/services/task_service.py
from __future__ import annotations
from typing import List, Optional
from datetime import date, timedelta

from ..models import Task, TaskStatus, TaskDependency, DependencyType, TaskAssignment
from ..interfaces import (
    TaskRepository,
    DependencyRepository,
    AssignmentRepository,
    ResourceRepository,
    CostRepository,
    CalendarEventRepository,
    ProjectResourceRepository,
    ProjectRepository,
)
from .work_calendar_engine import WorkCalendarEngine
from ..exceptions import ValidationError, NotFoundError, BusinessRuleError
from sqlalchemy.orm import Session
import logging
from core.events.domain_events import domain_events

logger = logging.getLogger(__name__)

class TaskService:
    def __init__(
        self,
        session: Session,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        resource_repo: ResourceRepository,
        cost_repo: CostRepository,
        calendar_repo: CalendarEventRepository,
        work_calendar_engine= WorkCalendarEngine,
        project_resource_repo = ProjectResourceRepository,
        project_repo = ProjectRepository,
    ):
        self._session = session
        self._task_repo = task_repo
        self._dependency_repo = dependency_repo
        self._assignment_repo = assignment_repo
        self._resource_repo = resource_repo
        self._cost_repo = cost_repo
        self._calendar_repo = calendar_repo
        self._work_calendar_engine = work_calendar_engine
        self._project_resource_repo = project_resource_repo
        self._project_repo = project_repo

    def create_task(
        self,
        project_id: str,
        name: str,
        description: str = "",
        start_date: Optional[date] = None,
        duration_days: Optional[int] = None,
        status: TaskStatus = TaskStatus.TODO,
        priority: int = 0,
        deadline: Optional[date] = None,
    ) -> Task:
        
        self._validate_dates(start_date, deadline, duration_days)
        self._validate_task_name(name)
        
        
        task = Task.create(
            project_id=project_id, 
            name=name, 
            description=description,
            start_date=start_date,
            duration_days=duration_days,
            status=status,
            priority=priority,
            deadline=deadline
        )
        task.start_date = start_date
        task.duration_days = duration_days
        if start_date and duration_days:
            task.end_date = start_date + timedelta(days=duration_days-1)
        
        self._validate_task_within_project_dates(project_id, task.start_date, task.end_date)
        
        try:
            self._task_repo.add(task)
            self._session.commit()
            logger.info(f"Created task {task.id} - {task.name} for project {project_id}")   
            domain_events.tasks_changed.emit(project_id)
            return task
        except Exception as e:
            self._session.rollback()
            logger.error(f"Error creating task: {e}")
            raise 

    def _validate_dates(self, start_date, end_date, duration_days):
        
        if start_date and end_date and end_date < start_date:
            raise ValidationError("Task deadline cannot be before start_date.")

        if duration_days is not None and duration_days < 0:
            raise ValidationError("Task duration_days cannot be negative.")

    def _validate_task_within_project_dates(self, project_id: str, task_start: date | None, task_end: date | None):
        proj = self._project_repo.get(project_id)
        if not proj:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        
        ps = getattr(proj, "start_date", None)
        pe = getattr(proj, "end_date", None)
        
        # if project dates exist
        if ps and task_start and task_start < ps:
            raise ValidationError(f"Task start date ({task_start}) can not be before project start ({ps})",code="TASK_INVALID_DATE")
        if pe and task_start and task_start > pe:
            raise ValidationError(f"Task start date ({task_start}) can not be after project end ({pe})",code="TASK_INVALID_DATE")
        if ps and task_end and task_end < ps:
            raise ValidationError(f"Task end date ({task_end}) can not be before project start ({ps})",code="TASK_INVALID_DATE")
        if pe and task_end and task_end > pe:
            raise ValidationError(f"Task end date ({task_start}) can not be after project end ({pe})",code="TASK_INVALID_DATE")
        
    def _validate_not_self_dependency(self, predecessor_id: str, successor_id: str):
        if predecessor_id == successor_id:
            raise ValidationError("A task cannot depend on itself.")

    def _validate_task_name(self, name: str) -> None:
        if not name.strip():
            raise ValidationError("Task name cannot be empty.", code="TASK_NAME_EMPTY") 
        if len(name.strip()) < 3:
            raise ValidationError("Task name must be at least 3 characters.", code="TASK_NAME_TOO_SHORT")
        if any(c in name for c in ['/', '\\', '?', '%', '*', ':', '|', '"', '<', '>']):
            raise ValidationError("Task name contains invalid characters.", code="TASK_NAME_INVALID_CHARS")
      
    def _check_no_circular_dependency(self, project_id: str, predecessor_id: str, successor_id: str) -> None:
        """
        Detect cycle for the PROPOSED edge predecessor_id -> successor_id.
        Cycle exists if successor_id can reach predecessor_id through existing edges.
        """
        deps = self._dependency_repo.list_by_project(project_id)

        graph: dict[str, list[str]] = {}
        for d in deps:
            graph.setdefault(d.predecessor_task_id, []).append(d.successor_task_id)

        # add the proposed edge virtually
        graph.setdefault(predecessor_id, []).append(successor_id)

        # DFS from successor, if we reach predecessor => cycle
        target = predecessor_id
        stack = [successor_id]
        visited = set()

        while stack:
            cur = stack.pop()
            if cur == target:
                raise BusinessRuleError(
                    "Adding this dependency would create a circular dependency.",
                    code="DEPENDENCY_CYCLE",
                )
            if cur in visited:
                continue
            visited.add(cur)
            for nxt in graph.get(cur, []):
                if nxt not in visited:
                    stack.append(nxt)
                
    def add_dependency(
        self,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
    ) -> TaskDependency:
        self._validate_not_self_dependency(predecessor_id, successor_id)

        pred = self._task_repo.get(predecessor_id)
        if not pred:
            raise NotFoundError("Predecessor task not found", code="TASK_NOT_FOUND")

        succ = self._task_repo.get(successor_id)
        if not succ:
            raise NotFoundError("Successor task not found", code="TASK_NOT_FOUND")

        # MUST be in same project
        if pred.project_id != succ.project_id:
            raise ValidationError(
                "Tasks must be in the same project to create a dependency.",
                code="DEPENDENCY_CROSS_PROJECT",
            )

        # prevent duplicate edge (same predecessor->successor)
        existing = self._dependency_repo.list_by_task(predecessor_id)
        if any(d.successor_task_id == successor_id for d in existing):
            raise ValidationError("This dependency already exists.", code="DEPENDENCY_DUPLICATE")

        # robust cycle check: if there is a path succ -> ... -> pred, then adding pred->succ makes a cycle
        self._check_no_circular_dependency(
            project_id=pred.project_id,
            predecessor_id=predecessor_id,
            successor_id=successor_id,
        )

        dep = TaskDependency.create(predecessor_id, successor_id, dependency_type, lag_days)
        try:
            self._dependency_repo.add(dep)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            raise e

        domain_events.tasks_changed.emit(pred.project_id)
        return dep


    def remove_dependency(self, dep_id: str) -> None:
        try:
            self._dependency_repo.delete(dep_id)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            raise e
    
    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._task_repo.get(task_id)
        if not task:
            raise ValueError("Task not found")
        task.status = status
        self._task_repo.update(task)

    def unassign_resource(self, assignment_id: str) -> None:
        try:
            self._assignment_repo.delete(assignment_id)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            raise e
    
    def list_tasks_for_project(self, project_id: str) -> List[Task]:
        return self._task_repo.list_by_project(project_id)
    
    def list_dependencies_for_task(self, task_id: str) -> List[TaskDependency]:
        return self._dependency_repo.list_by_task(task_id)

    def list_assignments_for_task(self, task_id: str) -> List[TaskAssignment]:
        return self._assignment_repo.list_by_assignment(task_id)

    def set_assignment_hours(self, assignment_id: str, hours_logged: float) -> TaskAssignment:
        if hours_logged < 0:
            raise ValidationError("hours_logged cannot be negative.")
        a = self._assignment_repo.get(assignment_id)
        task = self._task_repo.get(a.task_id)
        if not a:
            raise NotFoundError("Assignment not found.", code="ASSIGNMENT_NOT_FOUND")
        a.hours_logged = hours_logged
        try:
            self._assignment_repo.update(a)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            raise e
        domain_events.tasks_changed.emit(task.project_id)
        return a

    def get_assignment(self, assignment_id: str) -> TaskAssignment | None:
        return self._assignment_repo.get(assignment_id)    
    
    def delete_task(self, task_id: str) -> None:
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found")

        try:
            self._dependency_repo.delete_for_task(task_id)
            self._assignment_repo.delete_by_task(task_id)
            self._calendar_repo.delete_for_task(task_id)

            cost_items = self._cost_repo.list_by_project(task.project_id)
            for c in cost_items:
                if c.task_id == task_id:
                    self._cost_repo.delete(c.id)

            self._task_repo.delete(task_id)
        except Exception as e:
            self._session.rollback()
            raise e
        
        domain_events.tasks_changed.emit(task.project_id)
    
    def update_task(
        self,
        task_id: str,
        name: str | None = None,
        description: str | None = None,
        start_date: date | None = None,
        duration_days: int | None = None,
        status: TaskStatus | None = None,
        priority: int | None = None,
        deadline: date | None = None,
    ) -> Task:
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        if name is not None:
            task.name = name.strip()
        if description is not None:
            task.description = description.strip()
        if start_date is not None:
            task.start_date = start_date
        if duration_days is not None:
            if duration_days < 0:
                raise ValidationError("Task duration cannot be negative.")
            task.duration_days = duration_days

        # recompute end_date using working calendar if we have start + duration
        if task.start_date and task.duration_days is not None:
            task.end_date = self._work_calendar_engine.add_working_days(task.start_date, task.duration_days)

        if status is not None:
            task.status = status
        if priority is not None:
            task.priority = priority
        
        if deadline is not None:
            if deadline and task.start_date and deadline < task.start_date:
                raise ValidationError("Task deadline cannot be before start_date.")
            task.deadline = deadline
        
        self._validate_task_within_project_dates(task.project_id, task.start_date, task.end_date)
        
        try:
            self._task_repo.update(task)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            raise e

        domain_events.tasks_changed.emit(task.project_id)
        return task
    
    def update_progress(
            self,
            task_id: str,
            percent_complete: float | None = None,
            actual_start: date | None = None,
            actual_end: date | None = None,
        ) -> Task:
        
            today = date.today()
            task = self._task_repo.get(task_id)
            if not task:
                raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

            # Only validate and apply percent when provided
            if percent_complete is not None:
                if percent_complete < 0 or percent_complete > 100:
                    raise ValidationError("percent_complete must be between 0 and 100.")

                task.percent_complete = percent_complete
                
                # optional auto-status behavior based on provided percent
                if percent_complete == 0 and task.status != TaskStatus.TODO:
                    task.status = TaskStatus.TODO
                elif 0 < percent_complete < 100 and task.status == TaskStatus.TODO:
                    task.status = TaskStatus.IN_PROGRESS
                elif percent_complete == 100:
                    task.status = TaskStatus.DONE
                elif percent_complete < 100 and task.status == TaskStatus.DONE:
                    task.status = TaskStatus.IN_PROGRESS

            # Apply actual dates if provided; validate end against provided or existing start
            if actual_start is not None:
                task.actual_start = actual_start
            if actual_end is not None:
                check_start = actual_start if actual_start is not None else task.actual_start
                if check_start and actual_end < check_start:
                    raise ValidationError("Actual end date cannot be before actual start.")
                task.actual_end = actual_end
            self._validate_task_within_project_dates(task.project_id,task.actual_start,task.actual_end)
            
            try:
                self._task_repo.update(task)
                self._session.commit()
            except Exception as e:
                self._session.rollback()
                raise e

            domain_events.tasks_changed.emit(task.project_id)
            return task 
        
    def list_tasks_for_resource(self, resource_id: str) -> List[Task]:
        """
        Return all tasks this resource is assigned to.
        """
        assignments = self._assignment_repo.list_by_resource(resource_id)
        task_ids = {a.task_id for a in assignments}
        tasks: List[Task] = []
        for tid in task_ids:
            t = self._task_repo.get(tid)
            if t:
                tasks.append(t)
        return tasks
 
    def query_tasks(
        self,
        project_id: str | None = None,
        status: TaskStatus | None = None,
        resource_id: str | None = None,
        start_from: date | None = None,
        start_to: date | None = None,
        end_from: date | None = None,
        end_to: date | None = None,
    ) -> List[Task]:
        """
        Simple in-memory filters on top of repository queries.
        - If project_id is given, start with tasks for that project.
        - If resource_id given, intersect with tasks assigned to that resource.
        """

        # base set
        if project_id:
            tasks = self._task_repo.list_by_project(project_id)
        else:
            # if you want, add TaskRepository.list_all; otherwise, you can just
            # require project_id, or raise.
            raise ValidationError("project_id is required for query_tasks currently.")

        # filter by status
        if status:
            tasks = [t for t in tasks if t.status == status]

        # filter by dates
        if start_from:
            tasks = [t for t in tasks if t.start_date and t.start_date >= start_from]
        if start_to:
            tasks = [t for t in tasks if t.start_date and t.start_date <= start_to]
        if end_from:
            tasks = [t for t in tasks if t.end_date and t.end_date >= end_from]
        if end_to:
            tasks = [t for t in tasks if t.end_date and t.end_date <= end_to]

        # filter by resource
        if resource_id:
            assignments = self._assignment_repo.list_by_resource(resource_id)
            task_ids = {a.task_id for a in assignments}
            tasks = [t for t in tasks if t.id in task_ids]

        return tasks

    def assign_project_resource(self, task_id: str, project_resource_id: str, allocation_percent: float) -> TaskAssignment:
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        pr = self._project_resource_repo.get(project_resource_id)
        if not pr:
            raise NotFoundError("Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND")

        if pr.project_id != task.project_id:
            raise BusinessRuleError(
                "Selected resource is not linked to this task's project.",
                code="PROJECT_RESOURCE_MISMATCH",
            )

        if not getattr(pr, "is_active", True):
            raise BusinessRuleError("This project resource is inactive.", code="PROJECT_RESOURCE_INACTIVE")

        # This blocks assignments that would exceef 100% allocation on any day
        self._check_resource_overallocation(
            project_id= task.project_id,
            resource_id= pr.resource_id,
            new_task_id= task.id,
            new_alloc_percent= float(allocation_percent or 0.0)
        )
        
        # Keep resource_id for compatibility for now
        assignment = TaskAssignment.create(task_id, pr.resource_id, allocation_percent)
        setattr(assignment, "project_resource_id", pr.id)
        
        try:
            self._assignment_repo.add(assignment)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        
        domain_events.tasks_changed.emit(task.project_id)
        return assignment


    # -------------------------
    # Over-allocation validation (service-layer)
    # -------------------------
    def _iter_workdays(self, start: date, end: date):
        """Iterate dates between start/end inclusive.
        If you later add a true holiday calendar, update this here only.
        """
        if not start or not end:
            return
        if end < start:
            start, end = end, start
        cur = start
        while cur <= end:
            # basic Mon-Fri working day rule
            if cur.weekday() < 5:
                yield cur
            cur += timedelta(days=1)

    def _check_resource_overallocation(
        self,
        project_id: str,
        resource_id: str,
        new_task_id: str,
        new_alloc_percent: float,
    ) -> None:
        """
        Raises BusinessRuleError if adding/updating an assignment would
        over-allocate the resource (>100%) on any working day.

        Uses task planned dates (start_date/end_date). If tasks have no dates,
        they are ignored for overload checks.
        """
        # Need the new task range
        new_task = self._task_repo.get(new_task_id)
        if not new_task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        ns = getattr(new_task, "start_date", None)
        ne = getattr(new_task, "end_date", None)
        if not ns or not ne:
            # If no dates, we can't time-phase -> don't block assignment
            return

        # Pull ALL assignments for this resource (across tasks)
        assigns = self._assignment_repo.list_by_resource(resource_id)
        if not assigns:
            return

        # Build daily totals for the overlap window (we only need to check dates
        # that intersect the new task range)
        daily_total: dict[date, float] = {}
        daily_tasks: dict[date, list[str]] = {}

        for a in assigns:
            # Skip assignments from other projects
            t = self._task_repo.get(a.task_id)
            if not t or getattr(t, "project_id", None) != project_id:
                continue

            ts = getattr(t, "start_date", None)
            te = getattr(t, "end_date", None)
            if not ts or not te:
                continue

            # Only consider overlap with the NEW task window
            os = max(ns, ts)
            oe = min(ne, te)
            if oe < os:
                continue

            alloc = float(getattr(a, "allocation_percent", 0.0) or 0.0)
            if alloc <= 0:
                continue

            for d in self._iter_workdays(os, oe):
                daily_total[d] = daily_total.get(d, 0.0) + alloc
                daily_tasks.setdefault(d, []).append(getattr(t, "name", a.task_id))

        # Add the NEW allocation on top
        for d in self._iter_workdays(ns, ne):
            daily_total[d] = daily_total.get(d, 0.0) +  float(new_alloc_percent or 0.0)
            daily_tasks.setdefault(d, []).append(getattr(new_task, "name", new_task_id))

        # Find first violation (keep message short/pro)
        for d in sorted(daily_total.keys()):
            tot = daily_total[d]
            if tot > 100.0 + 1e-9:
                tasks = daily_tasks.get(d, [])[:6]
                extra = "..." if len(daily_tasks.get(d, [])) > 6 else ""
                msg = (
                    f"Resource would be over-allocated on {d.isoformat()} "
                    f"({tot:.1f}% > 100%).\n"
                    f"Tasks: {', '.join(tasks)}{extra}"
                )
                raise BusinessRuleError(msg, code="RESOURCE_OVERALLOCATED")
    
        