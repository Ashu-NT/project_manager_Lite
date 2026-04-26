import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string mode: "create"
    property var draft: ({})

    signal saveRequested(string mode, var payload)

    modal: true
    focus: true
    width: 620
    closePolicy: Popup.NoAutoClose
    title: root.mode === "create" ? "New Site" : "Edit Site"

    readonly property var formData: ({
        siteId: root.draft.siteId || root.draft.id || "",
        expectedVersion: root.draft.version || 0,
        siteCode: siteCodeField.text.trim(),
        name: nameField.text.trim(),
        description: descriptionField.text.trim(),
        city: cityField.text.trim(),
        country: countryField.text.trim(),
        timezoneName: timezoneField.text.trim(),
        currencyCode: currencyField.text.trim().toUpperCase(),
        siteType: siteTypeField.text.trim(),
        status: statusField.text.trim(),
        notes: notesField.text.trim(),
        isActive: activeCheck.checked
    })

    function openForCreate() {
        root.mode = "create"
        root.draft = ({})
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
        siteCodeField.text = root.draft.siteCode || ""
        nameField.text = root.draft.name || ""
        descriptionField.text = root.draft.description || ""
        cityField.text = root.draft.city || ""
        countryField.text = root.draft.country || ""
        timezoneField.text = root.draft.timezoneName || ""
        currencyField.text = root.draft.currencyCode || ""
        siteTypeField.text = root.draft.siteType || ""
        statusField.text = root.draft.status || ""
        notesField.text = root.draft.notes || ""
        activeCheck.checked = root.draft.isActive !== undefined ? root.draft.isActive : true
    }

    contentItem: ScrollView {
        implicitWidth: 580
        implicitHeight: 460
        clip: true

        ColumnLayout {
            width: parent.availableWidth
            spacing: Theme.AppTheme.spacingMd

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: siteCodeField

                    Layout.preferredWidth: 180
                    placeholderText: "Site code"
                }

                TextField {
                    id: nameField

                    Layout.fillWidth: true
                    placeholderText: "Site name"
                }
            }

            TextField {
                id: descriptionField

                Layout.fillWidth: true
                placeholderText: "Description"
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: cityField

                    Layout.fillWidth: true
                    placeholderText: "City"
                }

                TextField {
                    id: countryField

                    Layout.fillWidth: true
                    placeholderText: "Country"
                }
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

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                TextField {
                    id: siteTypeField

                    Layout.fillWidth: true
                    placeholderText: "Site type"
                }

                TextField {
                    id: statusField

                    Layout.fillWidth: true
                    placeholderText: "Status"
                }
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

                text: "Active site"
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
                enabled: siteCodeField.text.trim().length > 0
                    && nameField.text.trim().length > 0
                text: root.mode === "create" ? "Create" : "Save"
                onClicked: root.saveRequested(root.mode, root.formData)
            }
        }
    }
}
