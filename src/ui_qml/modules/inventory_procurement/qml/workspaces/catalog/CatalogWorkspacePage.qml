import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementCatalogWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.catalogWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "inventory_procurement.catalog",
            "title": "Catalog",
            "summary": "Category governance, reusable stock items, supplier context, and linked document workflows.",
            "migrationStatus": "QML CRUD catalog slice active",
            "legacyRuntimeStatus": "Existing QWidget catalog workspaces remain active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var categoriesModel: root.workspaceController
        ? root.workspaceController.categories
        : ({
            "title": "Category Catalog",
            "subtitle": "Govern category types, usage flags, and equipment grouping.",
            "emptyState": "Inventory catalog desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var itemsModel: root.workspaceController
        ? root.workspaceController.items
        : ({
            "title": "Item Catalog",
            "subtitle": "Manage reusable stock items, supplier context, and linked documents.",
            "emptyState": "Inventory catalog desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedCategoryModel: root.workspaceController
        ? root.workspaceController.selectedCategory
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a category from the catalog to review usage flags or update its governance settings.",
            "fields": [],
            "linkedDocuments": [],
            "state": {}
        })
    readonly property var selectedItemModel: root.workspaceController
        ? root.workspaceController.selectedItem
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select an item from the catalog to review operational fields, supplier context, and linked documents.",
            "fields": [],
            "linkedDocuments": [],
            "state": {}
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    CatalogDialogHost {
        id: dialogHost

        categoryTypeOptions: root.workspaceController ? (root.workspaceController.categoryTypeOptions || []) : []
        categoryOptions: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
        itemStatusOptions: root.workspaceController ? (root.workspaceController.itemStatusOptions || []) : []
        businessPartyOptions: root.workspaceController ? (root.workspaceController.businessPartyOptions || []) : []
        availableDocuments: root.workspaceController ? (root.workspaceController.availableDocuments || []) : []

        onCreateCategoryRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createCategory(payload)
            }
        }

        onUpdateCategoryRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateCategory(payload)
            }
        }

        onCreateItemRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createItem(payload)
            }
        }

        onUpdateItemRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateItem(payload)
            }
        }

        onLinkDocumentRequested: function(itemId, documentId) {
            if (root.workspaceController !== null) {
                root.workspaceController.linkDocument(itemId, documentId)
            }
        }
    }

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: 12

            CatalogMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            InventoryWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            InventoryWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML CRUD catalog slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Category and item master flows, supplier context, and document linking now run through a typed inventory controller backed by the module-local catalog desktop API."
            }

            CatalogFiltersSection {
                Layout.fillWidth: true
                activeOptions: root.workspaceController ? (root.workspaceController.activeOptions || []) : []
                usageOptions: root.workspaceController ? (root.workspaceController.usageOptions || []) : []
                categoryTypeOptions: root.workspaceController ? (root.workspaceController.categoryTypeOptions || []) : []
                categoryOptions: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                selectedActiveFilter: root.workspaceController ? root.workspaceController.selectedActiveFilter : "all"
                selectedUsageFilter: root.workspaceController ? root.workspaceController.selectedUsageFilter : "all"
                selectedCategoryTypeFilter: root.workspaceController ? root.workspaceController.selectedCategoryTypeFilter : "all"
                selectedCategoryFilter: root.workspaceController ? root.workspaceController.selectedCategoryFilter : "all"
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onSearchTextUpdated: function(searchText) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSearchText(searchText)
                    }
                }

                onActiveFilterUpdated: function(activeValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setActiveFilter(activeValue)
                    }
                }

                onUsageFilterUpdated: function(usageValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setUsageFilter(usageValue)
                    }
                }

                onCategoryTypeFilterUpdated: function(categoryType) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setCategoryTypeFilter(categoryType)
                    }
                }

                onCategoryFilterUpdated: function(categoryCode) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setCategoryFilter(categoryCode)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }

                onCreateCategoryRequested: dialogHost.openCreateCategoryDialog()
                onCreateItemRequested: dialogHost.openCreateItemDialog()
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                CategoryCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    categoriesModel: root.categoriesModel
                    selectedCategoryId: root.workspaceController ? root.workspaceController.selectedCategoryId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onCategorySelected: function(categoryId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectCategory(categoryId)
                        }
                    }

                    onEditRequested: function(categoryData) {
                        if (categoryData && categoryData.id && root.workspaceController !== null) {
                            root.workspaceController.selectCategory(categoryData.id)
                        }
                        dialogHost.openEditCategoryDialog(categoryData)
                    }

                    onToggleRequested: function(categoryData) {
                        if (!categoryData || !categoryData.state || root.workspaceController === null) {
                            return
                        }
                        root.workspaceController.toggleCategoryActive(
                            String(categoryData.state.categoryId || ""),
                            parseInt(String(categoryData.state.version || "0"), 10)
                        )
                    }
                }

                ItemCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    itemsModel: root.itemsModel
                    selectedInventoryItemId: root.workspaceController ? root.workspaceController.selectedItemId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onInventoryItemSelected: function(itemId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectItem(itemId)
                        }
                    }

                    onEditRequested: function(itemData) {
                        if (itemData && itemData.id && root.workspaceController !== null) {
                            root.workspaceController.selectItem(itemData.id)
                        }
                        dialogHost.openEditItemDialog(itemData)
                    }

                    onToggleRequested: function(itemData) {
                        if (!itemData || !itemData.state || root.workspaceController === null) {
                            return
                        }
                        root.workspaceController.toggleItemActive(
                            String(itemData.state.itemId || ""),
                            parseInt(String(itemData.state.version || "0"), 10)
                        )
                    }
                }

                CategoryDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    categoryDetail: root.selectedCategoryModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEditRequested: dialogHost.openEditCategoryDialog(root.selectedCategoryModel)

                    onToggleRequested: {
                        var state = root.selectedCategoryModel && root.selectedCategoryModel.state
                            ? root.selectedCategoryModel.state
                            : {}
                        if (root.workspaceController !== null && state.categoryId) {
                            root.workspaceController.toggleCategoryActive(
                                String(state.categoryId || ""),
                                parseInt(String(state.version || "0"), 10)
                            )
                        }
                    }
                }

                ItemDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    itemDetail: root.selectedItemModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEditRequested: dialogHost.openEditItemDialog(root.selectedItemModel)

                    onToggleRequested: {
                        var state = root.selectedItemModel && root.selectedItemModel.state
                            ? root.selectedItemModel.state
                            : {}
                        if (root.workspaceController !== null && state.itemId) {
                            root.workspaceController.toggleItemActive(
                                String(state.itemId || ""),
                                parseInt(String(state.version || "0"), 10)
                            )
                        }
                    }

                    onLinkDocumentRequested: dialogHost.openLinkDocumentDialog(root.selectedItemModel)

                    onUnlinkDocumentRequested: function(documentData) {
                        var state = root.selectedItemModel && root.selectedItemModel.state
                            ? root.selectedItemModel.state
                            : {}
                        if (root.workspaceController !== null && state.itemId && documentData && documentData.value) {
                            root.workspaceController.unlinkDocument(
                                String(state.itemId || ""),
                                String(documentData.value || "")
                            )
                        }
                    }
                }
            }
        }
    }
}

