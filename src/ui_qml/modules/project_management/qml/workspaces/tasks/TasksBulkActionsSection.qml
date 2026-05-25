import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    property var statusOptions: []
    property int selectedTaskCount: 0
    property int selectedTaskDoneCount: 0
    property int visibleTaskCount: 0
    property bool isBusy: false
    property bool canUndoTaskAction: false
    property bool canRedoTaskAction: false
    property string undoLabel: ""
    property string redoLabel: ""
    property string selectedStatusValue: ""

    signal selectVisibleRequested()
    signal clearRequested()
    signal applyStatusRequested(var payload)
    signal bulkDeleteRequested()
    signal undoRequested()
    signal redoRequested()

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function syncSelectedStatusValue() {
        if (root.statusOptions.length === 0) {
            root.selectedStatusValue = ""
            return
        }
        if (!root.selectedStatusValue) {
            root.selectedStatusValue = String(root.statusOptions[0].value || "")
            return
        }
        for (var index = 0; index < root.statusOptions.length; index += 1) {
            if (String(root.statusOptions[index].value || "") === root.selectedStatusValue) {
                return
            }
        }
        root.selectedStatusValue = String(root.statusOptions[0].value || "")
    }

    onStatusOptionsChanged: syncSelectedStatusValue()
    Component.onCompleted: syncSelectedStatusValue()

    implicitHeight: contentLayout.implicitHeight

    ColumnLayout {
        id: contentLayout

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Bulk Actions"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: root.selectedTaskCount > 0
                        ? String(root.selectedTaskCount) + " task(s) selected for bulk actions."
                        : "Select one or more tasks to apply status changes or delete in bulk."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            AppControls.SecondaryButton {
                text: "Select Visible"
                iconName: "view"
                enabled: !root.isBusy && root.visibleTaskCount > 0
                onClicked: root.selectVisibleRequested()
            }

            AppControls.SecondaryButton {
                text: "Clear"
                iconName: "close"
                enabled: !root.isBusy && root.selectedTaskCount > 0
                onClicked: root.clearRequested()
            }

            AppControls.SecondaryButton {
                text: "Undo"
                iconName: "history"
                enabled: !root.isBusy && root.canUndoTaskAction
                onClicked: root.undoRequested()

                ToolTip.visible: hovered && root.undoLabel.length > 0
                ToolTip.text: root.undoLabel
            }

            AppControls.SecondaryButton {
                text: "Redo"
                iconName: "history"
                enabled: !root.isBusy && root.canRedoTaskAction
                onClicked: root.redoRequested()

                ToolTip.visible: hovered && root.redoLabel.length > 0
                ToolTip.text: root.redoLabel
            }
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: root.selectedTaskDoneCount > 0 && root.selectedStatusValue !== "DONE"
            text: String(root.selectedTaskDoneCount) + " completed task(s) will be reopened by this status change."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            AppControls.ComboBox {
                id: statusCombo
                Layout.preferredWidth: 220
                model: root.statusOptions
                textRole: "label"
                enabled: !root.isBusy && root.selectedTaskCount > 0
                currentIndex: root.indexForValue(root.statusOptions, root.selectedStatusValue)

                onActivated: function(index) {
                    var option = root.statusOptions[index]
                    if (option) {
                        root.selectedStatusValue = String(option.value || "")
                    }
                }
            }

            AppControls.TextField {
                id: reopenPercentField
                Layout.preferredWidth: 160
                visible: root.selectedTaskDoneCount > 0 && root.selectedStatusValue === "IN_PROGRESS"
                enabled: !root.isBusy && root.selectedTaskCount > 0
                placeholderText: "Reopen %"
                text: "50"
            }

            AppControls.PrimaryButton {
                text: "Apply Status"
                iconName: "approve"
                enabled: !root.isBusy && root.selectedTaskCount > 0 && root.selectedStatusValue.length > 0
                onClicked: root.applyStatusRequested({
                    "status": root.selectedStatusValue,
                    "reopenPercentComplete": reopenPercentField.visible ? reopenPercentField.text : ""
                })
            }

            AppControls.SecondaryButton {
                text: "Bulk Delete"
                iconName: "delete"
                danger: true
                enabled: !root.isBusy && root.selectedTaskCount > 1
                onClicked: root.bulkDeleteRequested()
            }

            Item {
                Layout.fillWidth: true
            }
        }
    }
}
