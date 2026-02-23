from datetime import date
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.dates import date2num
from matplotlib import ticker

from core.services.reporting import GanttTaskBar


class GanttPngRenderer:
    _STATUS_COLORS = {
        "DONE": "#16A34A",
        "IN_PROGRESS": "#2563EB",
        "BLOCKED": "#B91C1C",
        "TODO": "#64748B",
    }
    _CRITICAL_COLOR = "#DC2626"
    _CRITICAL_PROGRESS_COLOR = "#991B1B"
    _DEFAULT_PROGRESS_COLOR = "#1D4ED8"

    def _normalize_status(self, status: str | None) -> str:
        if not status:
            return "TODO"
        return status.upper().strip()

    def _status_color(self, status: str | None, is_critical: bool) -> str:
        if is_critical:
            return self._CRITICAL_COLOR
        normalized = self._normalize_status(status)
        return self._STATUS_COLORS.get(normalized, self._STATUS_COLORS["TODO"])

    @staticmethod
    def _darken(hex_color: str, ratio: float = 0.8) -> str:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return "#1D4ED8"
        r = int(int(hex_color[0:2], 16) * ratio)
        g = int(int(hex_color[2:4], 16) * ratio)
        b = int(int(hex_color[4:6], 16) * ratio)
        return f"#{r:02x}{g:02x}{b:02x}"

    def render(self, bars: List[GanttTaskBar], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        bars = [b for b in bars if b.start and b.end]
        if not bars:
            raise ValueError("No tasks with dates available for Gantt chart")

        bars.sort(key=lambda b: (b.start, b.end or b.start))

        names = [b.name.strip() or "<untitled>" for b in bars]
        start_nums = [date2num(b.start) for b in bars]
        durations = [max(1, (b.end - b.start).days + 1) for b in bars]
        critical = [b.is_critical for b in bars]
        pct = [b.percent_complete or 0.0 for b in bars]
        statuses = [b.status for b in bars]
        colors = [self._status_color(status, is_critical) for status, is_critical in zip(statuses, critical)]

        fig_height = max(5.5, 2.6 + 0.48 * len(bars))
        fig, ax = plt.subplots(figsize=(16, fig_height))
        fig.patch.set_facecolor("#F8FAFC")
        ax.set_facecolor("white")

        for i in range(len(names)):
            if i % 2 == 0:
                ax.axhspan(i - 0.5, i + 0.5, color="#F8FAFC", zorder=0)

        for i, (s, d, c, p, color) in enumerate(zip(start_nums, durations, critical, pct, colors)):
            p = max(0.0, min(100.0, float(p or 0.0)))
            ax.barh(
                i,
                d,
                left=s,
                height=0.58,
                color=color,
                edgecolor="#0F172A",
                linewidth=0.5,
                alpha=0.88,
                zorder=2,
            )
            if p > 0:
                progress_color = self._CRITICAL_PROGRESS_COLOR if c else self._darken(color, ratio=0.72)
                ax.barh(
                    i,
                    d * p / 100.0,
                    left=s,
                    height=0.32,
                    color=progress_color,
                    edgecolor="none",
                    alpha=0.95,
                    zorder=3,
                )
            if d >= 2.0:
                x_label = s + d - 0.2
                ax.text(
                    x_label,
                    i,
                    f"{p:.0f}%",
                    va="center",
                    ha="right",
                    fontsize=8,
                    color="#0F172A",
                    zorder=4,
                )

        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=9)
        ax.invert_yaxis()
        ax.tick_params(axis="y", length=0)

        min_start = min(start_nums)
        max_finish = max(s + d for s, d in zip(start_nums, durations))
        ax.set_xlim(min_start - 2.0, max_finish + 2.0)

        major_locator = mdates.MonthLocator()
        minor_locator = mdates.WeekdayLocator(byweekday=mdates.MO)
        ax.xaxis.set_major_locator(major_locator)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_minor_locator(minor_locator)
        ax.xaxis.set_minor_formatter(ticker.NullFormatter())
        ax.tick_params(axis="x", labelsize=9)

        today = date.today()
        today_num = date2num(today)
        ax.axvline(today_num, color="#DC2626", linestyle="--", linewidth=1.2, zorder=5)
        ax.text(
            today_num + 0.2,
            -0.75,
            "Today",
            color="#B91C1C",
            fontsize=8,
            va="center",
            ha="left",
            zorder=6,
        )

        ax.set_title("Project Gantt Schedule", fontsize=14, fontweight="bold", color="#0F172A", pad=14)
        ax.set_xlabel("Timeline", fontsize=10, color="#475569", labelpad=8)
        ax.grid(True, which="major", axis="x", linestyle="-", linewidth=0.6, color="#CBD5E1", alpha=0.7)
        ax.grid(True, which="minor", axis="x", linestyle=":", linewidth=0.5, color="#E2E8F0", alpha=0.9)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_color("#CBD5E1")
        ax.spines["bottom"].set_color("#CBD5E1")

        legend_handles = [
            mpatches.Patch(color=self._STATUS_COLORS["DONE"], label="Done"),
            mpatches.Patch(color=self._STATUS_COLORS["IN_PROGRESS"], label="In Progress"),
            mpatches.Patch(color=self._STATUS_COLORS["TODO"], label="Not Started"),
            mpatches.Patch(color=self._CRITICAL_COLOR, label="Critical"),
            Line2D([0], [0], color="#DC2626", linestyle="--", linewidth=1.2, label="Today"),
        ]
        ax.legend(
            handles=legend_handles,
            loc="upper left",
            bbox_to_anchor=(0.0, 1.02),
            ncol=5,
            fontsize=8,
            frameon=False,
        )

        fig.subplots_adjust(left=0.24, right=0.98, top=0.90, bottom=0.12)
        fig.savefig(output_path, dpi=220)
        plt.close(fig)

        return output_path

