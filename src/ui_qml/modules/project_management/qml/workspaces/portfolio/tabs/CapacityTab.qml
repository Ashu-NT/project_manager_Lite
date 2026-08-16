pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Flickable {
    id: root

    property var capacityPoolModel: ({
        "title": "Capacity Pool", "subtitle": "", "emptyState": "Assign resources to tasks to see portfolio-level capacity demand.", "items": []
    })

    contentWidth: width
    contentHeight: _col.implicitHeight + Theme.AppTheme.marginMd * 2
    boundsBehavior: Flickable.StopAtBounds
    clip: true

    ColumnLayout {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingMd

        AppControls.Label {
            Layout.fillWidth: true
            text: root.capacityPoolModel.title || "Capacity Pool"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold: true
        }
        AppControls.Label {
            Layout.fillWidth: true
            text: root.capacityPoolModel.subtitle || ""
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
            wrapMode: Text.Wrap
            visible: !!text
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: (root.capacityPoolModel.items || []).length === 0
            title: "No capacity data"
            message: root.capacityPoolModel.emptyState || "Assign resources to tasks to see portfolio-level capacity demand."
        }

        Repeater {
            model: root.capacityPoolModel.items || []
            delegate: Rectangle {
                id: _capRow
                required property var modelData
                required property int index
                Layout.fillWidth: true
                implicitHeight: _capRowContent.implicitHeight + Theme.AppTheme.spacingSm * 2
                color: (_capRow.modelData.state && _capRow.modelData.state.overloaded)
                    ? Qt.rgba(Theme.AppTheme.danger.r, Theme.AppTheme.danger.g, Theme.AppTheme.danger.b, 0.08)
                    : Theme.AppTheme.surfaceAlt
                radius: Theme.AppTheme.radiusSm

                RowLayout {
                    id: _capRowContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: Theme.AppTheme.spacingSm
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: String(_capRow.modelData.title || "")
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        elide: Text.ElideRight
                    }
                    AppControls.Label {
                        text: String(_capRow.modelData.subtitle || "")
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                    }
                    AppControls.Label {
                        text: String(_capRow.modelData.statusLabel || "")
                        color: (_capRow.modelData.state && _capRow.modelData.state.overloaded)
                            ? Theme.AppTheme.danger : Theme.AppTheme.success
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                        font.bold: true
                    }
                }
            }
        }
    }
}
