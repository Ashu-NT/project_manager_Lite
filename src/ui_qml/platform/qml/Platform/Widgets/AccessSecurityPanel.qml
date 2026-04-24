import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers

ColumnLayout {
    id: root

    property PlatformControllers.PlatformAdminAccessWorkspaceController controller: null

    function indexOfOption(options, value) {
        for (let index = 0; index < options.length; index += 1) {
            if ((options[index].value || "") === value) {
                return index
            }
        }
        return options.length > 0 ? 0 : -1
    }

    function optionValue(options, index) {
        if (index < 0 || index >= options.length) {
            return ""
        }
        return options[index].value || ""
    }

    spacing: Theme.AppTheme.spacingMd

    RowLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingXs

            Label {
                Layout.fillWidth: true
                text: "Access And Security"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                font.bold: true
            }

            Label {
                Layout.fillWidth: true
                text: "Manage scoped access grants and handle account security actions from the QML admin surface."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }

        Button {
            enabled: root.controller !== null ? !root.controller.isBusy : false
            text: "Refresh"
            onClicked: {
                if (root.controller !== null) {
                    root.controller.refresh()
                }
            }
        }
    }

    WorkspaceStateBanner {
        Layout.fillWidth: true
        isLoading: root.controller !== null ? root.controller.isLoading : false
        isBusy: root.controller !== null ? root.controller.isBusy : false
        errorMessage: root.controller !== null ? root.controller.errorMessage : ""
        feedbackMessage: root.controller !== null ? root.controller.feedbackMessage : ""
    }

    Rectangle {
        Layout.fillWidth: true
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        border.color: Theme.AppTheme.border
        implicitHeight: controlsColumn.implicitHeight + (Theme.AppTheme.marginLg * 2)

        ColumnLayout {
            id: controlsColumn

            anchors.fill: parent
            anchors.margins: Theme.AppTheme.marginLg
            spacing: Theme.AppTheme.spacingMd

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                ComboBox {
                    id: scopeTypeCombo

                    Layout.fillWidth: true
                    enabled: root.controller !== null ? !root.controller.isBusy : false
                    model: root.controller !== null ? root.controller.scopeTypeOptions : []
                    textRole: "label"
                    currentIndex: root.indexOfOption(
                        root.controller !== null ? root.controller.scopeTypeOptions : [],
                        root.controller !== null ? root.controller.selectedScopeType : ""
                    )
                    onActivated: {
                        if (root.controller !== null) {
                            root.controller.setScopeType(root.optionValue(root.controller.scopeTypeOptions, currentIndex))
                        }
                    }
                }

                ComboBox {
                    id: scopeCombo

                    Layout.fillWidth: true
                    enabled: root.controller !== null ? !root.controller.isBusy : false
                    model: root.controller !== null ? root.controller.scopeOptions : []
                    textRole: "label"
                    currentIndex: root.indexOfOption(
                        root.controller !== null ? root.controller.scopeOptions : [],
                        root.controller !== null ? root.controller.selectedScopeId : ""
                    )
                    onActivated: {
                        if (root.controller !== null) {
                            root.controller.setScopeId(root.optionValue(root.controller.scopeOptions, currentIndex))
                        }
                    }
                }

                ComboBox {
                    id: userCombo

                    Layout.fillWidth: true
                    enabled: root.controller !== null ? !root.controller.isBusy : false
                    model: root.controller !== null ? root.controller.userOptions : []
                    textRole: "label"
                    currentIndex: root.indexOfOption(
                        root.controller !== null ? root.controller.userOptions : [],
                        root.controller !== null ? root.controller.selectedUserId : ""
                    )
                    onActivated: {
                        if (root.controller !== null) {
                            root.controller.setSelectedUserId(root.optionValue(root.controller.userOptions, currentIndex))
                        }
                    }
                }

                ComboBox {
                    id: roleCombo

                    Layout.fillWidth: true
                    enabled: root.controller !== null ? !root.controller.isBusy : false
                    model: root.controller !== null ? root.controller.roleOptions : []
                    textRole: "label"
                    currentIndex: root.indexOfOption(
                        root.controller !== null ? root.controller.roleOptions : [],
                        root.controller !== null ? root.controller.selectedRole : ""
                    )
                    onActivated: {
                        if (root.controller !== null) {
                            root.controller.setSelectedRole(root.optionValue(root.controller.roleOptions, currentIndex))
                        }
                    }
                }

                AppControls.PrimaryButton {
                    enabled: root.controller !== null ? !root.controller.isBusy : false
                    text: "Assign"
                    onClicked: {
                        if (root.controller !== null) {
                            root.controller.assignMembership()
                        }
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                text: root.controller !== null ? root.controller.scopeHint : ""
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }
    }

    GridLayout {
        Layout.fillWidth: true
        columns: width > 1100 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingMd

        RecordListCard {
            Layout.fillWidth: true
            title: root.controller !== null ? (root.controller.scopeGrants.title || "Scoped Access") : "Scoped Access"
            subtitle: root.controller !== null ? (root.controller.scopeGrants.subtitle || "") : ""
            emptyState: root.controller !== null ? (root.controller.scopeGrants.emptyState || "") : ""
            items: root.controller !== null ? (root.controller.scopeGrants.items || []) : []
            actionsEnabled: root.controller !== null ? !root.controller.isBusy : false
            primaryActionLabel: "Remove"
            onPrimaryActionRequested: function(itemId) {
                if (root.controller !== null) {
                    root.controller.removeMembership(itemId)
                }
            }
        }

        RecordListCard {
            Layout.fillWidth: true
            title: root.controller !== null ? (root.controller.securityUsers.title || "Security") : "Security"
            subtitle: root.controller !== null ? (root.controller.securityUsers.subtitle || "") : ""
            emptyState: root.controller !== null ? (root.controller.securityUsers.emptyState || "") : ""
            items: root.controller !== null ? (root.controller.securityUsers.items || []) : []
            actionsEnabled: root.controller !== null ? !root.controller.isBusy : false
            primaryActionLabel: "Unlock"
            secondaryActionLabel: "Revoke Sessions"

            onPrimaryActionRequested: function(itemId) {
                if (root.controller !== null) {
                    root.controller.unlockUser(itemId)
                }
            }

            onSecondaryActionRequested: function(itemId) {
                if (root.controller !== null) {
                    root.controller.revokeSessions(itemId)
                }
            }
        }
    }
}
