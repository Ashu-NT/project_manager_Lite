from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationMetricViewModel,
    CollaborationOverviewViewModel,
)


def build_overview(
    *,
    inbox: CollaborationCollectionViewModel,
    mentions: CollaborationCollectionViewModel,
    approvals: CollaborationCollectionViewModel,
    active_users_count: int,
) -> CollaborationOverviewViewModel:
    return CollaborationOverviewViewModel(
        title="Collaboration",
        subtitle=(
            "Principal inbox, task communication, Platform approvals, and recent activity "
            "across the accessible project scope."
        ),
        metrics=(
            CollaborationMetricViewModel(
                label="Inbox",
                value=str(inbox.total_count),
                supporting_text="Principal-scoped collaboration items in the current query.",
            ),
            CollaborationMetricViewModel(
                label="Approvals",
                value=str(approvals.total_count or len(approvals.items)),
                supporting_text="Governed approval requests currently visible to the user.",
            ),
            CollaborationMetricViewModel(
                label="Mentions",
                value=str(mentions.total_count),
                supporting_text="Mention threads across active project work.",
            ),
            CollaborationMetricViewModel(
                label="Active Users",
                value=str(active_users_count),
                supporting_text="People currently active in task collaboration or review flows.",
            ),
        ),
    )
