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
    property var moduleColumns: []
    property int moduleCount: 0
    property string selectedRowId: ""
    property bool busy: false
    property bool load: false

    signal rowSelected(string id)
    signal rowActivated(string id)

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
                    text: "Module Entitlements"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
                AppControls.Label {
                    visible: root.moduleCount > 0
                    text: String(root.moduleCount)
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    leftPadding: 4
                }

                Item { Layout.fillWidth: true }

                Rectangle {
                    implicitWidth: 26; implicitHeight: 26; radius: 4
                    color: _modRefreshMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"
                    AppIcons.AppIcon { anchors.centerIn: parent; name: "refresh"; size: 12; iconColor: Theme.AppTheme.textMuted }
                    MouseArea {
                        id: _modRefreshMA
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
            sourceModel: root.workspaceController ? root.workspaceController.moduleEntitlementsTableModel : null
            columns: root.moduleColumns
            selectedRowId: root.selectedRowId
            emptyText: root.workspaceController
                ? (root.workspaceController.moduleEntitlements.emptyState || "No modules configured")
                : "No modules configured"
            loading: root.load
            onRowSelected: function(id) { root.rowSelected(id) }
            onRowActivated: function(id) { root.rowActivated(id) }
        }
    }
}
