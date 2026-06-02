pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var skillRequirementsModel: ({ "items": [], "emptyState": "" })
    property var sectionErrors: ({})
    property bool isBusy: false

    implicitHeight: _skillsBodyCol.implicitHeight

    ColumnLayout {
        id: _skillsBodyCol
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 0

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            title: "Skills & Certifications"
            subtitle: "Skill and certification requirements for resource assignment."
            busy: root.isBusy
            actions: []
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.sectionErrors["skills"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["skills"] || "")
        }

        Repeater {
            model: root.skillRequirementsModel.items || []

            delegate: ColumnLayout {
                id: _reqItem
                required property var modelData
                Layout.fillWidth: true
                spacing: 0

                RowLayout {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.AppTheme.marginMd
                    Layout.rightMargin: Theme.AppTheme.marginMd
                    Layout.topMargin: Theme.AppTheme.spacingSm
                    Layout.bottomMargin: Theme.AppTheme.spacingSm
                    spacing: Theme.AppTheme.spacingMd

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_reqItem.modelData.title || "")
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                            color: Theme.AppTheme.textPrimary
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_reqItem.modelData.subtitle || "")
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            color: Theme.AppTheme.textSecondary
                            elide: Text.ElideRight
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            visible: String(_reqItem.modelData.supportingText || "").length > 0
                                && String(_reqItem.modelData.supportingText || "") !== "No notes recorded."
                            text: String(_reqItem.modelData.supportingText || "")
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            color: Theme.AppTheme.textMuted
                            elide: Text.ElideRight
                        }
                    }

                    AppWidgets.StatusChip {
                        visible: String(_reqItem.modelData.statusLabel || "").length > 0
                        status: String(_reqItem.modelData.statusLabel || "")
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 1
                    color: Theme.AppTheme.divider
                }
            }
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: (root.skillRequirementsModel.items || []).length === 0
            title: String(root.skillRequirementsModel.emptyState
                || "No skill requirements are linked to this task.")
        }
    }
}
