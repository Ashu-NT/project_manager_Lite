import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: dialog
    title:       "Sign in"
    primaryText: "Sign in"
    primaryIcon: "user"
    width: 360

    AppControls.TextField {
        id: username
        Layout.fillWidth: true
        placeholderText: "Username"
    }

    AppControls.TextField {
        id: password
        Layout.fillWidth: true
        placeholderText: "Password"
        echoMode: TextInput.Password
    }
}
