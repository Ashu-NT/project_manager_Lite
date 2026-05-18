import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import Shell.Controllers 1.0 as ShellControllers

ApplicationWindow {
    id: loginWindow

    property ShellControllers.ShellLoginController loginController

    width: 560
    height: 440
    visible: true
    title: "Sign in"
    color: Theme.AppTheme.appBackground

    onClosing: function() {
        if (loginController !== null && !loginController.isAuthenticated) {
            loginController.cancel()
        }
    }

    Connections {
        target: loginWindow.loginController

        function onAccepted() {
            loginWindow.close()
        }

        function onRejected() {
            loginWindow.close()
        }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#F7FBFF" }
            GradientStop { position: 1.0; color: Theme.AppTheme.appBackground }
        }
    }

    Rectangle {
        anchors.centerIn: parent
        width: Math.min(parent.width - 48, 440)
        height: Math.max(loginLayout.implicitHeight + Theme.AppTheme.marginLg * 2, 360)
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        border.color: Theme.AppTheme.border

        ColumnLayout {
            id: loginLayout
            
            anchors.fill: parent
            anchors.margins: Theme.AppTheme.marginLg
            spacing: Theme.AppTheme.spacingMd

            Label {
                text: "TECHASH Enterprise"
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: 28
                font.bold: true
                color: Theme.AppTheme.textPrimary
            }

            Label {
                text: "Sign in to open the QML workspace shell."
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
                color: Theme.AppTheme.textSecondary
                Layout.fillWidth: true
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.AppTheme.spacingSm
            }

            Label {
                text: "Username"
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                color: Theme.AppTheme.textMuted
            }

            TextField {
                id: usernameField
                Layout.fillWidth: true
                text: loginWindow.loginController ? loginWindow.loginController.username : ""
                placeholderText: "Username"
                enabled: loginWindow.loginController ? !loginWindow.loginController.isBusy : true

                onTextEdited: {
                    if (loginWindow.loginController !== null) {
                        loginWindow.loginController.setUsername(text)
                    }
                }
            }

            Label {
                text: "Password"
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                color: Theme.AppTheme.textMuted
            }

            TextField {
                id: passwordField
                Layout.fillWidth: true
                text: loginWindow.loginController ? loginWindow.loginController.password : ""
                placeholderText: "Password"
                echoMode: TextInput.Password
                enabled: loginWindow.loginController ? !loginWindow.loginController.isBusy : true

                onTextEdited: {
                    if (loginWindow.loginController !== null) {
                        loginWindow.loginController.setPassword(text)
                    }
                }

                onAccepted: {
                    if (loginWindow.loginController !== null && !loginWindow.loginController.isBusy) {
                        loginWindow.loginController.signIn()
                    }
                }
            }

            Label {
                visible: loginWindow.loginController !== null && loginWindow.loginController.errorMessage.length > 0
                text: loginWindow.loginController ? loginWindow.loginController.errorMessage : ""
                color: Theme.AppTheme.danger
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: Theme.AppTheme.spacingSm
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                Button {
                    text: "Exit"
                    enabled: loginWindow.loginController ? !loginWindow.loginController.isBusy : true

                    onClicked: {
                        if (loginWindow.loginController !== null) {
                            loginWindow.loginController.cancel()
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                }

                BusyIndicator {
                    running: loginWindow.loginController ? loginWindow.loginController.isBusy : false
                    visible: running
                }

                AppControls.PrimaryButton {
                    text: loginWindow.loginController && loginWindow.loginController.isBusy ? "Signing in..." : "Sign in"
                    enabled: loginWindow.loginController
                        ? (!loginWindow.loginController.isBusy
                            && loginWindow.loginController.username.length > 0
                            && loginWindow.loginController.password.length > 0)
                        : false

                    onClicked: {
                        if (loginWindow.loginController !== null) {
                            loginWindow.loginController.signIn()
                        }
                    }
                }
            }
        }
    }
}
