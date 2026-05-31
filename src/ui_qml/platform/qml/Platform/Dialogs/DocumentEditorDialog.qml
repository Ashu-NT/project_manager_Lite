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
    property var typeOptions: []
    property var structureOptions: []
    property var storageKindOptions: []

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 660
    title: root.mode === "create" ? "New Document" : "Edit Document"
    primaryText: root.mode === "create" ? "Create" : "Save"
    primaryIcon: root.mode === "create" ? "add" : "save"
    onOpened: root.errorMessage = ""
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function submitDialog() {
        if (documentCodeField.text.trim().length === 0) {
            root.errorMessage = "Document code is required."
            return
        }
        if (titleField.text.trim().length === 0) {
            root.errorMessage = "Document title is required."
            return
        }
        root.errorMessage = ""
        root.saveRequested(root.mode, root.formData)
    }

    readonly property var formData: ({
        documentId: root.draft.documentId || root.draft.id || "",
        expectedVersion: root.draft.version || 0,
        documentCode: documentCodeField.text.trim(),
        title: titleField.text.trim(),
        documentType: _currentValue(typeModel, typeCombo) || "GENERAL",
        documentStructureId: _currentValue(structureModel, structureCombo),
        storageKind: _currentValue(storageKindModel, storageKindCombo) || "FILE_PATH",
        storageUri: storageUriField.text.trim(),
        fileName: fileNameField.text.trim(),
        mimeType: mimeTypeField.text.trim(),
        sourceSystem: sourceSystemField.text.trim(),
        confidentialityLevel: confidentialityField.text.trim(),
        businessVersionLabel: versionField.text.trim(),
        isCurrent: currentCheck.checked,
        isActive: activeCheck.checked,
        notes: notesField.text.trim()
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
        root.typeOptions = options.typeOptions || []
        root.structureOptions = options.structureOptions || []
        root.storageKindOptions = options.storageKindOptions || []
        _reloadOptionModel(typeModel, root.typeOptions, "")
        _reloadOptionModel(structureModel, root.structureOptions, "Unstructured")
        _reloadOptionModel(storageKindModel, root.storageKindOptions, "")
    }

    function _reloadOptionModel(model, options, firstLabel) {
        model.clear()
        if (firstLabel.length > 0) {
            model.append({ label: firstLabel, value: "" })
        }
        for (let index = 0; index < options.length; index += 1) {
            const option = options[index]
            model.append({
                label: option.label || "",
                value: option.value || ""
            })
        }
    }

    function _loadDraft() {
        documentCodeField.text = root.draft.documentCode || ""
        titleField.text = root.draft.title || ""
        storageUriField.text = root.draft.storageUri || ""
        fileNameField.text = root.draft.fileName || ""
        mimeTypeField.text = root.draft.mimeType || ""
        sourceSystemField.text = root.draft.sourceSystem || ""
        confidentialityField.text = root.draft.confidentialityLevel || ""
        versionField.text = root.draft.businessVersionLabel || ""
        notesField.text = root.draft.notes || ""
        currentCheck.checked = root.draft.isCurrent !== undefined ? root.draft.isCurrent : true
        activeCheck.checked = root.draft.isActive !== undefined ? root.draft.isActive : true
        _setCurrentIndex(typeModel, typeCombo, root.draft.documentType || "GENERAL")
        _setCurrentIndex(structureModel, structureCombo, root.draft.documentStructureId || "")
        _setCurrentIndex(storageKindModel, storageKindCombo, root.draft.storageKind || "FILE_PATH")
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

    ListModel { id: typeModel }
    ListModel { id: structureModel }
    ListModel { id: storageKindModel }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppControls.TextField {
            id: documentCodeField

            Layout.preferredWidth: 180
            placeholderText: "Document code"
        }

        AppControls.TextField {
            id: titleField

            Layout.fillWidth: true
            placeholderText: "Title"
        }
    }

    AppControls.ComboBox {
        id: typeCombo

        Layout.fillWidth: true
        model: typeModel
        textRole: "label"
    }

    AppControls.ComboBox {
        id: structureCombo

        Layout.fillWidth: true
        model: structureModel
        textRole: "label"
    }

    AppControls.ComboBox {
        id: storageKindCombo

        Layout.fillWidth: true
        model: storageKindModel
        textRole: "label"
    }

    AppControls.TextField {
        id: storageUriField

        Layout.fillWidth: true
        placeholderText: "Storage URI"
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppControls.TextField {
            id: fileNameField

            Layout.fillWidth: true
            placeholderText: "File name"
        }

        AppControls.TextField {
            id: mimeTypeField

            Layout.fillWidth: true
            placeholderText: "MIME type"
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppControls.TextField {
            id: sourceSystemField

            Layout.fillWidth: true
            placeholderText: "Source system"
        }

        AppControls.TextField {
            id: confidentialityField

            Layout.fillWidth: true
            placeholderText: "Confidentiality"
        }
    }

    AppControls.TextField {
        id: versionField

        Layout.fillWidth: true
        placeholderText: "Business version"
    }

    AppControls.TextArea {
        id: notesField

        Layout.fillWidth: true
        Layout.preferredHeight: 110
        placeholderText: "Notes"
        wrapMode: TextEdit.WordWrap
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppControls.CheckBox {
            id: currentCheck

            text: "Current version"
        }

        AppControls.CheckBox {
            id: activeCheck

            text: "Active document"
        }
    }
}
