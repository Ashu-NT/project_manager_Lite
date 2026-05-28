import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Mock 1.0 as AppMock
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets
import App.Controls 1.0 as AppControls

Item {
    id: root

    property var entryDetail: AppMock.MockFactory.detail("Select a risk entry to review mitigation details.")
    property var urgentModel: AppMock.MockFactory.catalog("Urgent Review Queue", "", "No urgent risks.")
    property string selectedEntryId: ""
    property bool isBusy: false
    property var detailPage: null

    signal editRequested()
    signal deleteRequested()
    signal urgentEntrySelected(string entryId)

    readonly property bool _hasEntry: String(root.entryDetail.id || "").length > 0
    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property var _sections: root.detailPage ? (root.detailPage.sections || []) : []

    function _secIdx(name) {
        const secs = root._sections
        for (let i = 0; i < secs.length; i++) {
            const s = secs[i]
            const sLabel = (typeof s === "string") ? s : (s.label || "")
            if (sLabel === name) return i
        }
        return -1
    }

    readonly property int _activeSectionH: {
        const secs = root._sections
        const entry = (secs.length > root._idx) ? secs[root._idx] : null
        const name = entry ? ((typeof entry === "string") ? entry : (entry.label || "")) : ""
        if (name === "Details")  return _sec0.implicitHeight
        if (name === "Impact")   return _sec1.implicitHeight
        if (name === "Response") return _sec2.implicitHeight
        if (name === "Links")    return _sec3.implicitHeight
        return 0
    }

    implicitHeight: _activeSectionH
    height: implicitHeight

    function _sv(key) {
        const s = root.entryDetail.state || {}
        return String(s[key] || "")
    }

    AppWidgets.LazySectionLoader {
        id: _sec0
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Details")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Details"
                }

                Item {
                    width: parent.width
                    implicitHeight: detailSection.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    ProjectManagementWidgets.RegisterDetailSection {
                        id: detailSection
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.spacingMd
                        anchors.rightMargin: Theme.AppTheme.spacingMd

                        entryDetail: root.entryDetail
                        isBusy: root.isBusy
                        onEditRequested: root.editRequested()
                        onDeleteRequested: root.deleteRequested()
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec1
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Impact")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Impact"
                }

                AppWidgets.EmptyState {
                    width: parent.width
                    visible: !root._hasEntry
                    title: "No risk selected"
                    message: root.entryDetail.emptyState || "Select a risk entry to review impact and mitigation details."
                }

                Item {
                    width: parent.width
                    visible: root._hasEntry
                    implicitHeight: _impactContent.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    ColumnLayout {
                        id: _impactContent
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.spacingMd
                        spacing: Theme.AppTheme.spacingMd

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            Repeater {
                                model: [
                                    { "lbl": "Probability",    "val": root._sv("probabilityLabel") },
                                    { "lbl": "Impact",         "val": root._sv("impactLabel") },
                                    { "lbl": "Risk Score",     "val": root._sv("riskScore") },
                                    { "lbl": "Residual Risk",  "val": root._sv("residualRiskLabel") }
                                ]

                                delegate: ColumnLayout {
                                    id: _impactCell
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingXs

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_impactCell.modelData.lbl)
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_impactCell.modelData.val) || "-"
                                        color: Theme.AppTheme.textPrimary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.bodySize
                                        font.bold: true
                                        wrapMode: Text.NoWrap
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.AppTheme.divider
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: "Mitigation Strategy"
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.bold: true
                        }

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: root._sv("mitigationStrategy") || "No mitigation strategy defined."
                            color: root._sv("mitigationStrategy").length > 0
                                ? Theme.AppTheme.textPrimary
                                : Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.bodySize
                            wrapMode: Text.WordWrap
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: Theme.AppTheme.divider
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 0

                            Repeater {
                                model: [
                                    { "lbl": "Mitigation Owner", "val": root._sv("mitigationOwner") },
                                    { "lbl": "Due Date",         "val": root._sv("mitigationDueDateLabel") },
                                    { "lbl": "Escalation",       "val": root._sv("escalationStatus") }
                                ]

                                delegate: ColumnLayout {
                                    id: _mitigationCell
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingXs

                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_mitigationCell.modelData.lbl)
                                        color: Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                    }
                                    AppControls.Label {
                                        Layout.fillWidth: true
                                        text: String(_mitigationCell.modelData.val) || "-"
                                        color: Theme.AppTheme.textSecondary
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.smallSize
                                        wrapMode: Text.NoWrap
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec2
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Response")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Response"
                }

                Item {
                    width: parent.width
                    implicitHeight: urgentSection.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    ProjectManagementWidgets.RegisterUrgentSection {
                        id: urgentSection
                        anchors.top: parent.top
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.topMargin: Theme.AppTheme.spacingMd
                        anchors.leftMargin: Theme.AppTheme.spacingMd
                        anchors.rightMargin: Theme.AppTheme.spacingMd

                        urgentModel: root.urgentModel
                        selectedEntryId: root.selectedEntryId

                        onEntrySelected: function(entryId) { root.urgentEntrySelected(entryId) }
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec3
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Links")
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: 0

                AppWidgets.SectionHeading {
                    width: parent.width
                    label: "Links"
                }

                Item {
                    width: parent.width
                    implicitHeight: _activityFeed.implicitHeight + Theme.AppTheme.spacingMd * 2
                    height: implicitHeight

                    AppWidgets.ActivityFeed {
                        id: _activityFeed
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.spacingMd
                        items: (root.entryDetail.state && root.entryDetail.state.activityItems)
                            ? root.entryDetail.state.activityItems
                            : []
                        emptyText: root._hasEntry
                            ? "No activity has been recorded for this risk entry."
                            : "Select a risk entry to view linked activity."
                    }
                }
            }
        }
    }
}
