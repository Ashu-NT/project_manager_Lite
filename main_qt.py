# main_qt.py
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon
from infra.resource import resource_path

from infra.db.base import SessionLocal
from infra.logging_config import setup_logging
from infra.services import build_service_dict

from ui.main_window import MainWindow


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
    icon_path = resource_path("assets/icons/app.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    # 1) Global font (Segoe UI is modern & native on Windows, use Roboto/Noto on Linux etc.)
    app.setFont(QFont("Segoe UI", 9))

    # 2) Global stylesheet (QSS)
    from ui.styles.theme import apply_app_style
    apply_app_style(app)
   
    services = build_services()
    window = MainWindow(services)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
