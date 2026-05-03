import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
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
    height: Math.min(760, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 760)
    title: root.modeTitle
    closePolicy: Popup.CloseOnEscape

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

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        border.color: Theme.AppTheme.border
    }

    contentItem: Flickable {
        id: dialogFlickable

        contentWidth: width
        contentHeight: formLayout.implicitHeight
        clip: true

        ColumnLayout {
            id: formLayout

            width: dialogFlickable.width
            spacing: Theme.AppTheme.spacingMd

            Label {
                Layout.fillWidth: true
                text: root.editingExistingCost
                    ? "Adjust the commercial line, amounts, or finance coding for this cost item."
                    : "Add a financial control line for the selected project and optionally link it to a task."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                visible: root.validationMessage.length > 0
                text: root.validationMessage
                color: "#8B1E1E"
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 560 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label {
                    text: "Description"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: descriptionField

                    Layout.fillWidth: true
                    placeholderText: "Electrical material package"
                }

                Label {
                    text: "Task"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                ComboBox {
                    id: taskCombo

                    Layout.fillWidth: true
                    model: root.taskOptions
                    textRole: "label"
                    enabled: !root.editingExistingCost
                }

                Label {
                    text: "Cost type"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                ComboBox {
                    id: costTypeCombo

                    Layout.fillWidth: true
                    model: root.costTypeOptions
                    textRole: "label"
                }

                Label {
                    text: "Planned"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: plannedAmountField

                    Layout.fillWidth: true
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    placeholderText: "0.00"
                }

                Label {
                    text: "Committed"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: committedAmountField

                    Layout.fillWidth: true
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    placeholderText: "0.00"
                }

                Label {
                    text: "Actual"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: actualAmountField

                    Layout.fillWidth: true
                    inputMethodHints: Qt.ImhFormattedNumbersOnly
                    placeholderText: "0.00"
                }

                Label {
                    text: "Currency"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: currencyField

                    Layout.fillWidth: true
                    placeholderText: "EUR"
                }

                Label {
                    text: "Incurred date"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }

                TextField {
                    id: incurredDateField

                    Layout.fillWidth: true
                    placeholderText: "YYYY-MM-DD"
                }
            }
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item {
            Layout.fillWidth: true
        }

        Button {
            text: "Cancel"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            text: root.editingExistingCost ? "Save Changes" : "Create Cost Item"
            onClicked: root.submitDialog()
        }
    }
}
