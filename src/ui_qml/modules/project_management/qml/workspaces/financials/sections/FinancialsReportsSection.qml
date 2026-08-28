pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var reportBasis: ({ "title": "", "statusLabel": "", "emptyState": "", "fields": [] })
    property var reportDefinitions: ({ "items": [] })

    implicitHeight: _column.implicitHeight

    ColumnLayout {
        id: _column
        width: parent.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Reports" }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: (root.reportBasis.fields || []).length === 0
            title: "No report basis"
            message: root.reportBasis.emptyState || "Select a project before exporting."
        }

        Rectangle {
            Layout.fillWidth: true
            visible: (root.reportBasis.fields || []).length > 0
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceAlt
            border.width: 1
            border.color: Theme.AppTheme.subtleBorder
            implicitHeight: _basisColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

            ColumnLayout {
                id: _basisColumn
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingSm

                AppControls.Label {
                    Layout.fillWidth: true
                    text: root.reportBasis.title || "Canonical Financial Report"
                    color: Theme.AppTheme.textPrimary
                    font.pixelSize: Theme.AppTheme.sectionTitleSize
                    font.bold: true
                }
                AppControls.Label {
                    Layout.fillWidth: true
                    text: root.reportBasis.statusLabel || ""
                    color: Theme.AppTheme.accent
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                }
                Repeater {
                    model: root.reportBasis.fields || []
                    delegate: RowLayout {
                        id: _basisRow
                        required property var modelData
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingMd
                        AppControls.Label {
                            Layout.preferredWidth: 180
                            text: String(_basisRow.modelData.label || "")
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.captionSize
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_basisRow.modelData.value || "")
                            color: Theme.AppTheme.textPrimary
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: (root.reportBasis.fields || []).length > 0
            tone: "info"
            message: "Excel and PDF are generated from authoritative Finance reads with reconciliation controls, explicit version basis, and permission-filtered source sections."
        }

        FinancialsCollectionBlock {
            Layout.fillWidth: true
            collection: root.reportDefinitions
        }
    }
}
