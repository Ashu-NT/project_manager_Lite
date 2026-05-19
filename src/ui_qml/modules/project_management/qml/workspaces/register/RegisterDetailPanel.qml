import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Rectangle {
    id: root

    property var entryDetail: ({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "Select a register entry to review governance details.",
        "fields": [], "state": {}
    })
    property var urgentModel: ({
        "title": "Urgent Review Queue", "subtitle": "", "emptyState": "No urgent items.", "items": []
    })
    property string selectedEntryId: ""
    property bool isBusy: false

    signal editRequested()
    signal deleteRequested()
    signal urgentEntrySelected(string entryId)

    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    border.width: 1
    radius: Theme.AppTheme.radiusMd
    clip: true

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        AppWidgets.DetailTabBar {
            id: tabBar
            Layout.fillWidth: true
            tabs: ["Details", "Urgent Queue", "Activity", "Links"]
            currentIndex: 0
            onTabSelected: function(index) { tabBar.currentIndex = index }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: tabBar.currentIndex

            // Tab 0: Details
            Flickable {
                clip: true
                contentWidth: width
                contentHeight: detailSection.implicitHeight + Theme.AppTheme.spacingLg
                ScrollBar.vertical: ScrollBar {}

                ProjectManagementWidgets.RegisterDetailSection {
                    id: detailSection
                    width: parent.width
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right

                    entryDetail: root.entryDetail
                    isBusy: root.isBusy
                    onEditRequested: root.editRequested()
                    onDeleteRequested: root.deleteRequested()
                }
            }

            // Tab 1: Urgent Queue
            Flickable {
                clip: true
                contentWidth: width
                contentHeight: urgentSection.implicitHeight + Theme.AppTheme.spacingLg
                ScrollBar.vertical: ScrollBar {}

                ProjectManagementWidgets.RegisterUrgentSection {
                    id: urgentSection
                    width: parent.width
                    anchors.top: parent.top
                    anchors.left: parent.left
                    anchors.right: parent.right

                    urgentModel: root.urgentModel
                    selectedEntryId: root.selectedEntryId

                    onEntrySelected: function(entryId) { root.urgentEntrySelected(entryId) }
                }
            }

            // Tab 2: Activity (placeholder)
            Item {
                Label {
                    anchors.centerIn: parent
                    text: "Activity feed coming soon"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                }
            }

            // Tab 3: Links (placeholder)
            Item {
                Label {
                    anchors.centerIn: parent
                    text: "Linked documents and references coming soon"
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                }
            }
        }
    }
}
