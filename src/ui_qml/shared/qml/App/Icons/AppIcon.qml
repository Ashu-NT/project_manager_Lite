import QtQuick
import App.Theme 1.0 as Theme

Item {
    id: root

    // Public API
    property string name:      "default"
    property color  iconColor: Theme.AppTheme.textSecondary
    property int    size:      16
    property bool   active:    false
    property bool   disabled:  false

    // Sizing follows the rendered glyph
    implicitWidth:  _glyph.implicitWidth
    implicitHeight: _glyph.implicitHeight

    opacity: root.disabled ? 0.38 : 1.0

    Behavior on opacity {
        NumberAnimation {
            duration: 150
        }
    }

    // Effective color
    readonly property color _effectiveColor: root.disabled
        ? Theme.AppTheme.textMuted
        : (root.active ? Theme.AppTheme.accent : root.iconColor)

    // Primary + fallback font
    readonly property string _iconFontFamily:
        Qt.fontFamilies().indexOf("Segoe Fluent Icons") !== -1
            ? "Segoe Fluent Icons"
            : "Segoe MDL2 Assets"

    // Icon registry
    readonly property var _map: ({
        // Navigation and Shell
        "home":           "\uE80F",
        "dashboard":      "\uE9D2",
        "search":         "\uE721",
        "settings":       "\uE713",
        "notifications":  "\uEA8F",
        "user":           "\uE77B",
        "admin":          "\uE7EF",
        "control":        "\uE8EF",
        "menu":           "\uE700",

        // Actions
        "add":            "\uE710",
        "edit":           "\uE70F",
        "delete":         "\uE74D",
        "close":          "\uE711",
        "refresh":        "\uE72C",
        "filter":         "\uE71C",
        "export":         "\uEDE1",
        "import":         "\uE8B5",
        "approve":        "\uE8FB",
        "reject":         "\uE738",
        "history":        "\uE81C",

        // Project Management
        "project":        "\uE8D4",
        "tasks":          "\uE9D9",
        "calendar":       "\uE787",
        "resources":      "\uE716",
        "financials":     "\uE8C3",
        "risk":           "\uE946",
        "portfolio":      "\uE8F4",
        "register":       "\uE8C9",
        "collaboration":  "\uE939",
        "timesheets":     "\uE823",

        // Maintenance
        "assets":         "\uE90F",
        "maintenance":    "\uE907",
        "workflow":       "\uEA3A",
        "reliability":    "\uE9D5",
        "planner":        "\uE7FD",

        // Inventory and Procurement
        "catalog":        "\uE80B",
        "inventory":      "\uE8D3",
        "reservations":   "\uE8B9",
        "procurement":    "\uE719",
        "pricing":        "\uE8C0",

        // Drawer navigation
        "chevron_down":   "\uE70D",
        "chevron_up":     "\uE70E",
        "chevron_right":  "\uE76C",
        "chevron_left":   "\uE76D",

        // Additional actions
        "save":           "\uE74E",
        "view":           "\uE8A0",
        "upload":         "\uE898",

        // Fallback
        "default":        "\uE8B7"
    })

    // Glyph renderer
    Text {
        id: _glyph

        anchors.centerIn: parent

        text: root._map[root.name] !== undefined
              ? root._map[root.name]
              : root._map["default"]

        color: root._effectiveColor

        font.family: root._iconFontFamily
        font.pixelSize: root.size

        renderType: Text.NativeRendering

        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter

        Behavior on color {
            ColorAnimation {
                duration: 150
            }
        }
    }
}