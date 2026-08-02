import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property var parentTaskOptions: []
    property var taskData: ({})
    readonly property var taskState: root.taskData && root.taskData.state
        ? root.taskData.state
        : (root.taskData || {})
    readonly property var validParentOptions: (root.parentTaskOptions || []).filter(function(option) {
        const disabledFor = option.disabledForTaskIds || []
        return disabledFor.indexOf(String(root.taskState.taskId || "")) < 0
    })

    signal submitted(var payload)

    title: "Move / Recode WBS"
    subtitle: root.taskData && root.taskData.title
        ? "Change the WBS parent, code, or sibling position for " + root.taskData.title + "."
        : "Change the selected task's position in the work breakdown structure."
    primaryText: "Apply WBS Change"
    primaryIcon: "save"
    width: 480

    onOpened: root.populateFromTask()
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function indexForValue(options, targetValue) {
        for (let index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromTask() {
        parentTaskCombo.currentIndex = root.indexForValue(
            root.validParentOptions,
            root.taskState.parentTaskId || ""
        )
        wbsCodeField.text = String(root.taskState.wbsCode || "")
        positionField.text = String(Number(root.taskState.sortOrder || 0) + 1)
        root.errorMessage = ""
    }

    function submitDialog() {
        const position = Number(positionField.text)
        if (!Number.isInteger(position) || position < 1) {
            root.errorMessage = "Position must be a whole number greater than zero."
            return
        }
        const parentOption = root.validParentOptions[parentTaskCombo.currentIndex] || { "value": "" }
        root.errorMessage = ""
        root.submitted({
            "taskId": String(root.taskState.taskId || ""),
            "parentTaskId": String(parentOption.value || ""),
            "wbsCode": wbsCodeField.text,
            "sortOrder": position - 1,
            "expectedVersion": root.taskState.version
        })
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "WBS parent"
        AppControls.ComboBox {
            id: parentTaskCombo
            Layout.fillWidth: true
            model: root.validParentOptions
            textRole: "label"
            onActivated: {
                const selected = root.validParentOptions[currentIndex] || { "value": "" }
                if (String(selected.value || "") !== String(root.taskState.parentTaskId || "")) {
                    wbsCodeField.text = ""
                }
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "WBS code"
        AppControls.TextField {
            id: wbsCodeField
            Layout.fillWidth: true
            placeholderText: "Auto-number when moving to a new parent"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Sibling position"
        AppControls.TextField {
            id: positionField
            Layout.fillWidth: true
            placeholderText: "1"
        }
    }
}
