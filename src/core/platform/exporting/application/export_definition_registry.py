from __future__ import annotations

from src.core.platform.exporting.domain import ExportDefinition


class ExportDefinitionRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ExportDefinition] = {}

    @staticmethod
    def normalize_key(operation_key: str) -> str:
        normalized = str(operation_key or "").strip().lower()
        if not normalized:
            raise ValueError("Export operation key is required.")
        return normalized

    def register(self, definition: ExportDefinition) -> None:
        key = self.normalize_key(definition.operation_key)
        if key in self._definitions:
            raise ValueError(f"Export definition is already registered for '{key}'.")
        self._definitions[key] = definition

    def has(self, operation_key: str) -> bool:
        return self.normalize_key(operation_key) in self._definitions

    def get(self, operation_key: str) -> ExportDefinition:
        key = self.normalize_key(operation_key)
        try:
            return self._definitions[key]
        except KeyError as exc:
            raise ValueError(f"Unsupported export type: {operation_key}") from exc

    def list_operation_keys(self) -> tuple[str, ...]:
        return tuple(self._definitions.keys())


__all__ = ["ExportDefinitionRegistry"]
