pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var workspaceController: null
    property var capColumns: []
    property int capCount: 0
    property bool busy: false
    property bool load: false

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.AppTheme.toolbarHeight - 6
            color: Theme.AppTheme.surfaceRaised
            z: 1

            Rectangle {
                anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                height: 1; color: Theme.AppTheme.divider
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.rightMargin: 8
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "Integration Capabilities"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
                AppControls.Label {
                    visible: root.capCount > 0
                    text: String(root.capCount)
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    leftPadding: 4
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    implicitWidth: 26; implicitHeight: 26; radius: 4
                    color: _capRefreshMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"
                    AppIcons.AppIcon { anchors.centerIn: parent; name: "refresh"; size: 12; iconColor: Theme.AppTheme.textMuted }
                    MouseArea {
                        id: _capRefreshMA
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        enabled: !root.busy
                        onClicked: { if (root.workspaceController) root.workspaceController.refresh() }
                    }
                }
            }
        }

        AppWidgets.DataTable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceModel: root.workspaceController ? root.workspaceController.integrationCapabilitiesTableModel : null
            columns: root.capColumns
            emptyText: root.workspaceController
                ? (root.workspaceController.integrationCapabilities.emptyState || "No capabilities registered")
                : "No capabilities registered"
            loading: root.load
        }
    }
}
