#!/usr/bin/env python3
"""
Build output_aex/aex_option_surface_snapshot.json.

Priority:
1. Try a live public Yahoo Finance options-chain fetch for ^AEX.
2. If the public chain is missing / incomplete, fall back to a provider-fed JSON file.
3. If neither path is usable, write an explicit unavailable snapshot.

This script is intentionally conservative: incomplete public chain coverage should not be mistaken for a valid surface.
"""

from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

OUTPUT_PATH = Path("output_aex/aex_option_surface_snapshot.json")
PRIMARY_TECH_PATH = Path("output_aex/aex_primary_technical_snapshot.json")
PROVIDER_INPUT_PATH = Path("input_aex/aex_option_chain_provider.json")
YAHOO_OPTIONS_URL = "https://query2.finance.yahoo.com/v7/finance/options/%5EAEX"
USER_AGENT = "Mozilla/5.0 (compatible; DailyIndexOS/1.0)"


def load_primary_realized_vol() -> float | None:
    if not PRIMARY_TECH_PATH.exists():
        return None
    try:
        payload = json.loads(PRIMARY_TECH_PATH.read_text(encoding="utf-8"))
        return payload.get("realized_vol_state", {}).get("rv20_annualized")
    except Exception:
        return None


def try_fetch_yahoo_chain() -> dict[str, Any] | None:
    response = requests.get(YAHOO_OPTIONS_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    result = payload.get("optionChain", {}).get("result", [])
    if not result:
        return None
    block = result[0]
    expirations = block.get("expirationDates", []) or []
    options = block.get("options", []) or []
    if not expirations and not options:
        return None
    return block


def load_provider_chain() -> dict[str, Any] | None:
    if not PROVIDER_INPUT_PATH.exists():
        return None
    return json.loads(PROVIDER_INPUT_PATH.read_text(encoding="utf-8"))


def clean_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def median_relative_spread(rows: list[dict[str, Any]]) -> float | None:
    rels: list[float] = []
    for row in rows:
        bid = clean_float(row.get("bid"))
        ask = clean_float(row.get("ask"))
        if bid is None or ask is None or ask < bid:
            continue
        mid = (bid + ask) / 2.0
        if mid <= 0:
            continue
        rels.append((ask - bid) / mid)
    return statistics.median(rels) if rels else None


def pick_atm_iv(calls: list[dict[str, Any]], puts: list[dict[str, Any]], spot: float) -> float | None:
    candidates: list[tuple[float, float]] = []
    for row in calls + puts:
        strike = clean_float(row.get("strike"))
        iv = clean_float(row.get("impliedVolatility"))
        if strike is None or iv is None:
            continue
        candidates.append((abs(strike - spot), iv))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    nearest = [iv for _, iv in candidates[:6]]
    return statistics.mean(nearest) if nearest else None


def approximate_skew(calls: list[dict[str, Any]], puts: list[dict[str, Any]], spot: float) -> dict[str, float | None]:
    put_ivs: list[float] = []
    call_ivs: list[float] = []
    lower = spot * 0.95
    upper = spot * 1.05
    for row in puts:
        strike = clean_float(row.get("strike"))
        iv = clean_float(row.get("impliedVolatility"))
        if strike is not None and iv is not None and strike <= spot and strike >= lower:
            put_ivs.append(iv)
    for row in calls:
        strike = clean_float(row.get("strike"))
        iv = clean_float(row.get("impliedVolatility"))
        if strike is not None and iv is not None and strike >= spot and strike <= upper:
            call_ivs.append(iv)
    put_iv = statistics.mean(put_ivs) if put_ivs else None
    call_iv = statistics.mean(call_ivs) if call_ivs else None
    skew = (put_iv - call_iv) if put_iv is not None and call_iv is not None else None
    return {
        "near_put_iv": put_iv,
        "near_call_iv": call_iv,
        "put_minus_call_iv": skew,
    }


def implied_move_pct(calls: list[dict[str, Any]], puts: list[dict[str, Any]], spot: float) -> float | None:
    candidates: list[tuple[float, dict[str, Any], str]] = []
    for row in calls:
        strike = clean_float(row.get("strike"))
        if strike is not None:
            candidates.append((abs(strike - spot), row, "call"))
    for row in puts:
        strike = clean_float(row.get("strike"))
        if strike is not None:
            candidates.append((abs(strike - spot), row, "put"))
    if len(candidates) < 2:
        return None
    candidates.sort(key=lambda x: x[0])
    chosen = candidates[:8]
    call_mid: list[float] = []
    put_mid: list[float] = []
    for _, row, typ in chosen:
        bid = clean_float(row.get("bid")) or 0.0
        ask = clean_float(row.get("ask")) or 0.0
        last = clean_float(row.get("lastPrice")) or 0.0
        mid = (bid + ask) / 2.0 if bid > 0 or ask > 0 else last
        if mid <= 0:
            continue
        if typ == "call":
            call_mid.append(mid)
        else:
            put_mid.append(mid)
    if not call_mid or not put_mid or spot <= 0:
        return None
    return (statistics.mean(call_mid) + statistics.mean(put_mid)) / spot


def analyze_single_expiry(expiry_ts: int, spot: float, calls: list[dict[str, Any]], puts: list[dict[str, Any]], realized_vol: float | None) -> dict[str, Any]:
    atm_iv = pick_atm_iv(calls, puts, spot)
    skew = approximate_skew(calls, puts, spot)
    spread_call = median_relative_spread(calls)
    spread_put = median_relative_spread(puts)
    spread_med = statistics.mean([x for x in (spread_call, spread_put) if x is not None]) if any(x is not None for x in (spread_call, spread_put)) else None
    implied_move = implied_move_pct(calls, puts, spot)

    if atm_iv is None:
        regime = "surface_unavailable"
    elif realized_vol is not None and atm_iv <= realized_vol * 0.95:
        regime = "long_premium_favorable"
    elif realized_vol is not None and atm_iv >= realized_vol * 1.10 and (spread_med is not None and spread_med < 0.25):
        regime = "short_premium_favorable"
    elif spread_med is not None and spread_med < 0.25:
        regime = "financed_premium_favorable"
    else:
        regime = "surface_unattractive"

    return {
        "expiry_unix": expiry_ts,
        "expiry_date_utc": datetime.fromtimestamp(expiry_ts, tz=timezone.utc).strftime("%Y-%m-%d"),
        "atm_iv": round(atm_iv, 6) if atm_iv is not None else None,
        "skew_metrics": {k: (round(v, 6) if v is not None else None) for k, v in skew.items()},
        "median_relative_spread": round(spread_med, 6) if spread_med is not None else None,
        "implied_move_pct": round(implied_move, 6) if implied_move is not None else None,
        "surface_regime": regime,
        "call_count": len(calls),
        "put_count": len(puts),
    }


def build_from_yahoo(block: dict[str, Any], realized_vol: float | None) -> dict[str, Any] | None:
    quote = block.get("quote") or {}
    spot = clean_float(quote.get("regularMarketPrice"))
    if spot is None:
        return None

    expiries: list[int] = list(block.get("expirationDates") or [])
    option_sets = list(block.get("options") or [])
    analyses: list[dict[str, Any]] = []

    first_set = option_sets[0] if option_sets else {}
    if first_set:
        analyses.append(
            analyze_single_expiry(
                clean_float(first_set.get("expirationDate")) or expiries[0] if expiries else 0,
                spot,
                list(first_set.get("calls") or []),
                list(first_set.get("puts") or []),
                realized_vol,
            )
        )

    if not analyses or analyses[0]["call_count"] + analyses[0]["put_count"] == 0:
        return None

    next_iv = analyses[0].get("atm_iv")
    event_distortion = False
    if len(analyses) >= 2 and analyses[1].get("atm_iv") and next_iv:
        event_distortion = next_iv > analyses[1]["atm_iv"] * 1.15

    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "underlying": "AEX",
        "provider": "Yahoo Finance options chain",
        "provider_mode": "live_public_fetch",
        "expiries": [a["expiry_date_utc"] for a in analyses],
        "atm_iv_by_expiry": {a["expiry_date_utc"]: a["atm_iv"] for a in analyses},
        "realized_vol_reference": {"rv20_annualized": realized_vol},
        "skew_metrics": analyses[0]["skew_metrics"],
        "term_structure_metrics": {"limited_public_coverage": True},
        "liquidity_checks": {
            "spread_status": "acceptable" if analyses[0].get("median_relative_spread") is not None and analyses[0]["median_relative_spread"] < 0.25 else "wide_or_unknown",
            "open_interest_status": "not_available_in_public_v1",
        },
        "implied_move_pct_next_expiry": analyses[0].get("implied_move_pct"),
        "event_distortion_flag": event_distortion,
        "surface_regime": analyses[0].get("surface_regime"),
        "notes": [
            "Public chain coverage can be incomplete; do not over-trust missing expiries or empty sides.",
            "Use provider-fed chain input when institutional-grade option data is available.",
        ],
    }


def build_from_provider(payload: dict[str, Any], realized_vol: float | None) -> dict[str, Any]:
    spot = clean_float(payload.get("spot_price"))
    expiries = payload.get("expiries") or []
    if spot is None or not expiries:
        raise RuntimeError("Provider option-chain payload is missing spot_price or expiries.")

    analyses: list[dict[str, Any]] = []
    for exp in expiries:
        expiry_ts = int(exp.get("expiry_unix") or 0)
        calls = list(exp.get("calls") or [])
        puts = list(exp.get("puts") or [])
        analyses.append(analyze_single_expiry(expiry_ts, spot, calls, puts, realized_vol))

    analyses = [a for a in analyses if a["expiry_unix"]]
    analyses.sort(key=lambda x: x["expiry_unix"])
    if not analyses:
        raise RuntimeError("Provider option-chain payload did not produce valid expiry analyses.")

    event_distortion = False
    if len(analyses) >= 2 and analyses[0].get("atm_iv") and analyses[1].get("atm_iv"):
        event_distortion = analyses[0]["atm_iv"] > analyses[1]["atm_iv"] * 1.15

    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "underlying": "AEX",
        "provider": payload.get("provider", "external_provider_file"),
        "provider_mode": "provider_input_file",
        "expiries": [a["expiry_date_utc"] for a in analyses],
        "atm_iv_by_expiry": {a["expiry_date_utc"]: a["atm_iv"] for a in analyses},
        "realized_vol_reference": {"rv20_annualized": realized_vol},
        "skew_metrics": analyses[0]["skew_metrics"],
        "term_structure_metrics": {
            "front_to_next_iv_ratio": round((analyses[0]["atm_iv"] / analyses[1]["atm_iv"]), 6) if len(analyses) >= 2 and analyses[0].get("atm_iv") and analyses[1].get("atm_iv") else None
        },
        "liquidity_checks": {
            "spread_status": "acceptable" if analyses[0].get("median_relative_spread") is not None and analyses[0]["median_relative_spread"] < 0.25 else "wide_or_unknown",
            "open_interest_status": "provider_dependent",
        },
        "implied_move_pct_next_expiry": analyses[0].get("implied_move_pct"),
        "event_distortion_flag": event_distortion,
        "surface_regime": analyses[0].get("surface_regime"),
        "notes": [
            "Provider file is preferred when institutional-grade chain data is available.",
        ],
    }


def unavailable_snapshot(reason: str, realized_vol: float | None) -> dict[str, Any]:
    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "underlying": "AEX",
        "provider": "unavailable",
        "provider_mode": "unavailable",
        "expiries": [],
        "atm_iv_by_expiry": {},
        "realized_vol_reference": {"rv20_annualized": realized_vol},
        "skew_metrics": {},
        "term_structure_metrics": {},
        "liquidity_checks": {
            "spread_status": "unknown",
            "open_interest_status": "unknown",
        },
        "implied_move_pct_next_expiry": None,
        "event_distortion_flag": False,
        "surface_regime": "surface_unavailable",
        "notes": [reason],
    }


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    realized_vol = load_primary_realized_vol()

    payload: dict[str, Any]
    try:
        live = try_fetch_yahoo_chain()
        if live is not None:
            built = build_from_yahoo(live, realized_vol)
            if built is not None:
                payload = built
            else:
                provider = load_provider_chain()
                payload = build_from_provider(provider, realized_vol) if provider else unavailable_snapshot("Public options chain was incomplete and no provider input file was found.", realized_vol)
        else:
            provider = load_provider_chain()
            payload = build_from_provider(provider, realized_vol) if provider else unavailable_snapshot("Public options chain was unavailable and no provider input file was found.", realized_vol)
    except Exception as exc:
        provider = load_provider_chain()
        if provider is not None:
            payload = build_from_provider(provider, realized_vol)
            payload.setdefault("notes", []).append(f"Live public fetch failed; provider fallback used: {exc}")
        else:
            payload = unavailable_snapshot(f"Option surface build failed and no provider input file was found: {exc}", realized_vol)

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"AEX_OPTION_SURFACE_OK | file={OUTPUT_PATH} | mode={payload.get('provider_mode')}")


if __name__ == "__main__":
    main()
