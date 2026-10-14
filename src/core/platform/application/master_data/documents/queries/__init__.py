"""Document query handlers."""

from src.core.platform.application.master_data.documents.queries.document_attachment_queries import (
    DocumentAttachmentQueryHandler,
)
from src.core.platform.application.master_data.documents.queries.document_queries import (
    DocumentPage,
    DocumentQueryHandler,
    EntityDocumentPage,
    EntityDocumentRow,
)

__all__ = [
    "DocumentAttachmentQueryHandler",
    "DocumentPage",
    "DocumentQueryHandler",
    "EntityDocumentPage",
    "EntityDocumentRow",
]
