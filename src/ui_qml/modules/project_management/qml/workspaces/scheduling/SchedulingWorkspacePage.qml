pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementSchedulingWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.schedulingWorkspace
        : null

    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.scheduling",
            "title": "Scheduling",
            "summary": "Enterprise planning and schedule control workspace."
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var scheduleModel: root.workspaceController
        ? root.workspaceController.schedule
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "Scheduling desktop API is not connected in this QML preview." })
    readonly property var scheduleRows: root.workspaceController
        ? (root.workspaceController.scheduleRows || [])
        : []
    readonly property var timelineModel: root.workspaceController
        ? root.workspaceController.timeline
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No timeline items are available." })
    readonly property var diagnosticsModel: root.workspaceController
        ? root.workspaceController.diagnostics
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No diagnostics are available." })
    readonly property var diagnosticsRows: root.workspaceController
        ? (root.workspaceController.diagnosticsRows || [])
        : []
    readonly property var delayedActivitiesModel: root.workspaceController
        ? root.workspaceController.delayedActivities
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No delayed activities are visible." })
    readonly property var delayedRows: root.workspaceController
        ? (root.workspaceController.delayedActivityRows || [])
        : []
    readonly property var resourceLoadingModel: root.workspaceController
        ? root.workspaceController.resourceLoading
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No resource load data is available." })
    readonly property var resourceRows: root.workspaceController
        ? (root.workspaceController.resourceLoadingRows || [])
        : []
    readonly property var baselinesModel: root.workspaceController
        ? root.workspaceController.baselines
        : ({
            "options": [],
            "selectedBaselineAId": "",
            "selectedBaselineBId": "",
            "includeUnchanged": false,
            "summaryText": "",
            "rows": [],
            "emptyState": "No baseline comparison data is available."
        })
    readonly property var baselineCompareRows: root.workspaceController
        ? (root.workspaceController.baselineCompareRows || [])
        : []
    readonly property var baselineRegisterModel: root.workspaceController
        ? root.workspaceController.baselineRegister
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No baseline register entries are available." })
    readonly property var baselineRegisterRows: root.workspaceController
        ? (root.workspaceController.baselineRegisterRows || [])
        : []
    readonly property var calendarModel: root.workspaceController
        ? root.workspaceController.calendar
        : ({ "summaryText": "", "workingDays": [], "hoursPerDay": "8", "holidays": [], "emptyState": "No calendar data is available." })
    readonly property var calendarSummaryRows: root.workspaceController
        ? (root.workspaceController.calendarSummaryRows || [])
        : []
    readonly property var holidayRows: root.workspaceController
        ? (root.workspaceController.holidayRows || [])
        : []
    readonly property var selectedActivityModel: root.workspaceController
        ? root.workspaceController.selectedActivity
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select an activity from the schedule table to inspect the planning logic.",
            "fields": [],
            "state": {}
        })
    readonly property var dependenciesModel: root.workspaceController
        ? root.workspaceController.dependencies
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No dependencies are linked to the selected activity." })
    readonly property var dependencyRows: root.workspaceController
        ? (root.workspaceController.dependencyRows || [])
        : []
    readonly property var constraintsModel: root.workspaceController
        ? root.workspaceController.constraints
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No constraints are recorded for the selected activity." })
    readonly property var constraintRows: root.workspaceController
        ? (root.workspaceController.constraintRows || [])
        : []
    readonly property var activityFeedModel: root.workspaceController
        ? root.workspaceController.activityFeed
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No planning activity has been recorded." })
    readonly property var constraintViolationsModel: root.workspaceController
        ? root.workspaceController.constraintViolations
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No constraint violations detected." })
    readonly property var violationRows: root.workspaceController
        ? (root.workspaceController.violationRows || [])
        : []
    readonly property var baselineVarianceRows: root.workspaceController
        ? (root.workspaceController.baselineVarianceRows || [])
        : []

    property string activePanelId: "activity_timeline"
    // diagnosticsSearchText, resourcesSearchText, baselinesSearchText,
    // delaysSearchText, calendarsSearchText moved to Python controller
    // (replaced the _filterRows() anti-pattern with pre-filtered properties)
    property string feedSearchText: ""
    property string selectedBaselineRegisterId: ""
    property string selectedHolidayId: ""

    readonly property string selectedBaselineRegisterStatus: {
        const rows = root.baselineRegisterRows || []
        const targetId = root.selectedBaselineRegisterId
        for (let i = 0; i < rows.length; i++) {
            if (String(rows[i].id || "") === targetId) {
                return String(rows[i].status || "").toLowerCase()
            }
        }
        return ""
    }
    property var workingDayDraft: []
    property string hoursPerDayDraft: "8"
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item

    property string _activityTableId: "pm.scheduling.activity.table"
    property var    _activityColumns: []

    function _activityBaseColumns() {
        return [
            { "key": "activityCode",      "label": "Activity ID", "flex": 0, "minWidth": 96,  "sortable": true,  "required": true,  "visibleByDefault": true  },
            { "key": "wbs",               "label": "WBS",         "flex": 0, "minWidth": 72,  "sortable": true,  "visibleByDefault": true  },
            { "key": "taskName",          "label": "Task Name",   "flex": 2.1, "sortable": true, "required": true, "visibleByDefault": true  },
            { "key": "start",             "label": "Start",       "flex": 0, "minWidth": 90,  "visibleByDefault": true  },
            { "key": "finish",            "label": "Finish",      "flex": 0, "minWidth": 90,  "visibleByDefault": true  },
            { "key": "duration",          "label": "Duration",    "flex": 0, "minWidth": 88,  "visibleByDefault": true  },
            { "key": "remainingDuration", "label": "Remaining",   "flex": 0, "minWidth": 100, "visibleByDefault": true  },
            { "key": "float",             "label": "Float",       "flex": 0, "minWidth": 72,  "visibleByDefault": true  },
            { "key": "critical",          "label": "Critical",    "flex": 0, "minWidth": 88,  "type": "status",  "visibleByDefault": true  },
            { "key": "constraint",        "label": "Constraint",  "flex": 1.1,                "visibleByDefault": false },
            { "key": "calendar",          "label": "Calendar",    "flex": 0.9,                "visibleByDefault": false },
            { "key": "progress",          "label": "Progress",    "flex": 1.0, "minWidth": 120, "type": "progress", "visibleByDefault": true },
            { "key": "status",            "label": "Status",      "flex": 0.9, "type": "status", "visibleByDefault": true }
        ]
    }
    function _applyColumnState(base, saved) {
        const order = saved ? (saved.columnOrder || []) : []
        const hidden = saved ? (saved.hiddenColumns || []) : []
        if (order.length === 0) return base.slice()
        const hiddenSet = {}
        for (let i = 0; i < hidden.length; i++) hiddenSet[hidden[i]] = true
        const byKey = {}
        for (let i = 0; i < base.length; i++) byKey[base[i].key] = base[i]
        const result = []
        for (let j = 0; j < order.length; j++) {
            const col = byKey[order[j]]
            if (!col) continue
            const c = Object.assign({}, col)
            if (c.required !== true) c.visible = !hiddenSet[order[j]]
            result.push(c)
        }
        for (let i = 0; i < base.length; i++) {
            if (order.indexOf(base[i].key) < 0) result.push(Object.assign({}, base[i]))
        }
        return result
    }
    function _buildColumnState(columns) {
        const order = []
        const hidden = []
        for (let i = 0; i < columns.length; i++) {
            order.push(columns[i].key)
            if (columns[i].visible === false) hidden.push(columns[i].key)
        }
        return { "columnOrder": order, "hiddenColumns": hidden }
    }
    Component.onCompleted: {
        const base = root._activityBaseColumns()
        if (root.workspaceController !== null) {
            const saved = root.workspaceController.loadTableColumnState(root._activityTableId)
            root._activityColumns = root._applyColumnState(base, saved)
        } else {
            root._activityColumns = base
        }
    }
    readonly property var _diagnosticColumns: [
        { "key": "message", "label": "Diagnostic Message", "flex": 2.0, "sortable": true },
        { "key": "severity", "label": "Severity", "flex": 0.9, "type": "status" },
        { "key": "metric", "label": "Scope", "flex": 1.1 },
        { "key": "status", "label": "Value", "flex": 0.9 },
        { "key": "details", "label": "Details", "flex": 1.8 }
    ]
    readonly property var _violationColumns: [
        { "key": "activity", "label": "Activity", "flex": 1.5, "sortable": true },
        { "key": "constraintType", "label": "Constraint", "flex": 1.3 },
        { "key": "required", "label": "Required Date", "flex": 0.9 },
        { "key": "computed", "label": "Computed Date", "flex": 0.9 },
        { "key": "overrunDays", "label": "Overrun (days)", "flex": 0, "minWidth": 110 },
        { "key": "severity", "label": "Severity", "flex": 0.9, "type": "status" }
    ]
    readonly property var _resourceColumns: [
        { "key": "resource", "label": "Resource", "flex": 1.5, "sortable": true },
        { "key": "allocation", "label": "Allocation", "flex": 0.8 },
        { "key": "capacity", "label": "Capacity", "flex": 0.8 },
        { "key": "utilization", "label": "Utilization", "flex": 0.8 },
        { "key": "tasks", "label": "Tasks", "flex": 0, "minWidth": 64 },
        { "key": "status", "label": "Status", "flex": 0.8, "type": "status" }
    ]
    readonly property var _baselineCompareColumns: [
        { "key": "activity", "label": "Activity", "flex": 1.6, "sortable": true },
        { "key": "change", "label": "Change", "flex": 0.8, "type": "status" },
        { "key": "shift", "label": "Shift Summary", "flex": 1.7 },
        { "key": "dates", "label": "Baseline Dates", "flex": 2.1 },
        { "key": "cost", "label": "Cost Delta", "flex": 1.0 }
    ]
    readonly property var _baselineRegisterColumns: [
        { "key": "baseline", "label": "Baseline", "flex": 1.4, "sortable": true },
        { "key": "created", "label": "Created", "flex": 1.0 },
        { "key": "approvedBy", "label": "Approved By", "flex": 1.0 },
        { "key": "status", "label": "Status", "flex": 0.9, "type": "status" }
    ]
    readonly property var _baselineVarianceColumns: [
        { "key": "task", "label": "Task", "flex": 2.0, "sortable": true },
        { "key": "startVariance", "label": "Start Variance", "flex": 1.0 },
        { "key": "finishVariance", "label": "Finish Variance", "flex": 1.0 },
        { "key": "costVariance", "label": "Cost Delta", "flex": 1.0 },
        { "key": "status", "label": "Shift", "flex": 0.8, "type": "status" },
        { "key": "created", "label": "Recorded", "flex": 0.9 }
    ]
    readonly property var _delayedColumns: [
        { "key": "activity", "label": "Activity", "flex": 1.7, "sortable": true },
        { "key": "finish", "label": "Finish", "flex": 1.0 },
        { "key": "deadline", "label": "Deadline", "flex": 1.0 },
        { "key": "delay", "label": "Delay", "flex": 1.0 },
        { "key": "progress", "label": "Progress", "flex": 0.9 },
        { "key": "status", "label": "Status", "flex": 0.8, "type": "status" }
    ]
    readonly property var _calendarColumns: [
        { "key": "calendar", "label": "Calendar", "flex": 1.0 },
        { "key": "workingDays", "label": "Working Days", "flex": 1.7 },
        { "key": "shiftPattern", "label": "Shift Pattern", "flex": 1.0 },
        { "key": "hoursPerDay", "label": "Hours/Day", "flex": 0.8 },
        { "key": "exceptions", "label": "Exceptions", "flex": 0.8 }
    ]
    readonly property var _holidayColumns: [
        { "key": "date", "label": "Date", "flex": 0.9, "sortable": true },
        { "key": "exception", "label": "Exception", "flex": 1.2 },
        { "key": "calendar", "label": "Calendar", "flex": 1.0 },
        { "key": "details", "label": "Details", "flex": 1.8 }
    ]
    readonly property var _panelTabs: [
        { "id": "activity_timeline", "label": "Activity & Timeline" },
        { "id": "diagnostics",       "label": "Diagnostics" },
        { "id": "resources",         "label": "Resources" },
        { "id": "baselines",         "label": "Baselines" },
        { "id": "delays",            "label": "Delays" },
        { "id": "calendars",         "label": "Calendars" },
        { "id": "activity_feed",     "label": "Activity Feed" }
    ]

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    function _panelIndex(panelId) {
        for (let i = 0; i < root._panelTabs.length; i += 1) {
            if (String(root._panelTabs[i].id || "") === String(panelId || "")) {
                return i
            }
        }
        return 0
    }

    function _optionIndexForValue(options, value) {
        const optionList = options || []
        for (let i = 0; i < optionList.length; i += 1) {
            if (String(optionList[i].value || "") === String(value || "")) {
                return i
            }
        }
        return optionList.length > 0 ? 0 : -1
    }

    function _syncCalendarDraft() {
        const selected = []
        const workingDays = root.calendarModel.workingDays || []
        for (let i = 0; i < workingDays.length; i += 1) {
            if (workingDays[i].checked) {
                selected.push(workingDays[i].index)
            }
        }
        root.workingDayDraft = selected
        root.hoursPerDayDraft = String(root.calendarModel.hoursPerDay || "8")
    }

    function _openActivityDetail(activityId) {
        if (root.workspaceController === null || !String(activityId || "").length) {
            return
        }
        root.workspaceController.activateActivity(String(activityId || ""))
        root._pendingDetailSection = 0
        root._detailOpen = true
        if (detailPage) {
            detailPage.scrollToSection(0)
        }
    }

    onCalendarModelChanged: root._syncCalendarDraft()
    Component.onCompleted: root._syncCalendarDraft()

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            SchedulingDialogHost {
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                selectedActivityData: root.selectedActivityModel
                onCreateBaselineRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.createBaseline(payload)
                    }
                }
            }
        }
    }

    Item {
        anchors.fill: parent

        Item {
            anchors.fill: parent
            visible: !root._detailOpen

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.KpiStrip {
                    Layout.fillWidth: true
                    metrics: root.overviewModel.metrics || []
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: (root.workspaceController ? root.workspaceController.isLoading : false)
                        && !(root.workspaceController ? root.workspaceController.isBusy : false)
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "info"
                    message: "Loading scheduling data..."
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root.workspaceController
                        ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    tone: "info"
                    message: "Applying planning changes..."
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Rectangle {
                    Layout.fillWidth: true
                    color: Theme.AppTheme.surfaceRaised
                    radius: Theme.AppTheme.radiusMd
                    border.color: Theme.AppTheme.subtleBorder
                    border.width: 1
                    implicitHeight: navFlow.implicitHeight + (Theme.AppTheme.marginMd * 2)

                    Flow {
                        id: navFlow
                        anchors.fill: parent
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingSm

                        Repeater {
                            model: root._panelTabs

                            delegate: Rectangle {
                                id: tabButton
                                required property var modelData

                                readonly property bool _active: String(modelData.id || "") === root.activePanelId

                                implicitWidth: labelRow.implicitWidth + 22
                                implicitHeight: Theme.AppTheme.inputHeight
                                radius: Theme.AppTheme.radiusSm
                                color: tabButton._active
                                    ? Theme.AppTheme.navSelectedBackground
                                    : tabHover.containsMouse
                                        ? Theme.AppTheme.hoverSurface
                                        : Theme.AppTheme.surfaceOverlay
                                border.color: tabButton._active
                                    ? Theme.AppTheme.accent
                                    : Theme.AppTheme.subtleBorder
                                border.width: tabButton._active ? 1 : 0

                                RowLayout {
                                    id: labelRow
                                    anchors.centerIn: parent
                                    spacing: Theme.AppTheme.spacingXs

                                    AppControls.Label {
                                        text: String(tabButton.modelData.label || "")
                                        color: tabButton._active
                                            ? Theme.AppTheme.navSelectedText
                                            : Theme.AppTheme.textSecondary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold: tabButton._active
                                    }

                                    Rectangle {
                                        visible: parseInt(tabButton.modelData.count || 0, 10) > 0
                                        radius: 8
                                        color: tabButton._active
                                            ? Theme.AppTheme.accent
                                            : Theme.AppTheme.surfaceRaised
                                        implicitWidth: countLabel.implicitWidth + 8
                                        implicitHeight: 16

                                        AppControls.Label {
                                            id: countLabel
                                            anchors.centerIn: parent
                                            text: String(tabButton.modelData.count || "")
                                            color: tabButton._active
                                                ? Theme.AppTheme.textOnAccent
                                                : Theme.AppTheme.textMuted
                                            font.family: Theme.AppTheme.fontFamily
                                            font.pixelSize: Theme.AppTheme.captionSize
                                            font.bold: true
                                        }
                                    }
                                }

                                MouseArea {
                                    id: tabHover
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.activePanelId = String(tabButton.modelData.id || "activity_timeline")
                                }
                            }
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    StackLayout {
                        anchors.fill: parent
                        currentIndex: root._panelIndex(root.activePanelId)

                        SchedulingPanelFrame {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "Activity & Timeline"
                            subtitle: "Primary planning console with filtered activities and the current timeline lane."

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.margins: Theme.AppTheme.marginMd
                                spacing: Theme.AppTheme.spacingSm

                                SchedulingActionBar {
                                    Layout.fillWidth: true
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    actions: [
                                        { "id": "refresh", "label": "Refresh", "icon": "refresh", "enabled": true },
                                        { "id": "run_cpm", "label": "Run CPM", "icon": "approve", "enabled": String(root.workspaceController ? root.workspaceController.selectedProjectId : "").length > 0 }
                                    ]

                                    AppControls.ComboBox {
                                        Layout.preferredWidth: 210
                                        model: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                                        textRole: "label"
                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                        currentIndex: root._optionIndexForValue(
                                            root.workspaceController ? (root.workspaceController.projectOptions || []) : [],
                                            root.workspaceController ? root.workspaceController.selectedProjectId : ""
                                        )
                                        onActivated: function(index) {
                                            const options = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                                            if (root.workspaceController !== null && options[index]) {
                                                root.workspaceController.selectProject(String(options[index].value || ""))
                                            }
                                        }
                                    }

                                    AppControls.ComboBox {
                                        Layout.preferredWidth: 180
                                        model: root.workspaceController ? (root.workspaceController.baselineOptions || []) : []
                                        textRole: "label"
                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                            && (root.workspaceController ? (root.workspaceController.baselineOptions || []).length > 0 : false)
                                        currentIndex: root._optionIndexForValue(
                                            root.workspaceController ? (root.workspaceController.baselineOptions || []) : [],
                                            root.workspaceController ? root.workspaceController.selectedBaselineId : ""
                                        )
                                        onActivated: function(index) {
                                            const options = root.workspaceController ? (root.workspaceController.baselineOptions || []) : []
                                            if (root.workspaceController !== null && options[index]) {
                                                root.workspaceController.selectBaseline(String(options[index].value || ""))
                                            }
                                        }
                                    }

                                    AppControls.ComboBox {
                                        Layout.preferredWidth: 170
                                        model: root.workspaceController ? (root.workspaceController.calendarOptions || []) : []
                                        textRole: "label"
                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                            && (root.workspaceController ? (root.workspaceController.calendarOptions || []).length > 0 : false)
                                        currentIndex: root._optionIndexForValue(
                                            root.workspaceController ? (root.workspaceController.calendarOptions || []) : [],
                                            root.workspaceController ? root.workspaceController.selectedCalendarId : "default"
                                        )
                                        onActivated: function(index) {
                                            const options = root.workspaceController ? (root.workspaceController.calendarOptions || []) : []
                                            if (root.workspaceController !== null && options[index]) {
                                                root.workspaceController.selectCalendar(String(options[index].value || "default"))
                                            }
                                        }
                                    }

                                    onActionTriggered: function(actionId) {
                                        if (root.workspaceController === null) {
                                            return
                                        }
                                        if (actionId === "refresh") {
                                            root.workspaceController.refresh()
                                        } else if (actionId === "run_cpm") {
                                            root.workspaceController.recalculateSchedule()
                                        }
                                    }
                                }

                                AppWidgets.TableToolbar {
                                    id: activityToolbar
                                    Layout.fillWidth: true
                                    searchText: root.workspaceController ? root.workspaceController.searchText : ""
                                    searchPlaceholder: "Search activities..."
                                    showFilter: true
                                    showCustomize: true
                                    showExport: true
                                    showRefresh: false
                                    showViews: false
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                                    onSearchChanged: function(text) {
                                        if (root.workspaceController !== null) {
                                            root.workspaceController.setSearchText(text)
                                        }
                                    }
                                    onFilterClicked: activityFilterPopup.open()
                                    onCustomizeClicked: activityTable.openColumnCustomizer(activityToolbar.customizeButtonItem)
                                    onExportRequested: {
                                        if (root.workspaceController !== null) {
                                            root.workspaceController.exportSchedule()
                                        }
                                    }
                                }

                                SplitView {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    orientation: Qt.Horizontal

                                    Item {
                                        SplitView.minimumWidth: 420
                                        SplitView.preferredWidth: 560
                                        SplitView.fillHeight: true

                                        AppWidgets.DataTable {
                                            id: activityTable
                                            anchors.top: parent.top
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.bottom: activityPagination.top
                                            tableId: root._activityTableId
                                            columns: root._activityColumns
                                            sourceModel: root.workspaceController ? root.workspaceController.scheduleTableModel : null
                                            loading: root.workspaceController ? root.workspaceController.isLoading : false
                                            emptyText: root.scheduleModel.emptyState || "No activities are available for the selected planning scope."
                                            selectedRowId: root.workspaceController ? root.workspaceController.selectedActivityId : ""
                                            onColumnsStateChanged: function(cols) {
                                                if (root.workspaceController) root.workspaceController.saveTableColumnState(root._activityTableId, root._buildColumnState(cols))
                                                root._activityColumns = cols
                                            }

                                            onRowSelected: function(rowId) {
                                                if (root.workspaceController !== null) {
                                                    root.workspaceController.selectActivity(rowId)
                                                }
                                            }
                                            onRowActivated: function(rowId) {
                                                root._openActivityDetail(rowId)
                                            }
                                        }

                                        AppWidgets.TablePaginationBar {
                                            id: activityPagination
                                            anchors.left: parent.left
                                            anchors.right: parent.right
                                            anchors.bottom: parent.bottom
                                            currentPage: root.workspaceController ? root.workspaceController.activityPage : 1
                                            pageSize: root.workspaceController ? root.workspaceController.activityPageSize : 25
                                            totalItems: root.workspaceController ? root.workspaceController.activityTotalCount : 0
                                            busy: root.workspaceController ? root.workspaceController.isBusy : false
                                            onPageRequested: function(page) {
                                                if (root.workspaceController !== null) {
                                                    root.workspaceController.setActivityPage(page)
                                                }
                                            }
                                            onPageSizeRequested: function(pageSize) {
                                                if (root.workspaceController !== null) {
                                                    root.workspaceController.setActivityPageSize(pageSize)
                                                }
                                            }
                                        }

                                        AppWidgets.AnchoredPopup {
                                            id: activityFilterPopup
                                            anchorItem: activityToolbar.filterButtonItem
                                            width: 288
                                            padding: Theme.AppTheme.marginMd
                                            closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                                            background: Rectangle {
                                                radius: Theme.AppTheme.radiusLg
                                                color: Theme.AppTheme.surfaceRaised
                                                border.color: Theme.AppTheme.divider
                                                border.width: 1
                                            }

                                            contentItem: ColumnLayout {
                                                spacing: Theme.AppTheme.spacingSm

                                                AppControls.Label {
                                                    text: "Filters"
                                                    font.bold: true
                                                    font.family: Theme.AppTheme.fontFamily
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                    color: Theme.AppTheme.textMuted
                                                }

                                                AppControls.Label {
                                                    text: "Status"
                                                    font.bold: true
                                                    font.family: Theme.AppTheme.fontFamily
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                    color: Theme.AppTheme.textMuted
                                                }

                                                AppControls.ComboBox {
                                                    Layout.fillWidth: true
                                                    model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                                    textRole: "label"
                                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                                    currentIndex: root._optionIndexForValue(
                                                        root.workspaceController ? (root.workspaceController.statusOptions || []) : [],
                                                        root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                                                    )
                                                    onActivated: function(index) {
                                                        const options = root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                                        if (root.workspaceController !== null && options[index]) {
                                                            root.workspaceController.setStatusFilter(String(options[index].value || "all"))
                                                        }
                                                    }
                                                }

                                                AppControls.CheckBox {
                                                    text: "Critical only"
                                                    checked: root.workspaceController ? root.workspaceController.showCriticalOnly : false
                                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                                    onToggled: {
                                                        if (root.workspaceController !== null) {
                                                            root.workspaceController.setShowCriticalOnly(checked)
                                                        }
                                                    }
                                                }

                                                AppControls.CheckBox {
                                                    text: "Delayed only"
                                                    checked: root.workspaceController ? root.workspaceController.showDelayedOnly : false
                                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                                    onToggled: {
                                                        if (root.workspaceController !== null) {
                                                            root.workspaceController.setShowDelayedOnly(checked)
                                                        }
                                                    }
                                                }

                                                RowLayout {
                                                    Layout.fillWidth: true
                                                    spacing: Theme.AppTheme.spacingSm

                                                    AppControls.SecondaryButton {
                                                        Layout.fillWidth: true
                                                        text: "Clear"
                                                        iconName: "close"
                                                        onClicked: {
                                                            if (root.workspaceController !== null) {
                                                                root.workspaceController.clearFilters()
                                                            }
                                                            activityFilterPopup.close()
                                                        }
                                                    }

                                                    AppControls.PrimaryButton {
                                                        Layout.fillWidth: true
                                                        text: "Done"
                                                        iconName: "approve"
                                                        onClicked: activityFilterPopup.close()
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    SchedulingTimelinePanel {
                                        SplitView.minimumWidth: 420
                                        SplitView.preferredWidth: 760
                                        SplitView.fillWidth: true
                                        SplitView.fillHeight: true
                                        timelineModel: root.timelineModel
                                    }
                                }
                            }
                        }

                        SchedulingPanelFrame {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "Diagnostics"
                            subtitle: "Planner-quality checks for network logic, float pressure, and schedule stability."

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.margins: Theme.AppTheme.marginMd
                                spacing: Theme.AppTheme.spacingSm

                                SchedulingActionBar {
                                    Layout.fillWidth: true
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    actions: [
                                        { "id": "refresh", "label": "Refresh Diagnostics", "icon": "refresh", "enabled": true },
                                        { "id": "run_cpm", "label": "Run CPM", "icon": "approve", "enabled": true },
                                        { "id": "export", "label": "Export Report", "icon": "export", "enabled": true }
                                    ]
                                    onActionTriggered: function(actionId) {
                                        if (root.workspaceController === null) {
                                            return
                                        }
                                        if (actionId === "refresh") {
                                            root.workspaceController.refresh()
                                        } else if (actionId === "run_cpm") {
                                            root.workspaceController.recalculateSchedule()
                                        } else if (actionId === "export") {
                                            root.workspaceController.exportSchedule()
                                        }
                                    }
                                }

                                AppWidgets.TableToolbar {
                                    id: diagnosticsToolbar
                                    Layout.fillWidth: true
                                    searchText: root.workspaceController ? root.workspaceController.diagnosticsSearchText : ""
                                    searchPlaceholder: "Search diagnostics..."
                                    showCustomize: true
                                    showExport: true
                                    showRefresh: false
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    onSearchChanged: function(text) { if (root.workspaceController) root.workspaceController.setDiagnosticsSearchText(text) }
                                    onCustomizeClicked: diagnosticsTable.openColumnCustomizer(diagnosticsToolbar.customizeButtonItem)
                                    onExportRequested: {
                                        if (root.workspaceController !== null) {
                                            root.workspaceController.exportSchedule()
                                        }
                                    }
                                }

                                AppWidgets.DataTable {
                                    id: diagnosticsTable
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 210
                                    columns: root._diagnosticColumns
                                    sourceModel: root.workspaceController ? root.workspaceController.diagnosticsTableModel : null
                                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                                    emptyText: root.diagnosticsModel.emptyState || "No diagnostics are available."
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: "Constraint Violations"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true
                                }

                                AppWidgets.DataTable {
                                    id: violationsTable
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    columns: root._violationColumns
                                    sourceModel: root.workspaceController ? root.workspaceController.violationsTableModel : null
                                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                                    emptyText: root.constraintViolationsModel.emptyState || "No constraint violations detected for the current schedule."
                                }
                            }
                        }

                        SchedulingPanelFrame {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "Resources"
                            subtitle: "Resource loading pressure, overload exposure, and utilization visibility."

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.margins: Theme.AppTheme.marginMd
                                spacing: Theme.AppTheme.spacingSm

                                SchedulingActionBar {
                                    Layout.fillWidth: true
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    actions: [
                                        { "id": "refresh", "label": "Refresh", "icon": "refresh", "enabled": true },
                                        { "id": "run_cpm", "label": "Run CPM", "icon": "approve", "enabled": true },
                                        { "id": "export", "label": "Export", "icon": "export", "enabled": true }
                                    ]
                                    onActionTriggered: function(actionId) {
                                        if (root.workspaceController === null) {
                                            return
                                        }
                                        if (actionId === "refresh") {
                                            root.workspaceController.refresh()
                                        } else if (actionId === "run_cpm") {
                                            root.workspaceController.recalculateSchedule()
                                        } else if (actionId === "export") {
                                            root.workspaceController.exportSchedule()
                                        }
                                    }
                                }

                                AppWidgets.TableToolbar {
                                    id: resourcesToolbar
                                    Layout.fillWidth: true
                                    searchText: root.workspaceController ? root.workspaceController.resourcesSearchText : ""
                                    searchPlaceholder: "Search resources..."
                                    showCustomize: true
                                    showExport: true
                                    showRefresh: false
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    onSearchChanged: function(text) { if (root.workspaceController) root.workspaceController.setResourcesSearchText(text) }
                                    onCustomizeClicked: resourcesTable.openColumnCustomizer(resourcesToolbar.customizeButtonItem)
                                    onExportRequested: {
                                        if (root.workspaceController !== null) {
                                            root.workspaceController.exportSchedule()
                                        }
                                    }
                                }

                                AppWidgets.DataTable {
                                    id: resourcesTable
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    columns: root._resourceColumns
                                    sourceModel: root.workspaceController ? root.workspaceController.resourcesLoadingTableModel : null
                                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                                    emptyText: root.resourceLoadingModel.emptyState || "No resource load data is available."
                                }
                            }
                        }

                        SchedulingPanelFrame {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "Baselines"
                            subtitle: "Create, compare, archive, and review schedule freeze points for governance."

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.margins: Theme.AppTheme.marginMd
                                spacing: Theme.AppTheme.spacingSm

                                SchedulingActionBar {
                                    Layout.fillWidth: true
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    actions: [
                                        { "id": "save", "label": "Save Baseline", "icon": "register", "enabled": String(root.workspaceController ? root.workspaceController.selectedProjectId : "").length > 0 },
                                        { "id": "submit", "label": "Submit", "icon": "approve", "enabled": root.selectedBaselineRegisterStatus === "draft" && root.selectedBaselineRegisterId.length > 0 },
                                        { "id": "approve", "label": "Approve", "icon": "success", "enabled": root.selectedBaselineRegisterStatus === "submitted" && root.selectedBaselineRegisterId.length > 0 },
                                        { "id": "reject", "label": "Reject", "icon": "reject", "danger": true, "enabled": root.selectedBaselineRegisterStatus === "submitted" && root.selectedBaselineRegisterId.length > 0 },
                                        { "id": "compare", "label": "Compare", "icon": "refresh", "enabled": (root.baselinesModel.options || []).length > 1 },
                                        { "id": "archive", "label": "Archive", "icon": "delete", "danger": true, "enabled": root.selectedBaselineRegisterId.length > 0 },
                                        { "id": "export", "label": "Export", "icon": "export", "enabled": true }
                                    ]

                                    AppControls.ComboBox {
                                        Layout.preferredWidth: 180
                                        model: root.baselinesModel.options || []
                                        textRole: "label"
                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                            && (root.baselinesModel.options || []).length > 0
                                        currentIndex: root._optionIndexForValue(
                                            root.baselinesModel.options || [],
                                            root.baselinesModel.selectedBaselineAId || ""
                                        )
                                        onActivated: function(index) {
                                            const option = (root.baselinesModel.options || [])[index]
                                            if (root.workspaceController !== null && option) {
                                                root.workspaceController.selectBaselineA(String(option.value || ""))
                                            }
                                        }
                                    }

                                    AppControls.ComboBox {
                                        Layout.preferredWidth: 180
                                        model: root.baselinesModel.options || []
                                        textRole: "label"
                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                            && (root.baselinesModel.options || []).length > 0
                                        currentIndex: root._optionIndexForValue(
                                            root.baselinesModel.options || [],
                                            root.baselinesModel.selectedBaselineBId || ""
                                        )
                                        onActivated: function(index) {
                                            const option = (root.baselinesModel.options || [])[index]
                                            if (root.workspaceController !== null && option) {
                                                root.workspaceController.selectBaselineB(String(option.value || ""))
                                            }
                                        }
                                    }

                                    AppControls.CheckBox {
                                        text: "Include unchanged"
                                        checked: Boolean(root.baselinesModel.includeUnchanged)
                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                        onToggled: {
                                            if (root.workspaceController !== null) {
                                                root.workspaceController.setIncludeUnchanged(checked)
                                            }
                                        }
                                    }

                                    onActionTriggered: function(actionId) {
                                        if (root.workspaceController === null) {
                                            return
                                        }
                                        if (actionId === "save") {
                                            dialogHostLoader.invoke("openCreateBaselineDialog")
                                        } else if (actionId === "submit" && root.selectedBaselineRegisterId.length > 0) {
                                            root.workspaceController.submitBaseline(root.selectedBaselineRegisterId)
                                        } else if (actionId === "approve" && root.selectedBaselineRegisterId.length > 0) {
                                            root.workspaceController.approveBaseline(root.selectedBaselineRegisterId)
                                        } else if (actionId === "reject" && root.selectedBaselineRegisterId.length > 0) {
                                            root.workspaceController.rejectBaseline(root.selectedBaselineRegisterId)
                                        } else if (actionId === "compare") {
                                            root.workspaceController.refresh()
                                        } else if (actionId === "archive" && root.selectedBaselineRegisterId.length > 0) {
                                            root.workspaceController.deleteBaseline(root.selectedBaselineRegisterId)
                                        } else if (actionId === "export") {
                                            root.workspaceController.exportSchedule()
                                        }
                                    }
                                }

                                AppWidgets.InlineMessage {
                                    Layout.fillWidth: true
                                    visible: String(root.baselinesModel.summaryText || root.baselinesModel.emptyState || "").length > 0
                                    tone: "info"
                                    message: root.baselinesModel.summaryText || root.baselinesModel.emptyState || ""
                                }

                                AppWidgets.TableToolbar {
                                    id: baselinesToolbar
                                    Layout.fillWidth: true
                                    searchText: root.workspaceController ? root.workspaceController.baselinesSearchText : ""
                                    searchPlaceholder: "Search baselines..."
                                    showCustomize: true
                                    showExport: true
                                    showRefresh: false
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    onSearchChanged: function(text) { if (root.workspaceController) root.workspaceController.setBaselinesSearchText(text) }
                                    onCustomizeClicked: baselineRegisterTable.openColumnCustomizer(baselinesToolbar.customizeButtonItem)
                                    onExportRequested: {
                                        if (root.workspaceController !== null) {
                                            root.workspaceController.exportSchedule()
                                        }
                                    }
                                }

                                AppWidgets.DataTable {
                                    id: baselineCompareTable
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 190
                                    columns: root._baselineCompareColumns
                                    sourceModel: root.workspaceController ? root.workspaceController.baselineCompareTableModel : null
                                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                                    emptyText: root.baselinesModel.emptyState || "Choose two baselines to compare schedule drift."
                                }

                                AppWidgets.DataTable {
                                    id: baselineRegisterTable
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 200
                                    columns: root._baselineRegisterColumns
                                    sourceModel: root.workspaceController ? root.workspaceController.baselineRegisterTableModel : null
                                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                                    emptyText: root.baselineRegisterModel.emptyState || "No baseline register entries are available."
                                    selectedRowId: root.selectedBaselineRegisterId
                                    onRowSelected: function(rowId) {
                                        root.selectedBaselineRegisterId = String(rowId || "")
                                        if (root.workspaceController !== null) {
                                            root.workspaceController.loadVarianceRecordsForBaseline(String(rowId || ""))
                                        }
                                    }
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: "Approval-Time Variance"
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: true
                                }

                                AppWidgets.DataTable {
                                    id: baselineVarianceTable
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    columns: root._baselineVarianceColumns
                                    sourceModel: root.workspaceController ? root.workspaceController.baselineVarianceTableModel : null
                                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                                    emptyText: root.selectedBaselineRegisterId.length > 0
                                        ? "No variance records are stored for this baseline. Variance is recorded when a baseline supersedes the previously approved one."
                                        : "Select a baseline from the register to review its approval-time variance."
                                }
                            }
                        }

                        SchedulingPanelFrame {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "Delays"
                            subtitle: "Delayed activities and deadline pressure requiring planner attention."

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.margins: Theme.AppTheme.marginMd
                                spacing: Theme.AppTheme.spacingSm

                                SchedulingActionBar {
                                    Layout.fillWidth: true
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    actions: [
                                        { "id": "refresh", "label": "Refresh", "icon": "refresh", "enabled": true },
                                        { "id": "run_cpm", "label": "Run CPM", "icon": "approve", "enabled": true },
                                        { "id": "export", "label": "Export", "icon": "export", "enabled": true }
                                    ]
                                    onActionTriggered: function(actionId) {
                                        if (root.workspaceController === null) {
                                            return
                                        }
                                        if (actionId === "refresh") {
                                            root.workspaceController.refresh()
                                        } else if (actionId === "run_cpm") {
                                            root.workspaceController.recalculateSchedule()
                                        } else if (actionId === "export") {
                                            root.workspaceController.exportSchedule()
                                        }
                                    }
                                }

                                AppWidgets.TableToolbar {
                                    id: delaysToolbar
                                    Layout.fillWidth: true
                                    searchText: root.workspaceController ? root.workspaceController.delaysSearchText : ""
                                    searchPlaceholder: "Search delayed activities..."
                                    showCustomize: true
                                    showExport: true
                                    showRefresh: false
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    onSearchChanged: function(text) { if (root.workspaceController) root.workspaceController.setDelaysSearchText(text) }
                                    onCustomizeClicked: delaysTable.openColumnCustomizer(delaysToolbar.customizeButtonItem)
                                    onExportRequested: {
                                        if (root.workspaceController !== null) {
                                            root.workspaceController.exportSchedule()
                                        }
                                    }
                                }

                                AppWidgets.DataTable {
                                    id: delaysTable
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    columns: root._delayedColumns
                                    sourceModel: root.workspaceController ? root.workspaceController.delayedTableModel : null
                                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                                    emptyText: root.delayedActivitiesModel.emptyState || "No delayed activities are visible."
                                    onRowActivated: function(rowId) {
                                        const rows = root.delayedRows || []
                                        for (let i = 0; i < rows.length; i += 1) {
                                            if (String(rows[i].id || "") === String(rowId || "")) {
                                                root._openActivityDetail(rows[i].activityId || rowId)
                                                break
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        SchedulingPanelFrame {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "Calendars"
                            subtitle: "Working-week rules, holiday exceptions, and working-day calculations for the current schedule calendar."

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.margins: Theme.AppTheme.marginMd
                                spacing: Theme.AppTheme.spacingSm

                                SchedulingActionBar {
                                    Layout.fillWidth: true
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    actions: [
                                        { "id": "save", "label": "Save Calendar", "icon": "save", "enabled": true },
                                        { "id": "add_exception", "label": "Add Exception", "icon": "add", "enabled": true },
                                        { "id": "delete_exception", "label": "Delete Exception", "icon": "delete", "danger": true, "enabled": root.selectedHolidayId.length > 0 },
                                        { "id": "calculate", "label": "Calculate Days", "icon": "refresh", "enabled": true }
                                    ]

                                    AppControls.ComboBox {
                                        Layout.preferredWidth: 190
                                        model: root.workspaceController ? (root.workspaceController.calendarOptions || []) : []
                                        textRole: "label"
                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                            && (root.workspaceController ? (root.workspaceController.calendarOptions || []).length > 0 : false)
                                        currentIndex: root._optionIndexForValue(
                                            root.workspaceController ? (root.workspaceController.calendarOptions || []) : [],
                                            root.workspaceController ? root.workspaceController.selectedCalendarId : "default"
                                        )
                                        onActivated: function(index) {
                                            const options = root.workspaceController ? (root.workspaceController.calendarOptions || []) : []
                                            if (root.workspaceController !== null && options[index]) {
                                                root.workspaceController.selectCalendar(String(options[index].value || "default"))
                                            }
                                        }
                                    }

                                    onActionTriggered: function(actionId) {
                                        if (root.workspaceController === null) {
                                            return
                                        }
                                        if (actionId === "save") {
                                            root.workspaceController.saveCalendar({
                                                "workingDays": root.workingDayDraft,
                                                "hoursPerDay": root.hoursPerDayDraft
                                            })
                                        } else if (actionId === "add_exception") {
                                            root.workspaceController.addHoliday({
                                                "holidayDate": holidayDateField.text,
                                                "name": holidayNameField.text
                                            })
                                        } else if (actionId === "delete_exception" && root.selectedHolidayId.length > 0) {
                                            root.workspaceController.deleteHoliday(root.selectedHolidayId)
                                        } else if (actionId === "calculate") {
                                            root.workspaceController.calculateWorkingDays({
                                                "startDate": calcStartField.text,
                                                "workingDays": calcDaysField.text
                                            })
                                        }
                                    }
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingMd

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: calendarConfigColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)
                                        radius: Theme.AppTheme.radiusSm
                                        color: Theme.AppTheme.surfaceOverlay
                                        border.color: Theme.AppTheme.subtleBorder
                                        border.width: 1

                                        ColumnLayout {
                                            id: calendarConfigColumn
                                            anchors.fill: parent
                                            anchors.margins: Theme.AppTheme.marginMd
                                            spacing: Theme.AppTheme.spacingSm

                                            AppControls.Label {
                                                Layout.fillWidth: true
                                                text: "Working Week"
                                                color: Theme.AppTheme.textSecondary
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.captionSize
                                                font.bold: true
                                            }

                                            Flow {
                                                Layout.fillWidth: true
                                                spacing: Theme.AppTheme.spacingSm

                                                Repeater {
                                                    model: root.calendarModel.workingDays || []

                                                    delegate: AppControls.CheckBox {
                                                        required property var modelData
                                                        text: String(modelData.label || "")
                                                        checked: (root.workingDayDraft || []).indexOf(modelData.index) >= 0
                                                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                                        onToggled: {
                                                            const next = (root.workingDayDraft || []).slice()
                                                            const idx = next.indexOf(modelData.index)
                                                            if (checked && idx < 0) {
                                                                next.push(modelData.index)
                                                            } else if (!checked && idx >= 0) {
                                                                next.splice(idx, 1)
                                                            }
                                                            root.workingDayDraft = next
                                                        }
                                                    }
                                                }
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: Theme.AppTheme.spacingSm

                                                AppControls.Label {
                                                    text: "Hours/Day"
                                                    color: Theme.AppTheme.textMuted
                                                    font.family: Theme.AppTheme.fontFamily
                                                    font.pixelSize: Theme.AppTheme.captionSize
                                                }

                                                AppControls.TextField {
                                                    Layout.preferredWidth: 96
                                                    text: root.hoursPerDayDraft
                                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                                    onTextChanged: root.hoursPerDayDraft = text
                                                }
                                            }
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: calendarExceptionColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)
                                        radius: Theme.AppTheme.radiusSm
                                        color: Theme.AppTheme.surfaceOverlay
                                        border.color: Theme.AppTheme.subtleBorder
                                        border.width: 1

                                        ColumnLayout {
                                            id: calendarExceptionColumn
                                            anchors.fill: parent
                                            anchors.margins: Theme.AppTheme.marginMd
                                            spacing: Theme.AppTheme.spacingSm

                                            AppControls.Label {
                                                Layout.fillWidth: true
                                                text: "Exceptions & Calculator"
                                                color: Theme.AppTheme.textSecondary
                                                font.family: Theme.AppTheme.fontFamily
                                                font.pixelSize: Theme.AppTheme.captionSize
                                                font.bold: true
                                            }

                                            AppControls.DateField {
                                                id: holidayDateField
                                                Layout.fillWidth: true
                                                placeholderText: "Holiday date (YYYY-MM-DD)"
                                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                            }

                                            AppControls.TextField {
                                                id: holidayNameField
                                                Layout.fillWidth: true
                                                placeholderText: "Exception label"
                                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: Theme.AppTheme.spacingSm

                                                AppControls.DateField {
                                                    id: calcStartField
                                                    Layout.fillWidth: true
                                                    placeholderText: "Calc start (YYYY-MM-DD)"
                                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                                }

                                                AppControls.TextField {
                                                    id: calcDaysField
                                                    Layout.preferredWidth: 96
                                                    placeholderText: "Days"
                                                    enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                                }
                                            }

                                            AppWidgets.InlineMessage {
                                                Layout.fillWidth: true
                                                visible: String(root.workspaceController ? root.workspaceController.calculatorResult : "").length > 0
                                                tone: "success"
                                                message: root.workspaceController ? root.workspaceController.calculatorResult : ""
                                            }
                                        }
                                    }
                                }

                                AppWidgets.InlineMessage {
                                    Layout.fillWidth: true
                                    visible: String(root.calendarModel.summaryText || "").length > 0
                                    tone: "info"
                                    message: root.calendarModel.summaryText || ""
                                }

                                AppWidgets.TableToolbar {
                                    id: calendarsToolbar
                                    Layout.fillWidth: true
                                    searchText: root.workspaceController ? root.workspaceController.calendarsSearchText : ""
                                    searchPlaceholder: "Search calendar exceptions..."
                                    showCustomize: true
                                    showExport: false
                                    showRefresh: false
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    onSearchChanged: function(text) { if (root.workspaceController) root.workspaceController.setCalendarsSearchText(text) }
                                    onCustomizeClicked: holidaysTable.openColumnCustomizer(calendarsToolbar.customizeButtonItem)
                                }

                                AppWidgets.DataTable {
                                    Layout.fillWidth: true
                                    Layout.preferredHeight: 120
                                    columns: root._calendarColumns
                                    sourceModel: root.workspaceController ? root.workspaceController.calendarSummaryTableModel : null
                                    loading: false
                                    emptyText: "No calendar summary is available."
                                }

                                AppWidgets.DataTable {
                                    id: holidaysTable
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    columns: root._holidayColumns
                                    sourceModel: root.workspaceController ? root.workspaceController.holidayTableModel : null
                                    selectedRowId: root.selectedHolidayId
                                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                                    emptyText: root.calendarModel.emptyState || "No holiday exceptions are configured."
                                    onRowSelected: function(rowId) {
                                        root.selectedHolidayId = String(rowId || "")
                                    }
                                }
                            }
                        }

                        SchedulingPanelFrame {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            title: "Activity Feed"
                            subtitle: "Recent planning actions, delay notices, recalculation events, and resource warnings."

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                Layout.margins: Theme.AppTheme.marginMd
                                spacing: Theme.AppTheme.spacingSm

                                SchedulingActionBar {
                                    Layout.fillWidth: true
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    actions: [
                                        { "id": "refresh", "label": "Refresh", "icon": "refresh", "enabled": true }
                                    ]
                                    onActionTriggered: function(actionId) {
                                        if (actionId === "refresh" && root.workspaceController !== null) {
                                            root.workspaceController.refresh()
                                        }
                                    }
                                }

                                AppWidgets.TableToolbar {
                                    Layout.fillWidth: true
                                    searchText: root.feedSearchText
                                    searchPlaceholder: "Search activity..."
                                    showRefresh: false
                                    showExport: false
                                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                                    onSearchChanged: function(text) { root.feedSearchText = text }
                                }

                                AppWidgets.ActivityFeed {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    items: {
                                        const sourceItems = root.activityFeedModel.items || []
                                        const term = String(root.feedSearchText || "").trim().toLowerCase()
                                        if (!term.length) {
                                            return sourceItems
                                        }
                                        const filtered = []
                                        for (let i = 0; i < sourceItems.length; i += 1) {
                                            const item = sourceItems[i]
                                            const haystack = (
                                                String(item.title || "") + " " +
                                                String(item.metaText || "") + " " +
                                                String(item.statusLabel || "")
                                            ).toLowerCase()
                                            if (haystack.indexOf(term) >= 0) {
                                                filtered.push(item)
                                            }
                                        }
                                        return filtered
                                    }
                                    emptyText: root.activityFeedModel.emptyState || "No planning activity has been recorded."
                                }
                            }
                        }
                    }
                }
            }
        }

        Loader {
            id: detailPageLoader
            anchors.fill: parent
            active: root._detailOpen
            visible: root._detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent

            AppWidgets.SectionDetailPage {
                open: true
                anchors.fill: parent
                showHeader: false
                showEdit: false
                showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: [
                    "Overview",
                    "Dependencies",
                    "Constraints",
                    "Calendars",
                    "Baselines",
                    "Resources",
                    "Activity Feed",
                    "Change Impact"
                ]
                z: 20
                Component.onCompleted: scrollToSection(root._pendingDetailSection)

                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root.selectedActivityModel.title || "Activity Details"
                    subtitle: root.selectedActivityModel.statusLabel || root.selectedActivityModel.subtitle || ""
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: []
                    onBackRequested: root._detailOpen = false
                }

                SchedulingDetailPanel {
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    activityDetail: root.selectedActivityModel
                    dependenciesModel: root.dependenciesModel
                    dependencyRows: root.dependencyRows
                    dependencyTableModel: root.workspaceController ? root.workspaceController.dependencyTableModel : null
                    constraintsModel: root.constraintsModel
                    constraintRows: root.constraintRows
                    constraintTableModel: root.workspaceController ? root.workspaceController.constraintTableModel : null
                    calendarModel: root.calendarModel
                    calendarSummaryRows: root.calendarSummaryRows
                    calendarSummaryTableModel: root.workspaceController ? root.workspaceController.calendarSummaryTableModel : null
                    holidayRows: root.holidayRows
                    holidayTableModel: root.workspaceController ? root.workspaceController.holidayTableModel : null
                    baselinesModel: root.baselinesModel
                    baselineCompareRows: root.baselineCompareRows
                    baselineCompareTableModel: root.workspaceController ? root.workspaceController.baselineCompareTableModel : null
                    baselineRegisterModel: root.baselineRegisterModel
                    baselineRegisterRows: root.baselineRegisterRows
                    baselineRegisterTableModel: root.workspaceController ? root.workspaceController.baselineRegisterTableModel : null
                    resourceLoadingModel: root.resourceLoadingModel
                    resourceRows: root.resourceRows
                    resourcesLoadingTableModel: root.workspaceController ? root.workspaceController.resourcesLoadingTableModel : null
                    scheduleImpactTasksTableModel: root.workspaceController ? root.workspaceController.scheduleImpactTasksTableModel : null
                    activityFeedModel: root.activityFeedModel
                    scheduleImpactModel: root.workspaceController ? (root.workspaceController.scheduleImpact || {}) : ({})
                    workspaceController: root.workspaceController
                }
            }
        }
    }
}

