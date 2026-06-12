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
    unread_count: int,
    attention_count: int,
    active_users_count: int,
) -> CollaborationOverviewViewModel:
    return CollaborationOverviewViewModel(
        title="Collaboration",
        subtitle=(
            "Workflow inbox, operational communication, mentions, approvals, and activity feed "
            "across the accessible project scope."
        ),
        metrics=(
            CollaborationMetricViewModel(
                label="Unread",
                value=str(unread_count),
                supporting_text="Direct mentions and task follow-ups awaiting review.",
            ),
            CollaborationMetricViewModel(
                label="Approvals",
                value=str(len(approvals.items)),
                supporting_text="Governed approval requests currently visible to the user.",
            ),
            CollaborationMetricViewModel(
                label="Mentions",
                value=str(len(mentions.items)),
                supporting_text="Mention threads across active project work.",
            ),
            CollaborationMetricViewModel(
                label="Reviews",
                value=str(attention_count),
                supporting_text="Workflow items currently flagged as needing attention.",
            ),
            CollaborationMetricViewModel(
                label="Active Users",
                value=str(active_users_count),
                supporting_text="People currently active in task collaboration or review flows.",
            ),
            CollaborationMetricViewModel(
                label="Workflow Alerts",
                value=str(len(inbox.items)),
                supporting_text="Operational workflow items in the inbox stream.",
            ),
        ),
    )
