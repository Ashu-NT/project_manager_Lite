pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var costDetail: ({
        "id": "", "statusLabel": "", "description": "", "emptyState": "", "state": {}
    })

    readonly property bool _hasCost: String(root.costDetail.id || "").length > 0

    function _sv(key) {
        const s = root.costDetail.state || {}
        return String(s[key] || "")
    }

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Budget" }

        AppWidgets.EmptyState {
            width: parent.width
            visible: !root._hasCost
            title: "No cost item selected"
            message: root.costDetail.emptyState || "Select a cost item from the list to review its financial detail."
        }

        Item {
            width: parent.width
            visible: root._hasCost
            implicitHeight: _budgetContent.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            ColumnLayout {
                id: _budgetContent
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
                            { "lbl": "Budget",    "val": root._sv("plannedAmountLabel") },
                            { "lbl": "Committed", "val": root._sv("committedAmountLabel") },
                            { "lbl": "Actual",    "val": root._sv("actualAmountLabel") },
                            { "lbl": "Cost Type", "val": root.costDetail.statusLabel || "" }
                        ]

                        delegate: ColumnLayout {
                            id: _budgetCell
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_budgetCell.modelData.lbl)
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_budgetCell.modelData.val)
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

                    Repeater {
                        model: [
                            { "lbl": "Task",     "val": root._sv("taskName") },
                            { "lbl": "Date",     "val": root._sv("incurredDateLabel") },
                            { "lbl": "Currency", "val": root._sv("currency") },
                            { "lbl": "Version",  "val": root._sv("version") }
                        ]

                        delegate: ColumnLayout {
                            id: _metaCell
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_metaCell.modelData.lbl)
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_metaCell.modelData.val) || "-"
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                wrapMode: Text.NoWrap
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: String(root.costDetail.description || "").length > 0
                    text: root.costDetail.description || ""
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
