pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons

// Full-page record detail layout with sidebar scroll-spy navigation.
// Usage:
//   SectionDetailPage {
//       open: true
//       title: "Project Name"
//       sections: ["Overview", "Activity", "Settings"]
//       // place content children here — use SectionAnchor at each section start
//   }
Item {
    id: root

    property bool open: false
    property string title: ""
    property bool isBusy: false
    property bool showEdit: true
    property bool showDelete: true

    // Section labels for the sidebar nav
    property var sections: []

    // Currently highlighted sidebar item (updated by scroll-spy)
    readonly property int activeSectionIndex: _activeIdx

    signal backRequested()
    signal editRequested()
    signal deleteRequested()

    // Default alias — all content children go inside _contentCol
    default property alias content: _contentCol.data

    visible: root.open

    // Called by SectionAnchor children to register their Y position
    function registerSection(index, yOffset) {
        var arr = _sectionOffsets.slice()
        while (arr.length <= index) arr.push(0)
        arr[index] = yOffset
        _sectionOffsets = arr
    }

    // Scroll the right Flickable so section `index` is at the top
    function scrollToSection(index) {
        if (index < 0 || index >= root.sections.length) return
        var target = (index < _sectionOffsets.length) ? _sectionOffsets[index] : 0
        var maxY = Math.max(0, _contentFlickable.contentHeight - _contentFlickable.height)
        _contentFlickable.contentY = Math.max(0, Math.min(target, maxY))
        _activeIdx = index
    }

    property int _activeIdx: 0
    property var _sectionOffsets: []

    function _updateActiveFromScroll() {
        if (_sectionOffsets.length === 0) return
        var y = _contentFlickable.contentY
        var best = 0
        for (var i = 0; i < _sectionOffsets.length; i++) {
            if (_sectionOffsets[i] <= y + 28) best = i
        }
        if (_activeIdx !== best) _activeIdx = best
    }

    // ── Full-page background ──────────────────────────────────────────────
    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.background

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            // ── Header bar ───────────────────────────────────────────────
            Rectangle {
                Layout.fillWidth: true
                height: 44
                color: Theme.AppTheme.surface
                z: 2

                Rectangle {
                    anchors.bottom: parent.bottom
                    width: parent.width
                    height: 1
                    color: Theme.AppTheme.border
                }

                RowLayout {
                    anchors { fill: parent; leftMargin: 8; rightMargin: 12 }
                    spacing: 4

                    ToolButton {
                        implicitWidth: 32
                        implicitHeight: 32
                        contentItem: AppIcons.AppIcon {
                            name: "chevron_left"
                            size: 14
                            iconColor: Theme.AppTheme.textSecondary
                        }
                        onClicked: root.backRequested()
                    }

                    Label {
                        Layout.fillWidth: true
                        text: root.title
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textPrimary
                        elide: Text.ElideRight
                    }

                    BusyIndicator {
                        visible: root.isBusy
                        running: root.isBusy
                        width: 20; height: 20
                    }

                    ToolButton {
                        visible: root.showEdit
                        text: "Edit"
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        palette.buttonText: Theme.AppTheme.accent
                        enabled: !root.isBusy
                        onClicked: root.editRequested()
                    }

                    ToolButton {
                        visible: root.showDelete
                        text: "Delete"
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        palette.buttonText: Theme.AppTheme.error
                        enabled: !root.isBusy
                        onClicked: root.deleteRequested()
                    }
                }
            }

            // ── Body: sidebar + content ───────────────────────────────────
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 0

                // ── Left sidebar nav (200px) ──────────────────────────────
                Rectangle {
                    width: 200
                    Layout.fillHeight: true
                    color: Theme.AppTheme.surfaceAlt

                    Rectangle {
                        anchors.right: parent.right
                        width: 1
                        height: parent.height
                        color: Theme.AppTheme.border
                    }

                    Column {
                        id: navColumn
                        anchors {
                            top: parent.top
                            left: parent.left
                            right: parent.right
                            topMargin: 16
                            leftMargin: 8
                            rightMargin: 8
                        }
                        spacing: 2

                        Repeater {
                            model: root.sections

                            delegate: Item {
                                id: navItem
                                required property string modelData
                                required property int index

                                width: navColumn.width
                                height: 34

                                readonly property bool isActive: root._activeIdx === navItem.index

                                // Active background
                                Rectangle {
                                    anchors.fill: parent
                                    radius: 6
                                    color: Theme.AppTheme.accent
                                    opacity: navItem.isActive ? 0.10 : 0
                                    Behavior on opacity { NumberAnimation { duration: 120 } }
                                }

                                // Active left accent bar
                                Rectangle {
                                    visible: navItem.isActive
                                    anchors {
                                        left: parent.left
                                        top: parent.top
                                        bottom: parent.bottom
                                        topMargin: 6
                                        bottomMargin: 6
                                    }
                                    width: 3
                                    radius: 2
                                    color: Theme.AppTheme.accent
                                }

                                Label {
                                    anchors {
                                        verticalCenter: parent.verticalCenter
                                        left: parent.left
                                        leftMargin: 14
                                        right: parent.right
                                        rightMargin: 4
                                    }
                                    text: navItem.modelData
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.family: Theme.AppTheme.fontFamily
                                    font.bold: navItem.isActive
                                    color: navItem.isActive
                                        ? Theme.AppTheme.accent
                                        : Theme.AppTheme.textSecondary
                                    elide: Text.ElideRight

                                    Behavior on color { ColorAnimation { duration: 120 } }
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.scrollToSection(navItem.index)
                                }
                            }
                        }
                    }
                }

                // ── Right scrollable content ──────────────────────────────
                Flickable {
                    id: _contentFlickable
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    contentWidth: width
                    contentHeight: _contentCol.implicitHeight + 32
                    clip: true

                    onContentYChanged: root._updateActiveFromScroll()

                    Column {
                        id: _contentCol
                        width: _contentFlickable.width
                        // Content injected via default alias
                    }

                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                }
            }
        }
    }
}
