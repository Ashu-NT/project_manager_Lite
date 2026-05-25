pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

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
            "summary": "Time entry, review, labor capture, and project time reporting."
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var reviewQueueModel: root.workspaceController
        ? root.workspaceController.reviewQueue
        : ({
            "title": "Review Queue",
            "subtitle": "Timesheet periods pending review and approval.",
            "emptyState": "No timesheet periods match the current filter.",
            "items": []
        })
    readonly property var selectedPeriodModel: root.workspaceController
        ? root.workspaceController.reviewDetail
        : ({
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a timesheet period to review entries and manage approval.",
            "fields": [],
            "state": {}
        })
    readonly property var entriesModel: root.workspaceController
        ? root.workspaceController.entries
        : ({
            "title": "Time Entries",
            "subtitle": "",
            "emptyState": "No time entries for the selected period.",
            "items": []
        })
    readonly property var selectedEntryModel: root.workspaceController
        ? root.workspaceController.selectedEntry
        : ({
            "title": "",
            "subtitle": "",
            "emptyState": "Select an entry to review its labor note and details.",
            "fields": [],
            "state": {}
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item

    readonly property var _tableColumns: [
        { "key": "title",         "label": "Resource / Period", "flex": 2,   "sortable": true },
        { "key": "statusLabel",   "label": "Status",            "flex": 0,   "minWidth": 110, "type": "status" },
        { "key": "subtitle",      "label": "Assignment",        "flex": 1.5                   },
        { "key": "metaText",      "label": "Hours",             "flex": 0,   "minWidth": 80   },
        { "key": "supportingText","label": "Period",            "flex": 0,   "minWidth": 110  }
    ]

    readonly property var _detailActions: {
        const state = root.selectedPeriodModel ? (root.selectedPeriodModel.state || {}) : {}
        const status = String(state.periodStatus || "").toUpperCase()
        const hasPeriod = Boolean(state.periodId)
        const hasStatus = status.length > 0
        return [
            { "id": "submit",  "label": "Submit",        "icon": "approve",
              "enabled": hasPeriod && (!hasStatus || status === "DRAFT" || status === "OPEN"),
              "danger": false },
            { "id": "approve", "label": "Approve",       "icon": "approve",
              "enabled": hasPeriod && (!hasStatus || status === "SUBMITTED"),
              "danger": false },
            { "id": "reject",  "label": "Reject",        "icon": "close",
              "enabled": hasPeriod && (!hasStatus || status === "SUBMITTED"),
              "danger": true  },
            { "id": "lock",    "label": "Lock Period",   "icon": "lock",
              "enabled": hasPeriod && (!hasStatus || status === "APPROVED"),
              "danger": false },
            { "id": "unlock",  "label": "Unlock Period", "icon": "edit",
              "enabled": hasPeriod && (!hasStatus || status === "LOCKED"),
              "danger": false },
            { "id": "export",  "label": "Export",        "icon": "export",
              "enabled": true,
              "danger": false }
        ]
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
        if (detailPage) {
            detailPage.scrollToSection(sectionIndex)
        }
    }

    // ── Stacked layout: list page / detail page ───────────────────────
    Item {
        anchors.fill: parent

        // ── List page (hidden when detail is open) ────────────────────
        Item {
            id: _listPage
            anchors.fill: parent
            visible: !root._detailOpen

            ColumnLayout {
                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

                AppWidgets.KpiStrip {
                    Layout.fillWidth: true
                    metrics: root.overviewModel.metrics || []
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: (root.workspaceController ? root.workspaceController.isLoading : false)
                        && !(root.workspaceController ? root.workspaceController.isBusy : false)
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "info"
                    message: "Loading timesheets..."
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root.workspaceController
                        ? root.workspaceController.isBusy && String(root.workspaceController.errorMessage || "").length === 0
                        : false
                    tone: "info"
                    message: "Saving changes..."
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                AppWidgets.TableToolbar {
                    id: tableToolbar
                    Layout.fillWidth: true
                    searchPlaceholder: "Search timesheets..."
                    showCreate: false
                    showFilter: true
                    showCustomize: true
                    showViews: true
                    showRefresh: true
                    showExport: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onFilterClicked: filterPopup.open()
                    onCustomizeClicked: reviewTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
                    onViewsClicked: viewsPopup.open()
                    onRefreshRequested: {
                        if (root.workspaceController !== null) root.workspaceController.refresh()
                    }
                    onExportRequested: {}
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true

                    AppWidgets.DataTable {
                        id: reviewTable
                        anchors.top:    parent.top
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: _paginationBar.top
                        multiSelect: true
                        columns: root._tableColumns
                        rows: root.reviewQueueModel.items || []
                        loading: root.workspaceController ? root.workspaceController.isLoading : false
                        emptyText: root.reviewQueueModel.emptyState || "No timesheet periods available."
                        selectedRowId: root.workspaceController ? root.workspaceController.selectedQueuePeriodId : ""
                        selectedRowIds: root.workspaceController ? (root.workspaceController.selectedQueuePeriodIds || []) : []

                        onRowSelected: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectQueuePeriod(rowId)
                        }
                        onRowActivated: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectQueuePeriod(rowId)
                            root._openDetail(0)
                        }
                        onViewDetailRequested: function(rowId) {
                            if (root.workspaceController !== null) root.workspaceController.selectQueuePeriod(rowId)
                            root._openDetail(0)
                        }
                        onRowSelectionToggled: function(rowId, selected) {
                            if (root.workspaceController !== null)
                                root.workspaceController.setQueueBulkSelection(rowId, selected)
                        }
                        onSelectAllToggled: function(allSelected) {
                            if (root.workspaceController === null) return
                            if (allSelected) root.workspaceController.selectVisibleQueuePeriods()
                            else root.workspaceController.clearQueueBulkSelection()
                        }
                        onSortRequested: function(key) {}
                    }

                    AppWidgets.TablePaginationBar {
                        id: _paginationBar
                        anchors.left:   parent.left
                        anchors.right:  parent.right
                        anchors.bottom: parent.bottom
                        currentPage:  root.workspaceController ? root.workspaceController.queuePage       : 1
                        pageSize:     root.workspaceController ? root.workspaceController.queuePageSize    : 25
                        totalItems:   root.workspaceController ? root.workspaceController.queueTotalCount  : 0
                        busy:         root.workspaceController ? root.workspaceController.isBusy           : false
                        onPageRequested: function(page) {
                            if (root.workspaceController !== null) root.workspaceController.setQueuePage(page)
                        }
                        onPageSizeRequested: function(pageSize) {
                            if (root.workspaceController !== null) root.workspaceController.setQueuePageSize(pageSize)
                        }
                    }

                    AppWidgets.BulkActionBar {
                        id: _bulkActionBar
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: _paginationBar.top
                        anchors.bottomMargin: Theme.AppTheme.spacingMd
                        z: 10
                        selectedCount: root.workspaceController ? root.workspaceController.selectedQueuePeriodCount : 0
                        busy: root.workspaceController ? root.workspaceController.isBusy : false
                        actions: [
                            { "id": "approve", "label": "Approve", "icon": "approve", "danger": false, "enabled": true },
                            { "id": "reject",  "label": "Reject",  "icon": "close",   "danger": true,  "enabled": true }
                        ]

                        onCancelRequested: {
                            if (root.workspaceController !== null) root.workspaceController.clearQueueBulkSelection()
                        }
                        onActionTriggered: function(actionId) {
                            if (root.workspaceController === null) return
                            const ids = root.workspaceController.selectedQueuePeriodIds || []
                            if (actionId === "approve")
                                root.workspaceController.bulkApprovePeriods(ids)
                            else if (actionId === "reject")
                                root.workspaceController.bulkRejectPeriods(ids)
                        }
                    }

                    // ── Filter popup ──────────────────────────────────────
                    AppWidgets.AnchoredPopup {
                        id: filterPopup
                        anchorItem: tableToolbar.filterButtonItem
                        width: 280
                        padding: Theme.AppTheme.marginMd
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color: Theme.AppTheme.surfaceRaised
                            border.color: Theme.AppTheme.divider
                            border.width: 1
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: "Project"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
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
                                    const opts = root.workspaceController
                                        ? (root.workspaceController.projectOptions || []) : []
                                    if (root.workspaceController !== null && opts[index])
                                        root.workspaceController.selectProject(String(opts[index].value || "all"))
                                }
                            }

                            AppControls.Label {
                                text: "Assignment"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.assignmentOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.assignmentOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedAssignmentId : ""
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController
                                        ? (root.workspaceController.assignmentOptions || []) : []
                                    if (root.workspaceController !== null && opts[index])
                                        root.workspaceController.selectAssignment(String(opts[index].value || ""))
                                }
                            }

                            AppControls.Label {
                                text: "Period"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }
                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.periodOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.periodOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedPeriodStart : ""
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController
                                        ? (root.workspaceController.periodOptions || []) : []
                                    if (root.workspaceController !== null && opts[index])
                                        root.workspaceController.selectPeriod(String(opts[index].value || ""))
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
                                            root.workspaceController.selectAssignment("")
                                            root.workspaceController.selectPeriod("")
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

                    // ── Views popup (queue status / workflow stage) ───────
                    AppWidgets.AnchoredPopup {
                        id: viewsPopup
                        anchorItem: tableToolbar.viewsButtonItem
                        width: 260
                        padding: Theme.AppTheme.marginMd
                        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                        background: Rectangle {
                            radius: Theme.AppTheme.radiusLg
                            color: Theme.AppTheme.surfaceRaised
                            border.color: Theme.AppTheme.divider
                            border.width: 1
                        }

                        contentItem: ColumnLayout {
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: "View"
                                font.bold: true
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.family: Theme.AppTheme.fontFamily
                                color: Theme.AppTheme.textMuted
                            }

                            AppControls.ComboBox {
                                Layout.fillWidth: true
                                model: root.workspaceController ? (root.workspaceController.queueStatusOptions || []) : []
                                textRole: "label"
                                enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                                currentIndex: root._optionIndexForValue(
                                    root.workspaceController ? (root.workspaceController.queueStatusOptions || []) : [],
                                    root.workspaceController ? root.workspaceController.selectedQueueStatus : "SUBMITTED"
                                )
                                onActivated: function(index) {
                                    const opts = root.workspaceController
                                        ? (root.workspaceController.queueStatusOptions || []) : []
                                    if (root.workspaceController !== null && opts[index]) {
                                        root.workspaceController.setQueueStatus(String(opts[index].value || "SUBMITTED"))
                                        viewsPopup.close()
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        // ── Detail page (covers full area, z:20) ─────────────────────────
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
                open: true
                anchors.fill: parent
                showHeader: false
                showEdit: false
                showDelete: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: [
                    { "label": "Entries",          "count": (root.entriesModel.items || []).length },
                    "Approval History",
                    "Labor Notes",
                    "Audit Trail"
                ]
                z: 20
                Component.onCompleted: scrollToSection(root._pendingDetailSection)

                AppWidgets.ContextualActionToolbar {
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root.selectedPeriodModel.title || "Timesheet Period"
                    subtitle: root.selectedPeriodModel.statusLabel || root.selectedPeriodModel.subtitle || ""
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: root._detailActions

                    onBackRequested: root._detailOpen = false
                    onActionTriggered: function(actionId) {
                        if (root.workspaceController === null) return
                        const state = root.selectedPeriodModel ? (root.selectedPeriodModel.state || {}) : {}
                        const periodId = String(state.periodId || "")
                        if (!periodId) return
                        if (actionId === "submit") {
                            root.workspaceController.submitPeriod({ "periodId": periodId })
                        } else if (actionId === "approve") {
                            root.workspaceController.approvePeriod({ "periodId": periodId })
                        } else if (actionId === "reject") {
                            root.workspaceController.rejectPeriod({ "periodId": periodId })
                        } else if (actionId === "lock") {
                            root.workspaceController.lockPeriod({ "periodId": periodId })
                        } else if (actionId === "unlock") {
                            root.workspaceController.unlockPeriod({ "periodId": periodId })
                        }
                    }
                }

                TimesheetsDetailSection {
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    reviewDetail: root.selectedPeriodModel
                    entriesModel: root.entriesModel
                    selectedEntry: root.selectedEntryModel
                    selectedEntryId: root.workspaceController ? root.workspaceController.selectedEntryId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEntrySelected: function(entryId) {
                        if (root.workspaceController !== null) root.workspaceController.selectEntry(entryId)
                    }
                }
            }
        }
    }
}
