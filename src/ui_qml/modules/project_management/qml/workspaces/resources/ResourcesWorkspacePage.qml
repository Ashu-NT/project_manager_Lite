import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementResourcesWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.resourcesWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.resources",
            "title": "Resources",
            "summary": "Resource capacity, allocation, project assignments, and utilization views.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget resources workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var resourcesModel: root.workspaceController
        ? root.workspaceController.resources
        : ({
            "title": "Resource Pool",
            "subtitle": "Manage capacity, worker types, and resource availability.",
            "emptyState": "Project-management resources desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedResourceModel: root.workspaceController
        ? root.workspaceController.selectedResource
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a resource from the catalog to review details or edit its setup.",
            "fields": [],
            "state": {}
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    ResourcesDialogHost {
        id: dialogHost

        workerTypeOptions: root.workspaceController ? (root.workspaceController.workerTypeOptions || []) : []
        categoryOptions: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
        employeeOptions: root.workspaceController ? (root.workspaceController.employeeOptions || []) : []

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createResource(payload)
            }
        }

        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateResource(payload)
            }
        }

        onDeleteRequested: function(resourceId) {
            if (root.workspaceController !== null) {
                root.workspaceController.deleteResource(resourceId)
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

            ResourcesMetricsSection {
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
                    ? "QML CRUD resources slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Resource pool filters, employee-linked worker setup, create, edit, active toggle, and delete flows now run through a typed PM controller backed by the resources desktop API."
            }

            ResourcesFiltersSection {
                Layout.fillWidth: true
                categoryOptions: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                selectedActiveFilter: root.workspaceController ? root.workspaceController.selectedActiveFilter : "all"
                selectedCategoryFilter: root.workspaceController ? root.workspaceController.selectedCategoryFilter : "all"
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onSearchTextUpdated: function(searchText) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSearchText(searchText)
                    }
                }

                onActiveFilterUpdated: function(activeValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setActiveFilter(activeValue)
                    }
                }

                onCategoryFilterUpdated: function(categoryValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setCategoryFilter(categoryValue)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }

                onCreateRequested: function() {
                    dialogHost.openCreateDialog()
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                ResourcesCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    resourcesModel: root.resourcesModel
                    selectedResourceId: root.workspaceController ? root.workspaceController.selectedResourceId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onResourceSelected: function(resourceId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectResource(resourceId)
                        }
                    }

                    onEditRequested: function(resourceData) {
                        if (resourceData && resourceData.id && root.workspaceController !== null) {
                            root.workspaceController.selectResource(resourceData.id)
                        }
                        dialogHost.openEditDialog(resourceData)
                    }

                    onToggleRequested: function(resourceData) {
                        if (!resourceData || !resourceData.state || root.workspaceController === null) {
                            return
                        }
                        root.workspaceController.toggleResourceActive(
                            String(resourceData.state.resourceId || ""),
                            parseInt(String(resourceData.state.version || "0"), 10)
                        )
                    }

                    onDeleteRequested: function(resourceData) {
                        if (resourceData && resourceData.id && root.workspaceController !== null) {
                            root.workspaceController.selectResource(resourceData.id)
                        }
                        dialogHost.openDeleteDialog(resourceData)
                    }
                }

                ResourcesDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    resourceDetail: root.selectedResourceModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEditRequested: dialogHost.openEditDialog(root.selectedResourceModel)
                    onToggleRequested: {
                        var state = root.selectedResourceModel && root.selectedResourceModel.state
                            ? root.selectedResourceModel.state
                            : {}
                        if (root.workspaceController !== null && state.resourceId) {
                            root.workspaceController.toggleResourceActive(
                                String(state.resourceId || ""),
                                parseInt(String(state.version || "0"), 10)
                            )
                        }
                    }
                    onDeleteRequested: dialogHost.openDeleteDialog(root.selectedResourceModel)
                }
            }
        }
    }
}
