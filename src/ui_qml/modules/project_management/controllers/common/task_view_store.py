from __future__ import annotations

import json
from collections.abc import Callable

from PySide6.QtCore import QSettings

from src.infra.platform.app_settings import AppSettingsStore


class ProjectManagementTaskViewStore:
    ORG_NAME = "TECHASH"
    APP_NAME = "ProjectManagerLite"

    _KEY_TASK_SAVED_VIEWS = "task/saved_views"

    def __init__(
        self,
        settings: QSettings | None = None,
        *,
        organization_id_provider: Callable[[], str | None] | None = None,
    ) -> None:
        self._settings = settings or QSettings(self.ORG_NAME, self.APP_NAME)
        self._organization_id_provider = organization_id_provider

    def set_organization_id_provider(
        self,
        organization_id_provider: Callable[[], str | None] | None,
    ) -> None:
        self._organization_id_provider = organization_id_provider

    def _settings_key(self) -> str:
        provider = self._organization_id_provider
        organization_id = provider() if provider is not None else None
        return AppSettingsStore._tenant_key(
            self._KEY_TASK_SAVED_VIEWS,
            organization_id,
        )

    def load_task_saved_views(self) -> dict[str, dict[str, object]]:
        raw = self._settings.value(self._settings_key(), "{}")
        try:
            payload = json.loads(str(raw or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        normalized: dict[str, dict[str, object]] = {}
        for key, value in payload.items():
            if isinstance(key, str) and isinstance(value, dict):
                normalized[key] = dict(value)
        return normalized

    def save_task_saved_views(self, views: dict[str, dict[str, object]]) -> None:
        payload: dict[str, dict[str, object]] = {}
        for key, value in (views or {}).items():
            if isinstance(key, str) and isinstance(value, dict):
                payload[key] = dict(value)
        self._settings.setValue(
            self._settings_key(),
            json.dumps(payload, sort_keys=True),
        )
        self._settings.sync()


__all__ = ["ProjectManagementTaskViewStore"]
