from src.core.platform.application.support.dto.responses.settings import (
    SupportSettingsDto,
)


def settings_response(*, update_channel: str, update_auto_check: bool, update_manifest_source: str, theme_mode: str, governance_mode: str, app_version: str, support_email: str) -> SupportSettingsDto:
    return SupportSettingsDto(update_channel=update_channel, update_auto_check=update_auto_check, update_manifest_source=update_manifest_source, theme_mode=theme_mode, governance_mode=governance_mode, app_version=app_version, support_email=support_email)
