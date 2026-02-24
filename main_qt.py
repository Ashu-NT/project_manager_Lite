# main_qt.py
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from infra.resource import resource_path

from infra.db.base import SessionLocal
from infra.logging_config import setup_logging
from infra.services import build_service_dict

from ui.main_window import MainWindow
from ui.settings import MainWindowSettingsStore


def build_services():
    # same DB as CLI
    from infra.migrate import run_migrations
    from infra.path import default_db_path
    from pathlib import Path

    db_url:Path = default_db_path()

    run_migrations(
        db_url=db_url.as_posix()
    )
    #Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    return build_service_dict(session)


def main():
    setup_logging()

    app = QApplication(sys.argv)
    settings_store = MainWindowSettingsStore()
    startup_theme = settings_store.load_theme_mode(default_mode=os.getenv("PM_THEME", "light"))
    os.environ["PM_THEME"] = startup_theme
    icon_path = resource_path("assets/icons/app.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    # 1) Global font (Segoe UI is modern & native on Windows, use Roboto/Noto on Linux etc.)
    app.setFont(QFont("Segoe UI", 9))

    # 2) Global stylesheet (QSS)
    from ui.styles.theme import apply_app_style
    apply_app_style(app, mode=startup_theme)
   
    services = build_services()
    window = MainWindow(services)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
