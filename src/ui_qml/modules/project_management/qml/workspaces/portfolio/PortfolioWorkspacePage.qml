import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementPortfolioWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.portfolioWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.portfolio",
            "title": "Portfolio",
            "summary": "Portfolio summaries, cross-project visibility, and decision support.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget portfolio workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: 12

            ProjectManagementWidgets.RegisterMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            ProjectManagementWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            ProjectManagementWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML portfolio planning slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Portfolio intake, scoring templates, scenario comparison, cross-project dependencies, and executive pressure views now run through a typed PM controller backed by the portfolio desktop API."
            }

            PortfolioToolbarSection {
                Layout.fillWidth: true
                intakeStatusOptions: root.workspaceController ? (root.workspaceController.intakeStatusOptions || []) : []
                scenarioOptions: root.workspaceController ? (root.workspaceController.scenarioOptions || []) : []
                selectedIntakeStatusFilter: root.workspaceController ? root.workspaceController.selectedIntakeStatusFilter : "all"
                selectedScenarioId: root.workspaceController ? root.workspaceController.selectedScenarioId : ""
                selectedBaseScenarioId: root.workspaceController ? root.workspaceController.selectedBaseScenarioId : ""
                selectedCompareScenarioId: root.workspaceController ? root.workspaceController.selectedCompareScenarioId : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onIntakeStatusFilterChanged: function(value) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setIntakeStatusFilter(value)
                    }
                }

                onScenarioChanged: function(value) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectScenario(value)
                    }
                }

                onCompareBaseChanged: function(value) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectCompareBase(value)
                    }
                }

                onCompareScenarioChanged: function(value) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectCompareScenario(value)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1360 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: 12

                    PortfolioIntakeSection {
                        Layout.fillWidth: true
                        intakeStatusOptions: root.workspaceController ? (root.workspaceController.intakeStatusOptions || []) : []
                        templateOptions: root.workspaceController ? (root.workspaceController.templateOptions || []) : []
                        intakeItemsModel: root.workspaceController ? root.workspaceController.intakeItems : ({
                            "title": "Portfolio Intake",
                            "subtitle": "",
                            "emptyState": "",
                            "items": []
                        })
                        selectedStatusFilter: root.workspaceController ? root.workspaceController.selectedIntakeStatusFilter : "all"
                        isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                        onCreateRequested: function(payload) {
                            if (root.workspaceController !== null) {
                                root.workspaceController.createIntakeItem(payload)
                            }
                        }
                    }

                    PortfolioTemplatesSection {
                        Layout.fillWidth: true
                        activeTemplateSummary: root.workspaceController ? root.workspaceController.activeTemplateSummary : ""
                        templatesModel: root.workspaceController ? root.workspaceController.templates : ({
                            "title": "Scoring Templates",
                            "subtitle": "",
                            "emptyState": "",
                            "items": []
                        })
                        isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                        onCreateRequested: function(payload) {
                            if (root.workspaceController !== null) {
                                root.workspaceController.createTemplate(payload)
                            }
                        }

                        onActivateRequested: function(templateId) {
                            if (root.workspaceController !== null) {
                                root.workspaceController.activateTemplate(templateId)
                            }
                        }
                    }

                    PortfolioScenariosSection {
                        Layout.fillWidth: true
                        projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                        scenarioOptions: root.workspaceController ? (root.workspaceController.scenarioOptions || []) : []
                        intakeItemsModel: root.workspaceController ? root.workspaceController.intakeItems : ({
                            "items": []
                        })
                        scenariosModel: root.workspaceController ? root.workspaceController.scenarios : ({
                            "title": "Scenario Library",
                            "subtitle": "",
                            "emptyState": "",
                            "items": []
                        })
                        evaluationModel: root.workspaceController ? root.workspaceController.evaluation : ({
                            "title": "Scenario Evaluation",
                            "subtitle": "",
                            "emptyState": "",
                            "fields": []
                        })
                        comparisonModel: root.workspaceController ? root.workspaceController.comparison : ({
                            "title": "Scenario Comparison",
                            "subtitle": "",
                            "emptyState": "",
                            "fields": []
                        })
                        isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                        onCreateRequested: function(payload) {
                            if (root.workspaceController !== null) {
                                root.workspaceController.createScenario(payload)
                            }
                        }

                        onScenarioSelected: function(scenarioId) {
                            if (root.workspaceController !== null) {
                                root.workspaceController.selectScenario(scenarioId)
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: 12

                    PortfolioDependenciesSection {
                        Layout.fillWidth: true
                        projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                        dependencyTypeOptions: root.workspaceController ? (root.workspaceController.dependencyTypeOptions || []) : []
                        dependenciesModel: root.workspaceController ? root.workspaceController.dependencies : ({
                            "title": "Cross-project Dependencies",
                            "subtitle": "",
                            "emptyState": "",
                            "items": []
                        })
                        isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                        onCreateRequested: function(payload) {
                            if (root.workspaceController !== null) {
                                root.workspaceController.createDependency(payload)
                            }
                        }

                        onRemoveRequested: function(dependencyId) {
                            if (root.workspaceController !== null) {
                                root.workspaceController.removeDependency(dependencyId)
                            }
                        }
                    }

                    PortfolioExecutiveSection {
                        Layout.fillWidth: true
                        heatmapModel: root.workspaceController ? root.workspaceController.heatmap : ({
                            "title": "Portfolio Heatmap",
                            "subtitle": "",
                            "emptyState": "",
                            "items": []
                        })
                        recentActionsModel: root.workspaceController ? root.workspaceController.recentActions : ({
                            "title": "Recent Actions",
                            "subtitle": "",
                            "emptyState": "",
                            "items": []
                        })
                    }
                }
            }
        }
    }
}
