pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var workOrderDetail: ({
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
    signal statusRequested()

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
                    text: root.workOrderDetail.title || "Work Order Detail"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    text: root.workOrderDetail.subtitle || "Select a work order to inspect execution scope, planning state, and lifecycle updates."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            Rectangle {
                visible: String(root.workOrderDetail.statusLabel || "").length > 0
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.accentSoft
                border.color: Theme.AppTheme.accent
                implicitHeight: 30
                implicitWidth: statusLabel.implicitWidth + (Theme.AppTheme.marginMd * 2)

                Label {
                    id: statusLabel
                    anchors.centerIn: parent
                    text: root.workOrderDetail.statusLabel
                    color: Theme.AppTheme.accent
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
            }
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.workOrderDetail.emptyState || "").length > 0 && String(root.workOrderDetail.id || "").length === 0
            text: root.workOrderDetail.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: String(root.workOrderDetail.id || "").length > 0
            text: root.workOrderDetail.description || ""
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.workOrderDetail.fields || []

            delegate: Rectangle {
                id: fieldCard
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
                        text: String(fieldCard.modelData.label || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: true
                    }

                    Label {
                        Layout.fillWidth: true
                        text: String(fieldCard.modelData.value || "")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        wrapMode: Text.WordWrap
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: String(fieldCard.modelData.supportingText || "").length > 0
                        text: String(fieldCard.modelData.supportingText || "")
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
            visible: String(root.workOrderDetail.id || "").length > 0
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                text: "Edit"
                enabled: !root.isBusy && !!(root.workOrderDetail.state && root.workOrderDetail.state.canPrimaryAction)
                onClicked: root.editRequested()
            }

            AppControls.PrimaryButton {
                text: "Status"
                enabled: !root.isBusy && !!(root.workOrderDetail.state && root.workOrderDetail.state.canSecondaryAction)
                onClicked: root.statusRequested()
            }

            Item {
                Layout.fillWidth: true
            }
        }
    }
}
