from src.core.modules.project_management.api.desktop.projects.import_preview import (
    preview_import,
)


def test_desktop_import_preview_uses_file_parser_without_application_adapter_import(
    tmp_path,
) -> None:
    source = tmp_path / "tasks.csv"
    source.write_text("name,start_date,end_date\nDesign,2026-10-01,2026-10-02\n")
    sessions: dict[str, object] = {}

    result = preview_import(sessions, file_path=str(source), source_format="csv")

    assert result["totalRows"] == 1
    assert result["rows"][0]["name"] == "Design"
    assert result["sessionId"] in sessions
