pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import "../inventory/dialogs" as InventoryDlgs
import "panels" as Panels
import "components" as Components

AppLayouts.WorkspaceFrame {
    id: root

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementInventoryWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.inventoryWorkspace
        : null

    readonly property var storeroomsModel: root.workspaceController
        ? root.workspaceController.storerooms
        : ({ "items": [], "emptyState": "No storerooms configured." })
    readonly property var foundationModel: root.workspaceController
        ? root.workspaceController.foundation
        : ({ "locations": [], "locationTypeOptions": [] })
    readonly property var selectedStoreroomModel: root.workspaceController
        ? root.workspaceController.selectedStoreroom
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "fields": [], "state": {} })

    readonly property string _selectedLocationId: root.workspaceController ? root.workspaceController.selectedLocationId : ""
    readonly property var _selectedLocationRow: {
        const id = root._selectedLocationId
        if (!id) return null
        const locs = root.foundationModel.locations || []
        for (let i = 0; i < locs.length; i++) {
            if (String(locs[i].id || "") === id) return locs[i]
        }
        return null
    }
    readonly property var _selectedLocationFields: {
        const row = root._selectedLocationRow
        if (!row) return []
        return [
            row.title          ? { "label": "Location", "value": row.title }         : null,
            row.statusLabel    ? { "label": "Type",      "value": row.statusLabel }   : null,
            row.subtitle       ? { "label": "Storeroom", "value": row.subtitle }      : null,
            row.supportingText ? { "label": "Details",   "value": row.supportingText } : null,
            row.metaText       ? { "label": "Active",    "value": row.metaText }      : null
        ].filter(Boolean)
    }

    title:    "Warehouses & Locations"
    subtitle: "Storerooms, storage zones, bins, and sub-locations across all sites."

    // ── Detail state ───────────────────────────────────────────────────
    property bool _detailOpen: false
    property int  _pendingDetailSection: 0
    readonly property var _detailPage: _detailPageLoader.item

    // isStoreroomsView is driven by the list page's internal state — expose via ref
    property bool _isStoreroomsView: true

    readonly property var _detailActions: {
        const idx = root._detailPage ? root._detailPage.activeSectionIndex : 0
        if (idx !== 0) return []
        if (root._isStoreroomsView) {
            const detail   = root.selectedStoreroomModel
            const isActive = detail && detail.state && detail.state.isActive
            return [
                { "id": "edit",   "label": "Edit",                               "icon": "edit",                          "enabled": true, "danger": false },
                { "id": "toggle", "label": isActive ? "Deactivate" : "Activate", "icon": isActive ? "reject" : "approve", "enabled": true, "danger": false }
            ]
        }
        const row      = root._selectedLocationRow
        const isActive = row && row.state && row.state.isActive
        return [
            { "id": "edit_location",   "label": "Edit",                               "icon": "edit",                          "enabled": true, "danger": false },
            { "id": "toggle_location", "label": isActive ? "Deactivate" : "Activate", "icon": isActive ? "reject" : "approve", "enabled": true, "danger": false }
        ]
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (root._detailPage) root._detailPage.scrollToSection(sectionIndex)
    }

    // ── Dialog host ────────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            InventoryDlgs.InventoryDialogHost {
                siteOptions:            root.workspaceController ? (root.workspaceController.siteOptions            || []) : []
                storeroomStatusOptions: root.workspaceController ? (root.workspaceController.storeroomStatusOptions || []) : []
                managerPartyOptions:    root.workspaceController ? (root.workspaceController.managerPartyOptions    || []) : []
                itemOptions:            root.workspaceController ? (root.workspaceController.itemOptions            || []) : []
                storeroomOptions:       root.workspaceController ? (root.workspaceController.storeroomOptions       || []) : []
                workspaceController:    root.workspaceController
            }
        }
    }

    // ── Stacked list / detail ──────────────────────────────────────────
    Item {
        anchors.fill: parent

        Item {
            anchors.fill: parent
            visible: !root._detailOpen || _detailPageLoader.status !== Loader.Ready

            Components.WarehousesListPage {
                id: _listPage
                anchors.fill:           parent
                workspaceController:    root.workspaceController
                storeroomsModel:        root.storeroomsModel
                foundationModel:        root.foundationModel
                selectedLocationId:     root._selectedLocationId
                detailOpen:             root._detailOpen

                onRowActivated: {
                    root._isStoreroomsView = _listPage.isStoreroomsView
                    root._openDetail(0)
                }
                onCreateStoreroomRequested: dialogHostLoader.invoke("openCreateStoreroomDialog")
                onCreateLocationRequested:  function(filter) { dialogHostLoader.invoke("openCreateLocationDialog", filter) }
            }
        }

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
                sections:    ["Overview", "Activity"]
                z:           20
                Component.onCompleted: scrollToSection(root._pendingDetailSection)

                AppWidgets.ContextualActionToolbar {
                    width:    parent ? parent.width : 0
                    showBack: true
                    title:    root._isStoreroomsView
                        ? (root.selectedStoreroomModel.title || "Storeroom Detail")
                        : (root._selectedLocationRow ? (root._selectedLocationRow.title || "Location Detail") : "Location Detail")
                    subtitle: root._isStoreroomsView
                        ? (root.selectedStoreroomModel.statusLabel || root.selectedStoreroomModel.subtitle || "")
                        : (root._selectedLocationRow ? (root._selectedLocationRow.statusLabel || "") : "")
                    busy:    root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions
                    onBackRequested: { root._detailOpen = false }
                    onActionTriggered: function(actionId) {
                        if (actionId === "edit") {
                            dialogHostLoader.invoke("openEditStoreroomDialog", root.selectedStoreroomModel)
                        } else if (actionId === "toggle") {
                            const s = root.selectedStoreroomModel.state || {}
                            if (root.workspaceController !== null && s.storeroomId)
                                root.workspaceController.toggleStoreroomActive(String(s.storeroomId || ""), parseInt(String(s.version || "0"), 10))
                        } else if (actionId === "edit_location") {
                            dialogHostLoader.invoke("openEditLocationDialog", root._selectedLocationRow || {})
                        } else if (actionId === "toggle_location") {
                            const row = root._selectedLocationRow
                            const st  = row ? (row.state || {}) : {}
                            if (root.workspaceController !== null && st.locationId)
                                root.workspaceController.updateLocation({ "locationId": String(st.locationId || ""), "version": parseInt(String(st.version || "0"), 10), "isActive": !st.isActive })
                        }
                    }
                }

                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0; tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : "" }
                AppWidgets.InlineMessage { width: parent ? parent.width : 0; visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0 && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : "" }

                Panels.WarehousesDetailPanel {
                    width:             parent ? parent.width : 0
                    detailPage:        root._detailPage
                    isStoreroomsView:  root._isStoreroomsView
                    storeroomFields:   root.selectedStoreroomModel.fields || []
                    locationFields:    root._selectedLocationFields
                }
            }
        }
    }
}
