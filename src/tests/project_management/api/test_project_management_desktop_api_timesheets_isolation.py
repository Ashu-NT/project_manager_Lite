from pathlib import Path


def test_project_management_desktop_api_does_not_import_qml_or_infra() -> None:
    api_root = Path("src/core/modules/project_management/api/desktop")
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in api_root.rglob("*.py")
        if "__pycache__" not in path.parts
    )

    assert "src.ui_qml" not in source_text
    assert "ui_qml" not in source_text
    assert "infrastructure.persistence" not in source_text
