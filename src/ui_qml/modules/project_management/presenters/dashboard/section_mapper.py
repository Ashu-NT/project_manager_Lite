from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardSectionItemViewModel,
    ProjectDashboardSectionViewModel,
)


def to_sections(sections) -> tuple[ProjectDashboardSectionViewModel, ...]:
    return tuple(
        ProjectDashboardSectionViewModel(
            title=section.title,
            subtitle=section.subtitle,
            empty_state=section.empty_state,
            items=tuple(
                ProjectDashboardSectionItemViewModel(
                    id=item.id,
                    title=item.title,
                    status_label=item.status_label,
                    subtitle=item.subtitle,
                    supporting_text=item.supporting_text,
                    meta_text=item.meta_text,
                    state=dict(item.state),
                )
                for item in section.items
            ),
        )
        for section in sections
    )
