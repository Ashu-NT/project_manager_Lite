from pathlib import Path


QML_SHARED_ROOT = Path("src/ui_qml/shared/qml/App")
QML_SHELL_CONTEXT = Path("src/ui_qml/shell/qml/Shell/Context")
QML_PLATFORM_ROOT = Path("src/ui_qml/platform/qml")
QML_PLATFORM_CONTROLLERS = Path("src/ui_qml/platform/qml/Platform/Controllers")
QML_PLATFORM_DIALOGS = Path("src/ui_qml/platform/qml/Platform/Dialogs")
QML_PLATFORM_WIDGETS = Path("src/ui_qml/platform/qml/Platform/Widgets")
QML_PM_CONTROLLERS = Path(
    "src/ui_qml/modules/project_management/qml/ProjectManagement/Controllers"
)
QML_PM_DIALOGS = Path(
    "src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs"
)
QML_PM_WIDGETS = Path(
    "src/ui_qml/modules/project_management/qml/ProjectManagement/Widgets"
)


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
        QML_SHELL_CONTEXT / "qmldir",
        QML_SHELL_CONTEXT / "plugins.qmltypes",
    ]

    assert all(path.exists() for path in expected_files)


def test_qml_modules_declare_stable_namespaces() -> None:
    expected_modules = {
        QML_SHARED_ROOT / "Theme" / "qmldir": "module App.Theme",
        QML_SHARED_ROOT / "Controls" / "qmldir": "module App.Controls",
        QML_SHARED_ROOT / "Widgets" / "qmldir": "module App.Widgets",
        QML_SHARED_ROOT / "Layouts" / "qmldir": "module App.Layouts",
        QML_SHELL_CONTEXT / "qmldir": "module Shell.Context",
        QML_PLATFORM_CONTROLLERS / "qmldir": "module Platform.Controllers",
        QML_PLATFORM_DIALOGS / "qmldir": "module Platform.Dialogs",
        QML_PLATFORM_WIDGETS / "qmldir": "module Platform.Widgets",
        QML_PM_CONTROLLERS / "qmldir": "module ProjectManagement.Controllers",
        QML_PM_DIALOGS / "qmldir": "module ProjectManagement.Dialogs",
        QML_PM_WIDGETS / "qmldir": "module ProjectManagement.Widgets",
    }

    for path, module_name in expected_modules.items():
        assert module_name in path.read_text(encoding="utf-8")


def test_qml_platform_widgets_module_exists() -> None:
    expected_files = [
        QML_PLATFORM_CONTROLLERS / "qmldir",
        QML_PLATFORM_CONTROLLERS / "typeinfo" / "plugins.qmltypes",
        QML_PLATFORM_CONTROLLERS / "typeinfo" / "common.fragment",
        QML_PLATFORM_CONTROLLERS / "typeinfo" / "admin.fragment",
        QML_PLATFORM_CONTROLLERS / "typeinfo" / "control.fragment",
        QML_PLATFORM_CONTROLLERS / "typeinfo" / "settings.fragment",
        QML_PLATFORM_CONTROLLERS / "typeinfo" / "catalog.fragment",
        QML_PLATFORM_DIALOGS / "qmldir",
        QML_PLATFORM_DIALOGS / "DocumentLinkEditorDialog.qml",
        QML_PLATFORM_DIALOGS / "DocumentStructureEditorDialog.qml",
        QML_PLATFORM_WIDGETS / "OverviewSectionCard.qml",
        QML_PLATFORM_WIDGETS / "RecordListCard.qml",
        QML_PLATFORM_WIDGETS / "DocumentDetailPanel.qml",
        QML_PLATFORM_WIDGETS / "WorkspaceStateBanner.qml",
        QML_PLATFORM_WIDGETS / "qmldir",
    ]

    assert all(path.exists() for path in expected_files)


def test_qml_project_management_modules_exist() -> None:
    expected_files = [
        QML_PM_CONTROLLERS / "qmldir",
        QML_PM_CONTROLLERS / "typeinfo" / "plugins.qmltypes",
        QML_PM_CONTROLLERS / "typeinfo" / "common.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "projects.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "tasks.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "dashboard.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "catalog.fragment",
        QML_PM_DIALOGS / "qmldir",
        QML_PM_DIALOGS / "ProjectEditorDialog.qml",
        QML_PM_DIALOGS / "ProjectStatusDialog.qml",
        QML_PM_DIALOGS / "TaskEditorDialog.qml",
        QML_PM_DIALOGS / "TaskProgressDialog.qml",
        QML_PM_WIDGETS / "qmldir",
        QML_PM_WIDGETS / "DashboardChartCard.qml",
        QML_PM_WIDGETS / "DashboardPanelCard.qml",
        QML_PM_WIDGETS / "DashboardSectionCard.qml",
        QML_PM_WIDGETS / "RecordListCard.qml",
        QML_PM_WIDGETS / "WorkspaceStateBanner.qml",
        QML_PM_WIDGETS / "WorkspacePlaceholderPage.qml",
        QML_PM_WIDGETS / "WorkspaceStatusSection.qml",
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
