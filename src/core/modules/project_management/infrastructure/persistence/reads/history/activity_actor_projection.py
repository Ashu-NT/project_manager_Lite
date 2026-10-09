from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.platform.infrastructure.persistence.read.history.activity_actor_reader import (
    SqlAlchemyActivityActorReader,
)


def actor_labels_for_page(
    session: Session, *, tenant_id: str, actor_ids: tuple[str | None, ...]
) -> dict[str, tuple[str, str]]:
    """Resolve only actors from an already-authorized PM activity page."""
    ids = tuple(sorted({actor_id for actor_id in actor_ids if actor_id}))
    if not ids:
        return {}
    return {
        actor_id: (actor.kind.value, actor.label)
        for actor_id, actor in SqlAlchemyActivityActorReader(session).resolve_batch(
            tenant_id=tenant_id, actor_ids=ids
        ).items()
    }


__all__ = ["actor_labels_for_page"]
