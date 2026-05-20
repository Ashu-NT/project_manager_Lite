import QtQuick
import App.Mock 1.0 as AppMock
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

InventoryWidgets.RecordListCard {
    id: root

    property var reservationsModel: AppMock.MockFactory.catalog()
    property string selectedReservationId: ""
    property bool isBusy: false

    signal reservationSelected(string reservationId)
    signal issueRequested(var reservationData)
    signal releaseRequested(var reservationData)
    signal cancelRequested(var reservationData)

    title: root.reservationsModel.title || "Reservations"
    subtitle: root.reservationsModel.subtitle || ""
    emptyState: root.reservationsModel.emptyState || ""
    items: root.reservationsModel.items || []
    selectedItemId: root.selectedReservationId
    primaryActionLabel: "Issue"
    secondaryActionLabel: "Release"
    tertiaryActionLabel: "Cancel"
    actionsEnabled: !root.isBusy

    onItemSelected: function(reservationId) {
        root.reservationSelected(reservationId)
    }

    onPrimaryActionRequested: function(reservationData) {
        root.issueRequested(reservationData)
    }

    onSecondaryActionRequested: function(reservationData) {
        root.releaseRequested(reservationData)
    }

    onTertiaryActionRequested: function(reservationData) {
        root.cancelRequested(reservationData)
    }
}
