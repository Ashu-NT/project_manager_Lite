import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Mock 1.0 as AppMock
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
    id: root

    property var dependenciesModel: AppMock.MockFactory.catalog()
    property bool isBusy: false
    property bool canCreate: false

    signal createRequested()
    signal deleteRequested(var dependencyData)

    implicitHeight: sectionLayout.implicitHeight

    ColumnLayout {
        id: sectionLayout

        anchors.fill: parent
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
                iconName: "add"
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
