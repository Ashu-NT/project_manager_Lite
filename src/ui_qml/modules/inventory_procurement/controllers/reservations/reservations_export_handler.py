from __future__ import annotations

from src.ui_qml.modules.project_management.utils.table_exporter import export_to_file


def export_table(ctrl, columns: list, file_path: str) -> dict[str, object]:
    return export_to_file(
        list(ctrl._reservations_table_model._rows),
        list(columns),
        (file_path or "").strip(),
    )
