from __future__ import annotations

from src.ui_qml.modules.project_management.utils.file_paths import local_path_from_qml_file_url
from src.ui_qml.modules.project_management.utils.table_exporter import export_to_file


def test_local_path_from_qml_file_url_normalizes_windows_url():
    assert (
        local_path_from_qml_file_url("file:///C:/Users/ashuf/Downloads/tesr.xlsx")
        == "C:/Users/ashuf/Downloads/tesr.xlsx"
    )


def test_table_exporter_accepts_qml_file_url(tmp_path):
    output_path = tmp_path / "projects.csv"
    output_url = "file:///" + str(output_path).replace("\\", "/")

    result = export_to_file(
        [{"name": "Test Project", "status": "Active"}],
        [{"key": "name", "label": "Name"}, {"key": "status", "label": "Status"}],
        output_url,
    )

    assert result["ok"] is True
    assert output_path.exists()
    assert "Test Project" in output_path.read_text(encoding="utf-8-sig")
