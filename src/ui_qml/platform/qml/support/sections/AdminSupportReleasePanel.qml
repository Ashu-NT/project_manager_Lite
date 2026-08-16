pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

ColumnLayout {
    id: root

    property var  supportSettings: ({})
    property var  updateStatus:    ({})
    property bool isBusy:          false

    signal saveSettingsRequested(string channel, bool autoCheck, string manifestSource)
    signal checkUpdatesRequested(string channel, bool autoCheck, string manifestSource)
    signal installUpdateRequested(string channel, bool autoCheck, string manifestSource)
    signal openDownloadRequested()

    Layout.fillWidth:  true
    Layout.fillHeight: true
    spacing: 0

    function _payload() {
        const idx = channelCombo.currentIndex
        const ch  = (idx >= 0 && idx < channelCombo.count)
            ? String((channelCombo.model[idx] || {}).value || "stable") : "stable"
        return { channel: ch, autoCheck: autoCheckBox.checked, manifestSource: manifestField.text.trim() }
    }

    AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Release Management" }

    ColumnLayout {
        Layout.fillWidth:    true
        Layout.fillHeight:   true
        Layout.leftMargin:   Theme.AppTheme.marginMd
        Layout.rightMargin:  Theme.AppTheme.marginMd
        Layout.topMargin:    Theme.AppTheme.spacingSm
        Layout.bottomMargin: Theme.AppTheme.spacingSm
        spacing:             Theme.AppTheme.spacingSm

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3
                AppControls.Label { text: "Channel"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
                AppControls.ComboBox {
                    id: channelCombo
                    Layout.fillWidth: true
                    enabled:  !root.isBusy
                    model:    root.supportSettings.channelOptions || []
                    textRole: "label"
                }
            }

            AppControls.CheckBox {
                id: autoCheckBox
                Layout.alignment: Qt.AlignBottom
                text:    "Auto-check at startup"
                enabled: !root.isBusy
                font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3
            AppControls.Label { text: "Manifest Source"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
            AppControls.TextField {
                id: manifestField
                Layout.fillWidth: true
                enabled:         !root.isBusy
                placeholderText: "Update manifest URL or path"
            }
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.PrimaryButton {
                text: "Save Settings"; iconName: "save"; enabled: !root.isBusy
                onClicked: { const p = root._payload(); root.saveSettingsRequested(p.channel, p.autoCheck, p.manifestSource) }
            }
            AppControls.SecondaryButton {
                text: "Check Updates"; iconName: "refresh"; enabled: !root.isBusy
                onClicked: { const p = root._payload(); root.checkUpdatesRequested(p.channel, p.autoCheck, p.manifestSource) }
            }
            AppControls.SecondaryButton {
                visible: Qt.platform.os === "windows"
                text:    "Install Now"; iconName: "approve"
                enabled: !root.isBusy && Boolean(root.updateStatus.updateAvailable) && Boolean(root.updateStatus.canOpenDownload)
                onClicked: { const p = root._payload(); root.installUpdateRequested(p.channel, p.autoCheck, p.manifestSource) }
            }
            AppControls.SecondaryButton {
                text:    "Open Download"; iconName: "view"
                enabled: !root.isBusy && Boolean(root.updateStatus.canOpenDownload)
                onClicked: root.openDownloadRequested()
            }
            Item { Layout.fillWidth: true }
        }
    }
}
