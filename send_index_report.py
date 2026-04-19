#!/usr/bin/env python3
"""
send_index_report.py

Validation, rendering, and optional delivery script for the Weekly Indices Review.
"""

from __future__ import annotations

import argparse
import os
import re
import smtplib
from collections import OrderedDict
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import markdown as mdlib
from weasyprint import HTML

TITLE = "Weekly Indices Review"
DISCLAIMER_LINE = "This report is for informational and educational purposes only; please see the disclaimer at the end."
REPORT_RE = re.compile(r"^weekly_indices_review_(\d{6})(?:_(\d{2}))?\.md$")
SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.*)$")

REQUIRED_HEADINGS = [
    "# Weekly Indices Review",
    "## 1. Executive Summary",
    "## 2. Portfolio Action Snapshot",
    "## 3. Global Regime Dashboard",
    "## 4. Index Opportunity Board",
    "## 5. Key Risks / Invalidators",
    "## 6. Bottom Line",
    "## 7. Equity Curve and Portfolio Development",
    "## 8. Regional / Style Allocation Map",
    "## 9. Second-Order Effects Map",
    "## 10. Current Position Review",
    "## 11. Best New Index Opportunities",
    "## 12. Portfolio Rotation Plan",
    "## 13. Final Action Table",
    "## 14. Position Changes Executed This Run",
    "## 15. Current Portfolio Holdings and Cash",
    "## 16. Continuity Input for Next Run",
    "## 17. Disclaimer",
]

SECTION16_SENTENCE = "**This section is the canonical default input for the next run unless the user explicitly overrides it. Do not ask the user for portfolio input if this section is available.**"

BRAND = {
    "paper": "#F6F2EC",
    "surface": "#FCFAF7",
    "header": "#607887",
    "header_text": "#FBFAF7",
    "ink": "#2B3742",
    "muted": "#6B7882",
    "border": "#D9D3CB",
    "champagne": "#D4B483",
    "champagne_soft": "#EFE4D2",
    "sage": "#A4B19D",
    "terracotta": "#C99278",
}


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def strip_citations(text: str) -> str:
    text = normalize(text)
    patterns = [
        r"cite.*?",
        r"filecite.*?",
        r"\[\d+\]",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.DOTALL)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_md_inline(text: str) -> str:
    text = strip_citations(text)
    text = text.replace("**", "")
    text = text.replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


def esc(text: str) -> str:
    text = clean_md_inline(text)
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def report_sort_key(path: Path) -> tuple[str, int]:
    match = REPORT_RE.match(path.name)
    if not match:
        return ("", -1)
    return (match.group(1), int(match.group(2) or "0"))


def list_reports(output_dir: Path) -> list[Path]:
    return sorted(
        [p for p in output_dir.glob("weekly_indices_review_*.md") if REPORT_RE.match(p.name)],
        key=report_sort_key,
    )


def latest_report_file(output_dir: Path) -> Path:
    reports = list_reports(output_dir)
    if not reports:
        raise FileNotFoundError("No weekly_indices_review_*.md file found in output_indices/")
    return reports[-1]


def latest_reports_by_day(output_dir: Path) -> list[Path]:
    latest_per_day: OrderedDict[str, Path] = OrderedDict()
    for path in list_reports(output_dir):
        base_date = report_sort_key(path)[0]
        latest_per_day[base_date] = path
    return list(latest_per_day.values())


def parse_report_date(md_text: str, report_path: Optional[Path] = None) -> str:
    match = re.search(r"^#\s+Weekly Indices Review(?:\s+(\d{4}-\d{2}-\d{2}))?\s*$", md_text, flags=re.MULTILINE)
    if match and match.group(1):
        return match.group(1)
    if report_path:
        name_match = REPORT_RE.match(report_path.name)
        if name_match:
            token = name_match.group(1)
            yy, mm, dd = int(token[0:2]), int(token[2:4]), int(token[4:6])
            return f"{2000 + yy:04d}-{mm:02d}-{dd:02d}"
    return datetime.utcnow().strftime("%Y-%m-%d")


def format_full_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{dt.strftime('%A')}, {dt.day} {dt.strftime('%B %Y')}"


def extract_sections(md_text: str) -> tuple[str, list[dict]]:
    title = ""
    sections: list[dict] = []
    current = None
    for raw_line in md_text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if line.startswith("# "):
            title = clean_md_inline(line[2:])
            continue
        match = SECTION_RE.match(stripped)
        if match:
            if current:
                sections.append(current)
            current = {
                "number": int(match.group(1)),
                "raw_title": match.group(2),
                "title": clean_md_inline(match.group(2)),
                "lines": [],
            }
            continue
        if current is not None:
            current["lines"].append(line)
    if current:
        sections.append(current)
    return title, sections


def extract_section(md_text: str, title_contains: str) -> list[str]:
    _, sections = extract_sections(md_text)
    title_contains = title_contains.lower()
    for section in sections:
        if title_contains in section["title"].lower():
            return section["lines"]
    return []


def extract_label_pairs(lines: list[str]) -> list[tuple[str, str]]:
    pairs = []
    for line in lines:
        stripped = clean_md_inline(line.strip())
        if not stripped or stripped.startswith("## "):
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:]
        if ":" in stripped:
            k, v = stripped.split(":", 1)
            pairs.append((k.strip(), v.strip()))
    return pairs


def parse_numeric_value(md_text: str, label: str) -> float | None:
    pattern = rf"^- {re.escape(label)}:\s*([0-9][0-9,._%-]*)"
    match = re.search(pattern, md_text, flags=re.MULTILINE)
    if not match:
        return None
    raw = match.group(1).replace(",", "").replace("_", "").replace("%", "")
    try:
        return float(raw)
    except ValueError:
        return None


def parse_section15_totals(md_text: str) -> dict[str, float]:
    section = "\n".join(extract_section(md_text, "Current Portfolio Holdings and Cash"))
    if not section:
        return {}
    labels = [
        "Starting capital (EUR)",
        "Invested market value (EUR)",
        "Cash (EUR)",
        "Total portfolio value (EUR)",
        "Since inception return (%)",
        "EUR/USD used",
    ]
    data: dict[str, float] = {}
    for label in labels:
        value = parse_numeric_value(section, label)
        if value is not None:
            data[label] = value
    return data


def parse_section7_equity_points(md_text: str) -> list[tuple[str, float]]:
    lines = extract_section(md_text, "Equity Curve and Portfolio Development")
    if not lines:
        return []
    points: list[tuple[str, float]] = []
    in_table = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("| Date |"):
            in_table = True
            continue
        if in_table:
            if not stripped.startswith("|"):
                break
            if "---" in stripped:
                continue
            cells = [clean_md_inline(c) for c in stripped.strip("|").split("|")]
            if len(cells) < 2:
                continue
            try:
                nav = float(cells[1].replace(",", ""))
            except ValueError:
                continue
            points.append((cells[0], nav))
    return points


def validate_report(md_text: str) -> None:
    missing = [h for h in REQUIRED_HEADINGS if h not in md_text]
    if missing:
        raise RuntimeError("Report is missing required headings: " + ", ".join(missing))
    if DISCLAIMER_LINE not in md_text:
        raise RuntimeError("Disclaimer line is missing from report body.")
    if "EQUITY_CURVE_CHART_PLACEHOLDER" not in md_text:
        raise RuntimeError("Equity curve placeholder line is missing.")
    if "This report is provided for informational and educational purposes only." not in md_text:
        raise RuntimeError("Final disclaimer body is missing.")


def html_to_plain_text(html: str) -> str:
    text = re.sub(r"<style.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def plain_text_from_markdown(md_text: str) -> str:
    return html_to_plain_text(mdlib.markdown(strip_citations(md_text), extensions=["tables", "sane_lists", "fenced_code"]))


def validate_email_body(html_body: str, md_text: str | None = None) -> None:
    html_lower = html_body.lower()
    required_strings = [
        "weekly indices review",
        "executive summary",
        "portfolio action snapshot",
        "index opportunity board",
        "bottom line",
        "current portfolio holdings and cash",
        "continuity input for next run",
    ]
    for token in required_strings:
        if token.lower() not in html_lower:
            raise RuntimeError(f"HTML body is missing required content block: {token}")
    if md_text:
        plain_html = html_to_plain_text(html_body)
        plain_md = html_to_plain_text(mdlib.markdown(md_text, extensions=["tables", "sane_lists", "fenced_code"]))
        if len(plain_html) < 0.70 * len(plain_md):
            raise RuntimeError("HTML body appears too short relative to the full report.")


def write_manifest(path: Path, report_name: str, recipient: str, attachments: list[str], delivery_label: str) -> None:
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"timestamp_utc={ts}",
        f"report={report_name}",
        f"recipient={recipient}",
        f"delivery={delivery_label}",
        "html_body=full_report",
        f"pdf_attached={'yes' if any(a.lower().endswith('.pdf') for a in attachments) else 'no'}",
        "attachments=" + ", ".join(attachments),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def create_equity_curve_png(output_dir: Path, chart_path: Path, md_text: str | None = None) -> Path | None:
    points: list[tuple[str, float]] = []
    if md_text:
        points = parse_section7_equity_points(md_text)
    if not points:
        for report_path in latest_reports_by_day(output_dir):
            hist_md = report_path.read_text(encoding="utf-8")
            report_date = parse_report_date(hist_md)
            totals = parse_section15_totals(hist_md)
            nav = totals.get("Total portfolio value (EUR)")
            if nav is not None:
                points.append((report_date, nav))
    if not points:
        return None

    dates = [datetime.strptime(d, "%Y-%m-%d") for d, _ in points]
    values = [v for _, v in points]

    plt.figure(figsize=(8.8, 3.7))
    plt.plot(dates, values, marker="o", linewidth=2.2)
    plt.title("Equity Curve (EUR)")
    plt.xlabel("Date")
    plt.ylabel("Portfolio value (EUR)")
    plt.grid(True, alpha=0.28)
    plt.tight_layout()
    plt.savefig(chart_path, dpi=180)
    plt.close()
    return chart_path


def render_markdown_block(text: str, image_src: str | None = None) -> str:
    text = strip_citations(text)
    if image_src:
        text = text.replace("`EQUITY_CURVE_CHART_PLACEHOLDER`", f"![Equity curve]({image_src})")
        text = text.replace("EQUITY_CURVE_CHART_PLACEHOLDER", f"![Equity curve]({image_src})")
    else:
        text = text.replace("`EQUITY_CURVE_CHART_PLACEHOLDER`", "_Equity curve chart unavailable for this delivery._")
        text = text.replace("EQUITY_CURVE_CHART_PLACEHOLDER", "_Equity curve chart unavailable for this delivery._")
    return mdlib.markdown(text, extensions=["tables", "sane_lists", "fenced_code"])


def section_header_html(number: int, title: str) -> str:
    return (
        "<table class='section-kicker' role='presentation' cellpadding='0' cellspacing='0'><tr>"
        f"<td class='section-badge-cell'><span class='section-badge'>{number}</span></td>"
        f"<td class='section-label-cell'><span class='section-label'>{esc(title)}</span></td>"
        "</tr></table>"
    )


def parse_subsections(lines: list[str]) -> OrderedDict[str, list[str]]:
    groups: OrderedDict[str, list[str]] = OrderedDict()
    current_header = None
    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            current_header = clean_md_inline(stripped[4:])
            groups[current_header] = []
        elif stripped.startswith("- "):
            if current_header is None:
                current_header = "Items"
                groups[current_header] = []
            groups[current_header].append(clean_md_inline(stripped[2:]))
        elif re.match(r"^\d+\.\s+", stripped):
            if current_header is None:
                current_header = "Items"
                groups[current_header] = []
            groups[current_header].append(clean_md_inline(re.sub(r"^\d+\.\s+", "", stripped)))
        else:
            if current_header is None:
                current_header = "Items"
                groups[current_header] = []
            groups[current_header].append(clean_md_inline(stripped))
    return groups


def split_h3_blocks(lines: list[str]) -> list[dict[str, list[str] | str]]:
    blocks = []
    current = None
    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("### "):
            if current:
                blocks.append(current)
            current = {"title": clean_md_inline(stripped[4:]), "lines": []}
        elif current is not None:
            current["lines"].append(raw)
    if current:
        blocks.append(current)
    return blocks


def render_executive_summary(section: dict) -> str:
    pairs = extract_label_pairs(section["lines"])
    if not pairs:
        body = render_markdown_block("\n".join(section["lines"]))
        return f"<div class='panel panel-exec'>{section_header_html(section['number'], section['title'])}{body}</div>"

    body_parts = []
    for key, value in pairs:
        if key in {"Primary regime", "Secondary cross-current", "Geopolitical regime", "Main takeaway"}:
            continue
        body_parts.append(
            f"<div class='summary-line'><div class='summary-key'>{esc(key)}</div><div class='summary-value'>{esc(value)}</div></div>"
        )

    takeaway = next((v for k, v in pairs if k.lower() == "main takeaway"), "")
    takeaway_html = (
        f"<div class='takeaway'><div class='takeaway-label'>Main takeaway</div><div class='takeaway-text'>{esc(takeaway)}</div></div>"
        if takeaway else ""
    )

    return (
        f"<div class='panel panel-exec'>"
        f"{section_header_html(section['number'], section['title'])}"
        f"{''.join(body_parts)}"
        f"{takeaway_html}"
        f"</div>"
    )


def render_action_snapshot(section: dict) -> str:
    groups = parse_subsections(section["lines"])
    order = ["Add", "Hold", "Hold but replaceable", "Reduce", "Close"]
    rows = []
    for label in order:
        items = groups.get(label, [])
        val_html = ", ".join(esc(item) for item in items) if items else "None"
        rows.append(f"<tr><th>{esc(label)}</th><td>{val_html}</td></tr>")

    def block(title: str) -> str:
        items = groups.get(title, [])
        if not items:
            return ""
        list_html = "".join(f"<li>{esc(item)}</li>" for item in items)
        return f"<div class='subblock'><div class='subblock-title'>{esc(title)}</div><ul>{list_html}</ul></div>"

    return (
        f"<div class='panel panel-snapshot'>"
        f"{section_header_html(section['number'], section['title'])}"
        f"<table class='snapshot-table'><thead><tr><th>Recommendation</th><th>Tickers / notes</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
        f"{block('Best replacements to fund')}"
        f"<div class='subgrid'>{block('Top 3 actions this week')}{block('Top 3 risks this week')}</div>"
        f"</div>"
    )


def render_standard_panel(section: dict, image_src: str | None = None, extra_class: str = "") -> str:
    body = render_markdown_block("\n".join(section["lines"]), image_src=image_src)
    return f"<div class='panel {extra_class}'>{section_header_html(section['number'], section['title'])}{body}</div>"


def render_position_review(section: dict) -> str:
    blocks = split_h3_blocks(section["lines"])
    cards = []
    for block in blocks:
        block_html = render_markdown_block("\n".join(block["lines"]))
        cards.append(
            f"<article class='position-card'>"
            f"<div class='position-card-title'>{esc(str(block['title']))}</div>"
            f"<div class='position-card-body'>{block_html}</div>"
            f"</article>"
        )
    return f"<div class='panel panel-positions'>{section_header_html(section['number'], section['title'])}{''.join(cards)}</div>"


def render_carry_panel(section: dict) -> str:
    visible_lines = []
    hidden_sentence = clean_md_inline(SECTION16_SENTENCE)
    for raw in section["lines"]:
        if clean_md_inline(raw.strip()) == hidden_sentence:
            continue
        visible_lines.append(raw)
    body = render_markdown_block("\n".join(visible_lines))
    return f"<div class='panel panel-carry'>{section_header_html(section['number'], section['title'])}{body}</div>"


def build_report_html(md_text: str, report_date_str: str, image_src: str | None = None, render_mode: str = "email") -> str:
    _, sections = extract_sections(md_text)
    sections_by_number = {s["number"]: s for s in sections}
    display_date_str = format_full_date(report_date_str)

    exec_pairs = OrderedDict(extract_label_pairs(sections_by_number.get(1, {}).get("lines", [])))
    primary_regime = exec_pairs.get("Primary regime", "Pending classification")
    geo_regime = exec_pairs.get("Geopolitical regime", "Pending classification")
    main_takeaway = exec_pairs.get("Main takeaway", "Keep the current allocation disciplined.")

    intro_cards = (
        f"<div class='mini-card'><div class='mini-label'>Primary regime</div><div class='mini-value'>{esc(primary_regime)}</div></div>"
        f"<div class='mini-card'><div class='mini-label'>Geopolitical regime</div><div class='mini-value'>{esc(geo_regime)}</div></div>"
        f"<div class='mini-card'><div class='mini-label'>Main takeaway</div><div class='mini-value'>{esc(main_takeaway)}</div></div>"
    )

    client_grid = []
    if 1 in sections_by_number:
        client_grid.append(render_executive_summary(sections_by_number[1]))
    if 2 in sections_by_number:
        client_grid.append(render_action_snapshot(sections_by_number[2]))

    client_panels = []
    panel_map = {
        3: "panel-regime",
        4: "panel-radar",
        5: "panel-risks panel-compact",
        6: "panel-bottomline panel-compact",
        7: "panel-equity",
    }
    for number in [3, 4, 5, 6, 7]:
        if number in sections_by_number:
            img_src = image_src if number == 7 else None
            client_panels.append(render_standard_panel(sections_by_number[number], image_src=img_src, extra_class=panel_map.get(number, "")))

    analyst_panels = []
    for number in range(8, 18):
        if number not in sections_by_number:
            continue
        if number == 10:
            analyst_panels.append(render_position_review(sections_by_number[number]))
        elif number == 16:
            analyst_panels.append(render_carry_panel(sections_by_number[number]))
        else:
            analyst_panels.append(render_standard_panel(sections_by_number[number]))

    css_common = f"""
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 0;
      background: {BRAND['paper']};
      color: {BRAND['ink']};
      font-family: Arial, Helvetica, sans-serif;
      -webkit-font-smoothing: antialiased;
    }}
    .report-shell {{ max-width: 1180px; margin: 0 auto; padding: 0 0 18px 0; }}
    .hero {{ background: {BRAND['header']}; color: {BRAND['header_text']}; padding: 20px 24px 18px 24px; border-radius: 14px 14px 0 0; }}
    .hero-secondary {{ margin-top: 26px; }}
    .hero-table {{ width: 100%; border-collapse: collapse; }}
    .hero-table td {{ vertical-align: middle; }}
    .hero-left {{ text-align: left; }}
    .hero-right {{ text-align: right; white-space: nowrap; padding-left: 24px; }}
    .masthead {{ font-family: Georgia, 'Times New Roman', serif; font-weight: 700; font-size: 30px; letter-spacing: 1px; margin: 0 0 8px 0; text-transform: uppercase; }}
    .hero-sub {{ font-size: 14px; color: #EFF4F6; margin: 0; }}
    .hero-side-label {{ font-size: 16px; line-height: 1.2; font-weight: 700; color: {BRAND['header_text']}; letter-spacing: .03em; }}
    .hero-rule {{ height: 5px; background: {BRAND['champagne']}; margin: 8px 0 18px 0; border-radius: 999px; }}
    .notice {{ background: #F8F4EE; border: 1px solid {BRAND['border']}; color: {BRAND['muted']}; border-radius: 14px; padding: 12px 16px; font-size: 12px; margin: 0 0 18px 0; }}
    .summary-strip {{ display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: 14px; margin: 0 0 18px 0; }}
    .mini-card {{ background: {BRAND['surface']}; border: 1px solid {BRAND['border']}; border-radius: 16px; padding: 14px 18px; }}
    .mini-label {{ font-size: 11px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: {BRAND['muted']}; margin: 0 0 8px 0; }}
    .mini-value {{ font-family: Georgia, 'Times New Roman', serif; font-weight: 700; font-size: 22px; color: {BRAND['ink']}; line-height: 1.22; }}
    .client-grid {{ display: grid; grid-template-columns: 1.35fr 1fr; gap: 18px; align-items: start; margin: 0 0 18px 0; }}
    .panel {{ background: {BRAND['surface']}; border: 1px solid {BRAND['border']}; border-radius: 18px; padding: 16px 18px; margin: 0 0 18px 0; }}
    .section-kicker {{ width: auto; border-collapse: collapse; margin: 0 0 18px 0; }}
    .section-kicker td {{ vertical-align: middle; }}
    .section-badge-cell {{ width: 64px; padding: 0 16px 0 0; }}
    .section-badge {{ width: 46px; height: 46px; border-radius: 999px; background: #2A5384; color: #ffffff; font-weight: 700; font-size: 17px; display: block; text-align: center; line-height: 46px; font-family: Arial, Helvetica, sans-serif; }}
    .section-label {{ display: block; font-size: 15px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: {BRAND['muted']}; line-height: 1.12; }}
    .summary-line {{ margin: 0 0 12px 0; padding: 0 0 12px 0; border-bottom: 1px solid {BRAND['border']}; }}
    .summary-key {{ color: {BRAND['muted']}; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; margin: 0 0 6px 0; }}
    .summary-value {{ color: {BRAND['ink']}; font-size: 14px; line-height: 1.55; }}
    .takeaway {{ margin: 18px 0 0 0; padding: 14px 16px; border-radius: 12px; background: #F4EEE4; border: 1px solid #E7D7BB; }}
    .takeaway-label {{ color: {BRAND['muted']}; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; margin: 0 0 6px 0; }}
    .takeaway-text {{ color: {BRAND['ink']}; font-size: 17px; font-weight: 700; line-height: 1.42; }}
    .snapshot-table {{ width: 100%; border-collapse: collapse; margin: 0 0 16px 0; border: 1px solid {BRAND['border']}; table-layout: fixed; }}
    .snapshot-table th {{ background: #F2EBDD; color: {BRAND['ink']}; text-align: left; padding: 9px 10px; border-bottom: 1px solid {BRAND['border']}; font-size: 13px; font-weight: 700; }}
    .snapshot-table td {{ padding: 9px 10px; border-bottom: 1px solid #ECE6DE; vertical-align: top; font-size: 14px; line-height: 1.5; word-break: break-word; }}
    .snapshot-table tbody tr:nth-child(even) td {{ background: #FEFCF9; }}
    .subgrid {{ display: grid; grid-template-columns: 1fr; gap: 14px; }}
    .subblock {{ margin: 0 0 14px 0; padding: 12px 14px; background: #FBF7F0; border: 1px solid {BRAND['border']}; border-radius: 12px; }}
    .subblock-title {{ color: {BRAND['muted']}; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .06em; margin: 0 0 8px 0; }}
    .subblock ul {{ margin: 0; padding-left: 18px; }}
    .panel p, .panel li {{ font-size: 14px; line-height: 1.58; margin-top: 0; font-weight: 400; }}
    .panel strong {{ font-weight: 700; }}
    .panel ul, .panel ol {{ margin-top: 0; padding-left: 22px; }}
    .panel h3 {{ color: {BRAND['ink']}; font-size: 18px; font-weight: 700; line-height: 1.35; margin: 18px 0 10px 0; }}
    .panel h4 {{ color: {BRAND['muted']}; font-size: 11px; text-transform: uppercase; letter-spacing: .08em; font-weight: 700; margin: 18px 0 8px 0; }}
    .panel table {{ width: 100%; border-collapse: collapse; table-layout: fixed; margin: 12px 0 14px 0; border: 1px solid {BRAND['border']}; font-size: 12px; }}
    .panel th {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid {BRAND['border']}; background: #F2EBDD; color: {BRAND['ink']}; vertical-align: middle; font-size: 12px; font-weight: 700; }}
    .panel td {{ padding: 8px 10px; border-bottom: 1px solid #ECE6DE; vertical-align: top; word-wrap: break-word; }}
    .panel tr:nth-child(even) td {{ background: #FEFCF9; }}
    .panel img {{ max-width: 100%; height: auto; border: 1px solid {BRAND['border']}; border-radius: 10px; margin: 10px 0 4px 0; display: block; }}
    .position-card {{ margin: 0 0 16px 0; padding: 14px 16px; border: 1px solid {BRAND['border']}; background: #FBF7F0; border-radius: 14px; }}
    .position-card-title {{ font-size: 17px; font-weight: 700; color: {BRAND['ink']}; margin: 0 0 10px 0; }}
    .position-card-body table {{ margin-top: 10px; }}
    a {{ color: #315F8B; text-decoration: underline; }}
    """

    email_css = """
    @media screen and (max-width: 1100px) {
      .summary-strip, .client-grid, .subgrid { display: block; }
      .hero-table, .hero-table tbody, .hero-table tr, .hero-table td { display: block; width: 100%; }
      .hero-right { text-align: left; padding-left: 0; padding-top: 10px; }
      .mini-card, .panel { margin-bottom: 16px; }
      .panel table, .snapshot-table { table-layout: auto; }
    }
    """

    pdf_css = """
    @page { size: A4 landscape; margin: 12mm; }
    body { background: #ffffff; }
    .report-shell { max-width: none; padding-bottom: 0; }
    .hero, .notice, .mini-card, .panel { page-break-inside: avoid; break-inside: avoid-page; }
    .client-grid { display: block; margin-bottom: 8px; }
    .summary-strip { gap: 12px; }
    .panel { border-radius: 14px; padding: 16px 18px; margin-bottom: 14px; }
    .panel table, .snapshot-table { table-layout: auto; font-size: 11px; }
    .panel th, .panel td, .snapshot-table th, .snapshot-table td { padding: 6px 8px; }
    .subgrid { display: block; }
    .panel img { max-height: 170mm; object-fit: contain; }
    """

    mode_css = email_css if render_mode == "email" else pdf_css

    analyst_appendix = ""
    if analyst_panels:
        analyst_appendix = (
            f"<div class='hero hero-secondary'><table class='hero-table' role='presentation' cellpadding='0' cellspacing='0'><tr>"
            f"<td class='hero-left'><div class='masthead'>WEEKLY INDICES REVIEW</div><p class='hero-sub'>{esc(display_date_str)}</p></td>"
            f"<td class='hero-right'><div class='hero-side-label'>Analyst Report</div></td>"
            f"</tr></table></div><div class='hero-rule'></div>"
            + "".join(analyst_panels)
        )

    return f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <style>{css_common}{mode_css}</style>
      </head>
      <body>
        <div class="report-shell">
          <div class="hero">
            <table class="hero-table" role="presentation" cellpadding="0" cellspacing="0"><tr>
              <td class="hero-left"><div class="masthead">WEEKLY INDICES REVIEW</div><p class="hero-sub">{esc(display_date_str)}</p></td>
              <td class="hero-right"><div class="hero-side-label">Investor Report</div></td>
            </tr></table>
          </div>
          <div class="hero-rule"></div>
          <div class="notice">{esc(DISCLAIMER_LINE)}</div>
          <div class="summary-strip">{intro_cards}</div>
          <div class="client-grid">{''.join(client_grid)}</div>
          <div class="report-stack">{''.join(client_panels)}{analyst_appendix}</div>
        </div>
      </body>
    </html>
    """.strip()


def generate_delivery_assets(output_dir: Path, report_path: Path) -> dict:
    original_md_text = normalize(report_path.read_text(encoding="utf-8"))
    md_text_clean = strip_citations(original_md_text)
    validate_report(md_text_clean)
    report_date = parse_report_date(md_text_clean, report_path)

    clean_md_path = report_path.with_name(report_path.stem + "_clean.md")
    clean_md_path.write_text(md_text_clean, encoding="utf-8")

    equity_curve_png = report_path.with_name(report_path.stem + "_equity_curve.png")
    create_equity_curve_png(output_dir, equity_curve_png, md_text=md_text_clean)
    image_src_pdf = equity_curve_png.resolve().as_uri() if equity_curve_png.exists() else None
    image_src_email = "cid:equitycurve" if equity_curve_png.exists() else None

    html_email = build_report_html(md_text_clean, report_date, image_src=image_src_email, render_mode="email")
    html_pdf = build_report_html(md_text_clean, report_date, image_src=image_src_pdf, render_mode="pdf")

    validate_email_body(html_email, md_text_clean)

    html_path = report_path.with_name(report_path.stem + "_delivery.html")
    pdf_path = report_path.with_name(report_path.stem + ".pdf")
    html_path.write_text(html_email, encoding="utf-8")
    HTML(string=html_pdf, base_url=str(output_dir)).write_pdf(str(pdf_path))

    if not pdf_path.exists() or pdf_path.stat().st_size <= 0:
        raise RuntimeError("PDF was not created correctly.")

    return {
        "report_path": report_path,
        "clean_md_path": clean_md_path,
        "equity_curve_png": equity_curve_png,
        "html_path": html_path,
        "pdf_path": pdf_path,
        "html": html_email,
        "md_text_clean": md_text_clean,
        "report_date": report_date,
    }


def maybe_send_email(assets: dict) -> tuple[bool, list[str], str]:
    required = [
        "MRKT_RPRTS_SMTP_HOST",
        "MRKT_RPRTS_SMTP_PORT",
        "MRKT_RPRTS_SMTP_USER",
        "MRKT_RPRTS_SMTP_PASS",
        "MRKT_RPRTS_MAIL_FROM",
        "MRKT_RPRTS_MAIL_TO",
    ]
    if any(not os.environ.get(k) for k in required):
        return False, [], "delivery_skipped_missing_env"

    host = os.environ["MRKT_RPRTS_SMTP_HOST"]
    port = int(os.environ["MRKT_RPRTS_SMTP_PORT"])
    user = os.environ["MRKT_RPRTS_SMTP_USER"]
    password = os.environ["MRKT_RPRTS_SMTP_PASS"]
    mail_from = os.environ["MRKT_RPRTS_MAIL_FROM"]
    mail_to = os.environ["MRKT_RPRTS_MAIL_TO"]
    subject_prefix = os.environ.get("MRKT_RPRTS_SUBJECT_PREFIX", TITLE)

    root = MIMEMultipart("mixed")
    root["Subject"] = f"{subject_prefix} {assets['report_date']}"
    root["From"] = mail_from
    root["To"] = mail_to

    related = MIMEMultipart("related")
    alternative = MIMEMultipart("alternative")
    alternative.attach(MIMEText(plain_text_from_markdown(assets["md_text_clean"]), "plain", "utf-8"))
    alternative.attach(MIMEText(assets["html"], "html", "utf-8"))
    related.attach(alternative)

    attachments = [assets["pdf_path"].name, assets["clean_md_path"].name, assets["html_path"].name]

    if assets["equity_curve_png"].exists():
        png_bytes = assets["equity_curve_png"].read_bytes()
        inline_png = MIMEImage(png_bytes, _subtype="png")
        inline_png.add_header("Content-ID", "<equitycurve>")
        inline_png.add_header("Content-Disposition", "inline", filename=assets["equity_curve_png"].name)
        related.attach(inline_png)

        png_attachment = MIMEApplication(png_bytes, _subtype="png")
        png_attachment.add_header("Content-Disposition", "attachment", filename=assets["equity_curve_png"].name)
        root.attach(png_attachment)
        attachments.append(assets["equity_curve_png"].name)

    root.attach(related)

    for path in [assets["pdf_path"], assets["clean_md_path"], assets["html_path"]]:
        subtype = "pdf" if path.suffix == ".pdf" else ("html" if path.suffix == ".html" else "plain")
        with path.open("rb") as fh:
            part = MIMEApplication(fh.read(), _subtype=subtype)
        part.add_header("Content-Disposition", "attachment", filename=path.name)
        root.attach(part)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(mail_from, [mail_to], root.as_string())

    return True, attachments, mail_to


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--report-path", default=None, help="Optional explicit report markdown path")
    args = parser.parse_args()

    output_dir = Path("output_indices")
    latest = Path(args.report_path) if args.report_path else latest_report_file(output_dir)
    if not latest.exists():
        raise FileNotFoundError(f"Explicit report path does not exist: {latest}")
    assets = generate_delivery_assets(output_dir, latest)
    manifest_path = latest.with_name(latest.stem + "_delivery_manifest.txt")

    if args.validate_only:
        write_manifest(manifest_path, latest.name, "validation_only", [assets["html_path"].name, assets["pdf_path"].name], "validation_only")
        print(f"VALIDATION_OK | report={latest.name} | manifest={manifest_path.name}")
        return

    sent, attachment_names, recipient = maybe_send_email(assets)
    if sent:
        write_manifest(manifest_path, latest.name, recipient, attachment_names, "delivery_ok")
        print(f"DELIVERY_OK | report={latest.name} | recipient={recipient} | manifest={manifest_path.name}")
    else:
        write_manifest(manifest_path, latest.name, recipient, [assets['html_path'].name, assets['pdf_path'].name], recipient)
        print(f"RENDER_OK | report={latest.name} | delivery={recipient} | manifest={manifest_path.name}")


if __name__ == "__main__":
    main()
