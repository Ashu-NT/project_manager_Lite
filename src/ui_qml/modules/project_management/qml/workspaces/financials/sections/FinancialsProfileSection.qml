pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var profile: ({ "id": "", "title": "Financial Profile", "statusLabel": "", "subtitle": "", "fields": [], "emptyState": "" })
    readonly property var _fields: root.profile.fields || []

    implicitHeight: _column.implicitHeight

    ColumnLayout {
        id: _column
        width: parent.width
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Financial Profile" }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: String(root.profile.id || "").length === 0
            title: "No project selected"
            message: root.profile.emptyState || "Select a project to review its financial profile."
        }

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            visible: String(root.profile.id || "").length > 0
            title: root.profile.statusLabel || "Profile"

            ColumnLayout {
                width: parent ? parent.width : 0
                spacing: Theme.AppTheme.spacingMd

                AppControls.Label {
                    Layout.fillWidth: true
                    Layout.margins: Theme.AppTheme.spacingMd
                    Layout.bottomMargin: 0
                    text: root.profile.subtitle || ""
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }

                GridLayout {
                    Layout.fillWidth: true
                    Layout.margins: Theme.AppTheme.spacingMd
                    columns: width >= 900 ? 3 : (width >= 560 ? 2 : 1)
                    columnSpacing: Theme.AppTheme.spacingLg
                    rowSpacing: Theme.AppTheme.spacingMd

                    Repeater {
                        model: root._fields
                        delegate: ColumnLayout {
                            id: _field
                            required property var modelData
                            Layout.fillWidth: true
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_field.modelData.label || "")
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }
                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_field.modelData.value || "-")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }
}
