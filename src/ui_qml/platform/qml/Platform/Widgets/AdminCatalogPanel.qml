import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

ColumnLayout {
    id: root

    property string title: ""
    property string summary: ""
    property string createActionLabel: ""
    property bool createEnabled: true
    property bool actionsEnabled: true
    property string primaryActionLabel: ""
    property string secondaryActionLabel: ""
    property string tertiaryActionLabel: ""
    property bool secondaryDanger: false
    property bool tertiaryDanger: false
    property var catalog: ({
        "emptyState": "",
        "items": []
    })

    signal createRequested()
    signal primaryActionRequested(string itemId)
    signal secondaryActionRequested(string itemId)
    signal tertiaryActionRequested(string itemId)

    spacing: 0

    // Section title row — no heavy border box
    RowLayout {
        Layout.fillWidth: true
        Layout.bottomMargin: Theme.AppTheme.spacingXs
        spacing: Theme.AppTheme.spacingMd

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 2

            Label {
                Layout.fillWidth: true
                visible: root.title.length > 0
                text: root.title
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }

            Label {
                Layout.fillWidth: true
                visible: root.summary.length > 0
                text: root.summary
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                wrapMode: Text.WordWrap
            }
        }

        AppControls.PrimaryButton {
            visible: root.createActionLabel.length > 0
            enabled: root.createEnabled
            text: root.createActionLabel
            iconName: "add"
            onClicked: root.createRequested()
        }
    }

    // Divider under header
    Rectangle {
        Layout.fillWidth: true
        height: 1
        color: Theme.AppTheme.divider
        visible: root.title.length > 0
    }

    RecordListCard {
        Layout.fillWidth: true
        title: ""
        subtitle: ""
        emptyState: root.catalog.emptyState || ""
        items: root.catalog.items || []
        actionsEnabled: root.actionsEnabled
        primaryActionLabel: root.primaryActionLabel
        secondaryActionLabel: root.secondaryActionLabel
        tertiaryActionLabel: root.tertiaryActionLabel
        secondaryDanger: root.secondaryDanger
        tertiaryDanger: root.tertiaryDanger

        onPrimaryActionRequested: function(itemId) { root.primaryActionRequested(itemId) }
        onSecondaryActionRequested: function(itemId) { root.secondaryActionRequested(itemId) }
        onTertiaryActionRequested: function(itemId) { root.tertiaryActionRequested(itemId) }
    }
}
