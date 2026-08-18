pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    // ── Inputs ────────────────────────────────────────────────────────────
    property ProjectManagementControllers.ProjectManagementRegisterWorkspaceController workspaceController
    property var overviewModel:          ({ "metrics": [] })
    property var entriesModel:           ({ "emptyState": "No register entries available.", "items": [] })
    property var columns:                []
    property var bulkChangeProperties:   []
    property string createLabel:         "New Entry"
    property bool createEnabled:         true
    property bool detailOpen:            false

    // ── Signals ───────────────────────────────────────────────────────────
    signal rowActivated()
    signal createRequested()
    signal columnsStateChanged(var cols)

    // ── Derived ───────────────────────────────────────────────────────────
    readonly property var _typeTabs: [
        { "value": "all",    "label": "All Entries" },
        { "value": "RISK",   "label": "Risks"       },
        { "value": "ISSUE",  "label": "Issues"      },
        { "value": "CHANGE", "label": "Changes"     }
    ]
    readonly property string _activeType: root.workspaceController
        ? (root.workspaceController.selectedTypeFilter || "all")
        : "all"

    function _optionIndexForValue(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    // ── Layout ────────────────────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.KpiStrip { Layout.fillWidth: true; metrics: root.overviewModel.metrics || [] }

        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: (root.workspaceController ? root.workspaceController.isLoading : false)
                && !(root.workspaceController ? root.workspaceController.isBusy : false)
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            message: "Loading register..."; compact: true; modal: false
        }
        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: root.workspaceController ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0 : false
            message: "Saving changes..."; compact: true; modal: false
        }
        AppWidgets.InlineMessage { Layout.fillWidth: true; visible: !root.detailOpen && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0; tone: "danger"; message: root.workspaceController ? root.workspaceController.errorMessage : "" }
        AppWidgets.InlineMessage { Layout.fillWidth: true; visible: !root.detailOpen && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0 && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0; tone: "success"; message: root.workspaceController ? root.workspaceController.feedbackMessage : "" }

        // ── Type filter tabs ──────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: _tabRow.implicitHeight + Theme.AppTheme.spacingSm * 2
            color: Theme.AppTheme.surfaceRaised
            radius: Theme.AppTheme.radiusMd
            border.color: Theme.AppTheme.subtleBorder
            border.width: 1

            Row {
                id: _tabRow
                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; leftMargin: Theme.AppTheme.spacingSm; rightMargin: Theme.AppTheme.spacingSm }
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
                        color: _tabBtn._active ? Theme.AppTheme.navSelectedBackground : _tabHover.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"
                        border.color: _tabBtn._active ? Theme.AppTheme.accent : "transparent"
                        border.width: _tabBtn._active ? 1 : 0

                        AppControls.Label {
                            id: _tabLabel
                            anchors.centerIn: parent
                            text: _tabBtn.modelData.label
                            color: _tabBtn._active ? Theme.AppTheme.navSelectedText : Theme.AppTheme.textSecondary
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
                                    root.workspaceController.setTypeFilter(String(_tabBtn.modelData.value || "all"))
                            }
                        }
                    }
                }
            }
        }

        // ── Table toolbar ─────────────────────────────────────────────────
        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search register entries..."
            showCreate:    true
            createEnabled: root.createEnabled
            createLabel:   root.createLabel
            showFilter:    true
            showCustomize: true
            showRefresh:   true
            showExport:    false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged:   function(text) { if (root.workspaceController !== null) root.workspaceController.setSearchText(text) }
            onFilterClicked:   filterPopup.open()
            onCustomizeClicked: registerTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
            onCreateRequested: root.createRequested()
        }

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
                multiSelect:    true
                tableId:        "pm.register.table"
                columns:        root.columns
                sourceModel:    root.workspaceController ? root.workspaceController.entriesTableModel : null
                sortingMode:    "server"
                sortKey:        root.workspaceController ? root.workspaceController.entrySortKey : "triage"
                sortDirection:  root.workspaceController
                    ? root.workspaceController.entrySortDirection
                    : Qt.AscendingOrder
                loading:        root.workspaceController ? root.workspaceController.isLoading : false
                emptyText:      root.entriesModel.emptyState || "No register entries available."
                selectedRowId:  root.workspaceController ? root.workspaceController.selectedEntryId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedEntryIds || []) : []

                onColumnsStateChanged: function(cols) { root.columnsStateChanged(cols) }
                onSortRequested: function(key, direction) {
                    if (root.workspaceController !== null)
                        root.workspaceController.setEntrySort(key, direction)
                }
                onRowSelected: function(rowId) { if (root.workspaceController !== null) root.workspaceController.selectEntry(rowId) }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectEntry(rowId)
                    root.rowActivated()
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectEntry(rowId)
                    root.rowActivated()
                }
                onRowSelectionToggled: function(rowId, selected) {
                    if (root.workspaceController !== null) root.workspaceController.setEntryBulkSelection(rowId, selected)
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
                currentPage: root.workspaceController ? root.workspaceController.entryPage      : 1
                pageSize:    root.workspaceController ? root.workspaceController.entryPageSize   : 25
                totalItems:  root.workspaceController ? root.workspaceController.entryTotalCount : 0
                busy:        root.workspaceController ? root.workspaceController.isBusy          : false
                onPageRequested:     function(page) { if (root.workspaceController !== null) root.workspaceController.setEntryPage(page) }
                onPageSizeRequested: function(ps)   { if (root.workspaceController !== null) root.workspaceController.setEntryPageSize(ps) }
            }

            // ── Bulk action bar ───────────────────────────────────────────
            AppWidgets.BulkActionBar {
                id: _bulkActionBar
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: _paginationBar.top
                anchors.bottomMargin: Theme.AppTheme.spacingMd
                z: 10
                selectedCount: root.workspaceController ? root.workspaceController.selectedEntryCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: [
                    { "id": "delete", "label": "Delete", "icon": "delete", "danger": true, "enabled": true },
                    { "id": "change_property", "label": "Change Status", "icon": "edit", "danger": false, "enabled": true }
                ]

                onCancelRequested: { if (root.workspaceController !== null) root.workspaceController.clearEntryBulkSelection() }
                onActionTriggered: function(actionId) {
                    if (root.workspaceController === null) return
                    if (actionId === "delete")
                        root.workspaceController.bulkDeleteEntries(root.workspaceController.selectedEntryIds || [])
                    else if (actionId === "change_property")
                        _bulkChangePopup.open()
                }
            }

            AppWidgets.BulkChangePropertyPopup {
                id: _bulkChangePopup
                anchorItem:    _bulkActionBar.actionButtonForId("change_property")
                selectedCount: root.workspaceController ? root.workspaceController.selectedEntryCount : 0
                busy:          root.workspaceController ? root.workspaceController.isBusy : false
                properties:    root.bulkChangeProperties
                onApplyRequested: function(payload) {
                    if (root.workspaceController === null) return
                    if (payload.propertyId === "status")
                        root.workspaceController.applyBulkEntryStatus({ "value": payload.value })
                }
            }

            // ── Filter popup (project / status / severity) ────────────────
            AppControls.CenteredDialog {
                id: filterPopup

                // Draft selections, staged until Apply commits them.
                property string _draftProjectId: "all"
                property string _draftStatus: "all"
                property string _draftSeverity: "all"

                title:       "Filter Register"
                width:       340
                padding:     0
                modal:       true
                focus:       true
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                onAboutToShow: {
                    _draftProjectId = root.workspaceController ? root.workspaceController.selectedProjectId : "all"
                    _draftStatus = root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                    _draftSeverity = root.workspaceController ? root.workspaceController.selectedSeverityFilter : "all"
                }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingMd

                    Item { Layout.preferredHeight: Theme.AppTheme.spacingXs }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Theme.AppTheme.dialogPadding
                        Layout.rightMargin: Theme.AppTheme.dialogPadding
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.Label { text: "Project";  font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                        AppControls.ComboBox {
                            Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.projectOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.projectOptions || []) : [], filterPopup._draftProjectId)
                            onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.projectOptions || []) : []; if (opts[index]) filterPopup._draftProjectId = String(opts[index].value || "all") }
                        }

                        AppControls.Label { text: "Status";   font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                        AppControls.ComboBox {
                            Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.statusOptions || []) : [], filterPopup._draftStatus)
                            onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.statusOptions || []) : []; if (opts[index]) filterPopup._draftStatus = String(opts[index].value || "all") }
                        }

                        AppControls.Label { text: "Severity"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                        AppControls.ComboBox {
                            Layout.fillWidth: true; model: root.workspaceController ? (root.workspaceController.severityOptions || []) : []; textRole: "label"; enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.severityOptions || []) : [], filterPopup._draftSeverity)
                            onActivated: function(index) { const opts = root.workspaceController ? (root.workspaceController.severityOptions || []) : []; if (opts[index]) filterPopup._draftSeverity = String(opts[index].value || "all") }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: Theme.AppTheme.divider
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: Theme.AppTheme.dialogPadding
                        Layout.rightMargin: Theme.AppTheme.dialogPadding
                        Layout.bottomMargin: Theme.AppTheme.spacingSm
                        spacing: Theme.AppTheme.spacingSm
                        AppControls.SecondaryButton {
                            text: "Clear"; iconName: "refresh"
                            onClicked: {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.selectProject("all")
                                    root.workspaceController.setStatusFilter("all")
                                    root.workspaceController.setSeverityFilter("all")
                                }
                                filterPopup.close()
                            }
                        }
                        Item { Layout.fillWidth: true }
                        AppControls.SecondaryButton { text: "Close"; iconName: "close"; onClicked: filterPopup.close() }
                        AppControls.PrimaryButton {
                            text: "Apply"; iconName: "approve"
                            onClicked: {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.selectProject(filterPopup._draftProjectId)
                                    root.workspaceController.setStatusFilter(filterPopup._draftStatus)
                                    root.workspaceController.setSeverityFilter(filterPopup._draftSeverity)
                                }
                                filterPopup.close()
                            }
                        }
                    }
                }
            }
        }
    }
}
