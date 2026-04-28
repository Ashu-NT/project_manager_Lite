import QtQuick
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Flow {
    id: root

    property var metrics: []

    spacing: Theme.AppTheme.spacingMd

    Repeater {
        model: root.metrics || []

        delegate: AppWidgets.MetricCard {
            required property var modelData

            width: 210
            label: modelData.label
            value: modelData.value
            supportingText: modelData.supportingText
        }
    }
}
