pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import "dialogs" as Dialogs
import "sections" as Sections
import "panels" as Panels
import "components" as Components

AppLayouts.WorkspaceFrame {
    id: root

    property var platformCatalog
    property var _caps: ({})

    Component.onCompleted: {
        if (root.platformCatalog) root._caps = root.platformCatalog.capabilitySnapshot()
    }

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementCatalogWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.catalogWorkspace
        : null

    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": "Catalog", "subtitle": "Item master, categories, supplier references, and stock policies.", "metrics": [] })
    readonly property var itemsModel: root.workspaceController
        ? root.workspaceController.items
        : ({ "items": [], "emptyState": "No catalog items." })
    readonly property var categoriesModel: root.workspaceController
        ? root.workspaceController.categories
        : ({ "items": [], "emptyState": "No categories." })
    readonly property var selectedItemModel: root.workspaceController
        ? root.workspaceController.selectedItem
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "fields": [], "linkedDocuments": [], "state": {} })
    readonly property var selectedCategoryModel: root.workspaceController
        ? root.workspaceController.selectedCategory
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "fields": [], "state": {} })

    readonly property bool _isItemsView: root.workspaceController
        ? root.workspaceController.activeView === "items"
        : true

    title:    root.overviewModel.title    || "Catalog"
    subtitle: root.overviewModel.subtitle || ""

    // ── Detail state ───────────────────────────────────────────────────
    property bool _detailOpen: false
    property int  _pendingDetailSection: 0
    readonly property var _detailPage: _detailPageLoader.item

    readonly property var _detailSections: root._isItemsView
        ? ["Overview", "Documents", "Activity"]
        : ["Overview", "Activity"]

    readonly property var _detailActions: {
        const page = root._detailPage
        const idx  = page ? page.activeSectionIndex : 0
        if (idx !== 0) return []
        const detail  = root._isItemsView ? root.selectedItemModel : root.selectedCategoryModel
        const isActive = detail && detail.state && detail.state.isActive
        return [
            { "id": "edit",   "label": "Edit",                               "icon": "edit",                        "enabled": true, "danger": false },
            { "id": "toggle", "label": isActive ? "Deactivate" : "Activate", "icon": isActive ? "reject" : "approve", "enabled": true, "danger": false }
        ]
    }

    function _loadLazyDetailSection(sectionIndex) {
        if (root.workspaceController === null) return
        const activityIdx = root._isItemsView ? 2 : 1
        if (sectionIndex !== activityIdx) return
        const entityId   = root._isItemsView ? String(root.selectedItemModel.id || "") : String(root.selectedCategoryModel.id || "")
        const entityType = root._isItemsView ? "inventory_item" : "inventory_category"
        root.workspaceController.loadDetailActivity(entityId, entityType)
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (root._detailPage) {
            root._detailPage.scrollToSection(sectionIndex)
            root._loadLazyDetailSection(sectionIndex)
        }
    }

    // ── Export dialog ──────────────────────────────────────────────────
    FileDialog {
        id: _exportDialog
        title:       "Export Catalog"
        fileMode:    FileDialog.SaveFile
        nameFilters: ["Excel files (*.xlsx)", "CSV files (*.csv)"]
        onAccepted: {
            if (root.workspaceController !== null) {
                root.workspaceController.exportTable([], String(selectedFile || ""))
            }
        }
    }

    // ── Dialog host ────────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.CatalogDialogHost {
                categoryTypeOptions:  root.workspaceController ? (root.workspaceController.categoryTypeOptions  || []) : []
                categoryOptions:      root.workspaceController ? (root.workspaceController.categoryOptions      || []) : []
                itemStatusOptions:    root.workspaceController ? (root.workspaceController.itemStatusOptions    || []) : []
                businessPartyOptions: root.workspaceController ? (root.workspaceController.businessPartyOptions || []) : []
                availableDocuments:   root.workspaceController ? (root.workspaceController.availableDocuments   || []) : []
                workspaceController:  root.workspaceController
            }
        }
    }

    // ── Stacked list / detail ──────────────────────────────────────────
    Item {
        anchors.fill: parent

        // ── List page ─────────────────────────────────────────────────
        Item {
            anchors.fill: parent
            visible: !root._detailOpen || _detailPageLoader.status !== Loader.Ready

            Components.CatalogListPage {
                anchors.fill:      parent
                workspaceController: root.workspaceController
                overviewModel:     root.overviewModel
                itemsModel:        root.itemsModel
                categoriesModel:   root.categoriesModel
                detailOpen:        root._detailOpen

                onRowActivated:         root._openDetail(0)
                onExportRequested:      _exportDialog.open()
                onCreateItemRequested:  dialogHostLoader.invoke("openCreateItemDialog")
                onCreateCategoryRequested: dialogHostLoader.invoke("openCreateCategoryDialog")
            }
        }

        // ── Detail page (lazy loaded) ──────────────────────────────────
        Loader {
            id: _detailPageLoader
            anchors.fill: parent
            active:       root._detailOpen
            visible:      root._detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent

            AppWidgets.SectionDetailPage {
                open:        true
                anchors.fill: parent
                showHeader:  false
                showEdit:    false
                showDelete:  false
                isBusy:      root.workspaceController ? root.workspaceController.isBusy : false
                sections:    root._detailSections
                z:           20
                Component.onCompleted: {
                    scrollToSection(root._pendingDetailSection)
                    root._loadLazyDetailSection(root._pendingDetailSection)
                }
                onSectionChanged: function(index) { root._loadLazyDetailSection(index) }

                AppWidgets.ContextualActionToolbar {
                    width:    parent ? parent.width : 0
                    showBack: true
                    title:    root._isItemsView ? (root.selectedItemModel.title || "Item Detail") : (root.selectedCategoryModel.title || "Category Detail")
                    subtitle: root._isItemsView ? (root.selectedItemModel.statusLabel || root.selectedItemModel.subtitle || "") : (root.selectedCategoryModel.statusLabel || root.selectedCategoryModel.subtitle || "")
                    busy:     root.workspaceController ? root.workspaceController.isBusy : false
                    actions:  root._detailActions
                    onBackRequested: { root._detailOpen = false }
                    onActionTriggered: function(actionId) {
                        if (actionId === "edit") {
                            if (root._isItemsView) dialogHostLoader.invoke("openEditItemDialog", root.selectedItemModel)
                            else                   dialogHostLoader.invoke("openEditCategoryDialog", root.selectedCategoryModel)
                        } else if (actionId === "toggle") {
                            if (root._isItemsView) {
                                const s = root.selectedItemModel.state || {}
                                if (root.workspaceController !== null && s.itemId) root.workspaceController.toggleItemActive(String(s.itemId || ""), parseInt(String(s.version || "0"), 10))
                            } else {
                                const s = root.selectedCategoryModel.state || {}
                                if (root.workspaceController !== null && s.categoryId) root.workspaceController.toggleCategoryActive(String(s.categoryId || ""), parseInt(String(s.version || "0"), 10))
                            }
                        }
                    }
                }

                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0; tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : "" }
                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0 && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : "" }

                Panels.CatalogDetailPanel {
                    width:        parent ? parent.width : 0
                    isItemsView:  root._isItemsView
                    itemDetail:   root.selectedItemModel
                    categoryDetail: root.selectedCategoryModel
                    detailPage:   root._detailPage
                    isBusy:       root.workspaceController ? root.workspaceController.isBusy : false
                    activityItems: root.workspaceController ? (root.workspaceController.detailActivityItems || []) : []
                    onLinkDocumentRequested: dialogHostLoader.invoke("openLinkDocumentDialog", root.selectedItemModel)
                    onUnlinkDocumentRequested: function(documentData) {
                        const s = root.selectedItemModel.state || {}
                        if (root.workspaceController !== null && s.itemId && documentData && documentData.value)
                            root.workspaceController.unlinkDocument(String(s.itemId || ""), String(documentData.value || ""))
                    }
                }
            }
        }
    }
}
