"""PDF report generator (ReportLab, pure-Python, no system dependencies)."""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.reports.models import SecurityReport

_SEVERITY_COLORS = {
    "critical": colors.HexColor("#e11d48"),
    "high": colors.HexColor("#ea580c"),
    "medium": colors.HexColor("#ca8a04"),
    "low": colors.HexColor("#0284c7"),
    "informational": colors.HexColor("#64748b"),
}


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontSize=20, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontSize=14, spaceBefore=12, spaceAfter=6),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontSize=9.5, leading=13),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontSize=8, textColor=colors.HexColor("#475569")),
        "mono": ParagraphStyle("mono", parent=base["BodyText"], fontName="Courier", fontSize=7.5, leading=10),
    }


def build(report: SecurityReport) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=report.title,
    )
    s = _styles()
    result = report.result
    story: list = []

    story.append(Paragraph(report.title, s["title"]))
    story.append(Paragraph(f"Generated {report.generated_at} &middot; Report ID {report.report_id}", s["small"]))
    story.append(Spacer(1, 8))

    # Risk
    if result.risk:
        story.append(Paragraph("Overall risk", s["h2"]))
        risk_table = Table(
            [
                ["Score", f"{result.risk.score}/100"],
                ["Classification", result.risk.classification],
            ],
            colWidths=[40 * mm, 120 * mm],
        )
        risk_table.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story.append(risk_table)
        story.append(Spacer(1, 4))
        for line in result.risk.explanation:
            story.append(Paragraph(f"&bull; {_esc(line)}", s["body"]))

    # Token info
    story.append(Paragraph("Token information", s["h2"]))
    token = result.token
    rows = [
        ["Name", token.metadata.name if token else "n/a"],
        ["Symbol", token.metadata.symbol if token else "n/a"],
        ["Address", result.token_address],
        ["Chain", f"{token.chain_name if token else result.chain_id} (chain id {result.chain_id})"],
        ["Decimals", str(token.metadata.decimals) if token else "n/a"],
        ["Total supply", str(token.metadata.total_supply) if token else "n/a"],
        ["Owner", token.owner if token and token.owner else "none detected"],
        ["Contract type", token.contract_type.value if token else "unknown"],
        ["Proxy", ("yes - " + (token.proxy.proxy_type or "")) if token and token.proxy.is_proxy else "no"],
        ["Verified source", str(token.is_verified) if token else "unknown"],
        ["Analysis block", str(result.block_number) if result.block_number is not None else "n/a"],
    ]
    info_table = Table(rows, colWidths=[45 * mm, 115 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#475569")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
            ]
        )
    )
    story.append(info_table)

    # Simulation
    if result.simulation:
        story.append(Paragraph("Buy / sell simulation", s["h2"]))
        if result.simulation.performed:
            sim_rows = [["Scenario", "Wallet", "Buy", "Buy tax", "Sell", "Sell tax"]]
            for sc in result.simulation.scenarios:
                sim_rows.append(
                    [
                        sc.name,
                        sc.wallet[:10] + "...",
                        "ok" if sc.buy_result.success else "FAIL",
                        f"{sc.buy_tax_bps / 100:.2f}%" if sc.buy_tax_bps is not None else "-",
                        "ok" if sc.sell_result and sc.sell_result.success else "FAIL",
                        f"{sc.sell_tax_bps / 100:.2f}%" if sc.sell_tax_bps is not None else "-",
                    ]
                )
            t = Table(sim_rows, colWidths=[25 * mm, 30 * mm, 20 * mm, 25 * mm, 25 * mm, 25 * mm])
            t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0"))]))
            story.append(t)
            story.append(Spacer(1, 4))
            buy_tax = result.simulation.buy_tax_bps
            sell_tax = result.simulation.sell_tax_bps
            story.append(
                Paragraph(
                    f"Effective buy tax: {buy_tax / 100:.2f}% &middot; Effective sell tax: "
                    f"{sell_tax / 100:.2f}%" if buy_tax is not None and sell_tax is not None
                    else "Effective taxes: inconclusive",
                    s["body"],
                )
            )
            for lim in result.simulation.limitations:
                story.append(Paragraph(f"&bull; {_esc(lim)}", s["small"]))
        else:
            story.append(Paragraph(_esc(result.simulation.reason or "not performed"), s["body"]))

    story.append(PageBreak())
    story.append(Paragraph(f"Security findings ({len(result.findings)})", s["h2"]))
    for f in result.findings:
        color = _SEVERITY_COLORS.get(f.severity.value, colors.grey)
        title = Paragraph(
            f'<font color="{color.hexval()}"><b>[{f.severity.value.upper()}]</b></font> '
            f"<b>{_esc(f.title)}</b> "
            f'<font size="7" color="#64748b">({f.confidence.value}, {f.source.value}, {f.category.value})</font>',
            s["body"],
        )
        story.append(title)
        story.append(Paragraph(_esc(f.description), s["body"]))
        if f.impact:
            story.append(Paragraph(f"<i>Impact:</i> {_esc(f.impact)}", s["small"]))
        if f.recommendation:
            story.append(Paragraph(f"<i>Mitigation:</i> {_esc(f.recommendation)}", s["small"]))
        story.append(Spacer(1, 6))

    if result.risk and result.risk.uncertainties:
        story.append(Paragraph("Unresolved uncertainties", s["h2"]))
        for u in result.risk.uncertainties:
            story.append(Paragraph(f"&bull; {_esc(u)}", s["small"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Disclaimer", s["h2"]))
    story.append(Paragraph(_esc(report.disclaimer), s["small"]))

    doc.build(story)
    return buf.getvalue()


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
