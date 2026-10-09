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
    reader = SqlAlchemyActivityActorReader(session)
    labels: dict[str, tuple[str, str]] = {}
    for offset in range(0, len(ids), 200):
        labels.update({
            actor_id: (actor.kind.value, actor.label)
            for actor_id, actor in reader.resolve_batch(
                tenant_id=tenant_id, actor_ids=ids[offset:offset + 200]
            ).items()
        })
    return labels


__all__ = ["actor_labels_for_page"]
