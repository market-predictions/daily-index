#!/usr/bin/env python3
"""
Build output_aex/aex_primary_technical_snapshot.json from live public underlying data.

Data source:
- Yahoo Finance chart endpoint for the AEX index ticker.

This script intentionally focuses on the **underlying** and not on option chains.
It is the primary technical snapshot producer for the AEX system.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

import requests

AEX_TICKER = "^AEX"
OUTPUT_PATH = Path("output_aex/aex_primary_technical_snapshot.json")
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
USER_AGENT = "Mozilla/5.0 (compatible; DailyIndexOS/1.0)"


@dataclass
class Bar:
    dt: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None


def ensure_output_dir() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def fetch_daily_bars(ticker: str, *, range_: str = "1y", interval: str = "1d") -> list[Bar]:
    url = YAHOO_URL.format(ticker=ticker)
    params = {
        "range": range_,
        "interval": interval,
        "includePrePost": "false",
        "events": "div,splits",
    }
    response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    payload = response.json()

    result = payload.get("chart", {}).get("result", [])
    if not result:
        raise RuntimeError("Yahoo chart response did not contain result data.")

    block = result[0]
    timestamps = block.get("timestamp", [])
    quote = (block.get("indicators", {}).get("quote", [{}]) or [{}])[0]
    opens = quote.get("open", [])
    highs = quote.get("high", [])
    lows = quote.get("low", [])
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    bars: list[Bar] = []
    for idx, ts in enumerate(timestamps):
        try:
            o = opens[idx]
            h = highs[idx]
            l = lows[idx]
            c = closes[idx]
            v = volumes[idx] if idx < len(volumes) else None
        except IndexError:
            continue
        if any(x is None for x in (o, h, l, c)):
            continue
        bars.append(
            Bar(
                dt=datetime.fromtimestamp(ts, tz=timezone.utc),
                open=float(o),
                high=float(h),
                low=float(l),
                close=float(c),
                volume=float(v) if v is not None else None,
            )
        )
    if len(bars) < 60:
        raise RuntimeError(f"Insufficient bar history returned for {ticker}: {len(bars)} bars")
    return bars


def ema(values: Iterable[float], period: int) -> list[float]:
    values = list(values)
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out: list[float] = [values[0]]
    for val in values[1:]:
        out.append(alpha * val + (1.0 - alpha) * out[-1])
    return out


def annualized_realized_vol(closes: list[float], window: int = 20) -> float | None:
    if len(closes) < window + 1:
        return None
    returns: list[float] = []
    for prev, cur in zip(closes[-(window + 1):-1], closes[-window:]):
        if prev <= 0 or cur <= 0:
            continue
        returns.append(math.log(cur / prev))
    if len(returns) < 2:
        return None
    stdev = statistics.stdev(returns)
    return stdev * math.sqrt(252.0)


def build_weekly_bars(daily_bars: list[Bar]) -> list[Bar]:
    grouped: dict[tuple[int, int], list[Bar]] = defaultdict(list)
    for bar in daily_bars:
        iso = bar.dt.isocalendar()
        grouped[(iso.year, iso.week)].append(bar)

    weekly: list[Bar] = []
    for _, week_bars in sorted(grouped.items(), key=lambda kv: kv[0]):
        ordered = sorted(week_bars, key=lambda b: b.dt)
        weekly.append(
            Bar(
                dt=ordered[-1].dt,
                open=ordered[0].open,
                high=max(b.high for b in ordered),
                low=min(b.low for b in ordered),
                close=ordered[-1].close,
                volume=sum((b.volume or 0.0) for b in ordered),
            )
        )
    return weekly


def infer_trend_state(last_close: float, d1_ema20: float, d1_ema50: float, w1_ema13: float, w1_ema26: float) -> str:
    bullish_daily = last_close > d1_ema20 > d1_ema50
    bearish_daily = last_close < d1_ema20 < d1_ema50
    bullish_weekly = last_close > w1_ema13 > w1_ema26
    bearish_weekly = last_close < w1_ema13 < w1_ema26
    if bullish_daily and bullish_weekly:
        return "bullish"
    if bearish_daily and bearish_weekly:
        return "bearish"
    return "mixed"


def build_snapshot() -> dict:
    daily = fetch_daily_bars(AEX_TICKER)
    closes = [b.close for b in daily]
    d1_ema20 = ema(closes, 20)[-1]
    d1_ema50 = ema(closes, 50)[-1]

    weekly = build_weekly_bars(daily)
    weekly_closes = [b.close for b in weekly]
    w1_ema13 = ema(weekly_closes, 13)[-1]
    w1_ema26 = ema(weekly_closes, 26)[-1]

    last = daily[-1]
    rv20 = annualized_realized_vol(closes, 20)
    rv60 = annualized_realized_vol(closes, 60)

    support_levels = [round(min(b.low for b in daily[-20:]), 2), round(min(b.low for b in daily[-60:]), 2)]
    resistance_levels = [round(max(b.high for b in daily[-20:]), 2), round(max(b.high for b in daily[-60:]), 2)]

    trend_state = infer_trend_state(last.close, d1_ema20, d1_ema50, w1_ema13, w1_ema26)
    confidence = "high" if trend_state in {"bullish", "bearish"} else "medium"

    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "underlying": "AEX",
        "provider": "Yahoo Finance chart endpoint",
        "ticker": AEX_TICKER,
        "reference_price": round(last.close, 4),
        "last_bar_date": last.dt.strftime("%Y-%m-%d"),
        "trend_state": trend_state,
        "realized_vol_state": {
            "rv20_annualized": round(rv20, 6) if rv20 is not None else None,
            "rv60_annualized": round(rv60, 6) if rv60 is not None else None,
        },
        "moving_average_context": {
            "d1_ema20": round(d1_ema20, 4),
            "d1_ema50": round(d1_ema50, 4),
            "w1_ema13": round(w1_ema13, 4),
            "w1_ema26": round(w1_ema26, 4),
        },
        "support_levels": sorted(set(support_levels)),
        "resistance_levels": sorted(set(resistance_levels)),
        "breadth_context": "not_provided_in_v1",
        "technical_confidence": confidence,
        "freshness_status": "live_public_fetch",
        "notes": [
            "Primary AEX technical snapshot is based on the underlying, not on options.",
            "Breadth internals are intentionally omitted in v1 unless a dedicated breadth feed is added.",
        ],
    }


def main() -> None:
    ensure_output_dir()
    snapshot = build_snapshot()
    OUTPUT_PATH.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"AEX_PRIMARY_TECHNICAL_OK | file={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
