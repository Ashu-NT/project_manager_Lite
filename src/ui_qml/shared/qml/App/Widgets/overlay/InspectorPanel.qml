pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts

import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

Rectangle {
    id: root

    // Header
    property string title: ""
    property string statusLabel: ""
    property string statusTone: ""
    property bool showHeader: true

    // Metadata
    property var sections: []
    property var groups: []

    
    // Actions
    property bool busy: false

    property string editActionLabel: "Edit"
    property bool showEditAction: true

    property string secondaryActionLabel: ""
    property bool showSecondaryAction: false

    property string viewDetailsLabel: "View Details"
    property bool showViewDetailsAction: false
    property bool viewDetailsPrimary: false

    property var menuActions: []
    property string menuTriggerLabel: "Actions"


    // Layout
    //
    // Configurable sizing API (all opt-in, default -1 = unset): a consumer
    // that only ever needs a narrower inspector (e.g. a Detail-page
    // contextual inspector, as opposed to the main workspace list/Inspector
    // pattern) can declare preferredWidth/minimumWidth/maximumWidth instead
    // of hardcoding panelWidth. Leaving all three unset keeps today's exact
    // behavior: panelWidth === Theme.AppTheme.inspectorWidth. A consumer
    // that reports how much horizontal space it actually has available
    // (availableWidth) lets the panel shrink toward minimumWidth under
    // pressure and grow back up to maximumWidth (the shared normal width,
    // by default) when there's room — rather than every consumer
    // reimplementing its own clamp expression.
    property int preferredWidth: -1
    property int minimumWidth: -1
    property int maximumWidth: -1
    property real availableWidth: -1

    readonly property int _effectivePreferred: root.preferredWidth > 0
        ? root.preferredWidth
        : Theme.AppTheme.inspectorWidth
    readonly property int _effectiveMinimum: root.minimumWidth > 0
        ? root.minimumWidth
        : root._effectivePreferred
    readonly property int _effectiveMaximum: root.maximumWidth > 0
        ? root.maximumWidth
        : Math.max(root._effectivePreferred, Theme.AppTheme.inspectorWidth)

    property int panelWidth: root.availableWidth > 0
        ? Math.max(root._effectiveMinimum, Math.min(root.availableWidth, root._effectiveMaximum))
        : root._effectivePreferred

    readonly property int labelColumnWidth:Theme.AppTheme.inspectorLabelWidth


    // Extra content slot
    default property alias extraContent: _extraSlot.data

    
    // Signals
    signal closeRequested()
    signal editRequested()
    signal secondaryActionRequested()
    signal viewDetailsRequested()
    signal menuActionTriggered(string id)

    
    // Root appearance
    color: Theme.AppTheme.surface

    implicitWidth: root.panelWidth

    // Swallow background clicks so they don't propagate to any
    // click-outside handler behind the inspector.
    MouseArea {
        anchors.fill: parent
    }

    // Left panel divider.
    Rectangle {
        anchors {
            top: parent.top
            bottom: parent.bottom
            left: parent.left
        }

        width: Theme.AppTheme.borderWidthThin
        color: Theme.AppTheme.divider
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // HEADER
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight:
                root.showHeader
                    ? Theme.AppTheme.panelHeaderHeight
                    : 0

            visible: root.showHeader
            color: Theme.AppTheme.surfaceRaised

            Rectangle {
                anchors {
                    left: parent.left
                    right: parent.right
                    bottom: parent.bottom
                }

                height: Theme.AppTheme.borderWidthThin
                color: Theme.AppTheme.divider
            }

            RowLayout {
                anchors {
                    fill: parent
                    leftMargin: Theme.AppTheme.marginMd
                    rightMargin: Theme.AppTheme.spacingSm
                }

                spacing: Theme.AppTheme.spacingSm

                AppControls.Label {
                    Layout.fillWidth: true

                    text: root.title.length > 0
                        ? root.title
                        : "Details"

                    color: Theme.AppTheme.textPrimary

                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                    font.weight: Theme.AppTheme.weightSemibold

                    elide: Text.ElideRight
                }

                AppWidgets.StatusChip {
                    visible: root.statusLabel.length > 0

                    status: root.statusLabel
                    tone: root.statusTone
                }

                Rectangle {
                    id: _closeButton

                    Layout.preferredWidth: 26
                    Layout.preferredHeight: 26

                    radius: Theme.AppTheme.radiusSm

                    color: _closeMouseArea.containsMouse
                        ? Theme.AppTheme.hoverSurface
                        : "transparent"

                    AppIcons.AppIcon {
                        anchors.centerIn: parent

                        name: "close"
                        size: Theme.AppTheme.iconXs
                        iconColor: Theme.AppTheme.textMuted
                    }

                    MouseArea {
                        id: _closeMouseArea

                        anchors.fill: parent

                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor

                        onClicked: root.closeRequested()
                    }
                }
            }
        }

        // BODY
        Flickable {
            id: _body

            Layout.fillWidth: true
            Layout.fillHeight: true

            contentWidth: width

            contentHeight:
                _panelContent.implicitHeight
                + Theme.AppTheme.marginMd * 2

            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: _panelContent

                x: Theme.AppTheme.marginMd
                y: Theme.AppTheme.marginMd

                width:
                    parent.width
                    - Theme.AppTheme.marginMd * 2

                spacing: Theme.AppTheme.sectionGap

                // FLAT METADATA
                Repeater {
                    model:
                        root.groups.length > 0
                            ? []
                            : root.sections

                    delegate: AppWidgets.LabelValueRow {
                        required property var modelData

                        Layout.fillWidth: true

                        label:
                            String(modelData.label || "")

                        value:
                            String(modelData.value || "")

                        labelWidth:
                            root.labelColumnWidth
                    }
                }

                // GROUPED METADATA
                Repeater {
                    model: root.groups

                    delegate: ColumnLayout {
                        id: groupDelegate

                        required property var modelData

                        readonly property var _rows:
                            groupDelegate.modelData.rows || []

                        readonly property bool _hasContent: {
                            for (
                                let i = 0;
                                i < groupDelegate._rows.length;
                                i += 1
                            ) {
                                if (
                                    String(
                                        groupDelegate._rows[i].value || ""
                                    ).length > 0
                                ) {
                                    return true
                                }
                            }

                            return false
                        }

                        Layout.fillWidth: true

                        spacing: Theme.AppTheme.inspectorRowGap

                        visible:
                            groupDelegate._hasContent

                        // Group heading
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 28

                            radius: Theme.AppTheme.radiusSm
                            color: Theme.AppTheme.surfaceAlt

                            AppControls.Label {
                                anchors {
                                    left: parent.left
                                    leftMargin: Theme.AppTheme.spacingSm
                                    verticalCenter: parent.verticalCenter
                                }

                                text: String(groupDelegate.modelData.title || "").toUpperCase()
                                color: Theme.AppTheme.textSecondary

                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.typeMetadataSize
                                font.weight: Theme.AppTheme.weightSemibold
                                font.letterSpacing: 0.5
                            }
                        }

                        // Group rows
                        Repeater {
                            model: groupDelegate._rows

                            delegate: AppWidgets.LabelValueRow {
                                required property var modelData

                                Layout.fillWidth: true

                                label:
                                    String(modelData.label || "")

                                value:
                                    String(modelData.value || "")

                                labelWidth:
                                    root.labelColumnWidth
                            }
                        }
                    }
                }

                // CUSTOM ENTITY-SPECIFIC CONTENT
                ColumnLayout {
                    id: _extraSlot

                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm
                }

                // ACTION SEPARATOR
                Rectangle {
                    Layout.fillWidth: true
                    Layout.topMargin:
                        Theme.AppTheme.spacingXs

                    Layout.preferredHeight:
                        Theme.AppTheme.borderWidthThin

                    color: Theme.AppTheme.divider
                }

                // PRIMARY DETAILS ACTION

                AppControls.PrimaryButton {
                    Layout.fillWidth: true

                    visible:
                        root.showViewDetailsAction
                        && root.viewDetailsPrimary

                    text: root.viewDetailsLabel

                    iconName: "chevron_right"

                    enabled: !root.busy

                    onClicked:
                        root.viewDetailsRequested()
                }

                // SECONDARY ACTION ROW
                RowLayout {
                    Layout.fillWidth: true

                    spacing: Theme.AppTheme.spacingXs

                    // Edit as primary when details is not primary
                    AppControls.PrimaryButton {
                        Layout.fillWidth: true

                        visible:
                            root.showEditAction
                            && !root.viewDetailsPrimary

                        text: root.editActionLabel

                        iconName: "edit"

                        enabled: !root.busy

                        onClicked:
                            root.editRequested()
                    }

                    // Edit as secondary when Open Details is primary
                    AppControls.SecondaryButton {
                        Layout.fillWidth: true

                        visible:
                            root.showEditAction
                            && root.viewDetailsPrimary

                        text: root.editActionLabel

                        iconName: "edit"

                        enabled: !root.busy

                        onClicked:
                            root.editRequested()
                    }

                    // Optional explicit secondary action
                    AppControls.SecondaryButton {
                        visible:
                            root.showSecondaryAction

                        text:
                            root.secondaryActionLabel

                        iconName: "approve"

                        enabled: !root.busy

                        onClicked:
                            root.secondaryActionRequested()
                    }

                    // Actions menu
                    AppWidgets.ActionsMenuButton {
                        visible:
                            root.menuActions.length > 0

                        enabled:
                            !root.busy

                        items:
                            root.menuActions

                        triggerLabel:
                            root.menuTriggerLabel

                        onActionSelected: function(id) {
                            root.menuActionTriggered(id)
                        }
                    }
                }

                // DETAILS AS SECONDARY
                AppControls.SecondaryButton {
                    Layout.fillWidth: true

                    visible:
                        root.showViewDetailsAction
                        && !root.viewDetailsPrimary

                    text:
                        root.viewDetailsLabel

                    iconName:
                        "chevron_right"

                    enabled:
                        !root.busy

                    onClicked:
                        root.viewDetailsRequested()
                }
            }
        }
    }
}