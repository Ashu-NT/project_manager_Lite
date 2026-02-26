from __future__ import annotations

import json
import platform
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from infra.path import default_db_path, user_data_dir
from infra.version import get_app_version


@dataclass(frozen=True)
class DiagnosticsBundleResult:
    output_path: Path
    files_added: int
    warnings: tuple[str, ...]


def build_diagnostics_bundle(
    output_path: str | Path,
    *,
    settings_snapshot: dict[str, object] | None = None,
    include_db_copy: bool = True,
) -> DiagnosticsBundleResult:
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []

    with TemporaryDirectory(prefix="pm_diag_") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        logs_dir = user_data_dir() / "logs"
        db_path = default_db_path()

        metadata = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "app_version": get_app_version(),
            "python_version": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "db_path": str(db_path),
            "logs_dir": str(logs_dir),
            "settings": settings_snapshot or {},
        }
        (temp_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        copied_any_log = False
        if logs_dir.exists():
            for log_file in logs_dir.glob("app.log*"):
                if not log_file.is_file():
                    continue
                copied_any_log = True
                shutil.copy2(log_file, temp_dir / log_file.name)
        if not copied_any_log:
            warnings.append("No application logs were found.")

        if include_db_copy:
            if db_path.exists() and db_path.is_file():
                shutil.copy2(db_path, temp_dir / db_path.name)
            else:
                warnings.append("Database file not found; skipped DB snapshot.")

        files_added = 0
        with ZipFile(out_path, mode="w", compression=ZIP_DEFLATED) as bundle:
            for file_path in temp_dir.iterdir():
                if not file_path.is_file():
                    continue
                bundle.write(file_path, arcname=file_path.name)
                files_added += 1

    return DiagnosticsBundleResult(
        output_path=out_path,
        files_added=files_added,
        warnings=tuple(warnings),
    )


__all__ = ["DiagnosticsBundleResult", "build_diagnostics_bundle"]
