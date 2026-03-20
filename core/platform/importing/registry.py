from __future__ import annotations

from .contracts import ImportDefinition


class ImportDefinitionRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ImportDefinition] = {}

    @staticmethod
    def normalize_key(operation_key: str) -> str:
        normalized = str(operation_key or "").strip().lower()
        if not normalized:
            raise ValueError("Import operation key is required.")
        return normalized

    def register(self, definition: ImportDefinition) -> None:
        key = self.normalize_key(definition.operation_key)
        if key in self._definitions:
            raise ValueError(f"Import definition is already registered for '{key}'.")
        self._definitions[key] = definition

    def has(self, operation_key: str) -> bool:
        return self.normalize_key(operation_key) in self._definitions

    def get(self, operation_key: str) -> ImportDefinition:
        key = self.normalize_key(operation_key)
        try:
            return self._definitions[key]
        except KeyError as exc:
            raise ValueError(f"Unsupported import type: {operation_key}") from exc

    def list_operation_keys(self) -> tuple[str, ...]:
        return tuple(self._definitions.keys())


__all__ = ["ImportDefinitionRegistry"]
