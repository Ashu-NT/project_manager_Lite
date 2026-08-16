pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

// A single elevated KPI card -- one per Platform Overview metric, replacing
// the old single-strip-of-pills look with individually-scannable tiles.
// Platform-Overview-specific (not App.Widgets.KpiStrip) so this visual
// treatment doesn't ripple into Control/Settings' own KPI strips, which
// still use the shared component unchanged.
Rectangle {
    id: root

    property string label: ""
    property string value: "--"
    property string supportingText: ""
    property string trend: ""
    property string trendLabel: ""
    property string colorHint: ""
    property bool clickable: false

    signal activated()

    implicitHeight: _layout.implicitHeight + Theme.AppTheme.marginLg * 2
    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surfaceRaised
    border.width: 1
    border.color: _hover.hovered && root.clickable ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder

    Behavior on border.color { ColorAnimation { duration: 120 } }

    readonly property color _valueColor: {
        if (root.colorHint === "success") return Theme.AppTheme.success
        if (root.colorHint === "warning") return Theme.AppTheme.warning
        if (root.colorHint === "danger")  return Theme.AppTheme.danger
        return Theme.AppTheme.textPrimary
    }
    readonly property color _trendColor: {
        if (root.trend === "up")   return Theme.AppTheme.success
        if (root.trend === "down") return Theme.AppTheme.danger
        return Theme.AppTheme.textMuted
    }
    readonly property string _trendArrow: {
        if (root.trend === "up")   return "▲"
        if (root.trend === "down") return "▼"
        return ""
    }

    ColumnLayout {
        id: _layout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingXs

        AppControls.Label {
            Layout.fillWidth: true
            text: root.label.toUpperCase()
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
            font.bold: true
            font.letterSpacing: 0.6
            elide: Text.ElideRight
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 2
            spacing: Theme.AppTheme.spacingXs

            AppControls.Label {
                text: root.value
                color: root._valueColor
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: 30
                font.bold: true
            }

            Text {
                visible: root._trendArrow !== ""
                text: root._trendArrow
                color: root._trendColor
                font.pixelSize: Theme.AppTheme.smallSize
            }

            AppControls.Label {
                visible: root.trendLabel !== "" && root._trendArrow !== ""
                text: root.trendLabel
                color: root._trendColor
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
            }

            Item { Layout.fillWidth: true }
        }

        AppControls.Label {
            Layout.fillWidth: true
            Layout.topMargin: 2
            visible: root.supportingText !== ""
            text: root.supportingText
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            elide: Text.ElideRight
        }
    }

    HoverHandler {
        id: _hover
        enabled: root.clickable
        cursorShape: root.clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    TapHandler {
        enabled: root.clickable
        onTapped: root.activated()
    }
}
