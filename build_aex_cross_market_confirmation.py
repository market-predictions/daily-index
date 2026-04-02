#!/usr/bin/env python3
"""
Build output_aex/aex_cross_market_confirmation.json from live public market data.

This is a secondary confirmation layer. It must not replace the dedicated AEX primary technical snapshot.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests

OUTPUT_PATH = Path("output_aex/aex_cross_market_confirmation.json")
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
USER_AGENT = "Mozilla/5.0 (compatible; DailyIndexOS/1.0)"

TICKERS = {
    "dax": "^GDAXI",
    "eurostoxx50": "^STOXX50E",
    "sp500": "^GSPC",
    "vix": "^VIX",
    "eurusd": "EURUSD=X",
    "us10y_yield": "^TNX",
}


def ema(values: Iterable[float], period: int) -> list[float]:
    values = list(values)
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out = [values[0]]
    for val in values[1:]:
        out.append(alpha * val + (1.0 - alpha) * out[-1])
    return out


def fetch_closes(ticker: str, *, range_: str = "6mo", interval: str = "1d") -> list[float]:
    response = requests.get(
        YAHOO_URL.format(ticker=ticker),
        params={"range": range_, "interval": interval, "includePrePost": "false", "events": "div,splits"},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("chart", {}).get("result", [])
    if not result:
        raise RuntimeError(f"No chart result for {ticker}")
    closes = (result[0].get("indicators", {}).get("quote", [{}]) or [{}])[0].get("close", [])
    out = [float(x) for x in closes if x is not None]
    if len(out) < 60:
        raise RuntimeError(f"Insufficient data for {ticker}: {len(out)} closes")
    return out


def summarize_series(ticker: str) -> dict:
    closes = fetch_closes(ticker)
    e20 = ema(closes, 20)[-1]
    e50 = ema(closes, 50)[-1]
    last = closes[-1]
    ret20 = ((last / closes[-21]) - 1.0) if len(closes) >= 21 and closes[-21] != 0 else None
    if last > e20 > e50:
        trend = "bullish"
    elif last < e20 < e50:
        trend = "bearish"
    else:
        trend = "mixed"
    return {
        "ticker": ticker,
        "last_close": round(last, 6),
        "ema20": round(e20, 6),
        "ema50": round(e50, 6),
        "trend_state": trend,
        "return_20d": round(ret20, 6) if ret20 is not None else None,
    }


def build_payload() -> dict:
    markets = {label: summarize_series(ticker) for label, ticker in TICKERS.items()}
    supportive_breadth = sum(1 for k in ("dax", "eurostoxx50", "sp500") if markets[k]["trend_state"] == "bullish")
    defensive_flags = []
    if markets["vix"]["trend_state"] == "bullish":
        defensive_flags.append("vix_up")
    if markets["us10y_yield"]["trend_state"] == "bullish":
        defensive_flags.append("yields_up")
    if markets["eurusd"]["trend_state"] == "bearish":
        defensive_flags.append("eur_soft")

    if supportive_breadth >= 2 and not defensive_flags:
        overall = "supportive_risk"
    elif defensive_flags and supportive_breadth == 0:
        overall = "defensive_confirmation"
    else:
        overall = "mixed_confirmation"

    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider": "Yahoo Finance chart endpoint",
        "markets": markets,
        "supportive_equity_breadth_count": supportive_breadth,
        "defensive_flags": defensive_flags,
        "overall_confirmation": overall,
        "notes": [
            "This is a secondary cross-market confirmation layer.",
            "It must not replace the primary AEX technical snapshot.",
        ],
    }


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"AEX_CROSS_MARKET_CONFIRMATION_OK | file={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
