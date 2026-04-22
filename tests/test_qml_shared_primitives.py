from pathlib import Path


QML_SHARED_ROOT = Path("src/ui_qml/shared/qml")


def test_qml_shared_theme_primitives_exist() -> None:
    expected_files = [
        QML_SHARED_ROOT / "theme" / "AppTheme.qml",
        QML_SHARED_ROOT / "theme" / "qmldir",
        QML_SHARED_ROOT / "controls" / "PrimaryButton.qml",
        QML_SHARED_ROOT / "widgets" / "MetricCard.qml",
        QML_SHARED_ROOT / "layouts" / "WorkspaceFrame.qml",
    ]

    assert all(path.exists() for path in expected_files)


def test_qml_shared_theme_matches_legacy_widget_tokens() -> None:
    theme_qml = (QML_SHARED_ROOT / "theme" / "AppTheme.qml").read_text(encoding="utf-8")

    assert 'readonly property color appBackground: "#F7F9FC"' in theme_qml
    assert 'readonly property color surface: "#FFFFFF"' in theme_qml
    assert 'readonly property color accent: "#0A66A8"' in theme_qml
    assert 'readonly property string fontFamily: "Segoe UI Variable Text"' in theme_qml


def test_qml_workspace_frame_exposes_default_content_slot() -> None:
    frame_qml = (QML_SHARED_ROOT / "layouts" / "WorkspaceFrame.qml").read_text(
        encoding="utf-8"
    )

    assert "default property alias content: contentSlot.data" in frame_qml
