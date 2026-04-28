import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string mode: "create"
    property var draft: ({})
    property var siteOptions: []
    property var departmentOptions: []

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 620
    closePolicy: Popup.NoAutoClose
    title: root.mode === "create" ? "New Employee" : "Edit Employee"

    readonly property var formData: ({
        employeeId: root.draft.employeeId || root.draft.id || "",
        expectedVersion: root.draft.version || 0,
        employeeCode: employeeCodeField.text.trim(),
        fullName: fullNameField.text.trim(),
        departmentId: _currentValue(departmentModel, departmentCombo),
        departmentName: _currentLabel(departmentModel, departmentCombo),
        siteId: _currentValue(siteModel, siteCombo),
        siteName: _currentLabel(siteModel, siteCombo),
        title: titleField.text.trim(),
        employmentType: _currentValue(employmentTypeModel, employmentTypeCombo) || "FULL_TIME",
        email: emailField.text.trim(),
        phone: phoneField.text.trim(),
        isActive: activeCheck.checked
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
        root.siteOptions = options.siteOptions || []
        root.departmentOptions = options.departmentOptions || []
        _reloadOptionModel(siteModel, root.siteOptions)
        _reloadOptionModel(departmentModel, root.departmentOptions)
    }

    function _reloadOptionModel(model, options) {
        model.clear()
        model.append({ label: "Not set", value: "" })
        for (let index = 0; index < options.length; index += 1) {
            const option = options[index]
            model.append({
                label: option.label || "",
                value: option.value || ""
            })
        }
    }

    function _loadDraft() {
        employeeCodeField.text = root.draft.employeeCode || ""
        fullNameField.text = root.draft.fullName || ""
        titleField.text = root.draft.title || ""
        emailField.text = root.draft.email || ""
        phoneField.text = root.draft.phone || ""
        activeCheck.checked = root.draft.isActive !== undefined ? root.draft.isActive : true
        _setCurrentIndex(siteModel, siteCombo, root.draft.siteId || "")
        _setCurrentIndex(departmentModel, departmentCombo, root.draft.departmentId || "")
        _setCurrentIndex(employmentTypeModel, employmentTypeCombo, root.draft.employmentType || "FULL_TIME")
    }

    function _setCurrentIndex(model, combo, value) {
        for (let index = 0; index < model.count; index += 1) {
            if (model.get(index).value === value) {
                combo.currentIndex = index
                return
            }
        }
        combo.currentIndex = 0
    }

    function _currentValue(model, combo) {
        if (combo.currentIndex < 0 || combo.currentIndex >= model.count) {
            return ""
        }
        return model.get(combo.currentIndex).value || ""
    }

    function _currentLabel(model, combo) {
        if (combo.currentIndex <= 0 || combo.currentIndex >= model.count) {
            return ""
        }
        return model.get(combo.currentIndex).label || ""
    }

    ListModel { id: siteModel }
    ListModel { id: departmentModel }
    ListModel {
        id: employmentTypeModel

        ListElement { label: "Full Time"; value: "FULL_TIME" }
        ListElement { label: "Part Time"; value: "PART_TIME" }
        ListElement { label: "Contractor"; value: "CONTRACTOR" }
        ListElement { label: "Temporary"; value: "TEMPORARY" }
    }

    contentItem: ScrollView {
        implicitWidth: 580
        implicitHeight: 470
        clip: true

        ColumnLayout {
            width: parent.availableWidth
            spacing: Theme.AppTheme.spacingMd

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: employeeCodeField

                    Layout.preferredWidth: 180
                    placeholderText: "Employee code"
                }

                TextField {
                    id: fullNameField

                    Layout.fillWidth: true
                    placeholderText: "Full name"
                }
            }

            ComboBox {
                id: departmentCombo

                Layout.fillWidth: true
                model: departmentModel
                textRole: "label"
            }

            ComboBox {
                id: siteCombo

                Layout.fillWidth: true
                model: siteModel
                textRole: "label"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: titleField

                    Layout.fillWidth: true
                    placeholderText: "Job title"
                }

                ComboBox {
                    id: employmentTypeCombo

                    Layout.fillWidth: true
                    model: employmentTypeModel
                    textRole: "label"
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: emailField

                    Layout.fillWidth: true
                    placeholderText: "Email"
                }

                TextField {
                    id: phoneField

                    Layout.fillWidth: true
                    placeholderText: "Phone"
                }
            }

            CheckBox {
                id: activeCheck

                text: "Active employee"
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
                enabled: employeeCodeField.text.trim().length > 0
                    && fullNameField.text.trim().length > 0
                text: root.mode === "create" ? "Create" : "Save"
                onClicked: root.saveRequested(root.mode, root.formData)
            }
        }
    }
}
