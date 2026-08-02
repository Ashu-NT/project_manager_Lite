from __future__ import annotations


def serialize_selector_options(view_models) -> list[dict[str, object]]:
    options: list[dict[str, object]] = []
    for view_model in view_models:
        option: dict[str, object] = {
            "value": view_model.value,
            "label": view_model.label,
        }
        disabled_for_task_ids = tuple(
            getattr(view_model, "disabled_for_task_ids", ()) or ()
        )
        if disabled_for_task_ids:
            option["disabledForTaskIds"] = list(disabled_for_task_ids)
        options.append(option)
    return options


__all__ = ["serialize_selector_options"]
