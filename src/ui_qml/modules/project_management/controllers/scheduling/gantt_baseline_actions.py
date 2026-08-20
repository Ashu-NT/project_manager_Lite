from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def clear_gantt_baseline(controller, *, clear_selection: bool) -> None:
    controller._gantt_model.set_baseline_overlay(None)
    controller._gantt_time_axis.set_baseline_overlay(None)
    if clear_selection and controller._gantt_selected_baseline_id:
        controller._gantt_selected_baseline_id = ""
        controller.ganttSelectedBaselineIdChanged.emit()
    _set_loading(controller, False)
    _set_error(controller, "")


def select_gantt_baseline(controller, baseline_id: str) -> None:
    normalized = str(baseline_id or "").strip()
    if (
        normalized == controller._gantt_selected_baseline_id
        and not controller._gantt_baseline_error
    ):
        return
    _load_gantt_baseline(controller, normalized)
    _persist_gantt_baseline_preference(controller)


def retry_gantt_baseline(controller) -> None:
    if controller._gantt_selected_baseline_id:
        _load_gantt_baseline(controller, controller._gantt_selected_baseline_id)


def restore_gantt_baseline_after_workspace(controller) -> None:
    project_id = str(controller._selected_project_id or "").strip()
    if not project_id:
        return
    selected_id = str(controller._gantt_selected_baseline_id or "").strip()
    if not selected_id:
        selected_id = controller._app_settings.load_gantt_project_baseline(
            project_id,
            organization_id=controller._active_organization_id_for_settings(),
        )
    option_ids = {
        str(option.get("value") or "").strip()
        for option in controller._baseline_options
    }
    if selected_id not in option_ids:
        selected_id = ""
        controller._app_settings.save_gantt_project_baseline(
            project_id,
            "",
            organization_id=controller._active_organization_id_for_settings(),
        )
    if selected_id != controller._gantt_selected_baseline_id:
        controller._gantt_selected_baseline_id = selected_id
        controller.ganttSelectedBaselineIdChanged.emit()
    if selected_id:
        _load_gantt_baseline(controller, selected_id)


def _load_gantt_baseline(controller, baseline_id: str) -> None:
    # Invalidate first so selector state can never point at stale geometry.
    controller._gantt_model.set_baseline_overlay(None)
    controller._gantt_time_axis.set_baseline_overlay(None)
    if baseline_id != controller._gantt_selected_baseline_id:
        controller._gantt_selected_baseline_id = baseline_id
        controller.ganttSelectedBaselineIdChanged.emit()
    _set_error(controller, "")
    if not baseline_id:
        _set_loading(controller, False)
        return
    project_id = str(controller._selected_project_id or "").strip()
    option_ids = {
        str(option.get("value") or "").strip()
        for option in controller._baseline_options
    }
    if not project_id or baseline_id not in option_ids:
        controller._gantt_selected_baseline_id = ""
        controller.ganttSelectedBaselineIdChanged.emit()
        _set_loading(controller, False)
        _set_error(controller, "The selected baseline is no longer available for this project.")
        return
    _set_loading(controller, True)
    try:
        overlay = controller._scheduling_workspace_presenter.build_gantt_baseline_overlay(
            project_id,
            baseline_id,
        )
        projection = controller._gantt_model.projection
        if projection is None or (
            overlay.tenant_id != projection.tenant_id
            or overlay.organization_id != projection.organization_id
            or overlay.project_id != projection.project_id
            or overlay.baseline_id != baseline_id
        ):
            raise ValueError("Baseline overlay scope does not match the active Gantt project.")
        controller._gantt_time_axis.set_baseline_overlay(overlay)
        controller._gantt_model.set_baseline_overlay(overlay)
    except Exception:
        logger.exception(
            "PM Gantt baseline overlay load failed project=%s baseline=%s",
            project_id,
            baseline_id,
        )
        controller._gantt_model.set_baseline_overlay(None)
        controller._gantt_time_axis.set_baseline_overlay(None)
        _set_error(
            controller,
            "Baseline comparison could not be loaded. Retry or choose None.",
        )
    finally:
        _set_loading(controller, False)


def _set_loading(controller, value: bool) -> None:
    normalized = bool(value)
    if normalized == controller._gantt_baseline_loading:
        return
    controller._gantt_baseline_loading = normalized
    controller.ganttBaselineLoadingChanged.emit()


def _set_error(controller, value: str) -> None:
    normalized = str(value or "")
    if normalized == controller._gantt_baseline_error:
        return
    controller._gantt_baseline_error = normalized
    controller.ganttBaselineErrorChanged.emit()


def _persist_gantt_baseline_preference(controller) -> None:
    project_id = str(controller._selected_project_id or "").strip()
    if not project_id:
        return
    controller._app_settings.save_gantt_project_baseline(
        project_id,
        controller._gantt_selected_baseline_id,
        organization_id=controller._active_organization_id_for_settings(),
    )


__all__ = [
    "clear_gantt_baseline",
    "restore_gantt_baseline_after_workspace",
    "retry_gantt_baseline",
    "select_gantt_baseline",
]
