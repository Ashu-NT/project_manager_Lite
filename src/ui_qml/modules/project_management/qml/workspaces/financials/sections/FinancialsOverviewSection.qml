pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var overview: ({ "title": "Financials", "subtitle": "", "metrics": [] })
    readonly property var _metrics: root.overview.metrics || []

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            label: "Financial Overview"
        }

        AppControls.Label {
            Layout.fillWidth: true
            text: root.overview.subtitle || ""
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width >= 1050 ? 4 : (width >= 640 ? 2 : 1)
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingMd

            Repeater {
                model: root._metrics

                delegate: Rectangle {
                    id: metricCard
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.minimumWidth: 220
                    implicitHeight: metricContent.implicitHeight + Theme.AppTheme.spacingLg * 2
                    radius: Theme.AppTheme.radiusMd
                    color: Theme.AppTheme.surfaceRaised
                    border.width: 1
                    border.color: Theme.AppTheme.subtleBorder

                    ColumnLayout {
                        id: metricContent
                        anchors.fill: parent
                        anchors.margins: Theme.AppTheme.spacingLg
                        spacing: Theme.AppTheme.spacingXs

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(metricCard.modelData.label || "")
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(metricCard.modelData.value || "-")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.subtitleSize
                            font.bold: true
                            elide: Text.ElideRight
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(metricCard.modelData.supportingText || "")
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }
}
