pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme

// Section heading used inside SectionDetailPage content.
// Renders a styled label that visually separates content regions.
//
// Usage:
//   AppWidgets.SectionAnchor { sectionIndex: 0; detailPage: detailPage }
//   AppWidgets.SectionHeading { label: "Overview" }
//   // ... section content ...
Item {
    id: root

    property string label: ""
    property string text: ""

    width: parent ? parent.width : 0
    height: 40

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.AppTheme.divider
    }

    Label {
        anchors {
            verticalCenter: parent.verticalCenter
            left: parent.left
            leftMargin: Theme.AppTheme.spacingMd
        }
        text: (root.label || root.text).toUpperCase()

        color: Theme.AppTheme.textMuted
        
        font.pixelSize: Theme.AppTheme.smallSize
        font.bold: true
        font.family: Theme.AppTheme.fontFamily
        font.letterSpacing: 0.8

        elide: Text.ElideRight
    }
}
