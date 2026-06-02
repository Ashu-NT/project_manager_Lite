pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var taskDetail: ({
        "id": "", "title": "", "description": "", "emptyState": "", "fields": [], "state": {}
    })

    readonly property bool _hasTask: String(root.taskDetail.id || "").length > 0

    implicitHeight: _detailsCol.implicitHeight + Theme.AppTheme.spacingMd * 2

    ColumnLayout {
        id: _detailsCol
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: Theme.AppTheme.spacingMd
        anchors.leftMargin: Theme.AppTheme.marginMd
        anchors.rightMargin: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: !root._hasTask
                && String(root.taskDetail.emptyState || "").length > 0
            title: root.taskDetail.emptyState || ""
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: root._hasTask
                && String(root.taskDetail.description || "").length > 0
            text: root.taskDetail.description || ""
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        GridLayout {
            Layout.fillWidth: true
            visible: root._hasTask && (root.taskDetail.fields || []).length > 0
            columns: 2
            columnSpacing: Theme.AppTheme.spacingLg
            rowSpacing: Theme.AppTheme.spacingMd

            Repeater {
                model: root.taskDetail.fields || []

                delegate: ColumnLayout {
                    id: _field
                    required property var modelData

                    Layout.fillWidth: true
                    spacing: 2

                    AppControls.Label {
                        text: String(_field.modelData.label || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: String(_field.modelData.value || "-")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        elide: Text.ElideRight
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        visible: String(_field.modelData.supportingText || "").length > 0
                        text: String(_field.modelData.supportingText || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        elide: Text.ElideRight
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.AppTheme.divider
            visible: root._hasTask && (root.taskDetail.fields || []).length > 0
        }
    }
}
