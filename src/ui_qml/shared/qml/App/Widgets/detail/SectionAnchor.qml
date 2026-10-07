pragma ComponentBehavior: Bound
import QtQuick

// Zero-height position marker. Place one at the start of each content section
// inside SectionDetailPage to enable scroll-spy sidebar highlighting.
//
// Usage:
//   AppWidgets.SectionAnchor { sectionIndex: 0; detailPage: detailPage }
//   // ... section content ...
//   AppWidgets.SectionAnchor { sectionIndex: 1; detailPage: detailPage }
Item {
    id: root

    property int sectionIndex: 0
    property var detailPage: null

    height: 0
    width: parent ? parent.width : 0

    function _report() {
        if (root.detailPage !== null && root.sectionIndex >= 0)
            root.detailPage.registerSection(root.sectionIndex, root.y)
    }

    Component.onCompleted: Qt.callLater(_report)
    onYChanged: Qt.callLater(_report)
}
