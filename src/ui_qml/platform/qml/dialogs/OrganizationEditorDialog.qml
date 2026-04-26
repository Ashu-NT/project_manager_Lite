import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string mode: "create"
    property var draft: ({})
    property var moduleOptions: []

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 560
    closePolicy: Popup.NoAutoClose
    title: root.mode === "create" ? "New Organization" : "Edit Organization"

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

    contentItem: ScrollView {
        implicitWidth: 520
        implicitHeight: 420
        clip: true

        ColumnLayout {
            width: parent.availableWidth
            spacing: Theme.AppTheme.spacingMd

            TextField {
                id: organizationCodeField

                Layout.fillWidth: true
                placeholderText: "Organization code"
            }

            TextField {
                id: displayNameField

                Layout.fillWidth: true
                placeholderText: "Display name"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: timezoneField

                    Layout.fillWidth: true
                    placeholderText: "Timezone"
                }

                TextField {
                    id: currencyField

                    Layout.preferredWidth: 120
                    placeholderText: "Currency"
                }
            }

            CheckBox {
                id: activeCheck

                text: "Active organization"
            }

            ColumnLayout {
                Layout.fillWidth: true
                visible: root.mode === "create"
                spacing: Theme.AppTheme.spacingSm

                Label {
                    Layout.fillWidth: true
                    text: "Initial modules"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                Label {
                    Layout.fillWidth: true
                    text: "Choose the modules available immediately after organization provisioning."
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: moduleModel

                    delegate: CheckBox {
                        text: model.label
                        checked: model.selected
                        onToggled: moduleModel.setProperty(index, "selected", checked)
                    }
                }
            }
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
                enabled: organizationCodeField.text.trim().length > 0
                    && displayNameField.text.trim().length > 0
                    && timezoneField.text.trim().length > 0
                    && currencyField.text.trim().length > 0
                text: root.mode === "create" ? "Create" : "Save"
                onClicked: root.saveRequested(root.mode, root.formData)
            }
        }
    }
}
