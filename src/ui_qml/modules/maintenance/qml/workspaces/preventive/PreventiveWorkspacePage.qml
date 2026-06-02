pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import Maintenance.Controllers 1.0 as MaintenanceControllers
import Maintenance.Widgets 1.0 as MaintenanceWidgets
import "sections" as Sections

AppLayouts.WorkspaceFrame {
    id: root

    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog
    property MaintenanceControllers.MaintenancePreventiveWorkspaceController workspaceController: root.maintenanceCatalog
        ? root.maintenanceCatalog.preventiveWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "maintenance_management.preventive",
            "title": "Preventive",
            "summary": "Plans, task templates, generated work packages, and schedule compliance management.",
            "migrationStatus": "QML preventive slice active",
            "legacyRuntimeStatus": "Existing QWidget workspace remains active"
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

    function recordState(recordData) {
        return recordData && recordData.state ? recordData.state : (recordData || {})
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            Dialogs.PreventiveDialogHost {

        planFormOptions: root.workspaceController ? (root.workspaceController.planFormOptions || {}) : ({})
        planTaskFormOptions: root.workspaceController ? (root.workspaceController.planTaskFormOptions || {}) : ({})
        templateFormOptions: root.workspaceController ? (root.workspaceController.templateFormOptions || {}) : ({})
        stepFormOptions: root.workspaceController ? (root.workspaceController.stepFormOptions || {}) : ({})

                workspaceController: root.workspaceController
            }
        }
    }

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: 12

            AppWidgets.KpiStrip {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            MaintenanceWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            MaintenanceWidgets.WorkspaceStatusSection {
                visible: false
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML preventive slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Preventive queue, plan-library governance, and task-template maintenance now run through one typed maintenance controller backed by the preventive desktop API."
            }

            TabBar {
                id: preventiveTabs
                Layout.fillWidth: true

                TabButton { text: "Queue" }
                TabButton { text: "Plans" }
                TabButton { text: "Templates" }
            }

            StackLayout {
                Layout.fillWidth: true
                currentIndex: preventiveTabs.currentIndex

                Sections.PreventiveQueueSection {
                    queueState: root.workspaceController ? (root.workspaceController.queueState || {}) : ({})
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSiteFilterUpdated: function(siteId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setQueueSiteFilter(siteId)
                        }
                    }

                    onDueStateFilterUpdated: function(dueState) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setQueueDueStateFilter(dueState)
                        }
                    }

                    onSearchTextUpdated: function(searchText) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setQueueSearchText(searchText)
                        }
                    }

                    onRefreshRequested: function() {
                        if (root.workspaceController !== null) {
                            root.workspaceController.refresh()
                        }
                    }

                    onPlanSelected: function(planId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectQueuePlan(planId)
                        }
                    }

                    onRegenerateRequested: function(planId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.regeneratePlanSchedule(planId)
                        }
                    }

                    onGenerateRequested: function(planId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.generateDueWork(planId)
                        }
                    }
                }

                Sections.PreventivePlansSection {
                    planLibraryState: root.workspaceController ? (root.workspaceController.planLibraryState || {}) : ({})
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSiteFilterUpdated: function(siteId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setPlanSiteFilter(siteId)
                        }
                    }

                    onAssetFilterUpdated: function(assetId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setPlanAssetFilter(assetId)
                        }
                    }

                    onSystemFilterUpdated: function(systemId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setPlanSystemFilter(systemId)
                        }
                    }

                    onActiveFilterUpdated: function(activeFilter) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setPlanActiveFilter(activeFilter)
                        }
                    }

                    onStatusFilterUpdated: function(status) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setPlanStatusFilter(status)
                        }
                    }

                    onPlanTypeFilterUpdated: function(planType) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setPlanTypeFilter(planType)
                        }
                    }

                    onTriggerModeFilterUpdated: function(triggerMode) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setPlanTriggerModeFilter(triggerMode)
                        }
                    }

                    onSearchTextUpdated: function(searchText) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setPlanSearchText(searchText)
                        }
                    }

                    onRefreshRequested: function() {
                        if (root.workspaceController !== null) {
                            root.workspaceController.refresh()
                        }
                    }

                    onCreatePlanRequested: dialogHostLoader.invoke("openCreatePlanDialog")

                    onPlanSelected: function(planId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectPlan(planId)
                        }
                    }

                    onEditPlanRequested: function(planData) {
                        dialogHostLoader.invoke("openEditPlanDialog", planData)
                    }

                    onTogglePlanRequested: function(planData) {
                        if (root.workspaceController !== null) {
                            const state = root.recordState(planData)
                            root.workspaceController.togglePlanActive(
                                String(state.planId || ""),
                                !Boolean(state.isActive),
                                Number(state.expectedVersion || 0)
                            )
                        }
                    }

                    onCreatePlanTaskRequested: function(planId) {
                        dialogHostLoader.invoke("openCreatePlanTaskDialog", planId)
                    }

                    onPlanTaskSelected: function(planTaskId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectPlanTask(planTaskId)
                        }
                    }

                    onEditPlanTaskRequested: function(planTaskData) {
                        dialogHostLoader.invoke("openEditPlanTaskDialog", planTaskData)
                    }
                }

                Sections.PreventiveTemplatesSection {
                    templateLibraryState: root.workspaceController ? (root.workspaceController.templateLibraryState || {}) : ({})
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onActiveFilterUpdated: function(activeFilter) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setTemplateActiveFilter(activeFilter)
                        }
                    }

                    onMaintenanceTypeFilterUpdated: function(maintenanceType) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setTemplateMaintenanceTypeFilter(maintenanceType)
                        }
                    }

                    onStatusFilterUpdated: function(templateStatus) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setTemplateStatusFilter(templateStatus)
                        }
                    }

                    onSearchTextUpdated: function(searchText) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.setTemplateSearchText(searchText)
                        }
                    }

                    onRefreshRequested: function() {
                        if (root.workspaceController !== null) {
                            root.workspaceController.refresh()
                        }
                    }

                    onCreateTaskTemplateRequested: dialogHostLoader.invoke("openCreateTaskTemplateDialog")

                    onTaskTemplateSelected: function(taskTemplateId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectTaskTemplate(taskTemplateId)
                        }
                    }

                    onEditTaskTemplateRequested: function(taskTemplateData) {
                        dialogHostLoader.invoke("openEditTaskTemplateDialog", taskTemplateData)
                    }

                    onToggleTaskTemplateRequested: function(taskTemplateData) {
                        if (root.workspaceController !== null) {
                            const state = root.recordState(taskTemplateData)
                            root.workspaceController.toggleTaskTemplateActive(
                                String(state.taskTemplateId || ""),
                                !Boolean(state.isActive),
                                Number(state.expectedVersion || 0)
                            )
                        }
                    }

                    onCreateTaskStepRequested: function(taskTemplateId) {
                        dialogHostLoader.invoke("openCreateTaskStepDialog", taskTemplateId)
                    }

                    onTaskStepSelected: function(taskStepTemplateId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectTaskStep(taskStepTemplateId)
                        }
                    }

                    onEditTaskStepRequested: function(taskStepData) {
                        dialogHostLoader.invoke("openEditTaskStepDialog", taskStepData)
                    }

                    onToggleTaskStepRequested: function(taskStepData) {
                        if (root.workspaceController !== null) {
                            const state = root.recordState(taskStepData)
                            root.workspaceController.toggleTaskStepActive(
                                String(state.taskStepTemplateId || ""),
                                !Boolean(state.isActive),
                                Number(state.expectedVersion || 0)
                            )
                        }
                    }
                }
            }
        }
    }
}
