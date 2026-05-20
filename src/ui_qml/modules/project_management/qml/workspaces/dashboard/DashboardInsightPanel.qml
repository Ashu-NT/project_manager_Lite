pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property string hint: ""
    property string emptyState: ""
    property var metrics: []
    property var rows: []

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

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        Label {
            Layout.fillWidth: true
            visible: root.hint.length > 0
            text: root.hint
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: (root.metrics || []).length === 0
                && (root.rows || []).length === 0
                && root.emptyState.length > 0
            title: root.emptyState
        }

        GridLayout {
            Layout.fillWidth: true
            visible: (root.metrics || []).length > 0
            columns: width >= 420 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            Repeater {
                model: root.metrics || []

                delegate: ColumnLayout {
                    id: metricItem
                    required property var modelData

                    Layout.fillWidth: true
                    spacing: 1

                    Label {
                        Layout.fillWidth: true
                        text: metricItem.modelData.value || ""
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    Label {
                        Layout.fillWidth: true
                        text: metricItem.modelData.label || ""
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: String(metricItem.modelData.supportingText || "").length > 0
                        text: metricItem.modelData.supportingText || ""
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: (root.rows || []).length > 0
            spacing: 0

            Repeater {
                model: root.rows || []

                delegate: ColumnLayout {
                    id: summaryRow
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

                            Label {
                                Layout.fillWidth: true
                                text: summaryRow.modelData.label || ""
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }

                            Label {
                                Layout.fillWidth: true
                                visible: String(summaryRow.modelData.supportingText || "").length > 0
                                text: summaryRow.modelData.supportingText || ""
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                wrapMode: Text.WordWrap
                            }
                        }

                        Label {
                            text: summaryRow.modelData.value || ""
                            color: root.toneColor(summaryRow.modelData.tone)
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                            horizontalAlignment: Text.AlignRight
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 1
                        color: Theme.AppTheme.divider
                    }
                }
            }
        }
    }
}
