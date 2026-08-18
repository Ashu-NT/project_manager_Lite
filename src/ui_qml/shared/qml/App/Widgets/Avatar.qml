import QtQuick
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

// Small, decorative "person" avatar: a colored circle with initials, used
// wherever a list row identifies a person/resource (task assignments,
// comment authors, ...). The background color is picked deterministically
// from `name` (same name -> same color, every time, no state needed) out of
// a fixed categorical palette -- intentionally decorative, not a status/
// semantic color, so it stays stable across light/dark theme.
Rectangle {
    id: root

    property string name: ""
    property int size: 36

    readonly property var _palette: [
        "#5B8DEF", "#37B392", "#F2994A", "#9B6BDE",
        "#EB5B8C", "#3FA7D6", "#E0A800", "#4C6EF5"
    ]
    readonly property string _initials: {
        const parts = String(root.name || "").trim().split(/\s+/).filter(function (p) { return p.length > 0 })
        if (parts.length === 0) return "?"
        if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase()
        return String(parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase()
    }
    readonly property color _background: {
        let hash = 0
        const text = String(root.name || "")
        for (let i = 0; i < text.length; i++) {
            hash = (hash * 31 + text.charCodeAt(i)) & 0xffffffff
        }
        const index = Math.abs(hash) % root._palette.length
        return root._palette[index]
    }

    implicitWidth: root.size
    implicitHeight: root.size
    radius: root.size / 2
    color: root._background

    AppControls.Label {
        anchors.centerIn: parent
        text: root._initials
        color: "#ffffff"
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Math.round(root.size * 0.38)
        font.bold: true
    }
}
