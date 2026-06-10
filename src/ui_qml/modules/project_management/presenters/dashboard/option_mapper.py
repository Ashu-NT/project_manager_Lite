from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardSelectorOptionViewModel,
)


def to_selector_options(options) -> tuple[ProjectDashboardSelectorOptionViewModel, ...]:
    return tuple(
        ProjectDashboardSelectorOptionViewModel(value=option.value, label=option.label)
        for option in options
    )
