pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string mode: "create"
    property var draft: ({})
    property var moduleOptions: []

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 560
    title: root.mode === "create" ? "New Organization" : "Edit Organization"
    primaryText: root.mode === "create" ? "Create" : "Save"
    primaryIcon: root.mode === "create" ? "add" : "save"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function submitDialog() {
        if (organizationCodeField.text.trim().length === 0) {
            root.errorMessage = "Organization code is required."
            return
        }
        if (displayNameField.text.trim().length === 0) {
            root.errorMessage = "Display name is required."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root.mode, root.formData)
    }

    readonly property var formData: ({
        organizationId: root.draft.organizationId || root.draft.id || "",
        expectedVersion: root.draft.version || 0,
        organizationCode: organizationCodeField.text.trim(),
        displayName: displayNameField.text.trim(),
        timezoneName: timezoneField.text.trim(),
        baseCurrency: currencyField.text.trim().toUpperCase(),
        isActive: activeCheck.checked,
        initialModuleCodes: _selectedModuleCodes()
    })

    function openForCreate(options) {
        root.mode = "create"
        root.draft = ({})
        root.moduleOptions = options || []
        _loadDraft()
        open()
    }

    function openForEdit(draftData) {
        root.mode = "edit"
        root.draft = draftData || ({})
        _loadDraft()
        open()
    }

    function _loadDraft() {
        organizationCodeField.text = root.draft.organizationCode || ""
        displayNameField.text = root.draft.displayName || ""
        timezoneField.text = root.draft.timezoneName || "UTC"
        currencyField.text = root.draft.baseCurrency || "USD"
        activeCheck.checked = root.draft.isActive !== undefined ? root.draft.isActive : true
        _reloadModules()
    }

    function _reloadModules() {
        moduleModel.clear()
        const selected = root.draft.initialModuleCodes || []
        for (let index = 0; index < root.moduleOptions.length; index += 1) {
            const option = root.moduleOptions[index]
            moduleModel.append({
                label: option.label || "",
                value: option.value || "",
                supportingText: option.supportingText || "",
                selected: selected.indexOf(option.value) !== -1
            })
        }
    }

    function _selectedModuleCodes() {
        const values = []
        for (let index = 0; index < moduleModel.count; index += 1) {
            const option = moduleModel.get(index)
            if (option.selected) {
                values.push(option.value)
            }
        }
        return values
    }

    ListModel {
        id: moduleModel
    }

    AppControls.TextField {
        id: organizationCodeField

        Layout.fillWidth: true
        placeholderText: "Organization code"
    }

    AppControls.TextField {
        id: displayNameField

        Layout.fillWidth: true
        placeholderText: "Display name"
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppControls.TextField {
            id: timezoneField

            Layout.fillWidth: true
            placeholderText: "Timezone"
        }

        AppControls.TextField {
            id: currencyField

            Layout.preferredWidth: 120
            placeholderText: "Currency"
        }
    }

    AppControls.CheckBox {
        id: activeCheck

        text: "Active organization"
    }

    ColumnLayout {
        Layout.fillWidth: true
        visible: root.mode === "create"
        spacing: Theme.AppTheme.spacingSm

        AppControls.Label {
            Layout.fillWidth: true
            text: "Initial modules"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
        }

        AppControls.Label {
            Layout.fillWidth: true
            text: "Choose the modules available immediately after organization provisioning."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: moduleModel

            delegate: AppControls.CheckBox {
                required property int index
                required property string label
                required property bool selected

                text: label
                checked: selected
                onToggled: moduleModel.setProperty(index, "selected", checked)
            }
        }
    }
}
