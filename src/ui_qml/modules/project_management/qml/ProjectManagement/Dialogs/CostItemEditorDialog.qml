import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Cost Item"
    property var taskOptions: []
    property var costTypeOptions: []
    property var costData: ({})
    property string validationMessage: ""
    readonly property bool editingExistingCost: {
        var state = root.costData && root.costData.state ? root.costData.state : (root.costData || {})
        return String(state.costId || "").length > 0
    }

    signal submitted(var payload)

    modal: true
    width: 620
    closePolicy: Popup.CloseOnEscape

    title: root.modeTitle
    subtitle: root.editingExistingCost
        ? "Adjust the commercial line, amounts, or finance coding for this cost item."
        : "Add a financial control line for the selected project and optionally link it to a task."
    errorMessage: root.validationMessage
    primaryText: root.editingExistingCost ? "Save Changes" : "Create Cost Item"
    primaryIcon: root.editingExistingCost ? "save" : "add"

    onAccepted: root.submitDialog()
    onRejected: root.close()

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromCost() {
        var state = root.costData && root.costData.state ? root.costData.state : (root.costData || {})
        descriptionField.text = String(state.description || "")
        plannedAmountField.text = String(state.plannedAmount || "0.00")
        committedAmountField.text = String(state.committedAmount || "0.00")
        actualAmountField.text = String(state.actualAmount || "0.00")
        currencyField.text = String(state.currency || "")
        incurredDateField.text = String(state.incurredDate || "")
        costTypeCombo.currentIndex = root.indexForValue(root.costTypeOptions, state.costType || "OVERHEAD")
        taskCombo.currentIndex = root.indexForValue(root.taskOptions, state.taskId || "")
        root.validationMessage = ""
    }

    function buildPayload() {
        return {
            "description": descriptionField.text,
            "plannedAmount": plannedAmountField.text,
            "committedAmount": committedAmountField.text,
            "actualAmount": actualAmountField.text,
            "costType": String((root.costTypeOptions[costTypeCombo.currentIndex] || { "value": "OVERHEAD" }).value || "OVERHEAD"),
            "taskId": String((root.taskOptions[taskCombo.currentIndex] || { "value": "" }).value || ""),
            "currency": currencyField.text,
            "incurredDate": incurredDateField.text
        }
    }

    function submitDialog() {
        if (descriptionField.text.trim().length === 0) {
            root.validationMessage = "Description is required."
            return
        }
        if (plannedAmountField.text.trim().length === 0) {
            root.validationMessage = "Planned amount is required."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromCost()

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 560 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label {
            text: "Description"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        AppControls.TextField {
            id: descriptionField

            Layout.fillWidth: true
            placeholderText: "Electrical material package"
        }

        AppControls.Label {
            text: "Task"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        AppControls.ComboBox {
            id: taskCombo

            Layout.fillWidth: true
            model: root.taskOptions
            textRole: "label"
            enabled: !root.editingExistingCost
        }

        AppControls.Label {
            text: "Cost type"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        AppControls.ComboBox {
            id: costTypeCombo

            Layout.fillWidth: true
            model: root.costTypeOptions
            textRole: "label"
        }

        AppControls.Label {
            text: "Planned"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        AppControls.TextField {
            id: plannedAmountField

            Layout.fillWidth: true
            inputMethodHints: Qt.ImhFormattedNumbersOnly
            placeholderText: "0.00"
        }

        AppControls.Label {
            text: "Committed"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        AppControls.TextField {
            id: committedAmountField

            Layout.fillWidth: true
            inputMethodHints: Qt.ImhFormattedNumbersOnly
            placeholderText: "0.00"
        }

        AppControls.Label {
            text: "Actual"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        AppControls.TextField {
            id: actualAmountField

            Layout.fillWidth: true
            inputMethodHints: Qt.ImhFormattedNumbersOnly
            placeholderText: "0.00"
        }

        AppControls.Label {
            text: "Currency"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        AppControls.TextField {
            id: currencyField

            Layout.fillWidth: true
            placeholderText: "EUR"
        }

        AppControls.Label {
            text: "Incurred date"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        AppControls.DateField {
            id: incurredDateField

            Layout.fillWidth: true
            placeholderText: "YYYY-MM-DD"
        }
    }
}
