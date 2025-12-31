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

        img = Image(ctx.gantt_png_path)
        img._restrictSize(720, 280)
        story.append(img)
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
