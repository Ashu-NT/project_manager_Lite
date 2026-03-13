from __future__ import annotations

import hashlib
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import time
from urllib.parse import urlparse
from urllib.request import urlopen


def _ps_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _safe_installer_name(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name.strip() or "Setup_ProjectManagerLite_update.exe"
    if not name.lower().endswith(".exe"):
        name = f"{name}.exe"
    return name


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest().lower()


def verify_sha256(path: Path, expected_sha256: str) -> bool:
    expected = (expected_sha256 or "").strip().lower()
    if not expected:
        return True
    return sha256_file(path) == expected


def download_update_installer(
    *,
    url: str,
    download_dir: Path,
    timeout_seconds: int = 30,
    chunk_bytes: int = 1024 * 256,
    progress: Callable[[int | None, str | None], None] | None = None,
    is_cancelled: Callable[[], bool] | None = None,
) -> Path:
    source = (url or "").strip()
    if not source:
        raise ValueError("Update URL is required.")

    download_dir.mkdir(parents=True, exist_ok=True)
    target = download_dir / _safe_installer_name(source)
    temp_target = target.with_suffix(f"{target.suffix}.part")

    if temp_target.exists():
        temp_target.unlink()

    with urlopen(source, timeout=timeout_seconds) as response:  # noqa: S310
        total = int(response.headers.get("Content-Length", "0") or 0)
        read_bytes = 0
        with temp_target.open("wb") as handle:
            while True:
                if is_cancelled is not None and bool(is_cancelled()):
                    raise RuntimeError("Update download canceled.")
                chunk = response.read(max(1024, int(chunk_bytes)))
                if not chunk:
                    break
                handle.write(chunk)
                read_bytes += len(chunk)
                if progress is not None:
                    if total > 0:
                        percent = min(100, int((read_bytes * 100) / total))
                        progress(percent, f"Downloading installer... {percent}%")
                    else:
                        progress(None, "Downloading installer...")

    temp_target.replace(target)
    return target


@dataclass(frozen=True)
class PreparedUpdateLaunch:
    script_path: Path
    installer_path: Path


def prepare_windows_update_handoff(
    *,
    installer_path: Path,
    app_pid: int,
    relaunch_executable: str,
    relaunch_args: list[str],
    output_dir: Path,
) -> PreparedUpdateLaunch:
    if os.name != "nt":
        raise RuntimeError("In-app installer handoff is currently supported only on Windows.")
    if not installer_path.exists():
        raise FileNotFoundError(f"Installer not found: {installer_path}")
    if not relaunch_executable:
        raise ValueError("Relaunch executable is required.")

    output_dir.mkdir(parents=True, exist_ok=True)
    script_name = f"apply_update_{app_pid}_{int(time())}.ps1"
    script_path = output_dir / script_name

    args_literal = ", ".join(_ps_single_quote(arg) for arg in relaunch_args)
    args_initializer = f"@({args_literal})" if args_literal else "@()"

    script_text = "\n".join(
        [
            "$ErrorActionPreference = 'SilentlyContinue'",
            f"$targetPid = {int(app_pid)}",
            f"$installer = {_ps_single_quote(str(installer_path))}",
            f"$relaunchExe = {_ps_single_quote(str(relaunch_executable))}",
            f"$relaunchArgs = {args_initializer}",
            "",
            "while (Get-Process -Id $targetPid -ErrorAction SilentlyContinue) {",
            "  Start-Sleep -Milliseconds 500",
            "}",
            "",
            "$proc = $null",
            "try {",
            "  $proc = Start-Process -FilePath $installer -Wait -PassThru",
            "} catch {",
            "}",
            "",
            "try {",
            "  if ($relaunchArgs.Count -gt 0) {",
            "    Start-Process -FilePath $relaunchExe -ArgumentList $relaunchArgs | Out-Null",
            "  } else {",
            "    Start-Process -FilePath $relaunchExe | Out-Null",
            "  }",
            "} catch {",
            "}",
            "",
            "Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue",
            "",
        ]
    )
    script_path.write_text(script_text, encoding="utf-8")

    return PreparedUpdateLaunch(script_path=script_path, installer_path=installer_path)


def launch_windows_update_handoff(prepared: PreparedUpdateLaunch) -> None:
    if os.name != "nt":
        raise RuntimeError("In-app installer handoff is currently supported only on Windows.")
    if not prepared.script_path.exists():
        raise FileNotFoundError(f"Handoff script not found: {prepared.script_path}")

    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    command = [
        str(powershell),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(prepared.script_path),
    ]
    creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(command, close_fds=True, creationflags=creationflags)


__all__ = [
    "PreparedUpdateLaunch",
    "download_update_installer",
    "launch_windows_update_handoff",
    "prepare_windows_update_handoff",
    "sha256_file",
    "verify_sha256",
]
