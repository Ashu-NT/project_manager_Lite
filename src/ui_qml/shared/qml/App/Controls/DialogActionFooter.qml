import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Item {
    id: root

    default property alias content: footerRow.data

    implicitHeight: footerRow.implicitHeight + (Theme.AppTheme.dialogPadding * 2)

    RowLayout {
        id: footerRow

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.dialogPadding
        spacing: Theme.AppTheme.spacingSm
    }
}
