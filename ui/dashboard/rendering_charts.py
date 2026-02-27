from __future__ import annotations

import matplotlib.dates as mdates

from core.services.dashboard import DashboardData
from ui.dashboard.widgets import ChartWidget
from ui.styles.ui_config import UIConfig as CFG

class DashboardChartsRenderingMixin:
    burndown_chart: ChartWidget
    resource_chart: ChartWidget

    def _update_burndown_chart(self, data: DashboardData):
        self.burndown_chart.ax.clear()
        pts = data.burndown
        if not pts:
            self.burndown_chart.ax.set_title("No burndown data")
            self.burndown_chart.redraw()
            return

        dates = [p.day for p in pts]
        rem = [p.remaining_tasks for p in pts]

        self.burndown_chart.ax.plot(
            dates,
            rem,
            marker="o",
            linewidth=2.2,
            markersize=4,
            color=CFG.COLOR_ACCENT,
        )
        self.burndown_chart.ax.fill_between(dates, rem, color=CFG.COLOR_ACCENT_SOFT, alpha=0.35)
        if len(dates) > 1:
            self.burndown_chart.ax.plot(
                [dates[0], dates[-1]],
                [rem[0], 0],
                linestyle="--",
                linewidth=1.1,
                color=CFG.COLOR_TEXT_MUTED,
                label="Ideal trend",
            )
        self.burndown_chart.ax.set_title("Burndown (remaining tasks)")
        self.burndown_chart.ax.set_xlabel("Date", fontsize=10)
        self.burndown_chart.ax.set_ylabel("Remaining tasks", fontsize=10)
        self.burndown_chart.ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        self.burndown_chart.ax.xaxis.set_major_formatter(
            mdates.ConciseDateFormatter(mdates.AutoDateLocator())
        )
        self.burndown_chart.fig.autofmt_xdate(rotation=25)
        self.burndown_chart.ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
        self.burndown_chart.ax.legend(loc="upper right", fontsize=8)
        self.burndown_chart.fig.tight_layout()
        self.burndown_chart.redraw()

    def _update_resource_chart(self, data: DashboardData):
        self.resource_chart.ax.clear()
        rows = data.resource_load
        if not rows:
            self.resource_chart.ax.set_title("No resource load data")
            self.resource_chart.redraw()
            return

        rows_sorted = sorted(rows, key=lambda r: r.total_allocation_percent, reverse=True)
        names = [r.resource_name for r in rows_sorted]
        allocs = [r.total_allocation_percent for r in rows_sorted]

        y = range(len(names))
        colors = [CFG.COLOR_DANGER if v > 100.0 else CFG.COLOR_ACCENT for v in allocs]
        bars = self.resource_chart.ax.barh(y, allocs, color=colors, alpha=0.9, height=0.58)

        self.resource_chart.ax.set_yticks(list(y))
        self.resource_chart.ax.set_yticklabels(names, fontsize=8)
        self.resource_chart.ax.invert_yaxis()
        self.resource_chart.ax.set_xlabel("Allocation %", fontsize=10)
        self.resource_chart.ax.set_title("Resource load")
        self.resource_chart.ax.axvline(100.0, color=CFG.COLOR_DANGER, linestyle="--", linewidth=0.8)
        self.resource_chart.ax.grid(True, axis="x", linestyle=":", linewidth=0.5, alpha=0.6)
        max_alloc = max(allocs) if allocs else 100.0
        axis_max = max(110.0, max_alloc * 1.2)
        self.resource_chart.ax.set_xlim(0.0, axis_max)
        for i, bar in enumerate(bars):
            val = allocs[i]
            x = min(val + 2.0, axis_max - 2.0)
            self.resource_chart.ax.text(
                x,
                bar.get_y() + bar.get_height() / 2.0,
                f"{val:.0f}%",
                va="center",
                ha="left",
                fontsize=8,
                color=CFG.COLOR_TEXT_SECONDARY,
            )

        self.resource_chart.fig.tight_layout()
        self.resource_chart.redraw()

    def _update_upcoming(self, data: DashboardData):
        ups = data.upcoming_tasks
        upcoming_rows = [
            {
                "name": u.name,
                "start_date": u.start_date.isoformat() if u.start_date else "-",
                "end_date": u.end_date.isoformat() if u.end_date else "-",
                "progress": f"{u.percent_complete:.0f}%",
                "resource": u.main_resource or "-",
                "is_late": bool(u.is_late),
            }
            for u in ups
        ]
        late_count = sum(1 for row in upcoming_rows if bool(row["is_late"]))
        if late_count > 0:
            badge_variant = "danger"
        elif upcoming_rows:
            badge_variant = "info"
        else:
            badge_variant = "neutral"
        self._current_upcoming_rows = upcoming_rows
        self.btn_open_upcoming.set_badge(len(upcoming_rows), badge_variant)

        dlg = getattr(self, "_upcoming_dialog", None)
        if dlg is not None and dlg.isVisible():
            dlg.set_upcoming_rows(upcoming_rows)
