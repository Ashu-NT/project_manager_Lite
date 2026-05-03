import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

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
            "summary": "Calendars, baseline comparison, dependency graphs, and critical-path views.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget scheduling workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: 12

            SchedulingToolbarSection {
                Layout.fillWidth: true
                projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onProjectSelected: function(projectId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectProject(projectId)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }

                onRecalculateRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.recalculateSchedule()
                    }
                }
            }

            ProjectManagementWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            SchedulingMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            ProjectManagementWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML scheduling operations slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Calendar setup, working-day calculation, schedule recalculation, baseline comparison, and critical-path preview now flow through a typed PM controller backed by the scheduling desktop API."
            }

            SchedulingCalendarSection {
                Layout.fillWidth: true
                calendarModel: root.workspaceController ? root.workspaceController.calendar : ({})
                calculatorResult: root.workspaceController ? root.workspaceController.calculatorResult : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onSaveCalendarRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.saveCalendar(payload)
                    }
                }

                onAddHolidayRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.addHoliday(payload)
                    }
                }

                onDeleteHolidayRequested: function(holidayId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.deleteHoliday(holidayId)
                    }
                }

                onCalculateRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.calculateWorkingDays(payload)
                    }
                }
            }

            SchedulingBaselineSection {
                Layout.fillWidth: true
                baselinesModel: root.workspaceController ? root.workspaceController.baselines : ({})
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onBaselineASelected: function(baselineId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectBaselineA(baselineId)
                    }
                }

                onBaselineBSelected: function(baselineId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectBaselineB(baselineId)
                    }
                }

                onIncludeUnchangedUpdated: function(includeUnchanged) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setIncludeUnchanged(includeUnchanged)
                    }
                }

                onCreateBaselineRequested: function(payload) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.createBaseline(payload)
                    }
                }

                onDeleteBaselineRequested: function(baselineId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.deleteBaseline(baselineId)
                    }
                }
            }

            SchedulingScheduleSection {
                Layout.fillWidth: true
                scheduleModel: root.workspaceController ? root.workspaceController.schedule : ({})
                criticalPathModel: root.workspaceController ? root.workspaceController.criticalPath : ({})
            }
        }
    }
}
