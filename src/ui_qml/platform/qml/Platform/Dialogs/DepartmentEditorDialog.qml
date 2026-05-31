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
    property var siteOptions: []
    property var locationOptions: []
    property var parentOptions: []

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 620
    title: root.mode === "create" ? "New Department" : "Edit Department"
    primaryText: root.mode === "create" ? "Create" : "Save"
    primaryIcon: root.mode === "create" ? "add" : "save"
    onAccepted: root.saveRequested(root.mode, root.formData)
    onRejected: root.close()

    readonly property var formData: ({
        departmentId: root.draft.departmentId || root.draft.id || "",
        expectedVersion: root.draft.version || 0,
        departmentCode: departmentCodeField.text.trim(),
        name: nameField.text.trim(),
        description: descriptionField.text.trim(),
        siteId: _currentValue(siteModel, siteCombo),
        defaultLocationId: _currentValue(locationModel, locationCombo),
        parentDepartmentId: _currentValue(parentModel, parentCombo),
        departmentType: departmentTypeField.text.trim(),
        costCenterCode: costCenterField.text.trim(),
        notes: notesField.text.trim(),
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
        root.locationOptions = options.locationOptions || []
        root.parentOptions = options.parentOptions || []
        _reloadOptionModel(siteModel, root.siteOptions)
        _reloadOptionModel(locationModel, root.locationOptions)
        _reloadOptionModel(parentModel, root.parentOptions, root.draft.departmentId || root.draft.id || "")
    }

    function _reloadOptionModel(model, options, excludedValue) {
        model.clear()
        model.append({ label: "Not set", value: "" })
        for (let index = 0; index < options.length; index += 1) {
            const option = options[index]
            if ((excludedValue || "") !== "" && option.value === excludedValue) {
                continue
            }
            model.append({
                label: option.label || "",
                value: option.value || ""
            })
        }
    }

    function _loadDraft() {
        departmentCodeField.text = root.draft.departmentCode || ""
        nameField.text = root.draft.name || ""
        descriptionField.text = root.draft.description || ""
        departmentTypeField.text = root.draft.departmentType || ""
        costCenterField.text = root.draft.costCenterCode || ""
        notesField.text = root.draft.notes || ""
        activeCheck.checked = root.draft.isActive !== undefined ? root.draft.isActive : true
        _setCurrentIndex(siteModel, siteCombo, root.draft.siteId || "")
        _setCurrentIndex(locationModel, locationCombo, root.draft.defaultLocationId || "")
        _setCurrentIndex(parentModel, parentCombo, root.draft.parentDepartmentId || "")
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

    ListModel { id: siteModel }
    ListModel { id: locationModel }
    ListModel { id: parentModel }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppControls.TextField {
            id: departmentCodeField

            Layout.preferredWidth: 180
            placeholderText: "Department code"
        }

        AppControls.TextField {
            id: nameField

            Layout.fillWidth: true
            placeholderText: "Department name"
        }
    }

    AppControls.TextField {
        id: descriptionField

        Layout.fillWidth: true
        placeholderText: "Description"
    }

    AppControls.ComboBox {
        id: siteCombo

        Layout.fillWidth: true
        model: siteModel
        textRole: "label"
    }

    AppControls.ComboBox {
        id: locationCombo

        Layout.fillWidth: true
        model: locationModel
        textRole: "label"
    }

    AppControls.ComboBox {
        id: parentCombo

        Layout.fillWidth: true
        model: parentModel
        textRole: "label"
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppControls.TextField {
            id: departmentTypeField

            Layout.fillWidth: true
            placeholderText: "Department type"
        }

        AppControls.TextField {
            id: costCenterField

            Layout.fillWidth: true
            placeholderText: "Cost center"
        }
    }

    AppControls.TextArea {
        id: notesField

        Layout.fillWidth: true
        Layout.preferredHeight: 96
        placeholderText: "Notes"
        wrapMode: TextEdit.WordWrap
    }

    AppControls.CheckBox {
        id: activeCheck

        text: "Active department"
    }
}
