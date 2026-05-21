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

    readonly property int activeSectionIndex: _activeIdx

    signal backRequested()
    signal editRequested()
    signal deleteRequested()

    default property alias content: contentColumn.data

    visible: root.open

    function registerSection(index, yOffset) {
        // no-op: section switching is now index-based, not scroll-position-based
    }

    function scrollToSection(index) {
        if (index < 0 || index >= root.sections.length) {
            return
        }
        _activeIdx = index
        contentFlickable.contentY = 0
    }

    property int _activeIdx: 0
    property var _sectionOffsets: []  // kept for API compat

    function _updateActiveFromScroll() {}

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
                    anchors.leftMargin: Theme.AppTheme.marginMd
                    anchors.rightMargin: Theme.AppTheme.marginMd
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
                                size: 12
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

                    Label {
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

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                Rectangle {
                    Layout.preferredWidth: Theme.AppTheme.detailRailWidth
                    Layout.fillHeight: true
                    color: Theme.AppTheme.surfaceRaised

                    Rectangle {
                        anchors.right: parent.right
                        width: 1
                        height: parent.height
                        color: Theme.AppTheme.divider
                    }

                    Column {
                        id: navColumn
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.margins: Theme.AppTheme.marginMd
                        spacing: Theme.AppTheme.spacingXs

                        Label {
                            width: parent.width
                            visible: root.sections.length > 0
                            text: "SECTIONS"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                            font.letterSpacing: 0.8
                        }

                        Repeater {
                            model: root.sections

                            delegate: Item {
                                id: navItem
                                required property var modelData
                                required property int index

                                width: navColumn.width
                                height: Theme.AppTheme.sidebarRowHeight

                                readonly property bool   isActive: root._activeIdx === navItem.index
                                readonly property string _label: typeof navItem.modelData === "string"
                                    ? navItem.modelData
                                    : String(navItem.modelData.label || "")
                                readonly property int    _count: typeof navItem.modelData === "object"
                                    ? (parseInt(navItem.modelData.count || 0))
                                    : 0

                                Rectangle {
                                    anchors.fill: parent
                                    radius: Theme.AppTheme.radiusSm
                                    color: navItem.isActive
                                        ? Theme.AppTheme.navSelectedBackground
                                        : navHover.containsMouse
                                            ? Theme.AppTheme.hoverSurface
                                            : "transparent"
                                }

                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    width: 3
                                    radius: 2
                                    color: Theme.AppTheme.accent
                                    visible: navItem.isActive
                                }

                                Label {
                                    id: _navLabel
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left:        parent.left
                                    anchors.leftMargin:  14
                                    anchors.right:       _countBadge.visible ? _countBadge.left : parent.right
                                    anchors.rightMargin: Theme.AppTheme.spacingSm
                                    text:           navItem._label
                                    color:          navItem.isActive
                                        ? Theme.AppTheme.navSelectedText
                                        : Theme.AppTheme.textSecondary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold:      navItem.isActive
                                    elide:          Text.ElideRight
                                }

                                Rectangle {
                                    id: _countBadge
                                    anchors.right:          parent.right
                                    anchors.rightMargin:    Theme.AppTheme.spacingSm
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: navItem._count > 0
                                    width:  _countLabel.implicitWidth + 8
                                    height: 16
                                    radius: 8
                                    color:  navItem.isActive
                                        ? Theme.AppTheme.accent
                                        : Theme.AppTheme.surfaceOverlay

                                    Label {
                                        id: _countLabel
                                        anchors.centerIn: parent
                                        text:           String(navItem._count)
                                        color:          navItem.isActive
                                            ? Theme.AppTheme.textOnAccent
                                            : Theme.AppTheme.textMuted
                                        font.family:    Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        font.bold:      true
                                    }
                                }

                                MouseArea {
                                    id: navHover
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.scrollToSection(navItem.index)
                                }
                            }
                        }
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
                    }

                    ScrollBar.vertical: ScrollBar {
                        policy: ScrollBar.AsNeeded
                    }
                }
            }
        }
    }
}
