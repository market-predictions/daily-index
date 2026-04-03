#!/usr/bin/env python3
"""
send_aex_options_report.py

Validation, rendering, and optional delivery script for the Weekly AEX Option Review.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import markdown as mdlib
from weasyprint import HTML

TITLE = "Weekly AEX Option Review"
DISCLAIMER_LINE = "This report is for informational and educational purposes only; please see the disclaimer at the end."
REPORT_RE = re.compile(r"^weekly_aex_option_review_(\d{6})(?:_(\d{2}))?\.md$")

REQUIRED_HEADINGS = [
    "# Weekly AEX Option Review",
    "## 1. Executive summary",
    "## 2. Tradeable pricing snapshot",
    "## 3. Primary decision",
    "## 4. Watchlist and approved structures",
    "## 5. Why the top structure is not yet approved",
    "## 6. Market context appendix",
    "## 7. Portfolio and risk appendix",
    "## 8. Source receipt appendix",
    "## 9. Disclaimer",
]

BRAND = {
    "paper": "#F6F2EC",
    "surface": "#FCFAF7",
    "header": "#607887",
    "header_text": "#FBFAF7",
    "ink": "#2B3742",
    "muted": "#6B7882",
    "border": "#D9D3CB",
    "accent": "#D4B483",
}


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def report_sort_key(path: Path) -> tuple[str, int]:
    match = REPORT_RE.match(path.name)
    if not match:
        return ("", -1)
    return (match.group(1), int(match.group(2) or "0"))


def list_reports(output_dir: Path) -> list[Path]:
    return sorted(
        [p for p in output_dir.glob("weekly_aex_option_review_*.md") if REPORT_RE.match(p.name)],
        key=report_sort_key,
    )


def latest_report_file(output_dir: Path) -> Path:
    reports = list_reports(output_dir)
    if not reports:
        raise FileNotFoundError("No weekly_aex_option_review_*.md file found in output_aex/")
    return reports[-1]


def parse_report_date(md_text: str, report_path: Optional[Path] = None) -> str:
    match = re.search(r"^#\s+Weekly AEX Option Review(?:\s+(\d{4}-\d{2}-\d{2}))?\s*$", md_text, flags=re.MULTILINE)
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


def validate_report(md_text: str) -> None:
    missing = [h for h in REQUIRED_HEADINGS if h not in md_text]
    if missing:
        raise RuntimeError("Report is missing required headings: " + ", ".join(missing))
    if DISCLAIMER_LINE not in md_text:
        raise RuntimeError("Disclaimer line is missing from report body.")


def expected_trade_plan_path(report_path: Path) -> Path:
    stem = report_path.stem.replace("weekly_aex_option_review_", "aex_option_trade_plan_")
    return report_path.with_name(stem + ".json")


def validate_trade_plan(plan_path: Path) -> dict:
    if not plan_path.exists():
        raise FileNotFoundError(f"Missing machine trade plan: {plan_path.name}")
    data = json.loads(plan_path.read_text(encoding="utf-8"))
    required = [
        "report_date",
        "approval_status",
        "automation_level",
        "directional_regime",
        "options_regime",
        "primary_decision",
        "structures_considered",
        "approved_structures",
        "timing_gate_status",
        "freshness_summary",
        "risk_budget_summary",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        raise RuntimeError("Trade plan is missing required keys: " + ", ".join(missing))
    if data.get("primary_decision") == "NO_TRADE" and not data.get("no_trade_reason"):
        raise RuntimeError("Trade plan says NO_TRADE but no_trade_reason is missing.")
    return data


def html_shell(inner_html: str, date_str: str) -> str:
    full_date = format_full_date(date_str)
    return f"""
    <html>
      <head>
        <meta charset=\"utf-8\" />
        <style>
          body {{
            margin: 0;
            padding: 0;
            background: {BRAND['paper']};
            color: {BRAND['ink']};
            font-family: Arial, Helvetica, sans-serif;
          }}
          .shell {{
            max-width: 1080px;
            margin: 0 auto;
            padding: 0 0 18px 0;
          }}
          .hero {{
            background: {BRAND['header']};
            color: {BRAND['header_text']};
            padding: 22px 24px 18px 24px;
            border-radius: 14px 14px 0 0;
          }}
          .masthead {{
            font-family: Georgia, \"Times New Roman\", serif;
            font-size: 30px;
            font-weight: 700;
            text-transform: uppercase;
            margin: 0 0 8px 0;
          }}
          .sub {{ margin: 0; font-size: 14px; }}
          .rule {{ height: 5px; background: {BRAND['accent']}; border-radius: 999px; margin: 8px 0 18px 0; }}
          .notice {{ background: #F8F4EE; border: 1px solid {BRAND['border']}; color: {BRAND['muted']}; border-radius: 14px; padding: 12px 16px; font-size: 12px; margin-bottom: 18px; }}
          .panel {{ background: {BRAND['surface']}; border: 1px solid {BRAND['border']}; border-radius: 18px; padding: 18px 20px; }}
          .panel h1 {{ display: none; }}
          .panel h2 {{ color: {BRAND['muted']}; font-size: 14px; text-transform: uppercase; letter-spacing: .06em; margin-top: 26px; }}
          .panel h2:first-of-type {{ margin-top: 0; }}
          .panel h3 {{ color: {BRAND['ink']}; font-size: 15px; margin-top: 18px; }}
          .panel p, .panel li {{ line-height: 1.58; font-size: 14px; }}
          .panel table {{ width: 100%; border-collapse: collapse; margin: 12px 0 16px 0; font-size: 12px; }}
          .panel th, .panel td {{ border: 1px solid {BRAND['border']}; padding: 8px 10px; text-align: left; vertical-align: top; }}
          .panel th {{ background: #F2EBDD; }}
          @page {{ size: A4 portrait; margin: 12mm; }}
        </style>
      </head>
      <body>
        <div class=\"shell\">
          <div class=\"hero\">
            <div class=\"masthead\">WEEKLY AEX OPTION REVIEW</div>
            <p class=\"sub\">{full_date}</p>
          </div>
          <div class=\"rule\"></div>
          <div class=\"notice\">{DISCLAIMER_LINE}</div>
          <div class=\"panel\">{inner_html}</div>
        </div>
      </body>
    </html>
    """.strip()


def markdown_to_html(md_text: str, report_date: str) -> str:
    body_html = mdlib.markdown(md_text, extensions=["tables", "sane_lists", "fenced_code"])
    return html_shell(body_html, report_date)


def write_manifest(path: Path, report_name: str, trade_plan_name: str, recipient: str, attachments: list[str]) -> None:
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"timestamp_utc={ts}",
        f"report={report_name}",
        f"trade_plan={trade_plan_name}",
        f"recipient={recipient}",
        "html_body=full_report",
        f"pdf_attached={'yes' if any(a.lower().endswith('.pdf') for a in attachments) else 'no'}",
        "attachments=" + ", ".join(attachments),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_delivery_assets(output_dir: Path, report_path: Path) -> dict:
    md_text = normalize(report_path.read_text(encoding="utf-8"))
    validate_report(md_text)
    report_date = parse_report_date(md_text, report_path)

    trade_plan_path = expected_trade_plan_path(report_path)
    _ = validate_trade_plan(trade_plan_path)

    html = markdown_to_html(md_text, report_date)
    html_path = report_path.with_name(report_path.stem + "_delivery.html")
    pdf_path = report_path.with_name(report_path.stem + ".pdf")

    html_path.write_text(html, encoding="utf-8")
    HTML(string=html, base_url=str(output_dir)).write_pdf(str(pdf_path))

    if not pdf_path.exists() or pdf_path.stat().st_size <= 0:
        raise RuntimeError("PDF was not created correctly.")

    return {
        "report_path": report_path,
        "trade_plan_path": trade_plan_path,
        "html_path": html_path,
        "pdf_path": pdf_path,
        "html": html,
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

    root = MIMEMultipart("mixed")
    root["Subject"] = f"{TITLE} {assets['report_date']}"
    root["From"] = mail_from
    root["To"] = mail_to
    root.attach(MIMEText(assets["html"], "html", "utf-8"))

    attachments = [assets["pdf_path"], assets["report_path"], assets["trade_plan_path"], assets["html_path"]]
    names = []
    for path in attachments:
        subtype = "pdf" if path.suffix == ".pdf" else ("html" if path.suffix == ".html" else "plain")
        with path.open("rb") as fh:
            part = MIMEApplication(fh.read(), _subtype=subtype)
        part.add_header("Content-Disposition", "attachment", filename=path.name)
        root.attach(part)
        names.append(path.name)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.sendmail(mail_from, [mail_to], root.as_string())

    return True, names, mail_to


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--report-path", default=None, help="Optional explicit report markdown path")
    args = parser.parse_args()

    output_dir = Path("output_aex")
    latest = Path(args.report_path) if args.report_path else latest_report_file(output_dir)
    if not latest.exists():
        raise FileNotFoundError(f"Explicit report path does not exist: {latest}")
    assets = generate_delivery_assets(output_dir, latest)
    manifest_path = latest.with_name(latest.stem + "_delivery_manifest.txt")

    if args.validate_only:
        write_manifest(manifest_path, latest.name, assets["trade_plan_path"].name, "validation_only", [assets["html_path"].name, assets["pdf_path"].name, assets["trade_plan_path"].name])
        print(f"VALIDATION_OK | report={latest.name} | trade_plan={assets['trade_plan_path'].name} | manifest={manifest_path.name}")
        return

    sent, attachment_names, recipient = maybe_send_email(assets)
    if sent:
        write_manifest(manifest_path, latest.name, assets["trade_plan_path"].name, recipient, attachment_names)
        print(f"DELIVERY_OK | report={latest.name} | trade_plan={assets['trade_plan_path'].name} | recipient={recipient} | manifest={manifest_path.name}")
    else:
        write_manifest(manifest_path, latest.name, assets["trade_plan_path"].name, recipient, [assets["html_path"].name, assets["pdf_path"].name, assets["trade_plan_path"].name])
        print(f"RENDER_OK | report={latest.name} | trade_plan={assets['trade_plan_path'].name} | delivery={recipient} | manifest={manifest_path.name}")


if __name__ == "__main__":
    main()
