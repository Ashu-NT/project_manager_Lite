import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string moduleCode: ""
    property string moduleLabel: ""
    property string currentStatus: ""
    property var statusOptions: []

    signal statusConfirmed(string moduleCode, string lifecycleStatus)

    modal: true
    focus: true
    width: 480
    title: "Module Lifecycle"
    subtitle: root.moduleLabel.length > 0
        ? root.moduleLabel
        : "Lifecycle state controls whether a licensed module can run at runtime."
    primaryText: "Apply"
    primaryIcon: "approve"
    onAccepted: root.statusConfirmed(root.moduleCode, root._selectedValue())
    onRejected: root.close()

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

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Lifecycle Status"

        AppControls.ComboBox {
            id: statusCombo
            Layout.fillWidth: true
            model: root.statusOptions
            textRole: "label"
        }
    }
}
