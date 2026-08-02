from pathlib import Path


UI_QML_ROOT = Path("src/ui_qml")
QML_SHARED_ROOT = Path("src/ui_qml/shared/qml/App")
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
        QML_PM_DIALOGS / "TaskAssignmentResponseDialog.qml",
        QML_PM_DIALOGS / "TaskCollaborationComposerDialog.qml",
        QML_PM_DIALOGS / "TaskCommentDeleteDialog.qml",
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
        UI_QML_ROOT / "modules" / "project_management" / "qml" / "workspaces" / "tasks" / "components" / "TasksBulkActions.qml",
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


def test_qml_maintenance_modules_exist() -> None:
    _maint = UI_QML_ROOT / "modules" / "maintenance" / "qml" / "workspaces"
    expected_files = [
        QML_MAINT_CONTROLLERS / "qmldir",
        QML_MAINT_CONTROLLERS / "typeinfo" / "plugins.qmltypes",
        QML_MAINT_DIALOGS / "qmldir",
        QML_MAINT_WIDGETS / "qmldir",
        QML_MAINT_WIDGETS / "RecordListCard.qml",
        QML_MAINT_WIDGETS / "WorkspacePlaceholderPage.qml",
        QML_MAINT_WIDGETS / "WorkspaceStateBanner.qml",
        QML_MAINT_WIDGETS / "WorkspaceStatusSection.qml",
        _maint / "dashboard" / "DashboardWorkspace.qml",
        _maint / "dashboard" / "DashboardWorkspacePage.qml",
        _maint / "dashboard" / "sections" / "DashboardMetricsSection.qml",
        _maint / "dashboard" / "sections" / "DashboardFiltersSection.qml",
        _maint / "dashboard" / "sections" / "DashboardBacklogSection.qml",
        _maint / "dashboard" / "sections" / "DashboardRootCausesSection.qml",
        _maint / "dashboard" / "sections" / "DashboardRecurringSection.qml",
        _maint / "reliability" / "ReliabilityWorkspace.qml",
        _maint / "reliability" / "ReliabilityWorkspacePage.qml",
        _maint / "reliability" / "sections" / "ReliabilityMetricsSection.qml",
        _maint / "reliability" / "sections" / "ReliabilityFiltersSection.qml",
        _maint / "reliability" / "sections" / "ReliabilitySuggestionsSection.qml",
        _maint / "reliability" / "sections" / "ReliabilityRootCausesSection.qml",
        _maint / "reliability" / "sections" / "ReliabilityRecurringSection.qml",
        _maint / "assets" / "AssetsWorkspace.qml",
        _maint / "assets" / "AssetsWorkspacePage.qml",
        _maint / "assets" / "sections" / "AssetsMetricsSection.qml",
        _maint / "assets" / "sections" / "AssetsFiltersSection.qml",
        _maint / "assets" / "sections" / "AssetLibraryCatalogSection.qml",
        _maint / "assets" / "sections" / "AssetLibraryDetailSection.qml",
        _maint / "assets" / "dialogs" / "AssetsDialogHost.qml",
        _maint / "work_requests" / "WorkRequestsWorkspace.qml",
        _maint / "work_requests" / "WorkRequestsWorkspacePage.qml",
        _maint / "work_requests" / "sections" / "WorkRequestsMetricsSection.qml",
        _maint / "work_requests" / "sections" / "WorkRequestsFiltersSection.qml",
        _maint / "work_requests" / "sections" / "WorkRequestsCatalogSection.qml",
        _maint / "work_requests" / "panels" / "WorkRequestDetailPanel.qml",
        _maint / "work_requests" / "dialogs" / "WorkRequestsDialogHost.qml",
        _maint / "work_orders" / "WorkOrdersWorkspace.qml",
        _maint / "work_orders" / "WorkOrdersWorkspacePage.qml",
        _maint / "work_orders" / "sections" / "WorkOrdersMetricsSection.qml",
        _maint / "work_orders" / "sections" / "WorkOrdersFiltersSection.qml",
        _maint / "work_orders" / "sections" / "WorkOrdersCatalogSection.qml",
        _maint / "work_orders" / "panels" / "WorkOrderDetailPanel.qml",
        _maint / "work_orders" / "dialogs" / "WorkOrdersDialogHost.qml",
        _maint / "preventive" / "PreventiveWorkspace.qml",
        _maint / "preventive" / "PreventiveWorkspacePage.qml",
        _maint / "preventive" / "sections" / "PreventiveMetricsSection.qml",
        _maint / "preventive" / "sections" / "PreventiveDetailSection.qml",
        _maint / "preventive" / "sections" / "PreventiveQueueSection.qml",
        _maint / "preventive" / "sections" / "PreventivePlansSection.qml",
        _maint / "preventive" / "sections" / "PreventiveTemplatesSection.qml",
        _maint / "preventive" / "dialogs" / "PreventiveDialogHost.qml",
        _maint / "planner" / "PlannerWorkspace.qml",
        _maint / "planner" / "PlannerWorkspacePage.qml",
        _maint / "planner" / "sections" / "PlannerFiltersSection.qml",
        _maint / "planner" / "sections" / "PlannerMetricsSection.qml",
        _maint / "planner" / "sections" / "PlannerRequestsSection.qml",
        _maint / "planner" / "sections" / "PlannerBacklogSection.qml",
        _maint / "planner" / "sections" / "PlannerMaterialRisksSection.qml",
        _maint / "planner" / "sections" / "PlannerPreventiveSection.qml",
        _maint / "planner" / "sections" / "PlannerRecurringSection.qml",
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
