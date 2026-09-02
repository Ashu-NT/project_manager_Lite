import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var workspaceController: null
    property string projectId: ""
    property string mode: "create"
    property var budget: null
    property var line: null

    signal submitted(
        string mode, string lineId, int lineVersion, string budgetId,
        int parentVersion, string costCodeId, string taskId,
        string description, string amount, string currency
    )

    readonly property bool _isEdit: root.mode === "edit"
    readonly property var _budgetState: root.budget ? (root.budget.state || {}) : ({})
    readonly property var _lineState: root.line ? (root.line.state || {}) : ({})

    width: 680
    title: root._isEdit ? "Edit Budget Line" : "Add Budget Line"
    subtitle: "Amounts and dimensions are validated against the selected draft Budget on the server."
    primaryText: root._isEdit ? "Save Changes" : "Add Line"
    primaryIcon: root._isEdit ? "save" : "add"

    function populate() {
        descriptionField.text = root._isEdit ? String(root.line.title || "") : ""
        amountField.text = root._isEdit ? String(root._lineState.amount || "") : ""
        costCodeSelector.clearSelection()
        taskSelector.clearSelection()
        if (root._isEdit && root._lineState.costCodeId) {
            const result = root.workspaceController.resolveBudgetCostCode(
                root.projectId, String(root._lineState.costCodeId)
            )
            if (result && result.ok && result.item) costCodeSelector.setResolvedItem(result.item)
        }
        if (root._isEdit && root._lineState.taskId) {
            const result = root.workspaceController.resolveBudgetTask(
                root.projectId, String(root._lineState.taskId)
            )
            if (result && result.ok && result.item) taskSelector.setResolvedItem(result.item)
        }
        root.errorMessage = ""
        costCodeSelector.forceActiveFocus()
    }

    function submitDialog() {
        if (!costCodeSelector.selectedId) {
            root.errorMessage = "Cost code is required."
            costCodeSelector.forceActiveFocus()
            return
        }
        if (!descriptionField.text.trim()) {
            root.errorMessage = "Description is required."
            descriptionField.forceActiveFocus()
            return
        }
        const normalizedAmount = amountField.text.trim().replace(",", ".")
        if (!/^\d+(?:\.\d+)?$/.test(normalizedAmount)) {
            root.errorMessage = "Amount must be a non-negative decimal value."
            amountField.forceActiveFocus()
            return
        }
        root.errorMessage = ""
        root.submitted(
            root.mode,
            String(root.line ? root.line.id || "" : ""),
            Number(root._lineState.rowVersion || 0),
            String(root.budget ? root.budget.id || "" : ""),
            Number(root._budgetState.rowVersion || 0),
            costCodeSelector.selectedId,
            taskSelector.selectedId,
            descriptionField.text.trim(),
            normalizedAmount,
            String(root._budgetState.currency || "")
        )
    }

    onOpened: root.populate()
    onRejected: root.close()

    GridLayout {
        Layout.fillWidth: true
        columns: width >= 560 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Cost code"
            required: true
            AppControls.SearchablePagedSelector {
                id: costCodeSelector
                Layout.fillWidth: true
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
            label: "Task"
            AppControls.SearchablePagedSelector {
                id: taskSelector
                Layout.fillWidth: true
                allowEmpty: true
                emptyLabel: "Not linked to a task"
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
            Layout.columnSpan: parent.columns
            label: "Description"
            required: true
            AppControls.TextField {
                id: descriptionField
                Layout.fillWidth: true
                placeholderText: "Labor, materials, or delivery package"
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Amount"
            required: true
            AppControls.TextField {
                id: amountField
                Layout.fillWidth: true
                inputMethodHints: Qt.ImhFormattedNumbersOnly
                placeholderText: "0.00"
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Currency"
            required: true
            AppControls.TextField {
                Layout.fillWidth: true
                readOnly: true
                text: String(root._budgetState.currency || "")
            }
        }
    }
}
