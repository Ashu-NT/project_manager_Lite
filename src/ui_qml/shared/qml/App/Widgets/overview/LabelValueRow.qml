import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property string label: ""
    property string value: ""
    property int labelWidth: Theme.AppTheme.inspectorLabelWidth
    property bool showDivider: false

    visible: root.value.length > 0

    Layout.fillWidth: true

    implicitHeight: Math.max(
        Theme.AppTheme.inspectorMetadataRowHeight,
        rowLayout.implicitHeight + 2
    )

    GridLayout {
        id: rowLayout

        anchors {
            left: parent.left
            right: parent.right
            verticalCenter: parent.verticalCenter
        }

        columns: 2
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: 0

        // -------------------------------------------------------------
        // Label
        // -------------------------------------------------------------

        AppControls.Label {
            id: labelText

            Layout.preferredWidth: root.labelWidth
            Layout.maximumWidth: root.labelWidth
            Layout.alignment: Qt.AlignTop

            text: root.label

            color: Theme.AppTheme.textMuted

            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.typeMetadataSize
            font.weight: Theme.AppTheme.weightRegular

            verticalAlignment: Text.AlignTop

            elide: Text.ElideRight
            maximumLineCount: 1

            ToolTip.visible:
                labelHover.containsMouse
                && labelText.truncated

            ToolTip.text: root.label
            ToolTip.delay: 250

            MouseArea {
                id: labelHover

                anchors.fill: parent

                hoverEnabled: true
                acceptedButtons: Qt.NoButton
                cursorShape:
                    labelText.truncated
                        ? Qt.WhatsThisCursor
                        : Qt.ArrowCursor
            }
        }

        // Value
        AppControls.Label {
            id: valueText

            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop

            text: root.value

            color: Theme.AppTheme.textPrimary

            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.typeSupportingTextSize
            font.weight: Theme.AppTheme.weightMedium

            verticalAlignment: Text.AlignTop

            wrapMode: Text.WrapAtWordBoundaryOrAnywhere
        }
    }

    // Optional divider for consumers that need stronger row separation.
    Rectangle {
        visible: root.showDivider

        anchors {
            left: parent.left
            right: parent.right
            bottom: parent.bottom
        }

        height: Theme.AppTheme.borderWidthThin
        color: Theme.AppTheme.divider
    }
}