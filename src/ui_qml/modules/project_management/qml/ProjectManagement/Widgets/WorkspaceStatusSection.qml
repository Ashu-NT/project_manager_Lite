import QtQuick
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Flow {
    id: root

    property string migrationStatus: ""
    property string legacyRuntimeStatus: ""
    property string architectureStatus: "Presenter-backed shell"
    property string architectureSummary: "Typed QML bindings are ready for the next workflow migration."
    property real cardWidth: 280

    spacing: Theme.AppTheme.spacingMd

    AppWidgets.MetricCard {
        width: root.cardWidth
        label: "Migration status"
        value: root.migrationStatus
        supportingText: root.legacyRuntimeStatus
    }

    AppWidgets.MetricCard {
        width: root.cardWidth
        label: "Boundary status"
        value: root.architectureStatus
        supportingText: root.architectureSummary
    }
}
