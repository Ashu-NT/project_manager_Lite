pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import "../../inventory/panels"

Item {
    id: root

    // ── Inputs ────────────────────────────────────────────────────────────
    property var detailPage: null
    property bool isStockView: true
    property var stockSignalDetail:    ({ "id": "", "fields": [], "emptyState": "Select a row to view details." })
    property var supplierPricingDetail: ({ "id": "", "fields": [], "emptyState": "Select a row to view details." })
    property var activityItems: []

    readonly property var _activeDetail: root.isStockView ? root.stockSignalDetail : root.supplierPricingDetail

    width:          parent ? parent.width : 0
    implicitHeight: _panel.implicitHeight

    InventoryDetailPanel {
        id: _panel
        anchors.left:  parent.left
        anchors.right: parent.right
        detailPage:    root.detailPage
        fields:        root._activeDetail.fields || []
        activityItems: root.activityItems
        emptyState:    root._activeDetail.emptyState || "Select a row to view details."
    }
}
