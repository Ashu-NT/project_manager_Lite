from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from src.core.modules.project_management.domain.tasks.task import TaskDependency
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.domain.approval.policy import is_governance_required
from src.core.shared.activity import record_activity
from src.core.platform.application.security.authorization.enforcement.permission_checks import is_admin_session, require_permission
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.shared.events.domain_events import domain_events
from src.core.modules.project_management.domain.enums import DependencyType

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
        DependencyDiagnostic,
    )
    from src.core.modules.project_management.contracts.repositories.tasks.task import (
        DependencyRepository,
        TaskRepository,
    )


def _raise_for_invalid_diagnostic(diagnostic: "DependencyDiagnostic") -> None:
    """Shared error-mapping for a failed DependencyDiagnostic, used by both
    the request-time check (add/update) and the apply-time re-check
    (Phase H1) so the two can never map codes to exception types
    differently."""
    message = diagnostic.summary
    if diagnostic.detail:
        message = f"{diagnostic.summary}\n{diagnostic.detail}"
    if diagnostic.code == "TASK_NOT_FOUND":
        raise NotFoundError(message, code=diagnostic.code)
    if diagnostic.code == "DEPENDENCY_CYCLE":
        raise BusinessRuleError(message, code=diagnostic.code)
    raise ValidationError(message, code=diagnostic.code)


class TaskDependencyMixin:
    """Governed dependency lifecycle for add/remove/update. All three go
    through matching authorization/project-scope/governance/transaction
    machinery -- see docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
    Phase H. Approved requests for any of the three are applied via
    ``_apply_dependency_*_decision``, each of which re-validates against the
    CURRENT graph at apply time rather than trusting request-time
    validation (Phase H1's TOCTOU fix)."""

    _session: Session
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository

    def get_dependency(self, dep_id: str) -> TaskDependency | None:
        require_permission(self._user_session, "task.read", operation_label="view dependency")
        dependency = self._dependency_repo.get(dep_id)
        if dependency is None:
            return None
        predecessor = self._task_repo.get(dependency.predecessor_task_id)
        successor = self._task_repo.get(dependency.successor_task_id)
        project_id = predecessor.project_id if predecessor else (successor.project_id if successor else None)
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "task.read",
                operation_label="view dependency",
            )
        return dependency

    def add_dependency(
        self,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
    ) -> TaskDependency:
        predecessor = self._task_repo.get(predecessor_id)
        if not predecessor:
            raise NotFoundError("Predecessor task not found", code="TASK_NOT_FOUND")
        successor = self._task_repo.get(successor_id)
        if not successor:
            raise NotFoundError("Successor task not found", code="TASK_NOT_FOUND")
        self._require_leaf_task(predecessor, operation_label="participate in dependencies")
        self._require_leaf_task(successor, operation_label="participate in dependencies")
        governed = (
            self._approval_service is not None
            and is_governance_required("dependency.add")
            and not is_admin_session(self._user_session)
        )
        if governed:
            require_permission(self._user_session, "approval.request", operation_label="request dependency change")
            require_project_permission(
                self._user_session,
                predecessor.project_id,
                "approval.request",
                operation_label="request dependency change",
            )
        else:
            require_permission(self._user_session, "task.manage", operation_label="add dependency")
            require_project_permission(
                self._user_session,
                predecessor.project_id,
                "task.manage",
                operation_label="add dependency",
            )
        # Also scope-check the successor's project explicitly (not just the
        # predecessor's) -- the cross-project rule below still prevents any
        # SUCCESSFUL cross-project write, but omitting this check let an
        # authorized-on-predecessor-only caller distinguish "successor id
        # exists in a project I can't see" (DEPENDENCY_CROSS_PROJECT) from
        # "successor id doesn't exist" (TASK_NOT_FOUND) -- an information
        # disclosure oracle within a tenant. See §15 finding 4b.
        if successor.project_id != predecessor.project_id:
            require_project_permission(
                self._user_session,
                successor.project_id,
                "approval.request" if governed else "task.manage",
                operation_label="request dependency change" if governed else "add dependency",
            )
        diagnostic = self.get_dependency_diagnostics(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            include_impact=False,
        )
        if not diagnostic.is_valid:
            _raise_for_invalid_diagnostic(diagnostic)
        if governed:
            request = self._approval_service.request_change(
                request_type="dependency.add",
                entity_type="task_dependency",
                entity_id=successor_id,
                project_id=predecessor.project_id,
                payload={
                    "predecessor_id": predecessor_id,
                    "predecessor_name": predecessor.name,
                    "successor_id": successor_id,
                    "successor_name": successor.name,
                    "dependency_type": dependency_type.value,
                    "lag_days": lag_days,
                },
            )
            raise BusinessRuleError(
                f"Approval required for dependency change. Request {request.id} created.",
                code="APPROVAL_REQUIRED",
            )
        return self._apply_dependency_add_decision(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            commit=True,
        )

    def _apply_dependency_add_decision(
        self,
        *,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType,
        lag_days: int,
        commit: bool,
    ) -> TaskDependency:
        """Apply an add — either immediately (ungoverned path) or when an
        approved ``dependency.add`` request is finally applied. In the
        governed case, real time may have passed since the original
        request was validated, so this re-runs the full validation against
        the CURRENT graph rather than trusting the request-time diagnostic
        (Phase H1: closes the TOCTOU hole where two concurrently-approved
        requests could otherwise both apply and persist a cycle, or an
        endpoint could have become a summary task, moved project, etc. in
        the meantime)."""
        predecessor = self._task_repo.get(predecessor_id)
        if predecessor is None:
            raise NotFoundError("Predecessor task not found", code="TASK_NOT_FOUND")
        successor = self._task_repo.get(successor_id)
        if successor is None:
            raise NotFoundError("Successor task not found", code="TASK_NOT_FOUND")
        self._require_leaf_task(predecessor, operation_label="participate in dependencies")
        self._require_leaf_task(successor, operation_label="participate in dependencies")
        diagnostic = self.get_dependency_diagnostics(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            include_impact=False,
        )
        if not diagnostic.is_valid:
            _raise_for_invalid_diagnostic(diagnostic)
        dependency = TaskDependency.create(predecessor_id, successor_id, dependency_type, lag_days)
        try:
            self._dependency_repo.add(dependency)
            self._sync_project_schedule(predecessor.project_id, commit=False)
            record_activity(
                self,
                action="dependency.add",
                entity_type="task_dependency",
                entity_id=dependency.id,
                module="project_management",
                workspace_id=predecessor.project_id,
                details={
                    "predecessor_name": predecessor.name,
                    "successor_name": successor.name,
                    "type": dependency.dependency_type.value,
                    "lag_days": dependency.lag_days,
                },
                commit=False,
            )
            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except Exception as exc:
            if commit:
                self._session.rollback()
            raise exc
        if commit:
            domain_events.tasks_changed.emit(predecessor.project_id)
        return dependency

    def remove_dependency(self, dep_id: str) -> None:
        governed = (
            self._approval_service is not None
            and is_governance_required("dependency.remove")
            and not is_admin_session(self._user_session)
        )
        if governed:
            require_permission(self._user_session, "approval.request", operation_label="request dependency removal")
        else:
            require_permission(self._user_session, "task.manage", operation_label="remove dependency")
        dependency = self._dependency_repo.get(dep_id)
        if not dependency:
            raise NotFoundError("Dependency not found.", code="DEPENDENCY_NOT_FOUND")
        predecessor = self._task_repo.get(dependency.predecessor_task_id)
        successor = self._task_repo.get(dependency.successor_task_id)
        project_id = predecessor.project_id if predecessor else (successor.project_id if successor else None)
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "approval.request" if governed else "task.manage",
                operation_label="request dependency removal" if governed else "remove dependency",
            )
        if governed:
            request = self._approval_service.request_change(
                request_type="dependency.remove",
                entity_type="task_dependency",
                entity_id=dependency.id,
                project_id=project_id,
                payload={
                    "dependency_id": dependency.id,
                    "predecessor_id": dependency.predecessor_task_id,
                    "predecessor_name": predecessor.name if predecessor else None,
                    "successor_id": dependency.successor_task_id,
                    "successor_name": successor.name if successor else None,
                },
            )
            raise BusinessRuleError(
                f"Approval required for dependency removal. Request {request.id} created.",
                code="APPROVAL_REQUIRED",
            )
        self._apply_dependency_remove_decision(dependency_id=dep_id, commit=True)

    def _apply_dependency_remove_decision(self, *, dependency_id: str, commit: bool) -> None:
        # Fresh re-fetch: this may run immediately (ungoverned path) or much
        # later when an approved request is applied, so `dependency.version`
        # here is always the CURRENT version at apply time, not whatever it
        # was when the request was made.
        dependency = self._dependency_repo.get(dependency_id)
        if not dependency:
            raise NotFoundError("Dependency not found.", code="DEPENDENCY_NOT_FOUND")
        predecessor = self._task_repo.get(dependency.predecessor_task_id)
        successor = self._task_repo.get(dependency.successor_task_id)
        project_id = predecessor.project_id if predecessor else (successor.project_id if successor else None)
        try:
            self._dependency_repo.delete(dependency_id, expected_version=dependency.version)
            self._sync_project_schedule(project_id, commit=False)
            record_activity(
                self,
                action="dependency.remove",
                entity_type="task_dependency",
                entity_id=dependency_id,
                module="project_management",
                workspace_id=project_id,
                details={
                    "predecessor_name": predecessor.name if predecessor else None,
                    "successor_name": successor.name if successor else None,
                },
                commit=False,
            )
            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except Exception as exc:
            if commit:
                self._session.rollback()
            raise exc
        if commit and project_id:
            domain_events.tasks_changed.emit(project_id)

    def list_dependencies_for_task(self, task_id: str) -> list[TaskDependency]:
        require_permission(self._user_session, "task.read", operation_label="list task dependencies")
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="list task dependencies",
        )
        return self._dependency_repo.list_by_task(task_id)

    def list_dependencies_for_project(self, project_id: str) -> list[TaskDependency]:
        """One-query project-wide dependency read, backed directly by
        ``DependencyRepository.list_by_project`` (Phase L). Exists because
        the Scheduling desktop API's project-wide dependency read used to
        loop ``list_dependencies_for_task`` once per task -- a confirmed
        ``2N+1`` query pattern for an N-task project, despite this
        single-query repository method already existing one layer down.
        See docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
        §17/Phase L."""
        require_permission(self._user_session, "task.read", operation_label="list project dependencies")
        require_project_permission(
            self._user_session,
            project_id,
            "task.read",
            operation_label="list project dependencies",
        )
        return self._dependency_repo.list_by_project(project_id)

    def update_dependency(
        self,
        dep_id: str,
        *,
        dependency_type: DependencyType | None = None,
        lag_days: int | None = None,
        expected_version: int | None = None,
    ) -> TaskDependency:
        dependency = self._dependency_repo.get(dep_id)
        if not dependency:
            raise NotFoundError("Dependency not found.", code="DEPENDENCY_NOT_FOUND")
        # Phase N10: the client's expected_version reflects what it had
        # loaded when the edit dialog was opened, not just-now -- this is
        # the actual concurrency window an optimistic check needs to
        # cover. Checked before governance/diagnostics so a stale dialog
        # never gets to file an approval request against data it never
        # actually saw.
        if expected_version is not None and dependency.version != expected_version:
            raise ConcurrencyError("Dependency was updated by another user.", code="STALE_WRITE")

        predecessor = self._task_repo.get(dependency.predecessor_task_id)
        successor = self._task_repo.get(dependency.successor_task_id)
        project_id = predecessor.project_id if predecessor else (successor.project_id if successor else None)

        governed = (
            self._approval_service is not None
            and is_governance_required("dependency.update")
            and not is_admin_session(self._user_session)
        )
        if governed:
            require_permission(self._user_session, "approval.request", operation_label="request dependency change")
        else:
            require_permission(self._user_session, "task.manage", operation_label="update dependency")
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "approval.request" if governed else "task.manage",
                operation_label="request dependency change" if governed else "update dependency",
            )

        resolved_type = dependency.dependency_type if dependency_type is None else dependency_type
        resolved_lag = dependency.lag_days if lag_days is None else lag_days

        # Validate the CANDIDATE relationship, excluding this dependency's
        # own existing row from the duplicate check (Phase H4) -- the old
        # code instead blindly whitelisted DEPENDENCY_DUPLICATE for every
        # update, which also silently made the cycle check unreachable
        # (the duplicate check short-circuits before it in
        # get_dependency_diagnostics). Excluding by id keeps both checks
        # live.
        diagnostic = self.get_dependency_diagnostics(
            predecessor_id=dependency.predecessor_task_id,
            successor_id=dependency.successor_task_id,
            dependency_type=resolved_type,
            lag_days=resolved_lag,
            include_impact=False,
            exclude_dependency_id=dep_id,
        )
        if not diagnostic.is_valid:
            _raise_for_invalid_diagnostic(diagnostic)

        if governed:
            request = self._approval_service.request_change(
                request_type="dependency.update",
                entity_type="task_dependency",
                entity_id=dependency.id,
                project_id=project_id,
                payload={
                    "dependency_id": dep_id,
                    "predecessor_name": predecessor.name if predecessor else None,
                    "successor_name": successor.name if successor else None,
                    "dependency_type": resolved_type.value,
                    "lag_days": resolved_lag,
                    # Version AT REQUEST TIME (Phase N10) -- re-checked
                    # against whatever is current when an admin finally
                    # applies this, since approval can land long after
                    # the requester's dialog was open.
                    "expected_version": dependency.version,
                },
            )
            raise BusinessRuleError(
                f"Approval required for dependency change. Request {request.id} created.",
                code="APPROVAL_REQUIRED",
            )

        return self._apply_dependency_update_decision(
            dependency_id=dep_id,
            dependency_type=resolved_type,
            lag_days=resolved_lag,
            commit=True,
        )

    def _apply_dependency_update_decision(
        self,
        *,
        dependency_id: str,
        dependency_type: DependencyType,
        lag_days: int,
        commit: bool,
        expected_version: int | None = None,
    ) -> TaskDependency:
        """Apply an update -- either immediately (ungoverned path) or when
        an approved ``dependency.update`` request is finally applied.
        Always re-fetches and re-validates against the CURRENT row/graph at
        apply time (Phase H1), and is fully atomic: repository update,
        schedule recalculation, and activity recording all happen with
        ``commit=False`` and share exactly one final commit (Phase H2) --
        unlike the old code, which committed the dependency row change
        BEFORE running the schedule recalculation and activity write, so a
        failure in either of those left a committed dependency edit with a
        stale project schedule and no audit record.
        """
        dependency = self._dependency_repo.get(dependency_id)
        if not dependency:
            raise NotFoundError("Dependency not found.", code="DEPENDENCY_NOT_FOUND")
        if expected_version is not None and dependency.version != expected_version:
            raise ConcurrencyError("Dependency was updated by another user.", code="STALE_WRITE")
        predecessor = self._task_repo.get(dependency.predecessor_task_id)
        successor = self._task_repo.get(dependency.successor_task_id)
        project_id = predecessor.project_id if predecessor else (successor.project_id if successor else None)

        diagnostic = self.get_dependency_diagnostics(
            predecessor_id=dependency.predecessor_task_id,
            successor_id=dependency.successor_task_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            include_impact=False,
            exclude_dependency_id=dependency_id,
        )
        if not diagnostic.is_valid:
            _raise_for_invalid_diagnostic(diagnostic)

        candidate = replace(dependency, dependency_type=dependency_type, lag_days=lag_days)
        try:
            self._dependency_repo.update(candidate)
            if project_id:
                self._sync_project_schedule(project_id, commit=False)
            record_activity(
                self,
                action="dependency.update",
                entity_type="task_dependency",
                entity_id=candidate.id,
                module="project_management",
                workspace_id=project_id,
                details={
                    "predecessor_name": predecessor.name if predecessor else None,
                    "successor_name": successor.name if successor else None,
                    "type": candidate.dependency_type.value,
                    "lag_days": candidate.lag_days,
                },
                commit=False,
            )
            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except Exception as exc:
            if commit:
                self._session.rollback()
            raise exc
        if commit and project_id:
            domain_events.tasks_changed.emit(project_id)
        return candidate


__all__ = ["TaskDependencyMixin"]
