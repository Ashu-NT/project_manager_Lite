from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


class EvmCurveRenderer:
    def render(self, series, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        xs = [p.period_end for p in series]
        pv = [float(p.PV or 0.0) for p in series]
        ev = [float(p.EV or 0.0) for p in series]
        ac = [float(p.AC or 0.0) for p in series]

        fig = Figure(figsize=(9, 3))
        FigureCanvasAgg(fig)
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(xs, pv, label="PV")
        ax.plot(xs, ev, label="EV")
        ax.plot(xs, ac, label="AC")
        ax.legend()
        ax.grid(True, axis="y", linestyle=":", linewidth=0.6)

        fig.tight_layout()
        fig.savefig(output_path, dpi=150)
        fig.clear()

        return output_path
