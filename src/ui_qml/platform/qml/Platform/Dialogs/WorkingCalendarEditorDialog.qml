import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property var draft: ({})
    property var workingDayDraft: []

    signal saveRequested(var payload)

    modal: true
    focus: true
    width: 620
    title: "Edit Working Calendar"
    primaryText: "Save"
    primaryIcon: "save"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    readonly property var formData: ({
        calendarId: root.draft.calendarId || root.draft.id || "default",
        workingDays: root.workingDayDraft,
        hoursPerDay: hoursField.text.trim()
    })

    function openForEdit(draftData) {
        root.draft = draftData || ({})
        root.workingDayDraft = []
        const days = root.draft.workingDays || []
        for (let i = 0; i < days.length; i++) {
            if (days[i].checked === true)
                root.workingDayDraft.push(days[i].index)
        }
        hoursField.text = String(root.draft.hoursPerDayLabel || root.draft.hoursPerDay || "8")
        open()
    }

    function submitDialog() {
        if ((root.workingDayDraft || []).length === 0) {
            root.errorMessage = "Select at least one working day."
            return
        }
        if (hoursField.text.trim().length === 0) {
            root.errorMessage = "Hours per day is required."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root.formData)
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Calendar"

        AppControls.TextField {
            Layout.fillWidth: true
            readOnly: true
            text: String(root.draft.name || "Default Calendar")
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Working Week"
        required: true

        Flow {
            width: parent ? parent.width : 0
            spacing: Theme.AppTheme.spacingSm

            Repeater {
                model: root.draft.workingDays || []

                delegate: AppControls.CheckBox {
                    required property var modelData
                    text: String(modelData.label || "")
                    checked: (root.workingDayDraft || []).indexOf(modelData.index) >= 0
                    onToggled: {
                        const next = (root.workingDayDraft || []).slice()
                        const idx = next.indexOf(modelData.index)
                        if (checked && idx < 0)
                            next.push(modelData.index)
                        else if (!checked && idx >= 0)
                            next.splice(idx, 1)
                        root.workingDayDraft = next
                    }
                }
            }
        }
    }

    AppWidgets.FormField {
        Layout.preferredWidth: 160
        label: "Hours / Day"
        required: true

        AppControls.TextField {
            id: hoursField
            Layout.fillWidth: true
            placeholderText: "e.g. 8"
        }
    }
}
