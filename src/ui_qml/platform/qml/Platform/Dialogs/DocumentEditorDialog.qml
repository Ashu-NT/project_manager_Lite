import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
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
    closePolicy: Popup.NoAutoClose
    title: root.mode === "create" ? "New Document" : "Edit Document"

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

    contentItem: ScrollView {
        implicitWidth: 620
        implicitHeight: 560
        clip: true

        ColumnLayout {
            width: parent.availableWidth
            spacing: Theme.AppTheme.spacingMd

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: documentCodeField

                    Layout.preferredWidth: 180
                    placeholderText: "Document code"
                }

                TextField {
                    id: titleField

                    Layout.fillWidth: true
                    placeholderText: "Title"
                }
            }

            ComboBox {
                id: typeCombo

                Layout.fillWidth: true
                model: typeModel
                textRole: "label"
            }

            ComboBox {
                id: structureCombo

                Layout.fillWidth: true
                model: structureModel
                textRole: "label"
            }

            ComboBox {
                id: storageKindCombo

                Layout.fillWidth: true
                model: storageKindModel
                textRole: "label"
            }

            TextField {
                id: storageUriField

                Layout.fillWidth: true
                placeholderText: "Storage URI"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: fileNameField

                    Layout.fillWidth: true
                    placeholderText: "File name"
                }

                TextField {
                    id: mimeTypeField

                    Layout.fillWidth: true
                    placeholderText: "MIME type"
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: sourceSystemField

                    Layout.fillWidth: true
                    placeholderText: "Source system"
                }

                TextField {
                    id: confidentialityField

                    Layout.fillWidth: true
                    placeholderText: "Confidentiality"
                }
            }

            TextField {
                id: versionField

                Layout.fillWidth: true
                placeholderText: "Business version"
            }

            TextArea {
                id: notesField

                Layout.fillWidth: true
                Layout.preferredHeight: 110
                placeholderText: "Notes"
                wrapMode: TextEdit.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                CheckBox {
                    id: currentCheck

                    text: "Current version"
                }

                CheckBox {
                    id: activeCheck

                    text: "Active document"
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
                enabled: documentCodeField.text.trim().length > 0
                    && titleField.text.trim().length > 0
                text: root.mode === "create" ? "Create" : "Save"
                onClicked: root.saveRequested(root.mode, root.formData)
            }
        }
    }
}
