from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from infra.version import get_app_version


def has_default_mail_client() -> bool:
    if os.name != "nt":
        return True
    try:
        import winreg
    except Exception:
        return True

    roots = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
    keys = (
        r"Software\Clients\Mail",
        r"SOFTWARE\WOW6432Node\Clients\Mail",
    )
    for root in roots:
        for key_path in keys:
            try:
                with winreg.OpenKey(root, key_path) as key:
                    value, _ = winreg.QueryValueEx(key, None)
                    if str(value or "").strip():
                        return True
            except OSError:
                continue
    return False


def compose_incident_email(*, incident_id: str, bundle_path: Path) -> tuple[str, str]:
    subject = f"ProjectManagerLite Incident {incident_id}"
    body = "\n".join(
        [
            "Please find incident diagnostics attached.",
            "",
            f"Incident ID: {incident_id}",
            f"App Version: {get_app_version()}",
            f"Generated: {datetime.now().isoformat(timespec='seconds')}",
            f"Bundle Path: {bundle_path}",
            "",
            "Issue Summary:",
            "- What were you trying to do?",
            "- What happened instead?",
            "- Steps to reproduce:",
        ]
    )
    return subject, body


def open_incident_mailto(*, support_email: str, subject_text: str, body_text: str) -> bool:
    if not has_default_mail_client():
        return False
    subject = quote(subject_text)
    body = quote(body_text)
    return QDesktopServices.openUrl(QUrl(f"mailto:{support_email}?subject={subject}&body={body}"))


def clipboard_email_template(*, support_email: str, subject_text: str, body_text: str) -> str:
    return "\n".join(
        [
            f"To: {support_email}",
            f"Subject: {subject_text}",
            "",
            body_text,
        ]
    )


__all__ = [
    "clipboard_email_template",
    "compose_incident_email",
    "has_default_mail_client",
    "open_incident_mailto",
]
