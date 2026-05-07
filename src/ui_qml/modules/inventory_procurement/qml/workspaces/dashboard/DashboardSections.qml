pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme

ColumnLayout {
    id: root

    property var sections: []
    property string emptyState: ""

    spacing: Theme.AppTheme.spacingMd

    Repeater {
        model: root.sections

        delegate: Rectangle {
            id: sectionCard
            required property var modelData

            Layout.fillWidth: true
            radius: Theme.AppTheme.radiusLg
            color: Theme.AppTheme.surface
            border.color: Theme.AppTheme.border
            implicitHeight: sectionColumn.implicitHeight + Theme.AppTheme.marginLg * 2

            ColumnLayout {
                id: sectionColumn
                anchors.fill: parent
                anchors.margins: Theme.AppTheme.marginLg
                spacing: Theme.AppTheme.spacingMd

                Text {
                    text: sectionCard.modelData.title || ""
                    color: Theme.AppTheme.textPrimary
                    font.pixelSize: 18
                    font.bold: true
                }

                Text {
                    visible: (sectionCard.modelData.subtitle || "").length > 0
                    text: sectionCard.modelData.subtitle || ""
                    color: Theme.AppTheme.textMuted
                    wrapMode: Text.WordWrap
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Theme.AppTheme.spacingSm
                    visible: (sectionCard.modelData.rows || []).length > 0

                    Repeater {
                        model: sectionCard.modelData.rows || []

                        delegate: Rectangle {
                            id: sectionRowCard
                            required property var modelData

                            Layout.fillWidth: true
                            radius: Theme.AppTheme.radiusMd
                            color: Theme.AppTheme.surfaceAlt
                            border.color: Theme.AppTheme.border
                            implicitHeight: rowColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: rowColumn
                                anchors.fill: parent
                                anchors.margins: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingXs

                                RowLayout {
                                    Layout.fillWidth: true

                                    Text {
                                        Layout.fillWidth: true
                                        text: sectionRowCard.modelData.title || ""
                                        color: Theme.AppTheme.textPrimary
                                        font.bold: true
                                        wrapMode: Text.WordWrap
                                    }

                                    Text {
                                        visible: (sectionRowCard.modelData.statusLabel || "").length > 0
                                        text: sectionRowCard.modelData.statusLabel || ""
                                        color: Theme.AppTheme.textSecondary
                                    }
                                }

                                Text {
                                    visible: (sectionRowCard.modelData.subtitle || "").length > 0
                                    text: sectionRowCard.modelData.subtitle || ""
                                    color: Theme.AppTheme.textSecondary
                                    wrapMode: Text.WordWrap
                                }

                                Text {
                                    visible: (sectionRowCard.modelData.supportingText || "").length > 0
                                    text: sectionRowCard.modelData.supportingText || ""
                                    color: Theme.AppTheme.textPrimary
                                    wrapMode: Text.WordWrap
                                }

                                Text {
                                    visible: (sectionRowCard.modelData.metaText || "").length > 0
                                    text: sectionRowCard.modelData.metaText || ""
                                    color: Theme.AppTheme.textMuted
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }

                Text {
                    visible: (sectionCard.modelData.rows || []).length === 0
                    text: sectionCard.modelData.emptyState || root.emptyState
                    color: Theme.AppTheme.textMuted
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
