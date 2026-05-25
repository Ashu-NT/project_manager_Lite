import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Mock 1.0 as AppMock
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var entryDetail: AppMock.MockFactory.detail("Select a risk entry to review mitigation details.")
    property var urgentModel: AppMock.MockFactory.catalog("Urgent Review Queue", "", "No urgent risks.")
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

    AppWidgets.LazySectionLoader {
        id: _sec0
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 0
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
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
    }

    AppWidgets.LazySectionLoader {
        id: _sec1
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 1
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Impact"
                }

                Rectangle {
                    width: parent.width
                    height: 80
                    color: "transparent"

                    AppControls.Label {
                        anchors.centerIn: parent
                        text: "Mitigation actions and owner assignments coming soon"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        wrapMode: Text.WordWrap
                        horizontalAlignment: Text.AlignHCenter
                        width: parent.width - Theme.AppTheme.spacingLg * 2
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec2
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 2
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Response"
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
    }

    AppWidgets.LazySectionLoader {
        id: _sec3
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 3
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Links"
                }

                Rectangle {
                    width: parent.width
                    height: 80
                    color: "transparent"

                    AppControls.Label {
                        anchors.centerIn: parent
                        text: "Activity feed coming soon"
                        color: Theme.AppTheme.textMuted
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                    }
                }
            }
        }
    }
}
