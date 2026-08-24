from pathlib import Path
import re

from PySide6.QtCore import QSettings


QMLLS_CONFIG = Path(".qmlls.ini")
UI_QML_ROOT = Path("src/ui_qml")
QML_SHARED_ROOT = Path("src/ui_qml/shared/qml/App")
QML_SHARED_MODELS = Path("src/ui_qml/shared/qml/App/Models")
QML_SHELL_CONTEXT = Path("src/ui_qml/shell/qml/Shell/Context")
QML_SHELL_CONTROLLERS = Path("src/ui_qml/shell/qml/Shell/Controllers")
QML_PLATFORM_ROOT = Path("src/ui_qml/platform/qml")
QML_PLATFORM_CONTROLLERS = Path("src/ui_qml/platform/qml/Platform/Controllers")
QML_PLATFORM_DIALOGS = Path("src/ui_qml/platform/qml/Platform/Dialogs")
QML_PLATFORM_WIDGETS = Path("src/ui_qml/platform/qml/Platform/Widgets")
QML_PM_CONTROLLERS = Path(
    "src/ui_qml/modules/project_management/qml/ProjectManagement/Controllers"
)
QML_PM_WIDGETS = Path(
    "src/ui_qml/modules/project_management/qml/ProjectManagement/Widgets"
)
QML_INV_CONTROLLERS = Path(
    "src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Controllers"
)
QML_INV_DIALOGS = Path(
    "src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Dialogs"
)
QML_INV_WIDGETS = Path(
    "src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Widgets"
)
def test_qml_shared_theme_primitives_exist() -> None:
    expected_files = [
        QML_SHARED_ROOT / "Theme" / "AppTheme.qml",
        QML_SHARED_ROOT / "Theme" / "qmldir",
        QML_SHARED_MODELS / "qmldir",
        QML_SHARED_MODELS / "plugins.qmltypes",
        QML_SHARED_ROOT / "Controls" / "CheckBox.qml",
        QML_SHARED_ROOT / "Controls" / "ComboBox.qml",
        QML_SHARED_ROOT / "Controls" / "DateField.qml",
        QML_SHARED_ROOT / "Controls" / "Label.qml",
        QML_SHARED_ROOT / "Controls" / "PrimaryButton.qml",
        QML_SHARED_ROOT / "Controls" / "RadioButton.qml",
        QML_SHARED_ROOT / "Controls" / "SearchField.qml",
        QML_SHARED_ROOT / "Controls" / "qmldir",
        QML_SHARED_ROOT / "Widgets" / "MetricCard.qml",
        QML_SHARED_ROOT / "Controls" / "SecondaryButton.qml",
        QML_SHARED_ROOT / "Controls" / "TextArea.qml",
        QML_SHARED_ROOT / "Controls" / "TextField.qml",
        QML_SHARED_ROOT / "Controls" / "ToggleSwitch.qml",
        QML_SHARED_ROOT / "Widgets" / "qmldir",
        QML_SHARED_ROOT / "Layouts" / "WorkspaceFrame.qml",
        QML_SHARED_ROOT / "Layouts" / "qmldir",
        QML_SHELL_CONTEXT / "qmldir",
        QML_SHELL_CONTEXT / "plugins.qmltypes",
        QML_SHELL_CONTROLLERS / "qmldir",
        QML_SHELL_CONTROLLERS / "plugins.qmltypes",
    ]

    assert all(path.exists() for path in expected_files)


def test_qml_modules_declare_stable_namespaces() -> None:
    expected_modules = {
        QML_SHARED_ROOT / "Theme" / "qmldir": "module App.Theme",
        QML_SHARED_MODELS / "qmldir": "module App.Models",
        QML_SHARED_ROOT / "Controls" / "qmldir": "module App.Controls",
        QML_SHARED_ROOT / "Widgets" / "qmldir": "module App.Widgets",
        QML_SHARED_ROOT / "Layouts" / "qmldir": "module App.Layouts",
        QML_SHELL_CONTEXT / "qmldir": "module Shell.Context",
        QML_SHELL_CONTROLLERS / "qmldir": "module Shell.Controllers",
        QML_PLATFORM_CONTROLLERS / "qmldir": "module Platform.Controllers",
        QML_PLATFORM_DIALOGS / "qmldir": "module Platform.Dialogs",
        QML_PLATFORM_WIDGETS / "qmldir": "module Platform.Widgets",
        QML_PM_CONTROLLERS / "qmldir": "module ProjectManagement.Controllers",
        QML_PM_WIDGETS / "qmldir": "module ProjectManagement.Widgets",
        QML_INV_CONTROLLERS / "qmldir": "module InventoryProcurement.Controllers",
        QML_INV_DIALOGS / "qmldir": "module InventoryProcurement.Dialogs",
        QML_INV_WIDGETS / "qmldir": "module InventoryProcurement.Widgets",
    }

    for path, module_name in expected_modules.items():
        assert module_name in path.read_text(encoding="utf-8")


def test_qml_controls_module_exports_enterprise_control_set() -> None:
    controls_qmldir = (QML_SHARED_ROOT / "Controls" / "qmldir").read_text(
        encoding="utf-8"
    )

    expected_exports = [
        "CheckBox 1.0 CheckBox.qml",
        "ComboBox 1.0 ComboBox.qml",
        "DateField 1.0 DateField.qml",
        "Label 1.0 Label.qml",
        "PrimaryButton 1.0 PrimaryButton.qml",
        "RadioButton 1.0 RadioButton.qml",
        "SearchField 1.0 SearchField.qml",
        "SecondaryButton 1.0 SecondaryButton.qml",
        "TextArea 1.0 TextArea.qml",
        "TextField 1.0 TextField.qml",
        "ToggleSwitch 1.0 ToggleSwitch.qml",
    ]

    for export in expected_exports:
        assert export in controls_qmldir


def test_qml_uses_enterprise_controls_instead_of_raw_form_controls() -> None:
    controls_root = QML_SHARED_ROOT / "Controls"
    raw_control_patterns = {
        "Label": re.compile(r"(?<![A-Za-z0-9_.])Label(?=\s*\{)"),
        "TextField": re.compile(r"(?<![A-Za-z0-9_.])TextField(?=\s*\{)"),
        "TextArea": re.compile(r"(?<![A-Za-z0-9_.])TextArea(?=\s*\{)"),
        "ComboBox": re.compile(r"(?<![A-Za-z0-9_.])ComboBox(?=\s*\{)"),
        "CheckBox": re.compile(r"(?<![A-Za-z0-9_.])CheckBox(?=\s*\{)"),
        "RadioButton": re.compile(r"(?<![A-Za-z0-9_.])RadioButton(?=\s*\{)"),
    }
    violations: list[str] = []

    for path in UI_QML_ROOT.rglob("*.qml"):
        if controls_root in path.parents:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for control_name, pattern in raw_control_patterns.items():
            if pattern.search(text):
                violations.append(f"{path}:{control_name}")

    assert not violations, f"Raw form controls found outside App.Controls: {violations}"


def test_qmlls_import_paths_cover_named_qml_modules() -> None:
    config_text = QMLLS_CONFIG.read_text(encoding="utf-8")
    expected_paths = [
        "src/ui_qml/shared/qml",
        "src/ui_qml/shell/qml",
        "src/ui_qml/platform/qml",
        "src/ui_qml/modules/project_management/qml",
        "src/ui_qml/modules/inventory_procurement/qml",
    ]

    for expected_path in expected_paths:
        assert expected_path in config_text

    assert "src/ui_qml/modules;" not in config_text
    assert not config_text.rstrip().endswith("src/ui_qml/modules")


def test_qmlls_import_paths_parse_as_qt_string_list() -> None:
    settings = QSettings(str(QMLLS_CONFIG.resolve()), QSettings.IniFormat)
    import_paths = settings.value("AdditionalQmlImportPaths")

    assert isinstance(import_paths, list)
    assert "C:/Users/ashuf/Desktop/Projects/project_mangement_app/src/ui_qml/shared/qml" in import_paths
    assert "C:/Users/ashuf/Desktop/Projects/project_mangement_app/src/ui_qml/shell/qml" in import_paths
    assert "C:/Users/ashuf/Desktop/Projects/project_mangement_app/src/ui_qml/platform/qml" in import_paths
    assert "C:/Users/ashuf/Desktop/Projects/project_mangement_app/src/ui_qml/modules/project_management/qml" in import_paths
    assert "C:/Users/ashuf/Desktop/Projects/project_mangement_app/src/ui_qml/modules/inventory_procurement/qml" in import_paths
