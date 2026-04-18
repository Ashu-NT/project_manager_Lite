from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class UndoCommand:
    label: str
    redo: Callable[[], None]
    undo: Callable[[], None]


class UndoStack:
    def __init__(self, max_depth: int = 50) -> None:
        self._undo: list[UndoCommand] = []
        self._redo: list[UndoCommand] = []
        self._max_depth = max(1, int(max_depth))

    def push_and_execute(self, command: UndoCommand) -> None:
        command.redo()
        self._undo.append(command)
        if len(self._undo) > self._max_depth:
            self._undo = self._undo[-self._max_depth :]
        self._redo.clear()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> str | None:
        if not self._undo:
            return None
        command = self._undo.pop()
        command.undo()
        self._redo.append(command)
        return command.label

    def redo(self) -> str | None:
        if not self._redo:
            return None
        command = self._redo.pop()
        command.redo()
        self._undo.append(command)
        return command.label

    def next_undo_label(self) -> str | None:
        return self._undo[-1].label if self._undo else None

    def next_redo_label(self) -> str | None:
        return self._redo[-1].label if self._redo else None

