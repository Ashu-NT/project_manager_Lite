pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Flickable {
    id: root

    property var overviewModel: ({ "metrics": [] })
    property var topAtRiskModel: ({ "title": "Top At-Risk Projects", "subtitle": "", "emptyState": "", "items": [] })
    property var recentActionsModel: ({ "title": "Recent Actions", "emptyState": "", "items": [] })

    contentWidth: width
    contentHeight: _col.implicitHeight + Theme.AppTheme.marginMd * 2
    boundsBehavior: Flickable.StopAtBounds
    clip: true

    ColumnLayout {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingLg

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                text: root.topAtRiskModel.title || "Top At-Risk Projects"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: root.topAtRiskModel.subtitle || ""
                visible: text.length > 0
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                wrapMode: Text.WordWrap
            }

            AppWidgets.EmptyState {
                Layout.fillWidth: true
                visible: (root.topAtRiskModel.items || []).length === 0
                title: "No elevated pressure"
                message: root.topAtRiskModel.emptyState || "No projects currently show elevated delivery pressure."
            }

            Repeater {
                model: root.topAtRiskModel.items || []

                delegate: Rectangle {
                    id: _riskRow
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: _riskRowLayout.implicitHeight + Theme.AppTheme.spacingSm * 2
                    radius: Theme.AppTheme.radiusSm
                    color: Theme.AppTheme.surfaceAlt
                    border.color: Theme.AppTheme.subtleBorder
                    border.width: 1

                    RowLayout {
                        id: _riskRowLayout
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.spacingSm
                        spacing: Theme.AppTheme.spacingSm

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_riskRow.modelData.title || "")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                                elide: Text.ElideRight
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_riskRow.modelData.supportingText || "")
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                elide: Text.ElideRight
                            }
                        }

                        AppWidgets.StatusChip {
                            status: String(_riskRow.modelData.statusLabel || "")
                        }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                text: root.recentActionsModel.title || "Recent Actions"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }

            AppWidgets.ActivityFeed {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.max(160, implicitHeight)
                items: root.recentActionsModel.items || []
                emptyText: root.recentActionsModel.emptyState || "No recent PM actions are available yet."
            }
        }
    }
}
