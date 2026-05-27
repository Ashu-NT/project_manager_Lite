pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property string title: ""
    property string subtitle: ""
    property string hint: ""
    property string emptyState: ""
    property var rows: []
    property var metrics: []

    function toneColor(tone) {
        switch (String(tone || "")) {
        case "danger":  return Theme.AppTheme.danger
        case "warning": return Theme.AppTheme.warning
        case "success": return Theme.AppTheme.success
        case "accent":  return Theme.AppTheme.accent
        default:        return Theme.AppTheme.textPrimary
        }
    }

    implicitWidth: 420
    implicitHeight: panelLayout.implicitHeight

    ColumnLayout {
        id: panelLayout
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2
            visible: root.title.length > 0 || root.subtitle.length > 0

            AppControls.Label {
                Layout.fillWidth: true
                visible: root.title.length > 0
                text: root.title
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: root.subtitle.length > 0
                text: root.subtitle
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: root.hint.length > 0
            text: root.hint
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
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

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: (root.metrics || []).length === 0
                && (root.rows || []).length === 0
                && root.emptyState.length > 0
            title: root.emptyState
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            visible: (root.rows || []).length > 0

            Repeater {
                model: root.rows || []

                delegate: ColumnLayout {
                    id: panelRow
                    required property var modelData

                    Layout.fillWidth: true
                    spacing: 2

                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: Theme.AppTheme.spacingXs
                        Layout.bottomMargin: Theme.AppTheme.spacingXs
                        spacing: Theme.AppTheme.spacingSm

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: panelRow.modelData.label || ""
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                visible: String(panelRow.modelData.supportingText || "").length > 0
                                text: panelRow.modelData.supportingText || ""
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.WordWrap
                            }
                        }

                        AppControls.Label {
                            text: panelRow.modelData.value || ""
                            color: root.toneColor(panelRow.modelData.tone)
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                            horizontalAlignment: Text.AlignRight
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: Theme.AppTheme.divider
                    }
                }
            }
        }
    }
}
