"""Platform QML presenters."""
from src.ui_qml.platform.presenters.admin_presenter import PlatformAdminWorkspacePresenter
from src.ui_qml.platform.presenters.control_queue_presenter import PlatformControlQueuePresenter
from src.ui_qml.platform.presenters.control_presenter import PlatformControlWorkspacePresenter
from src.ui_qml.platform.presenters.runtime_presenter import PlatformRuntimePresenter
from src.ui_qml.platform.presenters.settings_catalog_presenter import PlatformSettingsCatalogPresenter
from src.ui_qml.platform.presenters.settings_presenter import PlatformSettingsWorkspacePresenter

__all__ = [
    "PlatformAdminWorkspacePresenter",
    "PlatformControlQueuePresenter",
    "PlatformControlWorkspacePresenter",
    "PlatformRuntimePresenter",
    "PlatformSettingsCatalogPresenter",
    "PlatformSettingsWorkspacePresenter",
]
