from __future__ import annotations

import re
from urllib.parse import quote

import send_index_report as _base

TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([A-Z][A-Z0-9.\-]{1,11})(?![A-Za-z0-9])")
TRADINGVIEW_LINK_RE = re.compile(r'(<a\s+href=")([^\"]*tradingview\.com/chart/\?symbol=[^\"]+)(")', flags=re.IGNORECASE)
TICKER_DENYLIST = {
    "USD", "EUR", "CASH", "NONE", "N/A", "ETF", "INDEX", "LONG", "SHORT", "ADD", "HOLD", "REDUCE", "CLOSE",
}
TICKER_HEADER_HINTS = {
    "ticker",
    "primary proxy",
    "implementation proxy",
    "alternative proxy",
    "proxy",
    "primary_proxy",
    "tickers / public names",
}


orig_build_report_html = _base.build_report_html


def tradingview_url(ticker: str) -> str:
    ticker = _base.clean_md_inline(ticker)
    return f"https://www.tradingview.com/chart/?symbol={quote(ticker, safe='')}"


def is_probable_ticker(value: str) -> bool:
    raw = _base.clean_md_inline(value).strip()
    if not raw:
        return False
    if raw.upper() in TICKER_DENYLIST:
        return False
    if len(raw) < 2 or len(raw) > 12:
        return False
    return bool(re.fullmatch(r"[A-Z][A-Z0-9.\-]{1,11}", raw))


def ticker_anchor_html(ticker: str) -> str:
    ticker = _base.clean_md_inline(ticker)
    return f'<a href="{tradingview_url(ticker)}" target="_blank" rel="noopener noreferrer">{_base.esc(ticker)}</a>'


def ticker_anchor_md(ticker: str) -> str:
    ticker = _base.clean_md_inline(ticker)
    return f'[{ticker}]({tradingview_url(ticker)})'


def add_tradingview_targets(html: str) -> str:
    return TRADINGVIEW_LINK_RE.sub(r'\1\2" target="_blank" rel="noopener noreferrer\3', html)


def linkify_tokens_in_text_md(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        token = match.group(1)
        return ticker_anchor_md(token) if is_probable_ticker(token) else token
    return TOKEN_RE.sub(repl, text)


def linkify_inline_tickers_html(text: str) -> str:
    raw = _base.clean_md_inline(text)
    out: list[str] = []
    last = 0
    for match in TOKEN_RE.finditer(raw):
        token = match.group(1)
        if not is_probable_ticker(token):
            continue
        out.append(_base.esc(raw[last:match.start()]))
        out.append(ticker_anchor_html(token))
        last = match.end()
    out.append(_base.esc(raw[last:]))
    return "".join(out)


def is_markdown_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def is_markdown_separator_line(line: str) -> bool:
    stripped = line.strip().strip("|").replace(":", "").replace("-", "").replace(" ", "")
    return stripped == ""


def parse_markdown_table(block_lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in block_lines:
        rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
    return rows


def _norm_header(value: str) -> str:
    return re.sub(r"\s+", " ", _base.clean_md_inline(value).strip().lower())


def linkify_table_cell_md(header: str, value: str) -> str:
    norm = _norm_header(header)
    if norm in TICKER_HEADER_HINTS or "ticker" in norm or "proxy" in norm:
        return linkify_tokens_in_text_md(value)
    return value


def linkify_ticker_tables(md_text: str) -> str:
    lines = md_text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        if i + 1 < len(lines) and is_markdown_table_line(lines[i]) and is_markdown_separator_line(lines[i + 1]):
            block = [lines[i], lines[i + 1]]
            j = i + 2
            while j < len(lines) and is_markdown_table_line(lines[j]):
                block.append(lines[j])
                j += 1
            rows = parse_markdown_table(block)
            if len(rows) >= 2:
                headers = rows[0]
                out.append("| " + " | ".join(headers) + " |")
                out.append(block[1])
                for row in rows[2:]:
                    padded = row + [""] * (len(headers) - len(row))
                    cells = [linkify_table_cell_md(headers[idx], padded[idx]) for idx in range(len(headers))]
                    out.append("| " + " | ".join(cells) + " |")
            else:
                out.extend(block)
            i = j
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def preprocess_markdown_block(text: str) -> str:
    text = _base.strip_citations(text)
    text = re.sub(r"\(\*\*([A-Z][A-Z0-9.\-]{1,11})\*\*\)", lambda m: f"(**{ticker_anchor_md(m.group(1))}**)" if is_probable_ticker(m.group(1)) else m.group(0), text)
    text = re.sub(r"\((([A-Z][A-Z0-9.\-]{1,11}))\)", lambda m: f"({ticker_anchor_md(m.group(1))})" if is_probable_ticker(m.group(1)) else m.group(0), text)
    text = re.sub(r"\bvia\s+([A-Z][A-Z0-9.\-]{1,11})\b", lambda m: f"via {ticker_anchor_md(m.group(1))}" if is_probable_ticker(m.group(1)) else m.group(0), text)
    return linkify_ticker_tables(text)


def render_markdown_block(text: str, image_src: str | None = None) -> str:
    text = preprocess_markdown_block(text)
    if image_src:
        text = text.replace("`EQUITY_CURVE_CHART_PLACEHOLDER`", f"![Equity curve]({image_src})")
        text = text.replace("EQUITY_CURVE_CHART_PLACEHOLDER", f"![Equity curve]({image_src})")
    else:
        text = text.replace("`EQUITY_CURVE_CHART_PLACEHOLDER`", "_Equity curve chart unavailable for this delivery._")
        text = text.replace("EQUITY_CURVE_CHART_PLACEHOLDER", "_Equity curve chart unavailable for this delivery._")
    html = _base.mdlib.markdown(text, extensions=["tables", "sane_lists", "fenced_code"])
    return add_tradingview_targets(html)


def render_action_snapshot(section: dict) -> str:
    groups = _base.parse_subsections(section["lines"])
    order = ["Add", "Hold", "Hold but replaceable", "Reduce", "Close"]
    rows = []
    for label in order:
        items = groups.get(label, [])
        val_html = ", ".join(linkify_inline_tickers_html(item) for item in items) if items else "None"
        rows.append(f"<tr><th>{_base.esc(label)}</th><td>{val_html}</td></tr>")

    def block(title: str) -> str:
        items = groups.get(title, [])
        if not items:
            return ""
        list_html = "".join(f"<li>{linkify_inline_tickers_html(item)}</li>" for item in items)
        return f"<div class='subblock'><div class='subblock-title'>{_base.esc(title)}</div><ul>{list_html}</ul></div>"

    return (
        f"<div class='panel panel-snapshot'>"
        f"{_base.section_header_html(section['number'], section['title'])}"
        f"<table class='snapshot-table'><thead><tr><th>Recommendation</th><th>Tickers / notes</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"
        f"{block('Best replacements to fund')}"
        f"<div class='subgrid'>{block('Top 3 actions this week')}{block('Top 3 risks this week')}</div>"
        f"</div>"
    )


def render_position_review(section: dict) -> str:
    blocks = _base.split_h3_blocks(section["lines"])
    cards = []
    for block in blocks:
        block_html = render_markdown_block("\n".join(block["lines"]))
        cards.append(
            f"<article class='position-card'>"
            f"<div class='position-card-title'>{linkify_inline_tickers_html(str(block['title']))}</div>"
            f"<div class='position-card-body'>{block_html}</div>"
            f"</article>"
        )
    return f"<div class='panel panel-positions'>{_base.section_header_html(section['number'], section['title'])}{''.join(cards)}</div>"


def build_report_html(md_text: str, report_date_str: str, image_src: str | None = None, render_mode: str = "email") -> str:
    return add_tradingview_targets(orig_build_report_html(md_text, report_date_str, image_src=image_src, render_mode=render_mode))


_base.render_markdown_block = render_markdown_block
_base.render_action_snapshot = render_action_snapshot
_base.render_position_review = render_position_review
_base.build_report_html = build_report_html


def main() -> None:
    _base.main()


if __name__ == "__main__":
    main()
