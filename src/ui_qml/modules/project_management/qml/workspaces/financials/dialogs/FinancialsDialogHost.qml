import QtQuick

Item {
    id: root

    property var workspaceController: null
    property string selectedProjectId: ""
    property string selectedProjectLabel: ""
    property var manualActualDefaults: ({ "currencyCode": "", "entryKinds": [] })

    function _handleResult(dialog, result) {
        if (result && result.ok) {
            dialog.close()
        } else {
            dialog.errorMessage = (result && result.message) || "An unexpected error occurred."
        }
    }

    function openCreateManualActualDialog() {
        editorDialog.commandId = root.workspaceController
            ? root.workspaceController.newFinancialCommandId() : ""
        editorDialog.errorMessage = ""
        editorDialog.open()
    }

    function openCreateCostCodeDialog() {
        costCodeEditorDialog.errorMessage = ""
        costCodeEditorDialog.open()
    }

    function openBudgetVersionDialog(mode, budget) {
        budgetVersionEditorDialog.mode = String(mode || "create")
        budgetVersionEditorDialog.projectId = root.selectedProjectId
        budgetVersionEditorDialog.budget = budget || null
        budgetVersionEditorDialog.errorMessage = ""
        budgetVersionEditorDialog.open()
    }

    function openBudgetLineDialog(mode, budget, line) {
        budgetLineEditorDialog.mode = String(mode || "create")
        budgetLineEditorDialog.projectId = root.selectedProjectId
        budgetLineEditorDialog.budget = budget || null
        budgetLineEditorDialog.line = line || null
        budgetLineEditorDialog.errorMessage = ""
        budgetLineEditorDialog.open()
    }

    function openBudgetLifecycleDialog(action, budget, line) {
        budgetLifecycleDialog.action = String(action || "submit")
        budgetLifecycleDialog.budget = budget || null
        budgetLifecycleDialog.line = line || null
        budgetLifecycleDialog.errorMessage = ""
        budgetLifecycleDialog.open()
    }

    function openForecastGenerationDialog() {
        forecastGenerationDialog.projectId = root.selectedProjectId
        forecastGenerationDialog.projectLabel = root.selectedProjectLabel
        forecastGenerationDialog.errorMessage = ""
        forecastGenerationDialog.open()
    }

    function openForecastLifecycleDialog(action, forecast) {
        forecastLifecycleDialog.action = String(action || "submit")
        forecastLifecycleDialog.forecast = forecast || null
        forecastLifecycleDialog.projectLabel = root.selectedProjectLabel
        forecastLifecycleDialog.errorMessage = ""
        forecastLifecycleDialog.open()
    }

    function openFinancialChangeRequestDialog(mode, change) {
        financialChangeRequestDialog.mode = String(mode || "create")
        financialChangeRequestDialog.projectId = root.selectedProjectId
        financialChangeRequestDialog.change = change || null
        financialChangeRequestDialog.errorMessage = ""
        financialChangeRequestDialog.open()
    }

    function openFinancialChangeImpactDialog(mode, change, impact) {
        financialChangeImpactDialog.mode = String(mode || "create")
        financialChangeImpactDialog.projectId = root.selectedProjectId
        financialChangeImpactDialog.change = change || null
        financialChangeImpactDialog.impact = impact || null
        financialChangeImpactDialog.errorMessage = ""
        financialChangeImpactDialog.open()
    }

    function openFinancialChangeLifecycleDialog(action, change, impact) {
        financialChangeLifecycleDialog.action = String(action || "submit")
        financialChangeLifecycleDialog.change = change || null
        financialChangeLifecycleDialog.impact = impact || null
        financialChangeLifecycleDialog.errorMessage = ""
        financialChangeLifecycleDialog.open()
    }

    // Opens the shared reject/post/reverse decision dialog for the given
    // canonical ProjectCostEntry. Submit and approve need no extra fields
    // and are dispatched directly by the caller without a dialog.
    function openActualDecisionDialog(mode, entryId, rowVersion) {
        actualLifecycleDialog.mode = String(mode || "reject")
        actualLifecycleDialog.entryId = String(entryId || "")
        actualLifecycleDialog.rowVersion = Number(rowVersion || 0)
        actualLifecycleDialog.commandId = root.workspaceController
            ? root.workspaceController.newFinancialCommandId() : ""
        actualLifecycleDialog.errorMessage = ""
        actualLifecycleDialog.open()
    }

    ManualActualEditorDialog {
        id: editorDialog

        initialProjectId: root.selectedProjectId
        initialDefaults: root.manualActualDefaults
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            const result = root.workspaceController.createManualActual(payload)
            root._handleResult(editorDialog, result)
        }
    }

    CostCodeEditorDialog {
        id: costCodeEditorDialog

        selectedProjectId: root.selectedProjectId
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            const result = root.workspaceController.createCostCode(payload)
            root._handleResult(costCodeEditorDialog, result)
        }
    }

    ActualLifecycleDialog {
        id: actualLifecycleDialog

        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onDecided: function(mode, payload) {
            if (!root.workspaceController) return
            let result
            if (mode === "post") {
                result = root.workspaceController.postActual(payload)
            } else if (mode === "reverse") {
                result = root.workspaceController.reverseActual(payload)
            } else {
                result = root.workspaceController.rejectActual(payload)
            }
            root._handleResult(actualLifecycleDialog, result)
        }
    }

    BudgetVersionEditorDialog {
        id: budgetVersionEditorDialog
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(mode, projectId, budgetId, rowVersion, name, currency, notes) {
            if (!root.workspaceController) return
            let result
            if (mode === "edit") {
                result = root.workspaceController.updateBudget(
                    budgetId, rowVersion, name, notes
                )
            } else if (mode === "successor") {
                result = root.workspaceController.createBudgetSuccessor(budgetId, name)
            } else {
                result = root.workspaceController.createBudgetVersion(
                    projectId, name, currency
                )
            }
            root._handleResult(budgetVersionEditorDialog, result)
        }
    }

    BudgetLineEditorDialog {
        id: budgetLineEditorDialog
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(
            mode, lineId, lineVersion, budgetId, parentVersion,
            costCodeId, taskId, description, amount, currency
        ) {
            if (!root.workspaceController) return
            const result = mode === "edit"
                ? root.workspaceController.updateBudgetLine(
                    lineId, lineVersion, parentVersion, costCodeId,
                    taskId, description, amount, currency
                )
                : root.workspaceController.addBudgetLine(
                    budgetId, parentVersion, costCodeId, taskId,
                    description, amount, currency
                )
            root._handleResult(budgetLineEditorDialog, result)
        }
    }

    BudgetLifecycleDialog {
        id: budgetLifecycleDialog
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onDecided: function(
            action, budgetId, budgetVersion, approvalRequestId,
            lineId, lineVersion, notes
        ) {
            if (!root.workspaceController) return
            let result
            if (action === "submit") {
                result = root.workspaceController.submitBudget(
                    budgetId, budgetVersion, notes
                )
            } else if (action === "request_approval") {
                result = root.workspaceController.requestBudgetApproval(
                    budgetId, budgetVersion, notes
                )
            } else if (action === "approve" || action === "reject") {
                result = root.workspaceController.decideBudgetApproval(
                    approvalRequestId, action === "approve", notes
                )
            } else if (action === "close") {
                result = root.workspaceController.closeBudget(
                    budgetId, budgetVersion, notes
                )
            } else if (action === "delete_line") {
                result = root.workspaceController.deleteBudgetLine(
                    lineId, lineVersion, budgetVersion
                )
            } else {
                result = root.workspaceController.deleteBudget(
                    budgetId, budgetVersion
                )
            }
            root._handleResult(budgetLifecycleDialog, result)
        }
    }

    ForecastGenerationDialog {
        id: forecastGenerationDialog
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            root._handleResult(
                forecastGenerationDialog,
                root.workspaceController.generateForecast(payload)
            )
        }
    }

    ForecastLifecycleDialog {
        id: forecastLifecycleDialog
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onDecided: function(action, forecastId, version, requestId, notes) {
            if (!root.workspaceController) return
            let result
            if (action === "submit") {
                result = root.workspaceController.submitForecast(forecastId, version, notes)
            } else if (action === "request_approval") {
                result = root.workspaceController.requestForecastApproval(
                    forecastId, version, notes
                )
            } else {
                result = root.workspaceController.decideForecastApproval(
                    requestId, action === "approve", notes
                )
            }
            root._handleResult(forecastLifecycleDialog, result)
        }
    }

    FinancialChangeRequestDialog {
        id: financialChangeRequestDialog
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            const result = financialChangeRequestDialog.mode === "edit"
                ? root.workspaceController.updateFinancialChange(payload)
                : root.workspaceController.createFinancialChange(payload)
            root._handleResult(financialChangeRequestDialog, result)
        }
    }

    FinancialChangeImpactDialog {
        id: financialChangeImpactDialog
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            const result = financialChangeImpactDialog.mode === "edit"
                ? root.workspaceController.updateFinancialChangeImpact(payload)
                : root.workspaceController.addFinancialChangeImpact(payload)
            root._handleResult(financialChangeImpactDialog, result)
        }
    }

    FinancialChangeLifecycleDialog {
        id: financialChangeLifecycleDialog
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onDecided: function(action, payload) {
            if (!root.workspaceController) return
            let result
            if (action === "submit") {
                result = root.workspaceController.submitFinancialChange(payload)
            } else if (action === "remove_impact") {
                result = root.workspaceController.removeFinancialChangeImpact(payload)
            } else {
                result = root.workspaceController.decideFinancialChange(
                    String(payload.approvalRequestId || ""),
                    action === "approve",
                    String(payload.notes || "")
                )
            }
            root._handleResult(financialChangeLifecycleDialog, result)
        }
    }
}
