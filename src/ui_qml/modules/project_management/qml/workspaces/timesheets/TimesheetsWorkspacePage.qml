import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementTimesheetsWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.timesheetsWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.timesheets",
            "title": "Timesheets",
            "summary": "Time entry, review, labor capture, and project time reporting.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget timesheets workspace remains active"
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

            ProjectManagementWidgets.RegisterMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            ProjectManagementWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            ProjectManagementWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML timesheet capture and review slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Assignment-level time entry, resource-period submission, and review-queue approval flows now run through a typed PM controller backed by the timesheets desktop API."
            }

            TimesheetsToolbarSection {
                Layout.fillWidth: true
                projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                assignmentOptions: root.workspaceController ? (root.workspaceController.assignmentOptions || []) : []
                periodOptions: root.workspaceController ? (root.workspaceController.periodOptions || []) : []
                queueStatusOptions: root.workspaceController ? (root.workspaceController.queueStatusOptions || []) : []
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : "all"
                selectedAssignmentId: root.workspaceController ? root.workspaceController.selectedAssignmentId : ""
                selectedPeriodStart: root.workspaceController ? root.workspaceController.selectedPeriodStart : ""
                selectedQueueStatus: root.workspaceController ? root.workspaceController.selectedQueueStatus : "SUBMITTED"
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onProjectChanged: function(value) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectProject(value)
                    }
                }

                onAssignmentChanged: function(value) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectAssignment(value)
                    }
                }

                onPeriodChanged: function(value) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectPeriod(value)
                    }
                }

                onQueueStatusChanged: function(value) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setQueueStatus(value)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1340 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                TimesheetsEntriesSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    assignmentSummary: root.workspaceController ? root.workspaceController.assignmentSummary : ({
                        "title": "",
                        "subtitle": "",
                        "emptyState": "",
                        "fields": [],
                        "state": {}
                    })
                    entriesModel: root.workspaceController ? root.workspaceController.entries : ({
                        "title": "",
                        "subtitle": "",
                        "emptyState": "",
                        "items": []
                    })
                    selectedEntryDetail: root.workspaceController ? root.workspaceController.selectedEntry : ({
                        "title": "",
                        "subtitle": "",
                        "emptyState": "",
                        "fields": [],
                        "state": {}
                    })
                    selectedEntryId: root.workspaceController ? root.workspaceController.selectedEntryId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEntrySelected: function(entryId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectEntry(entryId)
                        }
                    }

                    onAddRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.addTimeEntry(payload)
                        }
                    }

                    onUpdateRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.updateTimeEntry(payload)
                        }
                    }

                    onDeleteRequested: function(entryId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.deleteTimeEntry(entryId)
                        }
                    }

                    onSubmitRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.submitPeriod(payload)
                        }
                    }

                    onLockRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.lockPeriod(payload)
                        }
                    }

                    onUnlockRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.unlockPeriod(payload)
                        }
                    }
                }

                TimesheetsReviewSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    reviewQueueModel: root.workspaceController ? root.workspaceController.reviewQueue : ({
                        "title": "",
                        "subtitle": "",
                        "emptyState": "",
                        "items": []
                    })
                    reviewDetail: root.workspaceController ? root.workspaceController.reviewDetail : ({
                        "title": "",
                        "subtitle": "",
                        "emptyState": "",
                        "fields": [],
                        "state": {}
                    })
                    selectedQueuePeriodId: root.workspaceController ? root.workspaceController.selectedQueuePeriodId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onQueuePeriodSelected: function(periodId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectQueuePeriod(periodId)
                        }
                    }

                    onApproveRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.approvePeriod(payload)
                        }
                    }

                    onRejectRequested: function(payload) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.rejectPeriod(payload)
                        }
                    }
                }
            }
        }
    }
}
