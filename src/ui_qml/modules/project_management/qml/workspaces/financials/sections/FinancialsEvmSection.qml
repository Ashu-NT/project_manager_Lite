pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var basis: ({ "fields": [] })
    property var metrics: ({ "items": [] })

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Earned Value Management" }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.basis.emptyState || "").length > 0
            tone: "warning"
            message: String(root.basis.emptyState || "")
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width >= 900 ? 3 : width >= 620 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingMd

            Repeater {
                model: root.metrics.items || []
                delegate: Rectangle {
                    id: metricCard
                    required property var modelData
                    Layout.fillWidth: true
                    Layout.preferredHeight: 126
                    radius: Theme.AppTheme.radiusMd
                    color: Theme.AppTheme.surfaceAlt
                    border.width: 1
                    border.color: Theme.AppTheme.subtleBorder

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingXs

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(metricCard.modelData.title || "")
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.captionSize
                            wrapMode: Text.WordWrap
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(metricCard.modelData.statusLabel || "Not available")
                            color: Theme.AppTheme.textPrimary
                            font.pixelSize: Theme.AppTheme.sectionTitleSize
                            font.bold: true
                            elide: Text.ElideRight
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: String(metricCard.modelData.subtitle || "")
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.captionSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            tone: "info"
            message: "Isolates the existing EVM authority. Its known binary-float precision and no-duration fallback defects remain explicit R6E debt; no formula is recalculated in QML."
        }
    }
}
