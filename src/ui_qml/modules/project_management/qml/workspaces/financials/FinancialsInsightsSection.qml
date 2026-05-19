import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
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

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            title: root.cashflowModel.title || "Cashflow"
            implicitHeight: cashflowList.implicitHeight + 32 + Theme.AppTheme.spacingMd

            ProjectManagementWidgets.RecordListCard {
                id: cashflowList
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.spacingSm
                title: ""
                subtitle: root.cashflowModel.subtitle || ""
                emptyState: root.cashflowModel.emptyState || ""
                items: root.cashflowModel.items || []
            }
        }

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            title: root.ledgerModel.title || "Ledger Trail"
            implicitHeight: ledgerList.implicitHeight + 32 + Theme.AppTheme.spacingMd

            ProjectManagementWidgets.RecordListCard {
                id: ledgerList
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.spacingSm
                title: ""
                subtitle: root.ledgerModel.subtitle || ""
                emptyState: root.ledgerModel.emptyState || ""
                items: root.ledgerModel.items || []
            }
        }

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            title: root.sourceAnalyticsModel.title || "Source Breakdown"
            implicitHeight: sourceList.implicitHeight + 32 + Theme.AppTheme.spacingMd

            ProjectManagementWidgets.RecordListCard {
                id: sourceList
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.spacingSm
                title: ""
                subtitle: root.sourceAnalyticsModel.subtitle || ""
                emptyState: root.sourceAnalyticsModel.emptyState || ""
                items: root.sourceAnalyticsModel.items || []
            }
        }

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            title: root.costTypeAnalyticsModel.title || "Cost Type Breakdown"
            implicitHeight: costTypeList.implicitHeight + 32 + Theme.AppTheme.spacingMd

            ProjectManagementWidgets.RecordListCard {
                id: costTypeList
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.spacingSm
                title: ""
                subtitle: root.costTypeAnalyticsModel.subtitle || ""
                emptyState: root.costTypeAnalyticsModel.emptyState || ""
                items: root.costTypeAnalyticsModel.items || []
            }
        }
    }

    AppWidgets.SectionCard {
        Layout.fillWidth: true
        visible: (root.notes || []).length > 0
        title: "Finance Notes"
        implicitHeight: notesContent.implicitHeight + 32 + Theme.AppTheme.spacingMd

        ColumnLayout {
            id: notesContent
            anchors.fill: parent
            anchors.margins: Theme.AppTheme.spacingMd
            spacing: Theme.AppTheme.spacingSm

            Repeater {
                model: root.notes || []

                delegate: Label {
                    required property var modelData

                    Layout.fillWidth: true
                    text: "• " + String(modelData || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
