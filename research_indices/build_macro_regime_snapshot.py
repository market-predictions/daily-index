from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pricing_indices.data_sources import fetch_yahoo_history
from .common import latest_report_token, resolve_requested_close_date

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


def _pct_return(rows: list[dict[str, Any]], lookback: int) -> float | None:
    if len(rows) <= lookback:
        return None
    latest = float(rows[-1]["close"])
    base = float(rows[-1 - lookback]["close"])
    if base == 0:
        return None
    return (latest / base) - 1.0


def _series_metrics(symbol: str, requested_close_date: str) -> dict[str, Any]:
    history = fetch_yahoo_history(symbol, requested_close_date=requested_close_date, range_period="1y", interval="1d")
    rows = [row for row in history["rows"] if row["date"] <= requested_close_date]
    if not rows:
        raise RuntimeError(f"No usable rows for {symbol} on or before {requested_close_date}")
    selected = rows[-1]
    return {
        "symbol": symbol,
        "label": MARKET_SERIES[symbol],
        "requested_close_date": requested_close_date,
        "selected_data_date": selected["date"],
        "latest_close": round(float(selected["close"]), 6),
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


def build_snapshot(requested_close_date: str) -> dict[str, Any]:
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
        "equity_risk_appetite": _flag(0.55 * spy20 + 0.45 * spy60),
        "growth_leadership": _flag(qqq20 - spy20, positive_cutoff=0.0075, negative_cutoff=-0.0075),
        "breadth_confirmation": _flag(iwm20 - spy20, positive_cutoff=-0.0025, negative_cutoff=-0.025),
        "europe_confirmation": _flag(fez20, positive_cutoff=0.015, negative_cutoff=-0.015),
        "japan_confirmation": _flag(ewj20, positive_cutoff=0.015, negative_cutoff=-0.015),
        "em_confirmation": _flag(eem20, positive_cutoff=0.015, negative_cutoff=-0.015),
        "duration_support": _flag(tlt20),
        "credit_support": _flag(hyg20),
        "commodity_pressure": _flag(dbc20, positive_cutoff=0.025, negative_cutoff=-0.025),
        "dollar_pressure": _flag(uup20, positive_cutoff=0.0125, negative_cutoff=-0.0125),
    }

    risk_on_score = 0.0
    risk_on_score += 0.90 if market_signals["equity_risk_appetite"] == "supportive" else (-0.90 if market_signals["equity_risk_appetite"] == "headwind" else 0.0)
    risk_on_score += 0.45 if market_signals["credit_support"] == "supportive" else (-0.45 if market_signals["credit_support"] == "headwind" else 0.0)
    risk_on_score += 0.35 if market_signals["growth_leadership"] == "supportive" else (-0.20 if market_signals["growth_leadership"] == "headwind" else 0.0)
    risk_on_score += 0.30 if market_signals["breadth_confirmation"] == "supportive" else (-0.30 if market_signals["breadth_confirmation"] == "headwind" else 0.0)
    risk_on_score += 0.20 if market_signals["duration_support"] == "supportive" else (-0.15 if market_signals["duration_support"] == "headwind" else 0.0)
    risk_on_score += -0.20 if market_signals["dollar_pressure"] == "supportive" else (0.10 if market_signals["dollar_pressure"] == "headwind" else 0.0)
    risk_on_score += -0.20 if market_signals["commodity_pressure"] == "supportive" else 0.0

    if risk_on_score >= 2.8:
        suggested_primary_regime = "Soft Landing"
    elif risk_on_score >= 0.7:
        suggested_primary_regime = "Policy Transition / Mixed Regime"
    elif risk_on_score <= -1.5:
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
            "Phase 1.1 pins all market-derived research to the same resolved requested close date as the pricing pass.",
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
    requested_close_date = args.requested_close_date or resolve_requested_close_date(output_dir)
    payload = build_snapshot(requested_close_date=requested_close_date)
    path = output_dir / "research" / f"index_macro_snapshot_{token}.json"
    _write_json(path, payload)
    print(
        f"MACRO_SNAPSHOT_OK | token={token} | file={path.name} | requested_close={requested_close_date} | suggested_primary_regime={payload['suggested_primary_regime']}"
    )


if __name__ == "__main__":
    main()
