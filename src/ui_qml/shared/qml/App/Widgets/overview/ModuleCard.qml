pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls
import "ModuleIconMap.js" as ModuleIconMap

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
    // Structural-only reduction for constrained layouts (e.g. Global
    // Overview's compact responsive layout class) -- never a global scale
    // transform. Defaults false.
    property bool compact: false

    signal activated()

    readonly property bool _navigable: root.routeId.length > 0
    readonly property int _margin: root.compact ? Theme.AppTheme.marginMd : Theme.AppTheme.marginLg

    function _activate() {
        if (root._navigable) {
            root.activated()
        }
    }

    implicitHeight: _layout.implicitHeight + root._margin * 2
    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surfaceRaised
    border.width: root.activeFocus && root._navigable ? 2 : 1
    border.color: root.activeFocus && root._navigable
        ? Theme.AppTheme.focusBorder
        : _hover.hovered && root._navigable ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder

    Behavior on border.color { ColorAnimation { duration: 120 } }

    // -- Keyboard / accessibility -------------------------------------
    // Informational (non-navigable) cards are deliberately left out of
    // the Tab order and carry no button semantics.
    activeFocusOnTab: root._navigable
    Accessible.role: root._navigable ? Accessible.Button : Accessible.StaticText
    Accessible.name: root.title
    Accessible.onPressAction: root._activate()

    Keys.onPressed: (event) => {
        if (!root._navigable) {
            return
        }
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
            root._activate()
            event.accepted = true
        }
    }

    RowLayout {
        id: _layout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: root._margin
        spacing: Theme.AppTheme.spacingMd

        Rectangle {
            Layout.preferredWidth: Theme.AppTheme.sizeLg
            Layout.preferredHeight: Theme.AppTheme.sizeLg
            Layout.alignment: Qt.AlignTop
            radius: Theme.AppTheme.radiusMd
            color: Theme.AppTheme.accentSoft

            AppIcons.AppIcon {
                anchors.centerIn: parent
                name: ModuleIconMap.iconNameFor(root.iconKey)
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
        onTapped: {
            root.forceActiveFocus()
            root._activate()
        }
    }
}
