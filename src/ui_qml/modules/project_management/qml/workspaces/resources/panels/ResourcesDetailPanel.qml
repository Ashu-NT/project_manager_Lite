pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets
import "../sections"

Item {
    id: root

    property var resourceDetail: ({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "Select a resource from the pool to review details or edit its setup.",
        "fields": [], "state": {}
    })
    property bool isBusy: false
    property var detailPage: null
    property var workspaceController: null
    property var resourceAvailabilityModel: ({
        "resourceId": "", "peakLoadPercent": 0, "averageLoadPercent": 0,
        "overloadedDays": 0, "availableDays": 0, "isAvailable": true,
        "fromDateLabel": "", "toDateLabel": "", "days": []
    })
    property bool canManageSkills: true
    property var resourceAssignmentsTableModel: null

    signal editRequested()
    signal toggleRequested()
    signal deleteRequested()
    signal addSkillRequested()
    signal addCertificationRequested()
    signal removeSkillRequested(string skillId)
    signal removeCertificationRequested(string certId)

    readonly property bool _hasResource: String(root.resourceDetail.id || "").length > 0
    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0

    readonly property int _activeSectionH: {
        if (root._idx === 0) return _sec0.implicitHeight
        if (root._idx === 1) return _sec1.implicitHeight
        if (root._idx === 2) return _sec2.implicitHeight
        if (root._idx === 3) return _sec3.implicitHeight
        if (root._idx === 4) return _sec4.implicitHeight
        if (root._idx === 5) return _sec5.implicitHeight
        if (root._idx === 6) return _sec6.implicitHeight
        if (root._idx === 7) return _sec8.implicitHeight
        if (root._idx === 8) return _sec7.implicitHeight
        return 0
    }

    implicitHeight: _activeSectionH
    height: implicitHeight

    AppWidgets.LazySectionLoader {
        id: _sec0
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 0
        loadingMessage: "Loading overview..."
        sourceComponent: Component {
            ResourcesOverviewSection {
                width: parent ? parent.width : 0
                resourceDetail: root.resourceDetail
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec1
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 1
        loadingMessage: "Loading assignments..."
        sourceComponent: Component {
            ResourcesAssignmentsSection {
                width: parent ? parent.width : 0
                resourceDetail: root.resourceDetail
                resourceAssignmentsTableModel: root.resourceAssignmentsTableModel
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec2
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 2
        loadingMessage: "Loading capacity..."
        sourceComponent: Component {
            ResourcesCapacitySection {
                width: parent ? parent.width : 0
                resourceDetail: root.resourceDetail
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec3
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 3
        loadingMessage: "Loading calendar..."
        sourceComponent: Component {
            ResourcesCalendarSection {
                width: parent ? parent.width : 0
                resourceDetail: root.resourceDetail
                resourceAvailabilityModel: root.resourceAvailabilityModel
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec4
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 4
        loadingMessage: "Loading skills..."
        sourceComponent: Component {
            ResourcesSkillsSection {
                width: parent ? parent.width : 0
                workspaceController: root.workspaceController
                hasResource: root._hasResource
                canManageSkills: root.canManageSkills
                isBusy: root.isBusy
                onAddSkillRequested: root.addSkillRequested()
                onRemoveSkillRequested: function(skillId) { root.removeSkillRequested(skillId) }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec5
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 5
        loadingMessage: "Loading certifications..."
        sourceComponent: Component {
            ResourcesCertificationsSection {
                width: parent ? parent.width : 0
                workspaceController: root.workspaceController
                hasResource: root._hasResource
                canManageSkills: root.canManageSkills
                isBusy: root.isBusy
                onAddCertificationRequested: root.addCertificationRequested()
                onRemoveCertificationRequested: function(certId) { root.removeCertificationRequested(certId) }
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec6
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 6
        loadingMessage: "Loading cost rates..."
        sourceComponent: Component {
            ResourcesCostRatesSection {
                width: parent ? parent.width : 0
                resourceDetail: root.resourceDetail
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec8
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 7
        loadingMessage: "Loading availability..."
        sourceComponent: Component {
            ResourcesAvailabilitySection {
                width: parent ? parent.width : 0
                hasResource: root._hasResource
                availabilityModel: root.resourceAvailabilityModel
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec7
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === 8
        loadingMessage: "Loading activity..."
        sourceComponent: Component {
            ResourcesActivitySection {
                width: parent ? parent.width : 0
                resourceDetail: root.resourceDetail
            }
        }
    }
}
