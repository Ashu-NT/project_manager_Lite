pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

ColumnLayout {
    id: root

    property var supportSettings: ({})
    property var updateStatus:    ({})

    Layout.preferredWidth: 260
    Layout.fillHeight:     true
    spacing: 0

    AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Runtime Status" }

    ColumnLayout {
        Layout.fillWidth:    true
        Layout.fillHeight:   true
        Layout.leftMargin:   Theme.AppTheme.marginMd
        Layout.rightMargin:  Theme.AppTheme.marginMd
        Layout.topMargin:    Theme.AppTheme.spacingSm
        Layout.bottomMargin: Theme.AppTheme.spacingSm
        spacing:             Theme.AppTheme.spacingXs

        RowLayout {
            Layout.fillWidth: true; spacing: Theme.AppTheme.spacingXs
            AppControls.Label { Layout.fillWidth: true; text: "Release Status"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; font.bold: true }
            AppWidgets.StatusChip { status: String(root.updateStatus.statusLabel || "Ready") }
        }

        SupportMetaRow { rowLabel: "App Version"; rowValue: String(root.supportSettings.appVersion    || "-") }
        SupportMetaRow { rowLabel: "Current";     rowValue: String(root.updateStatus.currentVersion   || "-") }
        SupportMetaRow { rowLabel: "Latest";      rowValue: String(root.updateStatus.latestVersion    || "-") }
        SupportMetaRow { rowLabel: "Theme";       rowValue: String(root.supportSettings.themeMode     || "-") }
        SupportMetaRow { rowLabel: "Governance";  rowValue: String(root.supportSettings.governanceMode || "-") }

        AppControls.Label {
            Layout.fillWidth: true
            visible:  String(root.updateStatus.notes || "").length > 0
            text:     String(root.updateStatus.notes || "")
            color:    Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; wrapMode: Text.WordWrap
        }
        AppControls.Label {
            Layout.fillWidth: true
            visible:  String(root.updateStatus.summary || "").length > 0
            text:     String(root.updateStatus.summary || "")
            color:    Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize; wrapMode: Text.WordWrap
        }
        AppControls.Label {
            Layout.fillWidth: true
            visible:  String(root.updateStatus.sha256 || "").length > 0
            text:     "SHA256: " + String(root.updateStatus.sha256 || "")
            color:    Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.captionSize
            wrapMode: Text.WrapAnywhere; maximumLineCount: 2; elide: Text.ElideRight
        }

        Item { Layout.fillHeight: true }
    }
}
