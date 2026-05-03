import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create Register Entry"
    property var projectOptions: []
    property var typeOptions: []
    property var statusOptions: []
    property var severityOptions: []
    property var entryData: ({})
    property bool typeFieldVisible: true
    property string fixedTypeValue: "RISK"
    property string validationMessage: ""
    readonly property var editableProjectOptions: (root.projectOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })
    readonly property var editableTypeOptions: (root.typeOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })
    readonly property var editableStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })
    readonly property var editableSeverityOptions: (root.severityOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(var payload)

    modal: true
    width: 680
    height: Math.min(820, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 820)
    title: root.modeTitle
    closePolicy: Popup.CloseOnEscape

    function indexForValue(options, targetValue) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromEntry() {
        var state = root.entryData && root.entryData.state ? root.entryData.state : (root.entryData || {})
        projectCombo.currentIndex = root.indexForValue(root.editableProjectOptions, state.projectId || "")
        typeCombo.currentIndex = root.indexForValue(root.editableTypeOptions, state.type || root.fixedTypeValue)
        statusCombo.currentIndex = root.indexForValue(root.editableStatusOptions, state.status || "OPEN")
        severityCombo.currentIndex = root.indexForValue(root.editableSeverityOptions, state.severity || "MEDIUM")
        titleField.text = String(state.title || "")
        ownerField.text = String(state.ownerName || "")
        dueDateField.text = String(state.dueDate || "")
        descriptionField.text = String(state.description || "")
        impactField.text = String(state.impactSummary || "")
        responseField.text = String(state.responsePlan || "")
        root.validationMessage = ""
    }

    function buildPayload() {
        var typeOption = root.editableTypeOptions[typeCombo.currentIndex] || { "value": root.fixedTypeValue }
        var statusOption = root.editableStatusOptions[statusCombo.currentIndex] || { "value": "OPEN" }
        var severityOption = root.editableSeverityOptions[severityCombo.currentIndex] || { "value": "MEDIUM" }
        var projectOption = root.editableProjectOptions[projectCombo.currentIndex] || { "value": "" }
        return {
            "projectId": String(projectOption.value || ""),
            "entryType": root.typeFieldVisible ? String(typeOption.value || root.fixedTypeValue) : root.fixedTypeValue,
            "title": titleField.text,
            "status": String(statusOption.value || "OPEN"),
            "severity": String(severityOption.value || "MEDIUM"),
            "ownerName": ownerField.text,
            "dueDate": dueDateField.text,
            "description": descriptionField.text,
            "impactSummary": impactField.text,
            "responsePlan": responseField.text
        }
    }

    function submitDialog() {
        if (root.editableProjectOptions.length === 0) {
            root.validationMessage = "Create a project before adding a register entry."
            return
        }
        if (String((root.editableProjectOptions[projectCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a project before saving."
            return
        }
        if (titleField.text.trim().length === 0) {
            root.validationMessage = "Register title is required."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromEntry()

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
                text: root.typeFieldVisible
                    ? "Capture the project, entry type, severity, status, and response context for this governance item."
                    : "Capture the project, severity, owner, and response context for this risk item."
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
                columns: root.width > 600 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label { text: "Project"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                ComboBox {
                    id: projectCombo
                    Layout.fillWidth: true
                    model: root.editableProjectOptions
                    textRole: "label"
                }

                Label {
                    visible: root.typeFieldVisible
                    text: "Entry type"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                }
                ComboBox {
                    id: typeCombo
                    visible: root.typeFieldVisible
                    Layout.fillWidth: true
                    model: root.editableTypeOptions
                    textRole: "label"
                }

                Label { text: "Title"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                TextField {
                    id: titleField
                    Layout.fillWidth: true
                    placeholderText: root.typeFieldVisible ? "Critical supplier dependency" : "Late switchgear delivery"
                }

                Label { text: "Severity"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                ComboBox {
                    id: severityCombo
                    Layout.fillWidth: true
                    model: root.editableSeverityOptions
                    textRole: "label"
                }

                Label { text: "Status"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                ComboBox {
                    id: statusCombo
                    Layout.fillWidth: true
                    model: root.editableStatusOptions
                    textRole: "label"
                }

                Label { text: "Owner"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                TextField {
                    id: ownerField
                    Layout.fillWidth: true
                    placeholderText: "PM Lead"
                }

                Label { text: "Due date"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
                TextField {
                    id: dueDateField
                    Layout.fillWidth: true
                    placeholderText: "YYYY-MM-DD"
                }
            }

            Label {
                Layout.fillWidth: true
                text: "Description"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            TextArea {
                id: descriptionField
                Layout.fillWidth: true
                Layout.preferredHeight: 120
                placeholderText: "Describe the trigger, scope, or context behind this entry."
                wrapMode: TextEdit.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "Impact summary"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            TextArea {
                id: impactField
                Layout.fillWidth: true
                Layout.preferredHeight: 110
                placeholderText: "Summarize delivery, cost, or schedule impact."
                wrapMode: TextEdit.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: "Response plan"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            TextArea {
                id: responseField
                Layout.fillWidth: true
                Layout.preferredHeight: 130
                placeholderText: "Capture mitigation, action owner, and next review step."
                wrapMode: TextEdit.WordWrap
            }
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item { Layout.fillWidth: true }

        Button {
            text: "Cancel"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            text: root.modeTitle.indexOf("Create") === 0 ? "Create Entry" : "Save Changes"
            onClicked: root.submitDialog()
        }
    }
}
