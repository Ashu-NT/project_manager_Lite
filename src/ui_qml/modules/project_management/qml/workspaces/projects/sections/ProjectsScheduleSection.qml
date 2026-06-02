pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var projectDetail: ({
        "id": "", "state": {}
    })
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

        AppWidgets.SectionHeading { width: parent.width; label: "Schedule" }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.sectionErrors["schedule"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["schedule"] || "")
        }

        Item {
            width: parent.width
            implicitHeight: _scheduleContent.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            ColumnLayout {
                id: _scheduleContent
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingXs

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: !root._hasProject
                    title: "No schedule data"
                    message: "Select a project to review its schedule."
                }

                Item {
                    Layout.fillWidth: true
                    visible: root._hasProject
                    implicitHeight: _scheduleGrid.implicitHeight

                    GridLayout {
                        id: _scheduleGrid
                        width: parent.width
                        columns: 2
                        columnSpacing: Theme.AppTheme.spacingMd
                        rowSpacing: Theme.AppTheme.spacingXs

                        AppControls.Label {
                            text: "Start Date"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root._sv("startDateLabel") || "Not scheduled"
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                        }

                        AppControls.Label {
                            text: "Finish Date"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root._sv("endDateLabel") || "Not scheduled"
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                        }
                    }
                }
            }
        }
    }
}
