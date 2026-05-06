pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var tasksModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property string selectedTaskId: ""
    property var selectedTaskIds: []
    property bool isBusy: false

    signal taskSelected(string taskId)
    signal taskSelectionToggled(string taskId, bool selected)
    signal editRequested(var taskData)
    signal progressRequested(var taskData)
    signal deleteRequested(var taskData)

    function isTaskSelected(taskId) {
        for (var index = 0; index < root.selectedTaskIds.length; index += 1) {
            if (String(root.selectedTaskIds[index] || "") === String(taskId || "")) {
                return true
            }
        }
        return false
    }

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs

            Label {
                Layout.fillWidth: true
                text: root.tasksModel.title || "Task Catalog"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                text: root.tasksModel.subtitle || ""
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                visible: text.length > 0
                wrapMode: Text.WordWrap
            }
        }

        Label {
            Layout.fillWidth: true
            visible: (root.tasksModel.items || []).length === 0 && String(root.tasksModel.emptyState || "").length > 0
            text: root.tasksModel.emptyState || ""
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.tasksModel.items || []

            delegate: Rectangle {
                id: recordCardDelegate

                required property var modelData
                property string itemId: String(recordCardDelegate.modelData.id || "")
                property string statusText: String(recordCardDelegate.modelData.statusLabel || "")
                property string subtitleText: String(recordCardDelegate.modelData.subtitle || "")
                property string supportingTextValue: String(recordCardDelegate.modelData.supportingText || "")
                property string metaTextValue: String(recordCardDelegate.modelData.metaText || "")
                readonly property bool selected: root.selectedTaskId.length > 0
                    && root.selectedTaskId === recordCardDelegate.itemId

                Layout.fillWidth: true
                radius: Theme.AppTheme.radiusMd
                color: recordCardDelegate.selected ? Theme.AppTheme.accentSoft : Theme.AppTheme.surfaceAlt
                border.color: recordCardDelegate.selected ? Theme.AppTheme.accent : Theme.AppTheme.border
                implicitHeight: contentLayout.implicitHeight + (Theme.AppTheme.marginMd * 2)

                TapHandler {
                    onTapped: root.taskSelected(recordCardDelegate.itemId)
                }

                ColumnLayout {
                    id: contentLayout

                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingXs

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        CheckBox {
                            checked: root.isTaskSelected(recordCardDelegate.itemId)
                            enabled: !root.isBusy
                            onToggled: root.taskSelectionToggled(recordCardDelegate.itemId, checked)
                        }

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
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.PrimaryButton {
                            visible: recordCardDelegate.modelData.canPrimaryAction
                            enabled: !root.isBusy
                            text: "Edit"
                            onClicked: root.editRequested(recordCardDelegate.modelData)
                        }

                        AppControls.PrimaryButton {
                            visible: recordCardDelegate.modelData.canSecondaryAction
                            enabled: !root.isBusy
                            text: "Progress"
                            onClicked: root.progressRequested(recordCardDelegate.modelData)
                        }

                        AppControls.PrimaryButton {
                            visible: recordCardDelegate.modelData.canTertiaryAction
                            enabled: !root.isBusy
                            text: "Delete"
                            danger: true
                            onClicked: root.deleteRequested(recordCardDelegate.modelData)
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
