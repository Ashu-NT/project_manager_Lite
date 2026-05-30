import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import Shell.Controllers 1.0 as ShellControllers

ApplicationWindow {
    id: loginWindow

    property ShellControllers.ShellLoginController loginController

    width: 900
    height: 560
    minimumWidth: 740
    minimumHeight: 480
    visible: true
    title: "Sign in — TECHASH Enterprise"
    color: "#0F1117"

    onClosing: function() {
        if (loginController !== null && !loginController.isAuthenticated) {
            loginController.cancel()
        }
    }

    Connections {
        target: loginWindow.loginController
        function onAccepted() { loginWindow.close() }
        function onRejected() { loginWindow.close() }
    }

    // ── Left brand panel ──────────────────────────────────────────────
    Rectangle {
        id: _leftPanel
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: Math.floor(parent.width * 0.42)
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: "#0D1B3E" }
            GradientStop { position: 1.0; color: "#1A3461" }
        }

        // Decorative rings
        Rectangle {
            width: 320; height: 320
            radius: 160
            anchors.horizontalCenter: parent.right
            anchors.verticalCenter: parent.top
            anchors.verticalCenterOffset: 40
            color: "transparent"
            border.color: Qt.rgba(1, 1, 1, 0.05)
            border.width: 60
        }
        Rectangle {
            width: 220; height: 220
            radius: 110
            anchors.horizontalCenter: parent.left
            anchors.verticalCenter: parent.bottom
            anchors.verticalCenterOffset: -20
            color: "transparent"
            border.color: Qt.rgba(1, 1, 1, 0.04)
            border.width: 44
        }
        // Accent bar at the top
        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 3
            color: Theme.AppTheme.accent
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 40
            spacing: 0

            // Logo mark
            Rectangle {
                width: 44; height: 44
                radius: 10
                color: Theme.AppTheme.accent

                Text {
                    anchors.centerIn: parent
                    text: "T"
                    color: "white"
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: 24
                    font.bold: true
                    font.letterSpacing: -0.5
                }
            }

            Item { Layout.preferredHeight: 32 }

            Text {
                text: "TECHASH"
                color: "white"
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: 28
                font.bold: true
                font.letterSpacing: 1.5
            }

            Item { Layout.preferredHeight: 6 }

            Text {
                text: "Enterprise Suite"
                color: Qt.rgba(1, 1, 1, 0.55)
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: 13
                font.letterSpacing: 0.5
            }

            Item { Layout.fillHeight: true }

            // Feature pills
            Column {
                spacing: 10

                Repeater {
                    model: [
                        { icon: "▸", label: "Project & Portfolio Management" },
                        { icon: "▸", label: "Resource Planning & Scheduling" },
                        { icon: "▸", label: "Inventory & Procurement" },
                        { icon: "▸", label: "Maintenance Operations" }
                    ]

                    delegate: Row {
                        required property var modelData
                        spacing: 10

                        Text {
                            text: modelData.icon
                            color: Theme.AppTheme.accent
                            font.pixelSize: 11
                            anchors.verticalCenter: parent.verticalCenter
                        }
                        Text {
                            text: modelData.label
                            color: Qt.rgba(1, 1, 1, 0.6)
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: 12
                        }
                    }
                }
            }

            Item { Layout.preferredHeight: 24 }

            Text {
                text: "© 2026 TECHASH • All rights reserved"
                color: Qt.rgba(1, 1, 1, 0.25)
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: 10
            }
        }
    }

    // ── Right form panel ──────────────────────────────────────────────
    Rectangle {
        anchors.left: _leftPanel.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        color: Theme.AppTheme.surface

        ColumnLayout {
            id: _formLayout
            anchors.centerIn: parent
            width: Math.min(340, parent.width - 64)
            spacing: 0

            // Header
            Text {
                text: "Welcome back"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: 24
                font.bold: true
            }

            Item { Layout.preferredHeight: 6 }

            Text {
                text: "Sign in to your workspace"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: 13
            }

            Item { Layout.preferredHeight: 32 }

            // Username field
            Text {
                text: "Username"
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: 12
                font.bold: true
            }

            Item { Layout.preferredHeight: 6 }

            AppControls.TextField {
                id: usernameField
                Layout.fillWidth: true
                text: loginWindow.loginController ? loginWindow.loginController.username : ""
                placeholderText: "Enter your username"
                enabled: loginWindow.loginController ? !loginWindow.loginController.isBusy : true
                onTextEdited: {
                    if (loginWindow.loginController !== null)
                        loginWindow.loginController.setUsername(text)
                }
                Keys.onTabPressed: passwordField.forceActiveFocus()
            }

            Item { Layout.preferredHeight: 16 }

            // Password field
            Text {
                text: "Password"
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: 12
                font.bold: true
            }

            Item { Layout.preferredHeight: 6 }

            AppControls.TextField {
                id: passwordField
                Layout.fillWidth: true
                text: loginWindow.loginController ? loginWindow.loginController.password : ""
                placeholderText: "Enter your password"
                echoMode: TextInput.Password
                enabled: loginWindow.loginController ? !loginWindow.loginController.isBusy : true
                onTextEdited: {
                    if (loginWindow.loginController !== null)
                        loginWindow.loginController.setPassword(text)
                }
                onAccepted: {
                    if (loginWindow.loginController !== null && !loginWindow.loginController.isBusy)
                        loginWindow.loginController.signIn()
                }
            }

            Item { Layout.preferredHeight: 8 }

            // Error message
            Rectangle {
                Layout.fillWidth: true
                visible: loginWindow.loginController !== null
                    && loginWindow.loginController.errorMessage.length > 0
                height: visible ? _errRow.implicitHeight + 16 : 0
                radius: Theme.AppTheme.radiusSm
                color: Qt.rgba(
                    Theme.AppTheme.danger.r,
                    Theme.AppTheme.danger.g,
                    Theme.AppTheme.danger.b,
                    0.08
                )
                border.color: Qt.rgba(
                    Theme.AppTheme.danger.r,
                    Theme.AppTheme.danger.g,
                    Theme.AppTheme.danger.b,
                    0.3
                )
                border.width: 1

                Row {
                    id: _errRow
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 12
                    spacing: 8

                    Text {
                        text: "⚠"
                        color: Theme.AppTheme.danger
                        font.pixelSize: 13
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    Text {
                        width: parent.width - 24
                        text: loginWindow.loginController ? loginWindow.loginController.errorMessage : ""
                        color: Theme.AppTheme.danger
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                }
            }

            Item { Layout.preferredHeight: 20 }

            // Sign in button
            Rectangle {
                Layout.fillWidth: true
                height: 44
                radius: Theme.AppTheme.radiusSm
                color: _signInMouse.containsMouse && !_signInMouse.pressed
                    ? Theme.AppTheme.accentHover
                    : _signInMouse.pressed
                        ? Theme.AppTheme.accentPressed
                        : Theme.AppTheme.accent
                opacity: _canSignIn ? 1.0 : 0.45

                readonly property bool _canSignIn: loginWindow.loginController
                    ? (!loginWindow.loginController.isBusy
                        && loginWindow.loginController.username.length > 0
                        && loginWindow.loginController.password.length > 0)
                    : false

                Row {
                    anchors.centerIn: parent
                    spacing: 8

                    BusyIndicator {
                        visible: loginWindow.loginController ? loginWindow.loginController.isBusy : false
                        running: visible
                        width: 18; height: 18
                        anchors.verticalCenter: parent.verticalCenter
                        contentItem: Item {
                            Rectangle {
                                width: 14; height: 14
                                radius: 7
                                anchors.centerIn: parent
                                color: "transparent"
                                border.color: Qt.rgba(1,1,1,0.7)
                                border.width: 2
                            }
                        }
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: loginWindow.loginController && loginWindow.loginController.isBusy
                            ? "Signing in…"
                            : "Sign in"
                        color: "white"
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: 14
                        font.bold: true
                    }
                }

                MouseArea {
                    id: _signInMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    enabled: parent._canSignIn
                    onClicked: {
                        if (loginWindow.loginController !== null)
                            loginWindow.loginController.signIn()
                    }
                }
            }

            Item { Layout.preferredHeight: 24 }

            // Exit link
            Row {
                Layout.alignment: Qt.AlignHCenter
                spacing: 4

                Text {
                    text: "Not now?"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: 12
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "Exit application"
                    color: Theme.AppTheme.accent
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: 12
                    font.bold: true
                    anchors.verticalCenter: parent.verticalCenter

                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        enabled: loginWindow.loginController
                            ? !loginWindow.loginController.isBusy : true
                        onClicked: {
                            if (loginWindow.loginController !== null)
                                loginWindow.loginController.cancel()
                        }
                    }
                }
            }
        }
    }
}
