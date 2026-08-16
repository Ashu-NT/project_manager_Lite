import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var taskOptions: []
    property var actualOptions: ({ "currencyCode": "", "costCodes": [], "entryKinds": [] })
    property string selectedProjectId: ""
    property string commandId: ""

    signal submitted(var payload)

    modal: true
    width: 620
    closePolicy: Popup.CloseOnEscape
    title: "Create Manual Actual"
    subtitle: "Create a governed draft actual or adjustment. Submission, approval, and posting remain separate actions."
    primaryText: "Create Draft"
    primaryIcon: "add"

    onAccepted: root.submitDialog()
    onRejected: root.close()

    function selectedValue(options, index, fallback) {
        const item = (options || [])[index]
        return item ? String(item.value || fallback || "") : String(fallback || "")
    }

    function populateDefaults() {
        descriptionField.text = ""
        amountField.text = ""
        transactionDateField.text = Qt.formatDate(new Date(), "yyyy-MM-dd")
        entryKindCombo.currentIndex = 0
        costCodeCombo.currentIndex = 0
        taskCombo.currentIndex = 0
        root.errorMessage = ""
    }

    function buildPayload() {
        return {
            "projectId": root.selectedProjectId,
            "commandId": root.commandId,
            "description": descriptionField.text,
            "entryKind": root.selectedValue(root.actualOptions.entryKinds, entryKindCombo.currentIndex, "actual"),
            "amount": amountField.text,
            "currency": String(root.actualOptions.currencyCode || ""),
            "transactionDate": transactionDateField.text,
            "costCodeId": root.selectedValue(root.actualOptions.costCodes, costCodeCombo.currentIndex, ""),
            "taskId": root.selectedValue(root.taskOptions, taskCombo.currentIndex, "")
        }
    }

    function submitDialog() {
        if (descriptionField.text.trim().length === 0) {
            root.errorMessage = "Description is required."
            return
        }
        if (amountField.text.trim().length === 0) {
            root.errorMessage = "Amount is required."
            return
        }
        if ((root.actualOptions.costCodes || []).length === 0) {
            root.errorMessage = "Configure an active project cost code before creating an actual."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateDefaults()

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 560 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

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
            label: "Entry type"
            required: true
            AppControls.ComboBox {
                id: entryKindCombo
                Layout.fillWidth: true
                model: root.actualOptions.entryKinds || []
                textRole: "label"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Task"
            AppControls.ComboBox {
                id: taskCombo
                Layout.fillWidth: true
                model: root.taskOptions
                textRole: "label"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Cost code"
            required: true
            AppControls.ComboBox {
                id: costCodeCombo
                Layout.fillWidth: true
                model: root.actualOptions.costCodes || []
                textRole: "label"
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
                text: String(root.actualOptions.currencyCode || "")
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
            }
        }
    }
}
