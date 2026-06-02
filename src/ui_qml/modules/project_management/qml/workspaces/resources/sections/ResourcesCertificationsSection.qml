pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var workspaceController: null
    property bool hasResource: false
    property bool canManageSkills: true
    property bool isBusy: false

    signal addCertificationRequested()
    signal removeCertificationRequested(string certId)

    readonly property var _certs: root.workspaceController
        ? (root.workspaceController.resourceCertifications || []) : []
    property string _selectedCertId: ""
    readonly property var _selectedCert: {
        const cid = root._selectedCertId
        if (!cid) return null
        const list = root._certs
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].id || "") === cid) return list[i]
        }
        return null
    }
    readonly property int _tableH: {
        const n = root._certs.length
        const rH = Theme.AppTheme.compactRowHeight
        const hH = Theme.AppTheme.normalRowHeight
        return n === 0 ? (hH + 80) : Math.min(hH + n * rH + 12, 300)
    }
    readonly property var _columns: [
        { key: "title",       label: "Certification", flex: 2,  sortable: false },
        { key: "subtitle",    label: "Code",          flex: 1,  sortable: false },
        { key: "statusLabel", label: "Status",        flex: 0,  minWidth: 110, type: "status" },
        { key: "metaText",    label: "Expiry",        flex: 1,  sortable: false }
    ]

    implicitHeight: _certsCol.implicitHeight

    ColumnLayout {
        id: _certsCol
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 0

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            visible: !root._selectedCertId
            title: "Certifications"
            subtitle: root._certs.length > 0 ? String(root._certs.length) : ""
            busy: root.isBusy
            createLabel: (root.hasResource && root.canManageSkills) ? "Add Certification" : ""
            actions: []
            onCreateRequested: root.addCertificationRequested()
        }

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            visible: Boolean(root._selectedCertId)
            showBack: true
            title: root._selectedCert ? String(root._selectedCert.title || "Certification") : "Certification"
            subtitle: root._selectedCert ? String(root._selectedCert.statusLabel || "") : ""
            busy: root.isBusy
            actions: [
                { id: "remove", label: "Remove", icon: "delete", enabled: true, danger: true }
            ]
            onBackRequested: root._selectedCertId = ""
            onActionTriggered: function(actionId) {
                if (actionId === "remove" && root._selectedCert)
                    root.removeCertificationRequested(String(root._selectedCert.id || ""))
            }
        }

        Item {
            Layout.fillWidth: true
            implicitHeight: root._tableH

            AppWidgets.DataTable {
                anchors.fill: parent
                columns: root._columns
                sourceModel: root.workspaceController ? root.workspaceController.resourceCertificationsTableModel : null
                selectedRowId: root._selectedCertId
                loading: root.isBusy
                emptyText: root.hasResource
                    ? "No certifications recorded for this resource."
                    : "Select a resource to view its certifications."
                onRowSelected: function(rowId) { root._selectedCertId = rowId }
                onRowActivated: function(rowId) { root._selectedCertId = rowId }
            }
        }
    }
}
