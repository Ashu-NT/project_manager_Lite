pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls

Item {
    id: root

    property bool open: false
    property string title: ""
    property bool isBusy: false
    property bool showHeader: true
    property bool showEdit: true
    property bool showDelete: true
    property var sections: []
    property bool sectionGroupsCollapsedByDefault: true

    readonly property int activeSectionIndex: _activeIdx

    signal backRequested()
    signal editRequested()
    signal deleteRequested()
    signal sectionChanged(int index)

    default property alias content: contentColumn.data

    visible: root.open

    function registerSection(index, yOffset) {
        // no-op: section switching is now index-based, not scroll-position-based
    }

    function scrollToSection(index) {
        if (index < 0 || index >= root.sections.length) {
            return
        }

        if (_activeIdx === index) {
            return
        }

        sectionNavigation.expandGroupForSection(index)
        _activeIdx = index
        contentFlickable.contentY = 0
        root.sectionChanged(index)
    }

    property int _activeIdx: 0
    property var _sectionOffsets: []  // kept for API compat
    onSectionsChanged: {
        if (root._activeIdx >= root.sections.length) {
            root._activeIdx = Math.max(0, root.sections.length - 1)
        }
    }

    function _updateActiveFromScroll() {}

    function _isPinnedContent(item) {
        return item && item.detailPagePinned === true
    }

    function _syncPinnedContent() {
        const scrollingChildren = contentColumn.children || []
        for (let index = 0; index < scrollingChildren.length; index += 1) {
            const child = scrollingChildren[index]
            if (root._isPinnedContent(child) && child.parent !== stickyColumn) {
                child.parent = stickyColumn
            }
        }

        const pinnedChildren = stickyColumn.children || []
        for (let index = 0; index < pinnedChildren.length; index += 1) {
            const child = pinnedChildren[index]
            if (!root._isPinnedContent(child) && child.parent !== contentColumn) {
                child.parent = contentColumn
            }
        }
    }

    Component.onCompleted: Qt.callLater(root._syncPinnedContent)

    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.workspaceBackground

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: root.showHeader ? Theme.AppTheme.panelHeaderHeight : 0
                visible: root.showHeader
                color: Theme.AppTheme.surfaceRaised

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: Theme.AppTheme.divider
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.AppTheme.pagePadding
                    anchors.rightMargin: Theme.AppTheme.pagePadding
                    spacing: Theme.AppTheme.spacingSm

                    Item {
                        id: backButton
                        implicitWidth: backRow.implicitWidth + 14
                        implicitHeight: Theme.AppTheme.inputHeight

                        Rectangle {
                            anchors.fill: parent
                            radius: Theme.AppTheme.radiusSm
                            color: backHover.containsMouse
                                ? Theme.AppTheme.hoverSurface
                                : Theme.AppTheme.surfaceOverlay
                        }

                        Row {
                            id: backRow
                            anchors.centerIn: parent
                            spacing: Theme.AppTheme.spacingXs

                            AppIcons.AppIcon {
                                name: "chevron_left"
                                size: Theme.AppTheme.headerIconSize
                                iconColor: Theme.AppTheme.textSecondary
                                anchors.verticalCenter: parent.verticalCenter
                            }

                            Text {
                                text: "Back"
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                                anchors.verticalCenter: parent.verticalCenter
                            }
                        }

                        MouseArea {
                            id: backHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.backRequested()
                        }
                    }

                    Rectangle {
                        implicitWidth: 1
                        implicitHeight: 18
                        color: Theme.AppTheme.divider
                    }

                    AppControls.Label {
                        Layout.fillWidth: true
                        text: root.title
                        font.pixelSize: Theme.AppTheme.sectionSize
                        font.bold: true
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textPrimary
                        elide: Text.ElideRight
                    }

                    BusyIndicator {
                        visible: root.isBusy
                        running: root.isBusy
                        implicitWidth: 20
                        implicitHeight: 20
                    }

                    AppControls.SecondaryButton {
                        visible: root.showEdit
                        text: "Edit"
                        iconName: "edit"
                        enabled: !root.isBusy
                        implicitWidth: 72
                        onClicked: root.editRequested()
                    }

                    AppControls.SecondaryButton {
                        visible: root.showDelete
                        text: "Delete"
                        iconName: "delete"
                        danger: true
                        enabled: !root.isBusy
                        implicitWidth: 80
                        onClicked: root.deleteRequested()
                    }
                }
            }

            Item {
                id: stickyHost
                Layout.fillWidth: true
                implicitHeight: stickyColumn.childrenRect.height
                visible: implicitHeight > 0

                Column {
                    id: stickyColumn
                    width: parent.width
                    spacing: 0

                    onChildrenChanged: Qt.callLater(root._syncPinnedContent)
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                SectionNavigationRail {
                    id: sectionNavigation

                    Layout.preferredWidth: Theme.AppTheme.detailRailWidth
                    Layout.fillHeight: true
                    sections: root.sections
                    activeSectionIndex: root._activeIdx
                    groupsCollapsedByDefault: root.sectionGroupsCollapsedByDefault
                    onSectionRequested: function(index) {
                        root.scrollToSection(index)
                    }
                }

                Flickable {
                    id: contentFlickable
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: width
                    contentHeight: contentColumn.implicitHeight + Theme.AppTheme.pagePadding
                    clip: true

                    Column {
                        id: contentColumn
                        width: contentFlickable.width

                        onChildrenChanged: Qt.callLater(root._syncPinnedContent)
                    }

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                    }
                }
            }
        }
    }
}
