import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

ColumnLayout {
    id: root

    property var cashflowModel: ({})
    property var ledgerModel: ({})
    property var sourceAnalyticsModel: ({})
    property var costTypeAnalyticsModel: ({})
    property var notes: []

    spacing: Theme.AppTheme.spacingMd

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 1180 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingMd

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.cashflowModel.title || "Cashflow"
            subtitle: root.cashflowModel.subtitle || ""
            emptyState: root.cashflowModel.emptyState || ""
            items: root.cashflowModel.items || []
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.ledgerModel.title || "Ledger Trail"
            subtitle: root.ledgerModel.subtitle || ""
            emptyState: root.ledgerModel.emptyState || ""
            items: root.ledgerModel.items || []
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.sourceAnalyticsModel.title || "Source Breakdown"
            subtitle: root.sourceAnalyticsModel.subtitle || ""
            emptyState: root.sourceAnalyticsModel.emptyState || ""
            items: root.sourceAnalyticsModel.items || []
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: root.costTypeAnalyticsModel.title || "Cost Type Breakdown"
            subtitle: root.costTypeAnalyticsModel.subtitle || ""
            emptyState: root.costTypeAnalyticsModel.emptyState || ""
            items: root.costTypeAnalyticsModel.items || []
        }
    }

    Rectangle {
        Layout.fillWidth: true
        visible: (root.notes || []).length > 0
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        border.color: Theme.AppTheme.border
        implicitHeight: notesColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

        ColumnLayout {
            id: notesColumn

            anchors.fill: parent
            anchors.margins: Theme.AppTheme.marginLg
            spacing: Theme.AppTheme.spacingSm

            Label {
                Layout.fillWidth: true
                text: "Finance Notes"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }

            Repeater {
                model: root.notes || []

                delegate: Label {
                    required property var modelData

                    Layout.fillWidth: true
                    text: "- " + String(modelData || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
