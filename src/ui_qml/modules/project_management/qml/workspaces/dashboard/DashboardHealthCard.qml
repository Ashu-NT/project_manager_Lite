pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Rectangle {
    id: root

    property var model: ({})
    property var shellModel: null

    readonly property string _routeId: String(root.model.routeId || "")
    readonly property bool _clickable: root._routeId.length > 0 && root.shellModel

    radius: Theme.AppTheme.radiusMd
    color: mouseArea.containsMouse && root._clickable
        ? Theme.AppTheme.hoverSurface
        : Theme.AppTheme.surfaceRaised
    border.color: Theme.AppTheme.subtleBorder
    border.width: 1
    implicitHeight: 108

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginSm
        spacing: Theme.AppTheme.spacingXs

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                text: String(root.model.title || "")
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
                font.letterSpacing: 0.4
                elide: Text.ElideRight
            }

            AppWidgets.StatusChip {
                visible: String(root.model.statusLabel || "").length > 0
                status: String(root.model.statusLabel || "")
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            Label {
                text: String(root.model.metricValue || "—")
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize + 4
                font.bold: true
            }

            Label {
                Layout.fillWidth: true
                text: String(root.model.metricLabel || "")
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                elide: Text.ElideRight
                maximumLineCount: 1
            }
        }

        Label {
            Layout.fillWidth: true
            text: String(root.model.supportingText || "")
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }

        Item {
            Layout.fillHeight: true
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                text: String(root.model.metaText || "")
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Label {
                visible: root._clickable
                text: "Open"
                color: Theme.AppTheme.accent
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
            }
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: root._clickable
        enabled: root._clickable
        cursorShape: root._clickable ? Qt.PointingHandCursor : Qt.ArrowCursor

        onClicked: root.shellModel.selectRoute(root._routeId)
    }
}

