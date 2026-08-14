pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "../sections" as Sections

Flickable {
    id: root

    property ProjectManagementControllers.ProjectManagementPortfolioWorkspaceController workspaceController
    property var scenariosModel: ({ "title": "Scenario Library", "subtitle": "", "emptyState": "", "items": [] })
    property var templatesModel: ({ "title": "Scoring Templates", "subtitle": "", "emptyState": "", "items": [] })

    contentWidth: width
    contentHeight: _col.implicitHeight + Theme.AppTheme.marginMd * 2
    boundsBehavior: Flickable.StopAtBounds
    clip: true

    ColumnLayout {
        id: _col
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingLg

        Sections.PortfolioGovernanceToolbar {
            Layout.fillWidth: true
            scenarioOptions: root.workspaceController ? (root.workspaceController.scenarioOptions || []) : []
            selectedScenarioId: root.workspaceController ? root.workspaceController.selectedScenarioId : ""
            selectedBaseScenarioId: root.workspaceController ? root.workspaceController.selectedBaseScenarioId : ""
            selectedCompareScenarioId: root.workspaceController ? root.workspaceController.selectedCompareScenarioId : ""
            evaluationModel: root.workspaceController ? root.workspaceController.evaluation : ({ "fields": [] })
            comparisonModel: root.workspaceController ? root.workspaceController.comparison : ({ "fields": [] })
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onScenarioSelected: function(id) { if (root.workspaceController !== null) root.workspaceController.selectScenario(id) }
            onCompareBaseSelected: function(id) { if (root.workspaceController !== null) root.workspaceController.selectCompareBase(id) }
            onCompareScenarioSelected: function(id) { if (root.workspaceController !== null) root.workspaceController.selectCompareScenario(id) }
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                text: root.scenariosModel.title || "Scenario Library"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: root.scenariosModel.subtitle || ""
                visible: text.length > 0
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                wrapMode: Text.WordWrap
            }

            AppWidgets.EmptyState {
                Layout.fillWidth: true
                visible: (root.scenariosModel.items || []).length === 0
                title: "No scenarios yet"
                message: root.scenariosModel.emptyState || "No portfolio scenarios are available yet."
            }

            Repeater {
                model: root.scenariosModel.items || []

                delegate: Rectangle {
                    id: _scnRow
                    required property var modelData
                    Layout.fillWidth: true
                    implicitHeight: _scnRowLayout.implicitHeight + Theme.AppTheme.spacingSm * 2
                    radius: Theme.AppTheme.radiusSm
                    color: (root.workspaceController && root.workspaceController.selectedScenarioId === String(_scnRow.modelData.id || ""))
                        ? Qt.rgba(Theme.AppTheme.accent.r, Theme.AppTheme.accent.g, Theme.AppTheme.accent.b, 0.08)
                        : Theme.AppTheme.surfaceAlt
                    border.color: Theme.AppTheme.subtleBorder
                    border.width: 1

                    ColumnLayout {
                        id: _scnRowLayout
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: Theme.AppTheme.spacingSm
                        spacing: 2

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_scnRow.modelData.title || "")
                            color: Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.smallSize
                            font.bold: true
                            elide: Text.ElideRight
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_scnRow.modelData.subtitle || "")
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            elide: Text.ElideRight
                        }
                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(_scnRow.modelData.supportingText || "")
                            color: Theme.AppTheme.textSecondary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                            elide: Text.ElideRight
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (root.workspaceController !== null)
                                root.workspaceController.selectScenario(String(_scnRow.modelData.id || ""))
                        }
                    }
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.Label {
                Layout.fillWidth: true
                text: root.templatesModel.title || "Scoring Templates"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }

            AppControls.Label {
                Layout.fillWidth: true
                text: root.templatesModel.subtitle || ""
                visible: text.length > 0
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            Repeater {
                model: root.templatesModel.items || []

                delegate: Rectangle {
                    id: _tplRow
                    required property var modelData
                    Layout.fillWidth: true
                    height: _tplRowLayout.implicitHeight + 16
                    radius: Theme.AppTheme.radiusSm
                    color: Theme.AppTheme.surfaceAlt
                    border.color: Theme.AppTheme.subtleBorder
                    border.width: 1

                    RowLayout {
                        id: _tplRowLayout
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.top: parent.top
                        anchors.margins: 8
                        spacing: Theme.AppTheme.spacingSm

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_tplRow.modelData.title || "")
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.smallSize
                                font.bold: true
                                elide: Text.ElideRight
                            }

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(_tplRow.modelData.subtitle || "")
                                color: Theme.AppTheme.textSecondary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                elide: Text.ElideRight
                            }
                        }

                        AppWidgets.StatusChip {
                            status: String(_tplRow.modelData.statusLabel || "")
                        }

                        AppControls.SecondaryButton {
                            visible: Boolean(_tplRow.modelData.canPrimaryAction)
                            text: "Activate"
                            iconName: "approve"
                            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            onClicked: {
                                if (root.workspaceController !== null)
                                    root.workspaceController.activateTemplate(
                                        String((_tplRow.modelData.state || {}).templateId || "")
                                    )
                            }
                        }
                    }
                }
            }

            AppControls.Label {
                Layout.fillWidth: true
                visible: (root.templatesModel.items || []).length === 0
                text: root.templatesModel.emptyState || "No scoring templates available."
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }
        }
    }
}
