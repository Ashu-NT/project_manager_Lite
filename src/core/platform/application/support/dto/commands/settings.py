from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SupportSettingsUpdateCommand:
    update_channel: str
    update_auto_check: bool
    update_manifest_source: str
