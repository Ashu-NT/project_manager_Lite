"""Document command handlers."""

from src.core.platform.application.master_data.documents.commands.document_attachment_commands import (
    DocumentAttachmentCommandHandler,
    link_existing_document_in_uow,
    register_entity_attachments_in_uow,
)
from src.core.platform.application.master_data.documents.commands.document_commands import (
    DocumentCommandHandler,
)
from src.core.platform.application.master_data.documents.commands.document_structure_commands import (
    DocumentStructureCommandHandler,
)

__all__ = [
    "DocumentAttachmentCommandHandler",
    "DocumentCommandHandler",
    "DocumentStructureCommandHandler",
    "link_existing_document_in_uow",
    "register_entity_attachments_in_uow",
]
