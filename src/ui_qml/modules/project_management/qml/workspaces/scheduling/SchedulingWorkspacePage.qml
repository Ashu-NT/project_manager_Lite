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
import "dialogs" as Dialogs
import "components" as Components

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
    readonly property var delayedRows: root.workspaceController ? (root.workspaceController.delayedActivityRows || []) : []
    readonly property var dependenciesModel: root.workspaceController
        ? root.workspaceController.dependencies
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No dependencies are linked to the selected activity." })
    readonly property var dependencyRows: root.workspaceController ? (root.workspaceController.dependencyRows || []) : []
    readonly property var constraintsModel: root.workspaceController
        ? root.workspaceController.constraints
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No constraints are recorded for the selected activity." })
    readonly property var constraintRows:            root.workspaceController ? (root.workspaceController.constraintRows || []) : []
    readonly property var resourceLoadingModel: root.workspaceController
        ? root.workspaceController.resourceLoading
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No resource load data is available." })
    readonly property var resourceRows:              root.workspaceController ? (root.workspaceController.resourceLoadingRows || []) : []
    readonly property var baselineCompareRows:       root.workspaceController ? (root.workspaceController.baselineCompareRows || []) : []
    readonly property var baselineRegisterRows:      root.workspaceController ? (root.workspaceController.baselineRegisterRows || []) : []
    readonly property var calendarSummaryRows:       root.workspaceController ? (root.workspaceController.calendarSummaryRows || []) : []
    readonly property var holidayRows:               root.workspaceController ? (root.workspaceController.holidayRows || []) : []
    readonly property var timelineModel: root.workspaceController
        ? root.workspaceController.timeline
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No timeline items are available." })

    title:    root.overviewModel.title    || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    // ── State ─────────────────────────────────────────────────────────────
    SchedulingWorkspaceState {
        id: state
        pmCatalog:           root.pmCatalog
        workspaceController: root.workspaceController
    }

    // ── Dialog host ───────────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.SchedulingDialogHost {
                selectedProjectId:    root.workspaceController ? root.workspaceController.selectedProjectId : ""
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

        // ── Panel view ────────────────────────────────────────────────────
        Item {
            anchors.fill: parent
            visible: !state.detailOpen

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
                        ? root.workspaceController.isBusy
                            && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    message: "Applying planning changes..."
                    compact: true
                    modal: false
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: !state.detailOpen
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: !state.detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                // ── Action bar (project / baseline / calendar selectors) ──
                Components.SchedulingActionBar {
                    Layout.fillWidth: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: [
                        { "id": "refresh",  "label": "Refresh", "icon": "refresh", "enabled": true },
                        { "id": "run_cpm",  "label": "Run CPM", "icon": "approve",
                          "enabled": String(root.workspaceController ? root.workspaceController.selectedProjectId : "").length > 0 }
                    ]

                    AppControls.ComboBox {
                        Layout.preferredWidth: 210
                        model:      root.workspaceController ? (root.workspaceController.projectOptions  || []) : []
                        textRole:   "label"
                        enabled:    !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: state.optionIndexForValue(
                            root.workspaceController ? (root.workspaceController.projectOptions || []) : [],
                            root.workspaceController ? root.workspaceController.selectedProjectId : ""
                        )
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.selectProject(String(opts[index].value || ""))
                        }
                    }

                    AppControls.ComboBox {
                        Layout.preferredWidth: 180
                        model:    root.workspaceController ? (root.workspaceController.baselineOptions || []) : []
                        textRole: "label"
                        enabled:  !(root.workspaceController ? root.workspaceController.isBusy : false)
                            && (root.workspaceController ? (root.workspaceController.baselineOptions || []).length > 0 : false)
                        currentIndex: state.optionIndexForValue(
                            root.workspaceController ? (root.workspaceController.baselineOptions || []) : [],
                            root.workspaceController ? root.workspaceController.selectedBaselineId : ""
                        )
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.baselineOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.selectBaseline(String(opts[index].value || ""))
                        }
                    }

                    AppControls.ComboBox {
                        Layout.preferredWidth: 170
                        model:    root.workspaceController ? (root.workspaceController.calendarOptions || []) : []
                        textRole: "label"
                        enabled:  !(root.workspaceController ? root.workspaceController.isBusy : false)
                            && (root.workspaceController ? (root.workspaceController.calendarOptions || []).length > 0 : false)
                        currentIndex: state.optionIndexForValue(
                            root.workspaceController ? (root.workspaceController.calendarOptions || []) : [],
                            root.workspaceController ? root.workspaceController.selectedCalendarId : "default"
                        )
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.calendarOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.selectCalendar(String(opts[index].value || "default"))
                        }
                    }

                    onActionTriggered: function(actionId) {
                        if (root.workspaceController === null) return
                        if      (actionId === "refresh")  root.workspaceController.refresh()
                        else if (actionId === "run_cpm")  root.workspaceController.recalculateSchedule()
                    }
                }

                // ── Panel tab strip ───────────────────────────────────────
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
                            model: state.panelTabs

                            delegate: Rectangle {
                                id: tabButton
                                required property var modelData

                                readonly property bool _active: String(modelData.id || "") === state.activePanelId

                                implicitWidth:  labelRow.implicitWidth + 22
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
                                        color: tabButton._active
                                            ? Theme.AppTheme.navSelectedText
                                            : Theme.AppTheme.textSecondary
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        font.bold:      tabButton._active
                                    }

                                    Rectangle {
                                        visible: parseInt(tabButton.modelData.count || 0, 10) > 0
                                        radius: 8
                                        color:  tabButton._active ? Theme.AppTheme.accent : Theme.AppTheme.surfaceRaised
                                        implicitWidth:  countLabel.implicitWidth + 8
                                        implicitHeight: 16

                                        AppControls.Label {
                                            id: countLabel
                                            anchors.centerIn: parent
                                            text: String(tabButton.modelData.count || "")
                                            color: tabButton._active
                                                ? Theme.AppTheme.textOnAccent
                                                : Theme.AppTheme.textMuted
                                            font.family:    Theme.AppTheme.fontFamily
                                            font.pixelSize: Theme.AppTheme.captionSize
                                            font.bold: true
                                        }
                                    }
                                }

                                MouseArea {
                                    id: tabHover
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape:  Qt.PointingHandCursor
                                    onClicked: state.activePanelId = String(tabButton.modelData.id || "activity_timeline")
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
                        currentIndex: state.panelIndex(state.activePanelId)

                        Panels.SchedulingActivityTimelinePanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                            activityColumns:     state.activityColumns
                            activityTableId:     state.activityTableId
                            timelineModel:       root.timelineModel
                            onActivityColumnsStateChanged: function(cols)   { state.activityColumns = cols }
                            onActivityDetailRequested: function(activityId) { state.openActivityDetail(activityId) }
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
                            workspaceController:             root.workspaceController
                            pmCatalog:                       root.pmCatalog
                            baselinesModel:                  root.baselinesModel
                            selectedBaselineRegisterId:      state.selectedBaselineRegisterId
                            selectedBaselineRegisterStatus:  state.selectedBaselineRegisterStatus
                            onSelectedBaselineRegisterSelectionChanged: function(id) { state.selectedBaselineRegisterId = id }
                            onCreateBaselineRequested: dialogHostLoader.invoke("openCreateBaselineDialog")
                        }

                        Panels.SchedulingDelaysPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                            delayedRows:         root.delayedRows
                            onActivityDetailRequested: function(activityId) { state.openActivityDetail(activityId) }
                        }

                        Panels.SchedulingCalendarsPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                            calendarModel:       root.calendarModel
                        }

                        Panels.SchedulingActivityFeedPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                            activityFeedModel:   root.activityFeedModel
                            feedSearchText:      state.feedSearchText
                            onFeedSearchRequested: function(text) { state.feedSearchText = text }
                        }
                    }
                }
            }
        }

        // ── Detail page ───────────────────────────────────────────────────
        Loader {
            id: detailPageLoader
            anchors.fill: parent
            active:       state.detailOpen
            visible:      state.detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent

            AppWidgets.SectionDetailPage {
                open:        true
                anchors.fill: parent
                showHeader:  false
                showEdit:    false
                showDelete:  false
                isBusy:      root.workspaceController ? root.workspaceController.isBusy : false
                sections:    ["Overview", "Dependencies", "Constraints", "Calendars", "Baselines", "Resources", "Activity Feed", "Change Impact"]
                z:           20
                Component.onCompleted: scrollToSection(state.pendingDetailSection)

                AppWidgets.ContextualActionToolbar {
                    detailPagePinned: true
                    width:     parent ? parent.width : 0
                    showBack:  true
                    title:     root.selectedActivityModel.title    || "Activity Details"
                    subtitle:  root.selectedActivityModel.statusLabel || root.selectedActivityModel.subtitle || ""
                    busy:      root.workspaceController ? root.workspaceController.isBusy : false
                    actions:   []
                    onBackRequested: state.detailOpen = false
                }

                AppWidgets.InlineMessage {
                    width:   parent ? parent.width : 0
                    visible: state.detailOpen
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone:    "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.InlineMessage {
                    width:   parent ? parent.width : 0
                    visible: state.detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone:    "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Panels.SchedulingDetailPanel {
                    width:                          parent ? parent.width : 0
                    detailPage:                     detailPageLoader.item
                    activityDetail:                 root.selectedActivityModel
                    dependenciesModel:              root.dependenciesModel
                    dependencyRows:                 root.dependencyRows
                    dependencyTableModel:           root.workspaceController ? root.workspaceController.dependencyTableModel : null
                    constraintsModel:               root.constraintsModel
                    constraintRows:                 root.constraintRows
                    constraintTableModel:           root.workspaceController ? root.workspaceController.constraintTableModel : null
                    calendarModel:                  root.calendarModel
                    calendarSummaryRows:            root.calendarSummaryRows
                    calendarSummaryTableModel:      root.workspaceController ? root.workspaceController.calendarSummaryTableModel : null
                    holidayRows:                    root.holidayRows
                    holidayTableModel:              root.workspaceController ? root.workspaceController.holidayTableModel : null
                    baselinesModel:                 root.baselinesModel
                    baselineCompareRows:            root.baselineCompareRows
                    baselineCompareTableModel:      root.workspaceController ? root.workspaceController.baselineCompareTableModel : null
                    baselineRegisterModel:          root.baselineRegisterModel
                    baselineRegisterRows:           root.baselineRegisterRows
                    baselineRegisterTableModel:     root.workspaceController ? root.workspaceController.baselineRegisterTableModel : null
                    resourceLoadingModel:           root.resourceLoadingModel
                    resourceRows:                   root.resourceRows
                    resourcesLoadingTableModel:     root.workspaceController ? root.workspaceController.resourcesLoadingTableModel : null
                    scheduleImpactTasksTableModel:  root.workspaceController ? root.workspaceController.scheduleImpactTasksTableModel : null
                    activityFeedModel:              root.activityFeedModel
                    scheduleImpactModel:            root.workspaceController ? (root.workspaceController.scheduleImpact || {}) : ({})
                    workspaceController:            root.workspaceController
                }
            }
        }
    }
}
