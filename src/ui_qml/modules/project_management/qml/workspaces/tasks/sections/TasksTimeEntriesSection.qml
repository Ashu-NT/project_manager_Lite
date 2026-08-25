pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Controls 1.0 as AppControls
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme

Item {
    id: root

    // Task-scoped planned/actual/remaining/overrun totals + resource
    // breakdown (docs §44 Time redesign) -- straight from
    // TaskTimeSummaryDesktopDto, rendered as-is.
    property var taskTimeSummary: ({ "hasSummary": false })
    property var assignmentOptions: []
    property var taskTimeEntriesPage: ({ "items": [], "total": 0, "page": 1, "pageSize": 25 })
    property var entriesTableModel: null
    property string timeResourceFilter: ""
    property var selectedEntryDetail: AppMock.MockFactory.fieldRecord()
    property string selectedEntryId: ""
    property bool isBusy: false
    property string errorText: ""

    signal addRequested(var payload)
    signal updateRequested(var payload)
    signal deleteRequested(string entryId)
    signal entrySelected(string entryId)
    signal resourceFilterRequested(string resourceId)
    signal pageRequested(int page)
    signal openTimesheetsRequested()
    signal goToAssignmentRequested(string assignmentId)

    property int _activeTabIndex: 0

    readonly property var _summary: root.taskTimeSummary || {}
    readonly property bool _hasAssignments: root.assignmentOptions.length > 0
    readonly property var _resourceOptions: {
        const rows = root._summary.resourceBreakdown || []
        const seen = {}
        const options = []
        for (let i = 0; i < rows.length; i += 1) {
            const id = String(rows[i].resourceId || "")
            if (!id || seen[id]) continue
            seen[id] = true
            options.push({ "value": id, "label": String(rows[i].resourceName || id) })
        }
        return options
    }
    readonly property var _kpiMetrics: {
        const s = root._summary
        if (!s.hasSummary) return []
        const metrics = [
            { "label": "Planned Work", "value": String(s.plannedHoursLabel || "") },
            { "label": "Actual Logged", "value": String(s.actualHoursLabel || "") }
        ]
        if (s.hasOverrun) {
            metrics.push({ "label": "Overrun", "value": String(s.overrunHoursLabel || ""), "colorHint": "danger" })
        } else {
            metrics.push({ "label": "Remaining", "value": String(s.remainingHoursLabel || "") })
        }
        metrics.push({
            "label": "Status",
            "value": String(s.burnStatusLabel || ""),
            "colorHint": s.burnStatus === "OVERRUN" ? "danger" : (s.burnStatus === "NEAR_PLAN" ? "warning" : "success")
        })
        return metrics
    }

    readonly property var _detailTabs: [
        { "id": "overview", "label": "Overview" },
        { "id": "logTime", "label": "Log Time" },
        { "id": "timeEntries", "label": "Time Entries" }
    ]
    readonly property int _resolvedTabIndex: Math.max(0, Math.min(root._activeTabIndex, root._detailTabs.length - 1))
    readonly property real _activePanelHeight: {
        if (root._resolvedTabIndex === 1) return _logTimePanel.implicitHeight
        if (root._resolvedTabIndex === 2) return _timeEntriesPanel.implicitHeight
        return _overviewPanel.implicitHeight
    }

    function switchToLogTime() {
        root._activeTabIndex = 1
    }

    function resetTimeEntryEditor() {
        _logTimeEditor.resetForCreate()
    }

    implicitHeight: _contentColumn.implicitHeight
    height: implicitHeight

    ColumnLayout {
        id: _contentColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Time"
            subtitle: "Track actual work recorded against this task."
            busy: root.isBusy
            createLabel: root._hasAssignments ? "Log Time" : ""
            actions: [
                { "id": "open_timesheets", "label": "Open in Timesheets", "icon": "time", "enabled": true, "danger": false }
            ]
            onCreateRequested: root.switchToLogTime()
            onActionTriggered: function(actionId) {
                if (actionId === "open_timesheets") root.openTimesheetsRequested()
            }
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.errorText.length > 0
            tone: "danger"
            message: root.errorText
        }

        // No resources assigned -- Time capture cannot invent an arbitrary
        // resource (docs §44 Time redesign §11); everything below this
        // point assumes at least one TaskAssignment exists.
        ColumnLayout {
            Layout.fillWidth: true
            Layout.topMargin: Theme.AppTheme.spacingLg
            visible: !root._hasAssignments
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                Layout.fillWidth: true
                text: "No resources are assigned to this task."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
            }
            AppControls.Label {
                Layout.fillWidth: true
                text: "Assign a resource before recording task time."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                horizontalAlignment: Text.AlignHCenter
            }
            AppControls.PrimaryButton {
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: Theme.AppTheme.spacingSm
                text: "Go to Assignment"
                onClicked: root.goToAssignmentRequested("")
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: root._hasAssignments
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.KpiStrip {
                Layout.fillWidth: true
                metrics: root._kpiMetrics
            }

            AppWidgets.DetailTabBar {
                Layout.fillWidth: true
                tabs: root._detailTabs
                currentIndex: root._resolvedTabIndex
                onTabSelected: function(index) {
                    root._activeTabIndex = index
                }
            }

            StackLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: root._activePanelHeight
                implicitHeight: root._activePanelHeight
                currentIndex: root._resolvedTabIndex

                TaskTimeOverview {
                    id: _overviewPanel
                    Layout.fillWidth: true
                    taskTimeSummary: root.taskTimeSummary
                    isBusy: root.isBusy
                    onLogTimeRequested: root.switchToLogTime()
                    onViewAssignmentRequested: function(assignmentId) {
                        root.goToAssignmentRequested(assignmentId)
                    }
                }

                Item {
                    id: _logTimePanel
                    Layout.fillWidth: true
                    implicitHeight: _logTimeEditor.implicitHeight

                    TaskTimeEntryEditor {
                        id: _logTimeEditor
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        assignmentOptions: root.assignmentOptions
                        taskTimeSummary: root.taskTimeSummary
                        entryState: root.selectedEntryDetail.state || {}
                        isBusy: root.isBusy
                        onAddRequested: function(payload) { root.addRequested(payload) }
                        onUpdateRequested: function(payload) { root.updateRequested(payload) }
                        onDeleteRequested: function(entryId) { root.deleteRequested(entryId) }
                        onCancelEditRequested: {
                            root.entrySelected("")
                            _logTimeEditor.resetForCreate()
                        }
                    }
                }

                TaskTimeEntriesTable {
                    id: _timeEntriesPanel
                    Layout.fillWidth: true
                    taskTimeEntriesPage: root.taskTimeEntriesPage
                    entriesTableModel: root.entriesTableModel
                    resourceOptions: root._resourceOptions
                    resourceFilter: root.timeResourceFilter
                    selectedEntryId: root.selectedEntryId
                    isBusy: root.isBusy
                    onEntrySelected: function(entryId) {
                        root.entrySelected(entryId)
                        root.switchToLogTime()
                    }
                    onResourceFilterRequested: function(resourceId) {
                        root.resourceFilterRequested(resourceId)
                    }
                    onPageRequested: function(page) {
                        root.pageRequested(page)
                    }
                }
            }
        }
    }
}
