"""Resource-leveling preview assembly (R4.4Q) -- gathers the same
in-memory snapshot shape the planner's own tests build (leaf tasks,
assignments, dependencies, resource names), runs the ONE authoritative
``ResourceLevelingPlanner`` (application/scheduling/leveling/
resource_leveling_planner.py), and returns both the raw domain
``LevelingProposal`` (for the desktop API to cache and later hand back
to ``apply_resource_leveling_plan`` verbatim -- Apply must revalidate
against the EXACT snapshot Preview reasoned about) and its QML-facing
DTO.
"""
from __future__ import annotations

from src.core.modules.project_management.application.scheduling.leveling.resource_leveling_planner import (
    ResourceLevelingPlanner,
)
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks
from src.core.modules.project_management.api.desktop.scheduling.models.leveling import (
    SchedulingLevelingProposalDto,
)
from src.core.modules.project_management.api.desktop.scheduling.serializers.leveling_serializer import (
    serialize_leveling_proposal,
)


def build_resource_leveling_preview(project_id, task_service, work_calendar_engine):
    """Returns (LevelingProposal, SchedulingLevelingProposalDto), or
    None if the project/services aren't available."""
    if not project_id or task_service is None or work_calendar_engine is None:
        return None

    tasks = select_leaf_tasks(task_service._task_repo.list_by_project(project_id))
    tasks_by_id = {t.id: t for t in tasks}
    assignments = task_service._assignment_repo.list_by_tasks(list(tasks_by_id)) if tasks_by_id else []
    deps = task_service._dependency_repo.list_by_project(project_id)

    resource_ids = sorted({a.resource_id for a in assignments})
    resources = task_service._resource_repo.list_by_ids(resource_ids) if resource_ids else []
    resource_name_by_id = {r.id: r.name for r in resources}

    planner = ResourceLevelingPlanner(work_calendar_engine)
    proposal = planner.build_proposal(
        project_id=project_id,
        tasks_by_id=tasks_by_id,
        deps=deps,
        assignments=assignments,
        resource_name_by_id=resource_name_by_id,
    )
    return proposal, serialize_leveling_proposal(proposal)


def empty_leveling_proposal_dto(project_id: str = "") -> SchedulingLevelingProposalDto:
    return SchedulingLevelingProposalDto(
        project_id=project_id,
        schedule_fingerprint="",
        is_feasible=True,
        resource_conflicts_before=0,
        resource_conflicts_after=0,
        moves=(),
        unresolved_conflicts=(),
        project_finish_before_label="--",
        project_finish_after_label="--",
        critical_path_changed=False,
        warnings=(),
    )


__all__ = ["build_resource_leveling_preview", "empty_leveling_proposal_dto"]
