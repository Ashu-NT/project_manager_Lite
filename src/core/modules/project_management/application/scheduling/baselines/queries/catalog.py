

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.scheduling.dto.responses.baselines import (
    SchedulingBaselineVarianceRowDto,
)
from src.core.modules.project_management.application.scheduling.mappers.baselines import (
    map_baseline_variance,
)
from src.core.modules.project_management.contracts.repositories.scheduling.baseline import (
    BaselineRepository,
)
from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineTask,
    BaselineVarianceRecord,
    ProjectBaseline,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    NotFoundError,
)


class BaselineQueryHandler(ProjectManagementModuleGuardMixin):
    'Scoped read-only baseline catalog and snapshot capability.'

    def __init__(self, *, baseline_repo: BaselineRepository, user_session=None, module_catalog_service=None):
        self._baselines = baseline_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

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


    def list_baseline_tasks(
        self,
        baseline_id: str,
        *,
        expected_project_id: str | None = None,
    ) -> list[BaselineTask]:
        """Return one authorized, tenant-scoped baseline snapshot read."""
        require_permission(
            self._user_session,
            "project.read",
            operation_label="view baseline task snapshots",
        )
        baseline = self._baselines.get_baseline(baseline_id)
        if baseline is None or (
            expected_project_id is not None
            and baseline.project_id != expected_project_id
        ):
            raise NotFoundError("Baseline not found.", code="BASELINE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            baseline.project_id,
            "project.read",
            operation_label="view baseline task snapshots",
        )
        return sorted(
            self._baselines.list_tasks(baseline.id),
            key=lambda item: (item.task_id, item.id),
        )


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
        *,
        expected_project_id: str | None = None,
    ) -> list[BaselineVarianceRecord]:
        """Return variance records created when this baseline was approved."""
        require_permission(
            self._user_session, "project.read", operation_label="list baseline variance"
        )
        baseline = self._baselines.get_baseline(baseline_id)
        if not baseline:
            raise NotFoundError("Baseline not found.", code="BASELINE_NOT_FOUND")
        if expected_project_id is not None and baseline.project_id != expected_project_id:
            raise NotFoundError("Baseline not found.", code="BASELINE_NOT_FOUND")
        require_project_permission(
            self._user_session,
            baseline.project_id,
            "project.read",
            operation_label="list baseline variance",
        )
        return self._baselines.list_variance_records(baseline_id)


    def query_variance_responses(self, baseline_id: str) -> tuple[SchedulingBaselineVarianceRowDto, ...]:
        return tuple(map_baseline_variance(record) for record in self.list_variance_records(baseline_id))

    def get_baseline_task(self, baseline_id: str, task_id: str) -> BaselineTask | None:
        """Return one task's snapshot from a baseline, or None if the
        baseline has no snapshot for that task. Read-only passthrough over
        the repository's existing ``list_tasks`` -- added for Task Detail
        -> Schedule Impact's baseline-finish/variance display; does not
        expand baseline management (creation/approval remain unchanged)."""
        require_permission(
            self._user_session, "project.read", operation_label="view baseline task snapshot"
        )
        baseline = self._baselines.get_baseline(baseline_id)
        if not baseline:
            return None
        require_project_permission(
            self._user_session,
            baseline.project_id,
            "project.read",
            operation_label="view baseline task snapshot",
        )
        for baseline_task in self._baselines.list_tasks(baseline_id):
            if baseline_task.task_id == task_id:
                return baseline_task
        return None


