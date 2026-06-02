pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Invoices" }

        AppWidgets.EmptyState {
            width: parent.width
            title: "No invoices"
            message: "Invoice management will be available in a future release."
        }
    }
}
