"""Task queries."""

from src.core.modules.project_management.application.tasks.queries.collaboration_comments import (
    CollaborationCommentQueryMixin,
)
from src.core.modules.project_management.application.tasks.queries.collaboration_documents import (
    CollaborationDocumentQueryMixin,
)
from src.core.modules.project_management.application.tasks.queries.collaboration_inbox import (
    CollaborationInboxQueryMixin,
)
from src.core.modules.project_management.application.tasks.queries.collaboration_notifications import (
    CollaborationNotificationQueryMixin,
)
from src.core.modules.project_management.application.tasks.queries.collaboration_presence import (
    CollaborationPresenceQueryMixin,
)
from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    DependencyDiagnostic,
    DependencyImpactRow,
    TaskDependencyDiagnosticsMixin,
)
from src.core.modules.project_management.application.tasks.queries.task_query import (
    TaskQueryMixin,
)

__all__ = [
    "CollaborationCommentQueryMixin",
    "CollaborationDocumentQueryMixin",
    "CollaborationInboxQueryMixin",
    "CollaborationNotificationQueryMixin",
    "CollaborationPresenceQueryMixin",
    "DependencyDiagnostic",
    "DependencyImpactRow",
    "TaskDependencyDiagnosticsMixin",
    "TaskQueryMixin",
]
