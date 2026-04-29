from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SupportSettingsDto:
    update_channel: str
    update_auto_check: bool
    update_manifest_source: str
    theme_mode: str
    governance_mode: str
    app_version: str
    support_email: str


@dataclass(frozen=True)
class SupportSettingsUpdateCommand:
    update_channel: str
    update_auto_check: bool
    update_manifest_source: str


@dataclass(frozen=True)
class SupportUpdateStatusDto:
    status_label: str
    summary: str
    current_version: str
    latest_version: str
    channel: str
    update_available: bool
    can_open_download: bool
    download_url: str
    notes: str
    sha256: str


@dataclass(frozen=True)
class SupportEventDto:
    timestamp_utc: str
    event_type: str
    level: str
    trace_id: str
    message: str
    details_summary: str


@dataclass(frozen=True)
class SupportPathsDto:
    data_directory_path: str
    data_directory_url: str
    logs_directory_path: str
    logs_directory_url: str
    incidents_directory_path: str
    incidents_directory_url: str
    events_file_path: str
    events_file_url: str


@dataclass(frozen=True)
class SupportBundleDto:
    output_path: str
    output_url: str
    files_added: int
    warnings: tuple[str, ...]
    support_email: str = ""


__all__ = [
    "SupportBundleDto",
    "SupportEventDto",
    "SupportPathsDto",
    "SupportSettingsDto",
    "SupportSettingsUpdateCommand",
    "SupportUpdateStatusDto",
]
