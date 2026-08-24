pragma ComponentBehavior: Bound

import QtQuick
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import workspaces.resources.sections 1.0

Item {
    id: root

    property var resourceDetail: ({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "Select a resource to open its details.",
        "fields": [], "state": {}
    })
    property bool isBusy: false
    property var detailPage: null
    property var workspaceController: null
    property bool canManageSkills: false
    property string selectedSkillId: ""
    property string selectedCertificationId: ""

    signal addSkillRequested()
    signal addCertificationRequested()
    signal removeSkillRequested(string skillId)
    signal removeCertificationRequested(string certId)
    signal skillSelectionChanged(string skillId)
    signal certificationSelectionChanged(string certId)

    readonly property bool _hasResource: String(root.resourceDetail.id || "").length > 0
    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0

    function _clearCapabilitySelections() {
        if (root._idx === 1) return
        if (root.selectedSkillId.length > 0) {
            root.selectedSkillId = ""
            root.skillSelectionChanged("")
        }
        if (root.selectedCertificationId.length > 0) {
            root.selectedCertificationId = ""
            root.certificationSelectionChanged("")
        }
    }

    on_IdxChanged: root._clearCapabilitySelections()
    onResourceDetailChanged: {
        root.selectedSkillId = ""
        root.selectedCertificationId = ""
        root.skillSelectionChanged("")
        root.certificationSelectionChanged("")
    }

    readonly property int _activeSectionHeight: {
        if (root._idx === 0) return overviewLoader.implicitHeight
        if (root._idx === 1) return capabilityLoader.implicitHeight
        if (root._idx === 2) return availabilityLoader.implicitHeight
        if (root._idx === 3) return projectsLoader.implicitHeight
        if (root._idx === 4) return assignmentsLoader.implicitHeight
        if (root._idx === 5) return activityLoader.implicitHeight
        return 0
    }

    implicitHeight: root._activeSectionHeight
    height: implicitHeight

    AppWidgets.LazySectionLoader {
        id: overviewLoader
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 0
        loadingMessage: "Loading Resource overview..."
        sourceComponent: Component {
            ResourcesOverviewSection {
                width: parent ? parent.width : 0
                resourceDetail: root.resourceDetail
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: capabilityLoader
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 1
        loadingMessage: "Loading Resource capability..."
        sourceComponent: Component {
            Column {
                width: parent ? parent.width : 0
                spacing: Theme.AppTheme.spacingMd

                ResourcesSkillsSection {
                    width: parent.width
                    workspaceController: root.workspaceController
                    hasResource: root._hasResource
                    canManageSkills: root.canManageSkills
                    isBusy: root.isBusy
                    onAddSkillRequested: root.addSkillRequested()
                    onSelectionChanged: function(skillId) {
                        root.selectedSkillId = String(skillId || "")
                        if (root.selectedSkillId.length > 0 && root.selectedCertificationId.length > 0) {
                            root.selectedCertificationId = ""
                            root.certificationSelectionChanged("")
                        }
                        root.skillSelectionChanged(root.selectedSkillId)
                    }
                    onRemoveSkillRequested: function(skillId) {
                        root.removeSkillRequested(skillId)
                    }
                }

                ResourcesCertificationsSection {
                    width: parent.width
                    workspaceController: root.workspaceController
                    hasResource: root._hasResource
                    canManageSkills: root.canManageSkills
                    isBusy: root.isBusy
                    onAddCertificationRequested: root.addCertificationRequested()
                    onSelectionChanged: function(certId) {
                        root.selectedCertificationId = String(certId || "")
                        if (root.selectedCertificationId.length > 0 && root.selectedSkillId.length > 0) {
                            root.selectedSkillId = ""
                            root.skillSelectionChanged("")
                        }
                        root.certificationSelectionChanged(root.selectedCertificationId)
                    }
                    onRemoveCertificationRequested: function(certId) {
                        root.removeCertificationRequested(certId)
                    }
                }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: availabilityLoader
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 2
        sourceComponent: Component {
            ResourcesDeferredSection {
                width: parent ? parent.width : 0
                title: "Availability"
                message: "The authoritative calendar and workload projection is delivered in R5D. No legacy capacity formula is shown here."
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: projectsLoader
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 3
        sourceComponent: Component {
            ResourcesDeferredSection {
                width: parent ? parent.width : 0
                title: "Projects"
                message: "The scoped, paged Resource-to-Projects reader is delivered in R5E."
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: assignmentsLoader
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 4
        sourceComponent: Component {
            ResourcesDeferredSection {
                width: parent ? parent.width : 0
                title: "Assignments"
                message: "The scoped, paged Resource-to-Assignments reader is delivered in R5E."
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: activityLoader
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 5
        sourceComponent: Component {
            ResourcesDeferredSection {
                width: parent ? parent.width : 0
                title: "Activity"
                message: "Authoritative audit and activity history is delivered in R5E. Assignment snapshots are not presented as history."
            }
        }
    }
}
