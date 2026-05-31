pragma ComponentBehavior: Bound
import App.Controls 1.0 as AppControls

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var detailPage
    property var activityDetail: ({})
    property var dependenciesModel: ({ "items": [], "emptyState": "" })
    property var dependencyRows: []
    property var dependencyTableModel: null
    property var constraintsModel: ({ "items": [], "emptyState": "" })
    property var constraintRows: []
    property var constraintTableModel: null
    property var calendarModel: ({ "summaryText": "", "workingDays": [], "hoursPerDay": "8", "holidays": [], "emptyState": "" })
    property var calendarSummaryRows: []
    property var calendarSummaryTableModel: null
    property var holidayRows: []
    property var holidayTableModel: null
    property var baselinesModel: ({ "options": [], "rows": [], "summaryText": "", "emptyState": "" })
    property var baselineCompareRows: []
    property var baselineCompareTableModel: null
    property var baselineRegisterModel: ({ "items": [], "emptyState": "" })
    property var baselineRegisterRows: []
    property var baselineRegisterTableModel: null
    property var resourceLoadingModel: ({ "items": [], "emptyState": "" })
    property var resourceRows: []
    property var resourcesLoadingTableModel: null
    property var scheduleImpactTasksTableModel: null
    property var activityFeedModel: ({ "items": [], "emptyState": "" })
    property var scheduleImpactModel: ({
        "taskId": "", "affectedCount": 0, "maxProjectFinishShiftDays": 0,
        "requiresApproval": false, "newlyCriticalCount": 0, "noLongerCriticalCount": 0,
        "affectedTasks": [], "available": false
    })
    property var workspaceController: null

    readonly property int _sectionIdx: detailPage ? detailPage.activeSectionIndex : 0
    readonly property int _activeSectionH: {
        if (root._sectionIdx === 0) return _sec0.implicitHeight
        if (root._sectionIdx === 1) return _sec1.implicitHeight
        if (root._sectionIdx === 2) return _sec2.implicitHeight
        if (root._sectionIdx === 3) return _sec3.implicitHeight
        if (root._sectionIdx === 4) return _sec4.implicitHeight
        if (root._sectionIdx === 5) return _sec5.implicitHeight
        if (root._sectionIdx === 6) return _sec6.implicitHeight
        return _sec7.implicitHeight
    }

    implicitHeight: _activeSectionH
    height: implicitHeight

    AppWidgets.LazySectionLoader {
        id: _sec0
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._sectionIdx === 0
        loadingMessage: "Loading..."
        sourceComponent: Component {
            SchedulingPanelFrame {
                width: parent ? parent.width : 0
                implicitHeight: 480
                title: "Activity Details"
                subtitle: "Planning identifiers, current dates, float, and schedule context for the selected activity."

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppWidgets.InlineMessage {
                        Layout.fillWidth: true
                        visible: String(root.activityDetail.emptyState || "").length > 0
                        tone: "info"
                        message: root.activityDetail.emptyState || ""
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: String(root.activityDetail.description || "").length > 0
                        text: root.activityDetail.description || ""
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: root.activityDetail.fields || []

                        delegate: Rectangle {
                            id: fieldCard
                            required property var modelData

                            Layout.fillWidth: true
                            implicitHeight: fieldColumn.implicitHeight + (Theme.AppTheme.spacingSm * 2)
                            radius: Theme.AppTheme.radiusSm
                            color: Theme.AppTheme.surfaceOverlay
                            border.color: Theme.AppTheme.subtleBorder
                            border.width: 1

                            ColumnLayout {
                                id: fieldColumn
                                anchors.fill: parent
                                anchors.margins: Theme.AppTheme.spacingSm
                                spacing: 2

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(fieldCard.modelData.label || "")
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(fieldCard.modelData.value || "")
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.WordWrap
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    visible: String(fieldCard.modelData.supportingText || "").length > 0
                                    text: String(fieldCard.modelData.supportingText || "")
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec1
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._sectionIdx === 1
        loadingMessage: "Loading..."
        sourceComponent: Component {
            SchedulingPanelFrame {
                width: parent ? parent.width : 0
                implicitHeight: 360
                title: "Dependencies"
                subtitle: "Read-only predecessor and successor visibility from the current schedule network."

                AppWidgets.DataTable {
                    sourceModel: root.dependencyTableModel
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    columns: [
                        { "key": "relatedActivity", "label": "Related Activity", "flex": 2.0, "sortable": true },
                        { "key": "dependencyType", "label": "Type", "flex": 1.0 },
                        { "key": "lag", "label": "Lag", "flex": 0, "minWidth": 72 },
                        { "key": "direction", "label": "Direction", "flex": 0.9, "type": "status" },
                        { "key": "status", "label": "Status", "flex": 0.9, "type": "status" },
                        { "key": "notes", "label": "Network Note", "flex": 1.4 }
                    ]
                    loading: false
                    emptyText: root.dependenciesModel.emptyState || "No dependencies are linked to the selected activity."
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec2
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._sectionIdx === 2
        loadingMessage: "Loading..."
        sourceComponent: Component {
            SchedulingPanelFrame {
                width: parent ? parent.width : 0
                implicitHeight: 320
                title: "Constraints"
                subtitle: "Date guards and execution locks currently affecting the selected activity."

                AppWidgets.DataTable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    sourceModel: root.constraintTableModel
                    columns: [
                        { "key": "constraint", "label": "Constraint", "flex": 1.3 },
                        { "key": "value", "label": "Value", "flex": 1.0 },
                        { "key": "status", "label": "Status", "flex": 0.8, "type": "status" },
                        { "key": "notes", "label": "Notes", "flex": 1.8 }
                    ]
                    loading: false
                    emptyText: root.constraintsModel.emptyState || "No explicit schedule controls are recorded for the selected activity."
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec3
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._sectionIdx === 3
        loadingMessage: "Loading..."
        sourceComponent: Component {
            SchedulingPanelFrame {
                width: parent ? parent.width : 0
                implicitHeight: 480
                title: "Calendars"
                subtitle: "Working calendar context and registered exceptions used by this schedule."

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppWidgets.InlineMessage {
                        Layout.fillWidth: true
                        visible: String(root.calendarModel.summaryText || "").length > 0
                        tone: "info"
                        message: root.calendarModel.summaryText || ""
                    }

                    AppWidgets.DataTable {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 120
                        sourceModel: root.calendarSummaryTableModel
                        columns: [
                            { "key": "calendar", "label": "Calendar", "flex": 1.0 },
                            { "key": "workingDays", "label": "Working Days", "flex": 1.7 },
                            { "key": "shiftPattern", "label": "Shift Pattern", "flex": 1.0 },
                            { "key": "hoursPerDay", "label": "Hours/Day", "flex": 0.8 },
                            { "key": "exceptions", "label": "Exceptions", "flex": 0.8 }
                        ]
                        loading: false
                        emptyText: "No calendar summary is available."
                    }

                    AppWidgets.DataTable {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        sourceModel: root.holidayTableModel
                        columns: [
                            { "key": "date", "label": "Date", "flex": 0.9 },
                            { "key": "exception", "label": "Exception", "flex": 1.1 },
                            { "key": "calendar", "label": "Calendar", "flex": 1.0 },
                            { "key": "details", "label": "Details", "flex": 1.8 }
                        ]
                        loading: false
                        emptyText: root.calendarModel.emptyState || "No holiday exceptions are configured."
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec4
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._sectionIdx === 4
        loadingMessage: "Loading..."
        sourceComponent: Component {
            SchedulingPanelFrame {
                width: parent ? parent.width : 0
                implicitHeight: 520
                title: "Baselines"
                subtitle: "Stored freezes and the current comparison output for the selected schedule scope."

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppWidgets.InlineMessage {
                        Layout.fillWidth: true
                        visible: String(root.baselinesModel.summaryText || root.baselinesModel.emptyState || "").length > 0
                        tone: "info"
                        message: root.baselinesModel.summaryText || root.baselinesModel.emptyState || ""
                    }

                    AppWidgets.DataTable {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        sourceModel: root.baselineCompareTableModel
                        columns: [
                            { "key": "activity", "label": "Activity", "flex": 1.6 },
                            { "key": "change", "label": "Change", "flex": 0.8, "type": "status" },
                            { "key": "shift", "label": "Shift Summary", "flex": 1.7 },
                            { "key": "dates", "label": "Baseline Dates", "flex": 2.1 },
                            { "key": "cost", "label": "Cost Delta", "flex": 1.0 }
                        ]
                        loading: false
                        emptyText: root.baselinesModel.emptyState || "Choose two baselines in the Baselines panel to compare drift."
                    }

                    AppWidgets.DataTable {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        sourceModel: root.baselineRegisterTableModel
                        columns: [
                            { "key": "baseline", "label": "Baseline", "flex": 1.4 },
                            { "key": "created", "label": "Created", "flex": 1.0 },
                            { "key": "approvedBy", "label": "Approved By", "flex": 1.0 },
                            { "key": "state", "label": "State", "flex": 0.8, "type": "status" }
                        ]
                        loading: false
                        emptyText: root.baselineRegisterModel.emptyState || "No baseline register entries are available."
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec5
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._sectionIdx === 5
        loadingMessage: "Loading..."
        sourceComponent: Component {
            SchedulingPanelFrame {
                width: parent ? parent.width : 0
                implicitHeight: 360
                title: "Resources"
                subtitle: "Current resource loading indicators related to the selected planning scope."

                AppWidgets.DataTable {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    sourceModel: root.resourcesLoadingTableModel
                    columns: [
                        { "key": "resource", "label": "Resource", "flex": 1.5 },
                        { "key": "allocation", "label": "Allocation", "flex": 0.9 },
                        { "key": "capacity", "label": "Capacity", "flex": 0.9 },
                        { "key": "utilization", "label": "Utilization", "flex": 0.9 },
                        { "key": "tasks", "label": "Tasks", "flex": 0.6 },
                        { "key": "status", "label": "Status", "flex": 0.8, "type": "status" }
                    ]
                    loading: false
                    emptyText: root.resourceLoadingModel.emptyState || "No resource load data is available."
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec6
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._sectionIdx === 6
        loadingMessage: "Loading..."
        sourceComponent: Component {
            SchedulingPanelFrame {
                width: parent ? parent.width : 0
                implicitHeight: 360
                title: "Activity Feed"
                subtitle: "Recent planning actions, warnings, and schedule control events for this session."

                AppWidgets.ActivityFeed {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    items: root.activityFeedModel.items || []
                    emptyText: root.activityFeedModel.emptyState || "No planning activity has been recorded."
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec7
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._sectionIdx === 7
        loadingMessage: "Loading..."
        sourceComponent: Component {
            SchedulingPanelFrame {
                width: parent ? parent.width : 0
                implicitHeight: 520
                title: "Change Impact"
                subtitle: "Schedule ripple analysis — affected tasks, critical path shifts, and approval requirements."

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    AppWidgets.InlineMessage {
                        Layout.fillWidth: true
                        visible: !root.scheduleImpactModel.available
                        tone: "info"
                        message: "Select an activity and run the analysis to see how a proposed change would ripple through the schedule."
                    }

                    AppControls.SecondaryButton {
                        Layout.alignment: Qt.AlignLeft
                        text: "Run Impact Analysis"
                        visible: root.workspaceController !== null
                        onClicked: {
                            if (root.workspaceController)
                                root.workspaceController.computeScheduleImpact({})
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm
                        visible: root.scheduleImpactModel.available === true

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: _metricCol0.implicitHeight + Theme.AppTheme.spacingMd * 2
                            radius: Theme.AppTheme.radiusSm
                            color: Theme.AppTheme.surfaceOverlay
                            border.color: Theme.AppTheme.subtleBorder
                            border.width: 1
                            ColumnLayout {
                                id: _metricCol0
                                anchors.fill: parent
                                anchors.margins: Theme.AppTheme.spacingMd
                                spacing: 2
                                AppControls.Label {
                                    text: "Affected Tasks"
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    text: String(root.scheduleImpactModel.affectedCount || 0)
                                    color: Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.headerSize
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: _metricCol1.implicitHeight + Theme.AppTheme.spacingMd * 2
                            radius: Theme.AppTheme.radiusSm
                            color: Theme.AppTheme.surfaceOverlay
                            border.color: Theme.AppTheme.subtleBorder
                            border.width: 1
                            ColumnLayout {
                                id: _metricCol1
                                anchors.fill: parent
                                anchors.margins: Theme.AppTheme.spacingMd
                                spacing: 2
                                AppControls.Label {
                                    text: "Max Finish Shift"
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    text: (root.scheduleImpactModel.maxProjectFinishShiftDays || 0) + "d"
                                    color: (root.scheduleImpactModel.maxProjectFinishShiftDays || 0) > 0
                                           ? Theme.AppTheme.danger : Theme.AppTheme.textPrimary
                                    font.pixelSize: Theme.AppTheme.headerSize
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: _metricCol2.implicitHeight + Theme.AppTheme.spacingMd * 2
                            radius: Theme.AppTheme.radiusSm
                            color: (root.scheduleImpactModel.requiresApproval === true)
                                   ? Theme.AppTheme.warning : Theme.AppTheme.surfaceOverlay
                            border.color: (root.scheduleImpactModel.requiresApproval === true)
                                          ? Theme.AppTheme.warning : Theme.AppTheme.subtleBorder
                            border.width: 1
                            ColumnLayout {
                                id: _metricCol2
                                anchors.fill: parent
                                anchors.margins: Theme.AppTheme.spacingMd
                                spacing: 2
                                AppControls.Label {
                                    text: "Approval"
                                    color: Theme.AppTheme.textMuted
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold: true
                                }
                                AppControls.Label {
                                    text: root.scheduleImpactModel.requiresApproval === true ? "Required" : "Not Required"
                                    color: root.scheduleImpactModel.requiresApproval === true
                                           ? Theme.AppTheme.warning : Theme.AppTheme.success
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true
                                }
                            }
                        }
                    }

                    AppWidgets.DataTable {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        sourceModel: root.scheduleImpactTasksTableModel
                        visible: root.scheduleImpactModel.available === true
                        columns: [
                            { "key": "taskName", "label": "Task", "flex": 2.0 },
                            { "key": "startShiftDays", "label": "Start Shift", "flex": 0.8 },
                            { "key": "finishShiftDays", "label": "Finish Shift", "flex": 0.8 },
                            { "key": "isCritical", "label": "Critical", "flex": 0.7, "type": "status" }
                        ]
                        loading: false
                        emptyText: "No affected tasks found for this activity."
                    }
                }
            }
        }
    }
}
