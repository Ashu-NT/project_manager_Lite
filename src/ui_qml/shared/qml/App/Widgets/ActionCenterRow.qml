pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import App.Controls 1.0 as AppControls

// A single Action Center item. Navigation only activates when routeId is
// non-empty -- the workspace-level route the backend contributor already
// assigned; this component never invents a per-object deep link.
Item {
    id: root

    property string title: ""
    property string moduleLabel: ""
    property string subjectDisplay: ""
    property string actionState: ""
    property string statusLabel: ""
    property string priorityLabel: ""
    property string dueLabel: ""
    property string routeId: ""

    signal activated()

    readonly property bool _navigable: root.routeId.length > 0

    readonly property string _subtitle: {
        const parts = [root.moduleLabel, root.subjectDisplay].filter(function (part) {
            return part.length > 0
        })
        return parts.join(" · ")
    }

    readonly property string _statusLine: {
        const parts = [root.statusLabel, root.dueLabel].filter(function (part) {
            return part.length > 0
        })
        return parts.join(" · ")
    }

    readonly property color _statusColor: root.actionState === "rejected"
        ? Theme.AppTheme.danger
        : Theme.AppTheme.textSecondary

    // ActionCenterRow renders exactly one presentation concept --
    // cross-module action priority ("High"/"Medium"/"Low"/"Critical"/"Not set") 
    readonly property string _priorityTone: {
        const p = root.priorityLabel.toLowerCase()
        if (p === "critical" || p === "high") return "danger"
        if (p === "medium") return "warning"
        if (p === "low") return "info"
        return "neutral"
    }

    function _activate() {
        if (root._navigable) {
            root.activated()
        }
    }

    implicitHeight: _layout.implicitHeight + Theme.AppTheme.spacingSm * 2

    // -- Keyboard / accessibility -------------------------------------
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

    Rectangle {
        anchors.fill: parent
        radius: Theme.AppTheme.radiusMd
        color: _hover.hovered && root._navigable ? Theme.AppTheme.hoverSurface : "transparent"
        Behavior on color { ColorAnimation { duration: 100 } }
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.AppTheme.radiusMd
        color: "transparent"
        border.width: 2
        border.color: Theme.AppTheme.focusBorder
        visible: root.activeFocus && root._navigable
    }

    ColumnLayout {
        id: _layout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: Theme.AppTheme.spacingSm
        anchors.rightMargin: Theme.AppTheme.spacingSm
        spacing: 2

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs

            AppControls.Label {
                Layout.fillWidth: true
                text: root.title
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
                elide: Text.ElideRight
            }

            AppWidgets.StatusChip {
                visible: root.priorityLabel.length > 0
                status: root.priorityLabel
                tone:   root._priorityTone
            }
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: root._subtitle.length > 0
            text: root._subtitle
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
            elide: Text.ElideRight
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: root._statusLine.length > 0
            text: root._statusLine
            color: root._statusColor
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
            font.bold: root.actionState === "rejected"
            elide: Text.ElideRight
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
