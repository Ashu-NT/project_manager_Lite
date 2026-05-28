pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme

Item {
    id: root

    property var    assignmentsModel:     AppMock.MockFactory.catalog()
    property string selectedAssignmentId: ""
    property bool   isBusy:              false
    property bool   canCreate:           false
    property var    assignmentPreview:   null

    signal createRequested()
    signal assignmentSelected(string assignmentId)
    signal editAllocationRequested(var assignmentData)
    signal setHoursRequested(var assignmentData)
    signal deleteRequested(var assignmentData)
    signal previewRequested(string projectResourceId, string taskId)

    readonly property bool _hasPreview: {
        const p = root.assignmentPreview
        if (!p) return false
        return (p.overallocationPct > 0) || !p.skillsMatched || !p.certsValid
            || p.isBlocked || p.hasWarnings
    }
    readonly property string _previewTone: {
        const p = root.assignmentPreview
        if (!p) return "info"
        if (p.isBlocked) return "danger"
        if (!p.skillsMatched || !p.certsValid || p.overallocationPct > 0) return "warning"
        if (p.hasWarnings) return "warning"
        return "success"
    }
    readonly property string _previewMessage: {
        const p = root.assignmentPreview
        if (!p) return ""
        const parts = []
        if (p.isBlocked) {
            parts.push("Blocked: " + (p.blockMessages || []).join("; "))
        } else {
            if (p.overallocationPct > 0)
                parts.push("Overallocated +" + p.overallocationPct + "% — conflicts: "
                    + (p.conflictProjects && p.conflictProjects.length
                        ? p.conflictProjects.join(", ") : "current project"))
            if (!p.skillsMatched) parts.push("Missing required skills")
            if (!p.certsValid)    parts.push("Certification expired or missing")
            if (p.hasWarnings && !parts.length)
                parts.push((p.warningMessages || []).join("; "))
        }
        return parts.join(" · ")
    }

    readonly property var _items: root.assignmentsModel.items || []
    readonly property var _selectedItem: {
        const id = root.selectedAssignmentId
        if (!id) return null
        const list = root._items
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].id || "") === id) return list[i]
        }
        return null
    }

    readonly property int _tableH: {
        const n = root._items.length
        const rH = Theme.AppTheme.compactRowHeight
        const hH = Theme.AppTheme.normalRowHeight
        return n === 0 ? (hH + 80) : Math.min(hH + n * rH + 12, 320)
    }

    readonly property var _columns: [
        { key: "title",       label: "Resource",   flex: 2,   sortable: false },
        { key: "subtitle",    label: "Role",        flex: 1.5, sortable: false },
        { key: "metaText",    label: "Allocation",  flex: 1.5, sortable: false },
        { key: "statusLabel", label: "Status",      flex: 0,   minWidth: 90, type: "status" }
    ]

    implicitHeight: _col.implicitHeight

    ColumnLayout {
        id: _col
        anchors.left:  parent.left
        anchors.right: parent.right
        anchors.top:   parent.top
        spacing: 0

        // Section toolbar — idle state
        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            visible:  !root.selectedAssignmentId
            title:    "Assignments"
            subtitle: root._items.length > 0 ? String(root._items.length) : ""
            busy:     root.isBusy
            createLabel: root.canCreate ? "Assign Resource" : ""
            actions: []
            onCreateRequested: root.createRequested()
        }

        // Section toolbar — row selected state
        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            visible:  Boolean(root.selectedAssignmentId)
            showBack: true
            title:    root._selectedItem ? String(root._selectedItem.title || "Assignment") : "Assignment"
            subtitle: root._selectedItem ? String(root._selectedItem.statusLabel || "") : ""
            busy:     root.isBusy
            actions: [
                { id: "allocation", label: "Allocation", icon: "edit",   enabled: true, danger: false },
                { id: "hours",      label: "Set Hours",  icon: "time",   enabled: true, danger: false },
                { id: "remove",     label: "Remove",     icon: "delete", enabled: true, danger: true  }
            ]
            onBackRequested: root.selectedAssignmentId = ""
            onActionTriggered: function(actionId) {
                const item = root._selectedItem
                if (!item) return
                if      (actionId === "allocation") root.editAllocationRequested(item)
                else if (actionId === "hours")      root.setHoursRequested(item)
                else if (actionId === "remove")     root.deleteRequested(item)
            }
        }

        // Assignment preview strip
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root._hasPreview
            message: root._previewMessage
            tone: root._previewTone
        }

        // DataTable
        Item {
            Layout.fillWidth: true
            height: root._tableH

            AppWidgets.DataTable {
                anchors.fill:  parent
                columns:       root._columns
                rows:          root._items
                selectedRowId: root.selectedAssignmentId
                loading:       root.isBusy
                emptyText:     root.assignmentsModel.emptyState || "No assignments for this task."

                onRowSelected: function(rowId) {
                    root.selectedAssignmentId = rowId
                    root.assignmentSelected(rowId)
                }
                onRowActivated: function(rowId) {
                    root.selectedAssignmentId = rowId
                    root.assignmentSelected(rowId)
                }
            }
        }
    }
}
