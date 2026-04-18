from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from src.ui.shared.formatting.ui_config import UIConfig as CFG


@dataclass(frozen=True)
class NavigationEntry:
    module_code: str
    module_label: str
    group_label: str
    label: str
    tab_index: int


@dataclass(frozen=True)
class NavigationModule:
    code: str
    label: str
    enabled: bool = True


class ShellNavigation(QWidget):
    workspace_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._item_by_tab_index: dict[int, QTreeWidgetItem] = {}
        self._module_items: dict[str, QTreeWidgetItem] = {}
        self._group_items: dict[tuple[str, str], QTreeWidgetItem] = {}
        self._syncing_selection = False
        self.setObjectName("shellNavigation")
        self.setMinimumWidth(240)
        self.setMaximumWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.setSpacing(CFG.SPACING_SM)

        self.eyebrow = QLabel("Enterprise shell")
        self.eyebrow.setObjectName("shellNavigationEyebrow")
        layout.addWidget(self.eyebrow)

        self.title_label = QLabel("Navigation")
        self.title_label.setObjectName("shellNavigationTitle")
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Platform tools and business modules live together here.")
        self.subtitle_label.setObjectName("shellNavigationSubtitle")
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

        self.tree = QTreeWidget()
        self.tree.setObjectName("shellNavigationTree")
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setIndentation(16)
        self.tree.setUniformRowHeights(True)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tree, 1)

        self.empty_state_label = QLabel("No workspaces are available for this account.")
        self.empty_state_label.setObjectName("shellNavigationEmpty")
        self.empty_state_label.setWordWrap(True)
        self.empty_state_label.hide()
        layout.addWidget(self.empty_state_label)

        self.setStyleSheet(
            f"""
            QWidget#shellNavigation {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 16px;
            }}
            QLabel#shellNavigationEyebrow {{
                color: {CFG.COLOR_ACCENT};
                font-size: 9pt;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }}
            QLabel#shellNavigationTitle {{
                color: {CFG.COLOR_TEXT_PRIMARY};
                font-size: 16pt;
                font-weight: 700;
            }}
            QLabel#shellNavigationSubtitle, QLabel#shellNavigationEmpty {{
                color: {CFG.COLOR_TEXT_SECONDARY};
                font-size: 9pt;
            }}
            QTreeWidget#shellNavigationTree {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QTreeWidget#shellNavigationTree::item {{
                color: {CFG.COLOR_TEXT_SECONDARY};
                padding: 6px 10px;
                border-radius: 8px;
            }}
            QTreeWidget#shellNavigationTree::item:selected {{
                background: {CFG.COLOR_ACCENT_SOFT};
                color: {CFG.COLOR_ACCENT};
                font-weight: 700;
            }}
            """
        )

    def set_entries(
        self,
        entries: list[NavigationEntry],
        *,
        modules: list[NavigationModule] | None = None,
    ) -> None:
        self._syncing_selection = True
        try:
            self.tree.clear()
            self._item_by_tab_index.clear()
            self._module_items.clear()
            self._group_items.clear()

            module_entries = modules or self._infer_modules(entries)
            for module in module_entries:
                module_item = QTreeWidgetItem([module.label])
                module_item.setFirstColumnSpanned(True)
                module_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                module_font = module_item.font(0)
                module_font.setBold(True)
                module_item.setFont(0, module_font)
                module_item.setData(0, Qt.ItemDataRole.UserRole, None)
                if not module.enabled:
                    module_item.setDisabled(True)
                    module_item.setToolTip(0, f"{module.label} is planned and not yet enabled.")
                self.tree.addTopLevelItem(module_item)
                self._module_items[module.code] = module_item

            for entry in entries:
                module_item = self._module_items.get(entry.module_code)
                if module_item is None:
                    module_item = QTreeWidgetItem([entry.module_label])
                    module_item.setFirstColumnSpanned(True)
                    module_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    module_font = module_item.font(0)
                    module_font.setBold(True)
                    module_item.setFont(0, module_font)
                    module_item.setData(0, Qt.ItemDataRole.UserRole, None)
                    self.tree.addTopLevelItem(module_item)
                    self._module_items[entry.module_code] = module_item

                group_key = (entry.module_code, entry.group_label)
                group_item = self._group_items.get(group_key)
                if group_item is None:
                    group_item = QTreeWidgetItem([entry.group_label])
                    group_item.setFirstColumnSpanned(True)
                    group_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    group_font = group_item.font(0)
                    group_font.setBold(True)
                    group_item.setFont(0, group_font)
                    group_item.setData(0, Qt.ItemDataRole.UserRole, None)
                    module_item.addChild(group_item)
                    self._group_items[group_key] = group_item

                item = QTreeWidgetItem([entry.label])
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item.setData(0, Qt.ItemDataRole.UserRole, entry.tab_index)
                group_item.addChild(item)
                self._item_by_tab_index[entry.tab_index] = item

            for module in module_entries:
                module_item = self._module_items.get(module.code)
                if module_item is not None and module.enabled:
                    module_item.setExpanded(True)
            for group_item in self._group_items.values():
                group_item.setExpanded(True)
            has_entries = bool(entries)
            self.tree.setVisible(has_entries)
            self.empty_state_label.setVisible(not has_entries)
        finally:
            self._syncing_selection = False

    def set_module_summary(self, summary_text: str | None) -> None:
        text = (summary_text or "").strip()
        if not text:
            text = "Grouped navigation for delivery, control, and admin work."
        self.subtitle_label.setText(text)

    def set_current_index(self, index: int) -> None:
        self._syncing_selection = True
        try:
            item = self._item_by_tab_index.get(index)
            self.tree.clearSelection()
            if item is not None:
                self.tree.setCurrentItem(item)
                item.setSelected(True)
            else:
                self.tree.setCurrentItem(None)
        finally:
            self._syncing_selection = False

    def _infer_modules(self, entries: list[NavigationEntry]) -> list[NavigationModule]:
        seen: list[NavigationModule] = []
        known_codes: set[str] = set()
        for entry in entries:
            if entry.module_code in known_codes:
                continue
            seen.append(NavigationModule(code=entry.module_code, label=entry.module_label, enabled=True))
            known_codes.add(entry.module_code)
        return seen

    def _on_selection_changed(self) -> None:
        if self._syncing_selection:
            return
        items = self.tree.selectedItems()
        if not items:
            return
        tab_index = items[0].data(0, Qt.ItemDataRole.UserRole)
        if isinstance(tab_index, int):
            self.workspace_selected.emit(tab_index)
