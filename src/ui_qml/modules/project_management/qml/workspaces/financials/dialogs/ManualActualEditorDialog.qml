import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root
    objectName: "manualActualEditorDialog"

    property var workspaceController: null
    property string mode: "create"
    property var entry: null
    property string initialProjectId: ""
    property string initialTaskId: ""
    property string initialCostCodeId: ""
    property var initialDefaults: ({ "currencyCode": "", "entryKinds": [] })
    property var actualDefaults: root.initialDefaults
    property string commandId: ""
    readonly property bool _isEdit: root.mode === "edit"

    signal submitted(var payload)

    modal: true
    width: 680
    closePolicy: Popup.CloseOnEscape
    title: root._isEdit ? "Edit Manual Actual Draft" : "Create Manual Actual"
    subtitle: root._isEdit
        ? "Update this draft before it is submitted. Submitted and posted evidence remains immutable."
        : "Create a governed draft actual or adjustment. Submission, approval, and posting remain separate actions."
    primaryText: root._isEdit ? "Save Draft" : "Create Draft"
    primaryIcon: root._isEdit ? "save" : "add"
    primaryEnabled: projectSelector.selectedId.length > 0
        && costCodeSelector.selectedId.length > 0
        && String(root.actualDefaults.currencyCode || "").length > 0
    infoMessage: projectSelector.selectedId.length === 0
        ? "Select an eligible project before creating a manual actual."
        : (costCodeSelector.selectedId.length === 0
            ? "Select an active cost code for the transaction date."
            : "")

    onAccepted: root.submitDialog()
    onRejected: root.close()

    function selectedValue(options, index, fallback) {
        const item = (options || [])[index]
        return item ? String(item.value || fallback || "") : String(fallback || "")
    }

    function _entryState() {
        return root.entry ? (root.entry.state || {}) : ({})
    }

    function _selectEntryKind(value) {
        const options = root.actualDefaults.entryKinds || []
        for (let index = 0; index < options.length; ++index) {
            if (String(options[index].value || "") === String(value || "")) {
                entryKindCombo.currentIndex = index
                return
            }
        }
        entryKindCombo.currentIndex = 0
    }

    function _loadDefaults(projectId) {
        if (!root.workspaceController || !projectId) {
            root.actualDefaults = ({ "currencyCode": "", "entryKinds": [] })
            return
        }
        const result = root.workspaceController.loadManualActualDefaults(projectId)
        if (!result || !result.ok) {
            root.actualDefaults = ({ "currencyCode": "", "entryKinds": [] })
            root.errorMessage = String((result && result.message) || "Unable to load project financial defaults.")
            return
        }
        root.actualDefaults = {
            "currencyCode": String(result.currencyCode || ""),
            "entryKinds": result.entryKinds || []
        }
        entryKindCombo.currentIndex = 0
    }

    function _applyProject(value, label) {
        projectSelector.setResolvedItem({ "value": value, "label": label })
        taskSelector.contextKey = String(value || "")
        costCodeSelector.contextKey = String(value || "") + "|" + transactionDateField.text
        taskSelector.clearSelection()
        resourceSelector.clearSelection()
        costCodeSelector.clearSelection()
        root.errorMessage = ""
        root._loadDefaults(String(value || ""))
    }

    function _resolveInitialSelections() {
        if (!root.workspaceController || !root.initialProjectId) return
        const projectResult = root.workspaceController.resolveManualActualProject(root.initialProjectId)
        if (!projectResult || !projectResult.ok || !projectResult.item) {
            root.errorMessage = String((projectResult && projectResult.message)
                || "The selected project is not eligible for manual actuals.")
            return
        }
        root._applyProject(projectResult.item.value, projectResult.item.label)
        const state = root._entryState()
        const taskId = root._isEdit ? String(state.taskId || "") : root.initialTaskId
        if (taskId) {
            const taskResult = root.workspaceController.resolveManualActualTask(
                projectSelector.selectedId, taskId
            )
            if (taskResult && taskResult.ok && taskResult.item)
                taskSelector.setResolvedItem(taskResult.item)
        }
        const resourceId = root._isEdit ? String(state.resourceId || "") : ""
        if (resourceId) {
            const resourceResult = root.workspaceController.resolveManualActualResource(
                projectSelector.selectedId, resourceId
            )
            if (resourceResult && resourceResult.ok && resourceResult.item)
                resourceSelector.setResolvedItem(resourceResult.item)
        }
        const costCodeId = root._isEdit
            ? String(state.costCodeId || "") : root.initialCostCodeId
        if (costCodeId) {
            const codeResult = root.workspaceController.resolveManualActualCostCode(
                projectSelector.selectedId,
                costCodeId,
                transactionDateField.text
            )
            if (codeResult && codeResult.ok && codeResult.item)
                costCodeSelector.setResolvedItem(codeResult.item)
        }
    }

    function populateDefaults() {
        const state = root._entryState()
        descriptionField.text = root._isEdit ? String(state.description || "") : ""
        amountField.text = root._isEdit ? String(state.amount || "") : ""
        transactionDateField.text = root._isEdit
            ? String(state.transactionDate || "")
            : Qt.formatDate(new Date(), "yyyy-MM-dd")
        entryKindCombo.currentIndex = 0
        projectSelector.clearSelection()
        taskSelector.clearSelection()
        resourceSelector.clearSelection()
        costCodeSelector.clearSelection()
        root.actualDefaults = root.initialDefaults
        root.errorMessage = ""
        root._resolveInitialSelections()
        if (root._isEdit)
            root._selectEntryKind(state.entryKind)
    }

    function buildPayload() {
        const payload = {
            "projectId": projectSelector.selectedId,
            "commandId": root.commandId,
            "description": descriptionField.text,
            "entryKind": root.selectedValue(root.actualDefaults.entryKinds, entryKindCombo.currentIndex, "actual"),
            "amount": amountField.text,
            "currency": String(root.actualDefaults.currencyCode || ""),
            "transactionDate": transactionDateField.text,
            "costCodeId": costCodeSelector.selectedId,
            "taskId": taskSelector.selectedId,
            "resourceId": resourceSelector.selectedId
        }
        if (root._isEdit) {
            const state = root._entryState()
            payload["entryId"] = String(state.entryId || root.entry.id || "")
            payload["rowVersion"] = Number(state.rowVersion || 0)
        }
        return payload
    }

    function submitDialog() {
        if (projectSelector.selectedId.length === 0) {
            root.errorMessage = "Project is required."
            return
        }
        if (descriptionField.text.trim().length === 0) {
            root.errorMessage = "Description is required."
            return
        }
        if (amountField.text.trim().length === 0) {
            root.errorMessage = "Amount is required."
            return
        }
        if (costCodeSelector.selectedId.length === 0) {
            root.errorMessage = "Cost code is required."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateDefaults()

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 600 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.columnSpan: parent.columns
            Layout.fillWidth: true
            label: "Project"
            required: true
            AppControls.SearchablePagedSelector {
                id: projectSelector
                objectName: "manualActualProjectSelector"
                Layout.fillWidth: true
                placeholderText: "Select project"
                searchPlaceholder: "Search project name or code..."
                contextKey: "manual-actual-projects"
                enabled: !root._isEdit
                onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                    const result = root.workspaceController
                        ? root.workspaceController.searchManualActualProjects(query, page, pageSize)
                        : ({ "ok": false, "message": "Finance controller is unavailable." })
                    projectSelector.acceptResult(result, generation, lookupContext)
                }
                onSelectionChanged: function(value, label) { root._applyProject(value, label) }
            }
        }

        AppWidgets.FormField {
            Layout.columnSpan: parent.columns
            Layout.fillWidth: true
            label: "Description"
            required: true
            AppControls.TextField {
                id: descriptionField
                Layout.fillWidth: true
                placeholderText: "Supplier correction, travel expense, or approved adjustment"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Resource"
            AppControls.SearchablePagedSelector {
                id: resourceSelector
                objectName: "manualActualResourceSelector"
                Layout.fillWidth: true
                enabled: projectSelector.selectedId.length > 0
                allowEmpty: true
                emptyLabel: "Not linked to a resource"
                placeholderText: "Optional resource"
                searchPlaceholder: "Search resource name or code..."
                contextKey: projectSelector.selectedId
                onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                    const result = root.workspaceController
                        ? root.workspaceController.searchManualActualResources(
                            projectSelector.selectedId, query, page, pageSize
                        )
                        : ({ "ok": false, "message": "Finance controller is unavailable." })
                    resourceSelector.acceptResult(result, generation, lookupContext)
                }
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Entry type"
            required: true
            AppControls.ComboBox {
                id: entryKindCombo
                Layout.fillWidth: true
                model: root.actualDefaults.entryKinds || []
                textRole: "label"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Task"
            AppControls.SearchablePagedSelector {
                id: taskSelector
                objectName: "manualActualTaskSelector"
                Layout.fillWidth: true
                enabled: projectSelector.selectedId.length > 0
                allowEmpty: true
                emptyLabel: "Not linked to a task"
                placeholderText: "Optional task"
                searchPlaceholder: "Search task name, code, or WBS..."
                onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                    const requestedProject = projectSelector.selectedId
                    const result = root.workspaceController
                        ? root.workspaceController.searchManualActualTasks(
                            requestedProject, query, page, pageSize
                        )
                        : ({ "ok": false, "message": "Finance controller is unavailable." })
                    taskSelector.acceptResult(result, generation, lookupContext)
                }
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Cost code"
            required: true
            AppControls.SearchablePagedSelector {
                id: costCodeSelector
                objectName: "manualActualCostCodeSelector"
                Layout.fillWidth: true
                enabled: projectSelector.selectedId.length > 0
                placeholderText: "Select cost code"
                searchPlaceholder: "Search cost code or name..."
                onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                    const requestedProject = projectSelector.selectedId
                    const requestedDate = transactionDateField.text
                    const result = root.workspaceController
                        ? root.workspaceController.searchManualActualCostCodes(
                            requestedProject, query, page, pageSize, requestedDate
                        )
                        : ({ "ok": false, "message": "Finance controller is unavailable." })
                    costCodeSelector.acceptResult(result, generation, lookupContext)
                }
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
                text: String(root.actualDefaults.currencyCode || "")
                readOnly: true
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Transaction date"
            required: true
            AppControls.DateField {
                id: transactionDateField
                Layout.fillWidth: true
                placeholderText: "YYYY-MM-DD"
                onTextChanged: {
                    costCodeSelector.contextKey = projectSelector.selectedId + "|" + text
                    costCodeSelector.clearSelection()
                }
            }
        }
    }
}
