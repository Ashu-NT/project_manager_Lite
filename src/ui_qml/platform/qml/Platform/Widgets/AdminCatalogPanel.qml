import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
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

    spacing: Theme.AppTheme.spacingSm

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs

            Label {
                Layout.fillWidth: true
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
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        AppControls.PrimaryButton {
            visible: root.createActionLabel.length > 0
            enabled: root.createEnabled
            text: root.createActionLabel
            onClicked: root.createRequested()
        }
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

        onPrimaryActionRequested: function(itemId) {
            root.primaryActionRequested(itemId)
        }

        onSecondaryActionRequested: function(itemId) {
            root.secondaryActionRequested(itemId)
        }

        onTertiaryActionRequested: function(itemId) {
            root.tertiaryActionRequested(itemId)
        }
    }
}
