import QtQuick
import App.Theme 1.0 as Theme

Item {
    id: root

    property real value: 0.0
    property string colorHint: ""

    implicitWidth: 80
    implicitHeight: 6

    readonly property color _fillColor: {
        if (root.colorHint === "success") return Theme.AppTheme.success
        if (root.colorHint === "warning") return Theme.AppTheme.warning
        if (root.colorHint === "danger")  return Theme.AppTheme.danger
        if (root.value >= 1.0)            return Theme.AppTheme.success
        if (root.value >= 0.7)            return Theme.AppTheme.accent
        if (root.value >= 0.4)            return Theme.AppTheme.warning
        return Theme.AppTheme.danger
    }

    // Track
    Rectangle {
        anchors.fill: parent
        radius: 3
        color: Theme.AppTheme.surfaceSunken
    }

    // Fill
    Rectangle {
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: Math.max(0, Math.min(1.0, root.value)) * parent.width
        radius: 3
        color: root._fillColor

        Behavior on width {
            NumberAnimation { duration: 200; easing.type: Easing.OutCubic }
        }
    }
}
