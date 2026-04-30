import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var taskDetail: ({
        "id": "",
        "title": "",
        "statusLabel": "",
        "subtitle": "",
        "description": "",
        "emptyState": "",
        "fields": [],
        "state": {}
    })
    property bool isBusy: false

    signal editRequested()
    signal progressRequested()
    signal deleteRequested()

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: contentColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    Layout.fillWidth: true
                    text: root.taskDetail.title || "Task Detail"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    text: root.taskDetail.subtitle || "Select a task to inspect details."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            Rectangle {
                visible: String(root.taskDetail.statusLabel || "").length > 0
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.accentSoft
                border.color: Theme.AppTheme.accent
                implicitHeight: 30
                implicitWidth: statusLabel.implicitWidth + (Theme.AppTheme.marginMd * 2)

                Label {
                    id: statusLabel

                    anchors.centerIn: parent
                    text: root.taskDetail.statusLabel
                    color: Theme.AppTheme.accent
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
            }
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.taskDetail.emptyState || "").length > 0 && String(root.taskDetail.id || "").length === 0
            text: root.taskDetail.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.taskDetail.id || "").length > 0
            text: root.taskDetail.description || ""
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.taskDetail.fields || []

            delegate: Rectangle {
                required property var modelData

                Layout.fillWidth: true
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.surfaceAlt
                border.color: Theme.AppTheme.border
                implicitHeight: fieldLayout.implicitHeight + (Theme.AppTheme.marginMd * 2)

                ColumnLayout {
                    id: fieldLayout

                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingXs

                    Label {
                        Layout.fillWidth: true
                        text: String(modelData.label || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: true
                    }

                    Label {
                        Layout.fillWidth: true
                        text: String(modelData.value || "")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: String(modelData.supportingText || "").length > 0
                        text: String(modelData.supportingText || "")
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            visible: String(root.taskDetail.id || "").length > 0
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                text: "Edit"
                enabled: !root.isBusy
                onClicked: root.editRequested()
            }

            AppControls.PrimaryButton {
                text: "Progress"
                enabled: !root.isBusy
                onClicked: root.progressRequested()
            }

            AppControls.PrimaryButton {
                text: "Delete"
                danger: true
                enabled: !root.isBusy
                onClicked: root.deleteRequested()
            }

            Item { Layout.fillWidth: true }
        }
    }
}
