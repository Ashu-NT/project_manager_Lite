# main_qt.py
import sys
import os
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtGui import QFont, QIcon
from infra.resource import resource_path

from infra.db.base import SessionLocal, get_db_url
from infra.logging_config import setup_logging
from infra.services import build_service_dict

from ui.auth import LoginDialog
from ui.main_window import MainWindow
from ui.settings import MainWindowSettingsStore


def build_services():
    # same DB as CLI
    from infra.migrate import run_migrations
    run_migrations(db_url=get_db_url())
    #Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    return build_service_dict(session)


def main():
    setup_logging()

    app = QApplication(sys.argv)
    settings_store = MainWindowSettingsStore()
    startup_theme = settings_store.load_theme_mode(default_mode=os.getenv("PM_THEME", "light"))
    startup_governance = settings_store.load_governance_mode(
        default_mode=os.getenv("PM_GOVERNANCE_MODE", "off")
    )
    os.environ["PM_THEME"] = startup_theme
    os.environ["PM_GOVERNANCE_MODE"] = startup_governance
    icon_path = resource_path("assets/icons/app.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    # 1) Global font (Segoe UI is modern & native on Windows, use Roboto/Noto on Linux etc.)
    app.setFont(QFont("Segoe UI", 9))

    # 2) Global stylesheet (QSS)
    from ui.styles.theme import apply_app_style
    apply_app_style(app, mode=startup_theme)
   
    services = build_services()
    if os.getenv("PM_SKIP_LOGIN", "0").strip() not in {"1", "true", "TRUE"}:
        login = LoginDialog(
            auth_service=services["auth_service"],
            user_session=services["user_session"],
        )
        if login.exec() != QDialog.Accepted:
            return
    window = MainWindow(services)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
