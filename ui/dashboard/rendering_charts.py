from __future__ import annotations

import matplotlib.dates as mdates
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QListWidgetItem, QTableWidgetItem

from core.services.dashboard import DashboardData


class DashboardChartsRenderingMixin:
    def _update_burndown_chart(self, data: DashboardData):
        self.burndown_chart.ax.clear()
        pts = data.burndown
        if not pts:
            self.burndown_chart.ax.set_title("No burndown data")
            self.burndown_chart.redraw()
            return

        dates = [p.day for p in pts]
        rem = [p.remaining_tasks for p in pts]

        self.burndown_chart.ax.plot(dates, rem, marker="o")
        self.burndown_chart.ax.set_title("Burndown (remaining tasks)")
        self.burndown_chart.ax.set_xlabel("Date", fontsize=10)
        self.burndown_chart.ax.set_ylabel("Remaining tasks", fontsize=10)
        self.burndown_chart.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.burndown_chart.ax.xaxis.set_major_formatter(
            mdates.ConciseDateFormatter(mdates.AutoDateLocator())
        )
        self.burndown_chart.fig.autofmt_xdate(rotation=30)
        self.burndown_chart.ax.grid(True, linestyle=":", linewidth=0.5)

        self.burndown_chart.fig.tight_layout()
        self.burndown_chart.redraw()

    def _update_resource_chart(self, data: DashboardData):
        self.resource_chart.ax.clear()
        rows = data.resource_load
        if not rows:
            self.resource_chart.ax.set_title("No resource load data")
            self.resource_chart.redraw()
            return

        names = [r.resource_name for r in rows]
        allocs = [r.total_allocation_percent for r in rows]

        x = range(len(names))
        bars = self.resource_chart.ax.bar(x, allocs)
        for i, r in enumerate(rows):
            if r.total_allocation_percent > 100.0:
                bars[i].set_color("#d0021b")

        self.resource_chart.ax.set_xticks(list(x))
        self.resource_chart.ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
        self.resource_chart.ax.set_ylabel("Allocation %", fontsize=10)
        self.resource_chart.ax.set_title("Resource load")
        self.resource_chart.ax.axhline(100.0, color="red", linestyle="--", linewidth=0.5)
        self.resource_chart.ax.grid(True, axis="y", linestyle=":", linewidth=0.5)

        self.resource_chart.fig.tight_layout()
        self.resource_chart.redraw()

    def _update_alerts(self, data: DashboardData):
        self.alerts_list.clear()
        if not data.alerts:
            self.alerts_list.addItem("No alerts. Everything looks good.")
            return

        for msg in data.alerts:
            item = QListWidgetItem("WARNING: " + msg)
            item.setForeground(QColor("#d0021b"))
            self.alerts_list.addItem(item)

    def _update_upcoming(self, data: DashboardData):
        self.upcoming_table.setRowCount(0)
        ups = data.upcoming_tasks
        if not ups:
            return

        self.upcoming_table.setRowCount(len(ups))
        for row, u in enumerate(ups):
            def set_cell(col, text, color_bg=None):
                item = QTableWidgetItem(text)
                if color_bg:
                    item.setBackground(color_bg)
                self.upcoming_table.setItem(row, col, item)

            set_cell(0, u.name)
            set_cell(1, u.start_date.isoformat() if u.start_date else "-")
            set_cell(2, u.end_date.isoformat() if u.end_date else "-")
            set_cell(3, f"{u.percent_complete:.0f}%")
            set_cell(4, u.main_resource or "-")

            if u.is_late:
                for col in range(5):
                    it = self.upcoming_table.item(row, col)
                    it.setBackground(QColor("#ffe5e5"))
