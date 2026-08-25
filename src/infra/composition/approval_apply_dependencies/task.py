"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `dependencies_factory(session)` for the Task
family -- `dependency.add`, `dependency.remove`, `dependency.update`, `task.constraint.update`,
`scheduling.leveling.apply`.

Follows `build_budget_approval_deps` (the reference template every other approval-backed
family's own `build_<x>_approval_deps` follows) as closely as the Task family's own real
construction allows. It is a plain function -- never a generic, type-keyed registry -- called
explicitly at its own `register_apply_handler` call site.

Unlike Budget, the Task apply-decision methods call two further session-sensitive collaborators
that Budget's methods never touch:

* ``self._sync_project_schedule`` (used by all of dependency add/remove/update and
  constraint-update) delegates to ``self._scheduling_engine.recalculate_project_schedule(...,
  commit=False)`` -- if this ran against a *different* Session than the one the dependency/
  constraint/leveling mutation itself lands on, the recalculated task dates would never
  participate in the same transaction as that mutation. So, mirroring exactly how
  `project_registry.py` builds its own long-lived `scheduling_engine`, this factory builds a
  fresh `SchedulingEngine` bound to `session` on every call.
* ``record_activity`` (called by all five methods) resolves `self._activity_service`, and
  `ActivityService` itself holds a `Session` (`session=...`) -- exactly the kind of
  permanently-bound collaborator this phase exists to stop reusing. A fresh `ActivityService`,
  bound to `session`, is built here rather than reusing `platform_services.activity_service`.

`work_calendar_engine`/`enterprise_calendar_resolver`/`calendar_assignment_service` are, like
Budget's `user_session`/`tenant_context_service`, ambient collaborators one layer up in
`PlatformServiceBundle` -- read-only calendar lookups that never themselves participate in this
transaction's write set (`SchedulingEngine` only ever *writes* through the fresh, `session`-bound
`task_repo` this factory builds) -- so, per ADR-005 Section 24 Round 7's "ambient collaborators
... may be reused as-is" rule, they are passed through rather than rebuilt.

`timesheet_service` is the one required-but-`None`-typed `TaskService` constructor argument left
as `None`: none of the five apply-decision methods reference `self._timesheet_service` (confirmed
by grep), and building a real one would require an entirely separate tree of session-bound
collaborators no apply path here ever exercises.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.scheduling import (
    ProjectCalendarAdapter,
    SchedulingEngine,
)
from src.core.modules.project_management.application.tasks.service import TaskService
from src.core.modules.project_management.infrastructure.approval.task_apply_participant import (
    TaskApprovalDeps,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.infra.composition.approval_apply_dependencies._shared import wire_tenant_context_service
from src.infra.composition.repositories import build_repository_bundle


def build_task_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    work_calendar_engine: CalendarProtocol,
    enterprise_calendar_resolver,
    calendar_assignment_service,
    module_catalog_service=None,
) -> TaskApprovalDeps:
    """Every transaction-sensitive collaborator (every repository, `ActivityService`,
    `SchedulingEngine`, and `TaskService` itself) is constructed fresh, bound to `session` --
    never the caller's own, possibly different, Session. `user_session`/`tenant_context_service`/
    `module_catalog_service`/`work_calendar_engine`/`enterprise_calendar_resolver`/
    `calendar_assignment_service` are ambient, stateless-with-respect-to-this-transaction
    collaborators, passed through as-is. `approval_service` is deliberately omitted -- see
    `task_apply_participant.py`'s module docstring."""
    bundle = build_repository_bundle(session)
    # Matches platform_registry.py's own "wire _tenant_context_service on every repo that
    # supports it" loop -- several of TaskService's mixins (not just the five apply-decision
    # methods this participant calls) raise TENANT_CONTEXT_REQUIRED outright when this is unset.
    for field_name in bundle.__dataclass_fields__:
        wire_tenant_context_service(getattr(bundle, field_name), tenant_context_service)

    activity_service = ActivityService(
        session=session,
        activity_repo=bundle.activity_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    project_calendar_adapter = ProjectCalendarAdapter(
        resolver=enterprise_calendar_resolver,
        assignment_service=calendar_assignment_service,
    )
    scheduling_engine = SchedulingEngine(
        session,
        bundle.task_repo,
        bundle.dependency_repo,
        work_calendar_engine,
        assignment_repo=bundle.assignment_repo,
        resource_repo=bundle.resource_repo,
        project_calendar_adapter=project_calendar_adapter,
    )
    task_service = TaskService(
        session,
        bundle.task_repo,
        bundle.dependency_repo,
        bundle.assignment_repo,
        bundle.time_entry_repo,
        bundle.timesheet_period_repo,
        None,  # timesheet_service -- see module docstring
        bundle.resource_repo,
        work_calendar_engine,
        scheduling_engine,
        bundle.project_resource_repo,
        bundle.project_repo,
        user_session=user_session,
        activity_service=activity_service,
        approval_service=None,
        module_catalog_service=module_catalog_service,
        employee_repo=bundle.employee_repo,
        tenant_context_service=tenant_context_service,
    )
    return TaskApprovalDeps(task_service=task_service)


__all__ = ["build_task_approval_deps"]
