from __future__ import annotations

from dataclasses import replace
from datetime import date

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.currency_policy import (
    resolve_pm_currency,
)
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.domain.financials.cost import CostItem
from src.core.platform.common.code_generation import CodeGenerator
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.shared.events.domain_events import domain_events


class LegacyCostTestSupport:
    """Test-only legacy row factory for pre-C.7 reporting coverage.

    TRANSITION(PF-C6-LEGACY-TEST-SEED): delete this wrapper and its fixture wiring
    when C.7 migrates legacy reporting fixtures to canonical financial sources.
    This class must never be imported by production composition or application code.
    """

    def __init__(self, *, query_service, task_repo, tenant_context_service, session: Session):
        self._query_service = query_service
        self._cost_repo = query_service._cost_repo
        self._project_repo = query_service._project_repo
        self._task_repo = task_repo
        self._tenant_context_service = tenant_context_service
        self._session = session

    def __getattr__(self, name: str):
        return getattr(self._query_service, name)

    def add_cost_item(
        self,
        project_id: str,
        description: str,
        planned_amount: float,
        task_id: str | None = None,
        cost_type: CostType = CostType.OVERHEAD,
        committed_amount: float = 0.0,
        actual_amount: float = 0.0,
        incurred_date: date | None = None,
        currency_code: str | None = None,
        code: str = "",
    ) -> CostItem:
        project = self._project_repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        self._require_task(project_id=project_id, task_id=task_id)
        resolved_code = self._resolve_code(
            project_id=project_id,
            description=description,
            code=code,
        )
        item = CostItem.create(
            project_id=project_id,
            task_id=task_id,
            code=resolved_code,
            description=description,
            planned_amount=planned_amount,
            cost_type=cost_type,
            committed_amount=committed_amount,
            actual_amount=actual_amount,
            incurred_date=incurred_date,
            currency_code=resolve_pm_currency(
                tenant_context_service=self._tenant_context_service,
                operation_label="seed legacy cost test row",
                explicit=currency_code,
                project_default=getattr(project, "currency", None),
            ),
        )
        self._cost_repo.add(item)
        self._session.commit()
        domain_events.costs_changed.emit(project_id)
        return item

    def update_cost_item(
        self,
        cost_id: str,
        *,
        code: str | None = None,
        description: str | None = None,
        planned_amount: float | None = None,
        committed_amount: float | None = None,
        actual_amount: float | None = None,
        cost_type: CostType | None = None,
        incurred_date: date | None = None,
        currency_code: str | None = None,
    ) -> CostItem:
        item = self._cost_repo.get(cost_id)
        if item is None:
            raise NotFoundError("Cost item not found.", code="COST_NOT_FOUND")
        project = self._project_repo.get(item.project_id)
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        candidate = replace(
            item,
            code=(
                item.code
                if code is None
                else self._resolve_code(
                    project_id=item.project_id,
                    description=description or item.description,
                    code=code,
                    exclude_id=item.id,
                )
            ),
            description=item.description if description is None else description,
            planned_amount=item.planned_amount if planned_amount is None else planned_amount,
            committed_amount=(
                item.committed_amount if committed_amount is None else committed_amount
            ),
            actual_amount=item.actual_amount if actual_amount is None else actual_amount,
            cost_type=item.cost_type if cost_type is None else cost_type,
            incurred_date=item.incurred_date if incurred_date is None else incurred_date,
            currency_code=(
                item.currency_code
                if currency_code is None
                else resolve_pm_currency(
                    tenant_context_service=self._tenant_context_service,
                    operation_label="update legacy cost test row",
                    explicit=currency_code,
                    project_default=getattr(project, "currency", None),
                )
            ),
        )
        self._cost_repo.update(candidate)
        self._session.commit()
        domain_events.costs_changed.emit(candidate.project_id)
        return candidate

    def delete_cost_item(self, cost_id: str) -> None:
        item = self._cost_repo.get(cost_id)
        if item is None:
            raise NotFoundError("Cost item not found.", code="COST_NOT_FOUND")
        self._cost_repo.delete(cost_id)
        self._session.commit()
        domain_events.costs_changed.emit(item.project_id)

    def _require_task(self, *, project_id: str, task_id: str | None) -> None:
        if task_id is None:
            return
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        if task.project_id != project_id:
            raise ValidationError(
                "Task must belong to the selected project.",
                code="TASK_PROJECT_MISMATCH",
            )

    def _resolve_code(
        self,
        *,
        project_id: str,
        description: str,
        code: str,
        exclude_id: str | None = None,
    ) -> str:
        existing = {
            str(item.code or "").upper()
            for item in self._cost_repo.list_by_project(project_id)
            if item.id != exclude_id
        }
        manual = str(code or "").strip().upper()
        if manual:
            if manual in existing:
                raise ValidationError(
                    f"Cost code '{manual}' already exists in this project.",
                    code="CODE_DUPLICATE",
                )
            return manual
        return CodeGenerator().generate(
            "cost",
            exists=lambda candidate: candidate.upper() in existing,
            name=str(description or "").strip() or None,
            use_year=not bool(str(description or "").strip()),
        )


def install_legacy_cost_test_support(graph: dict[str, object], session: Session) -> None:
    graph["cost_service"] = LegacyCostTestSupport(
        query_service=graph["cost_service"],
        task_repo=graph["task_service"]._task_repo,
        tenant_context_service=graph["tenant_context_service"],
        session=session,
    )


__all__ = ["LegacyCostTestSupport", "install_legacy_cost_test_support"]
