import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

AppControls.CenteredDialog {
    id: root

    property var proficiencyOptions: [
        { value: "beginner",     label: "Beginner"     },
        { value: "intermediate", label: "Intermediate" },
        { value: "advanced",     label: "Advanced"     },
        { value: "expert",       label: "Expert"       }
    ]
    property string validationMessage: ""

    signal submitted(var payload)

    modal: true
    width: 480
    height: Math.min(480, parent ? parent.height - Theme.AppTheme.marginLg * 2 : 480)
    title: "Add Skill"
    closePolicy: Popup.CloseOnEscape

    function _indexForValue(targetValue) {
        for (var i = 0; i < root.proficiencyOptions.length; i++) {
            if (String(root.proficiencyOptions[i].value || "") === String(targetValue || ""))
                return i
        }
        return 1
    }

    function _reset() {
        skillCodeField.text = ""
        skillNameField.text = ""
        proficiencyCombo.currentIndex = 1
        notesField.text = ""
        root.validationMessage = ""
    }

    function _submit() {
        if (skillCodeField.text.trim().length === 0) {
            root.validationMessage = "Skill code is required."
            return
        }
        root.validationMessage = ""
        root.submitted({
            "skillCode": skillCodeField.text.trim(),
            "skillName": skillNameField.text.trim(),
            "proficiency": String((root.proficiencyOptions[proficiencyCombo.currentIndex] || { value: "intermediate" }).value),
            "notes": notesField.text.trim()
        })
    }

    onOpened: root._reset()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        AppControls.Label {
            Layout.fillWidth: true
            text: "Record a skill or competency for this resource."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        AppControls.Label {
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
            columns: 2
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            AppControls.Label { text: "Skill Code *"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
            AppControls.TextField {
                id: skillCodeField
                Layout.fillWidth: true
                placeholderText: "e.g. PY-DEV"
                Keys.onReturnPressed: root._submit()
            }

            AppControls.Label { text: "Skill Name"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
            AppControls.TextField {
                id: skillNameField
                Layout.fillWidth: true
                placeholderText: "e.g. Python Development"
                Keys.onReturnPressed: root._submit()
            }

            AppControls.Label { text: "Proficiency"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
            AppControls.ComboBox {
                id: proficiencyCombo
                Layout.fillWidth: true
                model: root.proficiencyOptions
                textRole: "label"
            }

            AppControls.Label { text: "Notes"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
            AppControls.TextField {
                id: notesField
                Layout.fillWidth: true
                placeholderText: "Optional notes"
            }
        }
    }

    footer: AppControls.DialogActionFooter {
        Item { Layout.fillWidth: true }
        AppControls.SecondaryButton {
            text: "Cancel"
            iconName: "close"
            onClicked: root.close()
        }
        AppControls.PrimaryButton {
            text: "Add Skill"
            iconName: "add"
            onClicked: root._submit()
        }
    }
}
