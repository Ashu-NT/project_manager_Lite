pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var changes: ({ "items": [] })
    property var impacts: ({ "items": [] })
    property var selectedChange: ({ "id": "", "fields": [] })
    property var changesTableModel: null
    property var impactsTableModel: null
    property string selectedChangeId: ""
    property string changeSortKey: "metaText"
    property int changeSortDirection: Qt.DescendingOrder
    property string impactSortKey: "metaText"
    property int impactSortDirection: Qt.AscendingOrder
    property string changeSearch: ""
    property string changeStatus: ""
    property string changeApprovalStatus: ""
    property string changeAppliedState: ""
    property string impactSearch: ""
    property string impactType: ""
    property string impactAppliedState: ""
    property bool busy: false
    property bool canCreate: false
    property string selectedImpactId: ""

    readonly property var selectedChangeState: root.selectedChange
        ? (root.selectedChange.state || {}) : ({})
    readonly property var selectedImpact: {
        const rows = root.impacts.items || []
        for (let index = 0; index < rows.length; index += 1) {
            if (String(rows[index].id || "") === root.selectedImpactId) return rows[index]
        }
        return null
    }

    signal changeSelected(string changeId)
    signal changePageRequested(int page)
    signal impactPageRequested(int page)
    signal changeSortRequested(string key, int direction)
    signal impactSortRequested(string key, int direction)
    signal changeFiltersRequested(string search, string status, string approvalStatus, string appliedState)
    signal impactFiltersRequested(string search, string impactType, string appliedState)
    signal requestCreateRequested()
    signal requestEditRequested(var change)
    signal requestLifecycleRequested(string action, var change)
    signal impactCreateRequested(var change)
    signal impactEditRequested(var change, var impact)
    signal impactRemoveRequested(var change, var impact)

    readonly property var _changeColumns: [
        { "key": "title", "label": "Change Request", "flex": 1.7, "sortable": true },
        { "key": "statusLabel", "label": "Status", "minWidth": 125, "flex": 0, "sortable": true },
        { "key": "subtitle", "label": "Revision / effective", "flex": 1.35, "sortable": true },
        { "key": "supportingText", "label": "Governance / impacts", "flex": 1.55, "sortable": true },
        { "key": "metaText", "label": "Timeline", "flex": 1.25, "sortable": true }
    ]
    readonly property var _impactColumns: [
        { "key": "title", "label": "Impact", "flex": 1.7, "sortable": true },
        { "key": "statusLabel", "label": "Type", "minWidth": 105, "flex": 0, "sortable": true },
        { "key": "subtitle", "label": "Change", "flex": 1.15, "sortable": true },
        { "key": "supportingText", "label": "Target", "flex": 1.6, "sortable": true },
        { "key": "metaText", "label": "Applied result", "flex": 1.45, "sortable": true }
    ]
    readonly property var _changeStatuses: [
        { "value": "", "label": "All statuses" },
        { "value": "draft", "label": "Draft" },
        { "value": "pending_approval", "label": "Pending Approval" },
        { "value": "applied", "label": "Applied" },
        { "value": "rejected", "label": "Rejected" }
    ]
    readonly property var _approvalStatuses: [
        { "value": "", "label": "All approvals" },
        { "value": "pending", "label": "Pending" },
        { "value": "approved", "label": "Approved" },
        { "value": "rejected", "label": "Rejected" }
    ]
    readonly property var _appliedStates: [
        { "value": "", "label": "Any apply state" },
        { "value": "applied", "label": "Applied" },
        { "value": "not_applied", "label": "Not Applied" }
    ]
    readonly property var _impactTypes: [
        { "value": "", "label": "All impact types" },
        { "value": "budget", "label": "Budget" },
        { "value": "forecast", "label": "Forecast" },
        { "value": "schedule", "label": "Schedule" }
    ]

    function _indexOf(model, value) {
        for (let index = 0; index < model.length; index += 1) {
            if (String(model[index].value) === String(value || "")) return index
        }
        return 0
    }

    function _changeFilters() {
        const status = root._changeStatuses[changeStatusFilter.currentIndex]
        const approval = root._approvalStatuses[approvalStatusFilter.currentIndex]
        const applied = root._appliedStates[changeAppliedFilter.currentIndex]
        root.changeFiltersRequested(root.changeSearch,
                                    status ? String(status.value) : "",
                                    approval ? String(approval.value) : "",
                                    applied ? String(applied.value) : "")
    }

    function _impactFilters() {
        const type = root._impactTypes[impactTypeFilter.currentIndex]
        const applied = root._appliedStates[impactAppliedFilter.currentIndex]
        root.impactFiltersRequested(root.impactSearch,
                                    type ? String(type.value) : "",
                                    applied ? String(applied.value) : "")
    }

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Change Requests" }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm
            leftPadding: Theme.AppTheme.spacingMd
            rightPadding: Theme.AppTheme.spacingMd

            AppControls.SecondaryButton {
                visible: root.canCreate
                enabled: !root.busy
                text: "Create Change Request"
                iconName: "add"
                onClicked: root.requestCreateRequested()
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedChangeState.canEdit)
                enabled: !root.busy
                text: "Edit"
                iconName: "edit"
                onClicked: root.requestEditRequested(root.selectedChange)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedChangeState.canSubmit)
                enabled: !root.busy
                text: "Submit"
                iconName: "approve"
                onClicked: root.requestLifecycleRequested("submit", root.selectedChange)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedChangeState.canApprove)
                enabled: !root.busy
                text: "Approve & Apply"
                iconName: "approve"
                onClicked: root.requestLifecycleRequested("approve", root.selectedChange)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedChangeState.canReject)
                enabled: !root.busy
                text: "Reject"
                iconName: "reject"
                onClicked: root.requestLifecycleRequested("reject", root.selectedChange)
            }
        }

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: root.changeSearch
            searchPlaceholder: "Search title, reason, requester, or approval..."
            showFilter: false
            showRefresh: false
            isBusy: root.busy
            onSearchChanged: function(text) {
                const status = root._changeStatuses[changeStatusFilter.currentIndex]
                const approval = root._approvalStatuses[approvalStatusFilter.currentIndex]
                const applied = root._appliedStates[changeAppliedFilter.currentIndex]
                root.changeFiltersRequested(text,
                                            status ? String(status.value) : "",
                                            approval ? String(approval.value) : "",
                                            applied ? String(applied.value) : "")
            }
            AppControls.ComboBox {
                id: changeStatusFilter
                implicitWidth: 150
                textRole: "label"
                model: root._changeStatuses
                currentIndex: root._indexOf(root._changeStatuses, root.changeStatus)
                onActivated: root._changeFilters()
            }
            AppControls.ComboBox {
                id: approvalStatusFilter
                implicitWidth: 145
                textRole: "label"
                model: root._approvalStatuses
                currentIndex: root._indexOf(root._approvalStatuses, root.changeApprovalStatus)
                onActivated: root._changeFilters()
            }
            AppControls.ComboBox {
                id: changeAppliedFilter
                implicitWidth: 150
                textRole: "label"
                model: root._appliedStates
                currentIndex: root._indexOf(root._appliedStates, root.changeAppliedState)
                onActivated: root._changeFilters()
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: (root.changes.items || []).length === 0
            title: "No Change Requests"
            message: root.changes.emptyState || "No Change Requests match the current filters."
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 270
            visible: (root.changes.items || []).length > 0
            AppWidgets.DataTable {
                objectName: "financialChangesTable"
                anchors.fill: parent
                columns: root._changeColumns
                sourceModel: root.changesTableModel
                sortingMode: "server"
                sortKey: root.changeSortKey
                sortDirection: root.changeSortDirection
                selectedRowId: root.selectedChangeId
                loading: root.busy
                emptyText: root.changes.emptyState || "No Change Requests."
                onRowSelected: function(rowId) {
                    root.selectedImpactId = ""
                    root.changeSelected(String(rowId || ""))
                }
                onSortRequested: function(key, direction) { root.changeSortRequested(key, direction) }
            }
        }

        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: Number(root.changes.total || 0) > Number(root.changes.pageSize || 50)
            currentPage: Number(root.changes.page || 1)
            pageSize: Number(root.changes.pageSize || 50)
            totalItems: Number(root.changes.total || 0)
            busy: root.busy
            onPageRequested: function(page) { root.changePageRequested(page) }
        }

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            visible: String(root.selectedChange.id || "").length > 0
            title: root.selectedChange.title || "Selected Change Request"
            ColumnLayout {
                width: parent ? parent.width : 0
                spacing: Theme.AppTheme.spacingMd
                AppControls.Label {
                    Layout.fillWidth: true
                    Layout.margins: Theme.AppTheme.spacingMd
                    visible: String(root.selectedChange.description || "").length > 0
                    text: String(root.selectedChange.description || "")
                    wrapMode: Text.WordWrap
                    color: Theme.AppTheme.textMuted
                }
                GridLayout {
                    Layout.fillWidth: true
                    columns: width >= 900 ? 3 : (width >= 560 ? 2 : 1)
                    columnSpacing: Theme.AppTheme.spacingLg
                    rowSpacing: Theme.AppTheme.spacingSm
                    Repeater {
                        model: root.selectedChange.fields || []
                        delegate: ColumnLayout {
                            id: detailField
                            required property var modelData
                            Layout.fillWidth: true
                            Layout.margins: Theme.AppTheme.spacingMd
                            AppControls.Label { Layout.fillWidth: true; text: String(detailField.modelData.label || ""); color: Theme.AppTheme.textMuted }
                            AppControls.Label { Layout.fillWidth: true; text: String(detailField.modelData.value || "-"); font.bold: true; wrapMode: Text.WordWrap }
                            AppControls.Label { Layout.fillWidth: true; visible: String(detailField.modelData.supportingText || "").length > 0; text: String(detailField.modelData.supportingText || ""); color: Theme.AppTheme.textMuted; wrapMode: Text.WordWrap }
                        }
                    }
                }
            }
        }

        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Selected Change Impacts" }

        Flow {
            Layout.fillWidth: true
            visible: root.selectedChangeId.length > 0
            spacing: Theme.AppTheme.spacingSm
            leftPadding: Theme.AppTheme.spacingMd
            rightPadding: Theme.AppTheme.spacingMd

            AppControls.SecondaryButton {
                visible: Boolean(root.selectedChangeState.canAddImpact)
                enabled: !root.busy
                text: "Add Impact"
                iconName: "add"
                onClicked: root.impactCreateRequested(root.selectedChange)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedImpact
                    && root.selectedImpact.state
                    && root.selectedImpact.state.canEdit)
                enabled: !root.busy
                text: "Edit Impact"
                iconName: "edit"
                onClicked: root.impactEditRequested(root.selectedChange, root.selectedImpact)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedImpact
                    && root.selectedImpact.state
                    && root.selectedImpact.state.canRemove)
                enabled: !root.busy
                text: "Remove Impact"
                iconName: "delete"
                onClicked: root.impactRemoveRequested(root.selectedChange, root.selectedImpact)
            }
        }

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            visible: root.selectedChangeId.length > 0
            searchText: root.impactSearch
            searchPlaceholder: "Search impact, cost code, task, or applied reference..."
            showFilter: false
            showRefresh: false
            isBusy: root.busy
            onSearchChanged: function(text) {
                const type = root._impactTypes[impactTypeFilter.currentIndex]
                const applied = root._appliedStates[impactAppliedFilter.currentIndex]
                root.impactFiltersRequested(text,
                                            type ? String(type.value) : "",
                                            applied ? String(applied.value) : "")
            }
            AppControls.ComboBox {
                id: impactTypeFilter
                implicitWidth: 165
                textRole: "label"
                model: root._impactTypes
                currentIndex: root._indexOf(root._impactTypes, root.impactType)
                onActivated: root._impactFilters()
            }
            AppControls.ComboBox {
                id: impactAppliedFilter
                implicitWidth: 150
                textRole: "label"
                model: root._appliedStates
                currentIndex: root._indexOf(root._appliedStates, root.impactAppliedState)
                onActivated: root._impactFilters()
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: root.selectedChangeId.length === 0 || (root.impacts.items || []).length === 0
            title: root.selectedChangeId.length === 0 ? "Select a Change Request" : "No Impacts"
            message: root.selectedChangeId.length === 0
                ? "Choose a Change Request above to load its typed impact evidence."
                : (root.impacts.emptyState || "No impacts match the current filters.")
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 290
            visible: root.selectedChangeId.length > 0 && (root.impacts.items || []).length > 0
            AppWidgets.DataTable {
                objectName: "financialChangeImpactsTable"
                anchors.fill: parent
                columns: root._impactColumns
                sourceModel: root.impactsTableModel
                sortingMode: "server"
                sortKey: root.impactSortKey
                sortDirection: root.impactSortDirection
                selectedRowId: root.selectedImpactId
                loading: root.busy
                emptyText: root.impacts.emptyState || "No impacts."
                onSortRequested: function(key, direction) { root.impactSortRequested(key, direction) }
                onRowSelected: function(rowId) {
                    root.selectedImpactId = String(rowId || "")
                }
            }
        }

        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: root.selectedChangeId.length > 0
                && Number(root.impacts.total || 0) > Number(root.impacts.pageSize || 50)
            currentPage: Number(root.impacts.page || 1)
            pageSize: Number(root.impacts.pageSize || 50)
            totalItems: Number(root.impacts.total || 0)
            busy: root.busy
            onPageRequested: function(page) { root.impactPageRequested(page) }
        }
    }
}
