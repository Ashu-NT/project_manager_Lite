pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "components" as Components

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementTimesheetsWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.reviewQueueWorkspace
        : null

    TimesheetsWorkspaceState {
        id: state
        pmCatalog: root.pmCatalog
        workspaceController: root.workspaceController
    }

    readonly property var workspaceModel: state.workspaceModel
    readonly property var overviewModel: state.overviewModel
    readonly property var reviewQueueModel: state.reviewQueueModel
    readonly property var selectedPeriodModel: state.selectedPeriodModel
    readonly property bool _hasInspector: String(root.workspaceController
        ? root.workspaceController.selectedQueuePeriodId : "").length > 0
    readonly property int _sideInspectorThreshold: Theme.AppTheme.inspectorWidth + 720
    readonly property bool _useSideInspector: root.width >= root._sideInspectorThreshold

    property var _columns: state.columns

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    function _saveColumnState(columns) {
        state.saveColumnState(columns)
        root._columns = state.columns
    }

    function _clearInspector() {
        compactInspector.close()
        if (root.workspaceController !== null)
            root.workspaceController.selectQueuePeriod("")
        Qt.callLater(listPage.restoreTableFocus)
    }

    function _requestReviewAction(actionId) {
        if (root.workspaceController === null || !root._hasInspector) return
        reviewDecisionDialog.actionMode = actionId
        reviewDecisionDialog.reviewData = root.selectedPeriodModel
        reviewDecisionDialog.open()
    }

    on_UseSideInspectorChanged: {
        if (root._useSideInspector) compactInspector.close()
        else if (root._hasInspector) compactInspector.open()
    }
    on_HasInspectorChanged: {
        if (!root._hasInspector) compactInspector.close()
        else if (!root._useSideInspector) compactInspector.open()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Components.TimesheetsListPage {
            id: listPage
            objectName: "timesheetReviewQueueListPage"
            Layout.fillWidth: true
            Layout.fillHeight: true
            workspaceController: root.workspaceController
            state: state
            overviewModel: root.overviewModel
            reviewQueueModel: root.reviewQueueModel

            onRowSelected: function(rowId) {
                if (root.workspaceController !== null)
                    root.workspaceController.selectQueuePeriod(rowId)
            }
            onRowActivated: function(rowId) {
                if (root.workspaceController !== null)
                    root.workspaceController.selectQueuePeriod(rowId)
            }
            onColumnsStateChanged: function(columns) {
                root._saveColumnState(columns)
            }
            onFilterClicked: filterPopup.open()
            onRefreshRequested: {
                if (root.workspaceController !== null)
                    root.workspaceController.refresh()
            }
        }

        Components.TimesheetReviewInspector {
            objectName: "reviewQueueSideInspector"
            Layout.fillHeight: true
            Layout.preferredWidth: Theme.AppTheme.inspectorWidth
            visible: root._hasInspector && root._useSideInspector
            reviewData: root.selectedPeriodModel
            actions: state.detailActions
            busy: root.workspaceController ? root.workspaceController.isBusy : false
            errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
            onCloseRequested: root._clearInspector()
            onActionRequested: function(actionId) {
                root._requestReviewAction(actionId)
            }
        }
    }

    Components.TimesheetsFilterPopup {
        id: filterPopup
        workspaceController: root.workspaceController
        state: state
        onClosed: Qt.callLater(listPage.restoreTableFocus)
    }

    Popup {
        id: compactInspector
        parent: root
        x: Math.max(0, root.width - width)
        y: 0
        width: Math.min(Theme.AppTheme.inspectorWidth, root.width * 0.9)
        height: root.height
        padding: 0
        modal: false
        closePolicy: Popup.NoAutoClose

        contentItem: Components.TimesheetReviewInspector {
            objectName: "reviewQueueCompactInspector"
            reviewData: root.selectedPeriodModel
            actions: state.detailActions
            busy: root.workspaceController ? root.workspaceController.isBusy : false
            errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
            onCloseRequested: root._clearInspector()
            onActionRequested: function(actionId) {
                root._requestReviewAction(actionId)
            }
        }
    }

    Connections {
        target: root.workspaceController
        function onSelectedQueuePeriodIdChanged() {
            if (!root._useSideInspector && root._hasInspector)
                compactInspector.open()
            else if (!root._hasInspector || root._useSideInspector)
                compactInspector.close()
        }
    }

    Components.TimesheetReviewDecisionDialog {
        id: reviewDecisionDialog
        objectName: "reviewQueueDecisionDialog"
        reviewData: root.selectedPeriodModel
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onClosed: Qt.callLater(listPage.restoreTableFocus)

        onSubmitted: function(payload) {
            if (root.workspaceController === null) return
            let result = ({ "ok": false })
            if (reviewDecisionDialog.actionMode === "approve")
                result = root.workspaceController.approvePeriod(payload)
            else if (reviewDecisionDialog.actionMode === "reject")
                result = root.workspaceController.rejectPeriod(payload)
            else if (reviewDecisionDialog.actionMode === "lock")
                result = root.workspaceController.lockPeriod(payload)
            else if (reviewDecisionDialog.actionMode === "unlock")
                result = root.workspaceController.unlockPeriod(payload)
            if (result.ok === true) {
                reviewDecisionDialog.close()
                root._clearInspector()
            } else {
                reviewDecisionDialog.errorMessage = String(result.message
                    || "The review item changed. Refresh and try again.")
            }
        }
    }
}
