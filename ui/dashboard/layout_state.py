from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from core.services.dashboard import PORTFOLIO_SCOPE_ID
from ui.dashboard.layout_builder import (
    DashboardLayoutDialog,
    PORTFOLIO_PANELS,
    PROJECT_PANELS,
)


class DashboardLayoutStateMixin:
    def _apply_persisted_dashboard_layout(self) -> None:
        store = getattr(self, "_settings_store", None)
        payload = store.load_dashboard_layout() if store is not None else {}
        self._apply_dashboard_layout(payload)

    def _open_dashboard_layout_builder(self) -> None:
        current = self._current_dashboard_layout_payload()
        dlg = DashboardLayoutDialog(
            self,
            current_layout=current,
            portfolio_mode=self._is_dashboard_portfolio_mode(),
        )
        if dlg.exec() != QDialog.Accepted:
            return
        payload = dlg.layout_payload
        self._apply_dashboard_layout(payload)
        store = getattr(self, "_settings_store", None)
        if store is not None:
            store.save_dashboard_layout(payload)

    def _current_dashboard_layout_payload(self) -> dict[str, object]:
        return self._normalize_dashboard_layout(getattr(self, "_dashboard_layout_preferences", {}))

    def _apply_dashboard_layout(self, payload: dict[str, object] | None) -> None:
        self._dashboard_layout_preferences = self._normalize_dashboard_layout(payload)
        self._sync_dashboard_panel_visibility()

    def _normalize_dashboard_layout(self, payload: dict[str, object] | None) -> dict[str, object]:
        data = dict(payload or {})
        if "project" in data or "portfolio" in data:
            return {
                "project": self._normalize_mode_layout(data.get("project"), PROJECT_PANELS),
                "portfolio": self._normalize_mode_layout(data.get("portfolio"), PORTFOLIO_PANELS),
            }
        return {
            "project": self._normalize_mode_layout(
                {
                    "visible_panels": self._legacy_visible_panels(data, portfolio_mode=False),
                    "panel_order": self._legacy_panel_order(data, PROJECT_PANELS, analysis_id="evm"),
                },
                PROJECT_PANELS,
            ),
            "portfolio": self._normalize_mode_layout(
                {
                    "visible_panels": self._legacy_visible_panels(data, portfolio_mode=True),
                    "panel_order": self._legacy_panel_order(data, PORTFOLIO_PANELS, analysis_id="portfolio"),
                },
                PORTFOLIO_PANELS,
            ),
        }

    def _normalize_mode_layout(self, value: object, defaults: tuple[str, ...]) -> dict[str, object]:
        raw = dict(value or {}) if isinstance(value, dict) else {}
        order = self._normalize_order(raw.get("panel_order"), defaults)
        visible = self._normalize_visible(raw.get("visible_panels"), order, defaults)
        return {
            "visible_panels": visible,
            "panel_order": order,
        }

    @staticmethod
    def _normalize_order(raw: object, defaults: tuple[str, ...]) -> list[str]:
        allowed = set(defaults)
        order: list[str] = []
        if isinstance(raw, (list, tuple)):
            for row in raw:
                token = str(row or "").strip().lower()
                if token in allowed and token not in order:
                    order.append(token)
        for token in defaults:
            if token not in order:
                order.append(token)
        return order

    def _normalize_visible(
        self,
        raw: object,
        order: list[str],
        defaults: tuple[str, ...],
    ) -> list[str]:
        visible: list[str] = []
        if isinstance(raw, (list, tuple)):
            allowed = set(defaults)
            for row in raw:
                token = str(row or "").strip().lower()
                if token in allowed and token not in visible:
                    visible.append(token)
        visible = [token for token in order if token in visible]
        for token in order:
            if len(visible) >= 2:
                break
            if token not in visible:
                visible.append(token)
        return visible[:4]

    def _legacy_visible_panels(self, payload: dict[str, object], *, portfolio_mode: bool) -> list[str]:
        selected: list[str] = []
        analysis_flag = bool(payload.get("show_analysis", payload.get("show_evm", True)))
        if bool(payload.get("show_kpi", True)):
            selected.append("kpi")
        if portfolio_mode:
            if bool(payload.get("show_portfolio", analysis_flag)):
                selected.append("portfolio")
        else:
            if analysis_flag:
                selected.append("evm")
        if bool(payload.get("show_burndown", True)):
            selected.append("burndown")
        if bool(payload.get("show_resource", True)):
            selected.append("resource")
        defaults = PORTFOLIO_PANELS if portfolio_mode else PROJECT_PANELS
        if not selected:
            return list(defaults)
        return selected

    def _legacy_panel_order(
        self,
        payload: dict[str, object],
        defaults: tuple[str, ...],
        *,
        analysis_id: str,
    ) -> list[str]:
        mapped: list[str] = []
        raw_values = []
        left_order = payload.get("left_order")
        chart_order = payload.get("chart_order")
        if isinstance(left_order, (list, tuple)):
            raw_values.extend(left_order)
        if isinstance(chart_order, (list, tuple)):
            raw_values.extend(chart_order)
        remap = {
            "kpi": "kpi",
            "evm": analysis_id,
            "analysis": analysis_id,
            "portfolio": analysis_id,
            "burndown": "burndown",
            "resource": "resource",
        }
        for row in raw_values:
            token = remap.get(str(row or "").strip().lower())
            if token and token not in mapped:
                mapped.append(token)
        return self._normalize_order(mapped, defaults)

    def _mode_key(self, portfolio_mode: bool) -> str:
        return "portfolio" if portfolio_mode else "project"

    def _mode_defaults(self, portfolio_mode: bool) -> tuple[str, ...]:
        return PORTFOLIO_PANELS if portfolio_mode else PROJECT_PANELS

    def _is_dashboard_portfolio_mode(self) -> bool:
        combo = getattr(self, "project_combo", None)
        if combo is not None and combo.currentData() == PORTFOLIO_SCOPE_ID:
            return True
        data = getattr(self, "_current_data", None)
        return bool(getattr(data, "portfolio", None) is not None)

    def _mode_layout_config(self, portfolio_mode: bool) -> dict[str, object]:
        prefs = self._normalize_dashboard_layout(getattr(self, "_dashboard_layout_preferences", {}))
        return dict(prefs[self._mode_key(portfolio_mode)])

    def _current_visible_panel_ids(self) -> list[str]:
        config = self._mode_layout_config(self._is_dashboard_portfolio_mode())
        return list(config.get("visible_panels", []))

    def _current_panel_order(self) -> list[str]:
        config = self._mode_layout_config(self._is_dashboard_portfolio_mode())
        return list(config.get("panel_order", []))

    def _panel_widgets(self) -> dict[str, object]:
        return {
            "kpi": self.kpi_group,
            "milestones": self.milestone_group,
            "watchlist": self.watchlist_group,
            "register": self.register_group,
            "evm": self.evm_group,
            "portfolio": self.portfolio_group,
            "burndown": self.burndown_chart,
            "resource": self.resource_chart,
        }

    def _active_dashboard_panel_count(self) -> int:
        return len(self._current_visible_panel_ids())

    def _sync_dashboard_panel_visibility(self) -> None:
        self.summary_widget.setVisible(True)
        self._arrange_dashboard_panels()
        if hasattr(self, "_sync_kpi_card_layout"):
            self._sync_kpi_card_layout()
        if hasattr(self, "dashboard_scope_hint"):
            count = self._active_dashboard_panel_count()
            self.dashboard_scope_hint.setText(f"{count} panels active")

    def _arrange_dashboard_panels(self) -> None:
        layout = getattr(self, "panel_grid", None)
        if layout is None:
            return
        layout.setAlignment(Qt.AlignTop)
        widgets = self._panel_widgets()
        selected = self._current_visible_panel_ids()
        columns = self._dashboard_panel_column_count(len(selected))

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                layout.removeWidget(widget)

        for widget in widgets.values():
            widget.setHidden(True)

        if not selected:
            return

        for idx, panel_id in enumerate(selected):
            widget = widgets[panel_id]
            widget.setHidden(False)
            row = idx if columns == 1 else idx // columns
            col = 0 if columns == 1 else idx % columns
            layout.addWidget(widget, row, col, 1, 1, Qt.AlignTop)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1 if columns > 1 else 0)
        layout.setColumnStretch(2, 1 if columns > 2 else 0)

    def _dashboard_panel_column_count(self, panel_count: int) -> int:
        if panel_count <= 1:
            return 1
        viewport = getattr(getattr(self, "panel_scroll", None), "viewport", lambda: None)()
        available_width = viewport.width() if viewport is not None else 0
        if available_width <= 0:
            return 2
        if available_width < 920:
            return 1
        if panel_count == 3 and available_width >= 1050:
            return 3
        return 2


__all__ = ["DashboardLayoutStateMixin"]
