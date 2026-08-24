import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Add Skill"
    property var skillData: ({})

    property var proficiencyOptions: [
        { value: "beginner",     label: "Beginner"     },
        { value: "intermediate", label: "Intermediate" },
        { value: "advanced",     label: "Advanced"     },
        { value: "expert",       label: "Expert"       }
    ]

    signal submitted(var payload)

    title: root.modeTitle
    subtitle: root.modeTitle === "Add Skill"
        ? "Record a skill or competency for this resource."
        : "Update this capability using its current version."
    primaryText: root.modeTitle === "Add Skill" ? "Add Skill" : "Save Changes"
    primaryIcon: root.modeTitle === "Add Skill" ? "add" : "save"
    width: 560

    onOpened:   root._reset()
    onAccepted: root._submit()
    onRejected: root.close()

    function _indexForValue(targetValue) {
        for (var i = 0; i < root.proficiencyOptions.length; i++) {
            if (String(root.proficiencyOptions[i].value || "") === String(targetValue || ""))
                return i
        }
        return 1
    }

    function _reset() {
        const state = root.skillData || {}
        skillCodeField.text = String(state.skillCode || "")
        skillNameField.text = String(state.skillName || "")
        proficiencyCombo.currentIndex = root._indexForValue(state.proficiency || "intermediate")
        notesField.text = String(state.notes || "")
        root.errorMessage = ""
    }

    function _submit() {
        if (skillCodeField.text.trim().length === 0) {
            root.errorMessage = "Skill code is required."
            return
        }
        root.errorMessage = ""
        root.submitted({
            "skillId": String((root.skillData || {}).id || ""),
            "expectedVersion": Number((root.skillData || {}).version || 0),
            "skillCode": skillCodeField.text.trim(),
            "skillName": skillNameField.text.trim(),
            "proficiency": String((root.proficiencyOptions[proficiencyCombo.currentIndex] || { value: "intermediate" }).value),
            "notes": notesField.text.trim()
        })
    }

    // ── Form content ──────────────────────────────────────────────────────────

    GridLayout {
        id: skillFormGrid
        Layout.fillWidth: true
        columns: root.width > 460 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Skill Code"
            required: true
            AppControls.TextField { id: skillCodeField; Layout.fillWidth: true; placeholderText: "e.g. PY-DEV"; Keys.onReturnPressed: root._submit() }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            required: true
            label: "Skill Name"
            AppControls.TextField { id: skillNameField; Layout.fillWidth: true; placeholderText: "e.g. Python Development"; Keys.onReturnPressed: root._submit() }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Proficiency"
            AppControls.ComboBox { id: proficiencyCombo; Layout.fillWidth: true; model: root.proficiencyOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Notes"
            AppControls.TextField { id: notesField; Layout.fillWidth: true; placeholderText: "Optional notes" }
        }
    }
}
