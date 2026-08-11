# src/core/modules/project_management/application/scheduling/baseline_service.py
from datetime import date

from src.core.platform.contract.time_management.calendar.calendar_protocol import CalendarProtocol

from sqlalchemy.orm import Session

from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineStatus,
    BaselineTask,
    BaselineVarianceRecord,
    ProjectBaseline,
)
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.task import TaskRepository
from src.core.modules.project_management.contracts.repositories.planned_cost import (
    ProjectPlannedCostVersionRepository,
)
from src.core.modules.project_management.contracts.repositories.baseline import BaselineRepository
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContext,
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.domain.approval.policy import is_governance_required
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.shared.activity import record_activity
from src.core.platform.application.security.authorization.enforcement.permission_checks import is_admin_session, require_permission
from src.core.modules.project_management.application.scheduling.services.scheduling_engine import SchedulingEngine
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin


class BaselineService(ProjectManagementModuleGuardMixin):
    """Governed baseline lifecycle; no ``bypass_approval`` flag."""

    def __init__(
        self,
        session: Session,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        planned_cost_repo: ProjectPlannedCostVersionRepository,
        baseline_repo: BaselineRepository,
        scheduling: SchedulingEngine,
        calendar: CalendarProtocol,
        user_session=None,
        activity_service=None,
        approval_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
    ):
        self._session: Session = session
        self._projects: ProjectRepository = project_repo
        self._tasks: TaskRepository = task_repo
        self._planned_costs = planned_cost_repo
        self._baselines: BaselineRepository = baseline_repo
        self._sched: SchedulingEngine = scheduling
        self._cal: CalendarProtocol = calendar
        self._user_session = user_session
        self._activity_service = activity_service
        self._approval_service = approval_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service

    def _require_context(self, operation_label: str) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                f"Active organization context is required to {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label=operation_label
        )

    def create_baseline(
        self,
        project_id: str,
        name: str = "Baseline",
        *,
        rate_as_of: date,
    ) -> ProjectBaseline:
        """``rate_as_of`` is the date the resource labor rates used for this
        baseline's planned-cost valuation are resolved as of — required,
        with no internal fallback to "today": if the baseline represents a
        plan effective on a known date, pass that date; otherwise the
        caller (desktop API / composition boundary) supplies its own
        creation-time date explicitly. This service never calls
        ``date.today()`` itself."""
        governed = (
            self._approval_service is not None
            and is_governance_required("baseline.create")
            and not is_admin_session(self._user_session)
        )
        if governed:
            require_permission(
                self._user_session,
                "approval.request",
                operation_label="request baseline creation",
            )
            require_project_permission(
                self._user_session,
                project_id,
                "approval.request",
                operation_label="request baseline creation",
            )
        else:
            require_permission(
                self._user_session,
                "baseline.manage",
                operation_label="create baseline",
            )
            require_project_permission(
                self._user_session,
                project_id,
                "baseline.manage",
                operation_label="create baseline",
            )
        project = self._projects.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        if governed:
            req = self._approval_service.request_change(
                request_type="baseline.create",
                entity_type="project_baseline",
                entity_id=project_id,
                project_id=project_id,
                payload={
                    "project_id": project_id,
                    "project_name": project.name,
                    "name": name,
                },
            )
            raise BusinessRuleError(
                f"Approval required for baseline creation. Request {req.id} created.",
                code="APPROVAL_REQUIRED",
            )
        return self._apply_baseline_creation_decision(
            project_id=project_id, name=name, rate_as_of=rate_as_of, commit=True
        )

    def _apply_baseline_creation_decision(
        self, *, project_id: str, name: str, rate_as_of: date, commit: bool
    ) -> ProjectBaseline:
        project = self._projects.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        # Ensure we have a computed schedule (CPM provides earliest_start/finish)
        schedule = self._sched.recalculate_project_schedule(project_id, commit=False)

        tasks = select_leaf_tasks(self._tasks.list_by_project(project_id))
        if not tasks:
            raise ValidationError("Cannot baseline: project has no tasks.")
        task_name_by_id = {task.id: task.name for task in tasks}

        # -------------------------
        # Baselines consume the latest immutable planned-cost snapshot at the
        # requested valuation date. Rate and allocation resolution belongs to
        # PlannedCostService and is never repeated during baseline creation.
        # -------------------------
        planned_by_task: dict[str, float] = {}
        planned_unassigned = 0.0
        versions = [
            version
            for version in self._planned_costs.list_for_project(project_id)
            if version.as_of <= rate_as_of
        ]
        if versions:
            version = max(versions, key=lambda item: (item.as_of, item.revision))
            if not (
                version.rates_complete
                and version.allocations_complete
                and version.cost_codes_complete
            ):
                raise BusinessRuleError(
                    "Cannot create baseline from an incomplete planned-cost snapshot.",
                    code="BASELINE_PLANNED_COST_INCOMPLETE",
                )
            for line in self._planned_costs.list_lines(version.id):
                planned_by_task[line.task_id] = (
                    planned_by_task.get(line.task_id, 0.0) + float(line.amount)
                )

        baseline = ProjectBaseline.create(project_id, name)

        # -------------------------
        # Build baseline task dates + durations (working days)
        # -------------------------
        task_infos = []
        durations: dict[str, int] = {}

        for t in tasks:
            info = schedule.get(t.id)
            bs = getattr(info, "earliest_start", None) if info else getattr(t, "start_date", None)
            bf = getattr(info, "earliest_finish", None) if info else getattr(t, "end_date", None)

            if bs and bf:
                dur = max(0, int(self._cal.working_days_between(bs, bf)))
            else:
                dur = max(0, int(getattr(t, "duration_days", 0) or 0))

            durations[t.id] = dur
            task_infos.append((t.id, bs, bf))

        total_dur = sum(durations.values())

        # -------------------------
        # Allocate unassigned planned budget across tasks (duration-weighted, else equal)
        # -------------------------
        alloc_unassigned: dict[str, float] = {}
        if planned_unassigned > 0 and tasks:
            if total_dur > 0:
                for tid in durations:
                    w = durations[tid] / total_dur if total_dur else 0.0
                    alloc_unassigned[tid] = planned_unassigned * w
            else:
                per = planned_unassigned / float(len(tasks))
                for tid in durations:
                    alloc_unassigned[tid] = per

        baseline_tasks: list[BaselineTask] = []
        for tid, bs, bf in task_infos:
            dur = durations.get(tid, 0)

            # Canonical snapshot lines are already task-valued. The only
            # allocation retained here is the project budget fallback used
            # when no planned-cost snapshot exists.
            planned_cost = (
                float(planned_by_task.get(tid, 0.0) or 0.0)
                + float(alloc_unassigned.get(tid, 0.0) or 0.0)
            )

            baseline_tasks.append(
                BaselineTask.create(
                    baseline_id=baseline.id,
                    task_id=tid,
                    task_name=task_name_by_id.get(tid),
                    baseline_start=bs,
                    baseline_finish=bf,
                    baseline_duration_days=dur,
                    baseline_planned_cost=planned_cost,
                )
            )

        try:
            self._baselines.add_baseline(baseline)
            self._session.flush()
            self._baselines.add_baseline_tasks(baseline_tasks)
            record_activity(
                self,
                action="baseline.create",
                entity_type="project_baseline",
                entity_id=baseline.id,
                module="project_management",
                workspace_id=project_id,
                details={"name": baseline.name},
                commit=False,
            )
            if commit:
                self._session.commit()
            else:
                self._session.flush()
        except Exception:
            if commit:
                self._session.rollback()
            raise

        return baseline

    def get_latest_baseline(self, project_id: str) -> ProjectBaseline | None:
        require_permission(self._user_session, "project.read", operation_label="view latest baseline")
        require_project_permission(
            self._user_session,
            project_id,
            "project.read",
            operation_label="view latest baseline",
        )
        return self._baselines.get_latest_for_project(project_id)

    def list_baselines(self, project_id: str) -> list[ProjectBaseline]:
        require_permission(self._user_session, "project.read", operation_label="list baselines")
        require_project_permission(
            self._user_session,
            project_id,
            "project.read",
            operation_label="list baselines",
        )
        return self._baselines.list_for_project(project_id)

    def delete_baseline(self, baseline_id: str) -> None:
        require_permission(self._user_session, "baseline.manage", operation_label="delete baseline")
        baseline = self._baselines.get_baseline(baseline_id)
        if not baseline:
            raise NotFoundError("Baseline not found.", code="BASELINE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            baseline.project_id,
            "baseline.manage",
            operation_label="delete baseline",
        )
        try:
            self._baselines.delete_baseline(baseline_id)
            self._session.commit()
            record_activity(
                self,
                action="baseline.delete",
                entity_type="project_baseline",
                entity_id=baseline_id,
                module="project_management",
                workspace_id=baseline.project_id,
                details={"name": baseline.name},
            )
        except Exception:
            self._session.rollback()
            raise

    # ── lifecycle: submit / approve / reject ────────────────────────────────

    def submit_baseline(
        self,
        baseline_id: str,
        submitted_by: str,
        notes: str = "",
    ) -> ProjectBaseline:
        """Transition baseline from DRAFT → SUBMITTED for approval routing."""
        require_permission(
            self._user_session, "baseline.manage", operation_label="submit baseline"
        )
        baseline = self._baselines.get_baseline(baseline_id)
        if not baseline:
            raise NotFoundError("Baseline not found.", code="BASELINE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            baseline.project_id,
            "baseline.manage",
            operation_label="submit baseline",
        )
        baseline.submit(submitted_by=submitted_by, notes=notes)
        try:
            self._baselines.update_baseline(baseline)
            self._session.commit()
            record_activity(
                self,
                action="baseline.submit",
                entity_type="project_baseline",
                entity_id=baseline_id,
                module="project_management",
                workspace_id=baseline.project_id,
                details={"name": baseline.name, "submitted_by": submitted_by},
            )
        except Exception:
            self._session.rollback()
            raise
        return baseline

    def approve_baseline(
        self,
        baseline_id: str,
        approved_by: str,
        notes: str = "",
    ) -> ProjectBaseline:
        """
        Transition baseline from SUBMITTED → APPROVED.

        Supersedes the current approved baseline (if any) and builds variance
        records comparing the new plan against the previous approved plan.
        """
        require_permission(
            self._user_session, "baseline.approve", operation_label="approve baseline"
        )
        baseline = self._baselines.get_baseline(baseline_id)
        if not baseline:
            raise NotFoundError("Baseline not found.", code="BASELINE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            baseline.project_id,
            "baseline.approve",
            operation_label="approve baseline",
        )

        previous_approved = self._baselines.get_approved_baseline(baseline.project_id)

        baseline.approve(approved_by=approved_by, notes=notes)

        variance_records: list[BaselineVarianceRecord] = []
        if previous_approved is not None and previous_approved.id != baseline_id:
            variance_records = self._build_variance_records(
                new_baseline=baseline,
                previous_baseline=previous_approved,
            )
            previous_approved.supersede()

        try:
            if previous_approved is not None and previous_approved.id != baseline_id:
                self._baselines.update_baseline(previous_approved)
            self._baselines.update_baseline(baseline)
            if variance_records:
                self._baselines.add_variance_records(variance_records)
            self._session.commit()
            record_activity(
                self,
                action="baseline.approve",
                entity_type="project_baseline",
                entity_id=baseline_id,
                module="project_management",
                workspace_id=baseline.project_id,
                details={
                    "name": baseline.name,
                    "approved_by": approved_by,
                    "superseded_id": previous_approved.id if previous_approved else None,
                },
            )
        except Exception:
            self._session.rollback()
            raise

        return baseline

    def reject_baseline(
        self,
        baseline_id: str,
        notes: str = "",
    ) -> ProjectBaseline:
        """Transition baseline from SUBMITTED → REJECTED."""
        require_permission(
            self._user_session, "baseline.approve", operation_label="reject baseline"
        )
        baseline = self._baselines.get_baseline(baseline_id)
        if not baseline:
            raise NotFoundError("Baseline not found.", code="BASELINE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            baseline.project_id,
            "baseline.approve",
            operation_label="reject baseline",
        )
        baseline.reject(notes=notes)
        try:
            self._baselines.update_baseline(baseline)
            self._session.commit()
            record_activity(
                self,
                action="baseline.reject",
                entity_type="project_baseline",
                entity_id=baseline_id,
                module="project_management",
                workspace_id=baseline.project_id,
                details={"name": baseline.name},
            )
        except Exception:
            self._session.rollback()
            raise
        return baseline

    def get_approved_baseline(self, project_id: str) -> ProjectBaseline | None:
        """Return the currently approved baseline for the project, or None."""
        require_permission(
            self._user_session, "project.read", operation_label="view approved baseline"
        )
        require_project_permission(
            self._user_session,
            project_id,
            "project.read",
            operation_label="view approved baseline",
        )
        return self._baselines.get_approved_baseline(project_id)

    def list_variance_records(
        self,
        baseline_id: str,
    ) -> list[BaselineVarianceRecord]:
        """Return variance records created when this baseline was approved."""
        require_permission(
            self._user_session, "project.read", operation_label="list baseline variance"
        )
        baseline = self._baselines.get_baseline(baseline_id)
        if not baseline:
            raise NotFoundError("Baseline not found.", code="BASELINE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            baseline.project_id,
            "project.read",
            operation_label="list baseline variance",
        )
        return self._baselines.list_variance_records(baseline_id)

    # ── internal helpers ────────────────────────────────────────────────────

    def _build_variance_records(
        self,
        new_baseline: ProjectBaseline,
        previous_baseline: ProjectBaseline,
    ) -> list[BaselineVarianceRecord]:
        """
        Build per-task variance records comparing new vs previous baseline tasks.
        Only creates records for tasks present in both baselines.
        """
        new_tasks = {bt.task_id: bt for bt in self._baselines.list_tasks(new_baseline.id)}
        prev_tasks = {bt.task_id: bt for bt in self._baselines.list_tasks(previous_baseline.id)}

        records: list[BaselineVarianceRecord] = []
        for task_id, new_bt in new_tasks.items():
            prev_bt = prev_tasks.get(task_id)
            if prev_bt is None:
                continue

            start_var = 0
            if new_bt.baseline_start and prev_bt.baseline_start:
                start_var = (new_bt.baseline_start - prev_bt.baseline_start).days

            finish_var = 0
            if new_bt.baseline_finish and prev_bt.baseline_finish:
                finish_var = (new_bt.baseline_finish - prev_bt.baseline_finish).days

            cost_var = new_bt.baseline_planned_cost - prev_bt.baseline_planned_cost

            if start_var == 0 and finish_var == 0 and cost_var == 0.0:
                continue  # no change — skip to keep variance log clean

            records.append(BaselineVarianceRecord.create(
                project_id=new_baseline.project_id,
                new_baseline_id=new_baseline.id,
                superseded_baseline_id=previous_baseline.id,
                task_id=task_id,
                task_name=new_bt.task_name,
                start_variance_days=start_var,
                finish_variance_days=finish_var,
                cost_variance=cost_var,
            ))

        return records
