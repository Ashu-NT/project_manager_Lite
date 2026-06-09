from __future__ import annotations


class ActivityLogService:
    def __init__(self) -> None:
        self._log: list[dict[str, str]] = []

    @property
    def log(self) -> list[dict[str, str]]:
        return self._log

    def reset(self) -> None:
        self._log = []

    def record(
        self,
        *,
        title: str,
        status_label: str,
        subtitle: str,
        meta_text: str,
    ) -> None:
        if not title.strip():
            return
        self._log = [
            {
                "title": title.strip(),
                "statusLabel": status_label.strip() or "Info",
                "subtitle": subtitle.strip(),
                "metaText": meta_text.strip(),
            },
            *self._log[:11],
        ]


__all__ = ["ActivityLogService"]
