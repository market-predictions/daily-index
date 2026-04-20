from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

SECTION4_NAME = "Index Opportunity Board"
SECTION7_NAME = "Equity Curve and Portfolio Development"
SECTION11_NAME = "Best New Index Opportunities"
SECTION15_NAME = "Current Portfolio Holdings and Cash"
SECTION16_NAME = "Continuity Input for Next Run"
REPORT_RE = re.compile(r"weekly_indices_review_(\d{6})(?:_(\d{2}))?\.md$")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def latest_report_token(output_dir: Path) -> str:
    hits: list[tuple[str, int, Path]] = []
    for path in output_dir.glob("weekly_indices_review_*.md"):
        match = REPORT_RE.match(path.name)
        if match:
            hits.append((match.group(1), int(match.group(2) or "0"), path))
    if not hits:
        raise FileNotFoundError("No weekly_indices_review_*.md file found")
    hits.sort(key=lambda x: (x[0], x[1]))
    return hits[-1][0]


def exposure_reason(exposure_id: str, plan: dict[str, Any], fallback: str) -> str:
    for row in plan.get("recommended_changes") or []:
        if row.get("exposure_id") == exposure_id and row.get("reason"):
            return str(row["reason"])
    for row in plan.get("best_new_opportunities") or []:
        if row.get("exposure_id") == exposure_id:
            if row.get("portfolio_gap_fill"):
                return "Improves breadth or fills an important portfolio gap without forcing a low-conviction rotation."
            return "Ranks well enough internally to stay near the live board."
    return fallback


def _read_valuation_history(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _fmt_num(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:  # noqa: BLE001
        return "—"


def build_section4(candidate_ranking: dict[str, Any], plan: dict[str, Any]) -> str:
    published = [c for c in candidate_ranking.get("candidates", []) if c.get("publish")]
    published = sorted(published, key=lambda x: (-float(x.get("board_score") or x.get("score") or 0.0), x.get("public_index_name") or ""))[:6]

    lines = [f"## 4. {SECTION4_NAME}", ""]
    lines.append("| Exposure | Benchmark / public index | Implementation proxy | Regional group | Score | Status | Why it is on the board |")
    lines.append("|---|---|---|---|---:|---|---|")
    for row in published:
        status = "Funded" if row.get("currently_held") else "Surfaced"
        fallback_reason = "Ranks high enough internally to remain on the compact published board."
        why = exposure_reason(str(row.get("exposure_id")), plan, fallback_reason)
        lines.append(
            f"| {row.get('public_index_name')} | {row.get('public_index_name')} | {row.get('primary_proxy')} | {row.get('regional_group')} | {float(row.get('board_score') or row.get('score') or 0.0):.2f} | {status} | {why} |"
        )

    near_miss_groups = [g for g in candidate_ranking.get("regional_group_status", []) if g.get("status") == "near_miss"]
    if near_miss_groups:
        strongest = near_miss_groups[0].get("strongest_candidate") or {}
        if strongest:
            lines += [
                "",
                f"The board remains intentionally compact. The strongest omitted regional challenger this run is **{strongest.get('public_index_name')} ({strongest.get('primary_proxy')})**, which remains close enough to matter without displacing a higher-ranked funded exposure.",
            ]
    return "\n".join(lines)


def build_section7(state: dict[str, Any], valuation_rows: list[dict[str, str]]) -> str:
    requested_close = ((state.get("pricing_basis") or {}).get("requested_close_date")) or "unknown"
    total_value = float(state.get("total_portfolio_value_eur") or 0.0)
    cash_eur = float(state.get("cash_eur") or 0.0)
    starting_capital = float(state.get("starting_capital_eur") or 100000.0)
    invested_eur = total_value - cash_eur
    ret_pct = ((total_value / starting_capital) - 1.0) * 100.0 if starting_capital else 0.0
    fx_date = ((state.get("pricing_basis") or {}).get("fx_date")) or requested_close

    lines = [f"## 7. {SECTION7_NAME}", ""]
    lines += [
        f"- Starting capital (EUR): {starting_capital:.2f}",
        f"- Current portfolio value (EUR): {total_value:.2f}",
        f"- Since inception return (%): {ret_pct:.2f}",
        f"- Equity-curve state: {'Inaugural baseline' if len(valuation_rows) <= 1 else 'Live tracked'}",
        f"- Pricing basis requested close date: {requested_close}",
        f"- FX reference date: {fx_date}",
        f"- Notes: Holdings and NAV in this section are rebuilt from the live pricing/state layer for the requested close date {requested_close}.",
        "",
        "| Date | Portfolio value (EUR) | Comment |",
        "|---|---:|---|",
    ]
    if valuation_rows:
        for row in valuation_rows[-10:]:
            lines.append(
                f"| {row.get('requested_close_date') or row.get('as_of')} | {float(row.get('total_portfolio_value_eur') or 0.0):.2f} | Pricing basis close {row.get('requested_close_date')} |"
            )
    else:
        lines.append(f"| {requested_close} | {total_value:.2f} | Live pricing/state rebuild |")
    lines += ["", "`EQUITY_CURVE_CHART_PLACEHOLDER`"]
    return "\n".join(lines)


def _breadth_rows(candidate_ranking: dict[str, Any], exposure_ids: list[str]) -> list[dict[str, Any]]:
    rows = []
    by_id = {row.get("exposure_id"): row for row in candidate_ranking.get("candidates", [])}
    for exposure_id in exposure_ids:
        row = by_id.get(exposure_id)
        if row:
            rows.append(row)
    return rows


def build_section11(candidate_ranking: dict[str, Any], coverage: dict[str, Any], plan: dict[str, Any]) -> str:
    candidates = [c for c in candidate_ranking.get("candidates", []) if not c.get("publish")]
    candidates = sorted(candidates, key=lambda x: (-float(x.get("challenger_score") or x.get("score") or 0.0), x.get("public_index_name") or ""))
    coverage_groups = coverage.get("groups") or []
    strongest_omitted = None
    for group in coverage_groups:
        cand = group.get("strongest_candidate") or {}
        if cand and not cand.get("publish"):
            strongest_omitted = cand
            break

    picked: list[dict[str, Any]] = []
    seen: set[str] = set()
    if strongest_omitted and strongest_omitted.get("exposure_id"):
        for row in candidates:
            if row.get("exposure_id") == strongest_omitted.get("exposure_id"):
                picked.append(row)
                seen.add(str(row.get("exposure_id")))
                break
    for row in candidates:
        eid = str(row.get("exposure_id"))
        if eid in seen:
            continue
        picked.append(row)
        seen.add(eid)
        if len(picked) >= 4:
            break

    lines = [f"## 11. {SECTION11_NAME}", ""]
    if strongest_omitted:
        lines.append(
            f"The strongest omitted regional challenger this run is **{strongest_omitted.get('public_index_name')} ({strongest_omitted.get('primary_proxy')})**. It improves breadth and remains close enough to the live board to stay visible in the report."
        )
        lines.append("")

    for idx, row in enumerate(picked, start=1):
        reason = exposure_reason(str(row.get("exposure_id")), plan, "Ranks well internally but remains just below the current publication cutoff.")
        lines += [
            f"### {idx}. {row.get('public_index_name')} ({row.get('primary_proxy')})",
            f"- Regional group: {row.get('regional_group')}",
            f"- Challenger score: {float(row.get('challenger_score') or row.get('score') or 0.0):.2f}",
            f"- Board score: {float(row.get('board_score') or row.get('score') or 0.0):.2f}",
            f"- Why it matters: {reason}",
            f"- Why not on the board yet: {row.get('reason_code_if_not_published') or 'below_board_cutoff'}",
            "",
        ]

    lines += [
        "### Breadth checkpoint by region",
        "| Regional bucket | Strongest candidate | Proxy | Challenger score | Current status |",
        "|---|---|---|---:|---|",
    ]
    for group in coverage_groups:
        cand = group.get("strongest_candidate") or {}
        if not cand:
            continue
        status = "Published" if cand.get("publish") else ("Near miss" if group.get("status") == "near_miss" else "Ruled out / lower priority")
        lines.append(
            f"| {group.get('group')} | {cand.get('public_index_name')} | {cand.get('primary_proxy')} | {float(cand.get('challenger_score') or cand.get('score') or 0.0):.2f} | {status} |"
        )

    europe_rows = _breadth_rows(candidate_ranking, ["germany_cyclicals", "france_large_cap", "italy_large_cap", "spain_large_cap", "netherlands_large_cap"])
    if europe_rows:
        lines += [
            "",
            "### Continental Europe breadth checkpoint",
            "| Market | Proxy | Challenger score | Why not on the board yet |",
            "|---|---|---:|---|",
        ]
        for row in sorted(europe_rows, key=lambda x: (-float(x.get('challenger_score') or 0.0), x.get('public_index_name') or '')):
            lines.append(
                f"| {row.get('public_index_name')} | {row.get('primary_proxy')} | {float(row.get('challenger_score') or 0.0):.2f} | {row.get('reason_code_if_not_published') or 'published'} |"
            )

    asia_rows = _breadth_rows(candidate_ranking, ["china_large_cap", "india_large_cap", "australia_large_cap"])
    if asia_rows:
        lines += [
            "",
            "### Asia / EM breadth checkpoint",
            "| Market | Proxy | Challenger score | Why not on the board yet |",
            "|---|---|---:|---|",
        ]
        for row in sorted(asia_rows, key=lambda x: (-float(x.get('challenger_score') or 0.0), x.get('public_index_name') or '')):
            lines.append(
                f"| {row.get('public_index_name')} | {row.get('primary_proxy')} | {float(row.get('challenger_score') or 0.0):.2f} | {row.get('reason_code_if_not_published') or 'published'} |"
            )

    return "\n".join(lines).rstrip()


def build_section15(state: dict[str, Any]) -> str:
    starting_capital = float(state.get("starting_capital_eur") or 100000.0)
    total_value = float(state.get("total_portfolio_value_eur") or 0.0)
    cash_eur = float(state.get("cash_eur") or 0.0)
    invested_eur = total_value - cash_eur
    ret_pct = ((total_value / starting_capital) - 1.0) * 100.0 if starting_capital else 0.0
    requested_close = ((state.get("pricing_basis") or {}).get("requested_close_date")) or "unknown"
    fx_date = ((state.get("pricing_basis") or {}).get("fx_date")) or requested_close

    lines = [f"## 15. {SECTION15_NAME}", ""]
    lines += [
        f"- Starting capital (EUR): {starting_capital:.2f}",
        f"- Invested market value (EUR): {invested_eur:.2f}",
        f"- Cash (EUR): {cash_eur:.2f}",
        f"- Total portfolio value (EUR): {total_value:.2f}",
        f"- Since inception return (%): {ret_pct:.2f}",
        f"- Pricing basis requested close date: {requested_close}",
        f"- FX reference date: {fx_date}",
        "",
        "| Ticker | Public index / exposure | Shares | Price (local) | Currency | Market value (local) | Market value (EUR) | Weight % |",
        "|---|---|---:|---:|---|---:|---:|---:|",
    ]
    for pos in state.get("positions") or []:
        lines.append(
            f"| {pos.get('primary_proxy')} | {pos.get('display_name')} | {int(pos.get('shares') or 0)} | {float(pos.get('latest_proxy_close') or 0.0):.2f} | {pos.get('proxy_currency') or 'USD'} | {float(pos.get('market_value_local') or 0.0):.2f} | {float(pos.get('market_value_eur') or 0.0):.2f} | {float(pos.get('weight_pct') or 0.0):.2f} |"
        )
    lines.append(f"| CASH | Residual cash | - | 1.00 | EUR | {cash_eur:.2f} | {cash_eur:.2f} | {(cash_eur / total_value * 100.0 if total_value else 0.0):.2f} |")
    return "\n".join(lines)


def build_section16(candidate_ranking: dict[str, Any], coverage: dict[str, Any], plan: dict[str, Any]) -> str:
    continuity = plan.get("continuity") or {}
    lines = [f"## 16. {SECTION16_NAME}", ""]
    lines += [
        "### Watchlist / dynamic radar memory",
        "| Theme | Regional group | Primary Proxy | Status | Why it stays visible |",
        "|---|---|---|---|---|",
    ]
    watch_candidates = sorted(
        [c for c in candidate_ranking.get("candidates", []) if not c.get("publish")],
        key=lambda x: (-float(x.get("challenger_score") or x.get("score") or 0.0), x.get("public_index_name") or ""),
    )[:6]
    for row in watch_candidates:
        status = "Strong challenger" if row.get("reason_code_if_not_published") == "strong_challenger_not_published" else "Watchlist"
        why = exposure_reason(str(row.get("exposure_id")), plan, "Broad discovery keeps it visible even though it did not make the compact board.")
        lines.append(
            f"| {row.get('public_index_name')} | {row.get('regional_group')} | {row.get('primary_proxy')} | {status} | {why} |"
        )

    lines += [
        "",
        "### Discovery coverage checkpoint",
        "| Regional group | Status | Strongest candidate | Proxy | Score |",
        "|---|---|---|---|---:|",
    ]
    for group in coverage.get("groups") or []:
        cand = group.get("strongest_candidate") or {}
        lines.append(
            f"| {group.get('group')} | {group.get('status')} | {cand.get('public_index_name', '—')} | {cand.get('primary_proxy', '—')} | {float(cand.get('challenger_score') or cand.get('score') or 0.0):.2f} |"
        )

    lines += [
        "",
        "### Lane continuity notes",
        f"- Retained entries: {', '.join(continuity.get('retained_entries') or ['none'])}",
        f"- New entries: {', '.join(continuity.get('new_entries') or ['none'])}",
        f"- Dropped entries: {', '.join(continuity.get('dropped_entries') or ['none'])}",
        f"- Strong challengers not published: {', '.join(continuity.get('strong_challengers_not_published') or ['none'])}",
        f"- What would most likely change the board next run: {continuity.get('next_change_trigger') or 'No trigger recorded.'}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output_indices")
    parser.add_argument("--token", default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    token = args.token or latest_report_token(output_dir)

    ranking_path = output_dir / f"index_candidate_ranking_{token}.json"
    coverage_path = output_dir / f"index_discovery_coverage_{token}.json"
    plan_path = output_dir / f"index_recommendation_plan_{token}.json"
    state_path = output_dir / "index_portfolio_state.json"
    valuation_path = output_dir / "index_valuation_history.csv"

    if not ranking_path.exists():
        raise FileNotFoundError(f"Missing ranking artifact: {ranking_path}")
    if not coverage_path.exists():
        raise FileNotFoundError(f"Missing discovery coverage artifact: {coverage_path}")
    if not plan_path.exists():
        raise FileNotFoundError(f"Missing recommendation plan artifact: {plan_path}")
    if not state_path.exists():
        raise FileNotFoundError(f"Missing portfolio state artifact: {state_path}")

    candidate_ranking = _read_json(ranking_path)
    coverage = _read_json(coverage_path)
    plan = _read_json(plan_path)
    state = _read_json(state_path)
    valuation_rows = _read_valuation_history(valuation_path)

    assembled_dir = output_dir / "assembled"
    sec4 = build_section4(candidate_ranking, plan)
    sec7 = build_section7(state, valuation_rows)
    sec11 = build_section11(candidate_ranking, coverage, plan)
    sec15 = build_section15(state)
    sec16 = build_section16(candidate_ranking, coverage, plan)

    section4_path = assembled_dir / f"section4_index_opportunity_board_{token}.md"
    section7_path = assembled_dir / f"section7_equity_curve_{token}.md"
    section11_path = assembled_dir / f"section11_best_new_index_opportunities_{token}.md"
    section15_path = assembled_dir / f"section15_holdings_and_cash_{token}.md"
    section16_path = assembled_dir / f"section16_continuity_input_{token}.md"
    combined_path = assembled_dir / f"weekly_indices_artifact_blocks_{token}.md"

    _write_text(section4_path, sec4)
    _write_text(section7_path, sec7)
    _write_text(section11_path, sec11)
    _write_text(section15_path, sec15)
    _write_text(section16_path, sec16)
    _write_text(combined_path, "\n\n".join([sec4, sec7, sec11, sec15, sec16]))

    print(
        f"ASSEMBLY_BLOCKS_OK | token={token} | section4={section4_path.name} | section7={section7_path.name} | "
        f"section11={section11_path.name} | section15={section15_path.name} | section16={section16_path.name} | combined={combined_path.name}"
    )


if __name__ == "__main__":
    main()
