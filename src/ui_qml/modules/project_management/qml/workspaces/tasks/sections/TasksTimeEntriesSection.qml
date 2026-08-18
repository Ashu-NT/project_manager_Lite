pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme

Item {
    id: root

    property var assignmentSummary: AppMock.MockFactory.fieldRecord("", "", "Select a task assignment.")
    property var assignmentOptions: []
    property var periodOptions: []
    property string selectedPeriodStart: ""
    property var entriesModel: AppMock.MockFactory.catalog("Time Entries", "", "Select a task assignment.")
    property var entriesTableModel: null
    property var selectedEntryDetail: AppMock.MockFactory.fieldRecord()
    property string selectedEntryId: ""
    property bool isBusy: false
    property string errorText: ""

    signal periodChanged(string periodStart)
    signal assignmentChanged(string assignmentId)
    signal entrySelected(string entryId)
    signal addRequested(var payload)
    signal updateRequested(var payload)
    signal deleteRequested(string entryId)
    signal openTimesheetsRequested()

    property int _activeTabIndex: 0

    readonly property var _items: root.entriesModel.items || []
    readonly property var _state: root.assignmentSummary.state || {}
    readonly property string _assignmentStatus: String(root.assignmentSummary.statusLabel || "")
    // Submitting/locking/unlocking a *period* (which can span other tasks'
    // assignments too, not just this one) is handled exclusively by the
    // Timesheets workspace now -- see openTimesheetsRequested below. This
    // section only ever covers what's genuinely task-scoped: which
    // assignment, quick entry capture, and this task's own logged entries.
    readonly property var _detailTabs: [
        { "id": "assignment", "label": "Assignment" },
        { "id": "capture", "label": "Capture" },
        { "id": "ledger", "label": "Ledger" }
    ]
    readonly property int _resolvedTabIndex: {
        const tabs = root._detailTabs
        if (!tabs.length)
            return 0
        return Math.max(0, Math.min(root._activeTabIndex, tabs.length - 1))
    }
    readonly property real _activePanelHeight: {
        if (root._resolvedTabIndex === 1)
            return _capturePanel.implicitHeight
        if (root._resolvedTabIndex === 2)
            return _ledgerPanel.implicitHeight
        return _assignmentPanel.implicitHeight
    }

    function _syncEditorFields() {
        _captureEditor._syncEditorFields()
    }

    onSelectedEntryDetailChanged: Qt.callLater(root._syncEditorFields)
    Component.onCompleted: root._syncEditorFields()

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
            subtitle: root._assignmentStatus.length > 0
                ? root._assignmentStatus
                : (root._items.length > 0 ? root._items.length + " entries" : "Capture task time")
            busy: root.isBusy
            createLabel: ""
            actions: [
                { "id": "open_timesheets", "label": "Open in Timesheets", "icon": "time", "enabled": true, "danger": false }
            ]
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

            TaskTimeSummary {
                id: _assignmentPanel
                Layout.fillWidth: true
                assignmentSummary: root.assignmentSummary
                assignmentOptions: root.assignmentOptions
                periodOptions: root.periodOptions
                selectedPeriodStart: root.selectedPeriodStart
                isBusy: root.isBusy
                onAssignmentChanged: function(assignmentId) {
                    root.assignmentChanged(assignmentId)
                }
                onPeriodChanged: function(periodStart) {
                    root.periodChanged(periodStart)
                }
            }

            Item {
                id: _capturePanel
                Layout.fillWidth: true
                implicitHeight: _captureGrid.implicitHeight

                GridLayout {
                    id: _captureGrid
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    columns: width >= 980 ? 2 : 1
                    columnSpacing: Theme.AppTheme.spacingMd
                    rowSpacing: Theme.AppTheme.spacingMd

                    TaskTimeEntryEditor {
                        id: _captureEditor
                        Layout.fillWidth: true
                        assignmentState: root.assignmentSummary.state || {}
                        entryState: root.selectedEntryDetail.state || {}
                        isBusy: root.isBusy
                        onAddRequested: function(payload) {
                            root.addRequested(payload)
                        }
                        onUpdateRequested: function(payload) {
                            root.updateRequested(payload)
                        }
                        onDeleteRequested: function(entryId) {
                            root.deleteRequested(entryId)
                        }
                    }

                    TaskTimeEntryDetail {
                        Layout.fillWidth: true
                        assignmentSummary: root.assignmentSummary
                        selectedEntryDetail: root.selectedEntryDetail
                        selectedPeriodStart: root.selectedPeriodStart
                    }
                }
            }

            TaskTimeEntriesTable {
                id: _ledgerPanel
                Layout.fillWidth: true
                entriesModel: root.entriesModel
                entriesTableModel: root.entriesTableModel
                selectedEntryId: root.selectedEntryId
                isBusy: root.isBusy
                onEntrySelected: function(entryId) {
                    root.entrySelected(entryId)
                }
            }
        }
    }
}
