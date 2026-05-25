import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Shell.Context 1.0 as ShellContexts
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

Rectangle {
    id: header

    property ShellContexts.ShellContext shellModel
    property bool sidebarCollapsed: false

    signal toggleSidebar()

    readonly property string currentModuleLabel: {
        if (!header.shellModel) {
            return ""
        }
        const nav = header.shellModel.navigationItems || []
        const routeId = header.shellModel.currentRouteId || ""
        for (let i = 0; i < nav.length; i += 1) {
            if ((nav[i].routeId || "") === routeId) {
                return String(nav[i].moduleLabel || "")
            }
        }
        return ""
    }

    height: Theme.AppTheme.headerHeight
    color: Theme.AppTheme.surfaceRaised

    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 1
        color: Theme.AppTheme.divider
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.marginMd
        anchors.rightMargin: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingMd

        Rectangle {
            implicitWidth: Theme.AppTheme.inputHeight
            implicitHeight: Theme.AppTheme.inputHeight
            radius: Theme.AppTheme.radiusSm
            color: toggleHover.containsMouse
                ? Theme.AppTheme.hoverSurface
                : Theme.AppTheme.surfaceOverlay

            AppIcons.AppIcon {
                anchors.centerIn: parent
                name: "menu"
                size: 14
                iconColor: Theme.AppTheme.textMuted
            }

            MouseArea {
                id: toggleHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: header.toggleSidebar()
            }

            ToolTip {
                visible: toggleHover.containsMouse
                text: header.sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"
                delay: 400
            }
        }

        ColumnLayout {
            Layout.preferredWidth: 280
            spacing: 1

            Label {
                Layout.fillWidth: true
                text: header.shellModel ? header.shellModel.appTitle : "TECHASH Enterprise"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
                font.letterSpacing: 0.8
                elide: Text.ElideRight
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                Label {
                    Layout.fillWidth: true
                    text: header.shellModel ? (header.shellModel.currentRouteTitle || "") : ""
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    elide: Text.ElideRight
                }

                Rectangle {
                    visible: header.currentModuleLabel.length > 0
                    radius: Theme.AppTheme.radiusSm
                    color: Theme.AppTheme.surfaceOverlay
                    implicitWidth: moduleText.implicitWidth + 14
                    implicitHeight: Theme.AppTheme.inputHeight - 6

                    Label {
                        id: moduleText
                        anchors.centerIn: parent
                        text: header.currentModuleLabel
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                        elide: Text.ElideRight
                    }
                }
            }
        }

        Item {
            Layout.fillWidth: true
        }

        Rectangle {
            Layout.preferredWidth: 300
            Layout.preferredHeight: Theme.AppTheme.inputHeight
            radius: Theme.AppTheme.radiusSm
            color: Theme.AppTheme.surfaceOverlay

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.spacingSm
                anchors.rightMargin: Theme.AppTheme.spacingSm
                spacing: Theme.AppTheme.spacingXs

                AppIcons.AppIcon {
                    name: "search"
                    size: 12
                    iconColor: Theme.AppTheme.textMuted
                }

                Label {
                    Layout.fillWidth: true
                    text: "Global search"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    elide: Text.ElideRight
                }
            }
        }

        RowLayout {
            spacing: Theme.AppTheme.spacingXs

            Repeater {
                model: [
                    { "icon": "workflow", "label": "Approvals" },
                    { "icon": "notifications", "label": "Notifications" }
                ]

                delegate: Rectangle {
                    id: actionCell
                    required property var modelData

                    implicitWidth: Theme.AppTheme.inputHeight
                    implicitHeight: Theme.AppTheme.inputHeight
                    radius: Theme.AppTheme.radiusSm
                    color: actionHover.containsMouse
                        ? Theme.AppTheme.hoverSurface
                        : Theme.AppTheme.surfaceOverlay

                    AppIcons.AppIcon {
                        anchors.centerIn: parent
                        name: actionCell.modelData.icon
                        size: 13
                        iconColor: Theme.AppTheme.textMuted
                    }

                    MouseArea {
                        id: actionHover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                    }

                    ToolTip {
                        visible: actionHover.containsMouse
                        text: actionCell.modelData.label
                        delay: 350
                    }
                }
            }
        }

        Rectangle {
            implicitWidth: userRow.implicitWidth + Theme.AppTheme.spacingMd
            implicitHeight: Theme.AppTheme.inputHeight
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceOverlay

            RowLayout {
                id: userRow
                anchors.centerIn: parent
                spacing: Theme.AppTheme.spacingSm

                Rectangle {
                    implicitWidth: 28
                    implicitHeight: 28
                    radius: 14
                    color: Theme.AppTheme.accentSoft

                    Label {
                        anchors.centerIn: parent
                        text: {
                            const name = header.shellModel ? (header.shellModel.userDisplayName || "") : ""
                            return name.length > 0 ? name.charAt(0).toUpperCase() : "U"
                        }
                        color: Theme.AppTheme.accent
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: true
                    }
                }

                ColumnLayout {
                    spacing: 0

                    Label {
                        text: header.shellModel && (header.shellModel.userDisplayName || "").length > 0
                            ? header.shellModel.userDisplayName
                            : "User"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: true
                    }

                    Label {
                        text: header.currentModuleLabel.length > 0
                            ? header.currentModuleLabel
                            : "Workspace"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                }
            }
        }
    }
}

