pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    property string emptyState: ""
    property string primaryActionLabel: ""
    property string secondaryActionLabel: ""
    property string tertiaryActionLabel: ""
    property bool primaryDanger: false
    property bool secondaryDanger: false
    property bool tertiaryDanger: false
    property bool actionsEnabled: true
    property string selectedItemId: ""
    property var items: []

    signal itemSelected(string itemId)
    signal primaryActionRequested(var itemData)
    signal secondaryActionRequested(var itemData)
    signal tertiaryActionRequested(var itemData)

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitWidth: 420
    implicitHeight: 260

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        ColumnLayout {
            Layout.fillWidth: true
            visible: root.title.length > 0 || root.subtitle.length > 0
            spacing: Theme.AppTheme.spacingXs

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
                visible: root.subtitle.length > 0
                text: root.subtitle
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        Label {
            Layout.fillWidth: true
            visible: root.items.length === 0 && root.emptyState.length > 0
            text: root.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.items

            delegate: Rectangle {
                id: recordCardDelegate
                required property var modelData
                property string statusText: String(recordCardDelegate.modelData.statusLabel || "")
                property string subtitleText: String(recordCardDelegate.modelData.subtitle || "")
                property string supportingTextValue: String(recordCardDelegate.modelData.supportingText || "")
                property string metaTextValue: String(recordCardDelegate.modelData.metaText || "")
                readonly property bool selected: root.selectedItemId.length > 0
                    && root.selectedItemId === String(recordCardDelegate.modelData.id || "")

                Layout.fillWidth: true
                radius: Theme.AppTheme.radiusMd
                color: recordCardDelegate.selected ? Theme.AppTheme.accentSoft : Theme.AppTheme.surfaceAlt
                border.color: recordCardDelegate.selected ? Theme.AppTheme.accent : Theme.AppTheme.border
                implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)

                TapHandler {
                    onTapped: root.itemSelected(String(recordCardDelegate.modelData.id || ""))
                }

                ColumnLayout {
                    id: contentColumn

                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingXs

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        Label {
                            Layout.fillWidth: true
                            text: recordCardDelegate.modelData.title
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }

                        Rectangle {
                            visible: recordCardDelegate.statusText.length > 0
                            radius: Theme.AppTheme.radiusMd
                            color: Theme.AppTheme.surface
                            border.color: Theme.AppTheme.accent
                            implicitHeight: 28
                            implicitWidth: statusLabel.implicitWidth + (Theme.AppTheme.marginMd * 2)

                            Label {
                                id: statusLabel

                                anchors.centerIn: parent
                                text: recordCardDelegate.statusText
                                color: Theme.AppTheme.accent
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                            }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: recordCardDelegate.subtitleText.length > 0
                        text: recordCardDelegate.subtitleText
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: recordCardDelegate.supportingTextValue.length > 0
                        text: recordCardDelegate.supportingTextValue
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: recordCardDelegate.metaTextValue.length > 0
                        text: recordCardDelegate.metaTextValue
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.primaryActionLabel.length > 0
                            || root.secondaryActionLabel.length > 0
                            || root.tertiaryActionLabel.length > 0
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.PrimaryButton {
                            visible: root.primaryActionLabel.length > 0 && recordCardDelegate.modelData.canPrimaryAction
                            enabled: root.actionsEnabled
                            text: root.primaryActionLabel
                            danger: root.primaryDanger
                            onClicked: root.primaryActionRequested(recordCardDelegate.modelData)
                        }

                        AppControls.PrimaryButton {
                            visible: root.secondaryActionLabel.length > 0 && recordCardDelegate.modelData.canSecondaryAction
                            enabled: root.actionsEnabled
                            text: root.secondaryActionLabel
                            danger: root.secondaryDanger
                            onClicked: root.secondaryActionRequested(recordCardDelegate.modelData)
                        }

                        AppControls.PrimaryButton {
                            visible: root.tertiaryActionLabel.length > 0 && recordCardDelegate.modelData.canTertiaryAction
                            enabled: root.actionsEnabled
                            text: root.tertiaryActionLabel
                            danger: root.tertiaryDanger
                            onClicked: root.tertiaryActionRequested(recordCardDelegate.modelData)
                        }

                        Item {
                            Layout.fillWidth: true
                        }
                    }
                }
            }
        }
    }
}
