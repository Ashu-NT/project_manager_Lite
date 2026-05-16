pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property string emptyTitle: "No record selected"
    property string primaryActionLabel: "Edit"
    property string secondaryActionLabel: "Toggle Active"
    property var detailModel: ({
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

    signal primaryActionRequested()
    signal secondaryActionRequested()

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

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Label {
                    Layout.fillWidth: true
                    text: root.detailModel.id ? (root.detailModel.title || root.emptyTitle) : root.emptyTitle
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    text: root.detailModel.subtitle || root.detailModel.emptyState || ""
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            Rectangle {
                visible: String(root.detailModel.statusLabel || "").length > 0
                radius: Theme.AppTheme.radiusMd
                color: Theme.AppTheme.accentSoft
                border.color: Theme.AppTheme.accent
                implicitHeight: 30
                implicitWidth: statusLabel.implicitWidth + (Theme.AppTheme.marginMd * 2)

                Label {
                    id: statusLabel
                    anchors.centerIn: parent
                    text: root.detailModel.statusLabel
                    color: Theme.AppTheme.accent
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
            }
        }

        Label {
            Layout.fillWidth: true
            visible: !root.detailModel.id && String(root.detailModel.emptyState || "").length > 0
            text: root.detailModel.emptyState
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: !!root.detailModel.id
            text: root.detailModel.description || ""
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.detailModel.fields || []

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
            visible: !!root.detailModel.id
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                visible: root.primaryActionLabel.length > 0
                text: root.primaryActionLabel
                enabled: !root.isBusy && !!(root.detailModel.state && root.detailModel.state.canPrimaryAction)
                onClicked: root.primaryActionRequested()
            }

            AppControls.PrimaryButton {
                visible: root.secondaryActionLabel.length > 0
                text: root.secondaryActionLabel
                enabled: !root.isBusy && !!(root.detailModel.state && root.detailModel.state.canSecondaryAction)
                onClicked: root.secondaryActionRequested()
            }

            Item {
                Layout.fillWidth: true
            }
        }
    }
}
