pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "components" as Components
import "sections" as Sections
import "panels" as Panels

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementTimesheetsWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.timesheetsWorkspace
        : null

    // ── State management ──────────────────────────────────────────────────
    TimesheetsWorkspaceState {
        id: state
        pmCatalog: root.pmCatalog
        workspaceController: root.workspaceController
    }

    // ── Convenience aliases ────────────────────────────────────────────────
    readonly property var workspaceModel: state.workspaceModel
    readonly property var overviewModel: state.overviewModel
    readonly property var reviewQueueModel: state.reviewQueueModel
    readonly property var selectedPeriodModel: state.selectedPeriodModel
    readonly property var entriesModel: state.entriesModel
    readonly property var selectedEntryModel: state.selectedEntryModel

    // ── Column management ─────────────────────────────────────────────────
    property var _columns: state.columns

    function _saveColumnState(columns) {
        state.saveColumnState(columns)
        root._columns = state.columns
    }

    // ── Detail page state ─────────────────────────────────────────────────
    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary
    property bool _detailOpen: false
    property int _pendingDetailSection: 0
    readonly property var detailPage: detailPageLoader.item

    function _openDetail(sectionIndex) {
        root._pendingDetailSection = sectionIndex
        root._detailOpen = true
        if (detailPage) detailPage.scrollToSection(sectionIndex)
    }

    // ── Stacked layout: list page / detail page ───────────────────
    Item {
        anchors.fill: parent

        // ── List page ─────────────────────────────────────────────────────
        Item {
            id: _listPage
            anchors.fill: parent
            visible: !root._detailOpen

            Components.TimesheetsListPage {
                id: listPage
                anchors.fill: parent
                workspaceController: root.workspaceController
                state: state
                overviewModel: root.overviewModel
                reviewQueueModel: root.reviewQueueModel

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectQueuePeriod(rowId)
                }
                onRowActivated: function(rowId) {
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
                onColumnsStateChanged: function(cols) {
                    if (root.workspaceController !== null) root._saveColumnState(cols)
                }
                onFilterClicked: filterPopup.open()
                onViewsClicked: viewsPopup.open()
                onRefreshRequested: {
                    if (root.workspaceController !== null) root.workspaceController.refresh()
                }
                onExportRequested: {
                    if (root.workspaceController !== null) root.workspaceController.exportTimesheets()
                }
                onBulkCancelRequested: {
                    if (root.workspaceController !== null)
                        root.workspaceController.clearQueueBulkSelection()
                }
                onBulkActionRequested: function(actionId) {
                    if (root.workspaceController === null)
                        return
                    const ids = root.workspaceController.selectedQueuePeriodIds || []
                    if (actionId === "approve")
                        root.workspaceController.bulkApprovePeriods(ids)
                    else if (actionId === "reject")
                        root.workspaceController.bulkRejectPeriods(ids)
                }
            }

            Components.TimesheetsFilterPopup {
                id: filterPopup
                workspaceController: root.workspaceController
                state: state
                anchorItem: listPage.filterButtonItem
            }

            Components.TimesheetsViewsPopup {
                id: viewsPopup
                workspaceController: root.workspaceController
                state: state
                anchorItem: listPage.viewsButtonItem
            }
        }

        // ── Detail page (covers full area, z:20) ──────────────────────────
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
                sections: state.detailSections
                z: 20
                Component.onCompleted: scrollToSection(root._pendingDetailSection)

                AppWidgets.ContextualActionToolbar {
                    detailPagePinned: true
                    width: parent ? parent.width : 0
                    showBack: true
                    title: root.selectedPeriodModel.title || "Timesheet Period"
                    subtitle: root.selectedPeriodModel.statusLabel || root.selectedPeriodModel.subtitle || ""
                    busy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: state.detailActions

                    onBackRequested: root._detailOpen = false
                    onActionTriggered: function(actionId) {
                        if (root.workspaceController === null) return
                        const st = root.selectedPeriodModel ? (root.selectedPeriodModel.state || {}) : {}
                        const periodId = String(st.periodId || "")
                        if (!periodId) return
                        if (actionId === "submit")       root.workspaceController.submitPeriod({ "periodId": periodId })
                        else if (actionId === "approve") root.workspaceController.approvePeriod({ "periodId": periodId })
                        else if (actionId === "reject")  root.workspaceController.rejectPeriod({ "periodId": periodId })
                        else if (actionId === "lock")    root.workspaceController.lockPeriod({ "periodId": periodId })
                        else if (actionId === "unlock")  root.workspaceController.unlockPeriod({ "periodId": periodId })
                    }
                }

                AppWidgets.SectionScopedInlineMessage {
                    width: parent ? parent.width : 0
                    requestedVisible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
                    tone: "danger"
                    message: root.workspaceController ? root.workspaceController.errorMessage : ""
                }
                AppWidgets.SectionScopedInlineMessage {
                    width: parent ? parent.width : 0
                    requestedVisible: root._detailOpen
                        && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                        && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
                    tone: "success"
                    message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
                }

                Panels.TimesheetsDetailPanel {
                    width: parent ? parent.width : 0
                    detailPage: detailPageLoader.item
                    reviewDetail: root.selectedPeriodModel
                    entriesModel: root.entriesModel
                    entriesTableModel: root.workspaceController ? root.workspaceController.entriesTableModel : null
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
