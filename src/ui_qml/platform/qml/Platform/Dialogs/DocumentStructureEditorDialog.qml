import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string mode: "create"
    property var draft: ({})
    property var parentOptions: []
    property var objectScopeOptions: []
    property var defaultTypeOptions: []

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 620
    closePolicy: Popup.NoAutoClose
    title: root.mode === "create" ? "New Document Structure" : "Edit Document Structure"

    readonly property var formData: ({
        structureId: root.draft.structureId || root.draft.id || "",
        expectedVersion: root.draft.version || 0,
        structureCode: structureCodeField.text.trim(),
        name: nameField.text.trim(),
        description: descriptionField.text.trim(),
        parentStructureId: _currentValue(parentModel, parentCombo),
        objectScope: _currentValue(scopeModel, scopeCombo) || "GENERAL",
        defaultDocumentType: _currentValue(typeModel, typeCombo) || "GENERAL",
        sortOrder: sortOrderSpin.value,
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
        root.parentOptions = options.parentOptions || []
        root.objectScopeOptions = options.objectScopeOptions || []
        root.defaultTypeOptions = options.defaultTypeOptions || []
        _reloadOptionModel(parentModel, root.parentOptions, root.draft.structureId || root.draft.id || "")
        _reloadOptionModel(scopeModel, root.objectScopeOptions, "")
        _reloadOptionModel(typeModel, root.defaultTypeOptions, "")
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
        structureCodeField.text = root.draft.structureCode || ""
        nameField.text = root.draft.name || ""
        descriptionField.text = root.draft.description || ""
        notesField.text = root.draft.notes || ""
        sortOrderSpin.value = root.draft.sortOrder || 0
        activeCheck.checked = root.draft.isActive !== undefined ? root.draft.isActive : true
        _setCurrentIndex(parentModel, parentCombo, root.draft.parentStructureId || "")
        _setCurrentIndex(scopeModel, scopeCombo, root.draft.objectScope || "GENERAL")
        _setCurrentIndex(typeModel, typeCombo, root.draft.defaultDocumentType || "GENERAL")
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

    ListModel { id: parentModel }
    ListModel { id: scopeModel }
    ListModel { id: typeModel }

    contentItem: ScrollView {
        implicitWidth: 580
        implicitHeight: 500
        clip: true

        ColumnLayout {
            width: parent.availableWidth
            spacing: Theme.AppTheme.spacingMd

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: structureCodeField

                    Layout.preferredWidth: 180
                    placeholderText: "Structure code"
                }

                TextField {
                    id: nameField

                    Layout.fillWidth: true
                    placeholderText: "Structure name"
                }
            }

            TextField {
                id: descriptionField

                Layout.fillWidth: true
                placeholderText: "Description"
            }

            ComboBox {
                id: parentCombo

                Layout.fillWidth: true
                model: parentModel
                textRole: "label"
            }

            ComboBox {
                id: scopeCombo

                Layout.fillWidth: true
                model: scopeModel
                textRole: "label"
            }

            ComboBox {
                id: typeCombo

                Layout.fillWidth: true
                model: typeModel
                textRole: "label"
            }

            SpinBox {
                id: sortOrderSpin

                Layout.fillWidth: true
                from: 0
                to: 9999
            }

            TextArea {
                id: notesField

                Layout.fillWidth: true
                Layout.preferredHeight: 96
                placeholderText: "Notes"
                wrapMode: TextEdit.WordWrap
            }

            CheckBox {
                id: activeCheck

                text: "Active structure"
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
                enabled: structureCodeField.text.trim().length > 0
                    && nameField.text.trim().length > 0
                text: root.mode === "create" ? "Create" : "Save"
                onClicked: root.saveRequested(root.mode, root.formData)
            }
        }
    }
}
