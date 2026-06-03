"""Labor mixin — thin reporting delegate.

Business logic lives in financials/costs/labor_cost.py.
"""

from __future__ import annotations

from typing import List

from src.core.modules.project_management.contracts.repositories.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.application.financials.costs.labor_cost import (
    LaborCostEngine,
)
from src.core.modules.project_management.infrastructure.reporting.models.report_models import (
    LaborAssignmentRow,
    LaborPlanActualRow,
    LaborResourceRow,
)


class ReportingLaborMixin:
    _project_repo: ProjectRepository
    _task_repo: TaskRepository
    _assignment_repo: AssignmentRepository
    _resource_repo: ResourceRepository
    _project_resource_repo: ProjectResourceRepository

    def _make_labor_engine(self) -> LaborCostEngine:
        return LaborCostEngine(
            project_repo=self._project_repo,
            task_repo=self._task_repo,
            assignment_repo=self._assignment_repo,
            resource_repo=self._resource_repo,
            project_resource_repo=self._project_resource_repo,
        )

    def get_project_labor_details(self, project_id: str) -> List[LaborResourceRow]:
        self._require_view("view labor details", project_id=project_id)
        return self._make_labor_engine().get_project_labor_details(project_id)

    def get_project_labor_plan_vs_actual(self, project_id: str) -> list[LaborPlanActualRow]:
        self._require_view("view labor plan versus actual", project_id=project_id)
        return self._make_labor_engine().get_project_labor_plan_vs_actual(project_id)
