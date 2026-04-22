from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoginViewModel:
    title: str = "Sign in"
    username_label: str = "Username"
    password_label: str = "Password"
    submit_label: str = "Continue"
    username: str = ""
    password: str = ""
    error_message: str = ""
    is_busy: bool = False


__all__ = ["LoginViewModel"]
