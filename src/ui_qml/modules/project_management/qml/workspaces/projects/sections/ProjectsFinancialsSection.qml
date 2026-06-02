pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var projectDetail: ({ "id": "", "state": {} })
    property var sectionErrors: ({})

    readonly property bool _hasProject: String(root.projectDetail.id || "").length > 0

    function _sv(key) {
        const s = root.projectDetail.state || {}
        return String(s[key] || "")
    }

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Financials" }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.sectionErrors["financials"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["financials"] || "")
        }

        Item {
            width: parent.width
            implicitHeight: _financialsCol.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            ColumnLayout {
                id: _financialsCol
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: !root._hasProject
                    title: "No financial data"
                    message: "Select a project to review its financial information."
                }

                RowLayout {
                    Layout.fillWidth: true
                    visible: root._hasProject
                    spacing: Theme.AppTheme.spacingMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label {
                            text: "Planned Budget"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root._sv("plannedBudgetLabel") || "-"
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        AppControls.Label {
                            text: "Currency"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root._sv("currency") || "-"
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                        }
                    }

                    Item { Layout.fillWidth: true }
                    Item { Layout.fillWidth: true }
                }

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: root._hasProject
                    title: "Cost tracking data"
                    message: "Open the Financials workspace to review actuals, commitments, and forecast against this project's budget."
                }
            }
        }
    }
}
