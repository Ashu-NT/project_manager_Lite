pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var workspaceController: null
    property bool hasResource: false
    property bool canManageSkills: false
    property bool isBusy: false
    property real availableHeight: 0
    property string _selectedCertId: ""

    signal addCertificationRequested()
    signal removeCertificationRequested(string certId)
    signal selectionChanged(string certId)

    function _value(model, index) {
        const item = model[index]
        return item ? String(item.value || "all") : "all"
    }

    function _indexForValue(model, value) {
        const expected = String(value || "all").toLowerCase()
        for (let index = 0; index < model.length; index += 1) {
            if (String(model[index].value || "").toLowerCase() === expected) return index
        }
        return 0
    }

    function clearSelection() {
        if (!root._selectedCertId.length) return
        root._selectedCertId = ""
        root.selectionChanged("")
    }

    implicitHeight: Math.max(content.implicitHeight, root.availableHeight)

    ColumnLayout {
        id: content
        width: parent.width
        height: root.implicitHeight
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Certifications"
            subtitle: root.workspaceController
                ? String(root.workspaceController.resourceCertificationsTotal || 0) : "0"
            busy: root.isBusy
            createLabel: root.hasResource && root.canManageSkills
                ? "Add Certification" : ""
            actions: []
            onCreateRequested: root.addCertificationRequested()
        }

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: root.workspaceController
                ? root.workspaceController.resourceCertificationsSearch : ""
            searchPlaceholder: "Search certification, code, issuer, or number..."
            showFilter: false
            showRefresh: true
            isBusy: root.isBusy
            onSearchChanged: function(text) {
                if (root.workspaceController)
                    root.workspaceController.setResourceCertificationsSearch(text)
            }
            onRefreshRequested: {
                if (root.workspaceController)
                    root.workspaceController.refreshResourceCertifications()
            }

            AppControls.ComboBox {
                id: statusFilter
                implicitWidth: 155
                model: [
                    { "value": "all", "label": "All statuses" },
                    { "value": "valid", "label": "Valid" },
                    { "value": "expiring-soon", "label": "Expiring soon" },
                    { "value": "expired", "label": "Expired" },
                    { "value": "no-expiry", "label": "No expiry" }
                ]
                textRole: "label"
                currentIndex: root._indexForValue(
                    model,
                    root.workspaceController
                        ? root.workspaceController.resourceCertificationsStatus : "all"
                )
                onActivated: function(index) {
                    if (root.workspaceController) {
                        root.workspaceController.setResourceCertificationsStatus(
                            root._value(model, index)
                        )
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 300

            AppWidgets.DataTable {
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: pagination.top
                columns: [
                    { "key": "certificationName", "label": "Certification", "flex": 2, "minWidth": 190, "sortable": true },
                    { "key": "certificationCode", "label": "Code", "flex": 1, "minWidth": 105, "sortable": true },
                    { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 125, "type": "status", "sortable": true },
                    { "key": "issuedDate", "label": "Issued", "flex": 0, "minWidth": 110, "sortable": true },
                    { "key": "expiryDate", "label": "Expiry", "flex": 0, "minWidth": 110, "sortable": true },
                    { "key": "issuer", "label": "Issuer", "flex": 1.4, "minWidth": 135, "sortable": true }
                ]
                sourceModel: root.workspaceController
                    ? root.workspaceController.resourceCertificationsTableModel : null
                sortingMode: "server"
                sortKey: root.workspaceController
                    ? root.workspaceController.resourceCertificationsSortKey
                    : "certificationName"
                sortDirection: root.workspaceController
                    ? root.workspaceController.resourceCertificationsSortDirection
                    : Qt.AscendingOrder
                selectedRowId: root._selectedCertId
                loading: root.isBusy
                emptyText: root.hasResource
                    ? "No certifications match the selected filters."
                    : "Select a resource to view its certifications."
                onRowSelected: function(rowId) {
                    root._selectedCertId = rowId
                    root.selectionChanged(rowId)
                }
                onRowActivated: function(rowId) {
                    root._selectedCertId = rowId
                    root.selectionChanged(rowId)
                }
                onSortRequested: function(key, direction) {
                    if (root.workspaceController)
                        root.workspaceController.setResourceCertificationsSort(key, direction)
                }
            }

            AppWidgets.TablePaginationBar {
                id: pagination
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                currentPage: root.workspaceController
                    ? root.workspaceController.resourceCertificationsPage : 1
                pageSize: root.workspaceController
                    ? root.workspaceController.resourceCertificationsPageSize : 25
                totalItems: root.workspaceController
                    ? root.workspaceController.resourceCertificationsTotal : 0
                busy: root.isBusy
                onPageRequested: function(page) {
                    if (root.workspaceController)
                        root.workspaceController.setResourceCertificationsPage(page)
                }
                onPageSizeRequested: function(size) {
                    if (root.workspaceController)
                        root.workspaceController.setResourceCertificationsPageSize(size)
                }
            }
        }
    }
}
