import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
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
    property var detailPage: null

    signal editRequested()
    signal deleteRequested()
    signal urgentEntrySelected(string entryId)

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
            implicitHeight: detailSection.implicitHeight + Theme.AppTheme.spacingMd * 2

            ProjectManagementWidgets.RegisterDetailSection {
                id: detailSection
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd

                entryDetail: root.entryDetail
                isBusy: root.isBusy
                onEditRequested: root.editRequested()
                onDeleteRequested: root.deleteRequested()
            }
        }

        // ── Section 1: Impact ────────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 1; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Impact" }

        Item {
            width: parent.width
            implicitHeight: urgentSection.implicitHeight + Theme.AppTheme.spacingMd * 2

            ProjectManagementWidgets.RegisterUrgentSection {
                id: urgentSection
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd

                urgentModel: root.urgentModel
                selectedEntryId: root.selectedEntryId

                onEntrySelected: function(entryId) { root.urgentEntrySelected(entryId) }
            }
        }

        // ── Section 2: Response ──────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 2; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Response" }

        Rectangle {
            width: parent.width
            height: 80
            color: "transparent"

            Label {
                anchors.centerIn: parent
                text: "Activity feed coming soon"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
            }
        }

        // ── Section 3: Links ─────────────────────────────────────────────
        AppWidgets.SectionAnchor { sectionIndex: 3; detailPage: root.detailPage }
        AppWidgets.SectionHeading { label: "Links" }

        Rectangle {
            width: parent.width
            height: 80
            color: "transparent"

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
