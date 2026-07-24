from __future__ import annotations

from dataclasses import replace
from datetime import date

from sqlalchemy.exc import IntegrityError

from src.core.shared.events.domain_events import domain_events
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, ValidationError
from src.core.modules.project_management.domain.financials.cost import CostItem
from src.core.modules.project_management.domain.enums import CostType
from src.core.shared.activity import record_activity


class CostLifecycleMixin:
    @staticmethod
    def _is_cost_code_integrity_error(exc: IntegrityError) -> bool:
        message = " ".join(
            part
            for part in [
                str(getattr(exc, "orig", "") or ""),
                str(getattr(exc, "statement", "") or ""),
                str(exc),
            ]
            if part
        ).lower()
        return "ux_costs_project_code" in message or "cost_items.cost_code" in message

    @staticmethod
    def _raise_cost_code_duplicate(code: str, exc: IntegrityError) -> None:
        raise ValidationError(
            f"Cost code '{code}' already exists in this project.",
            code="CODE_DUPLICATE",
        ) from exc

    def _resolve_cost_code(
        self, code: str, project_id: str, description: str, *, exclude_id: str | None = None
    ) -> str:
        from src.core.platform.common.code_generation import (
            CodeGenerator,
            assert_code_unique,
            normalize_manual_code,
        )

        existing = {
            str(getattr(item, "code", "") or "").upper()
            for item in self._cost_repo.list_by_project(project_id)
            if exclude_id is None or item.id != exclude_id
        }
        manual = normalize_manual_code(code)
        if manual:
            assert_code_unique(
                manual,
                exists=lambda candidate: candidate.upper() in existing,
                label="Cost code",
            )
            return manual
        return CodeGenerator().generate(
            "cost",
            exists=lambda candidate: candidate.upper() in existing,
            name=(description or "").strip() or None,
            use_year=not bool((description or "").strip()),
        )

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
        bypass_approval: bool = False,
        code: str = "",
    ) -> CostItem:
        governed = self._is_governed(operation_code="cost.add", bypass_approval=bypass_approval)
        self._require_operation_permission(
            project_id=project_id,
            governed=governed,
            manage_permission="cost.manage",
            manage_label="add cost item",
            request_label="request cost item creation",
        )
        project = self._require_project(project_id)
        task = self._resolve_task_for_project(project_id=project_id, task_id=task_id)
        draft = CostItem(
            id="cost-validation-probe",
            project_id=project_id,
            task_id=task_id,
            description=description,
            planned_amount=planned_amount,
            cost_type=cost_type,
            committed_amount=committed_amount,
            actual_amount=actual_amount,
            incurred_date=incurred_date,
            currency_code=self._normalize_currency(currency_code),
        )

        if governed:
            req = self._approval_service.request_change(
                request_type="cost.add",
                entity_type="cost_item",
                entity_id=task_id or project_id,
                project_id=project_id,
                payload={
                    "project_id": project_id,
                    "task_id": task_id,
                    "task_name": task.name if task is not None else None,
                    "project_name": project.name,
                    "description": draft.description,
                    "planned_amount": draft.planned_amount,
                    "committed_amount": draft.committed_amount,
                    "actual_amount": draft.actual_amount,
                    "cost_type": draft.cost_type.value,
                    "incurred_date": str(draft.incurred_date) if draft.incurred_date else None,
                    "currency_code": draft.currency_code,
                },
            )
            raise BusinessRuleError(
                f"Approval required for cost creation. Request {req.id} created.",
                code="APPROVAL_REQUIRED",
            )

        cost_item = CostItem.create(
            project_id=project_id,
            task_id=task_id,
            code=self._resolve_cost_code(code, project_id, draft.description),
            description=draft.description,
            planned_amount=draft.planned_amount,
            committed_amount=draft.committed_amount,
            actual_amount=draft.actual_amount,
            cost_type=draft.cost_type,
            incurred_date=draft.incurred_date,
            currency_code=draft.currency_code,
        )

        try:
            self._cost_repo.add(cost_item)
            self._session.commit()
            record_activity(
                self,
                action="cost.add",
                entity_type="cost_item",
                entity_id=cost_item.id,
                module="project_management",
                workspace_id=project_id,
                details={
                    "description": cost_item.description,
                    "planned_amount": cost_item.planned_amount,
                    "actual_amount": cost_item.actual_amount,
                },
            )
        except IntegrityError as exc:
            self._session.rollback()
            if self._is_cost_code_integrity_error(exc):
                self._raise_cost_code_duplicate(cost_item.code, exc)
            raise
        except Exception:
            self._session.rollback()
            raise

        domain_events.costs_changed.emit(project_id)
        return cost_item

    def update_cost_item(
        self,
        cost_id: str,
        description: str | None = None,
        planned_amount: float | None = None,
        committed_amount: float | None = None,
        actual_amount: float | None = None,
        cost_type: CostType | None = None,
        incurred_date: date | None = None,
        currency_code: str | None = None,
        expected_version: int | None = None,
        bypass_approval: bool = False,
        code: str | None = None,
    ) -> CostItem:
        governed = self._is_governed(operation_code="cost.update", bypass_approval=bypass_approval)
        item = self._require_cost_item(cost_id)
        self._require_operation_permission(
            project_id=item.project_id,
            governed=governed,
            manage_permission="cost.manage",
            manage_label="update cost item",
            request_label="request cost item update",
        )
        if expected_version is not None and item.version != expected_version:
            raise ConcurrencyError(
                "Cost item changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        item_task = self._task_repo.get(item.task_id) if item.task_id else None
        resolved_description = item.description if description is None else description
        resolved_planned_amount = item.planned_amount if planned_amount is None else planned_amount
        resolved_committed_amount = (
            item.committed_amount if committed_amount is None else committed_amount
        )
        resolved_actual_amount = item.actual_amount if actual_amount is None else actual_amount
        resolved_cost_type = item.cost_type if cost_type is None else cost_type
        resolved_incurred_date = item.incurred_date if incurred_date is None else incurred_date
        resolved_currency_code = (
            item.currency_code
            if currency_code is None
            else self._normalize_currency(currency_code)
        )
        if governed:
            draft = replace(
                item,
                description=resolved_description,
                planned_amount=resolved_planned_amount,
                committed_amount=resolved_committed_amount,
                actual_amount=resolved_actual_amount,
                cost_type=resolved_cost_type,
                incurred_date=resolved_incurred_date,
                currency_code=resolved_currency_code,
            )
            req = self._approval_service.request_change(
                request_type="cost.update",
                entity_type="cost_item",
                entity_id=item.id,
                project_id=item.project_id,
                payload={
                    "cost_id": cost_id,
                    "description": draft.description,
                    "task_name": item_task.name if item_task is not None else None,
                    "planned_amount": draft.planned_amount,
                    "committed_amount": draft.committed_amount,
                    "actual_amount": draft.actual_amount,
                    "cost_type": draft.cost_type.value,
                    "incurred_date": str(draft.incurred_date) if draft.incurred_date else None,
                    "currency_code": draft.currency_code,
                    "expected_version": expected_version,
                },
            )
            raise BusinessRuleError(
                f"Approval required for cost update. Request {req.id} created.",
                code="APPROVAL_REQUIRED",
            )

        candidate = replace(
            item,
            description=resolved_description,
            planned_amount=resolved_planned_amount,
            committed_amount=resolved_committed_amount,
            actual_amount=resolved_actual_amount,
            cost_type=resolved_cost_type,
            incurred_date=resolved_incurred_date,
            currency_code=resolved_currency_code,
        )
        if code is not None and code.strip():
            candidate = replace(
                candidate,
                code=self._resolve_cost_code(
                    code,
                    item.project_id,
                    candidate.description,
                    exclude_id=item.id,
                ),
            )

        try:
            self._cost_repo.update(candidate)
            self._session.commit()
            record_activity(
                self,
                action="cost.update",
                entity_type="cost_item",
                entity_id=candidate.id,
                module="project_management",
                workspace_id=candidate.project_id,
                details={
                    "description": candidate.description,
                    "planned_amount": candidate.planned_amount,
                    "actual_amount": candidate.actual_amount,
                },
            )
        except IntegrityError as exc:
            self._session.rollback()
            if self._is_cost_code_integrity_error(exc):
                self._raise_cost_code_duplicate(candidate.code, exc)
            raise
        except Exception:
            self._session.rollback()
            raise

        domain_events.costs_changed.emit(candidate.project_id)
        return candidate

    def delete_cost_item(self, cost_id: str, bypass_approval: bool = False) -> None:
        governed = self._is_governed(operation_code="cost.delete", bypass_approval=bypass_approval)
        item = self._require_cost_item(cost_id)
        self._require_operation_permission(
            project_id=item.project_id,
            governed=governed,
            manage_permission="cost.manage",
            manage_label="delete cost item",
            request_label="request cost item deletion",
        )
        item_task = self._task_repo.get(item.task_id) if item.task_id else None
        if governed:
            req = self._approval_service.request_change(
                request_type="cost.delete",
                entity_type="cost_item",
                entity_id=item.id,
                project_id=item.project_id,
                payload={
                    "cost_id": cost_id,
                    "description": item.description,
                    "task_name": item_task.name if item_task is not None else None,
                },
            )
            raise BusinessRuleError(
                f"Approval required for cost deletion. Request {req.id} created.",
                code="APPROVAL_REQUIRED",
            )
        try:
            self._cost_repo.delete(cost_id)
            self._session.commit()
            record_activity(
                self,
                action="cost.delete",
                entity_type="cost_item",
                entity_id=item.id,
                module="project_management",
                workspace_id=item.project_id,
                details={"description": item.description},
            )
        except Exception:
            self._session.rollback()
            raise

        domain_events.costs_changed.emit(item.project_id)
