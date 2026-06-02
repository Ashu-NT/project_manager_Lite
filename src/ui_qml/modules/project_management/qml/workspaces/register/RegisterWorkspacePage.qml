pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets
import "sections" as Sections

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
            "summary": "Risks, issues, and changes — unified project governance register."
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
            "emptyState": "Select a project to review register entries.",
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
            "emptyState": "No urgent register items.",
            "items": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item

    // ── Type tab navigation ───────────────────────────────────────────────────
    readonly property var _typeTabs: [
        { "value": "all",    "label": "All Entries" },
        { "value": "RISK",   "label": "Risks"       },
        { "value": "ISSUE",  "label": "Issues"      },
        { "value": "CHANGE", "label": "Changes"     }
    ]

    readonly property string _activeType: root.workspaceController
        ? (root.workspaceController.selectedTypeFilter || "all")
        : "all"

    // Dialog config driven by active type tab
    readonly property bool   _typeFieldVisible: root._activeType === "all"
    readonly property string _fixedTypeValue:   root._activeType === "all" ? "RISK" : root._activeType
    readonly property string _createLabel: {
        switch (root._activeType) {
            case "RISK":   return "New Risk"
            case "ISSUE":  return "New Issue"
            case "CHANGE": return "New Change"
            default:       return "New Entry"
        }
    }

    // ── Column state ──────────────────────────────────────────────────────────
    property string _tableId: "pm.register.table"
    property var    _columns: []

    function _baseColumns() {
        return [
            { "key": "title",        "label": "Title",    "flex": 2,   "sortable": true,  "visibleByDefault": true,  "required": true  },
            { "key": "entryCode",    "label": "Code",     "flex": 0,   "minWidth": 120, "sortable": true,  "visibleByDefault": true   },
            { "key": "typeLabel",    "label": "Type",     "flex": 0,   "minWidth": 90,  "type": "status", "visibleByDefault": true   },
            { "key": "projectName",  "label": "Project",  "flex": 1.5, "sortable": true,  "visibleByDefault": true   },
            { "key": "ownerName",    "label": "Owner",    "flex": 1,                       "visibleByDefault": true   },
            { "key": "statusLabel",  "label": "Severity", "flex": 0,   "minWidth": 90,  "type": "status", "visibleByDefault": true   },
            { "key": "entryStatus",  "label": "Status",   "flex": 0,   "minWidth": 90,  "type": "status", "visibleByDefault": true   },
            { "key": "dueDateLabel", "label": "Due",      "flex": 0,   "minWidth": 90,     "visibleByDefault": true   }
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

    readonly property var _detailActions: [
        { "id": "edit",   "label": "Edit",   "icon": "edit",   "enabled": true, "danger": false },
        { "id": "delete", "label": "Delete", "icon": "delete", "enabled": true, "danger": true  }
    ]

    readonly property var _bulkChangeProperties: {
        const props = []
        const statusOpts = root.workspaceController
            ? (root.workspaceController.bulkStatusOptions || [])
            : []
        if (statusOpts.length > 0) {
            props.push({ "id": "status", "label": "Status", "values": statusOpts })
        }
        return props
    }

    function _optionIndexForValue(options, value) {
        const optionList = options || []
        for (let i = 0; i < optionList.length; i += 1) {
            if (String(optionList[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (detailPage) detailPage.scrollToSection(sectionIndex)
    }

    // ── Dialog host ───────────────────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            ProjectManagementWidgets.RegisterDialogHost {
                projectOptions:   root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                typeOptions:      root.workspaceController ? (root.workspaceController.typeOptions || []) : []
                statusOptions:    root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                severityOptions:  root.workspaceController ? (root.workspaceController.severityOptions || []) : []
                typeFieldVisible: root._typeFieldVisible
                fixedTypeValue:   root._fixedTypeValue
                entryLabel:       root._createLabel.replace("New ", "")
                workspaceController: root.workspaceController

                onDeleteRequested: function(entryId) {
                    if (root.workspaceController !== null) root.workspaceController.deleteEntry(entryId)
                }
            }
        }
    }

    // ── Main layout ───────────────────────────────────────────────────────────
    Item {
        anchors.fill: parent

        // ── List page ─────────────────────────────────────────────────────────
        Item {
            id: _listPage
            anchors.fill: parent
            visible: !root._detailOpen

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

                // KPI strip
                AppWidgets.KpiStrip {
                    Layout.fillWidth: true
                    metrics: root.overviewModel.metrics || []
                }

                // State messages
                AppWidgets.LoadingOverlay {
                    Layout.fillWidth: true
                    loading: (root.workspaceController ? root.workspaceController.isLoading : false)
                        && !(root.workspaceController ? root.workspaceController.isBusy : false)
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    message: "Loading register..."
                    compact: true
                    modal:   false
                }
                AppWidgets.LoadingOverlay {
                    Layout.fillWidth: true
                    loading: root.workspaceController
                        ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    message: "Saving changes..."
                    compact: true
                    modal:   false
                }
                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: !root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: !root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                // ── Type navigation tabs ──────────────────────────────────────
                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: _tabRow.implicitHeight + Theme.AppTheme.spacingSm * 2
                    color: Theme.AppTheme.surfaceRaised
                    radius: Theme.AppTheme.radiusMd
                    border.color: Theme.AppTheme.subtleBorder
                    border.width: 1

                    Row {
                        id: _tabRow
                        anchors {
                            left: parent.left
                            right: parent.right
                            verticalCenter: parent.verticalCenter
                            leftMargin: Theme.AppTheme.spacingSm
                            rightMargin: Theme.AppTheme.spacingSm
                        }
                        spacing: Theme.AppTheme.spacingXs

                        Repeater {
                            model: root._typeTabs

                            delegate: Rectangle {
                                id: _tabBtn
                                required property var modelData

                                readonly property bool _active: root._activeType === _tabBtn.modelData.value

                                implicitWidth:  _tabLabel.implicitWidth + Theme.AppTheme.spacingMd * 2
                                implicitHeight: Theme.AppTheme.toolbarHeight - 8
                                radius: Theme.AppTheme.radiusSm
                                color: _tabBtn._active
                                    ? Theme.AppTheme.navSelectedBackground
                                    : _tabHover.containsMouse
                                        ? Theme.AppTheme.hoverSurface
                                        : "transparent"
                                border.color: _tabBtn._active ? Theme.AppTheme.accent : "transparent"
                                border.width: _tabBtn._active ? 1 : 0

                                AppControls.Label {
                                    id: _tabLabel
                                    anchors.centerIn: parent
                                    text: _tabBtn.modelData.label
                                    color: _tabBtn._active
                                        ? Theme.AppTheme.navSelectedText
                                        : Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: _tabBtn._active
                                }

                                MouseArea {
                                    id: _tabHover
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: {
                                        if (root.workspaceController !== null)
                                            root.workspaceController.setTypeFilter(
                                                String(_tabBtn.modelData.value || "all")
                                            )
                                    }
                                }
                            }
                        }
                    }
                }

                // ── Table toolbar ─────────────────────────────────────────────
                AppWidgets.TableToolbar {
                    id: tableToolbar
                    Layout.fillWidth: true
                    searchPlaceholder: "Search register entries..."
                    showCreate: true
                    createEnabled: root.workspaceController
                        ? (root.workspaceController.projectOptions || []).some(function(option) {
                            return String(option.value || "").toLowerCase() !== "all"
                        })
                        : false
                    createLabel: root._createLabel
                    showFilter: true
                    showCustomize: true
                    showRefresh: true
                    showExport: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onSearchChanged: function(text) {
                        if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
                    }
                    onFilterClicked:   filterPopup.open()
                    onCustomizeClicked: registerTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
                    onRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                    onExportRequested: {
                        if (root.workspaceController !== null) root.workspaceController.exportRegister()
                    }
                    onCreateRequested: dialogHostLoader.invoke("openCreateDialog")
                }

                // ── Table + pagination ────────────────────────────────────────
                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: registerTable
                        anchors.top:    parent.top
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: _paginationBar.top
                        multiSelect: true
                        tableId: root._tableId
                        columns: root._columns
                        sourceModel: root.workspaceController ? root.workspaceController.entriesTableModel : null
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.entriesModel.emptyState || "No register entries available."
                        selectedRowId:  root.workspaceController ? root.workspaceController.selectedEntryId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedEntryIds || []) : []

                        onColumnsStateChanged: function(cols) {
                            if (root.workspaceController)
                                root.workspaceController.saveTableColumnState(root._tableId, root._buildColumnState(cols))
                            root._columns = cols
                        }
                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectEntry(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectEntry(rowId)
                            root._openDetail(0)
                        }
                        onViewDetailRequested: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectEntry(rowId)
                            root._openDetail(0)
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null)
                                root.workspaceController.setEntryBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) root.workspaceController.selectVisibleEntries()
                            else             root.workspaceController.clearEntryBulkSelection()
                        }
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: parent.bottom
                        currentPage:  root.workspaceController ? root.workspaceController.entryPage      : 1
                        pageSize:     root.workspaceController ? root.workspaceController.entryPageSize   : 25
                        totalItems:   root.workspaceController ? root.workspaceController.entryTotalCount : 0
                        busy:         root.workspaceController ? root.workspaceController.isBusy          : false
                        onPageRequested: function(page) {
                            if (root.workspaceController !== null) root.workspaceController.setEntryPage(page)
                        }
                        onPageSizeRequested: function(pageSize) {
                            if (root.workspaceController !== null) root.workspaceController.setEntryPageSize(pageSize)
                        }
                    }

                    // Bulk action bar
                    AppWidgets.BulkActionBar {
                        id: _bulkActionBar
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        selectedCount: root.workspaceController ? root.workspaceController.selectedEntryCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "delete",          "label": "Delete",        "icon": "delete", "danger": true,  "enabled": true },
                            { "id": "change_property", "label": "Change Status", "icon": "edit",   "danger": false, "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null) root.workspaceController.clearEntryBulkSelection()
                        }
                        onActionTriggered: function(actionId) {
                            if (root.workspaceController === null) return
                            if (actionId === "delete") {
                                root.workspaceController.bulkDeleteEntries(
                                    root.workspaceController.selectedEntryIds || []
                                )
                            } else if (actionId === "change_property") {
                                _bulkChangePropertyPopup.open()
                            }
                        }
                    }

                    AppWidgets.BulkChangePropertyPopup {
                        id: _bulkChangePropertyPopup
                        anchorItem:    _bulkActionBar.actionButtonForId("change_property")
                        selectedCount: root.workspaceController ? root.workspaceController.selectedEntryCount : 0
                        busy:          root.workspaceController ? root.workspaceController.isBusy : false
                        properties:    root._bulkChangeProperties
                        onApplyRequested: function(payload) {
                            if (root.workspaceController === null) return
                            if (payload.propertyId === "status")
                                root.workspaceController.applyBulkEntryStatus({ "value": payload.value })
                        }
                    }

                    // ── Filter popup (project / status / severity — NOT type, tabs handle that) ──
                    AppWidgets.AnchoredPopup {
                        id: filterPopup
                        anchorItem:  tableToolbar.filterButtonItem
                        width: 280
                        padding: Theme.AppTheme.marginMd
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color:  Theme.AppTheme.surfaceRaised
                            border.color: Theme.AppTheme.divider
                            border.width: 1
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: "Project"
                                font.bold: true; font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.projectOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedProjectId : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                                    if (root.workspaceController !== null && opts[index])
                                        root.workspaceController.selectProject(String(opts[index].value || "all"))
                                }
                            }

                            AppControls.Label {
                                text: "Status"
                                font.bold: true; font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.statusOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                                    if (root.workspaceController !== null && opts[index])
                                        root.workspaceController.setStatusFilter(String(opts[index].value || "all"))
                                }
                            }

                            AppControls.Label {
                                text: "Severity"
                                font.bold: true; font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.severityOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.severityOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedSeverityFilter : "all"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController ? (root.workspaceController.severityOptions || []) : []
                                    if (root.workspaceController !== null && opts[index])
                                        root.workspaceController.setSeverityFilter(String(opts[index].value || "all"))
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingSm

                                AppControls.SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "Clear"
                                    iconName: "close"
                                    onClicked: {
                                        if (root.workspaceController !== null) {
                                            root.workspaceController.selectProject("all")
                                            root.workspaceController.setStatusFilter("all")
                                            root.workspaceController.setSeverityFilter("all")
                                        }
                                        filterPopup.close()
                                    }
                                }
                                AppControls.SecondaryButton {
                                    Layout.fillWidth: true
                                    text: "Close"
                                    iconName: "close"
                                    onClicked: filterPopup.close()
                                }
                            }
                        }
                    }
                }
            }
        }

        // ── Detail page (covers full area, z:20) ──────────────────────────────
        Loader {
            id: detailPageLoader
            anchors.fill: parent
            active:  root._detailOpen
            visible: root._detailOpen && status === Loader.Ready
            asynchronous: true
            sourceComponent: _detailPageComponent
        }

        Component {
            id: _detailPageComponent

            AppWidgets.SectionDetailPage {
                open: true
                anchors.fill: parent
                showHeader: false
                showEdit: false
                showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: ["Details", "Impact", "Response", "Links"]
                z: 20
                Component.onCompleted: scrollToSection(root._pendingDetailSection)

                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title:    root.selectedEntryModel.title || "Register Entry"
                    subtitle: root.selectedEntryModel.statusLabel || root.selectedEntryModel.subtitle || ""
                    busy:     root.workspaceController ? root.workspaceController.isBusy : false
                    actions:  root._detailActions

                    onBackRequested: root._detailOpen = false
                    onActionTriggered: function(actionId) {
                        if (actionId === "edit") {
                            dialogHostLoader.invoke("openEditDialog", root.selectedEntryModel)
                        } else if (actionId === "delete") {
                            dialogHostLoader.invoke("openDeleteDialog", root.selectedEntryModel)
                        }
                    }
                }

                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.InlineMessage {
                    width: parent ? parent.width : 0
                    visible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Sections.RegisterDetailPanel {
                    width: parent ? parent.width : 0
                    detailPage:      detailPageLoader.item
                    entryDetail:     root.selectedEntryModel
                    urgentModel:     root.urgentModel
                    selectedEntryId: root.workspaceController ? root.workspaceController.selectedEntryId : ""
                    isBusy:          root.workspaceController ? root.workspaceController.isBusy : false
                    onEditRequested:  dialogHostLoader.invoke("openEditDialog", root.selectedEntryModel)
                    onDeleteRequested: dialogHostLoader.invoke("openDeleteDialog", root.selectedEntryModel)
                    onUrgentEntrySelected: function(entryId) {
                        if (root.workspaceController !== null) root.workspaceController.selectEntry(entryId)
                    }
                }
            }
        }
    }
}
