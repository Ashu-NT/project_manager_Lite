pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string projectId: ""
    property string projectLabel: ""
    property var workspaceController: null
    signal submitted(var payload)

    ListModel { id: manualModel }
    ListModel { id: riskModel }

    function _amount(value, label, field) {
        const normalized = String(value || "").trim().replace(",", ".")
        if (!/^\d+(?:\.\d+)?$/.test(normalized)) {
            root.errorMessage = label + " must be a non-negative decimal value."
            field.forceActiveFocus()
            return ""
        }
        return normalized
    }

    function addManualEstimate() {
        if (!manualCostCode.selectedId || !manualDescription.text.trim()) {
            root.errorMessage = "Manual ETC requires a Cost Code and description."
            return
        }
        const amount = root._amount(manualAmount.text, "Manual ETC amount", manualAmount)
        if (!amount) return
        manualModel.append({
            "costCodeId": manualCostCode.selectedId,
            "costCodeLabel": manualCostCode.selectedLabel,
            "taskId": manualTask.selectedId,
            "description": manualDescription.text.trim(),
            "amount": amount,
            "periodStart": "",
            "periodEnd": ""
        })
        manualCostCode.clearSelection()
        manualTask.clearSelection()
        manualDescription.clear()
        manualAmount.clear()
        root.errorMessage = ""
    }

    function addRiskContingency() {
        if (!riskSelector.selectedId || !riskCostCode.selectedId) {
            root.errorMessage = "Risk contingency requires an eligible Risk and Cost Code."
            return
        }
        const amount = root._amount(riskAmount.text, "Contingency amount", riskAmount)
        if (!amount) return
        riskModel.append({
            "riskId": riskSelector.selectedId,
            "riskLabel": riskSelector.selectedLabel,
            "costCodeId": riskCostCode.selectedId,
            "taskId": riskTask.selectedId,
            "description": riskDescription.text.trim(),
            "amount": amount,
            "periodStart": "",
            "periodEnd": ""
        })
        riskSelector.clearSelection()
        riskCostCode.clearSelection()
        riskTask.clearSelection()
        riskDescription.clear()
        riskAmount.clear()
        root.errorMessage = ""
    }

    function _rows(model) {
        const result = []
        for (let index = 0; index < model.count; index += 1)
            result.push(model.get(index))
        return result
    }

    width: 620
    title: "Generate Forecast"
    subtitle: "Create a governed draft from Planned Cost, posted Actuals, and open Commitments. Calculations and source evidence remain server authoritative."
    primaryText: "Generate Forecast"
    primaryIcon: "add"

    function submitDialog() {
        if (!root.projectId) {
            root.errorMessage = "Select a project before generating a Forecast."
            return
        }
        if (!nameField.text.trim()) {
            root.errorMessage = "Forecast name is required."
            nameField.forceActiveFocus()
            return
        }
        if (!/^\d{4}-\d{2}-\d{2}$/.test(asOfField.text.trim())) {
            root.errorMessage = "As-of date must use YYYY-MM-DD."
            asOfField.forceActiveFocus()
            return
        }
        root.errorMessage = ""
        root.submitted({
            "projectId": root.projectId,
            "name": nameField.text.trim(),
            "asOfDate": asOfField.text.trim(),
            "notes": notesField.text.trim(),
            "manualEstimates": root._rows(manualModel),
            "riskContingencies": root._rows(riskModel)
        })
    }

    onOpened: {
        nameField.text = "Forecast " + Qt.formatDate(new Date(), "yyyy-MM-dd")
        asOfField.text = Qt.formatDate(new Date(), "yyyy-MM-dd")
        notesField.text = ""
        manualModel.clear()
        riskModel.clear()
        root.errorMessage = ""
        nameField.forceActiveFocus()
    }
    onRejected: root.close()

    GridLayout {
        id: formGrid
        Layout.fillWidth: true
        columns: width >= 520 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            text: "Project: " + (root.projectLabel || root.projectId)
                + " | Currency: selected project financial currency (server authoritative)"
            wrapMode: Text.WordWrap
            color: Theme.AppTheme.textSecondary
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            Layout.columnSpan: parent.columns
            label: "Forecast name"
            required: true
            AppControls.TextField {
                id: nameField
                Layout.fillWidth: true
                placeholderText: "Monthly delivery forecast"
            }
        }

        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            Layout.columnSpan: parent.columns
            label: "Manual ETC Overrides"
        }
        AppControls.Label {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            text: "Each amount replaces remaining planned ETC for the selected Cost Code or Cost Code + Task scope."
            wrapMode: Text.WordWrap
            color: Theme.AppTheme.textSecondary
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Cost Code"
            AppControls.SearchablePagedSelector {
                id: manualCostCode
                Layout.fillWidth: true
                searchPlaceholder: "Search eligible Cost Codes..."
                contextKey: root.projectId + "|" + asOfField.text
                onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                    const result = root.workspaceController
                        ? root.workspaceController.searchForecastCostCodes(
                            root.projectId, query, page, pageSize, asOfField.text
                        ) : ({ "ok": false, "message": "Finance controller is unavailable." })
                    manualCostCode.acceptResult(result, generation, lookupContext)
                }
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Task (optional)"
            AppControls.SearchablePagedSelector {
                id: manualTask
                Layout.fillWidth: true
                allowEmpty: true
                emptyLabel: "Cost Code level"
                searchPlaceholder: "Search project Tasks..."
                contextKey: root.projectId
                onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                    const result = root.workspaceController
                        ? root.workspaceController.searchForecastTasks(
                            root.projectId, query, page, pageSize
                        ) : ({ "ok": false, "message": "Finance controller is unavailable." })
                    manualTask.acceptResult(result, generation, lookupContext)
                }
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Description"
            AppControls.TextField { id: manualDescription; Layout.fillWidth: true }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Replacement amount"
            AppControls.TextField {
                id: manualAmount
                Layout.fillWidth: true
                placeholderText: "0.00"
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }
        }
        AppControls.SecondaryButton {
            Layout.columnSpan: parent.columns
            text: "Add Manual ETC Override"
            iconName: "add"
            onClicked: root.addManualEstimate()
        }
        Repeater {
            model: manualModel
            delegate: RowLayout {
                id: manualRow
                required property int index
                required property string costCodeLabel
                required property string description
                required property string amount
                Layout.fillWidth: true
                Layout.columnSpan: formGrid.columns
                AppControls.Label {
                    Layout.fillWidth: true
                    text: manualRow.costCodeLabel + " | " + manualRow.description
                        + " | " + manualRow.amount
                    elide: Text.ElideRight
                }
                AppControls.SecondaryButton {
                    text: "Remove"
                    iconName: "delete"
                    danger: true
                    onClicked: manualModel.remove(manualRow.index)
                }
            }
        }

        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            Layout.columnSpan: parent.columns
            label: "Risk Contingency"
        }
        AppControls.Label {
            Layout.fillWidth: true
            Layout.columnSpan: formGrid.columns
            text: "Risk identity and eligibility come from the project Risk Register; Finance owns only this monetary contingency."
            wrapMode: Text.WordWrap
            color: Theme.AppTheme.textSecondary
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Eligible Risk"
            AppControls.SearchablePagedSelector {
                id: riskSelector
                Layout.fillWidth: true
                searchPlaceholder: "Search active project Risks..."
                contextKey: root.projectId
                onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                    const result = root.workspaceController
                        ? root.workspaceController.searchForecastRisks(
                            root.projectId, query, page, pageSize
                        ) : ({ "ok": false, "message": "Finance controller is unavailable." })
                    riskSelector.acceptResult(result, generation, lookupContext)
                }
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Cost Code"
            AppControls.SearchablePagedSelector {
                id: riskCostCode
                Layout.fillWidth: true
                searchPlaceholder: "Search eligible Cost Codes..."
                contextKey: root.projectId + "|" + asOfField.text
                onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                    const result = root.workspaceController
                        ? root.workspaceController.searchForecastCostCodes(
                            root.projectId, query, page, pageSize, asOfField.text
                        ) : ({ "ok": false, "message": "Finance controller is unavailable." })
                    riskCostCode.acceptResult(result, generation, lookupContext)
                }
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Task (optional)"
            AppControls.SearchablePagedSelector {
                id: riskTask
                Layout.fillWidth: true
                allowEmpty: true
                emptyLabel: "Not task-specific"
                searchPlaceholder: "Search project Tasks..."
                contextKey: root.projectId
                onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                    const result = root.workspaceController
                        ? root.workspaceController.searchForecastTasks(
                            root.projectId, query, page, pageSize
                        ) : ({ "ok": false, "message": "Finance controller is unavailable." })
                    riskTask.acceptResult(result, generation, lookupContext)
                }
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Contingency amount"
            AppControls.TextField {
                id: riskAmount
                Layout.fillWidth: true
                placeholderText: "0.00"
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            Layout.columnSpan: parent.columns
            label: "Contingency note"
            AppControls.TextField { id: riskDescription; Layout.fillWidth: true }
        }
        AppControls.SecondaryButton {
            Layout.columnSpan: parent.columns
            text: "Add Risk Contingency"
            iconName: "add"
            onClicked: root.addRiskContingency()
        }
        Repeater {
            model: riskModel
            delegate: RowLayout {
                id: riskRow
                required property int index
                required property string riskLabel
                required property string amount
                Layout.fillWidth: true
                Layout.columnSpan: formGrid.columns
                AppControls.Label {
                    Layout.fillWidth: true
                    text: riskRow.riskLabel + " | " + riskRow.amount
                    elide: Text.ElideRight
                }
                AppControls.SecondaryButton {
                    text: "Remove"
                    iconName: "delete"
                    danger: true
                    onClicked: riskModel.remove(riskRow.index)
                }
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "As-of date"
            required: true
            AppControls.DateField {
                id: asOfField
                Layout.fillWidth: true
            }
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            Layout.columnSpan: parent.columns
            label: "Generation note"
            AppControls.TextArea {
                id: notesField
                Layout.fillWidth: true
                Layout.preferredHeight: 88
                wrapMode: TextEdit.WordWrap
                placeholderText: "Optional context retained with this revision"
            }
        }
    }
}
