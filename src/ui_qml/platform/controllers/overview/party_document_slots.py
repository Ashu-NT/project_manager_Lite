from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Slot

from src.ui_qml.platform.controllers.common import PlatformWorkspaceControllerBase
from src.ui_qml.platform.controllers.documents.actions import (
    add_document_link,
    create_document,
    create_document_structure,
    remove_document_link,
    select_document,
    toggle_document_active,
    toggle_document_structure_active,
    update_document,
    update_document_structure,
)
from src.ui_qml.platform.controllers.parties.actions import (
    activate_party,
    create_party,
    deactivate_party,
    toggle_party_active,
    update_party,
)

if TYPE_CHECKING:
    from src.ui_qml.platform.controllers.documents.document_controller import (
        PlatformDocumentController,
    )
    from src.ui_qml.platform.controllers.parties.party_controller import (
        PlatformPartyController,
    )


class PlatformAdminPartyDocumentSlots(PlatformWorkspaceControllerBase):
    _party_controller: PlatformPartyController
    _document_controller: PlatformDocumentController

    @Slot("QVariantMap", result="QVariantMap")
    def createParty(self, payload: dict[str, object]) -> dict[str, object]:
        return create_party(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateParty(self, payload: dict[str, object]) -> dict[str, object]:
        return update_party(self, payload)

    @Slot(str, result="QVariantMap")
    def togglePartyActive(self, party_id: str) -> dict[str, object]:
        return toggle_party_active(self, party_id)

    @Slot(str, result="QVariantMap")
    def activateParty(self, party_id: str) -> dict[str, object]:
        return activate_party(self, party_id)

    @Slot(str, result="QVariantMap")
    def deactivateParty(self, party_id: str) -> dict[str, object]:
        return deactivate_party(self, party_id)

    @Slot(int)
    def setPartyPage(self, page: int) -> None:
        self._party_controller.setPartyPage(page)

    @Slot(int)
    def setPartyPageSize(self, page_size: int) -> None:
        self._party_controller.setPartyPageSize(page_size)

    @Slot(str)
    def setPartySearchText(self, value: str) -> None:
        self._party_controller.setPartySearchText(value)

    @Slot(str)
    def setPartyStatusFilter(self, status: str) -> None:
        self._party_controller.setPartyStatusFilter(status)

    @Slot(str)
    def setPartyTypeFilter(self, party_type: str) -> None:
        self._party_controller.setPartyTypeFilter(party_type)

    @Slot(str)
    def setPartyRoleFilter(self, role: str) -> None:
        self._party_controller.setPartyRoleFilter(role)

    @Slot(str, str, result="QVariantList")
    def partyActivity(self, party_id: str, organization_id: str) -> list[dict[str, object]]:
        result = self._party_controller.partyActivity(party_id, organization_id)
        self._set_error_message(cast("str", self._party_controller.errorMessage))
        return result

    @Slot(str, str, int, int, str, str, result="QVariantMap")
    def partyActivityPage(
        self, party_id: str, organization_id: str, page: int, page_size: int,
        search: str, date_range: str,
    ) -> dict[str, object]:
        return self._party_controller.partyActivityPage(
            party_id, organization_id, page, page_size, search, date_range
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDocument(self, payload: dict[str, object]) -> dict[str, object]:
        return create_document(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateDocument(self, payload: dict[str, object]) -> dict[str, object]:
        return update_document(self, payload)

    @Slot(str, result="QVariantMap")
    def toggleDocumentActive(self, document_id: str) -> dict[str, object]:
        return toggle_document_active(self, document_id)

    @Slot(str)
    def selectDocument(self, document_id: str) -> None:
        select_document(self, document_id)

    @Slot(str, int, int, str, str, result="QVariantMap")
    def organizationDocumentsPage(
        self, organization_id: str, page: int, page_size: int,
        search: str, status: str,
    ) -> dict[str, object]:
        return self._document_controller.organizationDocumentsPage(
            organization_id, page, page_size, search, status
        )

    @Slot("QVariantMap", result="QVariantMap")
    def createDocumentStructure(self, payload: dict[str, object]) -> dict[str, object]:
        return create_document_structure(self, payload)

    @Slot("QVariantMap", result="QVariantMap")
    def updateDocumentStructure(self, payload: dict[str, object]) -> dict[str, object]:
        return update_document_structure(self, payload)

    @Slot(str, result="QVariantMap")
    def toggleDocumentStructureActive(self, structure_id: str) -> dict[str, object]:
        return toggle_document_structure_active(self, structure_id)

    @Slot("QVariantMap", result="QVariantMap")
    def addDocumentLink(self, payload: dict[str, object]) -> dict[str, object]:
        return add_document_link(self, payload)

    @Slot(str, result="QVariantMap")
    def removeDocumentLink(self, link_id: str) -> dict[str, object]:
        return remove_document_link(self, link_id)
