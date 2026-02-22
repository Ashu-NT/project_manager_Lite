# infra/db/repositories.py
from __future__ import annotations
from datetime import date
from typing import List, Optional, Set

from sqlalchemy.orm import Session
from sqlalchemy import select, or_, delete

from core.interfaces import (
    ProjectRepository,
    TaskRepository,
    ResourceRepository,
    AssignmentRepository,
    DependencyRepository,
    CostRepository,
    CalendarEventRepository,
    WorkingCalendarRepository,
    BaselineRepository,
    ProjectResourceRepository
)
from core.models import (
    Project,
    Task,
    Resource,
    TaskAssignment,
    TaskDependency,
    CostItem,
    CalendarEvent,
    ProjectBaseline,
    BaselineTask,
    ProjectResource
)
from infra.db.models import (
    ProjectORM,
    TaskORM,
    ResourceORM,
    TaskAssignmentORM,
    TaskDependencyORM,
    CostItemORM,
    CalendarEventORM,
    WorkingCalendarORM,
    HolidayORM,
    ProjectBaselineORM,
    BaselineTaskORM,
    ProjectResourceORM
)

from core.models import WorkingCalendar, Holiday, CostType


# --- mapping helpers ----------------------------------------------------------------

def project_to_orm(p: Project) -> ProjectORM:
    return ProjectORM(
        id=p.id,
        name=p.name,
        description=p.description,
        start_date=p.start_date,
        end_date=p.end_date,
        status=p.status,
        client_name=p.client_name,
        client_contact=p.client_contact,
        planned_budget=p.planned_budget,
        currency=p.currency,
    )

def project_from_orm(o: ProjectORM) -> Project:
    return Project(
        id=o.id,
        name=o.name,
        description=o.description,
        start_date=o.start_date,
        end_date=o.end_date,
        status=o.status,
        client_name=o.client_name,
        client_contact=o.client_contact,    
        planned_budget=o.planned_budget,
        currency=o.currency,
    )

def task_to_orm(t: Task) -> TaskORM:
    return TaskORM(
        id=t.id,
        project_id=t.project_id,
        name=t.name,
        description=t.description,
        start_date=t.start_date,
        end_date=t.end_date,
        duration_days=t.duration_days,
        status=t.status,
        priority=t.priority,
        percent_complete=t.percent_complete,
        actual_start=t.actual_start,
        actual_end=t.actual_end,
        deadline=t.deadline,
    )


def task_from_orm(o: TaskORM) -> Task:
    return Task(
        id=o.id,
        project_id=o.project_id,
        name=o.name,
        description=o.description,
        start_date=o.start_date,
        end_date=o.end_date,
        duration_days=o.duration_days,
        status=o.status,
        priority=o.priority,
        percent_complete=o.percent_complete,
        actual_start=o.actual_start,
        actual_end=o.actual_end,
        deadline=o.deadline,
    )

def resource_to_orm(r: Resource) -> ResourceORM:
    return ResourceORM(
        id=r.id,
        name=r.name,
        role=r.role,
        hourly_rate=r.hourly_rate,
        is_active=r.is_active,
        cost_type=r.cost_type,
        currency_code=r.currency_code,
    )

def resource_from_orm(o: ResourceORM) -> Resource:
    return Resource(
        id=o.id,
        name=o.name,
        role=o.role,
        hourly_rate=o.hourly_rate,
        is_active=o.is_active,
        cost_type=o.cost_type,
        currency_code=o.currency_code,
    )

def assignment_to_orm(a: TaskAssignment) -> TaskAssignmentORM:
    o = TaskAssignmentORM(
        id=a.id,
        task_id=a.task_id,
        resource_id=a.resource_id,
        project_resource_id = getattr(a, "project_resource_id", None),
        allocation_percent=a.allocation_percent,
        hours_logged=getattr(a, "hours_logged", 0.0),
    )
    #setattr(o, "project_resource_id", getattr(a, "project_resource_id", None))
    return o

def assignment_from_orm(o: TaskAssignmentORM) -> TaskAssignment:
    a = TaskAssignment(
        id=o.id,
        task_id=o.task_id,
        resource_id=o.resource_id,
        project_resource_id= getattr(o, "project_resource_id", None),
        allocation_percent=o.allocation_percent,
        hours_logged=getattr(o, "hours_logged", 0.0),
    )
    #setattr(a, "project_resource_id", getattr(o, "project_resource_id", None))
    return a
    

def dependency_to_orm(d: TaskDependency) -> TaskDependencyORM:
    return TaskDependencyORM(
        id=d.id,
        predecessor_task_id=d.predecessor_task_id,
        successor_task_id=d.successor_task_id,
        dependency_type=d.dependency_type,
        lag_days=d.lag_days,
    )

def dependency_from_orm(o: TaskDependencyORM) -> TaskDependency:
    return TaskDependency(
        id=o.id,
        predecessor_task_id=o.predecessor_task_id,
        successor_task_id=o.successor_task_id,
        dependency_type=o.dependency_type,
        lag_days=o.lag_days,
    )

def cost_to_orm(c: CostItem) -> CostItemORM:
    return CostItemORM(
        id=c.id,
        project_id=c.project_id,
        task_id=c.task_id,
        description=c.description,
        planned_amount=c.planned_amount,
        actual_amount=c.actual_amount,
        committed_amount=c.committed_amount,
        cost_type=(c.cost_type.value if hasattr(c.cost_type, 'value') else c.cost_type),
        incurred_date=c.incurred_date,
        currency_code=c.currency_code,
    )

def cost_from_orm(o: CostItemORM) -> CostItem:
    return CostItem(
        id=o.id,
        project_id=o.project_id,
        task_id=o.task_id,
        description=o.description,
        planned_amount=o.planned_amount,
        committed_amount=o.committed_amount,
        actual_amount=o.actual_amount,
        cost_type=CostType(o.cost_type) if o.cost_type else CostType.OVERHEAD,
        incurred_date=o.incurred_date,
        currency_code=o.currency_code,
    )

def event_to_orm(e: CalendarEvent) -> CalendarEventORM:
    return CalendarEventORM(
        id=e.id,
        title=e.title,
        start_date=e.start_date,
        end_date=e.end_date,
        project_id=e.project_id,
        task_id=e.task_id,
        all_day=e.all_day,
        description=e.description,
    )

def event_from_orm(o: CalendarEventORM) -> CalendarEvent:
    return CalendarEvent(
        id=o.id,
        title=o.title,
        start_date=o.start_date,
        end_date=o.end_date,
        project_id=o.project_id,
        task_id=o.task_id,
        all_day=o.all_day,
        description=o.description,
    )
 
def calendar_from_orm(o: WorkingCalendarORM) -> WorkingCalendar:
    days: Set[int] = set()
    if o.working_days:
        for part in o.working_days.split(","):
            part = part.strip()
            if part:
                days.add(int(part))
    return WorkingCalendar(
        id=o.id,
        name=o.name,
        working_days=days,
        hours_per_day=o.hours_per_day,
    )

def calendar_to_orm(c: WorkingCalendar) -> WorkingCalendarORM:
    wd_str = ",".join(str(d) for d in sorted(c.working_days))
    return WorkingCalendarORM(
        id=c.id,
        name=c.name,
        working_days=wd_str,
        hours_per_day=c.hours_per_day,
    )

def holiday_from_orm(o: HolidayORM) -> Holiday:
    return Holiday(
        id=o.id,
        calendar_id=o.calendar_id,
        date=o.date,
        name=o.name,
    )

def holiday_to_orm(h: Holiday) -> HolidayORM:
    return HolidayORM(
        id=h.id,
        calendar_id=h.calendar_id,
        date=h.date,
        name=h.name,
    )
 
def baseline_from_orm(o: ProjectBaselineORM) -> ProjectBaseline:
    return ProjectBaseline(id=o.id, project_id=o.project_id, name=o.name, created_at=o.created_at)

def baseline_to_orm(b: ProjectBaseline) -> ProjectBaselineORM:
    return ProjectBaselineORM(id=b.id, project_id=b.project_id, name=b.name, created_at=b.created_at)

def baseline_task_from_orm(o: BaselineTaskORM) -> BaselineTask:
    return BaselineTask(
        id=o.id,
        baseline_id=o.baseline_id,
        task_id=o.task_id,
        baseline_start=o.baseline_start,
        baseline_finish=o.baseline_finish,
        baseline_duration_days=o.baseline_duration_days,
        baseline_planned_cost=o.baseline_planned_cost,
    )

def baseline_task_to_orm(t: BaselineTask) -> BaselineTaskORM:
    return BaselineTaskORM(
        id=t.id,
        baseline_id=t.baseline_id,
        task_id=t.task_id,
        baseline_start=t.baseline_start,
        baseline_finish=t.baseline_finish,
        baseline_duration_days=t.baseline_duration_days,
        baseline_planned_cost=t.baseline_planned_cost,
    )

def project_resource_from_orm(o: ProjectResourceORM) -> ProjectResource:
    return ProjectResource(
        id=o.id,
        project_id=o.project_id,
        resource_id=o.resource_id,
        hourly_rate=o.hourly_rate,
        currency_code=o.currency_code,
        planned_hours=o.planned_hours,
        is_active=o.is_active,
    )

def project_resource_to_orm(r: ProjectResource) -> ProjectResourceORM:
    return ProjectResourceORM(
        id=r.id,
        project_id=r.project_id,
        resource_id=r.resource_id,
        hourly_rate=r.hourly_rate,
        currency_code=r.currency_code,
        planned_hours=r.planned_hours,
        is_active=r.is_active,
    )

# --- repositories --------------------------------------------------------------------

class SqlAlchemyProjectRepository(ProjectRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, project: Project) -> None:
        self.session.add(project_to_orm(project))
        

    def update(self, project: Project) -> None:
        self.session.merge(project_to_orm(project))
        

    def delete(self, project_id: str) -> None:
        self.session.query(ProjectORM).filter_by(id=project_id).delete()
        

    def get(self, project_id: str) -> Optional[Project]:
        obj = self.session.get(ProjectORM, project_id)
        return project_from_orm(obj) if obj else None

    def list_all(self) -> List[Project]:
        stmt = select(ProjectORM)
        rows = self.session.execute(stmt).scalars().all()
        return [project_from_orm(r) for r in rows]

class SqlAlchemyProjectResourceRepository(ProjectResourceRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, pr: ProjectResource) -> None:
        self.session.add(project_resource_to_orm(pr))
        

    def get(self, pr_id: str) -> Optional[ProjectResource]:
        obj = self.session.get(ProjectResourceORM, pr_id)
        return project_resource_from_orm(obj) if obj else None

    def list_by_project(self, project_id: str) -> List[ProjectResource]:
        stmt = select(ProjectResourceORM).where(ProjectResourceORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [project_resource_from_orm(r) for r in rows]

    def get_for_project(self, project_id: str, resource_id: str) -> Optional[ProjectResource]:
        stmt = select(ProjectResourceORM).where(
            ProjectResourceORM.project_id == project_id,
            ProjectResourceORM.resource_id == resource_id
        )
        obj = self.session.execute(stmt).scalars().first()
        return project_resource_from_orm(obj) if obj else None

    def delete(self, pr_id: str) -> None:
       o = self.session.get(ProjectResourceORM, pr_id)
       if o:
           self.session.delete(o)
    
    def delete_by_resource(self, res_id: str) -> None:
        self.session.query(ProjectResourceORM).filter_by(resource_id=res_id).delete()

    def update(self, pr: ProjectResource) -> None:
        self.session.merge(project_resource_to_orm(pr))

class SqlAlchemyTaskRepository(TaskRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, task: Task) -> None:
        self.session.add(task_to_orm(task))
        

    def update(self, task: Task) -> None:
        self.session.merge(task_to_orm(task))
        

    def delete(self, task_id: str) -> None:
        self.session.query(TaskORM).filter_by(id=task_id).delete()
        

    def get(self, task_id: str) -> Optional[Task]:
        obj = self.session.get(TaskORM, task_id)
        return task_from_orm(obj) if obj else None

    def list_by_project(self, project_id: str) -> List[Task]:
        stmt = select(TaskORM).where(TaskORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [task_from_orm(r) for r in rows]

class SqlAlchemyResourceRepository(ResourceRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, resource: Resource) -> None:
        self.session.add(resource_to_orm(resource))
        

    def update(self, resource: Resource) -> None:
        self.session.merge(resource_to_orm(resource))
        

    def delete(self, resource_id: str) -> None:
        self.session.query(ResourceORM).filter_by(id=resource_id).delete()
        

    def get(self, resource_id: str) -> Optional[Resource]:
        obj = self.session.get(ResourceORM, resource_id)
        return resource_from_orm(obj) if obj else None

    def list_all(self) -> List[Resource]:
        stmt = select(ResourceORM)
        rows = self.session.execute(stmt).scalars().all()
        return [resource_from_orm(r) for r in rows]

class SqlAlchemyAssignmentRepository(AssignmentRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, assignment: TaskAssignment) -> None:
        self.session.add(assignment_to_orm(assignment))
        
    def get(self, assignment_id: str) -> Optional[TaskAssignment]:
        obj = self.session.get(TaskAssignmentORM, assignment_id)
        return assignment_from_orm(obj) if obj else None

    def list_by_task(self, task_id: str) -> List[TaskAssignment]:
        stmt = select(TaskAssignmentORM).where(TaskAssignmentORM.task_id == task_id)
        rows = self.session.execute(stmt).scalars().all()
        return [assignment_from_orm(r) for r in rows]

    def list_by_resource(self, resource_id: str) -> List[TaskAssignment]:
        stmt = select(TaskAssignmentORM).where(TaskAssignmentORM.resource_id == resource_id)
        rows = self.session.execute(stmt).scalars().all()
        return [assignment_from_orm(r) for r in rows]

    def update(self, assignment: TaskAssignment) -> None:
        self.session.merge(assignment_to_orm(assignment))

    def delete(self, assignment_id: str) -> None:
        self.session.query(TaskAssignmentORM).filter_by(id=assignment_id).delete()
        

    def delete_by_task(self, task_id: str) -> None:
        self.session.query(TaskAssignmentORM).filter_by(task_id=task_id).delete()
        
    def list_by_assignment(self, task_id: str) -> List[TaskAssignment]:
        stmt = select(TaskAssignmentORM).where(TaskAssignmentORM.task_id == task_id)
        rows = self.session.execute(stmt).scalars().all()
        return [assignment_from_orm(r) for r in rows]
    
    def list_by_tasks(self, task_ids: List[str]) -> List[TaskAssignment]:
        
        if not task_ids:
            return []   
        stmt = select(TaskAssignmentORM).where(TaskAssignmentORM.task_id.in_(task_ids))
        rows = self.session.execute(stmt).scalars().all()   
        return [assignment_from_orm(r) for r in rows]
        

class SqlAlchemyDependencyRepository(DependencyRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, dependency: TaskDependency) -> None:
        self.session.add(dependency_to_orm(dependency))
        
    def get(self, dependency_id: str) -> Optional[TaskDependency]:
        obj = self.session.get(TaskDependencyORM, dependency_id)
        return dependency_from_orm(obj) if obj else None

    def list_by_project(self, project_id: str) -> List[TaskDependency]:
        task_ids_subq = select(TaskORM.id).where(TaskORM.project_id == project_id)
        stmt = select(TaskDependencyORM).where(
            TaskDependencyORM.predecessor_task_id.in_(task_ids_subq),
            TaskDependencyORM.successor_task_id.in_(task_ids_subq),
        )
        rows = self.session.execute(stmt).scalars().all()
        return [dependency_from_orm(r) for r in rows]

    def delete(self, dependency_id: str) -> None:
        self.session.query(TaskDependencyORM).filter_by(id=dependency_id).delete()
        

    def delete_for_task(self, task_id: str) -> None:
        self.session.query(TaskDependencyORM).filter(
            or_(
                TaskDependencyORM.predecessor_task_id == task_id,
                TaskDependencyORM.successor_task_id == task_id,
            )
        ).delete(synchronize_session=False)
    
    def list_by_task(self, task_id: str) -> List[TaskDependency]:
        stmt = select(TaskDependencyORM).where(
            or_(
                TaskDependencyORM.predecessor_task_id == task_id,
                TaskDependencyORM.successor_task_id == task_id,
            )
        )
        rows = self.session.execute(stmt).scalars().all()
        return [dependency_from_orm(r) for r in rows]
    
   
class SqlAlchemyCostRepository(CostRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, cost_item: CostItem) -> None:
        self.session.add(cost_to_orm(cost_item))
        

    def update(self, cost_item: CostItem) -> None:
        self.session.merge(cost_to_orm(cost_item))
        

    def delete(self, cost_id: str) -> None:
        self.session.query(CostItemORM).filter_by(id=cost_id).delete()
        

    def list_by_project(self, project_id: str) -> List[CostItem]:
        stmt = select(CostItemORM).where(CostItemORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [cost_from_orm(r) for r in rows]

    def delete_by_project(self, project_id: str) -> None:
        self.session.query(CostItemORM).filter_by(project_id=project_id).delete()
        
    def get(self, cost_id: str) -> Optional[CostItem]:
        obj = self.session.get(CostItemORM, cost_id)
        return cost_from_orm(obj) if obj else None
        

class SqlAlchemyCalendarEventRepository(CalendarEventRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, event: CalendarEvent) -> None:
        self.session.add(event_to_orm(event))
        

    def update(self, event: CalendarEvent) -> None:
        self.session.merge(event_to_orm(event))
        

    def delete(self, event_id: str) -> None:
        self.session.query(CalendarEventORM).filter_by(id=event_id).delete()
        

    def get(self, event_id: str) -> Optional[CalendarEvent]:
        obj = self.session.get(CalendarEventORM, event_id)
        return event_from_orm(obj) if obj else None

    def list_for_project(self, project_id: str) -> List[CalendarEvent]:
        stmt = select(CalendarEventORM).where(CalendarEventORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [event_from_orm(r) for r in rows]

    def list_range(self, start_date: date, end_date: date) -> List[CalendarEvent]:
        stmt = select(CalendarEventORM).where(
            CalendarEventORM.end_date >= start_date,
            CalendarEventORM.start_date <= end_date,
        )
        rows = self.session.execute(stmt).scalars().all()
        return [event_from_orm(r) for r in rows]

    def delete_for_task(self, task_id: str) -> None:
        self.session.query(CalendarEventORM).filter_by(task_id=task_id).delete()
        

    def delete_for_project(self, project_id: str) -> None:
        self.session.query(CalendarEventORM).filter_by(project_id=project_id).delete()
 
class SqlAlchemyWorkingCalendarRepository(WorkingCalendarRepository):
    def __init__(self, session: Session):
        self.session = session

    def get(self, calendar_id: str) -> Optional[WorkingCalendar]:
        obj = self.session.get(WorkingCalendarORM, calendar_id)
        return calendar_from_orm(obj) if obj else None

    def get_default(self) -> Optional[WorkingCalendar]:
        return self.get("default")

    def upsert(self, calendar: WorkingCalendar) -> None:
        """
        Insert or update calendar using merge() so we never create duplicates
        for the same id in a single flush/transaction.
        """
        existing = self.session.get(WorkingCalendarORM, calendar.id)
        wd_str = ",".join(str(d) for d in sorted(calendar.working_days))
        if existing:
            # update fields
            existing.name = calendar.name
            existing.working_days = wd_str
            existing.hours_per_day = calendar.hours_per_day
        else:
            self.session.add(
                WorkingCalendarORM(
                    id=calendar.id,
                    name=calendar.name,
                    working_days=wd_str,
                    hours_per_day=calendar.hours_per_day,
                )
            )

    def list_holidays(self, calendar_id: str) -> List[Holiday]:
        stmt = select(HolidayORM).where(HolidayORM.calendar_id == calendar_id)
        rows = self.session.execute(stmt).scalars().all()
        return [holiday_from_orm(r) for r in rows]

    def add_holiday(self, holiday: Holiday) -> None:
        self.session.add(holiday_to_orm(holiday))

    def delete_holiday(self, holiday_id: str) -> None:
        self.session.query(HolidayORM).filter_by(id=holiday_id).delete()            
 

class SqlAlchemyBaselineRepository(BaselineRepository):
    def __init__(self, session: Session):
        self.session = session

    def add_baseline(self, b: ProjectBaseline) -> ProjectBaseline:
        self.session.add(baseline_to_orm(b))
        return b

    def get_baseline(self, baseline_id: str) -> Optional[ProjectBaseline]:
        row = self.session.get(ProjectBaselineORM, baseline_id)
        return baseline_from_orm(row) if row else None

    def get_latest_for_project(self, project_id: str) -> Optional[ProjectBaseline]:
        stmt = select(ProjectBaselineORM).where(ProjectBaselineORM.project_id == project_id).order_by(ProjectBaselineORM.created_at.desc())
        row = self.session.execute(stmt).scalars().first()
        return baseline_from_orm(row) if row else None

    def list_for_project(self, project_id: str) -> List[ProjectBaseline]:
        stmt = select(ProjectBaselineORM).where(ProjectBaselineORM.project_id == project_id).order_by(ProjectBaselineORM.created_at.desc())
        rows = self.session.execute(stmt).scalars().all()
        return [baseline_from_orm(r) for r in rows]

    def delete_baseline(self, baseline_id: str) -> None:
        row = self.session.get(ProjectBaselineORM, baseline_id)
        if row:
            self.session.delete(row)

    def add_baseline_tasks(self, tasks: List[BaselineTask]) -> None:
        self.session.add_all([baseline_task_to_orm(t) for t in tasks])

    def list_tasks(self, baseline_id: str) -> List[BaselineTask]:
        stmt = select(BaselineTaskORM).where(BaselineTaskORM.baseline_id == baseline_id)
        rows = self.session.execute(stmt).scalars().all()
        return [baseline_task_from_orm(r) for r in rows]

    def delete_tasks(self, baseline_id: str) -> None:
        stmt = delete(BaselineTaskORM).where(BaselineTaskORM.baseline_id == baseline_id)
        self.session.execute(stmt)         
