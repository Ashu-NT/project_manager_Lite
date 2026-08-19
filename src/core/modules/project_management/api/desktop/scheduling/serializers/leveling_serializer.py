"""Serializes a domain LevelingProposal (application layer, never
persisted -- see application/scheduling/models/leveling.py) into the
desktop DTOs QML renders. Every raw fact (dates, reason, float,
criticality, deadline warning) is copied verbatim from the planner's
own decision -- QML never re-derives WHY a move was proposed."""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.scheduling.models.leveling import (
    SchedulingLevelingProposalDto,
    SchedulingProposedTaskMoveDto,
    SchedulingUnresolvedConflictDto,
)


def _date_label(value: date | None) -> str:
    return value.strftime("%b %d, %Y") if value else "--"


def serialize_leveling_proposal(proposal) -> SchedulingLevelingProposalDto:
    return SchedulingLevelingProposalDto(
        project_id=proposal.project_id,
        schedule_fingerprint=proposal.schedule_fingerprint,
        is_feasible=proposal.is_feasible,
        resource_conflicts_before=proposal.resource_conflicts_before,
        resource_conflicts_after=proposal.resource_conflicts_after,
        moves=tuple(_serialize_move(move) for move in proposal.moves),
        unresolved_conflicts=tuple(
            _serialize_unresolved_conflict(conflict) for conflict in proposal.unresolved_conflicts
        ),
        project_finish_before_label=_date_label(proposal.project_finish_before),
        project_finish_after_label=_date_label(proposal.project_finish_after),
        critical_path_changed=proposal.critical_path_changed,
        warnings=tuple(proposal.warnings),
    )


def _serialize_move(move) -> SchedulingProposedTaskMoveDto:
    return SchedulingProposedTaskMoveDto(
        task_id=move.task_id,
        task_name=move.task_name,
        wbs_code=move.wbs_code,
        old_start=move.old_start.isoformat(),
        old_start_label=_date_label(move.old_start),
        old_finish_label=_date_label(move.old_finish),
        new_start=move.new_start.isoformat(),
        new_start_label=_date_label(move.new_start),
        new_finish_label=_date_label(move.new_finish),
        shift_working_days=move.shift_working_days,
        reason=move.reason,
        resource_names_label=", ".join(move.resource_names) if move.resource_names else "--",
        float_before=move.float_before,
        float_after=move.float_after,
        critical_before=move.critical_before,
        critical_after=move.critical_after,
        infeasible_after=move.infeasible_after,
        deadline_warning=move.deadline_warning,
    )


def _serialize_unresolved_conflict(conflict) -> SchedulingUnresolvedConflictDto:
    return SchedulingUnresolvedConflictDto(
        resource_id=conflict.resource_id,
        resource_name=conflict.resource_name,
        conflict_date_label=_date_label(conflict.conflict_date),
        total_allocation_percent=conflict.total_allocation_percent,
        total_allocation_label=f"{conflict.total_allocation_percent:.0f}%",
        reason=conflict.reason,
    )


__all__ = ["serialize_leveling_proposal"]
