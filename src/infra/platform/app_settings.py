from __future__ import annotations

import json
from math import isfinite

from PySide6.QtCore import QByteArray, QSettings

from src.infra.platform.update import default_update_manifest_source


class AppSettingsStore:
    """Shared QSettings adapter for desktop runtime and support preferences."""

    ORG_NAME = "TECHASH"
    APP_NAME = "ProjectManagerLite"
    _UNSCOPED_TENANT_SEGMENT = "__no_organization__"

    _KEY_THEME_MODE = "ui/theme_mode"
    _KEY_DENSITY_MODE = "ui/density_mode"
    _KEY_TAB_INDEX = "ui/current_tab_index"
    _KEY_GEOMETRY = "ui/platform/shell/main_window_geometry"
    _KEY_GOVERNANCE_MODE = "governance/mode"
    _KEY_UPDATE_CHANNEL = "updates/channel"
    _KEY_UPDATE_AUTO_CHECK = "updates/auto_check"
    _KEY_UPDATE_MANIFEST_URL = "updates/manifest_url"
    _KEY_DASHBOARD_LAYOUT = "dashboard/layout"
    _KEY_TABLE_COLUMN_STATE = "ui/table_column_state"
    _KEY_GANTT_VIEW_STATE = "ui/project_management/gantt/view_state"
    _KEY_GANTT_BASELINE_STATE = "ui/project_management/gantt/project_baselines"

    _GANTT_VIEW_MODES = {"grid", "timeline", "split"}
    _GANTT_TIMESCALES = {"day", "week", "month", "quarter"}
    _GANTT_ZOOM_LEVELS = (0.75, 0.875, 1.0, 1.25, 1.5)
    _GANTT_MIN_SPLIT_RATIO = 0.44
    _GANTT_MAX_SPLIT_RATIO = 0.62

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings(self.ORG_NAME, self.APP_NAME)

    @staticmethod
    def _tenant_key(base_key: str, organization_id: str | None = None) -> str:
        normalized = str(organization_id or "").strip()
        if not normalized:
            normalized = AppSettingsStore._UNSCOPED_TENANT_SEGMENT
        return f"tenant/{normalized}/{base_key}"

    def load_theme_mode(self, default_mode: str = "light") -> str:
        default = (default_mode or "light").strip().lower()
        if default not in {"light", "dark"}:
            default = "light"
        raw = str(self._settings.value(self._KEY_THEME_MODE, default)).strip().lower()
        return raw if raw in {"light", "dark"} else default

    def save_theme_mode(self, mode: str) -> None:
        normalized = (mode or "light").strip().lower()
        self._settings.setValue(self._KEY_THEME_MODE, "dark" if normalized == "dark" else "light")
        self._settings.sync()

    def load_density_mode(self, default_mode: str = "compact") -> str:
        default = (default_mode or "compact").strip().lower()
        if default not in {"compact", "comfortable", "spacious"}:
            default = "compact"
        raw = str(self._settings.value(self._KEY_DENSITY_MODE, default)).strip().lower()
        return raw if raw in {"compact", "comfortable", "spacious"} else default

    def save_density_mode(self, mode: str) -> None:
        normalized = (mode or "compact").strip().lower()
        if normalized not in {"compact", "comfortable", "spacious"}:
            normalized = "compact"
        self._settings.setValue(self._KEY_DENSITY_MODE, normalized)
        self._settings.sync()

    def load_governance_mode(self, default_mode: str = "off") -> str:
        default = (default_mode or "off").strip().lower()
        if default not in {"off", "required"}:
            default = "off"
        raw = str(self._settings.value(self._KEY_GOVERNANCE_MODE, default)).strip().lower()
        return raw if raw in {"off", "required"} else default

    def save_governance_mode(self, mode: str) -> None:
        normalized = (mode or "off").strip().lower()
        self._settings.setValue(self._KEY_GOVERNANCE_MODE, "required" if normalized == "required" else "off")
        self._settings.sync()

    def load_update_channel(self, default_channel: str = "stable") -> str:
        default = (default_channel or "stable").strip().lower()
        if default not in {"stable", "beta"}:
            default = "stable"
        raw = str(self._settings.value(self._KEY_UPDATE_CHANNEL, default)).strip().lower()
        return raw if raw in {"stable", "beta"} else default

    def save_update_channel(self, channel: str) -> None:
        normalized = (channel or "stable").strip().lower()
        self._settings.setValue(self._KEY_UPDATE_CHANNEL, "beta" if normalized == "beta" else "stable")
        self._settings.sync()

    def load_update_auto_check(self, default_enabled: bool = False) -> bool:
        raw = self._settings.value(self._KEY_UPDATE_AUTO_CHECK, default_enabled)
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    def save_update_auto_check(self, enabled: bool) -> None:
        self._settings.setValue(self._KEY_UPDATE_AUTO_CHECK, bool(enabled))
        self._settings.sync()

    def load_update_manifest_url(self, default_url: str = "") -> str:
        fallback = (default_url or default_update_manifest_source()).strip()
        raw = self._settings.value(self._KEY_UPDATE_MANIFEST_URL, fallback)
        value = str(raw or "").strip()
        return value or fallback

    def save_update_manifest_url(self, url: str) -> None:
        self._settings.setValue(self._KEY_UPDATE_MANIFEST_URL, (url or "").strip())
        self._settings.sync()

    def load_update_manifest_source(self, default_source: str = "") -> str:
        return self.load_update_manifest_url(default_source)

    def save_update_manifest_source(self, source: str) -> None:
        self.save_update_manifest_url(source)

    def load_tab_index(self, default_index: int = 0) -> int:
        raw = self._settings.value(self._KEY_TAB_INDEX, default_index)
        try:
            idx = int(raw)
        except (TypeError, ValueError):
            idx = default_index
        return max(0, idx)

    def save_tab_index(self, index: int) -> None:
        self._settings.setValue(self._KEY_TAB_INDEX, max(0, int(index)))
        self._settings.sync()

    def load_geometry(self) -> QByteArray | None:
        raw = self._settings.value(self._KEY_GEOMETRY)
        if isinstance(raw, QByteArray) and not raw.isEmpty():
            return raw
        return None

    def save_geometry(self, geometry: QByteArray | None) -> None:
        if geometry is not None and not geometry.isEmpty():
            self._settings.setValue(self._KEY_GEOMETRY, geometry)
            self._settings.sync()

    def load_dashboard_layout(self, *, organization_id: str | None = None) -> dict[str, object]:
        raw = self._settings.value(self._tenant_key(self._KEY_DASHBOARD_LAYOUT, organization_id), "{}")
        try:
            payload = json.loads(str(raw or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return dict(payload) if isinstance(payload, dict) else {}

    def save_dashboard_layout(self, layout: dict[str, object], *, organization_id: str | None = None) -> None:
        payload = dict(layout) if isinstance(layout, dict) else {}
        self._settings.setValue(
            self._tenant_key(self._KEY_DASHBOARD_LAYOUT, organization_id),
            json.dumps(payload, sort_keys=True),
        )
        self._settings.sync()

    def load_table_column_state(self, table_id: str, *, organization_id: str | None = None) -> dict[str, object]:
        all_states_raw = self._settings.value(
            self._tenant_key(self._KEY_TABLE_COLUMN_STATE, organization_id),
            "{}",
        )
        try:
            all_states = json.loads(str(all_states_raw or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        if not isinstance(all_states, dict):
            return {}
        state = all_states.get(str(table_id), {})
        return dict(state) if isinstance(state, dict) else {}

    def save_table_column_state(
        self,
        table_id: str,
        state: dict[str, object],
        *,
        organization_id: str | None = None,
    ) -> None:
        table_state_key = self._tenant_key(self._KEY_TABLE_COLUMN_STATE, organization_id)
        all_states_raw = self._settings.value(table_state_key, "{}")
        try:
            all_states = json.loads(str(all_states_raw or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            all_states = {}
        if not isinstance(all_states, dict):
            all_states = {}
        all_states[str(table_id)] = dict(state) if isinstance(state, dict) else {}
        self._settings.setValue(table_state_key, json.dumps(all_states, sort_keys=True))
        self._settings.sync()

    def load_gantt_view_state(
        self,
        *,
        organization_id: str | None = None,
    ) -> dict[str, object]:
        key = self._tenant_key(self._KEY_GANTT_VIEW_STATE, organization_id)
        raw = self._settings.value(key, "{}")
        try:
            payload = json.loads(str(raw or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            payload = {}
        return self._normalize_gantt_view_state(payload)

    def save_gantt_view_state(
        self,
        state: dict[str, object],
        *,
        organization_id: str | None = None,
    ) -> None:
        payload = self._normalize_gantt_view_state(state)
        self._settings.setValue(
            self._tenant_key(self._KEY_GANTT_VIEW_STATE, organization_id),
            json.dumps(payload, sort_keys=True),
        )
        self._settings.sync()

    def load_gantt_project_baseline(
        self,
        project_id: str,
        *,
        organization_id: str | None = None,
    ) -> str:
        normalized_project_id = str(project_id or "").strip()
        if not normalized_project_id:
            return ""
        states = self._load_gantt_project_baselines(organization_id=organization_id)
        return str(states.get(normalized_project_id) or "").strip()

    def save_gantt_project_baseline(
        self,
        project_id: str,
        baseline_id: str,
        *,
        organization_id: str | None = None,
    ) -> None:
        normalized_project_id = str(project_id or "").strip()
        if not normalized_project_id:
            return
        states = self._load_gantt_project_baselines(organization_id=organization_id)
        normalized_baseline_id = str(baseline_id or "").strip()
        if normalized_baseline_id:
            states[normalized_project_id] = normalized_baseline_id
        else:
            states.pop(normalized_project_id, None)
        self._settings.setValue(
            self._tenant_key(self._KEY_GANTT_BASELINE_STATE, organization_id),
            json.dumps(states, sort_keys=True),
        )
        self._settings.sync()

    def _load_gantt_project_baselines(
        self,
        *,
        organization_id: str | None,
    ) -> dict[str, str]:
        raw = self._settings.value(
            self._tenant_key(self._KEY_GANTT_BASELINE_STATE, organization_id),
            "{}",
        )
        try:
            payload = json.loads(str(raw or "{}"))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return {
            str(project_id).strip(): str(baseline_id).strip()
            for project_id, baseline_id in payload.items()
            if str(project_id).strip() and str(baseline_id or "").strip()
        }

    @classmethod
    def _normalize_gantt_view_state(cls, payload: object) -> dict[str, object]:
        source = payload if isinstance(payload, dict) else {}
        requested_view_mode = str(source.get("requestedViewMode") or "").strip().lower()
        if requested_view_mode not in cls._GANTT_VIEW_MODES:
            requested_view_mode = "split"
        timescale = str(source.get("timescale") or "").strip().lower()
        if timescale not in cls._GANTT_TIMESCALES:
            timescale = "week"

        raw_ratio = source.get("splitRatio")
        split_ratio = 0.5
        if isinstance(raw_ratio, (int, float)) and not isinstance(raw_ratio, bool):
            candidate = float(raw_ratio)
            if isfinite(candidate):
                split_ratio = min(
                    cls._GANTT_MAX_SPLIT_RATIO,
                    max(cls._GANTT_MIN_SPLIT_RATIO, candidate),
                )

        raw_zoom = source.get("zoomMultiplier")
        zoom_multiplier = 1.0
        if isinstance(raw_zoom, (int, float)) and not isinstance(raw_zoom, bool):
            candidate = float(raw_zoom)
            if isfinite(candidate):
                zoom_multiplier = next(
                    (
                        level
                        for level in cls._GANTT_ZOOM_LEVELS
                        if abs(level - candidate) < 0.000_001
                    ),
                    1.0,
                )

        dependency_lines = source.get("dependencyLinesEnabled")
        if not isinstance(dependency_lines, bool):
            dependency_lines = True
        highlight_critical = source.get("highlightCriticalTasks")
        if not isinstance(highlight_critical, bool):
            highlight_critical = True

        return {
            "version": 1,
            "requestedViewMode": requested_view_mode,
            "splitRatio": split_ratio,
            "timescale": timescale,
            "zoomMultiplier": zoom_multiplier,
            "dependencyLinesEnabled": dependency_lines,
            "highlightCriticalTasks": highlight_critical,
        }


__all__ = ["AppSettingsStore"]
