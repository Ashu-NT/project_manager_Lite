"""Constraint violation serializer."""

from src.core.modules.project_management.api.desktop.scheduling.models.constraints import SchedulingConstraintViolationDto


def serialize_constraint_violation(v, *, hard_pairs: set) -> SchedulingConstraintViolationDto:
    is_hard = (v.task_id, v.constraint_type) in hard_pairs
    return SchedulingConstraintViolationDto(
        task_id=v.task_id,
        task_name=v.task_name,
        constraint_type=str(getattr(v.constraint_type, "value", v.constraint_type)),
        constraint_type_label=str(getattr(v.constraint_type, "value", v.constraint_type)).replace("_", " ").title(),
        constraint_date=v.constraint_date,
        constraint_date_label=v.constraint_date.isoformat() if v.constraint_date else "-",
        computed_date=v.computed_date,
        computed_date_label=v.computed_date.isoformat() if v.computed_date else "-",
        overrun_working_days=int(v.overrun_working_days or 0),
        message=v.message,
        severity="hard" if is_hard else "soft",
        severity_label="Hard Constraint" if is_hard else "Soft Constraint",
    )


__all__ = ["serialize_constraint_violation"]
