"""Resource-leveling preview assembly -- calls the application layer's own
``build_resource_leveling_preview`` (application/tasks/commands/resource_leveling_apply.py,
which runs the ONE authoritative ``ResourceLevelingPlanner`` against a fresh in-memory
snapshot) and returns both the raw domain ``LevelingProposal`` (for the desktop API to
cache and later hand back to ``apply_resource_leveling_plan`` verbatim -- Apply must
revalidate against the EXACT snapshot Preview reasoned about) and its QML-facing DTO.
"""
from __future__ import annotations

from src.core.modules.project_management.api.desktop.scheduling.models.leveling import (
    SchedulingLevelingProposalDto,
)
from src.core.modules.project_management.api.desktop.scheduling.serializers.leveling_serializer import (
    serialize_leveling_proposal,
)


def build_resource_leveling_preview(project_id, task_service):
    """Returns (LevelingProposal, SchedulingLevelingProposalDto), or
    None if the project/service aren't available."""
    if not project_id or task_service is None:
        return None

    proposal = task_service.build_resource_leveling_preview(project_id)
    if proposal is None:
        return None
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
