from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QSizePolicy,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QStyle,
)

from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.shared.styles.ui_config import UIConfig as CFG


@dataclass(frozen=True)
class MaintenanceWorkbenchSection:
    key: str
    label: str
    widget: QWidget


class MaintenanceWorkbenchNavigator(QWidget):
    def __init__(self, *, object_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self._section_items: dict[str, QTreeWidgetItem] = {}
        self._stack_indexes: dict[str, int] = {}
        self._section_labels: dict[str, str] = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(CFG.SPACING_MD)

        self.tree_panel = QWidget()
        self.tree_panel.setObjectName(f"{object_name}TreePanel")
        self.tree_panel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.tree_panel.setMinimumWidth(220)
        self.tree_panel.setMaximumWidth(260)
        self.tree_panel.setStyleSheet(
            f"""
            QWidget#{object_name}TreePanel {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        tree_layout = QVBoxLayout(self.tree_panel)
        tree_layout.setContentsMargins(8, 8, 8, 8)
        tree_layout.setSpacing(CFG.SPACING_XS)
        tree_title = QLabel("Sections")
        tree_title.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        tree_layout.addWidget(tree_title)

        from PySide6.QtWidgets import QTreeWidget

        self.tree = QTreeWidget()
        self.tree.setObjectName(f"{object_name}Tree")
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(0)
        self.tree.setUniformRowHeights(True)
        self.tree.setStyleSheet(
            f"""
            QTreeWidget#{object_name}Tree {{
                background-color: transparent;
                border: none;
                padding: 2px;
            }}
            QTreeWidget#{object_name}Tree::item {{
                padding: 7px 8px;
                border-radius: 8px;
                color: {CFG.COLOR_TEXT_PRIMARY};
            }}
            QTreeWidget#{object_name}Tree::item:selected {{
                background-color: {CFG.COLOR_ACCENT};
                color: {CFG.COLOR_TEXT_ON_ACCENT};
            }}
            """
        )
        tree_layout.addWidget(self.tree, 1)

        self.content_panel = QWidget()
        content_layout = QVBoxLayout(self.content_panel)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(CFG.SPACING_SM)
        header_row = QHBoxLayout()
        header_row.setSpacing(CFG.SPACING_SM)
        self.current_section_label = QLabel("No section selected")
        self.current_section_label.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        header_row.addWidget(self.current_section_label, 1)
        self.btn_toggle_tree = QPushButton("<< Hide Sections")
        self.btn_toggle_tree.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_toggle_tree.setStyleSheet(dashboard_action_button_style("secondary"))
        header_row.addWidget(self.btn_toggle_tree)
        content_layout.addLayout(header_row)

        self.stack = QStackedWidget()
        self.stack.setObjectName(f"{object_name}Stack")
        content_layout.addWidget(self.stack, 1)
        layout.addWidget(self.tree_panel)
        layout.addWidget(self.content_panel, 1)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.btn_toggle_tree.clicked.connect(self._toggle_tree_panel)

    def set_sections(self, sections: Sequence[MaintenanceWorkbenchSection], *, initial_key: str | None = None) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        while self.stack.count():
            widget = self.stack.widget(0)
            self.stack.removeWidget(widget)
        self._section_items.clear()
        self._stack_indexes.clear()
        self._section_labels.clear()

        for section in sections:
            item = QTreeWidgetItem([section.label])
            item.setData(0, Qt.UserRole, section.key)
            self.tree.addTopLevelItem(item)
            self._section_items[section.key] = item
            self._stack_indexes[section.key] = self.stack.count()
            self._section_labels[section.key] = section.label
            self.stack.addWidget(section.widget)

        target_key = initial_key or (sections[0].key if sections else None)
        if target_key:
            self.set_current_section(target_key)
        self.tree.blockSignals(False)
        if not target_key:
            self.current_section_label.setText("No section selected")

    def set_current_section(self, key: str) -> None:
        item = self._section_items.get(key)
        if item is None:
            return
        self.tree.setCurrentItem(item)
        self._apply_item_to_stack(item)

    def current_section_key(self) -> str | None:
        item = self.tree.currentItem()
        if item is None:
            return None
        value = item.data(0, Qt.UserRole)
        return str(value) if value else None

    def _on_selection_changed(self) -> None:
        item = self.tree.currentItem()
        if item is None:
            return
        self._apply_item_to_stack(item)

    def _apply_item_to_stack(self, item: QTreeWidgetItem) -> None:
        key = item.data(0, Qt.UserRole)
        if not key:
            return
        stack_index = self._stack_indexes.get(str(key))
        if stack_index is not None:
            self.stack.setCurrentIndex(stack_index)
            self.current_section_label.setText(self._section_labels.get(str(key), str(key)))

    def _toggle_tree_panel(self) -> None:
        should_show = self.tree_panel.isHidden()
        self.tree_panel.setVisible(should_show)
        self.btn_toggle_tree.setText("<< Hide Sections" if should_show else ">> Show Sections")


def build_maintenance_header(
    *,
    root: QVBoxLayout,
    object_name: str,
    eyebrow_text: str,
    title_text: str,
    subtitle_text: str,
    badges: Sequence[QLabel],
) -> QWidget:
    header = QWidget()
    header.setObjectName(object_name)
    header.setSizePolicy(CFG.H_EXPAND_V_FIXED)
    header.setStyleSheet(
        f"""
        QWidget#{object_name} {{
            background-color: {CFG.COLOR_BG_SURFACE};
            border: 1px solid {CFG.COLOR_BORDER};
            border-radius: 12px;
        }}
        """
    )
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(CFG.MARGIN_SM, CFG.SPACING_XS, CFG.MARGIN_SM, CFG.SPACING_XS)
    header_layout.setSpacing(CFG.SPACING_SM)
    intro = QVBoxLayout()
    intro.setSpacing(CFG.SPACING_XS)
    eyebrow = QLabel(eyebrow_text)
    eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
    title = QLabel(title_text)
    title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
    subtitle = QLabel(subtitle_text)
    subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
    subtitle.setWordWrap(True)
    intro.addWidget(eyebrow)
    intro.addWidget(title)
    intro.addWidget(subtitle)
    header_layout.addLayout(intro, 1)

    badges_widget = QWidget()
    badges_layout = QGridLayout(badges_widget)
    badges_layout.setContentsMargins(0, 0, 0, 0)
    badges_layout.setHorizontalSpacing(CFG.SPACING_XS)
    badges_layout.setVerticalSpacing(CFG.SPACING_XS)
    for index, badge in enumerate(badges):
        badges_layout.addWidget(badge, index // 2, index % 2, 1, 1, Qt.AlignRight)
    header_layout.addWidget(badges_widget, 0, Qt.AlignTop | Qt.AlignRight)
    root.addWidget(header)
    return header


def make_accent_badge(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
    return label


def make_meta_badge(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(dashboard_meta_chip_style())
    return label


def make_filter_toggle_button(parent: QWidget, *, label: str = "Filters") -> QPushButton:
    button = QPushButton(label, parent)
    button.setFixedHeight(CFG.BUTTON_HEIGHT)
    button.setMinimumWidth(132)
    button.setStyleSheet(dashboard_action_button_style("secondary"))
    button.setIcon(parent.style().standardIcon(QStyle.SP_FileDialogDetailedView))
    return button


def set_filter_panel_visible(*, button: QPushButton, panel: QWidget, visible: bool) -> None:
    panel.setVisible(visible)
    button.setText(" Hide Filters" if visible else " Filters")
    button.setIcon(
        button.style().standardIcon(
            QStyle.SP_ArrowUp if visible else QStyle.SP_FileDialogDetailedView
        )
    )


def reset_combo_options(
    combo: QComboBox,
    *,
    placeholder: str,
    options: Iterable[tuple[str, object]],
    selected_value: object | None = None,
) -> None:
    combo.blockSignals(True)
    combo.clear()
    combo.addItem(placeholder, None)
    for label, value in options:
        combo.addItem(label, value)
    if selected_value is not None:
        index = combo.findData(selected_value)
        if index >= 0:
            combo.setCurrentIndex(index)
    combo.blockSignals(False)


def selected_combo_value(combo: QComboBox) -> str | None:
    value = combo.currentData()
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.isoformat(sep=" ", timespec="minutes")


def display_metric(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


__all__ = [
    "MaintenanceWorkbenchNavigator",
    "MaintenanceWorkbenchSection",
    "build_maintenance_header",
    "display_metric",
    "format_timestamp",
    "make_filter_toggle_button",
    "make_accent_badge",
    "make_meta_badge",
    "reset_combo_options",
    "selected_combo_value",
    "set_filter_panel_visible",
]
