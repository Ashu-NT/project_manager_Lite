from __future__ import annotations

LEGACY_MODULE_CODE_ALIASES: dict[str, str] = {
    "payroll": "hr_management",
}


def normalize_module_code(module_code: str | None) -> str:
    normalized = str(module_code or "").strip().lower()
    return LEGACY_MODULE_CODE_ALIASES.get(normalized, normalized)


def module_storage_codes(module_code: str | None) -> tuple[str, ...]:
    canonical_code = normalize_module_code(module_code)
    legacy_codes = tuple(
        legacy_code
        for legacy_code, target_code in LEGACY_MODULE_CODE_ALIASES.items()
        if target_code == canonical_code
    )
    return (canonical_code, *legacy_codes)


__all__ = [
    "LEGACY_MODULE_CODE_ALIASES",
    "module_storage_codes",
    "normalize_module_code",
]
