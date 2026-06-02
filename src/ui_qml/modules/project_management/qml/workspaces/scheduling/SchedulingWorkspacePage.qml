pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "panels" as Panels

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementSchedulingWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.schedulingWorkspace
        : null

    // ── Models ────────────────────────────────────────────────────────────
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({ "routeId": "project_management.scheduling", "title": "Scheduling", "summary": "Enterprise planning and schedule control workspace." })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({ "title": root.workspaceModel.title, "subtitle": root.workspaceModel.summary, "metrics": [] })
    readonly property var scheduleModel: root.workspaceController
        ? root.workspaceController.schedule
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "Scheduling desktop API is not connected in this QML preview." })
    readonly property var timelineModel: root.workspaceController
        ? root.workspaceController.timeline
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No timeline items are available." })
    readonly property var baselinesModel: root.workspaceController
        ? root.workspaceController.baselines
        : ({ "options": [], "selectedBaselineAId": "", "selectedBaselineBId": "", "includeUnchanged": false, "summaryText": "", "emptyState": "", "rows": [] })
    readonly property var baselineRegisterModel: root.workspaceController
        ? root.workspaceController.baselineRegister
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No baseline register entries are available." })
    readonly property var calendarModel: root.workspaceController
        ? root.workspaceController.calendar
        : ({ "summaryText": "", "workingDays": [], "hoursPerDay": "8", "holidays": [], "emptyState": "No calendar data is available." })
    readonly property var selectedActivityModel: root.workspaceController
        ? root.workspaceController.selectedActivity
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "emptyState": "Select an activity from the schedule table to inspect the planning logic.", "fields": [], "state": {} })
    readonly property var activityFeedModel: root.workspaceController
        ? root.workspaceController.activityFeed
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No planning activity has been recorded." })
    readonly property var delayedRows: root.workspaceController
        ? (root.workspaceController.delayedActivityRows || [])
        : []
    readonly property var dependenciesModel: root.workspaceController
        ? root.workspaceController.dependencies
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No dependencies are linked to the selected activity." })
    readonly property var dependencyRows: root.workspaceController ? (root.workspaceController.dependencyRows || []) : []
    readonly property var constraintsModel: root.workspaceController
        ? root.workspaceController.constraints
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No constraints are recorded for the selected activity." })
    readonly property var constraintRows: root.workspaceController ? (root.workspaceController.constraintRows || []) : []
    readonly property var resourceLoadingModel: root.workspaceController
        ? root.workspaceController.resourceLoading
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No resource load data is available." })
    readonly property var resourceRows: root.workspaceController ? (root.workspaceController.resourceLoadingRows || []) : []
    readonly property var baselineCompareRows: root.workspaceController ? (root.workspaceController.baselineCompareRows || []) : []
    readonly property var baselineRegisterRows: root.workspaceController ? (root.workspaceController.baselineRegisterRows || []) : []
    readonly property var calendarSummaryRows: root.workspaceController ? (root.workspaceController.calendarSummaryRows || []) : []
    readonly property var holidayRows: root.workspaceController ? (root.workspaceController.holidayRows || []) : []

    // ── State ─────────────────────────────────────────────────────────────
    property string activePanelId: "activity_timeline"
    property string feedSearchText: ""
    property string selectedBaselineRegisterId: ""
    property string selectedHolidayId: ""
    property var workingDayDraft: []
    property string hoursPerDayDraft: "8"
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item

    // ── Activity columns ──────────────────────────────────────────────────
    property string _activityTableId: "pm.scheduling.activity.table"
    property var _activityColumns: []

    readonly property string selectedBaselineRegisterStatus: {
        const rows = root.baselineRegisterRows || []
        const targetId = root.selectedBaselineRegisterId
        for (let i = 0; i < rows.length; i++) {
            if (String(rows[i].id || "") === targetId)
                return String(rows[i].status || "").toLowerCase()
        }
        return ""
    }

    // ── Column helpers ────────────────────────────────────────────────────
    function _activityBaseColumns() {
        return [
            { "key": "activityCode",      "label": "Activity ID", "flex": 0,   "minWidth": 96,  "sortable": true,  "required": true,  "visibleByDefault": true  },
            { "key": "wbs",               "label": "WBS",         "flex": 0,   "minWidth": 72,  "sortable": true,  "visibleByDefault": true  },
            { "key": "taskName",          "label": "Task Name",   "flex": 2.1, "sortable": true, "required": true, "visibleByDefault": true  },
            { "key": "start",             "label": "Start",       "flex": 0,   "minWidth": 90,  "visibleByDefault": true  },
            { "key": "finish",            "label": "Finish",      "flex": 0,   "minWidth": 90,  "visibleByDefault": true  },
            { "key": "duration",          "label": "Duration",    "flex": 0,   "minWidth": 88,  "visibleByDefault": true  },
            { "key": "remainingDuration", "label": "Remaining",   "flex": 0,   "minWidth": 100, "visibleByDefault": true  },
            { "key": "float",             "label": "Float",       "flex": 0,   "minWidth": 72,  "visibleByDefault": true  },
            { "key": "critical",          "label": "Critical",    "flex": 0,   "minWidth": 88,  "type": "status",  "visibleByDefault": true  },
            { "key": "constraint",        "label": "Constraint",  "flex": 1.1, "visibleByDefault": false },
            { "key": "calendar",          "label": "Calendar",    "flex": 0.9, "visibleByDefault": false },
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

    // ── Helpers ───────────────────────────────────────────────────────────
    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    readonly property var _panelTabs: [
        { "id": "activity_timeline", "label": "Activity & Timeline" },
        { "id": "diagnostics",       "label": "Diagnostics" },
        { "id": "resources",         "label": "Resources" },
        { "id": "baselines",         "label": "Baselines" },
        { "id": "delays",            "label": "Delays" },
        { "id": "calendars",         "label": "Calendars" },
        { "id": "activity_feed",     "label": "Activity Feed" }
    ]

    function _panelIndex(panelId) {
        for (let i = 0; i < root._panelTabs.length; i++) {
            if (String(root._panelTabs[i].id || "") === String(panelId || "")) return i
        }
        return 0
    }

    function _optionIndexForValue(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return list.length > 0 ? 0 : -1
    }

    function _syncCalendarDraft() {
        const selected = []
        const workingDays = root.calendarModel.workingDays || []
        for (let i = 0; i < workingDays.length; i++) {
            if (workingDays[i].checked) selected.push(workingDays[i].index)
        }
        root.workingDayDraft = selected
        root.hoursPerDayDraft = String(root.calendarModel.hoursPerDay || "8")
    }

    function _openActivityDetail(activityId) {
        if (root.workspaceController === null || !String(activityId || "").length) return
        root.workspaceController.activateActivity(String(activityId || ""))
        root._pendingDetailSection = 0
        root._detailOpen = true
        if (detailPage) detailPage.scrollToSection(0)
    }

    onCalendarModelChanged: root._syncCalendarDraft()

    Component.onCompleted: {
        const base = root._activityBaseColumns()
        if (root.workspaceController !== null) {
            const saved = root.workspaceController.loadTableColumnState(root._activityTableId)
            root._activityColumns = root._applyColumnState(base, saved)
        } else {
            root._activityColumns = base
        }
        root._syncCalendarDraft()
    }

    // ── Dialog host ───────────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            SchedulingDialogHost {
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                selectedActivityData: root.selectedActivityModel
                onCreateBaselineRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createBaseline(payload)
                }
            }
        }
    }

    // ── Main stacked layout ───────────────────────────────────────────────
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

                AppWidgets.LoadingOverlay {
                    Layout.fillWidth: true
                    loading: (root.workspaceController ? root.workspaceController.isLoading : false)
                        && !(root.workspaceController ? root.workspaceController.isBusy : false)
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    message: "Loading scheduling data..."
                    compact: true
                    modal: false
                }

                AppWidgets.LoadingOverlay {
                    Layout.fillWidth: true
                    loading: root.workspaceController
                        ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    message: "Applying planning changes..."
                    compact: true
                    modal: false
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: !root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: !root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                SchedulingActionBar {
                    Layout.fillWidth: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: [
                        { "id": "refresh", "label": "Refresh", "icon": "refresh", "enabled": true },
                        { "id": "run_cpm", "label": "Run CPM", "icon": "approve",  "enabled": String(root.workspaceController ? root.workspaceController.selectedProjectId : "").length > 0 }
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
                            if (root.workspaceController !== null && options[index])
                                root.workspaceController.selectProject(String(options[index].value || ""))
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
                            if (root.workspaceController !== null && options[index])
                                root.workspaceController.selectBaseline(String(options[index].value || ""))
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
                            if (root.workspaceController !== null && options[index])
                                root.workspaceController.selectCalendar(String(options[index].value || "default"))
                        }
                    }

                    onActionTriggered: function(actionId) {
                        if (root.workspaceController === null) return
                        if (actionId === "refresh") root.workspaceController.refresh()
                        else if (actionId === "run_cpm") root.workspaceController.recalculateSchedule()
                    }
                }

                // ── Tab navigation ────────────────────────────────────────
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
                                border.color: tabButton._active ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder
                                border.width: tabButton._active ? 1 : 0

                                RowLayout {
                                    id: labelRow
                                    anchors.centerIn: parent
                                    spacing: Theme.AppTheme.spacingXs

                                    AppControls.Label {
                                        text: String(tabButton.modelData.label || "")
                                        color: tabButton._active ? Theme.AppTheme.navSelectedText : Theme.AppTheme.textSecondary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold: tabButton._active
                                    }

                                    Rectangle {
                                        visible: parseInt(tabButton.modelData.count || 0, 10) > 0
                                        radius: 8
                                        color: tabButton._active ? Theme.AppTheme.accent : Theme.AppTheme.surfaceRaised
                                        implicitWidth: countLabel.implicitWidth + 8
                                        implicitHeight: 16

                                        AppControls.Label {
                                            id: countLabel
                                            anchors.centerIn: parent
                                            text: String(tabButton.modelData.count || "")
                                            color: tabButton._active ? Theme.AppTheme.textOnAccent : Theme.AppTheme.textMuted
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

                // ── Panel stack ───────────────────────────────────────────
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    StackLayout {
                        anchors.fill: parent
                        currentIndex: root._panelIndex(root.activePanelId)

                        Panels.SchedulingActivityTimelinePanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                            activityColumns: root._activityColumns
                            activityTableId: root._activityTableId
                            timelineModel: root.timelineModel
                            onActivityColumnsChanged: function(cols) { root._activityColumns = cols }
                            onActivityDetailRequested: function(activityId) { root._openActivityDetail(activityId) }
                        }

                        Panels.SchedulingDiagnosticsPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                        }

                        Panels.SchedulingResourcesPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                        }

                        Panels.SchedulingBaselinesPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                            pmCatalog: root.pmCatalog
                            baselinesModel: root.baselinesModel
                            selectedBaselineRegisterId: root.selectedBaselineRegisterId
                            selectedBaselineRegisterStatus: root.selectedBaselineRegisterStatus
                            onSelectedBaselineRegisterIdChanged: function(id) { root.selectedBaselineRegisterId = id }
                            onCreateBaselineRequested: dialogHostLoader.invoke("openCreateBaselineDialog")
                        }

                        Panels.SchedulingDelaysPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                            delayedRows: root.delayedRows
                            onActivityDetailRequested: function(activityId) { root._openActivityDetail(activityId) }
                        }

                        Panels.SchedulingCalendarsPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                            calendarModel: root.calendarModel
                            workingDayDraft: root.workingDayDraft
                            hoursPerDayDraft: root.hoursPerDayDraft
                            selectedHolidayId: root.selectedHolidayId
                            onWorkingDayDraftChanged: function(draft) { root.workingDayDraft = draft }
                            onHoursPerDayDraftChanged: function(hours) { root.hoursPerDayDraft = hours }
                            onSelectedHolidayIdChanged: function(id) { root.selectedHolidayId = id }
                        }

                        Panels.SchedulingActivityFeedPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                            activityFeedModel: root.activityFeedModel
                            feedSearchText: root.feedSearchText
                            onFeedSearchTextChanged: function(text) { root.feedSearchText = text }
                        }
                    }
                }
            }
        }

        // ── Detail page ───────────────────────────────────────────────────
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
                sections: ["Overview", "Dependencies", "Constraints", "Calendars", "Baselines", "Resources", "Activity Feed", "Change Impact"]
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

                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: root._detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
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
