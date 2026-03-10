from __future__ import annotations

from ui.dashboard.layout_builder import DashboardLayoutDialog


class DashboardLayoutStateMixin:
    def _apply_persisted_dashboard_layout(self) -> None:
        store = getattr(self, "_settings_store", None)
        payload = store.load_dashboard_layout() if store is not None else {}
        self._apply_dashboard_layout(payload)

    def _open_dashboard_layout_builder(self) -> None:
        current = self._current_dashboard_layout_payload()
        dlg = DashboardLayoutDialog(self, current_layout=current)
        if dlg.exec() != dlg.accepted:
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
        }

    def _apply_dashboard_layout(self, payload: dict[str, object] | None) -> None:
        data = dict(payload or {})
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


__all__ = ["DashboardLayoutStateMixin"]

