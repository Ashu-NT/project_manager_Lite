pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var costPhasing: ({ "items": [] })
    property var basis: ({ "fields": [] })
    property string dateFrom: ""
    property string dateTo: ""
    property string granularity: "month"
    signal presetRequested(int months, string granularity)

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: Theme.AppTheme.spacingLg

        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            label: "Cost Phasing"
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                Layout.fillWidth: true
                text: "Range " + root.dateFrom + " to " + root.dateTo
                color: Theme.AppTheme.textMuted
                font.pixelSize: Theme.AppTheme.captionSize
                elide: Text.ElideRight
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                AppControls.Button { text: "6 months"; onClicked: root.presetRequested(6, root.granularity) }
                AppControls.Button { text: "12 months"; onClicked: root.presetRequested(12, root.granularity) }
                AppControls.Button { text: "24 months"; onClicked: root.presetRequested(24, root.granularity) }
                AppControls.Button {
                    text: root.granularity === "quarter" ? "Quarterly" : "Monthly"
                    onClicked: root.presetRequested(0, root.granularity === "quarter" ? "month" : "quarter")
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            visible: (root.basis.fields || []).length > 0
            implicitHeight: _basisFlow.implicitHeight + Theme.AppTheme.spacingMd * 2
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceAlt
            border.width: 1
            border.color: Theme.AppTheme.subtleBorder

            Flow {
                id: _basisFlow
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingLg

                Repeater {
                    model: root.basis.fields || []
                    delegate: AppControls.Label {
                        required property var modelData
                        text: String(modelData.label || "") + ": " + String(modelData.value || "")
                        color: Theme.AppTheme.textMuted
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                }
            }
        }

        FinancialsCollectionBlock {
            Layout.fillWidth: true
            collection: root.costPhasing
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            tone: "info"
            message: "Cost Phasing stages planned, committed, posted actual, forecast, and exposure. It does not represent receipts, supplier payments, bank settlement, liquidity, AR, or AP."
        }
    }
}
