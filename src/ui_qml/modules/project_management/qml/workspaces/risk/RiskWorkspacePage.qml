import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets
import App.Controls 1.0 as AppControls

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
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item

    readonly property var _tableColumns: [
        { "key": "title",        "label": "Risk",     "flex": 2,   "sortable": true  },
        { "key": "statusLabel",  "label": "Severity", "flex": 0,   "minWidth": 100, "type": "status" },
        { "key": "entryStatus",  "label": "Status",   "flex": 0,   "minWidth": 90,  "type": "status" },
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
        typeFieldVisible: false
        fixedTypeValue: "RISK"
        entryLabel: "Risk"

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
                ? "QML risk register slice active"
                : (root.workspaceModel.migrationStatus || "")
            legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
            architectureStatus: "Desktop API + typed controller"
            architectureSummary: "Project risk triage, severity filters, mitigation detail, and create/edit/delete flows now run through a typed PM controller backed by the register desktop API."
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search risks…"
            showCreate: true
            createLabel: "New Risk"
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
            visible: !root._detailOpen

            AppWidgets.DataTable {
                id: riskTable
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
                    root._pendingDetailSection = 0
                    root._detailOpen = true
                }
                onSortRequested: function(key) {}
            }

            // Filter flyout popup — anchored to DataTable
            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: riskTable.filterButtonItem
                width: 260
                padding: 12
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                Column {
                    width: parent.width
                    spacing: 8

                    AppControls.Label {
                        text: "Project"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }

                    AppControls.ComboBox {
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

                    AppControls.Label {
                        text: "Status"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }

                    AppControls.ComboBox {
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

                    AppControls.Label {
                        text: "Severity"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }

                    AppControls.ComboBox {
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

            // Full-page detail view
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
                    title: root.selectedEntryModel.title || "Risk Details"
                    anchors.fill: parent
                    open: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    sections: ["Details", "Impact", "Response", "Links"]
                    Component.onCompleted: scrollToSection(root._pendingDetailSection)

                    onBackRequested: root._detailOpen = false
                    onEditRequested: dialogHost.openEditDialog(root.selectedEntryModel)
                    onDeleteRequested: dialogHost.openDeleteDialog(root.selectedEntryModel)

                    RiskDetailPanel {
                        width: parent.width
                        detailPage: detailPageLoader.item
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
}
