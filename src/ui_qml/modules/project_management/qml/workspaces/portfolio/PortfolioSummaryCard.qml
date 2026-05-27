import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var summaryModel: AppMock.MockFactory.fieldCatalog()

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn

        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppControls.Label {
            Layout.fillWidth: true
            text: root.summaryModel.title || ""
            visible: text.length > 0
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
            wrapMode: Text.WordWrap
        }

        AppControls.Label {
            Layout.fillWidth: true
            text: root.summaryModel.subtitle || ""
            visible: text.length > 0
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        AppControls.Label {
            Layout.fillWidth: true
            visible: (root.summaryModel.fields || []).length === 0 && String(root.summaryModel.emptyState || "").length > 0
            text: root.summaryModel.emptyState || ""
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: root.summaryModel.fields || []

            delegate: ColumnLayout {
                id: summaryFieldRow

                required property var modelData
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    Layout.fillWidth: true
                    text: String(summaryFieldRow.modelData.label || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    text: String(summaryFieldRow.modelData.value || "")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    visible: String(summaryFieldRow.modelData.supportingText || "").length > 0
                    text: String(summaryFieldRow.modelData.supportingText || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
