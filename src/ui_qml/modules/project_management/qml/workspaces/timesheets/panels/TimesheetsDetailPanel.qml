pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var reviewDetail: ({
        "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "", "fields": [], "state": {}
    })
    property var detailPage: null

    readonly property bool _hasPeriod: String(root.reviewDetail.id || "").length > 0
    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property var _state: root.reviewDetail.state || ({})
    readonly property real _activeHeight: root._idx === 0
        ? summarySection.implicitHeight
        : historySection.implicitHeight

    implicitHeight: _activeHeight
    height: implicitHeight

    AppWidgets.LazySectionLoader {
        id: summarySection
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 0
        loadingMessage: "Loading review summary..."
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Review Summary"
                }

                AppWidgets.EmptyState {
                    width: parent.width
                    visible: !root._hasPeriod
                    message: root.reviewDetail.emptyState || "Select a timesheet period to inspect its decision context."
                }

                GridLayout {
                    width: parent.width
                    visible: root._hasPeriod
                    columns: width >= 760 ? 2 : 1
                    columnSpacing: Theme.AppTheme.spacingLg
                    rowSpacing: 0

                    Repeater {
                        model: root.reviewDetail.fields || []

                        delegate: Item {
                            id: fieldRow
                            required property var modelData
                            Layout.fillWidth: true
                            implicitHeight: fieldContent.implicitHeight + Theme.AppTheme.spacingMd * 2

                            ColumnLayout {
                                id: fieldContent
                                anchors.fill: parent
                                anchors.margins: Theme.AppTheme.spacingMd
                                spacing: Theme.AppTheme.spacingXs

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(fieldRow.modelData.label || "")
                                    color: Theme.AppTheme.textMuted
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.captionSize
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String(fieldRow.modelData.value || "-")
                                    color: Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.bodySize
                                    font.bold: true
                                    wrapMode: Text.WordWrap
                                }
                                AppControls.Label {
                                    Layout.fillWidth: true
                                    visible: text.length > 0
                                    text: String(fieldRow.modelData.supportingText || "")
                                    color: Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: historySection
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 1
        loadingMessage: "Loading decision history..."
        sourceComponent: Component {
            ColumnLayout {
                width: parent ? parent.width : 0
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.SectionHeading {
                    Layout.fillWidth: true
                    label: "Decision History"
                }

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: !root._hasPeriod
                    message: "Select a timesheet period to inspect its latest decision evidence."
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.AppTheme.spacingMd
                    Layout.rightMargin: Theme.AppTheme.spacingMd
                    visible: root._hasPeriod
                    text: "Submitted by " + String(root._state.submittedBy || "-")
                        + " at " + String(root._state.submittedAt || "-")
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    wrapMode: Text.WordWrap
                }

                AppControls.Label {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.AppTheme.spacingMd
                    Layout.rightMargin: Theme.AppTheme.spacingMd
                    visible: root._hasPeriod
                    text: "Latest decision by " + String(root._state.decidedBy || "-")
                        + " at " + String(root._state.decidedAt || "-")
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.bodySize
                    wrapMode: Text.WordWrap
                }

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    Layout.leftMargin: Theme.AppTheme.spacingMd
                    Layout.rightMargin: Theme.AppTheme.spacingMd
                    visible: root._hasPeriod
                    tone: "info"
                    message: String(root._state.decisionNote || "No decision note recorded.")
                }
            }
        }
    }
}
