import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

// System Access relationship dialog -- links an Employee to an existing
// User account (link_employee_user_account). Never creates a User account
// here and never exposes password/role/MFA/session administration; those
// remain Identity & Access responsibilities. Options are pre-narrowed by
// the presenter (build_linkable_user_options) to valid, unlinked, human
// tenant accounts -- backend validation remains the source of truth.
AppWidgets.EntityDialog {
    id: root

    property string employeeId: ""
    property string employeeLabel: ""
    property var userOptions: []

    signal saveRequested(var payload)

    modal: true
    focus: true
    width: Theme.AppTheme.dialogWidthStandard
    title: "Link User Account"
    primaryText: "Link"
    primaryIcon: "add"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function openForLink(employeeId, employeeLabel, userOptions) {
        root.employeeId = employeeId || ""
        root.employeeLabel = employeeLabel || ""
        root.userOptions = userOptions || []
        _reloadOptionModel()
        open()
    }

    function _reloadOptionModel() {
        userModel.clear()
        for (let index = 0; index < root.userOptions.length; index += 1) {
            const option = root.userOptions[index]
            userModel.append({ label: option.label || "", value: option.value || "" })
        }
        userCombo.currentIndex = userModel.count > 0 ? 0 : -1
    }

    function _currentValue() {
        if (userCombo.currentIndex < 0 || userCombo.currentIndex >= userModel.count) {
            return ""
        }
        return userModel.get(userCombo.currentIndex).value || ""
    }

    function submitDialog() {
        const userId = root._currentValue()
        if (userId.length === 0) {
            root.errorMessage = "Select a user account to link."
            return
        }
        root.errorMessage = ""
        root.saveRequested({ employeeId: root.employeeId, userId: userId })
    }

    ListModel { id: userModel }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Employee"

        AppControls.TextField {
            Layout.fillWidth: true
            readOnly: true
            text: root.employeeLabel
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "User Account"
        required: true

        AppControls.ComboBox {
            id: userCombo
            Layout.fillWidth: true
            model: userModel
            textRole: "label"
        }
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        tone: "warning"
        message: "No eligible user accounts are available to link."
        visible: root.userOptions.length === 0
    }
}
