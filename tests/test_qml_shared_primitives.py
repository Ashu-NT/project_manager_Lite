from pathlib import Path


QML_SHARED_ROOT = Path("src/ui_qml/shared/qml/App")
QML_PLATFORM_ROOT = Path("src/ui_qml/platform/qml/Platform")


def test_qml_shared_theme_primitives_exist() -> None:
    expected_files = [
        QML_SHARED_ROOT / "Theme" / "AppTheme.qml",
        QML_SHARED_ROOT / "Theme" / "qmldir",
        QML_SHARED_ROOT / "Controls" / "PrimaryButton.qml",
        QML_SHARED_ROOT / "Controls" / "qmldir",
        QML_SHARED_ROOT / "Widgets" / "MetricCard.qml",
        QML_SHARED_ROOT / "Widgets" / "qmldir",
        QML_SHARED_ROOT / "Layouts" / "WorkspaceFrame.qml",
        QML_SHARED_ROOT / "Layouts" / "qmldir",
    ]

    assert all(path.exists() for path in expected_files)


def test_qml_modules_declare_stable_namespaces() -> None:
    expected_modules = {
        QML_SHARED_ROOT / "Theme" / "qmldir": "module App.Theme",
        QML_SHARED_ROOT / "Controls" / "qmldir": "module App.Controls",
        QML_SHARED_ROOT / "Widgets" / "qmldir": "module App.Widgets",
        QML_SHARED_ROOT / "Layouts" / "qmldir": "module App.Layouts",
        QML_PLATFORM_ROOT / "Widgets" / "qmldir": "module Platform.Widgets",
    }

    for path, module_name in expected_modules.items():
        assert module_name in path.read_text(encoding="utf-8")


def test_qml_platform_widgets_module_exists() -> None:
    expected_files = [
        QML_PLATFORM_ROOT / "Widgets" / "OverviewSectionCard.qml",
        QML_PLATFORM_ROOT / "Widgets" / "RecordListCard.qml",
        QML_PLATFORM_ROOT / "Widgets" / "WorkspaceStateBanner.qml",
        QML_PLATFORM_ROOT / "Widgets" / "qmldir",
    ]

    assert all(path.exists() for path in expected_files)


def test_qml_shared_theme_matches_legacy_widget_tokens() -> None:
    theme_qml = (QML_SHARED_ROOT / "Theme" / "AppTheme.qml").read_text(encoding="utf-8")

    assert 'readonly property color appBackground: "#F7F9FC"' in theme_qml
    assert 'readonly property color surface: "#FFFFFF"' in theme_qml
    assert 'readonly property color accent: "#0A66A8"' in theme_qml
    assert 'readonly property string fontFamily: "Segoe UI Variable Text"' in theme_qml


def test_qml_workspace_frame_exposes_default_content_slot() -> None:
    frame_qml = (QML_SHARED_ROOT / "Layouts" / "WorkspaceFrame.qml").read_text(
        encoding="utf-8"
    )

    assert "default property alias content: contentSlot.data" in frame_qml
