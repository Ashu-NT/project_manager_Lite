pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    signal saveRequested(var payload)

    modal: true
    focus: true
    width: Theme.AppTheme.dialogWidthStandard
    title: "New Tenant"
    primaryText: "Create"
    primaryIcon: "add"
    onOpened: {
        root.errorMessage = ""
        tenantCodeField.text = ""
        displayNameField.text = ""
    }
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function submitDialog() {
        if (tenantCodeField.text.trim().length === 0) {
            root.errorMessage = "Tenant code is required."
            return
        }
        if (displayNameField.text.trim().length === 0) {
            root.errorMessage = "Display name is required."
            return
        }
        root.errorMessage = ""
        root.saveRequested({
            tenantCode: tenantCodeField.text.trim(),
            displayName: displayNameField.text.trim()
        })
    }

    function openForCreate() {
        open()
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Tenant Code"
        required: true

        AppControls.TextField {
            id: tenantCodeField
            Layout.fillWidth: true
            placeholderText: "e.g. ACME"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Display Name"
        required: true

        AppControls.TextField {
            id: displayNameField
            Layout.fillWidth: true
            placeholderText: "e.g. Acme Industrial Group"
        }
    }
}
