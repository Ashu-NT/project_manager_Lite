import workspaces.financials.budgets.dialogs 1.0
import workspaces.financials.cost.dialogs 1.0
import workspaces.financials.financial_changes.dialogs 1.0
import workspaces.financials.forecasts.dialogs 1.0
import workspaces.financials.governance.dialogs 1.0
import workspaces.financials.invoicing.dialogs 1.0
import workspaces.financials.rate_cards.dialogs 1.0
import QtQuick

Item {
    id: root

    property var workspaceController: null
    property string selectedProjectId: ""
    property string selectedProjectLabel: ""
    property string selectedActualEntryId: ""
    property string selectedBillingPreparationId: ""
    property Item focusFallbackTarget: null
    property var manualActualDefaults: ({ "currencyCode": "", "entryKinds": [] })

    function _handleResult(dialog, result) {
        if (result && result.ok) {
            dialog.close()
        } else {
            dialog.errorMessage = (result && result.message) || "An unexpected error occurred."
        }
    }

    function _openSetupDialog(dialog) {
        const window = root.Window.window
        dialog.focusReturnTarget = window ? window.activeFocusItem : null
        dialog.open()
    }

    function openCreateManualActualDialog() {
        editorDialog.mode = "create"
        editorDialog.entry = null
        editorDialog.commandId = root.workspaceController
            ? root.workspaceController.newFinancialCommandId() : ""
        editorDialog.errorMessage = ""
        root._openSetupDialog(editorDialog)
    }

    function openEditManualActualDialog(entry) {
        editorDialog.mode = "edit"
        editorDialog.entry = entry || null
        editorDialog.commandId = ""
        editorDialog.errorMessage = ""
        root._openSetupDialog(editorDialog)
    }

    function openCostCodeDialog(mode, costCode) {
        costCodeEditorDialog.mode = String(mode || "create")
        costCodeEditorDialog.costCode = costCode || null
        costCodeEditorDialog.errorMessage = ""
        root._openSetupDialog(costCodeEditorDialog)
    }

    function openFinancialProfileDialog(profile) {
        financialProfileEditorDialog.profile = profile || null
        financialProfileEditorDialog.errorMessage = ""
        root._openSetupDialog(financialProfileEditorDialog)
    }

    function openFinancialSetupLifecycleDialog(action, profile, costCode, restriction) {
        financialSetupLifecycleDialog.action = String(action || "")
        financialSetupLifecycleDialog.profile = profile || null
        financialSetupLifecycleDialog.costCode = costCode || null
        financialSetupLifecycleDialog.restriction = restriction || null
        financialSetupLifecycleDialog.errorMessage = ""
        root._openSetupDialog(financialSetupLifecycleDialog)
    }

    function openCostCodeRestrictionDialog() {
        costCodeRestrictionDialog.errorMessage = ""
        root._openSetupDialog(costCodeRestrictionDialog)
    }

    function openBudgetVersionDialog(mode, budget) {
        budgetVersionEditorDialog.mode = String(mode || "create")
        budgetVersionEditorDialog.projectId = root.selectedProjectId
        budgetVersionEditorDialog.budget = budget || null
        budgetVersionEditorDialog.errorMessage = ""
        budgetVersionEditorDialog.open()
    }

    function openBillingProfileDialog() {
        billingProfileDialog.projectId = root.selectedProjectId
        billingProfileDialog.errorMessage = ""
        root._openSetupDialog(billingProfileDialog)
    }

    function openBillingScheduleLineDialog() {
        billingScheduleLineDialog.projectId = root.selectedProjectId
        billingScheduleLineDialog.errorMessage = ""
        root._openSetupDialog(billingScheduleLineDialog)
    }

    function openBillingPreparationDialog(correctionOfPreparationId) {
        billingPreparationDialog.projectId = root.selectedProjectId
        billingPreparationDialog.correctionOfPreparationId = String(correctionOfPreparationId || "")
        billingPreparationDialog.commandId = root.workspaceController
            ? root.workspaceController.newFinancialCommandId() : ""
        billingPreparationDialog.errorMessage = ""
        root._openSetupDialog(billingPreparationDialog)
    }

    function openBillingSourcePickerDialog(preparation) {
        const state = preparation ? (preparation.state || {}) : ({})
        billingSourcePickerDialog.projectId = root.selectedProjectId
        billingSourcePickerDialog.preparationId = String(preparation ? preparation.id : "")
        billingSourcePickerDialog.preparationVersion = Number(state.version || 0)
        billingSourcePickerDialog.errorMessage = ""
        root._openSetupDialog(billingSourcePickerDialog)
    }

    function openBillingDecisionDialog(action, preparation, lineId) {
        billingDecisionDialog.action = action
        billingDecisionDialog.preparation = preparation || ({})
        billingDecisionDialog.lineId = String(lineId || "")
        root._openSetupDialog(billingDecisionDialog)
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

    function openRateCardDialog(mode, rateCard) {
        rateCardEditorDialog.mode = String(mode || "create")
        rateCardEditorDialog.projectId = root.selectedProjectId
        rateCardEditorDialog.rateCard = rateCard || null
        rateCardEditorDialog.errorMessage = ""
        root._openSetupDialog(rateCardEditorDialog)
    }

    function openRateLineDialog(mode, rateCard, rateLine) {
        rateLineEditorDialog.mode = String(mode || "create")
        rateLineEditorDialog.projectId = root.selectedProjectId
        rateLineEditorDialog.rateCard = rateCard || null
        rateLineEditorDialog.rateLine = rateLine || null
        rateLineEditorDialog.errorMessage = ""
        root._openSetupDialog(rateLineEditorDialog)
    }

    function openRateLifecycleDialog(target, rateCard, rateLine) {
        rateLifecycleDialog.target = String(target || "card")
        rateLifecycleDialog.rateCard = rateCard || null
        rateLifecycleDialog.rateLine = rateLine || null
        rateLifecycleDialog.errorMessage = ""
        root._openSetupDialog(rateLifecycleDialog)
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

    // Opens the shared delete/reject/post/reverse decision dialog for the given
    // canonical ProjectCostEntry. Submit and approve need no extra fields
    // and are dispatched directly by the caller without a dialog.
    function openActualDecisionDialog(mode, entryId, rowVersion) {
        actualLifecycleDialog.mode = String(mode || "reject")
        actualLifecycleDialog.entryId = String(entryId || "")
        actualLifecycleDialog.rowVersion = Number(rowVersion || 0)
        actualLifecycleDialog.commandId = root.workspaceController
            ? root.workspaceController.newFinancialCommandId() : ""
        actualLifecycleDialog.errorMessage = ""
        root._openSetupDialog(actualLifecycleDialog)
    }

    function _editorEntryId() {
        const entry = editorDialog.entry || ({})
        const state = entry.state || ({})
        return String(state.entryId || entry.id || "")
    }

    function _closeEntryBoundActualDialogs() {
        if (editorDialog.opened && editorDialog.mode === "edit"
                && root._editorEntryId() !== root.selectedActualEntryId)
            editorDialog.close()
        if (actualLifecycleDialog.opened
                && actualLifecycleDialog.entryId !== root.selectedActualEntryId)
            actualLifecycleDialog.close()
    }

    onSelectedActualEntryIdChanged: root._closeEntryBoundActualDialogs()
    onSelectedBillingPreparationIdChanged: {
        if (billingSourcePickerDialog.opened) billingSourcePickerDialog.close()
        if (billingDecisionDialog.opened) billingDecisionDialog.close()
        if (billingPreparationDialog.opened && billingPreparationDialog.correctionOfPreparationId.length > 0)
            billingPreparationDialog.close()
    }
    onSelectedProjectIdChanged: {
        if (editorDialog.opened) editorDialog.close()
        if (actualLifecycleDialog.opened) actualLifecycleDialog.close()
        if (billingProfileDialog.opened) billingProfileDialog.close()
        if (billingScheduleLineDialog.opened) billingScheduleLineDialog.close()
        if (billingPreparationDialog.opened) billingPreparationDialog.close()
        if (billingSourcePickerDialog.opened) billingSourcePickerDialog.close()
        if (billingDecisionDialog.opened) billingDecisionDialog.close()
    }

    ManualActualEditorDialog {
        id: editorDialog

        initialProjectId: root.selectedProjectId
        initialDefaults: root.manualActualDefaults
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        focusFallbackTarget: root.focusFallbackTarget

        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            const result = editorDialog.mode === "edit"
                ? root.workspaceController.updateActualDraft(payload)
                : root.workspaceController.createManualActual(payload)
            root._handleResult(editorDialog, result)
        }
    }

    BillingProfileDialog {
        id: billingProfileDialog
        focusFallbackTarget: root.focusFallbackTarget
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            root._handleResult(
                billingProfileDialog,
                root.workspaceController.createBillingProfile(payload)
            )
        }
    }

    BillingScheduleLineDialog {
        id: billingScheduleLineDialog
        workspaceController: root.workspaceController
        focusFallbackTarget: root.focusFallbackTarget
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            root._handleResult(
                billingScheduleLineDialog,
                root.workspaceController.addBillingScheduleLine(payload)
            )
        }
    }

    BillingPreparationDialog {
        id: billingPreparationDialog
        focusFallbackTarget: root.focusFallbackTarget
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            root._handleResult(
                billingPreparationDialog,
                root.workspaceController.createBillingPreparation(payload)
            )
        }
    }

    BillingSourcePickerDialog {
        id: billingSourcePickerDialog
        focusFallbackTarget: root.focusFallbackTarget
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            root._handleResult(
                billingSourcePickerDialog,
                root.workspaceController.addBillingSource(payload)
            )
        }
    }

    BillingDecisionDialog {
        id: billingDecisionDialog
        focusFallbackTarget: root.focusFallbackTarget
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(action, preparation, lineId, note) {
            if (!root.workspaceController) return
            const state = preparation.state || ({})
            const payload = { "preparationId": String(preparation.id || ""), "version": Number(state.version || 0), "lineId": lineId }
            let result
            if (action === "approve" || action === "reject")
                result = root.workspaceController.decideBillingApproval(String(state.approvalRequestId || ""), action === "approve", note)
            else if (action === "submit") result = root.workspaceController.submitBillingPreparation(payload)
            else if (action === "cancel") result = root.workspaceController.cancelBillingPreparation(payload)
            else if (action === "remove") result = root.workspaceController.removeBillingLine(payload)
            else if (action === "request_delivery") result = root.workspaceController.requestBillingDelivery(payload)
            root._handleResult(billingDecisionDialog, result)
        }
    }

    CostCodeEditorDialog {
        id: costCodeEditorDialog

        selectedProjectId: root.selectedProjectId
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            const result = costCodeEditorDialog.mode === "edit"
                ? root.workspaceController.updateCostCode(payload)
                : root.workspaceController.createCostCode(payload)
            root._handleResult(costCodeEditorDialog, result)
        }
    }

    FinancialProfileEditorDialog {
        id: financialProfileEditorDialog
        projectId: root.selectedProjectId
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            root._handleResult(
                financialProfileEditorDialog,
                root.workspaceController.updateFinancialProfile(payload)
            )
        }
    }

    CostCodeRestrictionDialog {
        id: costCodeRestrictionDialog
        projectId: root.selectedProjectId
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            root._handleResult(
                costCodeRestrictionDialog,
                root.workspaceController.addCostCodeRestriction(payload)
            )
        }
    }

    FinancialSetupLifecycleDialog {
        id: financialSetupLifecycleDialog
        projectId: root.selectedProjectId
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onDecided: function(payload) {
            if (!root.workspaceController) return
            let result
            if (financialSetupLifecycleDialog.action.indexOf("profile_") === 0)
                result = root.workspaceController.transitionFinancialProfile(payload)
            else if (financialSetupLifecycleDialog.action === "remove_restriction")
                result = root.workspaceController.removeCostCodeRestriction(payload)
            else
                result = root.workspaceController.changeCostCodeStatus(payload)
            root._handleResult(financialSetupLifecycleDialog, result)
        }
    }

    ActualLifecycleDialog {
        id: actualLifecycleDialog

        busy: root.workspaceController ? root.workspaceController.isBusy : false
        focusFallbackTarget: root.focusFallbackTarget

        onDecided: function(mode, payload) {
            if (!root.workspaceController) return
            let result
            if (mode === "post") {
                result = root.workspaceController.postActual(payload)
            } else if (mode === "reverse") {
                result = root.workspaceController.reverseActual(payload)
            } else if (mode === "delete") {
                result = root.workspaceController.deleteActualDraft(payload)
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

    RateCardEditorDialog {
        id: rateCardEditorDialog
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            const result = rateCardEditorDialog.mode === "edit"
                ? root.workspaceController.updateRateCard(payload)
                : root.workspaceController.createRateCard(payload)
            root._handleResult(rateCardEditorDialog, result)
        }
    }

    RateLineEditorDialog {
        id: rateLineEditorDialog
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onSubmitted: function(payload) {
            if (!root.workspaceController) return
            const result = rateLineEditorDialog.mode === "edit"
                ? root.workspaceController.updateRateLine(payload)
                : root.workspaceController.addRateLine(payload)
            root._handleResult(rateLineEditorDialog, result)
        }
    }

    RateLifecycleDialog {
        id: rateLifecycleDialog
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onDecided: function(payload) {
            if (!root.workspaceController) return
            const result = rateLifecycleDialog.target === "line"
                ? root.workspaceController.deactivateRateLine(payload)
                : root.workspaceController.deactivateRateCard(payload)
            root._handleResult(rateLifecycleDialog, result)
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
