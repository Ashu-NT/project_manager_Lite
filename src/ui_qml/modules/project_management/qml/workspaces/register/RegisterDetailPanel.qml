import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Mock 1.0 as AppMock
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
    id: root

    property var entryDetail: AppMock.MockFactory.detail("Select a register entry to review governance details.")
    property var urgentModel: AppMock.MockFactory.catalog("Urgent Review Queue", "", "No urgent items.")
    property string selectedEntryId: ""
    property bool isBusy: false
    property var detailPage: null

    signal editRequested()
    signal deleteRequested()
    signal urgentEntrySelected(string entryId)

    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property int _activeSectionH: {
        if (root._idx === 0) return _sec0.implicitHeight
        if (root._idx === 1) return _sec1.implicitHeight
        if (root._idx === 2) return _sec2.implicitHeight
        return _sec3.implicitHeight
    }

    implicitHeight: _activeSectionH

    // ── Section 0: Details ────────────────────────────────────────────────
    Item {
        id: _sec0
        width: parent.width
        implicitHeight: _sec0Col.implicitHeight
        visible: root._idx === 0

        Column {
            id: _sec0Col
            width: parent.width
            spacing: 0

            AppWidgets.SectionHeading {
                width: parent.width
                label: "Details"
            }

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
        }
    }

    // ── Section 1: Impact ─────────────────────────────────────────────────
    Item {
        id: _sec1
        width: parent.width
        implicitHeight: _sec1Col.implicitHeight
        visible: root._idx === 1

        Column {
            id: _sec1Col
            width: parent.width
            spacing: 0

            AppWidgets.SectionHeading {
                width: parent.width
                label: "Impact"
            }

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
        }
    }

    // ── Section 2: Response ───────────────────────────────────────────────
    Item {
        id: _sec2
        width: parent.width
        implicitHeight: _sec2Col.implicitHeight
        visible: root._idx === 2

        Column {
            id: _sec2Col
            width: parent.width
            spacing: 0

            AppWidgets.SectionHeading {
                width: parent.width
                label: "Response"
            }

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
        }
    }

    // ── Section 3: Links ──────────────────────────────────────────────────
    Item {
        id: _sec3
        width: parent.width
        implicitHeight: _sec3Col.implicitHeight
        visible: root._idx === 3

        Column {
            id: _sec3Col
            width: parent.width
            spacing: 0

            AppWidgets.SectionHeading {
                width: parent.width
                label: "Links"
            }

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
}
