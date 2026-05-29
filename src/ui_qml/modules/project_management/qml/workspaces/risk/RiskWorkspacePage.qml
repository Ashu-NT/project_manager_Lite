pragma ComponentBehavior: Bound
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
            "summary": "Project risk register, mitigation, severity, and review workflows."
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

    property string _tableId: "pm.risk.table"
    property var    _columns: []

    function _baseColumns() {
        return [
            { "key": "title",            "label": "Risk",        "flex": 2,   "sortable": true,  "visibleByDefault": true  },
            { "key": "projectName",      "label": "Project",     "flex": 1.5, "sortable": true,  "visibleByDefault": true  },
            { "key": "ownerName",        "label": "Owner",       "flex": 1.5,                     "visibleByDefault": true  },
            { "key": "probabilityLabel", "label": "Probability", "flex": 0,   "minWidth": 100,    "visibleByDefault": true  },
            { "key": "impactLabel",      "label": "Impact",      "flex": 0,   "minWidth": 90,     "visibleByDefault": true  },
            { "key": "statusLabel",      "label": "Severity",    "flex": 0,   "minWidth": 100, "type": "status", "visibleByDefault": true  },
            { "key": "entryStatus",      "label": "Status",      "flex": 0,   "minWidth": 90,  "type": "status", "visibleByDefault": true  },
            { "key": "dueDateLabel",     "label": "Due",         "flex": 0,   "minWidth": 90,     "visibleByDefault": true  }
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
    function _buildColumnState(columns) {
        const order = []
        const hidden = []
        for (let i = 0; i < columns.length; i++) {
            order.push(columns[i].key)
            if (columns[i].visible === false) hidden.push(columns[i].key)
        }
        return { "columnOrder": order, "hiddenColumns": hidden }
    }
    Component.onCompleted: {
        const base = root._baseColumns()
        if (root.workspaceController !== null) {
            const saved = root.workspaceController.loadTableColumnState(root._tableId)
            root._columns = root._applyColumnState(base, saved)
        } else {
            root._columns = base
        }
    }

    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            ProjectManagementWidgets.RegisterDialogHost {
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

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search risks…"
            showCreate: true
            createEnabled: root.workspaceController
                ? (root.workspaceController.projectOptions || []).some(function(option) {
                    return String(option.value || "").toLowerCase() !== "all"
                })
                : false
            createLabel: "New Risk"
            showFilter: true
            showCustomize: true
            showRefresh: true
            showExport: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
            }
            onFilterClicked: filterPopup.open()
            onCustomizeClicked: riskTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
            onRefreshRequested: {
                if (root.workspaceController !== null) root.workspaceController.refresh()
            }
            onExportRequested: {
                if (root.workspaceController !== null) root.workspaceController.exportRegister()
            }
            onCreateRequested: dialogHostLoader.invoke("openCreateDialog")
        }

        // ── Full-width table with full-page detail view ───────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            visible: !root._detailOpen

            AppWidgets.DataTable {
                id: riskTable
                anchors.top:    parent.top
                anchors.left:   parent.left
                anchors.right:  parent.right
                anchors.bottom: _paginationBar.top
                tableId: root._tableId
                columns: root._columns
                sourceModel: root.workspaceController ? root.workspaceController.entriesTableModel : null
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.entriesModel.emptyState || "No risk entries available."
                selectedRowId: root.workspaceController ? root.workspaceController.selectedEntryId : ""
                onColumnsStateChanged: function(cols) {
                    if (root.workspaceController) root.workspaceController.saveTableColumnState(root._tableId, root._buildColumnState(cols))
                    root._columns = cols
                }

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
            }

            AppWidgets.TablePaginationBar {
                id: _paginationBar
                anchors.left:   parent.left
                anchors.right:  parent.right
                anchors.bottom: parent.bottom
                currentPage:  root.workspaceController ? root.workspaceController.riskPage       : 1
                pageSize:     root.workspaceController ? root.workspaceController.riskPageSize    : 25
                totalItems:   root.workspaceController ? root.workspaceController.riskTotalCount  : 0
                busy:         root.workspaceController ? root.workspaceController.isBusy          : false
                onPageRequested: function(page) {
                    if (root.workspaceController !== null) root.workspaceController.setRiskPage(page)
                }
                onPageSizeRequested: function(pageSize) {
                    if (root.workspaceController !== null) root.workspaceController.setRiskPageSize(pageSize)
                }
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
                    onEditRequested: dialogHostLoader.invoke("openEditDialog", root.selectedEntryModel)
                    onDeleteRequested: dialogHostLoader.invoke("openDeleteDialog", root.selectedEntryModel)

                    RiskDetailPanel {
                        width: parent.width
                        detailPage: detailPageLoader.item
                        entryDetail: root.selectedEntryModel
                        urgentModel: root.urgentModel
                        selectedEntryId: root.workspaceController ? root.workspaceController.selectedEntryId : ""
                        isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                        onEditRequested: dialogHostLoader.invoke("openEditDialog", root.selectedEntryModel)
                        onDeleteRequested: dialogHostLoader.invoke("openDeleteDialog", root.selectedEntryModel)
                        onUrgentEntrySelected: function(entryId) {
                            if (root.workspaceController !== null) root.workspaceController.selectEntry(entryId)
                        }
                    }
                }
            }
        }
    }
}
