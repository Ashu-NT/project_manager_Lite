pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var costDetail: ({
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
    property var detailPage: null

    signal editRequested()
    signal deleteRequested()

    implicitHeight: _mainCol.implicitHeight

    Column {
        id: _mainCol
        width: parent.width
        spacing: 0

        // ── Section 0: Details ───────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 0; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Details" }

        Item {
            width: parent.width
            implicitHeight: detailsContent.implicitHeight + Theme.AppTheme.spacingMd * 2

            ColumnLayout {
                id: detailsContent
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                anchors.bottomMargin: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs

                        Label {
                            Layout.fillWidth: true
                            text: root.costDetail.title || "Cost Detail"
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            font.bold: true
                            wrapMode: Text.WordWrap
                        }

                        Label {
                            Layout.fillWidth: true
                            text: root.costDetail.subtitle || "Select a cost item to inspect detail."
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            wrapMode: Text.WordWrap
                        }
                    }

                    AppWidgets.StatusChip {
                        visible: String(root.costDetail.statusLabel || "").length > 0
                        status: root.costDetail.statusLabel || ""
                    }
                }

                Label {
                    Layout.fillWidth: true
                    visible: String(root.costDetail.emptyState || "").length > 0
                        && String(root.costDetail.id || "").length === 0
                    text: root.costDetail.emptyState
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    wrapMode: Text.WordWrap
                }

                Label {
                    Layout.fillWidth: true
                    visible: String(root.costDetail.id || "").length > 0
                    text: root.costDetail.description || ""
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: root.costDetail.fields || []

                    delegate: Rectangle {
                        id: fieldCard
                        required property var modelData

                        Layout.fillWidth: true
                        radius: Theme.AppTheme.radiusMd
                        color: Theme.AppTheme.surfaceAlt
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
                    visible: String(root.costDetail.id || "").length > 0
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.PrimaryButton {
                        text: "Edit"
                        enabled: !root.isBusy
                        onClicked: root.editRequested()
                    }

                    AppControls.PrimaryButton {
                        text: "Delete"
                        danger: true
                        enabled: !root.isBusy
                        onClicked: root.deleteRequested()
                    }

                    Item {
                        Layout.fillWidth: true
                    }
                }
            }
        }

        // ── Section 1: Timeline ──────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 1; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Timeline" }

        Rectangle {
            width: parent.width
            height: 80
            color: "transparent"

            Label {
                anchors.centerIn: parent
                text: "Cost timeline and schedule coming soon"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
            }
        }

        // ── Section 2: Notes ─────────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 2; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Notes" }

        Rectangle {
            width: parent.width
            height: 80
            color: "transparent"

            Label {
                anchors.centerIn: parent
                text: "Cost notes and comments coming soon"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
            }
        }
    }
}
