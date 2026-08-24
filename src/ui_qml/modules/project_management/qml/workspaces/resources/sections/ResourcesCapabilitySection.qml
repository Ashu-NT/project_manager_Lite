pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var workspaceController: null
    property string resourceId: ""
    property bool hasResource: false
    property bool canManageSkills: false
    property bool isBusy: false
    property int activeTabIndex: 0

    signal addSkillRequested()
    signal addCertificationRequested()
    signal removeSkillRequested(string skillId)
    signal removeCertificationRequested(string certId)
    signal skillSelectionChanged(string skillId)
    signal certificationSelectionChanged(string certId)

    readonly property var _tabs: [
        {
            "id": "skills",
            "label": "Skills",
            "count": root.workspaceController
                ? Number(root.workspaceController.resourceSkillCount || 0) : 0
        },
        {
            "id": "certifications",
            "label": "Certifications",
            "count": root.workspaceController
                ? Number(root.workspaceController.resourceCertificationCount || 0) : 0
        }
    ]
    readonly property int _resolvedTabIndex: Math.max(
        0, Math.min(root.activeTabIndex, root._tabs.length - 1)
    )
    readonly property real _activePanelHeight: root._resolvedTabIndex === 0
        ? skillsSection.implicitHeight
        : certificationsSection.implicitHeight

    onResourceIdChanged: {
        skillsSection.clearSelection()
        certificationsSection.clearSelection()
        root.skillSelectionChanged("")
        root.certificationSelectionChanged("")
    }

    function _switchTab(index) {
        const nextIndex = Math.max(0, Math.min(Number(index), root._tabs.length - 1))
        if (nextIndex === root.activeTabIndex) return
        root.activeTabIndex = nextIndex
        if (nextIndex === 0) {
            certificationsSection.clearSelection()
            root.certificationSelectionChanged("")
        } else {
            skillsSection.clearSelection()
            root.skillSelectionChanged("")
        }
    }

    implicitHeight: contentColumn.implicitHeight
    height: implicitHeight

    ColumnLayout {
        id: contentColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.DetailTabBar {
            Layout.fillWidth: true
            tabs: root._tabs
            currentIndex: root._resolvedTabIndex
            onTabSelected: function(index) { root._switchTab(index) }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: root._activePanelHeight
            implicitHeight: root._activePanelHeight
            currentIndex: root._resolvedTabIndex

            ResourcesSkillsSection {
                id: skillsSection
                Layout.fillWidth: true
                workspaceController: root.workspaceController
                hasResource: root.hasResource
                canManageSkills: root.canManageSkills
                isBusy: root.isBusy
                onAddSkillRequested: root.addSkillRequested()
                onSelectionChanged: function(skillId) {
                    root.skillSelectionChanged(String(skillId || ""))
                }
                onRemoveSkillRequested: function(skillId) {
                    root.removeSkillRequested(skillId)
                }
            }

            ResourcesCertificationsSection {
                id: certificationsSection
                Layout.fillWidth: true
                workspaceController: root.workspaceController
                hasResource: root.hasResource
                canManageSkills: root.canManageSkills
                isBusy: root.isBusy
                onAddCertificationRequested: root.addCertificationRequested()
                onSelectionChanged: function(certId) {
                    root.certificationSelectionChanged(String(certId || ""))
                }
                onRemoveCertificationRequested: function(certId) {
                    root.removeCertificationRequested(certId)
                }
            }
        }
    }
}
