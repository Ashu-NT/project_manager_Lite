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
    property var    assignmentPreview: null
    property string errorText: ""

    signal createRequested()
    signal assignmentSelected(string assignmentId)
    signal editAllocationRequested(var assignmentData)
    signal setHoursRequested(var assignmentData)
    signal deleteRequested(var assignmentData)
    signal acceptRequested(var assignmentData)
    signal declineRequested(var assignmentData)
    signal previewRequested(string projectResourceId, string taskId)
    signal retryRequested()

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
                parts.push("Overallocated +" + p.overallocationPct + "% - conflicts: "
                    + (p.conflictProjects && p.conflictProjects.length
                        ? p.conflictProjects.join(", ") : "current project"))
            if (!p.skillsMatched) parts.push("Missing required skills")
            if (!p.certsValid)    parts.push("Certification expired or missing")
            if (p.hasWarnings && !parts.length)
                parts.push((p.warningMessages || []).join("; "))
        }
        return parts.join(" | ")
    }

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
            actions.push({ "id": "hours", "label": "Set Hours", "icon": "time" })
            actions.push({ "id": "remove", "label": "Remove", "icon": "delete", "danger": true })
        }
        return actions
    }

    function _allocationOf(item) {
        return parseFloat((item.state || {}).allocationPercent || "0") || 0
    }

    implicitHeight: _col.implicitHeight

    ColumnLayout {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 0

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Assignments"
            subtitle: root._items.length > 0
                ? (root._items.length === 1 ? "1 resource" : root._items.length + " resources")
                : ""
            busy: root.isBusy
            createLabel: root.canCreate ? "Assign Resource" : ""
            actions: root._selectedActions
            onCreateRequested: root.createRequested()
            onActionTriggered: function(actionId) {
                if (!root._selectedItem) return
                if (actionId === "accept") root.acceptRequested(root._selectedItem)
                else if (actionId === "decline") root.declineRequested(root._selectedItem)
                else if (actionId === "allocation") root.editAllocationRequested(root._selectedItem)
                else if (actionId === "hours") root.setHoursRequested(root._selectedItem)
                else if (actionId === "remove") root.deleteRequested(root._selectedItem)
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

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root._hasPreview
            message: root._previewMessage
            tone: root._previewTone
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            Layout.topMargin: Theme.AppTheme.spacingLg
            Layout.bottomMargin: Theme.AppTheme.spacingLg
            visible: !root.isBusy && root._items.length === 0
            title: root.assignmentsModel.emptyState || "No assignments for this task."
        }

        Repeater {
            model: root._items

            delegate: Rectangle {
                id: _row
                required property var modelData

                readonly property string _rowId: String(_row.modelData.id || "")
                readonly property var _rowState: _row.modelData.state || {}
                readonly property real _allocation: root._allocationOf(_row.modelData)
                readonly property bool _isSelected: root.selectedAssignmentId === _row._rowId

                Layout.fillWidth: true
                implicitHeight: 60
                color: _row._isSelected
                    ? Theme.AppTheme.selectedSurface
                    : (_rowArea.containsMouse ? Theme.AppTheme.hoverSurface : "transparent")

                Rectangle {
                    visible: _row._isSelected
                    anchors { left: parent.left; top: parent.top; bottom: parent.bottom }
                    width: 3
                    color: Theme.AppTheme.accent
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.AppTheme.marginMd
                    anchors.rightMargin: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingMd

                    AppWidgets.Avatar {
                        name: String(_row.modelData.title || "")
                        size: 36
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 3

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_row.modelData.title || "")
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: _row._isSelected
                            color: Theme.AppTheme.textPrimary
                            elide: Text.ElideRight
                        }

                        RowLayout {
                            spacing: Theme.AppTheme.spacingSm

                            AppWidgets.ProgressBar {
                                implicitWidth: 70
                                value: _row._allocation / 100.0
                                colorHint: _row._allocation > 100 ? "danger" : "success"
                            }

                            AppControls.Label {
                                text: _row._allocation.toFixed(0) + "% allocated"
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                color: Theme.AppTheme.textMuted
                            }

                            AppControls.Label {
                                text: "• " + String(_row.modelData.supportingText || "")
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                color: Theme.AppTheme.textMuted
                                elide: Text.ElideRight
                            }
                        }
                    }

                    AppWidgets.StatusChip {
                        visible: String(_row.modelData.statusLabel || "").length > 0
                        status: String(_row.modelData.statusLabel || "")
                    }
                }

                Rectangle {
                    anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
                    height: 1
                    color: Theme.AppTheme.divider
                }

                MouseArea {
                    id: _rowArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.assignmentSelected(_row._rowId)
                        root.previewRequested(
                            String(_row._rowState.projectResourceId || ""),
                            String(_row._rowState.taskId || "")
                        )
                    }
                }
            }
        }
    }
}
