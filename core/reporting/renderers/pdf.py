from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet

from core.reporting.contexts import PdfReportContext


class PdfReportRenderer:
    def render(self, ctx: PdfReportContext, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=landscape(A4),
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        story = []

        # ---------------- Title ----------------
        story.append(Paragraph(f"Project Report - {ctx.kpi.name}", styles["Title"]))
        story.append(Spacer(1, 12))

        # ---------------- Summary ----------------
        info = [
            f"Project ID: {ctx.kpi.project_id}",
            f"Start date: {ctx.kpi.start_date or '-'}",
            f"End date: {ctx.kpi.end_date or '-'}",
            f"Duration (working days): {ctx.kpi.duration_working_days}",
            f"Tasks total: {ctx.kpi.tasks_total}",
            f"Critical tasks: {ctx.kpi.critical_tasks}",
            f"Late tasks: {ctx.kpi.late_tasks}",
            f"Planned cost: {ctx.kpi.total_planned_cost:.2f}",
            f"Actual cost: {ctx.kpi.total_actual_cost:.2f}",
            f"Variance: {ctx.kpi.cost_variance:.2f}",
        ]

        for line in info:
            story.append(Paragraph(line, styles["Normal"]))

        story.append(Spacer(1, 16))

        # ---------------- Gantt ----------------
        story.append(Paragraph("Gantt Chart", styles["Heading2"]))
        story.append(Spacer(1, 8))

        if ctx.gantt_png_path and Path(ctx.gantt_png_path).exists():
            img = Image(ctx.gantt_png_path)
            img._restrictSize(720, 280)
            story.append(img)
        else:
            story.append(Paragraph("No tasks with valid dates were available for Gantt rendering.", styles["Normal"]))
        story.append(Spacer(1, 16))

        # ---------------- EVM ----------------
        if ctx.evm:
            story.append(Paragraph("Earned Value Management (EVM)", styles["Heading2"]))
            story.append(Spacer(1, 8))

            rows = [
                ["As of", ctx.as_of.isoformat()],
                ["BAC", f"{float(getattr(ctx.evm, 'BAC', 0.0) or 0.0):.2f}"],
                ["PV", f"{float(getattr(ctx.evm, 'PV', 0.0) or 0.0):.2f}"],
                ["EV", f"{float(getattr(ctx.evm, 'EV', 0.0) or 0.0):.2f}"],
                ["AC", f"{float(getattr(ctx.evm, 'AC', 0.0) or 0.0):.2f}"],
                ["SPI", f"{float(getattr(ctx.evm, 'SPI', 0.0) or 0.0):.3f}"],
                ["CPI", f"{float(getattr(ctx.evm, 'CPI', 0.0) or 0.0):.3f}"],
                ["EAC", f"{float(getattr(ctx.evm, 'EAC', 0.0) or 0.0):.2f}"],
                ["VAC", f"{float(getattr(ctx.evm, 'VAC', 0.0) or 0.0):.2f}"],
            ]

            table = Table([["Metric", "Value"]] + rows, colWidths=[180, 160])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ]))
            story.append(table)
            story.append(Spacer(1, 16))

        # ---------------- Baseline Variance ----------------
        if ctx.baseline_variance:
            story.append(Paragraph("Baseline vs Current Schedule Variance (Top 15)", styles["Heading2"]))
            story.append(Spacer(1, 8))

            data = [["Task", "Baseline Finish", "Current Finish", "Finish Var (days)", "Critical"]]
            for row in ctx.baseline_variance[:15]:
                data.append([
                    row.task_name,
                    str(row.baseline_finish or "-"),
                    str(row.current_finish or "-"),
                    "" if row.finish_variance_days is None else str(row.finish_variance_days),
                    "Yes" if getattr(row, "is_critical", False) else "No",
                ])

            table = Table(data, colWidths=[320, 110, 110, 110, 70])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ]))
            story.append(table)
            story.append(Spacer(1, 16))

        # ---------------- Cost Breakdown ----------------
        if ctx.cost_breakdown:
            story.append(Paragraph("Cost Breakdown (Planned vs Actual)", styles["Heading2"]))
            story.append(Spacer(1, 8))

            data = [["Type", "Currency", "Planned", "Actual", "Variance"]]
            for row in ctx.cost_breakdown:
                planned = float(row.planned or 0.0)
                actual = float(row.actual or 0.0)
                data.append([
                    str(row.cost_type),
                    str(row.currency),
                    f"{planned:.2f}",
                    f"{actual:.2f}",
                    f"{(actual - planned):.2f}",
                ])

            table = Table(data, colWidths=[140, 80, 120, 120, 120])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ]))
            story.append(table)
            story.append(Spacer(1, 16))

        # ---------------- Resources ----------------
        if ctx.resources:
            story.append(Paragraph("Resource Load Summary", styles["Heading2"]))
            story.append(Spacer(1, 8))

            data = [["Resource", "Allocation %", "Tasks"]]
            for r in ctx.resources:
                data.append([
                    f"{r.resource_name} ({r.resource_id})",
                    f"{r.total_allocation_percent:.1f}",
                    r.tasks_count,
                ])

            table = Table(data, colWidths=[280, 120, 80])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
                ("ALIGN", (1,1), (-1,-1), "RIGHT"),
            ]))
            story.append(table)

        doc.build(story)
        return output_path
