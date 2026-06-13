pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var workspaceController: null
    property bool hasResource: false
    property bool canManageSkills: true
    property bool isBusy: false

    signal addCertificationRequested()
    signal removeCertificationRequested(string certId)
    signal selectionChanged(string certId)

    readonly property var _certs: root.workspaceController
        ? (root.workspaceController.resourceCertifications || []) : []
    property string _selectedCertId: ""
    readonly property int _tableH: {
        const n = root._certs.length
        const rH = Theme.AppTheme.compactRowHeight
        const hH = Theme.AppTheme.normalRowHeight
        return n === 0 ? (hH + 80) : Math.min(hH + n * rH + 12, 300)
    }
    readonly property var _columns: [
        { key: "title",       label: "Certification", flex: 2, sortable: false },
        { key: "subtitle",    label: "Code",          flex: 1, sortable: false },
        { key: "statusLabel", label: "Status",        flex: 0, minWidth: 110, type: "status" },
        { key: "metaText",    label: "Expiry",        flex: 1, sortable: false }
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
            title: "Certifications"
            subtitle: root._certs.length > 0 ? String(root._certs.length) : ""
            busy: root.isBusy
            createLabel: (root.hasResource && root.canManageSkills) ? "Add Certification" : ""
            actions: []
            onCreateRequested: root.addCertificationRequested()
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
                onRowSelected: function(rowId) {
                    root._selectedCertId = rowId
                    root.selectionChanged(root._selectedCertId)
                }
                onRowActivated: function(rowId) {
                    root._selectedCertId = rowId
                    root.selectionChanged(root._selectedCertId)
                }
            }
        }
    }
}
