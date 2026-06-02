pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string mode: "create"
    property var draft: ({})
    property var roleOptions: []

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 560
    title: root.mode === "create" ? "New User" : "Edit User"

    primaryText: root.mode === "create" ? "Create" : "Save"
    primaryIcon: root.mode === "create" ? "add" : "save"
    primaryEnabled: usernameField.text.trim().length > 0 && (root.mode === "edit" || passwordField.text.length > 0)
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function submitDialog() {
        if (usernameField.text.trim().length === 0) {
            root.errorMessage = "Username is required."
            return
        }
        if (root.mode === "create" && passwordField.text.length === 0) {
            root.errorMessage = "A password is required for a new user."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root.mode, root.formData)
    }

    readonly property var formData: ({
        userId: root.draft.userId || root.draft.id || "",
        username: usernameField.text.trim(),
        displayName: displayNameField.text.trim(),
        email: emailField.text.trim(),
        password: passwordField.text,
        roleNames: _selectedRoleNames(),
        currentRoleNames: root.draft.currentRoleNames || root.draft.roleNames || [],
        isActive: activeCheck.checked,
        currentIsActive: root.draft.currentIsActive !== undefined ? root.draft.currentIsActive : activeCheck.checked
    })

    function openForCreate(options) {
        root.mode = "create"
        root.draft = ({})
        _assignOptions(options || ({}))
        _loadDraft()
        open()
    }

    function openForEdit(draftData, options) {
        root.mode = "edit"
        root.draft = draftData || ({})
        _assignOptions(options || ({}))
        _loadDraft()
        open()
    }

    function _assignOptions(options) {
        root.roleOptions = options.roleOptions || []
        _reloadRoles()
    }

    function _loadDraft() {
        usernameField.text = root.draft.username || ""
        displayNameField.text = root.draft.displayName || ""
        emailField.text = root.draft.email || ""
        passwordField.text = ""
        activeCheck.checked = root.draft.isActive !== undefined ? root.draft.isActive : true
        _reloadRoles()
    }

    function _reloadRoles() {
        roleModel.clear()
        const selected = root.draft.roleNames || []
        for (let index = 0; index < root.roleOptions.length; index += 1) {
            const option = root.roleOptions[index]
            roleModel.append({
                label: option.label || "",
                value: option.value || "",
                supportingText: option.supportingText || "",
                selected: selected.indexOf(option.value) !== -1
            })
        }
    }

    function _selectedRoleNames() {
        const values = []
        for (let index = 0; index < roleModel.count; index += 1) {
            const option = roleModel.get(index)
            if (option.selected) {
                values.push(option.value)
            }
        }
        return values
    }

    ListModel {
        id: roleModel
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Username"
        required: true

        AppControls.TextField {
            id: usernameField
            Layout.fillWidth: true
            placeholderText: "e.g. jsmith"
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Display Name"

            AppControls.TextField {
                id: displayNameField
                Layout.fillWidth: true
                placeholderText: "e.g. Jane Smith"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Email"

            AppControls.TextField {
                id: emailField
                Layout.fillWidth: true
                placeholderText: "name@company.com"
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Password"
        required: root.mode === "create"
        helperText: root.mode === "create" ? "" : "Leave blank to keep the current password."

        AppControls.TextField {
            id: passwordField
            Layout.fillWidth: true
            placeholderText: root.mode === "create"
                ? "Set an initial password"
                : "Reset password (optional)"
            echoMode: TextInput.Password
        }
    }

    AppControls.CheckBox {
        id: activeCheck

        text: "Active account"
    }

    ColumnLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingSm

        AppControls.Label {
            Layout.fillWidth: true
            text: "Roles"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
        }

        Repeater {
            model: roleModel

            delegate: AppControls.CheckBox {
                required property int index
                required property string label
                required property bool selected

                text: label
                checked: selected
                onToggled: roleModel.setProperty(index, "selected", checked)
            }
        }
    }
}
