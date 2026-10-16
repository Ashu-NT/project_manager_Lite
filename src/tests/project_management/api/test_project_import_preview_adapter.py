from src.core.modules.project_management.api.desktop.projects.import_preview import (
    execute_import,
    preview_import,
)
from src.ui_qml.modules.project_management.presenters.projects.import_preview_mapper import (
    build_import_preview,
    build_import_staging_result,
)


def test_desktop_import_preview_uses_file_parser_without_application_adapter_import(
    tmp_path,
) -> None:
    source = tmp_path / "tasks.csv"
    source.write_text("name,start_date,end_date\nDesign,2026-10-01,2026-10-02\n")
    sessions: dict[str, object] = {}

    result = preview_import(sessions, file_path=str(source), source_format="csv")

    assert result.total_rows == 1
    assert result.rows[0].mapped_data["name"] == "Design"
    assert sessions[result.session_id] is result

    view = build_import_preview(result)
    assert view["totalRows"] == 1
    assert view["rows"][0]["name"] == "Design"
    assert view["sessionId"] == result.session_id

    staging = execute_import(sessions, session_id=result.session_id)
    assert staging.staged_count == 1
    assert not sessions
    assert build_import_staging_result(staging) == {
        "ok": True,
        "importedCount": 1,
        "message": "Import accepted. 1 task(s) staged for this project.",
    }
