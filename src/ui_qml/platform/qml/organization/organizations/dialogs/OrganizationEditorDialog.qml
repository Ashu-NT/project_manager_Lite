pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string mode: "create"
    property var draft: ({})
    property var moduleOptions: []
    property var workspaceController: null
    property string organizationCode: ""

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
        if (root.organizationCode.trim().length === 0) {
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
        organizationCode: root.organizationCode.trim(),
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
        root.organizationCode = root.draft.organizationCode || ""
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

    AppWidgets.CodeFieldRow {
        Layout.fillWidth: true
        label: "Organization Code"
        value: root.organizationCode
        placeholderText: "Auto-generated if empty"
        required: true
        generateVisible: true
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onValueEdited: function(code) { root.organizationCode = code }
        onGenerateRequested: {
            if (root.workspaceController) {
                const suggested = root.workspaceController.generateEntityCode("organization", root.formData)
                if (suggested && suggested.length > 0) {
                    root.organizationCode = suggested
                }
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Display Name"
        required: true

        AppControls.TextField {
            id: displayNameField
            Layout.fillWidth: true
            placeholderText: "e.g. Acme Industrial Group"
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Timezone"

            AppControls.TextField {
                id: timezoneField
                Layout.fillWidth: true
                placeholderText: "e.g. Europe/Amsterdam"
            }
        }

        AppWidgets.FormField {
            Layout.preferredWidth: 140
            label: "Currency"

            AppControls.TextField {
                id: currencyField
                Layout.fillWidth: true
                placeholderText: "e.g. EUR"
            }
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
