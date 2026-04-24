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
    property bool primaryDanger: false
    property bool secondaryDanger: false
    property bool actionsEnabled: true
    property var items: []

    signal primaryActionRequested(string itemId)
    signal secondaryActionRequested(string itemId)

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
                required property var modelData

                Layout.fillWidth: true
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceAlt
                border.color: Theme.AppTheme.border
                implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginMd * 2)

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
                            text: modelData.title
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }

                        Rectangle {
                            visible: modelData.statusLabel.length > 0
                            radius: Theme.AppTheme.radiusMd
                            color: Theme.AppTheme.accentSoft
                            border.color: Theme.AppTheme.accent
                            implicitHeight: 28
                            implicitWidth: statusLabel.implicitWidth + (Theme.AppTheme.marginMd * 2)

                            Label {
                                id: statusLabel

                                anchors.centerIn: parent
                                text: modelData.statusLabel
                                color: Theme.AppTheme.accent
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                            }
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: modelData.subtitle.length > 0
                        text: modelData.subtitle
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: modelData.supportingText.length > 0
                        text: modelData.supportingText
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: modelData.metaText.length > 0
                        text: modelData.metaText
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: root.primaryActionLabel.length > 0 || root.secondaryActionLabel.length > 0
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.PrimaryButton {
                            visible: root.primaryActionLabel.length > 0 && modelData.canPrimaryAction
                            enabled: root.actionsEnabled
                            text: root.primaryActionLabel
                            danger: root.primaryDanger
                            onClicked: root.primaryActionRequested(modelData.id)
                        }

                        AppControls.PrimaryButton {
                            visible: root.secondaryActionLabel.length > 0 && modelData.canSecondaryAction
                            enabled: root.actionsEnabled
                            text: root.secondaryActionLabel
                            danger: root.secondaryDanger
                            onClicked: root.secondaryActionRequested(modelData.id)
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
