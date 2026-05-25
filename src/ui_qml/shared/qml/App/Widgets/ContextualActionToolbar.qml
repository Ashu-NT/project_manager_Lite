pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

// Contextual action toolbar for a selected record.
// Sits below the DataTable toolbar; visible while a record is selected.
// actions: [{id, label, icon, enabled, danger}]
Rectangle {
    id: root

    property string title:       ""
    property string subtitle:    ""
    property bool   busy:        false
    property bool   showBack:    false
    property string createLabel: ""
    property var    actions:     []

    signal backRequested()
    signal createRequested()
    signal actionTriggered(string id)

    implicitHeight: Theme.AppTheme.panelHeaderHeight
    color:          Theme.AppTheme.surfaceAlt

    Rectangle {
        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
        height: 1; color: Theme.AppTheme.divider
    }

    RowLayout {
        anchors.fill:        parent
        anchors.leftMargin:  Theme.AppTheme.marginMd
        anchors.rightMargin: 8
        spacing:             Theme.AppTheme.spacingXs

        // Back button
        Rectangle {
            visible: root.showBack
            Layout.preferredWidth: 26; Layout.preferredHeight: 26; radius: 4
            color: _backMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

            AppIcons.AppIcon {
                anchors.centerIn: parent
                name: "chevron_left"; size: Theme.AppTheme.headerIconSize
                iconColor: Theme.AppTheme.textMuted
            }

            MouseArea {
                id: _backMA
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                enabled: !root.busy
                onClicked: root.backRequested()
            }
        }

        // Title
        AppControls.Label {
            visible:        root.title.length > 0
            text:           root.title
            color:          Theme.AppTheme.textPrimary
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.sectionTitleSize
            font.bold:      true
            elide:          Text.ElideRight
            Layout.maximumWidth: 200
        }

        // Subtitle
        AppControls.Label {
            visible:        root.subtitle.length > 0
            text:           root.subtitle
            color:          Theme.AppTheme.textMuted
            font.family:    Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.captionSize
            elide:          Text.ElideRight
            Layout.maximumWidth: 160
        }

        Item { Layout.fillWidth: true }

        // Dynamic action buttons
        Repeater {
            model: root.actions
            delegate: AppControls.SecondaryButton {
                required property var modelData
                text:     modelData.label  || ""
                iconName: modelData.icon   || ""
                danger:   modelData.danger || false
                enabled:  !root.busy && (modelData.enabled !== false)
                onClicked: root.actionTriggered(String(modelData.id || ""))
            }
        }

        // Separator before create
        Rectangle {
            visible: root.createLabel.length > 0 && root.actions.length > 0
            Layout.preferredWidth: 1; Layout.preferredHeight: 14
            color: Theme.AppTheme.divider
        }

        // Create button
        AppControls.PrimaryButton {
            visible:  root.createLabel.length > 0
            text:     root.createLabel
            iconName: "add"
            enabled:  !root.busy
            onClicked: root.createRequested()
        }
    }
}
