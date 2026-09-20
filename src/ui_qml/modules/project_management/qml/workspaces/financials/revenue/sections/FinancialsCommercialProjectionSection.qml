pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var projection: ({ "id": "", "title": "", "subtitle": "", "statusLabel": "", "fields": [] })

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            label: "Projected Commercial Revenue/Margin"
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            tone: "info"
            message: root.projection.subtitle || "Managerial projection only; Accounting remains authoritative."
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width >= 900 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingMd

            Repeater {
                model: root.projection.fields || []
                delegate: Rectangle {
                    id: projectionCard
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: projectionContent.implicitHeight + Theme.AppTheme.spacingLg * 2
                    radius: Theme.AppTheme.radiusMd
                    color: Theme.AppTheme.surfaceRaised
                    border.width: 1
                    border.color: Theme.AppTheme.subtleBorder

                    ColumnLayout {
                        id: projectionContent
                        anchors.fill: parent
                        anchors.margins: Theme.AppTheme.spacingLg
                        spacing: Theme.AppTheme.spacingXs

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(projectionCard.modelData.label || "")
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(projectionCard.modelData.value || "-")
                            color: Theme.AppTheme.textPrimary
                            font.pixelSize: Theme.AppTheme.sectionTitleSize
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: text.length > 0
                            text: String(projectionCard.modelData.supportingText || "")
                            color: Theme.AppTheme.textSecondary
                            font.pixelSize: Theme.AppTheme.captionSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }
}
