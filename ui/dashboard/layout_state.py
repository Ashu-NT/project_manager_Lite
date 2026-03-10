from __future__ import annotations

from PySide6.QtWidgets import QDialog

from ui.dashboard.layout_builder import DashboardLayoutDialog


class DashboardLayoutStateMixin:
    def _apply_persisted_dashboard_layout(self) -> None:
        store = getattr(self, "_settings_store", None)
        payload = store.load_dashboard_layout() if store is not None else {}
        self._apply_dashboard_layout(payload)

    def _open_dashboard_layout_builder(self) -> None:
        current = self._current_dashboard_layout_payload()
        dlg = DashboardLayoutDialog(self, current_layout=current)
        if dlg.exec() != QDialog.Accepted:
            return
        payload = dlg.layout_payload
        self._apply_dashboard_layout(payload)
        store = getattr(self, "_settings_store", None)
        if store is not None:
            store.save_dashboard_layout(payload)

    def _current_dashboard_layout_payload(self) -> dict[str, object]:
        main_sizes = self.main_splitter.sizes()
        main_total = max(1, sum(main_sizes) or 1)
        chart_sizes = self.chart_splitter.sizes()
        chart_total = max(1, sum(chart_sizes) or 1)
        return {
            "show_summary": self.summary_widget.isVisible(),
            "show_kpi": self.kpi_group.isVisible(),
            "show_evm": self.evm_group.isVisible(),
            "show_burndown": self.burndown_chart.isVisible(),
            "show_resource": self.resource_chart.isVisible(),
            "main_left_percent": int((main_sizes[0] * 100) / main_total) if len(main_sizes) >= 2 else 50,
            "chart_top_percent": int((chart_sizes[0] * 100) / chart_total) if len(chart_sizes) >= 2 else 50,
            "left_order": self._current_left_order(),
            "chart_order": self._current_chart_order(),
        }

    def _apply_dashboard_layout(self, payload: dict[str, object] | None) -> None:
        data = dict(payload or {})
        self._apply_left_order(data.get("left_order"))
        self._apply_chart_order(data.get("chart_order"))
        self.summary_widget.setVisible(bool(data.get("show_summary", True)))
        self.kpi_group.setVisible(bool(data.get("show_kpi", True)))
        self.evm_group.setVisible(bool(data.get("show_evm", True)))
        self.burndown_chart.setVisible(bool(data.get("show_burndown", True)))
        self.resource_chart.setVisible(bool(data.get("show_resource", True)))

        main_left_percent = max(20, min(80, int(data.get("main_left_percent", 50))))
        chart_top_percent = max(20, min(80, int(data.get("chart_top_percent", 50))))
        main_width = max(600, self.main_splitter.size().width() or 1200)
        left = int(main_width * main_left_percent / 100)
        self.main_splitter.setSizes([left, max(200, main_width - left)])

        chart_height = max(260, self.chart_splitter.size().height() or 520)
        top = int(chart_height * chart_top_percent / 100)
        self.chart_splitter.setSizes([top, max(140, chart_height - top)])

    @staticmethod
    def _normalize_order(raw: object, defaults: tuple[str, ...]) -> list[str]:
        allowed = set(defaults)
        order: list[str] = []
        if isinstance(raw, (list, tuple)):
            for row in raw:
                key = str(row or "").strip().lower()
                if key in allowed and key not in order:
                    order.append(key)
        for key in defaults:
            if key not in order:
                order.append(key)
        return order

    def _left_widgets(self) -> dict[str, object]:
        return {
            "summary": self.summary_widget,
            "kpi": self.kpi_group,
            "evm": self.evm_group,
        }

    def _chart_widgets(self) -> dict[str, object]:
        return {
            "burndown": self.burndown_chart,
            "resource": self.resource_chart,
        }

    def _current_left_order(self) -> list[str]:
        layout = getattr(self, "left_layout", None)
        if layout is None:
            return ["summary", "kpi", "evm"]
        reverse = {id(widget): key for key, widget in self._left_widgets().items()}
        order: list[str] = []
        for idx in range(layout.count()):
            item = layout.itemAt(idx)
            widget = item.widget() if item is not None else None
            key = reverse.get(id(widget)) if widget is not None else None
            if key:
                order.append(key)
        return self._normalize_order(order, ("summary", "kpi", "evm"))

    def _current_chart_order(self) -> list[str]:
        reverse = {id(widget): key for key, widget in self._chart_widgets().items()}
        order: list[str] = []
        for idx in range(self.chart_splitter.count()):
            widget = self.chart_splitter.widget(idx)
            key = reverse.get(id(widget)) if widget is not None else None
            if key:
                order.append(key)
        return self._normalize_order(order, ("burndown", "resource"))

    def _apply_left_order(self, raw_order: object) -> None:
        layout = getattr(self, "left_layout", None)
        if layout is None:
            return
        widgets = self._left_widgets()
        order = self._normalize_order(raw_order, ("summary", "kpi", "evm"))
        for widget in widgets.values():
            layout.removeWidget(widget)
        for key in order:
            layout.addWidget(widgets[key])
        for key, widget in widgets.items():
            idx = layout.indexOf(widget)
            if idx >= 0:
                layout.setStretch(idx, 1 if key == "evm" else 0)

    def _apply_chart_order(self, raw_order: object) -> None:
        widgets = self._chart_widgets()
        order = self._normalize_order(raw_order, ("burndown", "resource"))
        for idx, key in enumerate(order):
            self.chart_splitter.insertWidget(idx, widgets[key])
            self.chart_splitter.setStretchFactor(idx, 1)


__all__ = ["DashboardLayoutStateMixin"]
