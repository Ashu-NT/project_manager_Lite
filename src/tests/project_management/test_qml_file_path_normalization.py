from __future__ import annotations

from src.ui_qml.modules.project_management.utils import table_exporter
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


def test_table_exporter_formats_permission_denied(monkeypatch):
    def deny_write(*_args, **_kwargs):
        raise PermissionError(13, "Permission denied", "C:/Users/ashuf/Downloads/test.xlsx")

    monkeypatch.setattr(table_exporter, "_write_xlsx", deny_write)

    result = export_to_file(
        [{"name": "Test Project"}],
        [{"key": "name", "label": "Name"}],
        "file:///C:/Users/ashuf/Downloads/test.xlsx",
    )

    assert result["ok"] is False
    assert result["errorCode"] == "permission_denied"
    assert "Close the file if it is open in Excel" in result["error"]
