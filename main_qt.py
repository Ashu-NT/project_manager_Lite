# main_qt.py
import os

from src.infra.platform.env_loader import load_env_file

load_env_file()

import resources.resources_rc  # noqa: E402,F401
from src.ui_qml.shell.app import main  # noqa: E402

if __name__ == "__main__":
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    raise SystemExit(main())
