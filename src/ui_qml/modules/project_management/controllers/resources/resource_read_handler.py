from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_resource_detail_view_model,
    serialize_resource_inspector_view_model,
)

from .resource_state import default_resource_inspector, default_selected_resource


def clear_resource_read_state(controller) -> None:
    controller._inspector_request_id += 1
    controller._detail_request_id += 1
    controller._set_resource_inspector(default_resource_inspector())
    controller._set_selected_resource(default_selected_resource())
    controller._set_inspector_error("")
    controller._set_detail_error("")
    controller._set_inspector_loading(False)
    controller._set_detail_loading(False)


def load_resource_inspector(controller, resource_id: str) -> None:
    normalized_id = str(resource_id or "").strip()
    controller._inspector_request_id += 1
    request_id = controller._inspector_request_id
    if not normalized_id:
        controller._set_resource_inspector(default_resource_inspector())
        controller._set_inspector_error("")
        controller._set_inspector_loading(False)
        return
    controller._set_inspector_loading(True)
    controller._set_inspector_error("")
    try:
        view_model = controller._resources_workspace_presenter.build_resource_inspector(
            normalized_id
        )
        if (
            request_id == controller._inspector_request_id
            and normalized_id == controller._selected_resource_id
        ):
            controller._set_resource_inspector(
                serialize_resource_inspector_view_model(view_model)
            )
    except Exception as exc:
        if (
            request_id == controller._inspector_request_id
            and normalized_id == controller._selected_resource_id
        ):
            controller._set_resource_inspector(default_resource_inspector())
            controller._set_inspector_error(str(exc))
    finally:
        if request_id == controller._inspector_request_id:
            controller._set_inspector_loading(False)


def load_resource_detail(controller, resource_id: str) -> bool:
    normalized_id = str(resource_id or "").strip()
    controller._detail_request_id += 1
    request_id = controller._detail_request_id
    if not normalized_id:
        controller._set_selected_resource(default_selected_resource())
        controller._set_detail_error("")
        controller._set_detail_loading(False)
        return False
    controller._set_detail_loading(True)
    controller._set_detail_error("")
    try:
        view_model = controller._resources_workspace_presenter.build_resource_detail(
            normalized_id
        )
        if request_id != controller._detail_request_id:
            return False
        controller._set_selected_resource(serialize_resource_detail_view_model(view_model))
        return True
    except Exception as exc:
        if request_id == controller._detail_request_id:
            controller._set_selected_resource(default_selected_resource())
            controller._set_detail_error(str(exc))
        return False
    finally:
        if request_id == controller._detail_request_id:
            controller._set_detail_loading(False)


def refresh_selected_resource_reads(controller) -> None:
    resource_id = controller._selected_resource_id
    if not resource_id:
        clear_resource_read_state(controller)
        return
    load_resource_inspector(controller, resource_id)
    selected_detail_id = str(controller._selected_resource.get("id", "") or "")
    if selected_detail_id == resource_id:
        load_resource_detail(controller, resource_id)


__all__ = [
    "clear_resource_read_state",
    "load_resource_detail",
    "load_resource_inspector",
    "refresh_selected_resource_reads",
]
