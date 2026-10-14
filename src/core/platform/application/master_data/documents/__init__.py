from src.core.platform.application.master_data.documents.commands import (
    DocumentAttachmentCommandHandler,
    DocumentCommandHandler,
    DocumentStructureCommandHandler,
)
from src.core.platform.application.master_data.documents.document_access import (
    PermissionDocumentAccessPolicy,
)
from src.core.platform.application.master_data.documents.queries import (
    DocumentAttachmentQueryHandler,
    DocumentQueryHandler,
)

__all__ = [
    "DocumentAttachmentCommandHandler",
    "DocumentAttachmentQueryHandler",
    "DocumentCommandHandler",
    "DocumentQueryHandler",
    "DocumentStructureCommandHandler",
    "PermissionDocumentAccessPolicy",
]
