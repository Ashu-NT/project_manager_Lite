from __future__ import annotations


def option(value: str, label: str) -> dict[str, str]:
    return {"value": value, "label": label}


def active_filter_options() -> list[dict[str, str]]:
    return [
        option("all", "All records"),
        option("active", "Active only"),
        option("inactive", "Inactive only"),
    ]


def hint_level_options() -> list[dict[str, str]]:
    return [
        option("", "No hint level"),
        option("LOW", "Low"),
        option("MEDIUM", "Medium"),
        option("HIGH", "High"),
        option("CRITICAL", "Critical"),
    ]


def build_task_template_type_options(desktop_api) -> list[dict[str, str]]:
    seen: set[str] = set()
    options = [option("all", "All maintenance types")]
    for opt in desktop_api.list_task_template_maintenance_types(active_only=None):
        key = str(opt.value or "").strip().upper()
        if not key or key in seen:
            continue
        seen.add(key)
        options.append(option(opt.value, opt.label))
    for fallback in (
        "PREVENTIVE",
        "INSPECTION",
        "LUBRICATION",
        "CALIBRATION",
        "CONDITION_BASED",
    ):
        if fallback in seen:
            continue
        seen.add(fallback)
        options.append(option(fallback, fallback.replace("_", " ").title()))
    return options
