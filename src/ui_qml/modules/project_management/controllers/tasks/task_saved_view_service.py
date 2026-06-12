from __future__ import annotations

from .task_utils import normalize_task_view_state


class TaskSavedViewService:
    """Manages persistence and resolution of named task filter views."""

    def __init__(self, view_store) -> None:
        self._store = view_store
        self._views: dict[str, dict[str, object]] = {}

    # ── Lifecycle ─────────────────────────────────────────────────────

    def load_and_init(self) -> None:
        raw = self._store.load_task_saved_views()
        self._views = {
            (name or "").strip(): normalize_task_view_state(state)
            for name, state in raw.items()
            if (name or "").strip() and isinstance(state, dict)
        }

    def persist(self) -> None:
        self._store.save_task_saved_views(self._views)

    # ── Read ──────────────────────────────────────────────────────────

    @property
    def views(self) -> dict[str, dict[str, object]]:
        return self._views

    def build_options(self) -> list[dict[str, str]]:
        options: list[dict[str, str]] = [{"value": "", "label": "Current Filters"}]
        options.extend({"value": n, "label": n} for n in sorted(self._views))
        return options

    def resolve_view_state(self, view_name: str) -> dict[str, object] | None:
        state = self._views.get(view_name)
        return normalize_task_view_state(state) if isinstance(state, dict) else None

    def has_view(self, view_name: str) -> bool:
        return view_name in self._views

    # ── Write ─────────────────────────────────────────────────────────

    def save_view(self, view_name: str, state: dict[str, object]) -> None:
        self._views[view_name] = state

    def delete_view(self, view_name: str) -> None:
        self._views.pop(view_name, None)


__all__ = ["TaskSavedViewService"]
