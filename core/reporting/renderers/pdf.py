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

        # ---------------- Cost Sources ----------------
        if ctx.cost_sources:
            story.append(Paragraph("Cost Sources (Policy Applied)", styles["Heading2"]))
            story.append(Spacer(1, 8))

            data = [["Source", "Planned", "Committed", "Actual"]]
            for src in ctx.cost_sources.rows:
                data.append([
                    str(src.source_label),
                    f"{float(src.planned or 0.0):.2f}",
                    f"{float(src.committed or 0.0):.2f}",
                    f"{float(src.actual or 0.0):.2f}",
                ])

            table = Table(data, colWidths=[200, 120, 120, 120])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ]))
            story.append(table)
            if ctx.cost_sources.notes:
                story.append(Spacer(1, 6))
                for note in ctx.cost_sources.notes:
                    story.append(Paragraph(note, styles["Normal"]))
            story.append(Spacer(1, 16))

        # ---------------- Finance ----------------
        if ctx.finance_snapshot:
            snap = ctx.finance_snapshot
            story.append(Paragraph("Finance Summary", styles["Heading2"]))
            story.append(Spacer(1, 8))

            summary_rows = [
                ["Metric", "Value"],
                ["Budget", f"{float(snap.budget or 0.0):.2f}"],
                ["Planned", f"{float(snap.planned or 0.0):.2f}"],
                ["Committed", f"{float(snap.committed or 0.0):.2f}"],
                ["Actual", f"{float(snap.actual or 0.0):.2f}"],
                ["Exposure", f"{float(snap.exposure or 0.0):.2f}"],
                [
                    "Available",
                    "-" if snap.available is None else f"{float(snap.available or 0.0):.2f}",
                ],
            ]
            table = Table(summary_rows, colWidths=[180, 140])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ]))
            story.append(table)
            story.append(Spacer(1, 12))

            if snap.cashflow:
                story.append(Paragraph("Cashflow / Forecast by Period (Top 18)", styles["Heading3"]))
                story.append(Spacer(1, 6))
                cash_rows = [["Period", "Planned", "Committed", "Actual", "Forecast", "Exposure"]]
                for p in snap.cashflow[:18]:
                    cash_rows.append([
                        p.period_key,
                        f"{float(p.planned or 0.0):.2f}",
                        f"{float(p.committed or 0.0):.2f}",
                        f"{float(p.actual or 0.0):.2f}",
                        f"{float(p.forecast or 0.0):.2f}",
                        f"{float(p.exposure or 0.0):.2f}",
                    ])
                table = Table(cash_rows, colWidths=[90, 90, 90, 90, 90, 90])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ]))
                story.append(table)
                story.append(Spacer(1, 10))

            if snap.by_source:
                story.append(Paragraph("Expense Analytics by Source", styles["Heading3"]))
                story.append(Spacer(1, 6))
                source_rows = [["Source", "Planned", "Committed", "Actual", "Forecast", "Exposure"]]
                for row in snap.by_source:
                    source_rows.append([
                        row.label,
                        f"{float(row.planned or 0.0):.2f}",
                        f"{float(row.committed or 0.0):.2f}",
                        f"{float(row.actual or 0.0):.2f}",
                        f"{float(row.forecast or 0.0):.2f}",
                        f"{float(row.exposure or 0.0):.2f}",
                    ])
                table = Table(source_rows, colWidths=[180, 85, 85, 85, 85, 85])
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
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
