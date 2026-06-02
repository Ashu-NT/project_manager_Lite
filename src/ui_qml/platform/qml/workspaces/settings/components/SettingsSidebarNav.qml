pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

Item {
    id: root

    property bool collapsed: false
    property string activeSection: ""

    signal sectionChanged(string section)

    implicitWidth: root.collapsed ? 48 : 220

    Behavior on implicitWidth {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.navBackground

        Rectangle {
            anchors { top: parent.top; bottom: parent.bottom; right: parent.right }
            width: 1; color: Theme.AppTheme.divider
        }
    }

    // ── Header ────────────────────────────────────────────────────────────
    Item {
        id: _sidebarHead
        anchors.top:   parent.top
        anchors.left:  parent.left
        anchors.right: parent.right
        height: 40

        AppControls.Label {
            visible: !root.collapsed
            anchors.left: parent.left
            anchors.leftMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: _sidebarToggle.left
            anchors.rightMargin: 4
            text: "Settings"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold: true
            elide: Text.ElideRight
        }

        Rectangle {
            id: _sidebarToggle
            anchors.right: parent.right
            anchors.rightMargin: 6
            anchors.verticalCenter: parent.verticalCenter
            width: 28; height: 28; radius: 4
            color: _toggleMA.containsMouse ? Theme.AppTheme.navHoverBackground : "transparent"

            AppIcons.AppIcon {
                anchors.centerIn: parent
                name: root.collapsed ? "chevron_right" : "chevron_left"
                size: 11
                iconColor: Theme.AppTheme.textMuted
            }

            MouseArea {
                id: _toggleMA
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.collapsed = !root.collapsed
            }
        }

        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1; color: Theme.AppTheme.divider
        }
    }

    // ── Nav list ──────────────────────────────────────────────────────────
    ListView {
        anchors.top: _sidebarHead.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        clip: true
        topMargin: 4
        bottomMargin: 4
        boundsBehavior: Flickable.StopAtBounds

        model: [
            { type: "group", label: "PLATFORM" },
            { type: "item",  section: "runtime",      label: "Runtime",               icon: "settings"  },
            { type: "item",  section: "modules",      label: "Module Entitlements",   icon: "project"   },
            { type: "group", label: "CONFIGURATION" },
            { type: "item",  section: "defaults",      label: "Platform Defaults",         icon: "register"      },
            { type: "item",  section: "integrations",  label: "Integration Capabilities",  icon: "collaboration" },
            { type: "item",  section: "security",      label: "Security",                  icon: "control"       },
            { type: "group", label: "SYSTEM" },
            { type: "item",  section: "sysinfo",       label: "Support & Diagnostics",     icon: "maintenance"   }
        ]

        delegate: Item {
            id: sidebarDelegate

            required property var modelData

            readonly property var itemData: sidebarDelegate.modelData
            readonly property bool isGroup: sidebarDelegate.itemData.type === "group"
            readonly property bool isItem:  sidebarDelegate.itemData.type === "item"

            width:   ListView.view ? ListView.view.width : 0
            height:  sidebarDelegate.isGroup ? (root.collapsed ? 0 : 24) : 34
            visible: sidebarDelegate.isGroup ? !root.collapsed : true
            clip:    true

            AppControls.Label {
                visible: sidebarDelegate.isGroup
                anchors.left: parent.left
                anchors.leftMargin: 14
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 3
                text: sidebarDelegate.itemData.label || ""
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
                font.letterSpacing: 0.7
            }

            Rectangle {
                id: _navBg
                visible: sidebarDelegate.isItem
                anchors.fill: parent
                anchors.leftMargin: 4
                anchors.rightMargin: 4
                radius: 4

                readonly property bool _active: root.activeSection === (sidebarDelegate.itemData.section || "")

                color: _navBg._active
                    ? Theme.AppTheme.navSelectedBackground
                    : _navMA.containsMouse
                        ? Theme.AppTheme.navHoverBackground : "transparent"

                Rectangle {
                    visible: _navBg._active
                    anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                    anchors.topMargin: 5; anchors.bottomMargin: 5
                    width: 3; radius: 2
                    color: Theme.AppTheme.accent
                }

                AppIcons.AppIcon {
                    id: _navIco
                    anchors.left: parent.left
                    anchors.leftMargin: root.collapsed ? 13 : 11
                    anchors.verticalCenter: parent.verticalCenter
                    name: sidebarDelegate.itemData.icon || "settings"
                    size: 13
                    iconColor: _navBg._active ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
                }

                AppControls.Label {
                    visible: !root.collapsed
                    anchors.left: _navIco.right
                    anchors.leftMargin: 9
                    anchors.right: parent.right
                    anchors.rightMargin: 8
                    anchors.verticalCenter: parent.verticalCenter
                    text: sidebarDelegate.itemData.label || ""
                    color: _navBg._active ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: _navBg._active
                    elide: Text.ElideRight
                }

                ToolTip.visible: root.collapsed && _navMA.containsMouse
                ToolTip.text: sidebarDelegate.itemData.label || ""
                ToolTip.delay: 700

                MouseArea {
                    id: _navMA
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        const s = sidebarDelegate.itemData.section || ""
                        if (s.length > 0) root.sectionChanged(s)
                    }
                }
            }
        }
    }
}
