pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    property string hint: ""
    property string emptyState: ""
    property var rows: []
    property var metrics: []

    function toneColor(tone) {
        switch (String(tone || "")) {
        case "danger":
            return Theme.AppTheme.danger
        case "warning":
            return Theme.AppTheme.warning
        case "success":
            return Theme.AppTheme.success
        case "accent":
            return Theme.AppTheme.accent
        default:
            return Theme.AppTheme.textPrimary
        }
    }

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitWidth: 420
    implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs
            visible: root.title.length > 0 || root.subtitle.length > 0

            Label {
                Layout.fillWidth: true
                visible: root.title.length > 0
                text: root.title
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                visible: root.subtitle.length > 0
                text: root.subtitle
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        Rectangle {
            Layout.fillWidth: true
            visible: root.hint.length > 0
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceAlt
            border.color: Theme.AppTheme.border
            implicitHeight: hintLabel.implicitHeight + (Theme.AppTheme.marginMd * 2)

            Label {
                id: hintLabel

                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginMd
                text: root.hint
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        Item {
            Layout.fillWidth: true
            visible: (root.metrics || []).length > 0
            implicitHeight: metricsFlow.implicitHeight

            Flow {
                id: metricsFlow

                anchors.fill: parent
                spacing: Theme.AppTheme.spacingSm

                Repeater {
                    model: root.metrics || []

                    delegate: AppWidgets.MetricCard {
                        required property var modelData

                        width: root.width >= 720
                            ? Math.max(160, (root.width - Theme.AppTheme.spacingSm) / 2)
                            : root.width
                        label: modelData.label || ""
                        value: modelData.value || ""
                        supportingText: modelData.supportingText || ""
                    }
                }
            }
        }

        Label {
            Layout.fillWidth: true
            visible: (root.metrics || []).length === 0 && (root.rows || []).length === 0 && root.emptyState.length > 0
            text: root.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.rows || []

            delegate: Rectangle {
                id: panelRow

                required property var modelData

                Layout.fillWidth: true
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceAlt
                border.color: Theme.AppTheme.border
                implicitHeight: rowColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)

                ColumnLayout {
                    id: rowColumn

                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingXs

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        Label {
                            Layout.fillWidth: true
                            text: panelRow.modelData.label || ""
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }

                        Label {
                            text: panelRow.modelData.value || ""
                            color: root.toneColor(panelRow.modelData.tone)
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                            horizontalAlignment: Text.AlignRight
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: String(panelRow.modelData.supportingText || "").length > 0
                        text: panelRow.modelData.supportingText || ""
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }
}
