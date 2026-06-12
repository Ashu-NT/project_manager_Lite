"""Mention entities, parsing rules, and value objects."""

from __future__ import annotations

import re
from dataclasses import dataclass


MENTION_RE = re.compile(r"@([A-Za-z0-9_.-]+)")


@dataclass(frozen=True)
class CollaborationMentionCandidate:
    user_id: str
    username: str
    display_name: str | None = None
    scope_role: str | None = None

    @property
    def handle(self) -> str:
        return (self.username or "").strip().lower()

    @property
    def label(self) -> str:
        display = (self.display_name or "").strip()
        role = (self.scope_role or "").strip()
        pieces = [f"@{self.handle}"]
        if display and display.lower() != self.handle:
            pieces.append(display)
        if role:
            pieces.append(role.title())
        return "  ".join(piece for piece in pieces if piece)


def extract_mention_tokens(text: str) -> list[str]:
    return [match.lower() for match in MENTION_RE.findall(text or "")]


def candidate_handles(candidate: CollaborationMentionCandidate) -> set[str]:
    handles = {candidate.handle}
    display = (candidate.display_name or "").strip().lower()
    if display:
        handles.add(display.strip(" @"))
        handles.add(display.replace(" ", "").strip(" @"))
        handles.add(display.replace(" ", ".").strip(" @"))
    return {token for token in handles if token}


def resolve_mentions(
    *,
    text: str,
    candidates: list[CollaborationMentionCandidate],
) -> tuple[list[str], list[str], list[str]]:
    handle_map: dict[str, CollaborationMentionCandidate] = {}
    for candidate in candidates:
        for token in candidate_handles(candidate):
            handle_map[token] = candidate

    canonical_mentions: set[str] = set()
    mentioned_user_ids: set[str] = set()
    unresolved: set[str] = set()
    for token in extract_mention_tokens(text):
        candidate = handle_map.get(token)
        if candidate is None:
            unresolved.add(token)
            continue
        canonical_mentions.add(candidate.handle)
        mentioned_user_ids.add(candidate.user_id)

    return sorted(canonical_mentions), sorted(mentioned_user_ids), sorted(unresolved)


__all__ = [
    "CollaborationMentionCandidate",
    "MENTION_RE",
    "candidate_handles",
    "extract_mention_tokens",
    "resolve_mentions",
]
