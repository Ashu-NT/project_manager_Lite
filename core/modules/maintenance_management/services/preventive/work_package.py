from __future__ import annotations

from dataclasses import dataclass

from core.modules.maintenance_management.domain import (
    MaintenancePreventivePlan,
    MaintenancePreventivePlanTask,
    MaintenanceWorkOrder,
)
from core.modules.maintenance_management.interfaces import (
    MaintenanceTaskStepTemplateRepository,
    MaintenanceTaskTemplateRepository,
)
from core.modules.maintenance_management.services.work_order_task import MaintenanceWorkOrderTaskService
from core.modules.maintenance_management.services.work_order_task_step import MaintenanceWorkOrderTaskStepService
from core.platform.common.exceptions import ValidationError


@dataclass(frozen=True)
class MaintenanceGeneratedWorkPackage:
    generated_task_ids: list[str]
    generated_step_ids: list[str]


class MaintenancePreventiveWorkPackageBuilder:
    def __init__(
        self,
        *,
        task_template_repo: MaintenanceTaskTemplateRepository,
        task_step_template_repo: MaintenanceTaskStepTemplateRepository,
        work_order_task_service: MaintenanceWorkOrderTaskService,
        work_order_task_step_service: MaintenanceWorkOrderTaskStepService,
    ) -> None:
        self._task_template_repo = task_template_repo
        self._task_step_template_repo = task_step_template_repo
        self._work_order_task_service = work_order_task_service
        self._work_order_task_step_service = work_order_task_step_service

    def populate_work_order(
        self,
        *,
        plan: MaintenancePreventivePlan,
        plan_tasks: list[MaintenancePreventivePlanTask],
        work_order: MaintenanceWorkOrder,
    ) -> MaintenanceGeneratedWorkPackage:
        generated_task_ids: list[str] = []
        generated_step_ids: list[str] = []
        sorted_plan_tasks = sorted(plan_tasks, key=lambda row: (row.sequence_no, row.created_at or row.updated_at))

        for plan_task in sorted_plan_tasks:
            task_template = self._get_task_template(plan_task.task_template_id, organization_id=plan.organization_id)
            step_templates = self._task_step_template_repo.list_for_organization(
                plan.organization_id,
                task_template_id=task_template.id,
                active_only=True,
            )
            task = self._work_order_task_service.create_task(
                work_order_id=work_order.id,
                task_template_id=task_template.id,
                task_name=task_template.name,
                description=task_template.description,
                assigned_employee_id=plan_task.default_assigned_employee_id,
                assigned_team_id=plan_task.default_assigned_team_id,
                estimated_minutes=plan_task.estimated_minutes_override or task_template.estimated_minutes,
                required_skill=task_template.required_skill,
                sequence_no=plan_task.sequence_no,
                is_mandatory=plan_task.is_mandatory,
                completion_rule="ALL_STEPS_REQUIRED" if step_templates else "NO_STEPS_REQUIRED",
                notes=f"Generated from preventive plan {plan.plan_code}.",
            )
            generated_task_ids.append(task.id)
            for step_template in step_templates:
                step = self._work_order_task_step_service.create_step(
                    work_order_task_id=task.id,
                    source_step_template_id=step_template.id,
                    step_number=step_template.step_number,
                    instruction=step_template.instruction,
                    expected_result=step_template.expected_result,
                    hint_level=step_template.hint_level,
                    hint_text=step_template.hint_text,
                    requires_confirmation=step_template.requires_confirmation,
                    requires_measurement=step_template.requires_measurement,
                    requires_photo=step_template.requires_photo,
                    measurement_unit=step_template.measurement_unit,
                    notes=f"Generated from task template {task_template.task_template_code}.",
                )
                generated_step_ids.append(step.id)

        return MaintenanceGeneratedWorkPackage(
            generated_task_ids=generated_task_ids,
            generated_step_ids=generated_step_ids,
        )

    def _get_task_template(self, task_template_id: str, *, organization_id: str):
        row = self._task_template_repo.get(task_template_id)
        if row is None or row.organization_id != organization_id:
            raise ValidationError(
                "Preventive plan references a task template outside the active organization.",
                code="MAINTENANCE_PREVENTIVE_TASK_TEMPLATE_NOT_FOUND",
            )
        return row


__all__ = ["MaintenanceGeneratedWorkPackage", "MaintenancePreventiveWorkPackageBuilder"]
