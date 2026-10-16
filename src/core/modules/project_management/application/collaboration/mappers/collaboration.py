"""Map collaboration data without desktop labels or deletion placeholders."""

from collections.abc import Mapping, Sequence

from src.core.modules.project_management.application.collaboration.dto.responses.collaboration import (
    CollaborationContextOptionsDto,
    TaskCollaborationReactionSummaryDto,
)
from src.core.modules.project_management.domain.collaboration import (
    CollaborationContextOptions,
)


def map_context_options(
    context: CollaborationContextOptions,
) -> CollaborationContextOptionsDto:
    return CollaborationContextOptionsDto(
        projects=context.projects, people=context.people
    )


def map_reactions(
    reactions: Mapping[str, Sequence[str]], *, principal_user_id: str
) -> tuple[TaskCollaborationReactionSummaryDto, ...]:
    return tuple(
        TaskCollaborationReactionSummaryDto(
            emoji=emoji,
            count=len(user_ids),
            reactor_user_ids=tuple(user_ids),
            reacted_by_current_user=bool(
                principal_user_id and principal_user_id in user_ids
            ),
        )
        for emoji, user_ids in sorted(reactions.items())
        if user_ids
    )
