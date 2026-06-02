pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Widgets 1.0 as PlatformWidgets
import Shell.Context 1.0 as ShellContexts

AppLayouts.WorkspaceFrame {
    id: root


                            // Entity name
                            AppControls.Label {
                                Layout.fillWidth: true
                                text:           root._detailItem ? (root._detailItem.title || "") : ""
                                color:          Theme.AppTheme.textPrimary
                                font.family:    Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.sectionSize
                                font.bold:      true
                                wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                            }

                            // Status chip
                            AppWidgets.StatusChip {
                                visible: root._detailItem
                                    ? (root._detailItem.statusLabel || "").length > 0 : false
                                status: root._detailItem ? (root._detailItem.statusLabel || "") : ""
                            }

                            // Divider
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.topMargin: 2; Layout.bottomMargin: 2
                                height: 1; color: Theme.AppTheme.divider
                            }

                            // Details field
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: root._detailItem
                                    ? (root._detailItem.subtitle || "").length > 0 : false

                                AppControls.Label {
                                    text:           "Details"
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text:           root._detailItem ? (root._detailItem.subtitle || "") : ""
                                    color:          Theme.AppTheme.textSecondary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }

                            // Info field
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                visible: root._detailItem
                                    ? (root._detailItem.metaText || "").length > 0 : false

                                AppControls.Label {
                                    text:           "Info"
                                    color:          Theme.AppTheme.textMuted
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                    font.bold:      true
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text:           root._detailItem ? (root._detailItem.metaText || "") : ""
                                    color:          Theme.AppTheme.textSecondary
                                    font.family:    Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode:       Text.WrapAtWordBoundaryOrAnywhere
                                }
                            }

                            // Action divider
                            Rectangle {
                                Layout.fillWidth: true
                                Layout.topMargin: 2
                                height: 1; color: Theme.AppTheme.divider
                                visible: root._detailItem !== null
                            }

                            // Primary actions: Edit + Set Active / Toggle
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: Theme.AppTheme.spacingXs
                                visible: root._detailItem !== null

                                AppControls.PrimaryButton {
                                    Layout.fillWidth: true
                                    text:     "Edit"
                                    iconName: "edit"
                                    enabled:  !root._busy
                                    onClicked: {
                                        const id = root._selectedRowId
                                        const s  = root._activeSection
                                        if      (s === "organizations") root.openOrganizationEdit(id)
                                        else if (s === "sites")         root.openSiteEdit(id)
                                        else if (s === "departments")   root.openDepartmentEdit(id)
                                        else if (s === "employees")     root.openEmployeeEdit(id)
                                        else if (s === "users")         root.openUserEdit(id)
                                        else if (s === "parties")       root.openPartyEdit(id)
                                        else if (s === "structures")    root.openDocumentStructureEdit(id)
                                    }
                                }

                                AppControls.SecondaryButton {
                                    visible:  root._activeSection === "organizations"
                                    text:     "Set Active"
                                    iconName: "approve"
                                    enabled:  !root._busy
                                    onClicked: {
                                        if (root.workspaceController)
                                            root.workspaceController.setActiveOrganization(root._selectedRowId)
                                    }
                                }

                                AppControls.SecondaryButton {
                                    visible:  root._activeSection !== "organizations"
                                    text:     "Toggle"
                                    iconName: "approve"
                                    enabled:  !root._busy
                                    onClicked: {
                                        const id = root._selectedRowId
                                        const s  = root._activeSection
                                        if (!root.workspaceController) return
                                        if      (s === "sites")       root.workspaceController.toggleSiteActive(id)
                                        else if (s === "departments") root.workspaceController.toggleDepartmentActive(id)
                                        else if (s === "employees")   root.workspaceController.toggleEmployeeActive(id)
                                        else if (s === "users")       root.workspaceController.toggleUserActive(id)
                                        else if (s === "parties")     root.workspaceController.togglePartyActive(id)
                                        else if (s === "structures")  root.workspaceController.toggleDocumentStructureActive(id)
                                    }
                                }
                            }

                            // Delete action
                            AppControls.SecondaryButton {
                                Layout.fillWidth: true
                                visible:  root._detailItem !== null
                                text:     "Delete"
                                iconName: "delete"
                                danger:   true
                                enabled:  !root._busy
                                onClicked: { /* root.workspaceController.deleteEntity(root._selectedRowId) */ }
                            }
                        }
                    }
                }
            }
        }
    }

    // ── Dialog host ───────────────────────────────────────────────
    AppWidgets.LazyObjectLoader {
        id: dialogHostLoader
        sourceComponent: Component {
            AdminDialogHost {
                workspaceController: root.workspaceController
            }
        }
    }
}


