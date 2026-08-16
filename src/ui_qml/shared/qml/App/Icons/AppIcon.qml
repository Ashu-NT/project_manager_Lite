import QtQuick
import App.Theme 1.0 as Theme
import "IconRegistry.js" as IconRegistry

Item {
    id: root

    // Public API
    property string name:      "default"
    property color  iconColor: Theme.AppTheme.textSecondary
    property int    size:      Theme.AppTheme.iconMd
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

    FontLoader {
        id: fluentRegular
        source: "qrc:/fonts/FluentRegular.ttf"
    }

    FontLoader {
        id: fluentFilled
        source: "qrc:/fonts/FluentFilled.ttf"
    }

    // Warn once per unrecognized name so a typo'd/\u672A-registered icon name is
    // caught during development instead of silently rendering the fallback
    // glyph forever.
    onNameChanged: {
        if (root.name.length > 0 && !IconRegistry.isKnown(root.name)) {
            console.warn("AppIcon: unknown icon name '" + root.name + "', rendering fallback glyph")
        }
    }

    // Glyph renderer
    Text {
        id: _glyph

        anchors.centerIn: parent

        text: IconRegistry.glyphFor(root.name)

        color: root._effectiveColor

        font.family: root.active ? fluentFilled.name : fluentRegular.name
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

