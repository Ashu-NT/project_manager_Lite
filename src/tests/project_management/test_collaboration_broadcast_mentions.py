"""@everyone / @team broadcast mention resolution."""

from __future__ import annotations

from src.core.modules.project_management.domain.collaboration.mentions.mention import (
    CollaborationMentionCandidate,
    resolve_mentions,
)


def _candidates() -> list[CollaborationMentionCandidate]:
    return [
        CollaborationMentionCandidate(user_id="user-1", username="alex", display_name="Alex Planner"),
        CollaborationMentionCandidate(user_id="user-2", username="planner", display_name="Project Planner"),
        CollaborationMentionCandidate(user_id="user-3", username="jordan", display_name="Jordan Blake"),
    ]


def test_at_everyone_resolves_to_every_candidate_user_id():
    mentions, mentioned_user_ids, unresolved = resolve_mentions(
        text="Heads up @everyone, deadline moved.",
        candidates=_candidates(),
    )

    assert mentions == ["everyone"]
    assert mentioned_user_ids == ["user-1", "user-2", "user-3"]
    assert unresolved == []


def test_at_team_resolves_to_every_candidate_user_id():
    mentions, mentioned_user_ids, unresolved = resolve_mentions(
        text="@team please review before Friday.",
        candidates=_candidates(),
    )

    assert mentions == ["team"]
    assert mentioned_user_ids == ["user-1", "user-2", "user-3"]
    assert unresolved == []


def test_at_everyone_with_no_candidates_is_a_noop_not_an_error():
    mentions, mentioned_user_ids, unresolved = resolve_mentions(
        text="@everyone welcome aboard.",
        candidates=[],
    )

    assert mentions == ["everyone"]
    assert mentioned_user_ids == []
    assert unresolved == []


def test_broadcast_and_individual_mentions_combine_in_one_message():
    mentions, mentioned_user_ids, unresolved = resolve_mentions(
        text="@everyone but especially @jordan please look at this.",
        candidates=_candidates(),
    )

    assert mentions == ["everyone", "jordan"]
    assert mentioned_user_ids == ["user-1", "user-2", "user-3"]
    assert unresolved == []
