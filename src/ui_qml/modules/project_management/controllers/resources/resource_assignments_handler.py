from __future__ import annotations


def set_resource_assignments(controller, rows: list[dict[str, object]]) -> None:
    if rows == controller._resource_assignments:
        return
    controller._resource_assignments = rows
    controller._table_models.resource_assignments.set_rows(rows)
    controller.resourceAssignmentsChanged.emit()


def load_resource_assignments(controller) -> None:
    resource_id = controller._selected_resource_id
    if not resource_id:
        set_resource_assignments(controller, [])
        return
    try:
        rows = controller._resources_workspace_presenter.build_resource_assignments(resource_id)
        set_resource_assignments(controller, rows)
    except Exception:
        set_resource_assignments(controller, [])


__all__ = ["load_resource_assignments", "set_resource_assignments"]
