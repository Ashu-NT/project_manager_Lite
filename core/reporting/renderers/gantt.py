from datetime import date
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import date2num
from matplotlib import ticker

from core.services.reporting_service import GanttTaskBar


class GanttPngRenderer:
    def render(self, bars: List[GanttTaskBar], output_path: Path) -> Path:
        bars = [b for b in bars if b.start and b.end]
        if not bars:
            raise ValueError("No tasks with dates available for Gantt chart")

        bars.sort(key=lambda b: (b.start, b.end or b.start))

        names = [b.name for b in bars]
        start_nums = [date2num(b.start) for b in bars]
        durations = [(b.end - b.start).days for b in bars]
        critical = [b.is_critical for b in bars]
        pct = [b.percent_complete or 0.0 for b in bars]

        fig, ax = plt.subplots(figsize=(12, 6))

        for i, (s, d, c, p) in enumerate(zip(start_nums, durations, critical, pct)):
            ax.barh(i, d, left=s, height=0.4,
                    color="#ffcccc" if c else "#d0d0ff",
                    edgecolor="black", linewidth=0.6)
            if p > 0:
                ax.barh(i, d * p / 100.0, left=s, height=0.4,
                        color="#ff6666" if c else "#8080ff")

        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=9)
        ax.invert_yaxis()

        locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.xaxis.set_minor_locator(ticker.NullLocator())

        today = date.today()
        ax.axvline(date2num(today), color="red", linestyle="--", linewidth=1)

        ax.set_title("Project Gantt Chart")
        ax.grid(True, axis="x", linestyle=":", linewidth=0.5)

        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        plt.close(fig)

        return output_path
