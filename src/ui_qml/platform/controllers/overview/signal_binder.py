"""Composite-controller signal rewiring for the temporary Admin Console facade.

Why it still exists: `PlatformAdminWorkspaceController` composes 9 single-entity
sub-controllers but exposes them to QML as if they were its own signals, since
AdminConsolePage.qml binds to one controller instance. This function rewires
each sub-controller's own Qt signals onto the composite's signals.

What contract it preserves: byte-for-byte the same signal-forwarding wiring
that previously lived in `controllers.admin.admin_child_signal_binder`.

Which later phase removes it: R2, when each capability controller is bound
directly to its own QML page and no composite re-forwarding is needed.
"""

from __future__ import annotations


def bind_child_signals(controller) -> None:
    controller._organization_controller.organizationsChanged.connect(
        controller.organizationsChanged.emit
    )
    controller._organization_controller.organizationEditorOptionsChanged.connect(
        controller.organizationEditorOptionsChanged.emit
    )
    controller._calendar_controller.calendarsChanged.connect(controller.calendarsChanged.emit)
    controller._site_controller.sitesChanged.connect(controller.sitesChanged.emit)
    controller._department_controller.departmentsChanged.connect(controller.departmentsChanged.emit)
    controller._department_controller.departmentEditorOptionsChanged.connect(
        controller.departmentEditorOptionsChanged.emit
    )
    controller._employee_controller.employeesChanged.connect(controller.employeesChanged.emit)
    controller._employee_controller.employeeEditorOptionsChanged.connect(
        controller.employeeEditorOptionsChanged.emit
    )
    controller._user_controller.usersChanged.connect(controller.usersChanged.emit)
    controller._user_controller.userEditorOptionsChanged.connect(
        controller.userEditorOptionsChanged.emit
    )
    controller._party_controller.partiesChanged.connect(controller.partiesChanged.emit)
    controller._party_controller.partyEditorOptionsChanged.connect(
        controller.partyEditorOptionsChanged.emit
    )
    controller._document_controller.documentsChanged.connect(controller.documentsChanged.emit)
    controller._document_controller.documentEditorOptionsChanged.connect(
        controller.documentEditorOptionsChanged.emit
    )
    controller._document_controller.selectedDocumentChanged.connect(
        controller.selectedDocumentChanged.emit
    )
    controller._document_controller.documentPreviewChanged.connect(
        controller.documentPreviewChanged.emit
    )
    controller._document_controller.documentLinksChanged.connect(
        controller.documentLinksChanged.emit
    )
    controller._document_structure_controller.documentStructuresChanged.connect(
        controller.documentStructuresChanged.emit
    )
    controller._document_structure_controller.documentStructureEditorOptionsChanged.connect(
        controller.documentStructureEditorOptionsChanged.emit
    )


__all__ = ["bind_child_signals"]
