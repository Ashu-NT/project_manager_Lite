# main_qt.py
import os
from src.ui_qml.shell.app import main

if __name__ == "__main__":
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    raise SystemExit(main())
