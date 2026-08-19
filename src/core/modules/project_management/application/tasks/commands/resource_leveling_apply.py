from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    is_admin_session,
    require_permission,
)
from src.core.platform.domain.approval.policy import is_governance_required
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError
from src.core.shared.activity import record_activity
from src.core.shared.events.domain_events import domain_events
from src.core.modules.project_management.application.scheduling.leveling.schedule_fingerprint import (
    compute_schedule_fingerprint,
)
from src.core.modules.project_management.application.scheduling.models.leveling import LevelingProposal


def _coerce_date(value: date | str) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


class ResourceLevelingApplyMixin:
    """R4.4M/R4.4O -- persists a previously-computed ``LevelingProposal``
    (R4.4K, always built by ``ResourceLevelingPlanner`` against an
    in-memory snapshot that never itself writes to the repository).

    Mirrors TaskSchedulingConstraintMixin's shape end to end: a public
    gate method that runs the governed/ungoverned branch (request-time),
    and an internal ``_apply_resource_leveling_plan_decision`` that does
    the actual atomic mutate+recalculate+commit (apply-time) -- reused
    directly, with ``commit=False``, by the approval apply-handler
    registered in the composition root when a governed request is later
    approved. The staleness guard is R4.4L's schedule fingerprint rather
    than a single task's ``version``, since a leveling plan spans many
    tasks at once and a per-task version check could pass for some moves
    while the ones that actually made the preview stale go unnoticed --
    this also naturally re-validates a governed request at apply time
    (TOCTOU-safe), exactly like the version re-check other governed
    commands in this module perform.
    """

    def _leveling_snapshot(self, project_id: str):
        tasks = select_leaf_tasks(self._task_repo.list_by_project(project_id))
        tasks_by_id = {t.id: t for t in tasks}
        assignments = self._assignment_repo.list_by_tasks(list(tasks_by_id)) if tasks_by_id else []
        deps = self._dependency_repo.list_by_project(project_id)
        return tasks_by_id, assignments, deps

    def apply_resource_leveling_plan(
        self,
        project_id: str,
        proposal: LevelingProposal,
    ) -> list[Task]:
        governed = (
            self._approval_service is not None
            and is_governance_required("scheduling.leveling.apply")
            and not is_admin_session(self._user_session)
        )
        if governed:
            require_permission(
                self._user_session, "approval.request", operation_label="request resource leveling apply"
            )
            require_project_permission(
                self._user_session, project_id, "approval.request", operation_label="request resource leveling apply"
            )
        else:
            require_permission(self._user_session, "task.manage", operation_label="apply resource leveling plan")
            require_project_permission(
                self._user_session, project_id, "task.manage", operation_label="apply resource leveling plan"
            )

        if not proposal.moves:
            return []

        if governed:
            request = self._approval_service.request_change(
                request_type="scheduling.leveling.apply",
                entity_type="project",
                entity_id=project_id,
                project_id=project_id,
                payload={
                    "schedule_fingerprint": proposal.schedule_fingerprint,
                    "moves": [
                        {
                            "task_id": move.task_id,
                            "new_start": move.new_start.isoformat(),
                            "reason": move.reason,
                        }
                        for move in proposal.moves
                    ],
                },
            )
            raise BusinessRuleError(
                f"Approval required for resource leveling apply. Request {request.id} created.",
                code="APPROVAL_REQUIRED",
            )

        return self._apply_resource_leveling_plan_decision(
            project_id=project_id,
            moves=[
                {"task_id": move.task_id, "new_start": move.new_start, "reason": move.reason}
                for move in proposal.moves
            ],
            schedule_fingerprint=proposal.schedule_fingerprint,
            commit=True,
        )

    def _apply_resource_leveling_plan_decision(
        self,
        *,
        project_id: str,
        moves: list[dict],
        schedule_fingerprint: str,
        commit: bool,
    ) -> list[Task]:
        """Apply immediately (ungoverned path) or when an approved
        ``scheduling.leveling.apply`` request is finally applied.
        Re-derives the CURRENT fingerprint from a fresh snapshot rather
        than trusting request-time facts -- real mutations may have
        landed on any involved task/dependency/assignment since the
        proposal (or the governed request carrying it) was built."""
        tasks_by_id, assignments, deps = self._leveling_snapshot(project_id)
        current_fingerprint = compute_schedule_fingerprint(tasks_by_id, deps, assignments)
        if current_fingerprint != schedule_fingerprint:
            raise ConcurrencyError(
                "The schedule changed since this leveling plan was previewed -- "
                "re-run the preview before applying.",
                code="STALE_SCHEDULE_FINGERPRINT",
            )

        if not moves:
            return []

        try:
            updated_ids: list[str] = []
            for move in moves:
                task_id = move["task_id"]
                task = tasks_by_id.get(task_id)
                if task is None:
                    raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
                old_start = task.start_date
                new_start = _coerce_date(move["new_start"])
                candidate = replace(task, resource_leveling_not_before=new_start)
                self._task_repo.update(candidate)
                updated_ids.append(task_id)
                # Per-task audit entry (matching the entity_type="task"
                # convention every other schedule-affecting command in
                # this module uses) so the moved task's OWN activity feed
                # explains why its start changed -- a project-level-only
                # summary would leave that task's history silent.
                record_activity(
                    self,
                    action="scheduling.leveling.apply",
                    entity_type="task",
                    entity_id=task_id,
                    module="project_management",
                    workspace_id=project_id,
                    details={
                        "old_start": old_start.isoformat() if old_start else None,
                        "new_start": new_start.isoformat(),
                        "reason": move.get("reason", ""),
                        "schedule_fingerprint": schedule_fingerprint,
                    },
                    commit=False,
                )

            self._sync_project_schedule(project_id, commit=False)
            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except Exception:
            if commit:
                self._session.rollback()
            raise

        if commit:
            domain_events.tasks_changed.emit(project_id)
        return [self._task_repo.get(task_id) for task_id in updated_ids]


__all__ = ["ResourceLevelingApplyMixin"]
