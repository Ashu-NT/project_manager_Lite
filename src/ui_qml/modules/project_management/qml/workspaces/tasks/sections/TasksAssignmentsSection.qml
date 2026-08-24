pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme

Item {
    id: root

    property var    assignmentsModel: AppMock.MockFactory.catalog()
    property var    assignmentsTableModel: null
    property string selectedAssignmentId: ""
    property bool   isBusy: false
    property bool   canCreate: false
    property var    projectResourceUsage: null
    property var    taskDetail: null
    property string errorText: ""
    property var workspaceController: null
    property real availableHeight: 0

    signal createRequested()
    signal assignmentSelected(string assignmentId)
    signal editAllocationRequested(var assignmentData)
    signal editPlannedHoursRequested(var assignmentData)
    signal deleteRequested(var assignmentData)
    signal acceptRequested(var assignmentData)
    signal declineRequested(var assignmentData)
    signal previewRequested(string projectResourceId, string taskId)
    signal retryRequested()
    signal manageProjectResourcesRequested()

    readonly property var _items: root.assignmentsModel.items || []
    function _itemForId(assignmentId) {
        const id = String(assignmentId || "")
        if (!id.length) return null
        const list = root._items
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].id || "") === id) return list[i]
        }
        return null
    }

    readonly property var _selectedItem: root._itemForId(root.selectedAssignmentId)
    readonly property var _selectedState: root._selectedItem
        ? (root._selectedItem.state || {})
        : ({})
    readonly property var _selectedActions: {
        if (!root._selectedItem) return []
        const actions = []
        if (root._selectedState.canAccept)
            actions.push({ "id": "accept", "label": "Accept", "icon": "approve" })
        if (root._selectedState.canDecline)
            actions.push({ "id": "decline", "label": "Decline", "icon": "close", "danger": true })
        if (actions.length === 0 && root._selectedState.canManage) {
            actions.push({ "id": "allocation", "label": "Edit Allocation", "icon": "edit" })
            actions.push({ "id": "plannedHours", "label": "Edit Planned Work", "icon": "time" })
            actions.push({ "id": "remove", "label": "Remove", "icon": "delete", "danger": true })
        }
        return actions
    }

    readonly property bool _capacityKnown: !!root._selectedState.capacityKnown
    readonly property string _capacityStatus: String(root._selectedState.capacityStatus || "UNKNOWN")
    readonly property string _taskPeriodLabel: {
        const fields = (root.taskDetail && root.taskDetail.fields) || []
        let start = "", finish = ""
        for (let i = 0; i < fields.length; i++) {
            if (fields[i].label === "Start") start = fields[i].value
            else if (fields[i].label === "Finish") finish = fields[i].value
        }
        if (!start && !finish) return "Not scheduled"
        return start + " – " + finish
    }
    readonly property var _taskPlanningRows: [
        { "label": "Task period", "value": root._taskPeriodLabel },
        { "label": "Allocation (%)", "value": String(root._selectedState.allocationPercent || "0") + "%" },
        { "label": "Available capacity", "value": root._capacityKnown
            ? String(root._selectedState.availableCapacityLabel || "")
            : "Capacity unavailable" },
        { "label": "Capacity committed", "value": String(root._selectedState.committedCapacityLabel || "") },
        { "label": "Planned work (h)", "value": String(root._selectedState.plannedHours || "0") + " h" },
        { "label": "Capacity headroom", "value": root._capacityKnown
            ? String(root._selectedState.capacityHeadroomLabel || "")
            : "Capacity unavailable" }
    ]
    readonly property var _executionRows: [
        { "label": "Actual logged", "value": String(root._selectedState.hoursLogged || "0") + " h" },
        { "label": "Remaining planned", "value": String(root._selectedState.remainingPlannedLabel || "0 h") }
    ]
    readonly property var _projectResourceRows: {
        const u = root.projectResourceUsage
        if (!u || !u.projectResourceId) return []
        return [
            { "label": "Project planned hours", "value": String(u.plannedHoursLabel || "") },
            { "label": "Distributed to tasks", "value": String(u.allocatedToTasksHoursLabel || "") },
            { "label": "Unallocated", "value": String(u.unallocatedPlannedHoursLabel || "") },
            { "label": "Actual worked", "value": String(u.actualHoursLabel || "") },
            { "label": "Remaining vs plan", "value": String(u.remainingProjectHoursLabel || "") }
        ]
    }
    readonly property bool _showOverCapacityWarning: root._capacityStatus === "OVER_CAPACITY"
    readonly property string _overCapacityMessage: {
        if (!root._showOverCapacityWarning) return ""
        const peak = root._selectedState.peakUtilizationPercent
        return "Resource is overallocated during part of this task period."
            + (root._capacityKnown ? " Peak utilization: " + Number(peak).toFixed(0) + "%" : "")
    }

    readonly property var _columns: [
        { key: "resourceName", label: "Resource", flex: 2, minWidth: 160, sortable: true },
        { key: "resourceCode", label: "Code", flex: 0, minWidth: 85, sortable: true },
        { key: "role", label: "Role", flex: 1.2, minWidth: 110, sortable: true },
        { key: "allocationPercent", label: "Allocation", flex: 0, minWidth: 95, sortable: true },
        { key: "plannedHours", label: "Planned", flex: 0, minWidth: 90, sortable: true },
        { key: "actualHours", label: "Actual", flex: 0, minWidth: 85, sortable: true },
        { key: "remainingHours", label: "Remaining", flex: 0, minWidth: 95, sortable: true },
        { key: "responseStatus", label: "Response", flex: 0, minWidth: 100, type: "status", sortable: true }
    ]
    readonly property int _tableH: Math.max(
        120,
        Theme.AppTheme.normalRowHeight
            + Math.max(root._items.length, 1) * Theme.AppTheme.compactRowHeight
            + 1
    )

    implicitHeight: Math.max(_col.implicitHeight, root.availableHeight)

    ColumnLayout {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: root.implicitHeight
        spacing: 0

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Assignments"
            subtitle: root._items.length > 0
                ? (root._items.length === 1 ? "1 resource" : root._items.length + " resources")
                : ""
            busy: root.isBusy
            createLabel: root.canCreate ? "Assign Resource" : ""
            actions: [{ "id": "refresh", "label": "Refresh", "icon": "refresh" }]
            onCreateRequested: root.createRequested()
            onActionTriggered: function(actionId) {
                if (actionId === "refresh") root.retryRequested()
            }
        }

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: String(root.assignmentsModel.searchText || "")
            searchPlaceholder: "Search resource, code, or role..."
            showFilter: false
            showRefresh: true
            isBusy: root.isBusy
            onSearchChanged: function(text) { if (root.workspaceController) root.workspaceController.setTaskAssignmentsSearch(text) }
            onRefreshRequested: root.retryRequested()
            AppControls.ComboBox {
                implicitWidth: 130; textRole: "label"
                model: [{"value":"all","label":"All responses"},{"value":"pending","label":"Pending"},
                        {"value":"accepted","label":"Accepted"},{"value":"declined","label":"Declined"}]
                onActivated: function(index) { if (root.workspaceController) root.workspaceController.setTaskAssignmentsResponse(String(model[index].value)) }
            }
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.errorText.length > 0
            tone: "danger"
            message: root.errorText
            actionLabel: "Retry"
            onActionClicked: root.retryRequested()
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: Math.max(
                root._tableH + assignmentPagination.implicitHeight,
                _inspector.visible ? _inspector.implicitHeight : 0
            )
            spacing: Theme.AppTheme.spacingMd

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                AppWidgets.DataTable {
                    anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: assignmentPagination.top
                    columns: root._columns
                    sourceModel: root.assignmentsTableModel
                    selectedRowId: root.selectedAssignmentId
                    loading: root.isBusy
                    sortingMode: "server"
                    sortKey: String(root.assignmentsModel.sortKey || "resourceName")
                    sortDirection: root.assignmentsModel.sortDirection === "desc" ? Qt.DescendingOrder : Qt.AscendingOrder
                    emptyText: root.assignmentsModel.emptyState || "No assignments match."

                    onRowSelected: function(rowId) {
                        root.assignmentSelected(rowId)
                        const item = root._itemForId(rowId)
                        const state = item ? (item.state || {}) : {}
                        root.previewRequested(
                            String(state.projectResourceId || ""),
                            String(state.taskId || "")
                        )
                    }
                    onRowActivated: function(rowId) {
                        root.assignmentSelected(rowId)
                        const item = root._itemForId(rowId)
                        const state = item ? (item.state || {}) : {}
                        root.previewRequested(
                            String(state.projectResourceId || ""),
                            String(state.taskId || "")
                        )
                    }
                    onSortRequested: function(key, direction) { root.workspaceController.setTaskAssignmentsSort(key, direction) }
                }

                AppWidgets.TablePaginationBar {
                    id: assignmentPagination
                    anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                    currentPage: Number(root.assignmentsModel.page || 1); pageSize: Number(root.assignmentsModel.pageSize || 25)
                    totalItems: Number(root.assignmentsModel.total || 0); busy: root.isBusy
                    onPageRequested: function(page) { root.workspaceController.setTaskAssignmentsPage(page) }
                    onPageSizeRequested: function(size) { root.workspaceController.setTaskAssignmentsPageSize(size) }
                }
            }

            AppWidgets.InspectorPanel {
                id: _inspector
                Layout.fillHeight: true
                visible: root._selectedItem !== null
                Layout.preferredWidth: visible ? Theme.AppTheme.inspectorWidth : 0
                title: root._selectedItem ? String(root._selectedItem.title || "") : ""
                statusLabel: String(root._selectedState.capacityStatusLabel || "")
                showEditAction: false
                showSecondaryAction: false

            onCloseRequested: root.assignmentSelected("")

            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                visible: root._showOverCapacityWarning
                tone: "danger"
                message: "⚠ " + root._overCapacityMessage
            }

            AppControls.Label {
                text: "TASK PLANNING"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
            }

            Repeater {
                model: root._taskPlanningRows
                delegate: ColumnLayout {
                    id: _tpRow
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 2
                    visible: String(_tpRow.modelData.value || "").length > 0
                    AppControls.Label {
                        text: String(_tpRow.modelData.label || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeMetadataSize
                    }
                    AppControls.Label {
                        Layout.fillWidth: true
                        text: String(_tpRow.modelData.value || "")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                        font.bold: true
                        wrapMode: Text.WrapAtWordBoundaryOrAnywhere
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.topMargin: 2
                height: Theme.AppTheme.borderWidthThin
                color: Theme.AppTheme.divider
            }

            AppControls.Label {
                text: "EXECUTION"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
            }

            Repeater {
                model: root._executionRows
                delegate: ColumnLayout {
                    id: _exRow
                    required property var modelData
                    Layout.fillWidth: true
                    spacing: 2
                    AppControls.Label {
                        text: String(_exRow.modelData.label || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeMetadataSize
                    }
                    AppControls.Label {
                        Layout.fillWidth: true
                        text: String(_exRow.modelData.value || "")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                        font.bold: true
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: root._projectResourceRows.length > 0
                spacing: Theme.AppTheme.spacingSm

                Rectangle {
                    Layout.fillWidth: true
                    Layout.topMargin: 2
                    Layout.preferredHeight: Theme.AppTheme.borderWidthThin
                    color: Theme.AppTheme.divider
                }

                AppControls.Label {
                    text: "PROJECT RESOURCE CONTEXT"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }

                Repeater {
                    model: root._projectResourceRows
                    delegate: ColumnLayout {
                        id: _prRow
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label {
                            text: String(_prRow.modelData.label || "")
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.typeMetadataSize
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_prRow.modelData.value || "")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                            font.bold: true
                        }
                    }
                }

                AppControls.SecondaryButton {
                    Layout.fillWidth: true
                    text: "Manage Project Resources"
                    iconName: "resource"
                    onClicked: root.manageProjectResourcesRequested()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.topMargin: 2
                height: Theme.AppTheme.borderWidthThin
                color: Theme.AppTheme.divider
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Repeater {
                    model: root._selectedActions
                    delegate: AppControls.SecondaryButton {
                        id: _actionBtn
                        required property var modelData
                        Layout.fillWidth: true
                        text: String(_actionBtn.modelData.label || "")
                        iconName: String(_actionBtn.modelData.icon || "")
                        danger: !!_actionBtn.modelData.danger
                        onClicked: {
                            const actionId = _actionBtn.modelData.id
                            if (actionId === "accept") root.acceptRequested(root._selectedItem)
                            else if (actionId === "decline") root.declineRequested(root._selectedItem)
                            else if (actionId === "allocation") root.editAllocationRequested(root._selectedItem)
                            else if (actionId === "plannedHours") root.editPlannedHoursRequested(root._selectedItem)
                            else if (actionId === "remove") root.deleteRequested(root._selectedItem)
                        }
                    }
                }
            }
            }
        }
    }
}
