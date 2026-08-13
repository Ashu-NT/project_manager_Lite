import QtQuick
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
    property var workspaceController: null
    property string documentCode: ""

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
        if (root.documentCode.trim().length === 0) {
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
        documentCode: root.documentCode.trim(),
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
        root.documentCode = root.draft.documentCode || ""
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

    AppWidgets.CodeFieldRow {
        Layout.fillWidth: true
        label: "Document Code"
        value: root.documentCode
        placeholderText: "Auto-generated if empty"
        required: true
        generateVisible: true
        busy: root.workspaceController ? root.workspaceController.isBusy : false
        onValueEdited: function(code) { root.documentCode = code }
        onGenerateRequested: {
            if (root.workspaceController) {
                const suggested = root.workspaceController.generateEntityCode("document", root.formData)
                if (suggested && suggested.length > 0) {
                    root.documentCode = suggested
                }
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Title"
        required: true

        AppControls.TextField {
            id: titleField
            Layout.fillWidth: true
            placeholderText: "e.g. Pump Maintenance Manual"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Document Type"

        AppControls.ComboBox {
            id: typeCombo
            Layout.fillWidth: true
            model: typeModel
            textRole: "label"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Structure"

        AppControls.ComboBox {
            id: structureCombo
            Layout.fillWidth: true
            model: structureModel
            textRole: "label"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Storage Kind"

        AppControls.ComboBox {
            id: storageKindCombo
            Layout.fillWidth: true
            model: storageKindModel
            textRole: "label"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Storage URI"

        AppControls.TextField {
            id: storageUriField
            Layout.fillWidth: true
            placeholderText: "Path or URL to the document"
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "File Name"

            AppControls.TextField {
                id: fileNameField
                Layout.fillWidth: true
                placeholderText: "e.g. manual.pdf"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "MIME Type"

            AppControls.TextField {
                id: mimeTypeField
                Layout.fillWidth: true
                placeholderText: "e.g. application/pdf"
            }
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Source System"

            AppControls.TextField {
                id: sourceSystemField
                Layout.fillWidth: true
                placeholderText: "e.g. SharePoint"
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Confidentiality"

            AppControls.TextField {
                id: confidentialityField
                Layout.fillWidth: true
                placeholderText: "e.g. Internal"
            }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Business Version"

        AppControls.TextField {
            id: versionField
            Layout.fillWidth: true
            placeholderText: "e.g. Rev. C"
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Notes"

        AppControls.TextArea {
            id: notesField
            Layout.fillWidth: true
            Layout.preferredHeight: 110
            placeholderText: "Context, scope, or handling notes"
            wrapMode: TextEdit.WordWrap
        }
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
