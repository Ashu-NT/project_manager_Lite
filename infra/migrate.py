from pathlib import Path
import sys
from alembic import command
from alembic.config import Config


def _app_dir() -> Path:
    """
    Returns the directory where the running app lives.
    - For PyInstaller onefile builds, prefer sys._MEIPASS (temporary extraction dir).
    - For PyInstaller onedir builds, use the folder containing the .exe.
    - In dev: return the project root (infra -> project root).
    """
    if getattr(sys, "frozen", False):
        # Onefile build (sys._MEIPASS) contains unpacked data resources
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        # Fallback to exe parent (onedir)
        return Path(sys.executable).resolve().parent
    # dev fallback: infra/migrate.py -> infra -> project root
    return Path(__file__).resolve().parents[1]


def run_migrations(db_url: str) -> None:
    app_dir = _app_dir()

    # Primary expected location: <app_dir>/migration
    candidates = [app_dir / "migration"]

    # Common packaging layout: some packagers place resources under an '_internal' folder
    candidates.append(app_dir / "_internal" / "migration")

    # Also consider a nested folder named after the app (e.g., dist/ProjectManagerLite/migration)
    candidates.append(app_dir / "ProjectManagerLite" / "migration")

    script_location = None
    alembic_ini = None
    for c in candidates:
        if c.exists():
            script_location = c
            alembic_ini = c / "alembic.ini"
            break

    if script_location is None:
        raise RuntimeError(
            "Alembic script_location missing. Tried the following locations: " + 
            ", ".join(str(p) for p in candidates)
        )

    if not alembic_ini.exists():
        raise RuntimeError(f"Alembic config missing: {alembic_ini}")

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(script_location))
    cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(cfg, "head")