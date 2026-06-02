pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import "../components"

Item {
    id: root

    property var workspaceController: null
    property var pmCatalog: null
    property var baselinesModel: ({
        "options": [], "selectedBaselineAId": "", "selectedBaselineBId": "",
        "includeUnchanged": false, "summaryText": "", "emptyState": ""
    })
    property string selectedBaselineRegisterId: ""
    property string selectedBaselineRegisterStatus: ""

    signal selectedBaselineRegisterIdChanged(string registerId)
    signal createBaselineRequested()

    readonly property var _compareColumns: [
        { "key": "activity", "label": "Activity",       "flex": 1.6, "sortable": true },
        { "key": "change",   "label": "Change",         "flex": 0.8, "type": "status" },
        { "key": "shift",    "label": "Shift Summary",  "flex": 1.7 },
        { "key": "dates",    "label": "Baseline Dates", "flex": 2.1 },
        { "key": "cost",     "label": "Cost Delta",     "flex": 1.0 }
    ]
    readonly property var _registerColumns: [
        { "key": "baseline",    "label": "Baseline",    "flex": 1.4, "sortable": true },
        { "key": "created",     "label": "Created",     "flex": 1.0 },
        { "key": "approvedBy",  "label": "Approved By", "flex": 1.0 },
        { "key": "status",      "label": "Status",      "flex": 0.9, "type": "status" }
    ]
    readonly property var _varianceColumns: [
        { "key": "task",           "label": "Task",           "flex": 2.0, "sortable": true },
        { "key": "startVariance",  "label": "Start Variance", "flex": 1.0 },
        { "key": "finishVariance", "label": "Finish Variance","flex": 1.0 },
        { "key": "costVariance",   "label": "Cost Delta",     "flex": 1.0 },
        { "key": "status",         "label": "Shift",          "flex": 0.8, "type": "status" },
        { "key": "created",        "label": "Recorded",       "flex": 0.9 }
    ]

    function _optionIndex(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return list.length > 0 ? 0 : -1
    }

    SchedulingPanelFrame {
        anchors.fill: parent
        title: "Baselines"
        subtitle: "Create, compare, archive, and review schedule freeze points for governance."

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.AppTheme.marginMd
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: Theme.AppTheme.spacingSm

                SchedulingActionBar {
                    Layout.fillWidth: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: {
                        const canApprove = root.pmCatalog ? root.pmCatalog.pmCapabilityController.canApproveBaseline : true
                        return [
                            { "id": "save",    "label": "Save Baseline", "icon": "register", "enabled": String(root.workspaceController ? root.workspaceController.selectedProjectId : "").length > 0 },
                            { "id": "submit",  "label": "Submit",  "icon": "approve", "enabled": root.selectedBaselineRegisterStatus === "draft" && root.selectedBaselineRegisterId.length > 0 },
                            { "id": "approve", "label": "Approve", "icon": "success", "enabled": canApprove && root.selectedBaselineRegisterStatus === "submitted" && root.selectedBaselineRegisterId.length > 0 },
                            { "id": "reject",  "label": "Reject",  "icon": "reject",  "danger": true, "enabled": canApprove && root.selectedBaselineRegisterStatus === "submitted" && root.selectedBaselineRegisterId.length > 0 },
                            { "id": "compare", "label": "Compare", "icon": "refresh", "enabled": (root.baselinesModel.options || []).length > 1 },
                            { "id": "archive", "label": "Archive", "icon": "delete",  "danger": true, "enabled": root.selectedBaselineRegisterId.length > 0 },
                            { "id": "export",  "label": "Export",  "icon": "export",  "enabled": true }
                        ]
                    }

                    AppControls.ComboBox {
                        Layout.preferredWidth: 180
                        model: root.baselinesModel.options || []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            && (root.baselinesModel.options || []).length > 0
                        currentIndex: root._optionIndex(
                            root.baselinesModel.options || [],
                            root.baselinesModel.selectedBaselineAId || ""
                        )
                        onActivated: function(index) {
                            const option = (root.baselinesModel.options || [])[index]
                            if (root.workspaceController !== null && option)
                                root.workspaceController.selectBaselineA(String(option.value || ""))
                        }
                    }

                    AppControls.ComboBox {
                        Layout.preferredWidth: 180
                        model: root.baselinesModel.options || []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            && (root.baselinesModel.options || []).length > 0
                        currentIndex: root._optionIndex(
                            root.baselinesModel.options || [],
                            root.baselinesModel.selectedBaselineBId || ""
                        )
                        onActivated: function(index) {
                            const option = (root.baselinesModel.options || [])[index]
                            if (root.workspaceController !== null && option)
                                root.workspaceController.selectBaselineB(String(option.value || ""))
                        }
                    }

                    AppControls.CheckBox {
                        text: "Include unchanged"
                        checked: Boolean(root.baselinesModel.includeUnchanged)
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        onToggled: {
                            if (root.workspaceController !== null)
                                root.workspaceController.setIncludeUnchanged(checked)
                        }
                    }

                    onActionTriggered: function(actionId) {
                        if (root.workspaceController === null) return
                        if (actionId === "save") {
                            root.createBaselineRequested()
                        } else if (actionId === "submit" && root.selectedBaselineRegisterId.length > 0) {
                            root.workspaceController.submitBaseline(root.selectedBaselineRegisterId)
                        } else if (actionId === "approve" && root.selectedBaselineRegisterId.length > 0) {
                            root.workspaceController.approveBaseline(root.selectedBaselineRegisterId)
                        } else if (actionId === "reject" && root.selectedBaselineRegisterId.length > 0) {
                            root.workspaceController.rejectBaseline(root.selectedBaselineRegisterId)
                        } else if (actionId === "compare") {
                            root.workspaceController.refresh()
                        } else if (actionId === "archive" && root.selectedBaselineRegisterId.length > 0) {
                            root.workspaceController.deleteBaseline(root.selectedBaselineRegisterId)
                        } else if (actionId === "export") {
                            root.workspaceController.exportSchedule()
                        }
                    }
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: String(root.baselinesModel.summaryText || root.baselinesModel.emptyState || "").length > 0
                    tone: "info"
                    message: root.baselinesModel.summaryText || root.baselinesModel.emptyState || ""
                }

                AppWidgets.TableToolbar {
                    id: baselinesToolbar
                    Layout.fillWidth: true
                    searchText: root.workspaceController ? root.workspaceController.baselinesSearchText : ""
                    searchPlaceholder: "Search baselines..."
                    showCustomize: true
                    showExport: true
                    showRefresh: false
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onSearchChanged: function(text) { if (root.workspaceController) root.workspaceController.setBaselinesSearchText(text) }
                    onCustomizeClicked: baselineRegisterTable.openColumnCustomizer(baselinesToolbar.customizeButtonItem)
                    onExportRequested: { if (root.workspaceController !== null) root.workspaceController.exportSchedule() }
                }

                AppWidgets.DataTable {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 340
                    columns: root._compareColumns
                    sourceModel: root.workspaceController ? root.workspaceController.baselineCompareTableModel : null
                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                    emptyText: root.baselinesModel.emptyState || "Choose two baselines to compare schedule drift."
                }

                AppWidgets.DataTable {
                    id: baselineRegisterTable
                    Layout.fillWidth: true
                    Layout.preferredHeight: 360
                    columns: root._registerColumns
                    sourceModel: root.workspaceController ? root.workspaceController.baselineRegisterTableModel : null
                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                    emptyText: root.workspaceController ? (root.workspaceController.baselineRegister.emptyState || "No baseline register entries are available.") : "No baseline register entries are available."
                    selectedRowId: root.selectedBaselineRegisterId
                    onRowSelected: function(rowId) {
                        root.selectedBaselineRegisterIdChanged(String(rowId || ""))
                        if (root.workspaceController !== null)
                            root.workspaceController.loadVarianceRecordsForBaseline(String(rowId || ""))
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Approval-Time Variance"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }

                AppWidgets.DataTable {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 520
                    columns: root._varianceColumns
                    sourceModel: root.workspaceController ? root.workspaceController.baselineVarianceTableModel : null
                    loading: root.workspaceController ? root.workspaceController.isLoading : false
                    emptyText: root.selectedBaselineRegisterId.length > 0
                        ? "No variance records are stored for this baseline."
                        : "Select a baseline from the register to review its approval-time variance."
                }

                Item { Layout.preferredHeight: Theme.AppTheme.marginMd }
            }
        }
    }
}
