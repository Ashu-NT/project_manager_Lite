import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string mode: "create"
    property var draft: ({})
    property var roleOptions: []

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 560
    closePolicy: Popup.NoAutoClose
    title: root.mode === "create" ? "New User" : "Edit User"

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

    contentItem: ScrollView {
        implicitWidth: 520
        implicitHeight: 460
        clip: true

        ColumnLayout {
            width: parent.availableWidth
            spacing: Theme.AppTheme.spacingMd

            TextField {
                id: usernameField

                Layout.fillWidth: true
                placeholderText: "Username"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: displayNameField

                    Layout.fillWidth: true
                    placeholderText: "Display name"
                }

                TextField {
                    id: emailField

                    Layout.fillWidth: true
                    placeholderText: "Email"
                }
            }

            TextField {
                id: passwordField

                Layout.fillWidth: true
                placeholderText: root.mode === "create"
                    ? "Password"
                    : "Reset password (optional)"
                echoMode: TextInput.Password
            }

            CheckBox {
                id: activeCheck

                text: "Active account"
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingSm

                Label {
                    Layout.fillWidth: true
                    text: "Roles"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                }

                Repeater {
                    model: roleModel

                    delegate: CheckBox {
                        text: model.label
                        checked: model.selected
                        onToggled: roleModel.setProperty(index, "selected", checked)
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
                enabled: usernameField.text.trim().length > 0
                    && (root.mode === "edit" || passwordField.text.length > 0)
                text: root.mode === "create" ? "Create" : "Save"
                onClicked: root.saveRequested(root.mode, root.formData)
            }
        }
    }
}
