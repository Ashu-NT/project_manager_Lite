import QtQuick
import App.Theme 1.0 as Theme
import Platform.Widgets 1.0 as PlatformWidgets

Flow {
    id: root

    property var sections: []

    spacing: Theme.AppTheme.spacingMd

    Repeater {
        model: root.sections || []

        delegate: PlatformWidgets.OverviewSectionCard {
            required property var modelData

            width: 320
            title: modelData.title
            rows: modelData.rows
            emptyState: modelData.emptyState
        }
    }
}
