pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var costPhasing: ({ "items": [] })
    property var sourceAnalytics: ({ "items": [] })
    property var costTypeAnalytics: ({ "items": [] })

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: Theme.AppTheme.spacingLg

        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            label: "Cost Phasing"
        }

        FinancialsCollectionBlock {
            Layout.fillWidth: true
            collection: root.costPhasing
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width >= 900 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingLg
            rowSpacing: Theme.AppTheme.spacingLg

            FinancialsCollectionBlock {
                Layout.fillWidth: true
                collection: root.sourceAnalytics
            }
            FinancialsCollectionBlock {
                Layout.fillWidth: true
                collection: root.costTypeAnalytics
            }
        }
    }
}
