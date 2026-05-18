pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Widgets 1.0 as AppWidgets

Rectangle {
    id: drawer
    property ShellContexts.ShellContext shellModel

    color: Theme.AppTheme.navBackground

    // Map route prefix → icon name
    function iconForRoute(routeId) {
        if (routeId === "shell.home")                  return "home"
        if (routeId.startsWith("platform.admin"))      return "admin"
        if (routeId.startsWith("platform.control"))    return "control"
        if (routeId.startsWith("platform.settings"))   return "settings"
        if (routeId.startsWith("platform."))           return "admin"
        if (routeId.startsWith("project_management.")) return "project"
        if (routeId.startsWith("inventory_procurement.")) return "inventory"
        if (routeId.startsWith("maintenance."))        return "maintenance"
        return "default"
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

        ColumnLayout {
            width: drawer.width
            spacing: 0

            // App name header in drawer
            Item {
                Layout.fillWidth: true
                height: 48

                Label {
                    anchors.left: parent.left
                    anchors.leftMargin: Theme.AppTheme.marginLg
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Navigation"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }
            }

            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: Theme.AppTheme.divider
            }

            Item { Layout.fillWidth: true; height: Theme.AppTheme.spacingSm }

            Repeater {
                id: navRepeater
                model: drawer.shellModel ? drawer.shellModel.navigationItems : []

                delegate: NavRow {
                    required property var modelData
                    required property int index

                    Layout.fillWidth: true
                    routeId: modelData.routeId
                    routeTitle: modelData.title
                    groupLabel: modelData.groupLabel
                    iconName: drawer.iconForRoute(modelData.routeId)
                    isSelected: drawer.shellModel
                        ? drawer.shellModel.currentRouteId === modelData.routeId
                        : false
                    prevGroupLabel: index > 0 && drawer.shellModel
                        ? drawer.shellModel.navigationItems[index - 1].groupLabel
                        : ""

                    onActivated: function(rId) {
                        if (drawer.shellModel) {
                            drawer.shellModel.selectRoute(rId)
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true; height: Theme.AppTheme.spacingMd }
        }
    }

    // Inline nav row component — keeps ShellDrawer self-contained
    component NavRow: ColumnLayout {
        id: navRow

        property string routeId: ""
        property string routeTitle: ""
        property string groupLabel: ""
        property string iconName: "default"
        property bool isSelected: false
        property string prevGroupLabel: ""

        signal activated(string routeId)

        spacing: 0

        // Group section header — shown when group changes
        Item {
            Layout.fillWidth: true
            height: groupLabel !== prevGroupLabel && groupLabel.length > 0
                ? Theme.AppTheme.sectionTitleSize + Theme.AppTheme.spacingMd
                : 0
            visible: height > 0
            clip: true

            Label {
                anchors.left: parent.left
                anchors.leftMargin: Theme.AppTheme.marginLg
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Theme.AppTheme.spacingXs
                text: navRow.groupLabel.toUpperCase()
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.sectionTitleSize
                font.bold: true
                font.letterSpacing: 0.5
            }
        }

        // Row item
        Rectangle {
            Layout.fillWidth: true
            height: Theme.AppTheme.sidebarRowHeight
            color: navRow.isSelected
                ? Theme.AppTheme.navSelectedBackground
                : rowHover.containsMouse
                    ? Theme.AppTheme.navHoverBackground
                    : "transparent"

            // Accent left rail for selected item
            Rectangle {
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                width: 3
                radius: 1
                color: Theme.AppTheme.accent
                visible: navRow.isSelected
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: navRow.isSelected
                    ? Theme.AppTheme.marginLg - 3
                    : Theme.AppTheme.marginLg
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                AppIcons.AppIcon {
                    name: navRow.iconName
                    size: 14
                    iconColor: navRow.isSelected
                        ? Theme.AppTheme.navSelectedText
                        : Theme.AppTheme.textMuted
                }

                Label {
                    Layout.fillWidth: true
                    text: navRow.routeTitle
                    color: navRow.isSelected
                        ? Theme.AppTheme.navSelectedText
                        : Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: navRow.isSelected
                    elide: Text.ElideRight
                }
            }

            MouseArea {
                id: rowHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: navRow.activated(navRow.routeId)
            }
        }
    }
}
