import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
AppControls.CenteredDialog {
    id: dialog
    title: "Sign in"
    modal: true
    standardButtons: Dialog.Ok | Dialog.Cancel

    ColumnLayout {
        spacing: 10

        AppControls.TextField {
            id: username
            Layout.preferredWidth: 320
            placeholderText: "Username"
        }

        AppControls.TextField {
            id: password
            Layout.preferredWidth: 320
            placeholderText: "Password"
            echoMode: TextInput.Password
        }
    }
}

