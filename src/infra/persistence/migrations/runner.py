from __future__ import annotations

from pathlib import Path
import sys


def _app_dir() -> Path:
    """
    Returns the directory where the running app lives.
    - For PyInstaller onefile builds, prefer sys._MEIPASS (temporary extraction dir).
    - For PyInstaller onedir builds, use the folder containing the .exe.
    - In dev: return the project root (`src/infra/persistence/migrations` -> root).
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[4]


def _migration_candidates(app_dir: Path) -> list[Path]:
    package_location = Path(__file__).resolve().parent
    candidates = [
        package_location,
        app_dir / "src" / "infra" / "persistence" / "migrations",
        app_dir / "_internal" / "src" / "infra" / "persistence" / "migrations",
        app_dir / "ProjectManagerLite" / "src" / "infra" / "persistence" / "migrations",
    ]

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen:
            unique_candidates.append(resolved)
            seen.add(resolved)
    return unique_candidates


def run_migrations(db_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    app_dir = _app_dir()
    candidates = _migration_candidates(app_dir)

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
