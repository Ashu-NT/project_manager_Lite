import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementRegisterWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.riskWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.risk",
            "title": "Risk",
            "summary": "Project risk register, mitigation, severity, and review workflows.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget risk workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var entriesModel: root.workspaceController
        ? root.workspaceController.entries
        : ({
            "title": "Risk Register",
            "subtitle": "Track delivery risks, mitigation owners, and due-date pressure.",
            "emptyState": "Project-management risk desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedEntryModel: root.workspaceController
        ? root.workspaceController.selectedEntry
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a risk entry to review mitigation details.",
            "fields": [],
            "state": {}
        })
    readonly property var urgentModel: root.workspaceController
        ? root.workspaceController.urgentEntries
        : ({
            "title": "Urgent Review Queue",
            "subtitle": "Severity-first shortlist to help triage what needs attention next.",
            "emptyState": "No urgent risk items are available in this QML preview.",
            "items": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    ProjectManagementWidgets.RegisterDialogHost {
        id: dialogHost

        projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
        typeOptions: root.workspaceController ? (root.workspaceController.typeOptions || []) : []
        statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
        severityOptions: root.workspaceController ? (root.workspaceController.severityOptions || []) : []
        typeFieldVisible: false
        fixedTypeValue: "RISK"
        entryLabel: "Risk"

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createEntry(payload)
            }
        }

        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateEntry(payload)
            }
        }

        onDeleteRequested: function(entryId) {
            if (root.workspaceController !== null) {
                root.workspaceController.deleteEntry(entryId)
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
                    ? "QML risk register slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Project risk triage, severity filters, mitigation detail, and create/edit/delete flows now run through a typed PM controller backed by the register desktop API."
            }

            ProjectManagementWidgets.RegisterFiltersSection {
                Layout.fillWidth: true
                projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                typeOptions: root.workspaceController ? (root.workspaceController.typeOptions || []) : []
                statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                severityOptions: root.workspaceController ? (root.workspaceController.severityOptions || []) : []
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : "all"
                selectedTypeFilter: root.workspaceController ? root.workspaceController.selectedTypeFilter : "RISK"
                selectedStatusFilter: root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                selectedSeverityFilter: root.workspaceController ? root.workspaceController.selectedSeverityFilter : "all"
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                showTypeFilter: false
                createButtonLabel: "New Risk"

                onProjectChanged: function(projectId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectProject(projectId)
                    }
                }

                onStatusChanged: function(statusValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setStatusFilter(statusValue)
                    }
                }

                onSeverityChanged: function(severityValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSeverityFilter(severityValue)
                    }
                }

                onSearchTextUpdated: function(searchText) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSearchText(searchText)
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

                ProjectManagementWidgets.RegisterCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    entriesModel: root.entriesModel
                    selectedEntryId: root.workspaceController ? root.workspaceController.selectedEntryId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEntrySelected: function(entryId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectEntry(entryId)
                        }
                    }

                    onEditRequested: function(entryData) {
                        if (entryData && entryData.id && root.workspaceController !== null) {
                            root.workspaceController.selectEntry(entryData.id)
                        }
                        dialogHost.openEditDialog(entryData)
                    }

                    onDeleteRequested: function(entryData) {
                        if (entryData && entryData.id && root.workspaceController !== null) {
                            root.workspaceController.selectEntry(entryData.id)
                        }
                        dialogHost.openDeleteDialog(entryData)
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: 12

                    ProjectManagementWidgets.RegisterDetailSection {
                        Layout.fillWidth: true
                        entryDetail: root.selectedEntryModel
                        isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                        onEditRequested: dialogHost.openEditDialog(root.selectedEntryModel)
                        onDeleteRequested: dialogHost.openDeleteDialog(root.selectedEntryModel)
                    }

                    ProjectManagementWidgets.RegisterUrgentSection {
                        Layout.fillWidth: true
                        urgentModel: root.urgentModel
                        selectedEntryId: root.workspaceController ? root.workspaceController.selectedEntryId : ""

                        onEntrySelected: function(entryId) {
                            if (root.workspaceController !== null) {
                                root.workspaceController.selectEntry(entryId)
                            }
                        }
                    }
                }
            }
        }
    }
}
