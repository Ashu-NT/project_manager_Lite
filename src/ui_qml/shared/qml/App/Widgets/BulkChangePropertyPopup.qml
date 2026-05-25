import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

// Bulk property change popup — anchored above BulkActionBar.
// properties: [{id, label, values:[{value, label}]}]
// Emits applyRequested({propertyId, value, note}) on confirm.
AnchoredPopup {
    id: root

    property int selectedCount: 0
    property string title:      "Bulk Update"
    property var    properties: []
    property bool   busy:       false

    signal applyRequested(var payload)
    signal cancelRequested()

    width:       240
    padding:     Theme.AppTheme.marginMd
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    placement:   "above-center"

    background: Rectangle {
        radius:       Theme.AppTheme.radiusLg
        color:        Theme.AppTheme.surfaceRaised
        border.color: Theme.AppTheme.divider
        border.width: 1
    }

    onAboutToShow: {
        _propCombo.currentIndex = 0
        _valueCombo.currentIndex = 0
        _noteField.text = ""
    }

    ColumnLayout {
        width:   parent.width
        spacing: Theme.AppTheme.spacingSm

        Label {
            text:           root.title
            font.bold:      true
            font.pixelSize: Theme.AppTheme.bodySize
            font.family:    Theme.AppTheme.fontFamily
            color:          Theme.AppTheme.textPrimary
        }

        Label {
            visible:        root.selectedCount > 0
            text:           root.selectedCount + " records will be updated"
            font.pixelSize: Theme.AppTheme.captionSize
            font.family:    Theme.AppTheme.fontFamily
            color:          Theme.AppTheme.textMuted
        }

        Label {
            text:           "Property"
            font.pixelSize: Theme.AppTheme.captionSize
            font.family:    Theme.AppTheme.fontFamily
            color:          Theme.AppTheme.textMuted
            font.bold:      true
        }

        ComboBox {
            id: _propCombo
            Layout.fillWidth: true
            model:    root.properties
            textRole: "label"
            enabled:  !root.busy
        }

        Label {
            text:           "Value"
            font.pixelSize: Theme.AppTheme.captionSize
            font.family:    Theme.AppTheme.fontFamily
            color:          Theme.AppTheme.textMuted
            font.bold:      true
        }

        ComboBox {
            id: _valueCombo
            Layout.fillWidth: true
            enabled: !root.busy
            model: {
                const idx = _propCombo.currentIndex
                const props = root.properties || []
                if (idx >= 0 && props[idx] && props[idx].values) return props[idx].values
                return []
            }
            textRole: "label"
        }

        Label {
            text:           "Note (optional)"
            font.pixelSize: Theme.AppTheme.captionSize
            font.family:    Theme.AppTheme.fontFamily
            color:          Theme.AppTheme.textMuted
            font.bold:      true
        }

        TextField {
            id: _noteField
            Layout.fillWidth: true
            placeholderText: "Reason for change..."
            enabled:    !root.busy
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            color: Theme.AppTheme.textPrimary
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
                text:     "Apply"
                iconName: "approve"
                enabled:  !root.busy
                onClicked: {
                    const propIdx  = _propCombo.currentIndex
                    const valIdx   = _valueCombo.currentIndex
                    const props    = root.properties || []
                    if (propIdx < 0 || !props[propIdx]) return
                    const prop     = props[propIdx]
                    const vals     = prop.values || []
                    const valEntry = vals[valIdx]
                    root.applyRequested({
                        propertyId: String(prop.id   || ""),
                        value:      valEntry ? String(valEntry.value || "") : "",
                        note:       _noteField.text.trim()
                    })
                    root.close()
                }
            }
        }
    }
}
