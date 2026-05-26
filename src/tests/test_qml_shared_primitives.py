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
QML_PM_DIALOGS = Path(
    "src/ui_qml/modules/project_management/qml/ProjectManagement/Dialogs"
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
QML_MAINT_CONTROLLERS = Path(
    "src/ui_qml/modules/maintenance/qml/Maintenance/Controllers"
)
QML_MAINT_DIALOGS = Path(
    "src/ui_qml/modules/maintenance/qml/Maintenance/Dialogs"
)
QML_MAINT_WIDGETS = Path(
    "src/ui_qml/modules/maintenance/qml/Maintenance/Widgets"
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
        QML_PM_DIALOGS / "qmldir": "module ProjectManagement.Dialogs",
        QML_PM_WIDGETS / "qmldir": "module ProjectManagement.Widgets",
        QML_INV_CONTROLLERS / "qmldir": "module InventoryProcurement.Controllers",
        QML_INV_DIALOGS / "qmldir": "module InventoryProcurement.Dialogs",
        QML_INV_WIDGETS / "qmldir": "module InventoryProcurement.Widgets",
        QML_MAINT_CONTROLLERS / "qmldir": "module Maintenance.Controllers",
        QML_MAINT_DIALOGS / "qmldir": "module Maintenance.Dialogs",
        QML_MAINT_WIDGETS / "qmldir": "module Maintenance.Widgets",
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
        "src/ui_qml/modules/maintenance/qml",
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
    assert "C:/Users/ashuf/Desktop/Projects/project_mangement_app/src/ui_qml/modules/maintenance/qml" in import_paths


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
        QML_PM_CONTROLLERS / "typeinfo" / "collaboration.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "financials.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "portfolio.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "projects.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "register.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "resources.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "scheduling.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "tasks.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "timesheets.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "dashboard.fragment",
        QML_PM_CONTROLLERS / "typeinfo" / "catalog.fragment",
        QML_PM_DIALOGS / "qmldir",
        QML_PM_DIALOGS / "CostItemEditorDialog.qml",
        QML_PM_DIALOGS / "ProjectEditorDialog.qml",
        QML_PM_DIALOGS / "ProjectStatusDialog.qml",
        QML_PM_DIALOGS / "RegisterEntryEditorDialog.qml",
        QML_PM_DIALOGS / "ResourceEditorDialog.qml",
        QML_PM_DIALOGS / "TaskAssignmentEditorDialog.qml",
        QML_PM_DIALOGS / "TaskAssignmentHoursDialog.qml",
        QML_PM_DIALOGS / "TaskCollaborationComposerDialog.qml",
        QML_PM_DIALOGS / "TaskDependencyEditorDialog.qml",
        QML_PM_DIALOGS / "TaskEditorDialog.qml",
        QML_PM_DIALOGS / "TaskProgressDialog.qml",
        QML_PM_WIDGETS / "qmldir",
        QML_PM_WIDGETS / "DashboardChartCard.qml",
        QML_PM_WIDGETS / "DashboardPanelCard.qml",
        QML_PM_WIDGETS / "DashboardSectionCard.qml",
        QML_PM_WIDGETS / "RecordListCard.qml",
        QML_PM_WIDGETS / "RegisterCatalogSection.qml",
        QML_PM_WIDGETS / "RegisterDetailSection.qml",
        QML_PM_WIDGETS / "RegisterDialogHost.qml",
        QML_PM_WIDGETS / "RegisterFiltersSection.qml",
        QML_PM_WIDGETS / "RegisterMetricsSection.qml",
        QML_PM_WIDGETS / "RegisterUrgentSection.qml",
        QML_PM_WIDGETS / "TimesheetEntriesCard.qml",
        QML_PM_WIDGETS / "WorkspaceStateBanner.qml",
        QML_PM_WIDGETS / "WorkspacePlaceholderPage.qml",
        QML_PM_WIDGETS / "WorkspaceStatusSection.qml",
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "TasksBulkActionsSection.qml",
    ]

    assert all(path.exists() for path in expected_files)


def test_qml_inventory_procurement_modules_exist() -> None:
    expected_files = [
        QML_INV_CONTROLLERS / "qmldir",
        QML_INV_CONTROLLERS / "typeinfo" / "plugins.qmltypes",
        QML_INV_DIALOGS / "qmldir",
        QML_INV_DIALOGS / "CategoryEditorDialog.qml",
        QML_INV_DIALOGS / "DocumentLinkDialog.qml",
        QML_INV_DIALOGS / "ItemEditorDialog.qml",
        QML_INV_DIALOGS / "PurchaseOrderEditorDialog.qml",
        QML_INV_DIALOGS / "PurchaseOrderLineDialog.qml",
        QML_INV_DIALOGS / "ReservationCreateDialog.qml",
        QML_INV_DIALOGS / "ReservationIssueDialog.qml",
        QML_INV_DIALOGS / "ReceiptPostDialog.qml",
        QML_INV_DIALOGS / "RequisitionEditorDialog.qml",
        QML_INV_DIALOGS / "RequisitionLineDialog.qml",
        QML_INV_DIALOGS / "StockMovementDialog.qml",
        QML_INV_DIALOGS / "StockTransferDialog.qml",
        QML_INV_DIALOGS / "StoreroomEditorDialog.qml",
        QML_INV_WIDGETS / "qmldir",
        QML_INV_WIDGETS / "RecordListCard.qml",
        QML_INV_WIDGETS / "WorkspacePlaceholderPage.qml",
        QML_INV_WIDGETS / "WorkspaceStateBanner.qml",
        QML_INV_WIDGETS / "WorkspaceStatusSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "dashboard" / "DashboardWorkspace.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "dashboard" / "DashboardWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "catalog" / "CatalogWorkspace.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "catalog" / "CatalogWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "catalog" / "CatalogDialogHost.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "catalog" / "CatalogFiltersSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "catalog" / "CategoryCatalogSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "catalog" / "CategoryDetailSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "catalog" / "ItemCatalogSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "catalog" / "ItemDetailSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "inventory" / "InventoryWorkspace.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "inventory" / "InventoryWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "inventory" / "InventoryDialogHost.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "inventory" / "InventoryFiltersSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "inventory" / "InventoryMetricsSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "inventory" / "StoreroomCatalogSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "inventory" / "StoreroomDetailSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "inventory" / "BalanceCatalogSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "inventory" / "BalanceDetailSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "inventory" / "TransactionsSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "reservations" / "ReservationsWorkspace.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "reservations" / "ReservationsWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "reservations" / "ReservationsDialogHost.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "reservations" / "ReservationsFiltersSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "reservations" / "ReservationsMetricsSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "reservations" / "ReservationsCatalogSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "reservations" / "ReservationDetailSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "procurement" / "ProcurementWorkspace.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "procurement" / "ProcurementWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "procurement" / "ProcurementDialogHost.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "procurement" / "ProcurementFiltersSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "procurement" / "ProcurementMetricsSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "procurement" / "RequisitionCatalogSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "procurement" / "RequisitionDetailSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "procurement" / "RequisitionLinesSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "procurement" / "PurchaseOrderCatalogSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "procurement" / "PurchaseOrderDetailSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "procurement" / "PurchaseOrderLinesSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "procurement" / "ReceiptHistorySection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "pricing" / "PricingWorkspace.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "pricing" / "PricingWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "pricing" / "PricingMetricsSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "pricing" / "PricingFiltersSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "pricing" / "PricingExportsSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "pricing" / "PricingStockSection.qml",
        UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces" / "pricing" / "PricingSupplierPricingSection.qml",
    ]

    assert all(path.exists() for path in expected_files)


def test_qml_maintenance_modules_exist() -> None:
    expected_files = [
        QML_MAINT_CONTROLLERS / "qmldir",
        QML_MAINT_CONTROLLERS / "typeinfo" / "plugins.qmltypes",
        QML_MAINT_DIALOGS / "qmldir",
        QML_MAINT_WIDGETS / "qmldir",
        QML_MAINT_WIDGETS / "RecordListCard.qml",
        QML_MAINT_WIDGETS / "WorkspacePlaceholderPage.qml",
        QML_MAINT_WIDGETS / "WorkspaceStateBanner.qml",
        QML_MAINT_WIDGETS / "WorkspaceStatusSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "dashboard" / "DashboardWorkspace.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "dashboard" / "DashboardWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "dashboard" / "DashboardMetricsSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "dashboard" / "DashboardFiltersSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "dashboard" / "DashboardBacklogSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "dashboard" / "DashboardRootCausesSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "dashboard" / "DashboardRecurringSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "reliability" / "ReliabilityWorkspace.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "reliability" / "ReliabilityWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "reliability" / "ReliabilityMetricsSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "reliability" / "ReliabilityFiltersSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "reliability" / "ReliabilitySuggestionsSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "reliability" / "ReliabilityRootCausesSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "reliability" / "ReliabilityRecurringSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "assets" / "AssetsWorkspace.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "assets" / "AssetsWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "assets" / "AssetsMetricsSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "assets" / "AssetsFiltersSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "assets" / "AssetLibraryCatalogSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "assets" / "AssetLibraryDetailSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "assets" / "AssetsDialogHost.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_requests" / "WorkRequestsWorkspace.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_requests" / "WorkRequestsWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_requests" / "WorkRequestsMetricsSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_requests" / "WorkRequestsFiltersSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_requests" / "WorkRequestsCatalogSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_requests" / "WorkRequestDetailSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_requests" / "WorkRequestsDialogHost.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_orders" / "WorkOrdersWorkspace.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_orders" / "WorkOrdersWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_orders" / "WorkOrdersMetricsSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_orders" / "WorkOrdersFiltersSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_orders" / "WorkOrdersCatalogSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_orders" / "WorkOrderDetailSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "work_orders" / "WorkOrdersDialogHost.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveWorkspace.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveMetricsSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveDetailSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveQueueSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventivePlansSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveTemplatesSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "preventive" / "PreventiveDialogHost.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "planner" / "PlannerWorkspace.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "planner" / "PlannerWorkspacePage.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "planner" / "PlannerFiltersSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "planner" / "PlannerMetricsSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "planner" / "PlannerRequestsSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "planner" / "PlannerBacklogSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "planner" / "PlannerMaterialRisksSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "planner" / "PlannerPreventiveSection.qml",
        UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces" / "planner" / "PlannerRecurringSection.qml",
        QML_MAINT_DIALOGS / "LocationEditorDialog.qml",
        QML_MAINT_DIALOGS / "SystemEditorDialog.qml",
        QML_MAINT_DIALOGS / "AssetEditorDialog.qml",
        QML_MAINT_DIALOGS / "ComponentEditorDialog.qml",
        QML_MAINT_DIALOGS / "WorkRequestEditorDialog.qml",
        QML_MAINT_DIALOGS / "WorkRequestStatusDialog.qml",
        QML_MAINT_DIALOGS / "WorkOrderEditorDialog.qml",
        QML_MAINT_DIALOGS / "WorkOrderStatusDialog.qml",
        QML_MAINT_DIALOGS / "PreventivePlanEditorDialog.qml",
        QML_MAINT_DIALOGS / "PreventivePlanTaskEditorDialog.qml",
        QML_MAINT_DIALOGS / "TaskTemplateEditorDialog.qml",
        QML_MAINT_DIALOGS / "TaskStepTemplateEditorDialog.qml",
    ]

    assert all(path.exists() for path in expected_files)


def test_qml_shared_theme_matches_legacy_widget_tokens() -> None:
    theme_qml = (QML_SHARED_ROOT / "Theme" / "AppTheme.qml").read_text(encoding="utf-8")

    assert 'property string densityMode: "compact"' in theme_qml
    assert 'readonly property color appBackground: "#F3F6FA"' in theme_qml
    assert "readonly property color background: appBackground" in theme_qml
    assert "readonly property color workspaceBackground:" in theme_qml
    assert 'readonly property color accent: "#0A66A8"' in theme_qml
    assert "readonly property int toolbarHeight:" in theme_qml
    assert "readonly property int compactRowHeight:" in theme_qml
    assert 'readonly property string fontFamily: "Segoe UI Variable Text"' in theme_qml


def test_qml_workspace_frame_exposes_default_content_slot() -> None:
    frame_qml = (QML_SHARED_ROOT / "Layouts" / "WorkspaceFrame.qml").read_text(
        encoding="utf-8"
    )

    assert "default property alias content: contentSlot.data" in frame_qml

