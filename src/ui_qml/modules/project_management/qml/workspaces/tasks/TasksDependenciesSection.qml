import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Rectangle {
    id: root

    property var dependenciesModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property bool isBusy: false
    property bool canCreate: false

    signal createRequested()
    signal deleteRequested(var dependencyData)

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    implicitHeight: sectionLayout.implicitHeight + (Theme.AppTheme.marginLg * 2)

    ColumnLayout {
        id: sectionLayout

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingXs

                Text {
                    Layout.fillWidth: true
                    text: String(root.dependenciesModel.title || "Dependencies")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    font.bold: true
                    wrapMode: Text.WordWrap
                }

                Text {
                    Layout.fillWidth: true
                    text: String(root.dependenciesModel.subtitle || "")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                    visible: text.length > 0
                }
            }

            AppControls.PrimaryButton {
                text: "Create Dependency"
                enabled: root.canCreate && !root.isBusy
                onClicked: root.createRequested()
            }
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            title: ""
            subtitle: ""
            emptyState: root.dependenciesModel.emptyState || ""
            items: root.dependenciesModel.items || []
            tertiaryActionLabel: "Remove"
            tertiaryDanger: true
            actionsEnabled: !root.isBusy

            onTertiaryActionRequested: function(itemData) {
                root.deleteRequested(itemData)
            }
        }
    }
}
