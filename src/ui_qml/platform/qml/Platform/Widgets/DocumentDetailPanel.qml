import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property var details: ({
        "hasSelection": false,
        "title": "Select a document",
        "summary": "",
        "badges": [],
        "metadataRows": [],
        "notes": ""
    })
    property var previewState: ({
        "statusLabel": "No document selected",
        "summary": "",
        "canOpen": false,
        "openLabel": "Open Source",
        "openTargetUrl": ""
    })
    property bool actionsEnabled: true

    signal openRequested(string targetUrl)

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitWidth: 420
    implicitHeight: detailColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: detailColumn

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: root.details.title || "Select a document"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.titleSize
            font.bold: true
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            text: root.details.summary || "Select a document to inspect metadata and preview state."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm
            visible: (root.details.badges || []).length > 0

            Repeater {
                model: root.details.badges || []

                delegate: Rectangle {
                    required property var modelData

                    radius: Theme.AppTheme.radiusMd
                    color: Theme.AppTheme.surfaceAlt
                    border.color: Theme.AppTheme.border
                    implicitHeight: badgeLabel.implicitHeight + Theme.AppTheme.marginSm * 2
                    implicitWidth: badgeLabel.implicitWidth + Theme.AppTheme.marginMd * 2

                    Label {
                        id: badgeLabel

                        anchors.centerIn: parent
                        text: String(modelData.label || "") + ": " + String(modelData.value || "")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: true
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.surfaceAlt
            border.color: Theme.AppTheme.border
            implicitHeight: previewColumn.implicitHeight + Theme.AppTheme.marginMd * 2

            ColumnLayout {
                id: previewColumn

                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    Label {
                        Layout.fillWidth: true
                        text: "Preview"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                    }

                    Rectangle {
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.accentSoft
                        border.color: Theme.AppTheme.accent
                        implicitHeight: previewStatusLabel.implicitHeight + Theme.AppTheme.marginSm * 2
                        implicitWidth: previewStatusLabel.implicitWidth + Theme.AppTheme.marginMd * 2

                        Label {
                            id: previewStatusLabel

                            anchors.centerIn: parent
                            text: root.previewState.statusLabel || "No document selected"
                            color: Theme.AppTheme.accent
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                        }
                    }
                }

                Label {
                    Layout.fillWidth: true
                    text: root.previewState.summary || ""
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                AppControls.PrimaryButton {
                    visible: true
                    enabled: root.actionsEnabled
                        && Boolean(root.previewState.canOpen)
                        && String(root.previewState.openTargetUrl || "").length > 0
                    text: root.previewState.openLabel || "Open Source"
                    onClicked: root.openRequested(String(root.previewState.openTargetUrl || ""))
                }
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: width > 520 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm
            visible: (root.details.metadataRows || []).length > 0

            Repeater {
                model: root.details.metadataRows || []

                delegate: ColumnLayout {
                    required property var modelData

                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingXs

                    Label {
                        Layout.fillWidth: true
                        text: modelData.label || ""
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: true
                    }

                    Label {
                        Layout.fillWidth: true
                        text: modelData.value || "-"
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs

            Label {
                Layout.fillWidth: true
                text: "Notes"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }

            Label {
                Layout.fillWidth: true
                text: String(root.details.notes || "").length > 0 ? root.details.notes : "No notes recorded."
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }
    }
}
