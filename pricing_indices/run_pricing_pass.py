from __future__ import annotations

import argparse
import csv
import json
import math
import re
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from .catalog import BY_PROXY, DEFAULT_EXPOSURES
from .data_sources import fetch_ecb_usd_per_eur, fetch_yahoo_close

REPORT_RE = re.compile(r"weekly_indices_review_(\d{6})(?:_(\d{2}))?\.md$")
US_REGULAR_CLOSE_UTC = time(hour=20, minute=15)  # conservative buffer after 16:00 ET during DST season


def latest_report_file(output_dir: Path) -> Path | None:
    files: list[tuple[str, int, Path]] = []
    for path in output_dir.glob("weekly_indices_review_*.md"):
        match = REPORT_RE.match(path.name)
        if match:
            files.append((match.group(1), int(match.group(2) or "1"), path))
    if not files:
        return None
    files.sort(key=lambda x: (x[0], x[1]))
    return files[-1][2]


def previous_business_day(d: date) -> date:
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def latest_completed_us_close_date(now_utc: datetime | None = None) -> str:
    now_utc = now_utc or datetime.now(timezone.utc)
    today = now_utc.date()
    if today.weekday() >= 5:
        return previous_business_day(today).isoformat()
    if now_utc.time() >= US_REGULAR_CLOSE_UTC:
        return today.isoformat()
    return previous_business_day(today - timedelta(days=1) if today.weekday() == 0 else today - timedelta(days=1)).isoformat() if today.weekday() == 0 else previous_business_day(today - timedelta(days=1)).isoformat()


def requested_close_from_today(today: date) -> str:
    d = today
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()


def _to_float(text: str | None) -> float | None:
    if text is None:
        return None
    raw = text.replace(",", "").replace("%", "").strip()
    if not raw or raw == "-":
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_section15_from_report(md_text: str) -> tuple[list[dict[str, Any]], float | None]:
    section_start = md_text.find("## 15.")
    if section_start == -1:
        return [], None
    section = md_text[section_start:]
    positions: list[dict[str, Any]] = []
    cash_eur: float | None = None
    in_table = False
    for line in section.splitlines():
        if line.startswith("| Ticker |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            if "---" in line:
                continue
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) < 7:
                continue
            ticker = parts[0].upper()
            if ticker == "CASH":
                cash_eur = _to_float(parts[5])
                continue
            meta = deepcopy(BY_PROXY.get(ticker, {}))
            positions.append(
                {
                    "exposure_id": meta.get("exposure_id", ticker.lower()),
                    "display_name": meta.get("display_name", ticker),
                    "benchmark_symbol": meta.get("benchmark_symbol", ticker),
                    "benchmark_name": meta.get("benchmark_name", ticker),
                    "primary_proxy": ticker,
                    "alternative_proxy": meta.get("alternative_proxy", ""),
                    "region": meta.get("region", "Unknown"),
                    "style": meta.get("style", "Unknown"),
                    "direction": "long",
                    "shares": int(_to_float(parts[1]) or 0),
                    "proxy_currency": parts[3] or "USD",
                    "avg_entry_proxy": _to_float(parts[2]),
                    "latest_proxy_close": _to_float(parts[2]),
                    "latest_benchmark_close": None,
                    "market_value_local": _to_float(parts[4]),
                    "market_value_eur": _to_float(parts[5]),
                    "weight_pct": _to_float(parts[6]),
                    "role": meta.get("role", "portfolio exposure"),
                    "original_thesis": meta.get("original_thesis", "Carry-forward from latest stored report."),
                    "current_status": "hold",
                    "target_weight_pct": meta.get("target_weight_pct"),
                }
            )
    return positions, cash_eur


def bootstrap_positions(starting_capital_eur: float, requested_close_date: str, usd_per_eur: float) -> tuple[list[dict[str, Any]], float]:
    positions: list[dict[str, Any]] = []
    invested_eur = 0.0
    for item in DEFAULT_EXPOSURES:
        proxy = fetch_yahoo_close(item["primary_proxy"], requested_close_date)
        benchmark = fetch_yahoo_close(item["benchmark_symbol"], requested_close_date)
        budget_eur = starting_capital_eur * (float(item["target_weight_pct"]) / 100.0)
        budget_usd = budget_eur * usd_per_eur
        shares = math.floor(budget_usd / proxy["close"])
        market_value_local = shares * proxy["close"]
        market_value_eur = market_value_local / usd_per_eur if usd_per_eur else 0.0
        invested_eur += market_value_eur
        positions.append(
            {
                "exposure_id": item["exposure_id"],
                "display_name": item["display_name"],
                "benchmark_symbol": item["benchmark_symbol"],
                "benchmark_name": item["benchmark_name"],
                "primary_proxy": item["primary_proxy"],
                "alternative_proxy": item["alternative_proxy"],
                "region": item["region"],
                "style": item["style"],
                "direction": "long",
                "shares": shares,
                "proxy_currency": proxy["currency"],
                "avg_entry_proxy": proxy["close"],
                "latest_proxy_close": proxy["close"],
                "latest_benchmark_close": benchmark["close"],
                "market_value_local": round(market_value_local, 2),
                "market_value_eur": round(market_value_eur, 2),
                "weight_pct": 0.0,
                "role": item["role"],
                "original_thesis": item["original_thesis"],
                "current_status": "hold",
                "target_weight_pct": item["target_weight_pct"],
            }
        )
    cash_eur = round(starting_capital_eur - invested_eur, 2)
    return positions, cash_eur


def load_positions(state_path: Path, output_dir: Path) -> tuple[list[dict[str, Any]], float | None, str]:
    if state_path.exists():
        state = _read_json(state_path)
        positions = state.get("positions") or []
        if positions:
            return positions, state.get("cash_eur"), "state_file"
    latest = latest_report_file(output_dir)
    if latest and latest.exists():
        positions, cash_eur = parse_section15_from_report(latest.read_text(encoding="utf-8"))
        if positions:
            return positions, cash_eur, "latest_report"
    return [], None, "bootstrap_required"


def ensure_csv_headers(path: Path, headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)


def append_valuation_row(path: Path, row: list[Any]) -> None:
    ensure_csv_headers(path, ["as_of", "requested_close_date", "total_portfolio_value_eur", "cash_eur", "fx_usd_per_eur", "source"])
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(row)


def build_state_payload(as_of: str, requested_close_date: str, fx_basis: dict[str, Any], positions: list[dict[str, Any]], cash_eur: float, total_portfolio_value_eur: float) -> dict[str, Any]:
    return {
        "as_of": as_of,
        "base_currency": "EUR",
        "starting_capital_eur": 100000.0,
        "total_portfolio_value_eur": round(total_portfolio_value_eur, 2),
        "cash_eur": round(cash_eur, 2),
        "pricing_basis": {
            "requested_close_date": requested_close_date,
            "fx_basis": fx_basis.get("source"),
            "fx_date": fx_basis.get("date"),
            "price_audit_file": f"output_indices/pricing/index_price_audit_{requested_close_date}.json",
        },
        "constraints": {
            "max_position_size_pct": 25.0,
            "max_positions": 8,
            "allow_leverage": False,
            "allow_short": False,
            "income_vs_growth_preference": "balanced growth with resilience bias",
            "drawdown_tolerance": "moderate",
        },
        "positions": positions,
        "watchlist_memory": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--requested-close-date", default=None)
    parser.add_argument("--output-dir", default="output_indices")
    parser.add_argument("--pricing-dir", default="output_indices/pricing")
    parser.add_argument("--state-path", default="output_indices/index_portfolio_state.json")
    args = parser.parse_args()

    today = date.today()
    requested_close_date = args.requested_close_date or latest_completed_us_close_date()
    run_date = today.isoformat()
    output_dir = Path(args.output_dir)
    pricing_dir = Path(args.pricing_dir)
    state_path = Path(args.state_path)

    fx_basis = fetch_ecb_usd_per_eur(requested_close_date)
    usd_per_eur = float(fx_basis["usd_per_eur"])

    positions, cash_eur, source_mode = load_positions(state_path, output_dir)
    bootstrapped = False
    if not positions:
        positions, cash_eur = bootstrap_positions(100000.0, requested_close_date, usd_per_eur)
        source_mode = "bootstrap_default_catalog"
        bootstrapped = True

    price_rows: list[dict[str, Any]] = []
    fresh_count = 0
    carried_forward_count = 0
    unresolved: list[str] = []
    invested_weight_coverage = 0.0
    total_value_eur = float(cash_eur or 0.0)

    for pos in positions:
        previous_proxy = pos.get("latest_proxy_close")
        previous_benchmark = pos.get("latest_benchmark_close")
        proxy_status = "carried_forward"
        benchmark_status = "carried_forward"

        try:
            proxy_quote = fetch_yahoo_close(pos["primary_proxy"], requested_close_date)
            pos["latest_proxy_close"] = round(float(proxy_quote["close"]), 4)
            pos["proxy_currency"] = proxy_quote.get("currency") or pos.get("proxy_currency") or "USD"
            proxy_status = "fresh_close"
            fresh_count += 1
        except Exception as exc:  # noqa: BLE001
            proxy_quote = None
            if previous_proxy is None:
                unresolved.append(pos["primary_proxy"])
                pos["latest_proxy_close"] = None
                proxy_status = f"unresolved: {exc}"
            else:
                carried_forward_count += 1
                pos["latest_proxy_close"] = previous_proxy
                proxy_status = "carried_forward"

        try:
            benchmark_quote = fetch_yahoo_close(pos["benchmark_symbol"], requested_close_date)
            pos["latest_benchmark_close"] = round(float(benchmark_quote["close"]), 4)
            benchmark_status = "fresh_close"
        except Exception as exc:  # noqa: BLE001
            benchmark_quote = None
            if previous_benchmark is None:
                pos["latest_benchmark_close"] = None
                benchmark_status = f"unresolved: {exc}"
            else:
                pos["latest_benchmark_close"] = previous_benchmark
                benchmark_status = "carried_forward"

        shares = int(pos.get("shares") or 0)
        latest_proxy_close = pos.get("latest_proxy_close") or 0.0
        market_value_local = round(shares * float(latest_proxy_close), 2)
        market_value_eur = round(market_value_local / usd_per_eur, 2) if usd_per_eur else 0.0
        pos["market_value_local"] = market_value_local
        pos["market_value_eur"] = market_value_eur
        total_value_eur += market_value_eur

        price_rows.append(
            {
                "exposure_id": pos.get("exposure_id"),
                "display_name": pos.get("display_name"),
                "benchmark_symbol": pos.get("benchmark_symbol"),
                "primary_proxy": pos.get("primary_proxy"),
                "shares": shares,
                "proxy_close": pos.get("latest_proxy_close"),
                "benchmark_close": pos.get("latest_benchmark_close"),
                "proxy_status": proxy_status,
                "benchmark_status": benchmark_status,
                "market_value_eur": market_value_eur,
            }
        )

    for pos in positions:
        pos["weight_pct"] = round((float(pos.get("market_value_eur") or 0.0) / total_value_eur) * 100.0, 2) if total_value_eur else 0.0
        if pos.get("latest_proxy_close") is not None:
            invested_weight_coverage += float(pos["weight_pct"])

    holdings_count = len(positions)
    coverage_count_pct = round((fresh_count / holdings_count) * 100.0, 2) if holdings_count else 0.0
    invested_weight_coverage_pct = round(invested_weight_coverage, 2)
    decision = "update_covered_holdings_carry_unresolved" if (coverage_count_pct >= 75.0 or invested_weight_coverage_pct >= 85.0) else "blocked_or_partial"

    state_payload = build_state_payload(run_date, requested_close_date, fx_basis, positions, float(cash_eur or 0.0), total_value_eur)
    _write_json(state_path, state_payload)

    pricing_dir.mkdir(parents=True, exist_ok=True)
    audit_path = pricing_dir / f"index_price_audit_{requested_close_date}.json"
    audit_payload = {
        "run_date": run_date,
        "requested_close_date": requested_close_date,
        "source_mode": source_mode,
        "bootstrapped": bootstrapped,
        "holdings_count": holdings_count,
        "fresh_holdings_count": fresh_count,
        "carried_forward_holdings_count": carried_forward_count,
        "coverage_count_pct": coverage_count_pct,
        "invested_weight_coverage_pct": invested_weight_coverage_pct,
        "decision": decision,
        "unresolved_tickers": unresolved,
        "fx_basis": fx_basis,
        "positions": price_rows,
        "cash_eur": round(float(cash_eur or 0.0), 2),
        "total_portfolio_value_eur": round(total_value_eur, 2),
        "state_file": str(state_path),
    }
    _write_json(audit_path, audit_payload)

    ensure_csv_headers(output_dir / "index_trade_ledger.csv", ["timestamp_utc", "action", "exposure_id", "proxy_ticker", "shares_delta", "note"])
    ensure_csv_headers(output_dir / "index_recommendation_scorecard.csv", ["as_of", "exposure_id", "display_name", "score", "action", "conviction_tier"])
    append_valuation_row(
        output_dir / "index_valuation_history.csv",
        [run_date, requested_close_date, round(total_value_eur, 2), round(float(cash_eur or 0.0), 2), usd_per_eur, source_mode],
    )

    print(
        f"PRICING_PASS_{'OK' if fresh_count else 'PARTIAL'} | requested_close={requested_close_date} | "
        f"holdings={holdings_count} | fresh={fresh_count} | carried={carried_forward_count} | "
        f"weight_coverage={invested_weight_coverage_pct:.2f} | audit={audit_path.name} | source_mode={source_mode}"
    )


if __name__ == "__main__":
    main()
