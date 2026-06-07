from __future__ import annotations

import logging
from pathlib import Path
import sys
from threading import Timer
from time import perf_counter


logger = logging.getLogger(__name__)


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
    from alembic.script import ScriptDirectory

    started = perf_counter()
    app_dir = _app_dir()
    candidates = _migration_candidates(app_dir)
    logger.info(
        "Alembic migration discovery begin app_dir=%s candidate_count=%s candidates=%s",
        app_dir,
        len(candidates),
        [str(candidate) for candidate in candidates],
    )

    script_location = None
    alembic_ini = None
    for c in candidates:
        if c.exists():
            script_location = c
            alembic_ini = c / "alembic.ini"
            break

    if script_location is None:
        logger.critical(
            "Alembic script_location missing candidates=%s",
            [str(path) for path in candidates],
        )
        raise RuntimeError(
            "Alembic script_location missing. Tried the following locations: " + 
            ", ".join(str(p) for p in candidates)
        )

    if not alembic_ini.exists():
        logger.critical("Alembic config missing path=%s", alembic_ini)
        raise RuntimeError(f"Alembic config missing: {alembic_ini}")

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(script_location))
    cfg.set_main_option("sqlalchemy.url", db_url)
    slow_watchdog = Timer(
        5.0,
        lambda: logger.warning(
            "Alembic migration upgrade still running duration_ms=%.1f script_location=%s",
            (perf_counter() - started) * 1000,
            script_location,
        ),
    )
    slow_watchdog.daemon = True
    slow_watchdog.start()
    try:
        script = ScriptDirectory.from_config(cfg)
        heads = script.get_heads()
        logger.info(
            "Alembic migration upgrade begin script_location=%s config=%s heads=%s db_url=%s",
            script_location,
            alembic_ini,
            heads,
            db_url,
        )
        command.upgrade(cfg, "head")
    except Exception:
        logger.exception(
            "Alembic migration upgrade failed script_location=%s duration_ms=%.1f",
            script_location,
            (perf_counter() - started) * 1000,
        )
        raise
    finally:
        slow_watchdog.cancel()
    logger.info(
        "Alembic migration upgrade complete duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
