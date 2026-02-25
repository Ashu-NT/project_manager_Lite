from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from core.domain.enums import CostType
from core.models import Resource
from ui.styles.ui_config import UIConfig as CFG


class ResourceFiltersMixin:
    _all_resources: list[Resource]

    def _build_resource_filters(self, layout: QVBoxLayout) -> None:
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Search:"))
        self.resource_search_filter = QLineEdit()
        self.resource_search_filter.setPlaceholderText("Name, role, category...")
        self.resource_search_filter.setClearButtonEnabled(True)
        self.resource_search_filter.setSizePolicy(CFG.INPUT_POLICY)
        self.resource_search_filter.setMinimumHeight(CFG.INPUT_HEIGHT)
        bar.addWidget(self.resource_search_filter)

        bar.addWidget(QLabel("Active:"))
        self.resource_active_filter = QComboBox()
        self.resource_active_filter.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.resource_active_filter.setFixedHeight(CFG.INPUT_HEIGHT)
        self.resource_active_filter.addItem("All", userData="")
        self.resource_active_filter.addItem("Active", userData="active")
        self.resource_active_filter.addItem("Inactive", userData="inactive")
        bar.addWidget(self.resource_active_filter)

        bar.addWidget(QLabel("Category:"))
        self.resource_category_filter = QComboBox()
        self.resource_category_filter.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.resource_category_filter.setFixedHeight(CFG.INPUT_HEIGHT)
        self.resource_category_filter.addItem("All", userData="")
        for cost_type in CostType:
            self.resource_category_filter.addItem(cost_type.value.title(), userData=cost_type.value)
        bar.addWidget(self.resource_category_filter)

        self.btn_clear_resource_filters = QPushButton("Clear Filters")
        self.btn_clear_resource_filters.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_clear_resource_filters.setFixedHeight(CFG.BUTTON_HEIGHT)
        bar.addWidget(self.btn_clear_resource_filters)
        layout.addLayout(bar)

        self.resource_search_filter.textChanged.connect(self._on_resource_filters_changed)
        self.resource_active_filter.currentIndexChanged.connect(self._on_resource_filters_changed)
        self.resource_category_filter.currentIndexChanged.connect(self._on_resource_filters_changed)
        self.btn_clear_resource_filters.clicked.connect(self._clear_resource_filters)

    def _on_resource_filters_changed(self, *_args) -> None:
        selected = self._get_selected_resource()
        selected_id = selected.id if selected else None
        self._render_resource_rows(preferred_resource_id=selected_id)

    def _clear_resource_filters(self) -> None:
        self.resource_search_filter.blockSignals(True)
        self.resource_active_filter.blockSignals(True)
        self.resource_category_filter.blockSignals(True)
        self.resource_search_filter.clear()
        self.resource_active_filter.setCurrentIndex(0)
        self.resource_category_filter.setCurrentIndex(0)
        self.resource_search_filter.blockSignals(False)
        self.resource_active_filter.blockSignals(False)
        self.resource_category_filter.blockSignals(False)
        self._render_resource_rows(preferred_resource_id=None)

    def _apply_resource_filters(self, resources: list[Resource]) -> list[Resource]:
        query = self.resource_search_filter.text().strip().lower()
        active_mode = str(self.resource_active_filter.currentData() or "").strip()
        category = str(self.resource_category_filter.currentData() or "").strip()
        filtered: list[Resource] = []
        for resource in resources:
            if active_mode == "active" and not getattr(resource, "is_active", True):
                continue
            if active_mode == "inactive" and getattr(resource, "is_active", True):
                continue
            resource_category = getattr(getattr(resource, "cost_type", None), "value", "")
            if category and resource_category != category:
                continue
            if query:
                haystack = " ".join(
                    [
                        resource.name or "",
                        resource.role or "",
                        resource_category,
                        resource.currency_code or "",
                    ]
                ).lower()
                if query not in haystack:
                    continue
            filtered.append(resource)
        return filtered

    def _render_resource_rows(self, preferred_resource_id: Optional[str]) -> None:
        visible_resources = self._apply_resource_filters(list(self._all_resources))
        self.model.set_resources(visible_resources)
        if not visible_resources:
            self._sync_actions()
            return

        row = 0
        if preferred_resource_id:
            for idx, resource in enumerate(visible_resources):
                if resource.id == preferred_resource_id:
                    row = idx
                    break
        self.table.selectRow(row)
        self._sync_actions()


__all__ = ["ResourceFiltersMixin"]
