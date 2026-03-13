from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ui.styles.ui_config import UIConfig as CFG


@dataclass(frozen=True)
class NavigationEntry:
    section: str
    label: str
    tab_index: int


class ShellNavigation(QWidget):
    workspace_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._item_by_tab_index: dict[int, QTreeWidgetItem] = {}
        self._syncing_selection = False
        self.setObjectName("shellNavigation")
        self.setMinimumWidth(240)
        self.setMaximumWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.setSpacing(CFG.SPACING_SM)

        self.eyebrow = QLabel("Program shell")
        self.eyebrow.setObjectName("shellNavigationEyebrow")
        layout.addWidget(self.eyebrow)

        self.title_label = QLabel("Workspaces")
        self.title_label.setObjectName("shellNavigationTitle")
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Grouped navigation for delivery, control, and admin work.")
        self.subtitle_label.setObjectName("shellNavigationSubtitle")
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

        self.tree = QTreeWidget()
        self.tree.setObjectName("shellNavigationTree")
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(14)
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
                padding: 7px 10px;
                border-radius: 8px;
            }}
            QTreeWidget#shellNavigationTree::item:selected {{
                background: {CFG.COLOR_ACCENT_SOFT};
                color: {CFG.COLOR_ACCENT};
                font-weight: 700;
            }}
            """
        )

    def set_entries(self, entries: list[NavigationEntry]) -> None:
        self._syncing_selection = True
        try:
            self.tree.clear()
            self._item_by_tab_index.clear()

            section_items: dict[str, QTreeWidgetItem] = {}
            for entry in entries:
                section_item = section_items.get(entry.section)
                if section_item is None:
                    section_item = QTreeWidgetItem([entry.section])
                    section_item.setFirstColumnSpanned(True)
                    section_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    section_font = section_item.font(0)
                    section_font.setBold(True)
                    section_item.setFont(0, section_font)
                    section_item.setData(0, Qt.ItemDataRole.UserRole, None)
                    self.tree.addTopLevelItem(section_item)
                    section_items[entry.section] = section_item

                item = QTreeWidgetItem([entry.label])
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                item.setData(0, Qt.ItemDataRole.UserRole, entry.tab_index)
                section_item.addChild(item)
                self._item_by_tab_index[entry.tab_index] = item

            self.tree.expandAll()
            has_entries = bool(entries)
            self.tree.setVisible(has_entries)
            self.empty_state_label.setVisible(not has_entries)
        finally:
            self._syncing_selection = False

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

    def _on_selection_changed(self) -> None:
        if self._syncing_selection:
            return
        items = self.tree.selectedItems()
        if not items:
            return
        tab_index = items[0].data(0, Qt.ItemDataRole.UserRole)
        if isinstance(tab_index, int):
            self.workspace_selected.emit(tab_index)
