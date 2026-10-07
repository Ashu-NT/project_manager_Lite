pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

// Bulk module grant/revoke popup — anchored above BulkActionBar, alongside
// BulkChangePropertyPopup (single-value bulk edit). This one applies a SET
// of modules to every selected record at once, so it needs its own
// checkbox-list UI rather than BulkChangePropertyPopup's single dropdown.
// moduleOptions: [{label, value, supportingText}]
// Emits applyRequested({moduleCodes, grant}) on confirm.
AnchoredPopup {
    id: root

    property int selectedCount: 0
    property string title: "Assign Modules"
    property var moduleOptions: []
    property bool busy: false

    signal applyRequested(var payload)
    signal cancelRequested()

    width: Math.min(320, Theme.AppTheme.dialogCompactWidth + 40)
    padding: Theme.AppTheme.dialogPadding
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    placement: "above-center"

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.dialogBackground
        border.color: Theme.AppTheme.dialogBorder
        border.width: 1
    }

    function _resetModuleModel() {
        _moduleModel.clear()
        const options = root.moduleOptions || []
        for (let i = 0; i < options.length; i++) {
            _moduleModel.append({ label: options[i].label || "", value: options[i].value || "", selected: false })
        }
    }

    onAboutToShow: {
        root._resetModuleModel()
        _actionCombo.currentIndex = 0
    }

    ListModel { id: _moduleModel }

    ColumnLayout {
        width: parent.width
        spacing: Theme.AppTheme.spacingSm

        AppControls.Label {
            text: root.title
            font.bold: true
            font.pixelSize: Theme.AppTheme.bodySize
            font.family: Theme.AppTheme.fontFamily
            color: Theme.AppTheme.textPrimary
        }

        AppControls.Label {
            visible: root.selectedCount > 0
            text: root.selectedCount + " organizations will be updated"
            font.pixelSize: Theme.AppTheme.captionSize
            font.family: Theme.AppTheme.fontFamily
            color: Theme.AppTheme.textMuted
        }

        AppControls.Label {
            text: "Action"
            font.pixelSize: Theme.AppTheme.captionSize
            font.family: Theme.AppTheme.fontFamily
            color: Theme.AppTheme.textMuted
            font.bold: true
        }

        AppControls.ComboBox {
            id: _actionCombo
            Layout.fillWidth: true
            enabled: !root.busy
            textRole: "label"
            model: ListModel {
                ListElement { label: "Grant selected modules"; value: "grant" }
                ListElement { label: "Revoke selected modules"; value: "revoke" }
            }
        }

        AppControls.Label {
            text: "Modules"
            font.pixelSize: Theme.AppTheme.captionSize
            font.family: Theme.AppTheme.fontFamily
            color: Theme.AppTheme.textMuted
            font.bold: true
        }

        AppControls.Label {
            visible: root.moduleOptions.length === 0
            text: "No modules available."
            font.pixelSize: Theme.AppTheme.captionSize
            font.family: Theme.AppTheme.fontFamily
            color: Theme.AppTheme.textMuted
        }

        Flickable {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(220, _moduleColumn.implicitHeight)
            contentWidth: width
            contentHeight: _moduleColumn.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: _moduleColumn
                width: parent.width
                spacing: 0

                Repeater {
                    model: _moduleModel
                    delegate: AppControls.CheckBox {
                        required property int index
                        required property string label
                        required property bool selected

                        Layout.fillWidth: true
                        text: label
                        checked: selected
                        enabled: !root.busy
                        onToggled: _moduleModel.setProperty(index, "selected", checked)
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                Layout.fillWidth: true
                text: "Cancel"
                iconName: "close"
                onClicked: {
                    root.cancelRequested()
                    root.close()
                }
            }

            AppControls.PrimaryButton {
                Layout.fillWidth: true
                text: "Apply"
                iconName: "approve"
                enabled: !root.busy
                onClicked: {
                    const codes = []
                    for (let i = 0; i < _moduleModel.count; i++) {
                        const entry = _moduleModel.get(i)
                        if (entry.selected) codes.push(entry.value)
                    }
                    if (codes.length === 0) return
                    root.applyRequested({
                        moduleCodes: codes,
                        grant: _actionCombo.currentIndex === 0
                    })
                    root.close()
                }
            }
        }
    }
}
