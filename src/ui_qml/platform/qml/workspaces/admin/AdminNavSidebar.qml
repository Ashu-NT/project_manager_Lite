import QtQuick
import QtQuick.Controls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

// Enterprise admin navigation sidebar.
// collapsed = true → 48 px icon-only strip; expanded = 220 px with labels + groups.
Item {
    id: root

    property string activeSection: "organizations"
    property bool   collapsed:     false

    signal sectionChanged(string section)

    implicitWidth: root.collapsed ? 48 : 220

    Behavior on implicitWidth {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    // ── Background ────────────────────────────────────────────────
    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.navBackground

        Rectangle {
            anchors { top: parent.top; bottom: parent.bottom; right: parent.right }
            width: 1; color: Theme.AppTheme.divider
        }
    }

    // ── Header row ────────────────────────────────────────────────
    Item {
        id: _header
        anchors.top:   parent.top
        anchors.left:  parent.left
        anchors.right: parent.right
        height: 40

        Label {
            visible: !root.collapsed
            anchors.left:           parent.left
            anchors.leftMargin:     14
            anchors.verticalCenter: parent.verticalCenter
            anchors.right:          _toggleBtn.left
            anchors.rightMargin:    4
            text:           "Admin Console"
            color:          Theme.AppTheme.textPrimary
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold:      true
            elide:          Text.ElideRight
        }

        Rectangle {
            id: _toggleBtn
            anchors.right:          parent.right
            anchors.rightMargin:    6
            anchors.verticalCenter: parent.verticalCenter
            width: 28; height: 28; radius: 4
            color: _toggleMA.containsMouse ? Theme.AppTheme.navHoverBackground : "transparent"

            AppIcons.AppIcon {
                anchors.centerIn: parent
                name:      root.collapsed ? "chevron_right" : "chevron_left"
                size:      11
                iconColor: Theme.AppTheme.textMuted
            }

            MouseArea {
                id: _toggleMA
                anchors.fill: parent
                hoverEnabled: true
                cursorShape:  Qt.PointingHandCursor
                onClicked:    root.collapsed = !root.collapsed
            }
        }

        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: 1; color: Theme.AppTheme.divider
        }
    }

    // ── Navigation list ───────────────────────────────────────────
    ListView {
        id: _navList
        anchors.top:    _header.bottom
        anchors.left:   parent.left
        anchors.right:  parent.right
        anchors.bottom: parent.bottom
        clip:           true
        topMargin:      4
        bottomMargin:   4
        boundsBehavior: Flickable.StopAtBounds

        model: [
            { type: "group", label: "ORGANIZATION"                                              },
            { type: "item",  section: "organizations", label: "Organizations", icon: "admin"    },
            { type: "item",  section: "sites",         label: "Sites",         icon: "settings" },
            { type: "item",  section: "departments",   label: "Departments",   icon: "resources"},
            { type: "group", label: "WORKFORCE"                                                 },
            { type: "item",  section: "employees",     label: "Employees",     icon: "user"     },
            { type: "item",  section: "users",         label: "Users",         icon: "admin"    },
            { type: "item",  section: "parties",       label: "Parties",       icon: "collaboration" },
            { type: "group", label: "CONTENT"                                                   },
            { type: "item",  section: "documents",     label: "Documents",     icon: "project"  },
            { type: "item",  section: "structures",    label: "Structures",    icon: "register" },
            { type: "group", label: "ACCESS"                                                    },
            { type: "item",  section: "access",        label: "Roles & Access", icon: "control" },
            { type: "group", label: "SYSTEM"                                                    },
            { type: "item",  section: "support",       label: "Support",       icon: "maintenance" },
            { type: "item",  section: "audit",         label: "Audit",         icon: "history"  }
        ]

        delegate: Item {
            // modelData and index are provided by ListView for array models
            property var  _d:  modelData
            property int  _i:  index
            property bool _isGroup: _d.type === "group"
            property bool _isItem:  _d.type === "item"

            width:   _navList.width
            height:  _isGroup ? (root.collapsed ? 0 : 24) : 34
            visible: _isGroup ? !root.collapsed : true
            clip:    true

            // ── Group header ──────────────────────────────────────
            Label {
                visible:         _isGroup
                anchors.left:    parent.left
                anchors.leftMargin: 14
                anchors.bottom:  parent.bottom
                anchors.bottomMargin: 3
                text:            _d.label || ""
                color:           Theme.AppTheme.textMuted
                font.family:     Theme.AppTheme.fontFamily
                font.pixelSize:  Theme.AppTheme.captionSize
                font.bold:       true
                font.letterSpacing: 0.7
            }

            // ── Nav item ──────────────────────────────────────────
            Rectangle {
                id: _itemBg
                visible:  _isItem
                anchors.fill:        parent
                anchors.leftMargin:  4
                anchors.rightMargin: 4
                radius: 4

                readonly property bool _active: root.activeSection === (_d.section || "")

                color: _active
                    ? Theme.AppTheme.navSelectedBackground
                    : _itemMA.containsMouse
                        ? Theme.AppTheme.navHoverBackground : "transparent"

                // Left accent bar
                Rectangle {
                    visible: _itemBg._active
                    anchors { top: parent.top; bottom: parent.bottom; left: parent.left }
                    anchors.topMargin: 5; anchors.bottomMargin: 5
                    width: 3; radius: 2
                    color: Theme.AppTheme.accent
                }

                AppIcons.AppIcon {
                    id: _ico
                    anchors.left:           parent.left
                    anchors.leftMargin:     root.collapsed ? 13 : 11
                    anchors.verticalCenter: parent.verticalCenter
                    name:      _d.icon || "settings"
                    size:      13
                    iconColor: _itemBg._active ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
                }

                Label {
                    visible:                !root.collapsed
                    anchors.left:           _ico.right
                    anchors.leftMargin:     9
                    anchors.right:          parent.right
                    anchors.rightMargin:    8
                    anchors.verticalCenter: parent.verticalCenter
                    text:           _d.label || ""
                    color:          _itemBg._active ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
                    font.family:    Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold:      _itemBg._active
                    elide:          Text.ElideRight
                }

                ToolTip.visible: root.collapsed && _itemMA.containsMouse
                ToolTip.text:    _d.label || ""
                ToolTip.delay:   700

                MouseArea {
                    id: _itemMA
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape:  Qt.PointingHandCursor
                    onClicked: {
                        const s = _d.section || ""
                        if (s.length > 0) root.sectionChanged(s)
                    }
                }
            }
        }
    }
}
