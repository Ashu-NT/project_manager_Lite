import QtQuick
import QtQuick.Layouts
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

Item {
    id: root

    property var scheduleModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property var criticalPathModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })

    implicitHeight: scheduleGrid.implicitHeight

    GridLayout {
        id: scheduleGrid

        width: parent ? parent.width : implicitWidth
        columns: width > 1180 ? 2 : 1
        columnSpacing: 12
        rowSpacing: 12

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            title: root.scheduleModel.title || "Schedule Snapshot"
            subtitle: root.scheduleModel.subtitle || ""
            emptyState: root.scheduleModel.emptyState || ""
            items: root.scheduleModel.items || []
        }

        ProjectManagementWidgets.RecordListCard {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            title: root.criticalPathModel.title || "Critical Path"
            subtitle: root.criticalPathModel.subtitle || ""
            emptyState: root.criticalPathModel.emptyState || ""
            items: root.criticalPathModel.items || []
        }
    }
}
