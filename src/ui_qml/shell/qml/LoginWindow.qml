import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import Shell.Controllers 1.0 as ShellControllers

ApplicationWindow {
    id: loginWindow

    property ShellControllers.ShellLoginController loginController
    property bool _showPassword: false

    width: 900
    height: 560
    minimumWidth: 740
    minimumHeight: 480
    visible: true
    title: "Sign in — TECHASH Enterprise"
    color: Theme.AppTheme.loginWindowBackground

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
            GradientStop { position: 0.0; color: Theme.AppTheme.loginBrandGradientStart }
            GradientStop { position: 1.0; color: Theme.AppTheme.loginBrandGradientEnd }
        }

        // Decorative rings
        Rectangle {
            width: 320; height: 320
            radius: 160
            anchors.horizontalCenter: parent.right
            anchors.verticalCenter: parent.top
            anchors.verticalCenterOffset: 40
            color: "transparent"
            border.color: Theme.AppTheme.loginBrandRing1
            border.width: 60
        }
        Rectangle {
            width: 220; height: 220
            radius: 110
            anchors.horizontalCenter: parent.left
            anchors.verticalCenter: parent.bottom
            anchors.verticalCenterOffset: -20
            color: "transparent"
            border.color: Theme.AppTheme.loginBrandRing2
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
                Layout.preferredWidth: 44; Layout.preferredHeight: 44
                radius: 10
                color: Theme.AppTheme.accent

                Text {
                    anchors.centerIn: parent
                    text: "T"
                    color: Theme.AppTheme.textOnAccent
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: 24
                    font.bold: true
                    font.letterSpacing: -0.5
                }
            }

            Item { Layout.preferredHeight: 32 }

            Text {
                text: "TECHASH"
                color: Theme.AppTheme.textOnAccent
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: 28
                font.bold: true
                font.letterSpacing: 1.5
            }

            Item { Layout.preferredHeight: 6 }

            Text {
                text: "Enterprise Suite"
                color: Theme.AppTheme.loginBrandSubtitle
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: 13
                font.letterSpacing: 0.5
            }

            Item { Layout.fillHeight: true }

            // Feature list
            Column {
                spacing: 10

                Repeater {
                    model: [
                        "Project & Portfolio Management",
                        "Resource Planning & Scheduling",
                        "Inventory & Procurement",
                        "Maintenance Operations"
                    ]

                    delegate: Row {
                        id: delegateRoot

                        required property string modelData
                        spacing: 10

                        AppIcons.AppIcon {
                            name: "checkmark"
                            size: Theme.AppTheme.iconSm
                            iconColor: Theme.AppTheme.accent
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            text: delegateRoot.modelData
                            color: Theme.AppTheme.loginBrandFeatureText
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: 12
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                }
            }

            Item { Layout.preferredHeight: 24 }

            Row {
                spacing: 5

                AppIcons.AppIcon {
                    name: "building"
                    size: Theme.AppTheme.iconXs
                    iconColor: Theme.AppTheme.loginBrandFooter
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    text: "2026 TECHASH • All rights reserved"
                    color: Theme.AppTheme.loginBrandFooter
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: 10
                    anchors.verticalCenter: parent.verticalCenter
                }
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

            // Username
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

            // Password
            Text {
                text: "Password"
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: 12
                font.bold: true
            }

            Item { Layout.preferredHeight: 6 }

            Item {
                Layout.fillWidth: true
                implicitHeight: Theme.AppTheme.inputHeight

                AppControls.TextField {
                    id: passwordField
                    anchors.fill: parent
                    rightPadding: 42
                    text: loginWindow.loginController ? loginWindow.loginController.password : ""
                    placeholderText: "Enter your password"
                    echoMode: loginWindow._showPassword ? TextInput.Normal : TextInput.Password
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

                // Password visibility toggle
                Item {
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 40
                    enabled: loginWindow.loginController ? !loginWindow.loginController.isBusy : true

                    AppIcons.AppIcon {
                        anchors.centerIn: parent
                        name: loginWindow._showPassword ? "view_off" : "view"
                        size: 16
                        iconColor: _eyeMouse.containsMouse
                            ? Theme.AppTheme.accent
                            : Theme.AppTheme.textMuted
                    }

                    MouseArea {
                        id: _eyeMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: loginWindow._showPassword = !loginWindow._showPassword
                    }
                }
            }

            Item { Layout.preferredHeight: 8 }

            // Error banner
            Rectangle {
                Layout.fillWidth: true
                visible: loginWindow.loginController !== null
                    && loginWindow.loginController.errorMessage.length > 0
                 Layout.preferredHeight: visible ? _errRow.implicitHeight + 16 : 0
                radius: Theme.AppTheme.radiusSm
                color: Theme.AppTheme.dangerSoft
                border.color: Theme.AppTheme.dangerSoftBorder
                border.width: 1

                Row {
                    id: _errRow
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 12
                    spacing: 8

                    AppIcons.AppIcon {
                        name: "warning"
                        size: Theme.AppTheme.iconSm
                        iconColor: Theme.AppTheme.danger
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
                Layout.preferredHeight: 44
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
                                border.color: Theme.AppTheme.loginSpinnerBorder
                                border.width: 2
                            }
                        }
                    }

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: loginWindow.loginController && loginWindow.loginController.isBusy
                            ? "Signing in…"
                            : "Sign in"
                        color: Theme.AppTheme.textOnAccent
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
