import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementRegisterWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.registerWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.register",
            "title": "Register",
            "summary": "Controlled project register records and governance-facing project history.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget register workspace remains active"
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
            "title": "Project Register",
            "subtitle": "Track risks, issues, and changes across the selected project scope.",
            "emptyState": "Project-management register desktop API is not connected in this QML preview.",
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
            "emptyState": "Select a register entry to review governance details.",
            "fields": [],
            "state": {}
        })
    readonly property var urgentModel: root.workspaceController
        ? root.workspaceController.urgentEntries
        : ({
            "title": "Urgent Review Queue",
            "subtitle": "Severity-first shortlist to help triage what needs attention next.",
            "emptyState": "No urgent register items are available in this QML preview.",
            "items": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    readonly property var _tableColumns: [
        { "key": "title",        "label": "Issue",    "flex": 2,   "sortable": true  },
        { "key": "statusLabel",  "label": "Severity", "flex": 0,   "minWidth": 100, "type": "status" },
        { "key": "typeLabel",    "label": "Type",     "flex": 0,   "minWidth": 90,  "type": "status" },
        { "key": "projectName",  "label": "Project",  "flex": 1.5, "sortable": true  },
        { "key": "ownerName",    "label": "Owner",    "flex": 1.5                    },
        { "key": "dueDateLabel", "label": "Due",      "flex": 0,   "minWidth": 90    }
    ]

    ProjectManagementWidgets.RegisterDialogHost {
        id: dialogHost

        projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
        typeOptions: root.workspaceController ? (root.workspaceController.typeOptions || []) : []
        statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
        severityOptions: root.workspaceController ? (root.workspaceController.severityOptions || []) : []
        typeFieldVisible: true
        fixedTypeValue: "RISK"
        entryLabel: "Register Entry"

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.createEntry(payload)
        }
        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.updateEntry(payload)
        }
        onDeleteRequested: function(entryId) {
            if (root.workspaceController !== null) root.workspaceController.deleteEntry(entryId)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.KpiStrip {
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
            visible: false
            Layout.fillWidth: true
            migrationStatus: root.workspaceController
                ? "QML governance register slice active"
                : (root.workspaceModel.migrationStatus || "")
            legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
            architectureStatus: "Desktop API + typed controller"
            architectureSummary: "Cross-project risks, issues, changes, and governance review flows now run through a typed PM controller backed by the register desktop API."
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search register entries…"
            showCreate: true
            createLabel: "New Entry"
            showRefresh: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
            }
            onRefreshRequested: {
                if (root.workspaceController !== null) root.workspaceController.refresh()
            }
            onCreateRequested: dialogHost.openCreateDialog()
        }

        // ── Full-width table with full-page detail view ───────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: registerTable
                anchors.fill: parent
                columns: root._tableColumns
                rows: root.entriesModel.items || []
                selectedRowId: root.workspaceController ? root.workspaceController.selectedEntryId : ""
                showFilter: true

                onFilterClicked: filterPopup.open()
                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectEntry(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectEntry(rowId)
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectEntry(rowId)
                    detailPage.open = true
                }
                onSortRequested: function(key) {}
            }

            Popup {
                id: filterPopup
                parent: registerTable
                width: 260
                padding: 12
                x: registerTable.width - width - 4
                y: 30
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                Column {
                    width: parent.width
                    spacing: 8

                    Label {
                        text: "Project"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    ComboBox {
                        width: parent.width
                        model: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.selectProject(String(opts[index].value || "all"))
                        }
                    }

                    Label {
                        text: "Type"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    ComboBox {
                        width: parent.width
                        model: root.workspaceController ? (root.workspaceController.typeOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.typeOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setTypeFilter(String(opts[index].value || "all"))
                        }
                    }

                    Label {
                        text: "Status"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    ComboBox {
                        width: parent.width
                        model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setStatusFilter(String(opts[index].value || "all"))
                        }
                    }

                    Label {
                        text: "Severity"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    ComboBox {
                        width: parent.width
                        model: root.workspaceController ? (root.workspaceController.severityOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.severityOptions || []) : []
                            if (root.workspaceController !== null && opts[index])
                                root.workspaceController.setSeverityFilter(String(opts[index].value || "all"))
                        }
                    }
                }
            }

            AppWidgets.SectionDetailPage {
                id: detailPage
                anchors.fill: parent
                title: root.selectedEntryModel.title || "Entry Details"
                open: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: ["Details", "Impact", "Response", "Links"]

                onBackRequested: detailPage.open = false
                onEditRequested: dialogHost.openEditDialog(root.selectedEntryModel)
                onDeleteRequested: dialogHost.openDeleteDialog(root.selectedEntryModel)

                RegisterDetailPanel {
                    width: parent.width
                    detailPage: detailPage
                    entryDetail: root.selectedEntryModel
                    urgentModel: root.urgentModel
                    selectedEntryId: root.workspaceController ? root.workspaceController.selectedEntryId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onEditRequested: dialogHost.openEditDialog(root.selectedEntryModel)
                    onDeleteRequested: dialogHost.openDeleteDialog(root.selectedEntryModel)
                    onUrgentEntrySelected: function(entryId) {
                        if (root.workspaceController !== null) root.workspaceController.selectEntry(entryId)
                    }
                }
            }
        }
    }
}
