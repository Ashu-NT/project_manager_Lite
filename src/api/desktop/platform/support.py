from __future__ import annotations

import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from PySide6.QtCore import QSettings

from src.api.desktop.platform.models import (
    DesktopApiError,
    DesktopApiResult,
    SupportBundleDto,
    SupportEventDto,
    SupportPathsDto,
    SupportSettingsDto,
    SupportSettingsUpdateCommand,
    SupportUpdateStatusDto,
)
from src.infra.platform.diagnostics import build_diagnostics_bundle
from src.infra.platform.operational_support import OperationalSupport, bind_trace_id, get_operational_support
from src.infra.platform.path import user_data_dir
from src.infra.platform.update import check_for_updates, default_update_manifest_source
from src.infra.platform.version import get_app_version

_DEFAULT_SUPPORT_EMAIL = "tech_ash_673@info.tech"


class _SupportSettingsStore:
    ORG_NAME = "TECHASH"
    APP_NAME = "ProjectManagerLite"

    _KEY_THEME_MODE = "ui/theme_mode"
    _KEY_GOVERNANCE_MODE = "governance/mode"
    _KEY_UPDATE_CHANNEL = "updates/channel"
    _KEY_UPDATE_AUTO_CHECK = "updates/auto_check"
    _KEY_UPDATE_MANIFEST_URL = "updates/manifest_url"

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings(self.ORG_NAME, self.APP_NAME)

    def load_theme_mode(self, default_mode: str = "light") -> str:
        default = (default_mode or "light").strip().lower()
        if default not in {"light", "dark"}:
            default = "light"
        raw = str(self._settings.value(self._KEY_THEME_MODE, default)).strip().lower()
        return raw if raw in {"light", "dark"} else default

    def load_governance_mode(self, default_mode: str = "off") -> str:
        default = (default_mode or "off").strip().lower()
        if default not in {"off", "required"}:
            default = "off"
        raw = str(self._settings.value(self._KEY_GOVERNANCE_MODE, default)).strip().lower()
        return raw if raw in {"off", "required"} else default

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

    def load_update_manifest_source(self, default_source: str = "") -> str:
        fallback = (default_source or default_update_manifest_source()).strip()
        raw = self._settings.value(self._KEY_UPDATE_MANIFEST_URL, fallback)
        value = str(raw or "").strip()
        return value or fallback

    def save_update_manifest_source(self, source: str) -> None:
        self._settings.setValue(self._KEY_UPDATE_MANIFEST_URL, (source or "").strip())
        self._settings.sync()


class PlatformSupportDesktopApi:
    """Desktop-facing adapter for support settings, update checks, and diagnostics flows."""

    def __init__(
        self,
        *,
        settings: QSettings | None = None,
        operational_support: OperationalSupport | None = None,
    ) -> None:
        self._settings_store = _SupportSettingsStore(settings)
        self._operational_support = operational_support or get_operational_support()

    def new_incident_id(self) -> str:
        return self._operational_support.new_incident_id()

    def load_settings(self) -> DesktopApiResult[SupportSettingsDto]:
        return DesktopApiResult(ok=True, data=self._build_settings_dto())

    def get_paths(self) -> DesktopApiResult[SupportPathsDto]:
        try:
            return DesktopApiResult(ok=True, data=self._build_paths_dto())
        except Exception as exc:  # noqa: BLE001
            return self._runtime_error(exc, code="support_paths_unavailable")

    def save_settings(
        self,
        command: SupportSettingsUpdateCommand,
        *,
        trace_id: str | None = None,
    ) -> DesktopApiResult[SupportSettingsDto]:
        try:
            self._persist_settings(command)
            self._emit_event(
                trace_id=trace_id,
                event_type="support.update.settings_saved",
                message="Update settings saved.",
                data={
                    "channel": command.update_channel,
                    "auto_check": command.update_auto_check,
                    "manifest_source": command.update_manifest_source,
                },
            )
            return DesktopApiResult(ok=True, data=self._build_settings_dto())
        except Exception as exc:  # noqa: BLE001
            return self._runtime_error(exc, code="support_settings_save_failed")

    def check_for_updates(
        self,
        command: SupportSettingsUpdateCommand,
        *,
        trace_id: str | None = None,
    ) -> DesktopApiResult[SupportUpdateStatusDto]:
        try:
            self._persist_settings(command)
            normalized_trace = (trace_id or self.new_incident_id()).strip()
            manifest_source = self._settings_store.load_update_manifest_source(
                default_source=default_update_manifest_source()
            )
            channel = self._settings_store.load_update_channel(default_channel="stable")
            self._emit_event(
                trace_id=normalized_trace,
                event_type="support.update.check_started",
                message="Started update check.",
                data={"channel": channel, "manifest_source": manifest_source},
            )
            with bind_trace_id(normalized_trace):
                result = check_for_updates(
                    current_version=get_app_version(),
                    channel=channel,
                    manifest_source=manifest_source,
                )
            dto = self._serialize_update_status(result)
            if dto.status_label == "Check Failed":
                self._emit_event(
                    trace_id=normalized_trace,
                    event_type="support.update.check_failed",
                    level="ERROR",
                    message=dto.summary,
                    data={"channel": dto.channel, "manifest_source": manifest_source},
                )
            elif dto.update_available:
                self._emit_event(
                    trace_id=normalized_trace,
                    event_type="support.update.available",
                    message=dto.summary,
                    data={
                        "channel": dto.channel,
                        "version": dto.latest_version,
                        "download_url": dto.download_url,
                        "sha256": dto.sha256,
                    },
                )
            else:
                self._emit_event(
                    trace_id=normalized_trace,
                    event_type="support.update.no_change",
                    message=dto.summary,
                    data={"channel": dto.channel},
                )
            return DesktopApiResult(ok=True, data=dto)
        except Exception as exc:  # noqa: BLE001
            return self._runtime_error(exc, code="support_update_check_failed")

    def list_activity(
        self,
        *,
        trace_id: str | None = None,
        limit: int = 12,
    ) -> DesktopApiResult[tuple[SupportEventDto, ...]]:
        try:
            events = self._operational_support.read_events(trace_id=trace_id)
            rows = tuple(
                self._serialize_event(row)
                for row in reversed(events[-max(1, int(limit)):])
            )
            return DesktopApiResult(ok=True, data=rows)
        except Exception as exc:  # noqa: BLE001
            return self._runtime_error(exc, code="support_activity_unavailable")

    def export_diagnostics(self, *, incident_id: str) -> DesktopApiResult[SupportBundleDto]:
        normalized_trace = (incident_id or self.new_incident_id()).strip()
        try:
            out_dir = user_data_dir()
            out_dir.mkdir(parents=True, exist_ok=True)
            output_path = out_dir / f"pm_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            self._emit_event(
                trace_id=normalized_trace,
                event_type="support.diagnostics.export_started",
                message="Started diagnostics export.",
                data={"output_path": str(output_path)},
            )
            with bind_trace_id(normalized_trace):
                result = build_diagnostics_bundle(
                    output_path=output_path,
                    settings_snapshot=self._settings_snapshot(),
                    include_db_copy=True,
                    incident_id=normalized_trace,
                )
            self._emit_event(
                trace_id=normalized_trace,
                event_type="support.diagnostics.exported",
                message="Diagnostics bundle exported.",
                data={
                    "output_path": str(result.output_path),
                    "files_added": result.files_added,
                    "warnings": list(result.warnings),
                },
            )
            return DesktopApiResult(ok=True, data=self._serialize_bundle(result.output_path, result.files_added, result.warnings))
        except Exception as exc:  # noqa: BLE001
            return self._runtime_error(exc, code="support_diagnostics_export_failed")

    def create_incident_report(self, *, incident_id: str) -> DesktopApiResult[SupportBundleDto]:
        normalized_trace = (incident_id or self.new_incident_id()).strip()
        support_email = self._support_email()
        try:
            incidents_dir = user_data_dir() / "incidents"
            incidents_dir.mkdir(parents=True, exist_ok=True)
            output_path = incidents_dir / (
                f"pm_incident_{normalized_trace}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            )
            self._emit_event(
                trace_id=normalized_trace,
                event_type="support.incident.report_started",
                message="Started incident report packaging.",
                data={"output_path": str(output_path), "support_email": support_email},
            )
            with bind_trace_id(normalized_trace):
                result = build_diagnostics_bundle(
                    output_path=output_path,
                    settings_snapshot=self._settings_snapshot(),
                    include_db_copy=True,
                    incident_id=normalized_trace,
                )
            self._emit_event(
                trace_id=normalized_trace,
                event_type="support.incident.report_ready",
                message="Incident report package is ready.",
                data={
                    "output_path": str(result.output_path),
                    "support_email": support_email,
                    "files_added": result.files_added,
                },
            )
            return DesktopApiResult(
                ok=True,
                data=self._serialize_bundle(
                    result.output_path,
                    result.files_added,
                    result.warnings,
                    support_email=support_email,
                ),
            )
        except Exception as exc:  # noqa: BLE001
            return self._runtime_error(exc, code="support_incident_report_failed")

    def _build_settings_dto(self) -> SupportSettingsDto:
        return SupportSettingsDto(
            update_channel=self._settings_store.load_update_channel(default_channel="stable"),
            update_auto_check=self._settings_store.load_update_auto_check(default_enabled=False),
            update_manifest_source=self._settings_store.load_update_manifest_source(
                default_source=default_update_manifest_source()
            ),
            theme_mode=self._settings_store.load_theme_mode(default_mode="light"),
            governance_mode=self._settings_store.load_governance_mode(default_mode="off"),
            app_version=get_app_version(),
            support_email=self._support_email(),
        )

    def _build_paths_dto(self) -> SupportPathsDto:
        data_dir = user_data_dir()
        logs_dir = data_dir / "logs"
        incidents_dir = data_dir / "incidents"
        logs_dir.mkdir(parents=True, exist_ok=True)
        incidents_dir.mkdir(parents=True, exist_ok=True)
        events_path = self._operational_support.events_path
        return SupportPathsDto(
            data_directory_path=str(data_dir),
            data_directory_url=data_dir.resolve().as_uri(),
            logs_directory_path=str(logs_dir),
            logs_directory_url=logs_dir.resolve().as_uri(),
            incidents_directory_path=str(incidents_dir),
            incidents_directory_url=incidents_dir.resolve().as_uri(),
            events_file_path=str(events_path),
            events_file_url=events_path.resolve().as_uri(),
        )

    def _persist_settings(self, command: SupportSettingsUpdateCommand) -> None:
        self._settings_store.save_update_channel(command.update_channel)
        self._settings_store.save_update_auto_check(command.update_auto_check)
        manifest_source = (command.update_manifest_source or "").strip() or default_update_manifest_source()
        self._settings_store.save_update_manifest_source(manifest_source)

    def _settings_snapshot(self) -> dict[str, object]:
        settings_dto = self._build_settings_dto()
        snapshot = asdict(settings_dto)
        snapshot["support_email"] = settings_dto.support_email
        return snapshot

    @staticmethod
    def _serialize_update_status(result) -> SupportUpdateStatusDto:
        latest = result.latest
        summary = str(result.message or "").strip()
        if summary.lower().startswith("update check failed:"):
            status_label = "Check Failed"
        elif result.update_available and latest is not None:
            status_label = "Update Available"
        else:
            status_label = "Up To Date"
        return SupportUpdateStatusDto(
            status_label=status_label,
            summary=summary,
            current_version=str(result.current_version or ""),
            latest_version=str(latest.version if latest is not None else ""),
            channel=str(result.channel or ""),
            update_available=bool(result.update_available),
            can_open_download=bool(latest is not None and latest.url),
            download_url=str(latest.url if latest is not None and latest.url else ""),
            notes=str(latest.notes if latest is not None and latest.notes else ""),
            sha256=str(latest.sha256 if latest is not None and latest.sha256 else ""),
        )

    @staticmethod
    def _serialize_event(payload: Mapping[str, Any]) -> SupportEventDto:
        details = payload.get("data")
        return SupportEventDto(
            timestamp_utc=str(payload.get("timestamp_utc") or ""),
            event_type=str(payload.get("event_type") or ""),
            level=str(payload.get("level") or "INFO"),
            trace_id=str(payload.get("trace_id") or ""),
            message=str(payload.get("message") or ""),
            details_summary=PlatformSupportDesktopApi._summarize_event_details(details),
        )

    @staticmethod
    def _serialize_bundle(
        output_path: Path,
        files_added: int,
        warnings: tuple[str, ...],
        *,
        support_email: str = "",
    ) -> SupportBundleDto:
        return SupportBundleDto(
            output_path=str(output_path),
            output_url=output_path.resolve().as_uri(),
            files_added=files_added,
            warnings=tuple(warnings),
            support_email=support_email,
        )

    @staticmethod
    def _summarize_event_details(details: Any) -> str:
        if not isinstance(details, Mapping) or not details:
            return ""
        parts: list[str] = []
        for key in sorted(details.keys()):
            value = details.get(key)
            if isinstance(value, list):
                value_text = ", ".join(str(item) for item in value[:3])
                if len(value) > 3:
                    value_text = f"{value_text}, +{len(value) - 3} more"
            else:
                value_text = str(value)
            parts.append(f"{key}: {value_text}")
        return " | ".join(parts[:3])

    @staticmethod
    def _support_email() -> str:
        override = (os.getenv("PM_SUPPORT_EMAIL") or "").strip()
        return override or _DEFAULT_SUPPORT_EMAIL

    def _emit_event(
        self,
        *,
        trace_id: str | None,
        event_type: str,
        message: str,
        level: str = "INFO",
        data: Mapping[str, object] | None = None,
    ) -> None:
        self._operational_support.emit_event(
            event_type=event_type,
            message=message,
            level=level,
            trace_id=(trace_id or self.new_incident_id()).strip(),
            data=data,
        )

    @staticmethod
    def _runtime_error(exc: Exception, *, code: str) -> DesktopApiResult[object]:
        return DesktopApiResult(
            ok=False,
            error=DesktopApiError(
                code=code,
                message=str(exc),
                category="runtime",
            ),
        )


__all__ = ["PlatformSupportDesktopApi"]
