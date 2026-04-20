from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from pricing_indices.data_sources import fetch_yahoo_history

REPORT_RE = re.compile(r"weekly_indices_review_(\d{6})(?:_(\d{2}))?\.md$")

MARKET_SERIES = {
    "SPY": "U.S. large-cap risk appetite",
    "QQQ": "growth leadership",
    "IWM": "small-cap breadth",
    "FEZ": "continental Europe confirmation",
    "EWJ": "Japan confirmation",
    "EEM": "EM confirmation",
    "TLT": "duration support",
    "HYG": "credit support",
    "GLD": "defensive inflation hedge",
    "DBC": "commodity pressure",
    "UUP": "dollar pressure",
}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def latest_report_token(output_dir: Path) -> str:
    hits: list[tuple[str, int]] = []
    for path in output_dir.glob("weekly_indices_review_*.md"):
        match = REPORT_RE.match(path.name)
        if match:
            hits.append((match.group(1), int(match.group(2) or "0")))
    if not hits:
        raise FileNotFoundError("No weekly_indices_review_*.md file found")
    hits.sort(key=lambda x: (x[0], x[1]))
    return hits[-1][0]


def _pct_return(rows: list[dict[str, Any]], lookback: int) -> float | None:
    if len(rows) <= lookback:
        return None
    latest = float(rows[-1]["close"])
    base = float(rows[-1 - lookback]["close"])
    if base == 0:
        return None
    return (latest / base) - 1.0


def _series_metrics(symbol: str, requested_close_date: str | None = None) -> dict[str, Any]:
    history = fetch_yahoo_history(symbol, requested_close_date=requested_close_date, range_period="1y", interval="1d")
    rows = history["rows"]
    return {
        "symbol": symbol,
        "label": MARKET_SERIES[symbol],
        "latest_date": rows[-1]["date"],
        "latest_close": round(float(rows[-1]["close"]), 6),
        "return_20d": round(_pct_return(rows, 20) or 0.0, 6),
        "return_60d": round(_pct_return(rows, 60) or 0.0, 6),
        "currency": history["currency"],
        "source": history["source"],
    }


def _flag(score: float, positive_cutoff: float = 0.01, negative_cutoff: float = -0.01) -> str:
    if score >= positive_cutoff:
        return "supportive"
    if score <= negative_cutoff:
        return "headwind"
    return "mixed"


def build_snapshot(requested_close_date: str | None = None) -> dict[str, Any]:
    series = {symbol: _series_metrics(symbol, requested_close_date=requested_close_date) for symbol in MARKET_SERIES}

    spy20 = float(series["SPY"]["return_20d"])
    spy60 = float(series["SPY"]["return_60d"])
    qqq20 = float(series["QQQ"]["return_20d"])
    iwm20 = float(series["IWM"]["return_20d"])
    fez20 = float(series["FEZ"]["return_20d"])
    ewj20 = float(series["EWJ"]["return_20d"])
    eem20 = float(series["EEM"]["return_20d"])
    tlt20 = float(series["TLT"]["return_20d"])
    hyg20 = float(series["HYG"]["return_20d"])
    dbc20 = float(series["DBC"]["return_20d"])
    uup20 = float(series["UUP"]["return_20d"])

    market_signals = {
        "equity_risk_appetite": _flag(0.6 * spy20 + 0.4 * spy60),
        "growth_leadership": _flag(qqq20 - spy20, positive_cutoff=0.005, negative_cutoff=-0.005),
        "breadth_confirmation": _flag(iwm20 - spy20, positive_cutoff=-0.005, negative_cutoff=-0.03),
        "europe_confirmation": _flag(fez20),
        "japan_confirmation": _flag(ewj20),
        "em_confirmation": _flag(eem20),
        "duration_support": _flag(tlt20),
        "credit_support": _flag(hyg20),
        "commodity_pressure": _flag(dbc20, positive_cutoff=0.02, negative_cutoff=-0.02),
        "dollar_pressure": _flag(uup20, positive_cutoff=0.01, negative_cutoff=-0.01),
    }

    risk_on_score = 0.0
    risk_on_score += 1.0 if market_signals["equity_risk_appetite"] == "supportive" else (-1.0 if market_signals["equity_risk_appetite"] == "headwind" else 0.0)
    risk_on_score += 0.5 if market_signals["credit_support"] == "supportive" else (-0.5 if market_signals["credit_support"] == "headwind" else 0.0)
    risk_on_score += 0.4 if market_signals["growth_leadership"] == "supportive" else (-0.2 if market_signals["growth_leadership"] == "headwind" else 0.0)
    risk_on_score += 0.3 if market_signals["breadth_confirmation"] == "supportive" else (-0.3 if market_signals["breadth_confirmation"] == "headwind" else 0.0)
    risk_on_score += -0.3 if market_signals["dollar_pressure"] == "supportive" else (0.2 if market_signals["dollar_pressure"] == "headwind" else 0.0)
    risk_on_score += -0.3 if market_signals["commodity_pressure"] == "supportive" else 0.0

    if risk_on_score >= 1.2:
        suggested_primary_regime = "Soft Landing"
    elif risk_on_score >= 0.3:
        suggested_primary_regime = "Policy Transition / Mixed Regime"
    elif risk_on_score <= -1.2:
        suggested_primary_regime = "Slowdown / Defensive"
    else:
        suggested_primary_regime = "Policy Transition / Mixed Regime"

    return {
        "requested_close_date": requested_close_date,
        "series": series,
        "market_signals": market_signals,
        "risk_on_score": round(risk_on_score, 3),
        "suggested_primary_regime": suggested_primary_regime,
        "notes": [
            "This snapshot is market-derived and should support, not replace, final macro and geopolitical judgment.",
            "The first purpose of this artifact is to create a repeatable evidence base for selection rather than a purely narrative regime call.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output_indices")
    parser.add_argument("--token", default=None)
    parser.add_argument("--requested-close-date", default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    token = args.token or latest_report_token(output_dir)
    payload = build_snapshot(requested_close_date=args.requested_close_date)
    path = output_dir / "research" / f"index_macro_snapshot_{token}.json"
    _write_json(path, payload)
    print(
        f"MACRO_SNAPSHOT_OK | token={token} | file={path.name} | suggested_primary_regime={payload['suggested_primary_regime']}"
    )


if __name__ == "__main__":
    main()
