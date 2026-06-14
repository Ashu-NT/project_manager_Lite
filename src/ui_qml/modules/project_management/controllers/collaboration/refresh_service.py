from __future__ import annotations

import logging

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_collaboration_collection_view_model,
    serialize_collaboration_context_view_model,
    serialize_collaboration_overview_view_model,
    serialize_collaboration_panel_tab_view_models,
    serialize_workspace_view_model,
)

from .panel_index_service import rebuild_panel_item_index

logger = logging.getLogger(__name__)


def refresh_collaboration_workspace(controller) -> None:
    controller._set_is_loading(True)
    try:
        controller._set_error_message("")
        controller._set_feedback_message("")
        controller._set_workspace(
            serialize_workspace_view_model(
                controller._workspace_presenter.build_view_model()
            )
        )
        ws = controller._collaboration_workspace_presenter.build_workspace_state()
        controller._set_overview(serialize_collaboration_overview_view_model(ws.overview))
        controller._set_notifications(
            serialize_collaboration_collection_view_model(ws.notifications)
        )
        controller._set_inbox(serialize_collaboration_collection_view_model(ws.inbox))
        controller._set_recent_activity(
            serialize_collaboration_collection_view_model(ws.recent_activity)
        )
        controller._set_active_presence(
            serialize_collaboration_collection_view_model(ws.active_presence)
        )
        controller._set_context(serialize_collaboration_context_view_model(ws.context))
        controller._set_panel_tabs(
            serialize_collaboration_panel_tab_view_models(ws.panel_tabs)
        )
        controller._set_mentions(serialize_collaboration_collection_view_model(ws.mentions))
        controller._set_approvals(
            serialize_collaboration_collection_view_model(ws.approvals)
        )
        controller._set_activity_feed(
            serialize_collaboration_collection_view_model(ws.activity_feed)
        )
        controller._set_team_updates(
            serialize_collaboration_collection_view_model(ws.team_updates)
        )
        rebuild_panel_item_index(controller)
        controller._set_empty_state(ws.empty_state)
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Failed to refresh project management collaboration workspace.")
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)


__all__ = ["refresh_collaboration_workspace"]
