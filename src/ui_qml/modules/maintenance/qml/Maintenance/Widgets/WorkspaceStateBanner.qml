import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

ColumnLayout {
    id: root

    property bool isLoading: false
    property bool isBusy: false
    property string errorMessage: ""
    property string feedbackMessage: ""

    spacing: Theme.AppTheme.spacingXs
    visible: root.isLoading || root.isBusy || root.errorMessage.length > 0 || root.feedbackMessage.length > 0

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: (root.isLoading || root.isBusy) && root.errorMessage.length === 0
        tone: "info"
        message: root.isBusy ? "Saving maintenance changes..." : "Loading maintenance workspace..."
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.errorMessage.length > 0
        tone: "danger"
        message: root.errorMessage
    }

    AppWidgets.InlineMessage {
        Layout.fillWidth: true
        visible: root.feedbackMessage.length > 0 && root.errorMessage.length === 0
        tone: "success"
        message: root.feedbackMessage
    }
}
