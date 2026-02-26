# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path

project_root = Path(SPECPATH)

hidden = (
    collect_submodules("infra")
    + collect_submodules("core")
    + collect_submodules("ui")
)

a = Analysis(
    ['main_qt.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "assets"), "assets"),
        (str(project_root / "migration"), "migration"),
        (str(project_root / "infra" / "app_version.txt"), "infra"),
    ],
    # Ensure stdlib logging.config is included for Alembic env imports
    hiddenimports=hidden + ["logging.config"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ProjectManagerLite',
    icon=str(project_root / 'assets' / 'icons' / 'app.ico'),
    debug=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name='ProjectManagerLite',
)
