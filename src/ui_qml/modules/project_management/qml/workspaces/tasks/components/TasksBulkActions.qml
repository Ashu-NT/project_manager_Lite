pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    // ── Input properties ─────────────────────────────────────────────────
    property var workspaceController: null
    property var state: null
    property var bulkActionBar: bulkActionBarItem
    property var bulkChangePropertyPopup: bulkChangePropertyPopupItem

    // ── Signals ──────────────────────────────────────────────────────────
    signal cancelRequested()
    signal deleteRequested()
    signal changePropertyApplied(var payload)

    // ── Bulk Action Bar ──────────────────────────────────────────────────
    AppWidgets.BulkActionBar {
        id: bulkActionBarItem
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: Theme.AppTheme.spacingMd
        z: 10
        selectedCount: root.workspaceController ? root.workspaceController.selectedTaskCount : 0
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        actions: [
            { "id": "delete", "label": "Delete", "icon": "delete", "danger": true, "enabled": true },
            { "id": "change_property", "label": "Change Property", "icon": "edit", "danger": false, "enabled": true }
        ]

        onCancelRequested: {
            root.cancelRequested()
        }
        onActionTriggered: function(actionId) {
            if (actionId === "delete") {
                root.deleteRequested()
            } else if (actionId === "change_property") {
                bulkChangePropertyPopupItem.open()
            }
        }
    }

    // ── Bulk Change Property Popup ───────────────────────────────────────
    AppWidgets.BulkChangePropertyPopup {
        id: bulkChangePropertyPopupItem
        anchorItem: bulkActionBarItem.actionButtonForId("change_property")
        selectedCount: root.workspaceController ? root.workspaceController.selectedTaskCount : 0
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        properties: root.state ? root.state.bulkChangeProperties : []

        onApplyRequested: function(payload) {
            if (root.workspaceController === null) {
                return
            }
            if (payload.propertyId === "status") {
                root.workspaceController.applyBulkStatus({ "status": payload.value })
                root.changePropertyApplied(payload)
            }
        }
    }
}
