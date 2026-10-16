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
