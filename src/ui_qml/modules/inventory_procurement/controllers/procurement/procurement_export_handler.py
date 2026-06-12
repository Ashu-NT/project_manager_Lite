from __future__ import annotations


def is_requisitions_view(ctrl) -> bool:
    return getattr(ctrl, "_active_view", "requisitions") != "purchase_orders"


def export_table(ctrl, columns: list, file_path: str) -> dict[str, object]:
    from src.ui_qml.modules.project_management.utils.table_exporter import export_to_file

    model = (
        ctrl._requisitions_table_model
        if is_requisitions_view(ctrl)
        else ctrl._purchase_orders_table_model
    )
    return export_to_file(list(model._rows), list(columns), (file_path or "").strip())
