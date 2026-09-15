pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls

// A single Global Overview module destination card. Generic over whatever
// modules GlobalOverviewService.list_module_summaries() returns -- must
// never hardcode "Platform"/"Project Management"; the caller supplies one
// card per ModuleCardViewModel. The whole card is the one navigation
// target (no separate button), matching the design rule that a module
// card is a destination, not a mini-dashboard.
Rectangle {
    id: root

    property string moduleCode: ""
    property string title: ""
    property string description: ""
    property string iconKey: ""
    property string summaryText: ""
    property string routeId: ""

    signal activated()

    readonly property bool _navigable: root.routeId.length > 0

    function _iconNameFor(key) {
        // The backend's icon_key is a semantic module identifier, not a
        // concrete icon-font glyph name -- this is the one place that maps
        // between them, so unknown/future module codes fail safely to the
        // generic "module" glyph rather than an unregistered icon warning.
        if (key === "platform") return "admin"
        if (key === "project_management") return "project"
        return "module"
    }

    implicitHeight: _layout.implicitHeight + Theme.AppTheme.marginLg * 2
    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surfaceRaised
    border.width: 1
    border.color: _hover.hovered && root._navigable ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder

    Behavior on border.color { ColorAnimation { duration: 120 } }

    RowLayout {
        id: _layout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        Rectangle {
            Layout.preferredWidth: Theme.AppTheme.sizeLg
            Layout.preferredHeight: Theme.AppTheme.sizeLg
            Layout.alignment: Qt.AlignTop
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.accentSoft

            AppIcons.AppIcon {
                anchors.centerIn: parent
                name: root._iconNameFor(root.iconKey)
                iconColor: Theme.AppTheme.accent
                size: Theme.AppTheme.iconLg
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs

            AppControls.Label {
                Layout.fillWidth: true
                text: root.title
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
                elide: Text.ElideRight
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: root.description.length > 0
                text: root.description
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
            }

            AppControls.Label {
                Layout.fillWidth: true
                Layout.topMargin: Theme.AppTheme.spacingXs
                // A blank/unavailable metric shows as "—" rather than
                // hiding or failing the card -- the card itself always
                // represents a real, accessible module.
                text: root.summaryText.length > 0 ? root.summaryText : "—"
                color: Theme.AppTheme.accent
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
                elide: Text.ElideRight
            }
        }

        AppIcons.AppIcon {
            visible: root._navigable
            Layout.alignment: Qt.AlignVCenter
            name: "chevron_right"
            size: Theme.AppTheme.iconLg
            iconColor: _hover.hovered ? Theme.AppTheme.accent : Theme.AppTheme.textMuted
        }
    }

    HoverHandler {
        id: _hover
        enabled: root._navigable
        cursorShape: root._navigable ? Qt.PointingHandCursor : Qt.ArrowCursor
    }

    TapHandler {
        enabled: root._navigable
        onTapped: root.activated()
    }
}
