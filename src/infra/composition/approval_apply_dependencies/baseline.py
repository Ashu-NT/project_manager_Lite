"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `dependencies_factory(session)` for
`baseline.create` (apply only).

Follows `build_budget_approval_deps` (the reference template every other approval-backed
family's own `build_<x>_approval_deps` follows). It is a plain function -- never a generic,
type-keyed registry -- called explicitly at its own `register_apply_handler` call site.

`BaselineService` needs a `SchedulingEngine` collaborator (to recompute the project's schedule
before snapshotting it into the baseline). `SchedulingEngine` is itself session-bound, so a fresh
one is constructed here too, bound to the same `session`, mirroring exactly how
`project_registry.py` constructs it in production: `calendar` is the enterprise
global-calendar shim and `project_calendar_adapter` is the enterprise calendar adapter --
both ambient, ADR-005 Section 24 Round 7 "reused as-is" collaborators (neither is Session-bound
in the way a repository is), passed through unchanged. `calendar_resolver` /
`resource_calendar_map` are left `None` because production never passes them to
`SchedulingEngine` either (per-resource calendar overrides are not wired up there).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.scheduling.services.scheduling_engine import (
    SchedulingEngine,
)
from src.core.modules.project_management.infrastructure.approval.baseline_apply_participant import (
    BaselineApprovalDeps,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.infra.composition.approval_apply_dependencies._shared import (
    build_activity_service,
    wire_tenant_context_service,
)
from src.infra.composition.repositories import build_repository_bundle


def build_baseline_approval_deps(
    session: Session,
    *,
    user_session: Any,
    tenant_context_service: Any,
    calendar: CalendarProtocol,
    module_catalog_service: Any = None,
    calendar_resolver: Any = None,
    resource_calendar_map: dict[str, CalendarProtocol] | None = None,
    project_calendar_adapter: Any = None,
) -> BaselineApprovalDeps:
    """Every transaction-sensitive collaborator (every repository, `SchedulingEngine`,
    `ActivityService`, and `BaselineService` itself) is constructed fresh, bound to `session` --
    never the caller's own, possibly different, Session. `user_session` /
    `tenant_context_service` / `module_catalog_service` / `calendar` / `calendar_resolver` /
    `resource_calendar_map` / `project_calendar_adapter` are ambient, stateless-with-respect-to-
    this-transaction collaborators, passed through as-is (ADR-005 Section 24, Round 7's "ambient
    collaborators ... may be reused as-is" rule). `approval_service` is deliberately omitted --
    see `baseline_apply_participant.py`'s module docstring."""
    bundle = build_repository_bundle(session)
    project_repo = wire_tenant_context_service(bundle.project_repo, tenant_context_service)
    task_repo = wire_tenant_context_service(bundle.task_repo, tenant_context_service)
    dependency_repo = wire_tenant_context_service(bundle.dependency_repo, tenant_context_service)
    assignment_repo = wire_tenant_context_service(bundle.assignment_repo, tenant_context_service)
    resource_repo = wire_tenant_context_service(bundle.resource_repo, tenant_context_service)
    planned_cost_repo = wire_tenant_context_service(
        bundle.planned_cost_repo, tenant_context_service
    )
    baseline_repo = wire_tenant_context_service(bundle.baseline_repo, tenant_context_service)

    scheduling_engine = SchedulingEngine(
        session,
        task_repo,
        dependency_repo,
        calendar,
        assignment_repo=assignment_repo,
        resource_repo=resource_repo,
        calendar_resolver=calendar_resolver,
        resource_calendar_map=resource_calendar_map,
        project_calendar_adapter=project_calendar_adapter,
    )
    activity_service = build_activity_service(
        session,
        bundle,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    baseline_service = BaselineService(
        session=session,
        project_repo=project_repo,
        task_repo=task_repo,
        planned_cost_repo=planned_cost_repo,
        baseline_repo=baseline_repo,
        scheduling=scheduling_engine,
        calendar=calendar,
        user_session=user_session,
        activity_service=activity_service,
        approval_service=None,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
    )
    return BaselineApprovalDeps(baseline_service=baseline_service)


__all__ = ["build_baseline_approval_deps"]
