pragma ComponentBehavior: Bound

import QtQuick
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
    readonly property ProjectManagementControllers.PMWorkspaceNavigationController pmNavigation: root.pmCatalog
        ? root.pmCatalog.pmNavigation
        : null
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
    readonly property var calendarModel: root.workspaceController
        ? root.workspaceController.calendar
        : ({ "summaryText": "", "workingDays": [], "hoursPerDay": "8", "holidays": [], "emptyState": "No calendar data is available." })
    readonly property var selectedActivityModel: root.workspaceController
        ? root.workspaceController.selectedActivity
        : ({ "id": "", "title": "", "statusLabel": "", "subtitle": "", "description": "", "emptyState": "Select an activity from the schedule table to inspect the planning logic.", "fields": [], "state": {} })
    readonly property var activityFeedModel: root.workspaceController
        ? root.workspaceController.activityFeed
        : ({ "title": "", "subtitle": "", "items": [], "emptyState": "No planning activity has been recorded." })

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
                onCreateBaselineRequested: function(payload) {
                    if (root.workspaceController !== null) root.workspaceController.createBaseline(payload)
                }
            }
        }
    }

    // ── Main stacked layout ───────────────────────────────────────────────
    Item {
        anchors.fill: parent

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

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

                // ── Persistent Planning context header (Project / Refresh / Run CPM) ──
                Components.SchedulingPlanningContextHeader {
                    Layout.fillWidth: true
                    workspaceController: root.workspaceController
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
                            model: state.primaryPanelTabs

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
                                    onClicked: state.activePanelId = String(tabButton.modelData.id || "overview")
                                }
                            }
                        }

                        AppWidgets.NavOverflowMenu {
                            items:        state.secondaryPanelTabs
                            activeId:     state.activePanelId
                            triggerLabel: "More"
                            onItemSelected: function(itemId) { state.activePanelId = itemId }
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

                        Panels.SchedulingOverviewPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                            overviewModel:       root.overviewModel
                        }

                        Panels.SchedulingGanttPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController:   root.workspaceController
                            activityColumns:       state.activityColumns
                            activityTableId:       state.activityTableId
                            selectedActivityModel: root.selectedActivityModel
                            onActivityColumnsStateChanged: function(cols) { state.activityColumns = cols }
                            onActivityDetailRequested: function(activityId) {
                                if (root.workspaceController !== null) root.workspaceController.selectActivity(activityId)
                                if (root.pmNavigation) {
                                    root.pmNavigation.openEntity("tasks", activityId, "")
                                }
                            }
                        }

                        Panels.SchedulingResourceLevelingPanel {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            workspaceController: root.workspaceController
                        }

                        Panels.SchedulingDiagnosticsPanel {
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
}
