import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var workspaceController: null
    property string mode: "create"
    property string projectId: ""
    property var change: null
    property var impact: null
    signal submitted(var payload)

    readonly property bool _editing: root.mode === "edit"
    readonly property var _changeState: root.change ? (root.change.state || {}) : ({})
    readonly property var _impactState: root.impact ? (root.impact.state || {}) : ({})
    readonly property string _impactType: {
        const option = impactTypeCombo.model[impactTypeCombo.currentIndex]
        return option ? String(option.value || "") : ""
    }
    readonly property bool _schedule: root._impactType === "schedule"
    readonly property var _types: [
        { "value": "budget", "label": "Budget" },
        { "value": "forecast", "label": "Forecast" },
        { "value": "schedule", "label": "Schedule" }
    ]

    width: 700
    title: root._editing ? "Edit Financial Change Impact" : "Add Financial Change Impact"
    subtitle: "Each impact is validated by its authoritative Budget, Forecast, or Scheduling service."
    primaryText: root._editing ? "Save Changes" : "Add Impact"
    primaryIcon: root._editing ? "save" : "add"

    function _typeIndex(value) {
        for (let index = 0; index < root._types.length; index += 1) {
            if (root._types[index].value === String(value || "")) return index
        }
        return 0
    }

    function populate() {
        descriptionField.text = root._editing ? String(root.impact.title || "") : ""
        amountField.text = root._editing ? String(root._impactState.amount || "0") : "0"
        targetLineField.text = root._editing ? String(root._impactState.targetLineId || "") : ""
        scheduleStartField.text = root._editing ? String(root._impactState.scheduleStart || "") : ""
        scheduleFinishField.text = root._editing ? String(root._impactState.scheduleFinish || "") : ""
        impactTypeCombo.currentIndex = root._typeIndex(
            root._editing ? root._impactState.impactType : "budget"
        )
        costCodeSelector.clearSelection()
        taskSelector.clearSelection()
        if (root._editing && root._impactState.costCodeId && root.workspaceController) {
            const result = root.workspaceController.resolveBudgetCostCode(
                root.projectId, String(root._impactState.costCodeId)
            )
            if (result && result.ok && result.item) costCodeSelector.setResolvedItem(result.item)
        }
        if (root._editing && root._impactState.taskId && root.workspaceController) {
            const result = root.workspaceController.resolveBudgetTask(
                root.projectId, String(root._impactState.taskId)
            )
            if (result && result.ok && result.item) taskSelector.setResolvedItem(result.item)
        }
        root.errorMessage = ""
        descriptionField.forceActiveFocus()
    }

    function submitDialog() {
        if (!descriptionField.text.trim()) {
            root.errorMessage = "Impact description is required."
            descriptionField.forceActiveFocus()
            return
        }
        const amount = amountField.text.trim().replace(",", ".")
        if (!root._schedule && !/^-?\d+(?:\.\d+)?$/.test(amount)) {
            root.errorMessage = "Amount must be a valid decimal value."
            amountField.forceActiveFocus()
            return
        }
        if (root._schedule && !taskSelector.selectedId) {
            root.errorMessage = "A task is required for a Schedule impact."
            taskSelector.forceActiveFocus()
            return
        }
        if (root._schedule && (!scheduleStartField.text || !scheduleFinishField.text)) {
            root.errorMessage = "Schedule start and finish dates are required."
            scheduleStartField.forceActiveFocus()
            return
        }
        root.errorMessage = ""
        root.submitted({
            "changeId": String(root.change ? root.change.id || "" : ""),
            "changeVersion": Number(root._changeState.version || 0),
            "impactId": String(root.impact ? root.impact.id || "" : ""),
            "impactVersion": Number(root._impactState.version || 0),
            "impactType": root._impactType,
            "description": descriptionField.text.trim(),
            "amount": root._schedule ? "0" : amount,
            "currency": root._schedule ? "" : String(root._changeState.currency || ""),
            "costCodeId": root._schedule ? "" : costCodeSelector.selectedId,
            "taskId": taskSelector.selectedId,
            "targetLineId": root._schedule ? "" : targetLineField.text.trim(),
            "scheduleStart": root._schedule ? scheduleStartField.text.trim() : "",
            "scheduleFinish": root._schedule ? scheduleFinishField.text.trim() : ""
        })
    }

    onOpened: root.populate()
    onRejected: root.close()

    GridLayout {
        Layout.fillWidth: true
        columns: width >= 580 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Impact type"
            required: true
            AppControls.ComboBox {
                id: impactTypeCombo
                Layout.fillWidth: true
                model: root._types
                textRole: "label"
                enabled: !root._editing
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Description"
            required: true
            AppControls.TextField {
                id: descriptionField
                Layout.fillWidth: true
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            visible: !root._schedule
            label: "Amount"
            required: true
            AppControls.TextField {
                id: amountField
                Layout.fillWidth: true
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            visible: !root._schedule
            label: "Cost code"
            AppControls.SearchablePagedSelector {
                id: costCodeSelector
                Layout.fillWidth: true
                allowEmpty: true
                searchPlaceholder: "Search cost code or name..."
                onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                    const result = root.workspaceController
                        ? root.workspaceController.searchBudgetCostCodes(
                            root.projectId, query, page, pageSize
                        ) : ({ "ok": false, "message": "Finance controller is unavailable." })
                    costCodeSelector.acceptResult(result, generation, lookupContext)
                }
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: root._schedule ? "Task" : "Task (optional)"
            required: root._schedule
            AppControls.SearchablePagedSelector {
                id: taskSelector
                Layout.fillWidth: true
                allowEmpty: !root._schedule
                searchPlaceholder: "Search task name, code, or WBS..."
                onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                    const result = root.workspaceController
                        ? root.workspaceController.searchBudgetTasks(
                            root.projectId, query, page, pageSize
                        ) : ({ "ok": false, "message": "Finance controller is unavailable." })
                    taskSelector.acceptResult(result, generation, lookupContext)
                }
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            visible: !root._schedule
            label: "Existing line ID (optional)"
            AppControls.TextField {
                id: targetLineField
                Layout.fillWidth: true
                placeholderText: "Leave blank to create a new line"
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            visible: root._schedule
            label: "Start"
            required: root._schedule
            AppControls.DateField { id: scheduleStartField; Layout.fillWidth: true }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            visible: root._schedule
            label: "Finish"
            required: root._schedule
            AppControls.DateField { id: scheduleFinishField; Layout.fillWidth: true }
        }
    }
}
