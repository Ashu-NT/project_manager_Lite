from pathlib import Path


UI_QML_ROOT = Path("src/ui_qml")
QML_SHARED_ROOT = Path("src/ui_qml/shared/qml/App")
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
        Path("src/ui_qml/platform/qml/documents/dialogs/DocumentLinkEditorDialog.qml"),
        Path("src/ui_qml/platform/qml/documents/dialogs/DocumentStructureEditorDialog.qml"),
        QML_PLATFORM_WIDGETS / "RecordListCard.qml",
        QML_SHARED_ROOT / "Widgets" / "OverviewSectionCard.qml",
        Path("src/ui_qml/platform/qml/documents/DocumentDetailPanel.qml"),
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
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/financials/dialogs"
        / "ManualActualEditorDialog.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/projects/dialogs"
        / "ProjectEditorDialog.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/projects/dialogs"
        / "ProjectStatusDialog.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/register/dialogs"
        / "RegisterEntryEditorDialog.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/resources/dialogs"
        / "ResourceEditorDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskAssignmentEditorDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskAssignmentPlannedHoursDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskAssignmentResponseDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskCollaborationComposerDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskCommentDeleteDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskDependencyEditorDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskEditorDialog.qml",
        UI_QML_ROOT / "modules/project_management/qml/workspaces/tasks/dialogs/TaskProgressDialog.qml",
        QML_PM_WIDGETS / "qmldir",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/dashboard/components"
        / "DashboardChartCard.qml",
        QML_PM_WIDGETS / "RecordListCard.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/register/sections"
        / "RegisterDetailSection.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/register/dialogs"
        / "RegisterDialogHost.qml",
        UI_QML_ROOT
        / "modules/project_management/qml/workspaces/register/sections"
        / "RegisterUrgentSection.qml",
    ]

    assert all(path.exists() for path in expected_files)


def test_qml_inventory_procurement_modules_exist() -> None:
    _inv = UI_QML_ROOT / "modules" / "inventory_procurement" / "qml" / "workspaces"
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
        _inv / "dashboard" / "DashboardWorkspace.qml",
        _inv / "dashboard" / "DashboardWorkspacePage.qml",
        _inv / "catalog" / "CatalogWorkspace.qml",
        _inv / "catalog" / "CatalogWorkspacePage.qml",
        _inv / "catalog" / "dialogs" / "CatalogDialogHost.qml",
        _inv / "catalog" / "panels" / "CatalogDetailPanel.qml",
        _inv / "inventory" / "InventoryWorkspace.qml",
        _inv / "inventory" / "InventoryWorkspacePage.qml",
        _inv / "inventory" / "dialogs" / "InventoryDialogHost.qml",
        _inv / "inventory" / "panels" / "InventoryDetailPanel.qml",
        _inv / "reservations" / "ReservationsWorkspace.qml",
        _inv / "reservations" / "ReservationsWorkspacePage.qml",
        _inv / "reservations" / "dialogs" / "ReservationsDialogHost.qml",
        _inv / "reservations" / "panels" / "ReservationsDetailPanel.qml",
        _inv / "procurement" / "ProcurementWorkspace.qml",
        _inv / "procurement" / "ProcurementWorkspacePage.qml",
        _inv / "procurement" / "dialogs" / "ProcurementDialogHost.qml",
        _inv / "pricing" / "PricingWorkspace.qml",
        _inv / "pricing" / "PricingWorkspacePage.qml",
        _inv / "pricing" / "panels" / "PricingDetailPanel.qml",
        _inv / "warehouses" / "WarehousesWorkspace.qml",
        _inv / "warehouses" / "WarehousesWorkspacePage.qml",
        _inv / "warehouses" / "panels" / "WarehousesDetailPanel.qml",
    ]

    assert all(path.exists() for path in expected_files)


def test_qml_shared_theme_matches_legacy_widget_tokens() -> None:
    theme_qml = (QML_SHARED_ROOT / "Theme" / "AppTheme.qml").read_text(encoding="utf-8")

    assert 'property string densityMode: "compact"' in theme_qml
    # R1.10 made these dark-mode-aware (root.darkMode ? <dark> : <light>) rather
    # than flat literals; the light-mode value is preserved unchanged, so check
    # for the property declaration and its light-mode value separately instead
    # of one exact-literal assignment.
    assert "readonly property color appBackground:" in theme_qml
    assert '"#F3F6FA"' in theme_qml
    assert "readonly property color background: appBackground" in theme_qml
    assert "readonly property color workspaceBackground:" in theme_qml
    assert "readonly property color accent:" in theme_qml
    assert '"#0A66A8"' in theme_qml
    assert "readonly property int toolbarHeight:" in theme_qml
    assert "readonly property int compactRowHeight:" in theme_qml
    assert 'readonly property string fontFamily: "Segoe UI Variable Text"' in theme_qml


def test_qml_workspace_frame_exposes_default_content_slot() -> None:
    frame_qml = (QML_SHARED_ROOT / "Layouts" / "WorkspaceFrame.qml").read_text(
        encoding="utf-8"
    )

    assert "default property alias content: contentSlot.data" in frame_qml


def test_data_table_declares_explicit_backward_compatible_sorting_modes() -> None:
    table_qml = (QML_SHARED_ROOT / "Widgets" / "DataTable.qml").read_text(
        encoding="utf-8"
    )

    assert 'property string sortingMode: clientSideSorting ? "client" : "none"' in table_qml
    assert 'mode === "client" || mode === "server" || mode === "none"' in table_qml
    mode_block = table_qml.split(
        "readonly property string _effectiveSortingMode:", maxsplit=1
    )[1].split("}", maxsplit=1)[0]
    assert ': "none"' in mode_block
    assert 'signal sortRequested(string key, int direction)' in table_qml


def test_data_table_server_sort_is_emit_only() -> None:
    table_qml = (QML_SHARED_ROOT / "Widgets" / "DataTable.qml").read_text(
        encoding="utf-8"
    )

    server_branch = table_qml.split(
        'if (root._effectiveSortingMode === "server") {', maxsplit=1
    )[1].split("return", maxsplit=1)[0]
    assert 'root.sortRequested(normalizedKey, requestedDirection)' in server_branch
    assert "root.sortKey =" not in server_branch
    assert "root.sortDirection =" not in server_branch
    assert "toggleSort" not in server_branch
    assert "const requestedDirection" in table_qml
    assert 'root._effectiveSortingMode !== "client"' in table_qml
    assert 'root._effectiveSortingMode !== "none"' in table_qml


def test_non_pm_data_tables_keep_legacy_client_sorting_default() -> None:
    consumers = [
        path
        for path in UI_QML_ROOT.rglob("*.qml")
        if "AppWidgets.DataTable {" in path.read_text(encoding="utf-8")
        and "project_management" not in path.parts
    ]

    assert consumers
    for path in consumers:
        content = path.read_text(encoding="utf-8")
        assert "sortingMode:" not in content, path
        assert "clientSideSorting:" not in content, path
