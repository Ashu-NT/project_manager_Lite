pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var commitmentSummaryModel: ({
        "plannedLabel": "", "uncommittedLabel": "", "committedLabel": "",
        "invoicedLabel": "", "paidLabel": "", "exposureLabel": "",
        "paidLabel": "", "commitmentRatePct": 0
    })
    property bool isBusy: false

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Commitments" }

        Item {
            width: parent.width
            implicitHeight: _commitContent.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            ColumnLayout {
                id: _commitContent
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingMd

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 0

                    Repeater {
                        model: [
                            { "lbl": "Uncommitted", "val": root.commitmentSummaryModel.uncommittedLabel || "—" },
                            { "lbl": "Committed",   "val": root.commitmentSummaryModel.committedLabel   || "—" },
                            { "lbl": "Invoiced",    "val": root.commitmentSummaryModel.invoicedLabel    || "—" },
                            { "lbl": "Paid",        "val": root.commitmentSummaryModel.paidLabel        || "—" }
                        ]

                        delegate: ColumnLayout {
                            id: _commitCell
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_commitCell.modelData.lbl)
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_commitCell.modelData.val)
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                                wrapMode: Text.NoWrap
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.AppTheme.divider }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 0

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs
                        AppControls.Label { Layout.fillWidth: true; text: "Exposure"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize }
                        AppControls.Label { Layout.fillWidth: true; text: String(root.commitmentSummaryModel.exposureLabel || "—"); color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.bodySize; font.bold: true }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs
                        AppControls.Label { Layout.fillWidth: true; text: "Commitment Rate"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize }
                        AppControls.Label { Layout.fillWidth: true; text: Number(root.commitmentSummaryModel.commitmentRatePct || 0).toFixed(1) + "%"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.bodySize; font.bold: true }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingXs
                        AppControls.Label { Layout.fillWidth: true; text: "Planned Total"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize }
                        AppControls.Label { Layout.fillWidth: true; text: String(root.commitmentSummaryModel.plannedLabel || "—"); color: Theme.AppTheme.textSecondary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: String(root.commitmentSummaryModel.plannedLabel || "").length === 0
                    text: "Select a project to view the commitment lifecycle breakdown."
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
