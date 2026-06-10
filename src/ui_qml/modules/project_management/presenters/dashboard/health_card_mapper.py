from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardHealthCardViewModel,
    ProjectDashboardOperationalTabViewModel,
)


def to_health_cards(
    cards,
) -> tuple[ProjectDashboardHealthCardViewModel, ...]:
    return tuple(
        ProjectDashboardHealthCardViewModel(
            id=card.id,
            title=card.title,
            status_label=card.status_label,
            metric_value=card.metric_value,
            metric_label=card.metric_label,
            supporting_text=card.supporting_text,
            meta_text=card.meta_text,
            tone=card.tone,
            route_id=card.route_id,
        )
        for card in cards
    )


def to_operational_tabs(
    tabs,
) -> tuple[ProjectDashboardOperationalTabViewModel, ...]:
    return tuple(
        ProjectDashboardOperationalTabViewModel(
            id=tab.id,
            label=tab.label,
            count=tab.count,
            route_id=tab.route_id,
        )
        for tab in tabs
    )
