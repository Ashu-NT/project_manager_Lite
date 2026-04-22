import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    title: "Sign in"
    modal: true
    standardButtons: Dialog.Ok | Dialog.Cancel

    ColumnLayout {
        spacing: 10

        TextField {
            id: username
            Layout.preferredWidth: 320
            placeholderText: "Username"
        }

        TextField {
            id: password
            Layout.preferredWidth: 320
            placeholderText: "Password"
            echoMode: TextInput.Password
        }
    }
}
