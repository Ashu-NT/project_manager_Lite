import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string moduleCode: ""
    property string moduleLabel: ""
    property string currentStatus: ""
    property var statusOptions: []

    signal statusConfirmed(string moduleCode, string lifecycleStatus)

    modal: true
    focus: true
    width: 480
    closePolicy: Popup.NoAutoClose
    title: "Module Lifecycle"

    function openForItem(itemData, options) {
        root.moduleCode = itemData && itemData.id ? String(itemData.id) : ""
        root.moduleLabel = itemData && itemData.title ? String(itemData.title) : ""
        root.currentStatus = itemData && itemData.state && itemData.state.lifecycleStatus
            ? String(itemData.state.lifecycleStatus)
            : "active"
        root.statusOptions = options || []
        _syncSelection()
        open()
    }

    function _syncSelection() {
        let selectedIndex = 0
        for (let index = 0; index < root.statusOptions.length; index += 1) {
            const option = root.statusOptions[index]
            if ((option.value || "") === root.currentStatus) {
                selectedIndex = index
                break
            }
        }
        statusCombo.currentIndex = selectedIndex
    }

    function _selectedValue() {
        if (statusCombo.currentIndex < 0 || statusCombo.currentIndex >= root.statusOptions.length) {
            return ""
        }
        return String(root.statusOptions[statusCombo.currentIndex].value || "")
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: root.moduleLabel.length > 0
                ? root.moduleLabel
                : "Select a lifecycle status for this module."
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            text: "Lifecycle state controls whether a licensed module can run at runtime."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        ComboBox {
            id: statusCombo

            Layout.fillWidth: true
            model: root.statusOptions
            textRole: "label"
        }
    }

    footer: Frame {
        padding: Theme.AppTheme.marginMd

        RowLayout {
            anchors.fill: parent
            spacing: Theme.AppTheme.spacingSm

            Item {
                Layout.fillWidth: true
            }

            Button {
                text: "Cancel"
                onClicked: root.close()
            }

            AppControls.PrimaryButton {
                text: "Apply"
                enabled: root.moduleCode.length > 0 && root._selectedValue().length > 0
                onClicked: root.statusConfirmed(root.moduleCode, root._selectedValue())
            }
        }
    }
}
