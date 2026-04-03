#!/usr/bin/env python3
"""
Build output_aex/aex_structure_candidates.json.

Purpose:
- turn the current regime + option-surface state into actual strike-aware structure candidates
- keep all proposed structures defined-risk
- stay conservative by default
- resolve option-chain inputs using an explicit source policy

Source policy is controlled by input_aex/aex_data_provider_config.json.
Default policy prefers provider-fed input first, then Yahoo fallback only when allowed.

The output is a candidate board, not an execution record.
The report generator can decide whether one of the candidates earns approval.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from aex_option_chain_ingest import DEFAULT_DELAYED_SNAPSHOT_PATH, clean_float, load_normalized_chain_payload

OUTPUT_DIR = Path("output_aex")
OUTPUT_PATH = OUTPUT_DIR / "aex_structure_candidates.json"

PRIMARY_PATH = OUTPUT_DIR / "aex_primary_technical_snapshot.json"
CROSS_PATH = OUTPUT_DIR / "aex_cross_market_confirmation.json"
SURFACE_PATH = OUTPUT_DIR / "aex_option_surface_snapshot.json"
MACRO_PATH = OUTPUT_DIR / "aex_macro_snapshot.json"
PORTFOLIO_PATH = OUTPUT_DIR / "aex_option_portfolio_state.json"
DEFAULT_PROVIDER_INPUT_PATH = Path("input_aex/aex_option_chain_provider.json")
CONFIG_PATH = Path("input_aex/aex_data_provider_config.json")

YAHOO_OPTIONS_URL = "https://query2.finance.yahoo.com/v7/finance/options/%5EAEX"
USER_AGENT = "Mozilla/5.0 (compatible; DailyIndexOS/1.0)"

ALLOWED_POLICIES = {"provider_first", "yahoo_first", "provider_only", "yahoo_only"}
ALLOWED_FAMILIES = {
    "collar_style_protection",
    "defined_risk_bullish_financed_convexity",
    "defined_risk_bearish_financed_convexity",
    "range_defined_risk_premium_structure",
    "hedge_only",
}


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_provider_config() -> dict[str, Any]:
    default = {
        "option_chain_source_policy": "provider_first",
        "provider_input_path": str(DEFAULT_PROVIDER_INPUT_PATH),
        "allow_yahoo_fallback": True,
    }
    if not CONFIG_PATH.exists():
        return default
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return default

    config = dict(default)
    if isinstance(payload, dict):
        config.update(payload)

    policy = str(config.get("option_chain_source_policy", default["option_chain_source_policy"]))
    if policy not in ALLOWED_POLICIES:
        policy = default["option_chain_source_policy"]
    config["option_chain_source_policy"] = policy
    config["allow_yahoo_fallback"] = bool(config.get("allow_yahoo_fallback", True))
    config["provider_input_path"] = str(config.get("provider_input_path") or default["provider_input_path"])
    return config


def source_order(config: dict[str, Any]) -> list[str]:
    policy = config["option_chain_source_policy"]
    if policy == "provider_only":
        return ["provider"]
    if policy == "yahoo_only":
        return ["yahoo"]
    if policy == "yahoo_first":
        return ["yahoo", "provider"]
    order = ["provider", "yahoo"]
    if not config.get("allow_yahoo_fallback", True):
        order = ["provider"]
    return order


def nearest_strike(rows: list[dict[str, Any]], target: float, side: str | None = None) -> dict[str, Any] | None:
    filtered = []
    for row in rows:
        strike = clean_float(row.get("strike"))
        if strike is None:
            continue
        if side == "above" and strike < target:
            continue
        if side == "below" and strike > target:
            continue
        filtered.append((abs(strike - target), strike, row))
    if not filtered:
        return None
    filtered.sort(key=lambda x: (x[0], x[1]))
    return filtered[0][2]


def first_strike_above(rows: list[dict[str, Any]], reference: float) -> dict[str, Any] | None:
    filtered = []
    for row in rows:
        strike = clean_float(row.get("strike"))
        if strike is None or strike <= reference:
            continue
        filtered.append((strike, row))
    if not filtered:
        return None
    filtered.sort(key=lambda x: x[0])
    return filtered[0][1]


def first_strike_below(rows: list[dict[str, Any]], reference: float) -> dict[str, Any] | None:
    filtered = []
    for row in rows:
        strike = clean_float(row.get("strike"))
        if strike is None or strike >= reference:
            continue
        filtered.append((strike, row))
    if not filtered:
        return None
    filtered.sort(key=lambda x: x[0], reverse=True)
    return filtered[0][1]


def row_mid(row: dict[str, Any]) -> float | None:
    bid = clean_float(row.get("bid"))
    ask = clean_float(row.get("ask"))
    last = clean_float(row.get("lastPrice"))
    if bid is not None and ask is not None and ask >= bid and (bid > 0 or ask > 0):
        return (bid + ask) / 2.0
    return last


def fetch_live_chain() -> dict[str, Any] | None:
    response = requests.get(YAHOO_OPTIONS_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    result = payload.get("optionChain", {}).get("result", [])
    if not result:
        return None
    block = result[0]
    option_sets = block.get("options") or []
    if not option_sets:
        return None
    first = option_sets[0]
    return {
        "provider": "Yahoo Finance options chain",
        "spot_price": (block.get("quote") or {}).get("regularMarketPrice"),
        "expiries": [
            {
                "expiry_unix": first.get("expirationDate"),
                "calls": first.get("calls") or [],
                "puts": first.get("puts") or [],
            }
        ],
    }


def load_provider_chain(config: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    candidate_paths = [Path(str(config.get("provider_input_path") or DEFAULT_PROVIDER_INPUT_PATH)), DEFAULT_DELAYED_SNAPSHOT_PATH]
    seen: set[str] = set()
    last_error: Exception | None = None

    for provider_path in candidate_paths:
        path_key = str(provider_path)
        if path_key in seen:
            continue
        seen.add(path_key)
        if not provider_path.exists():
            continue
        try:
            payload = load_normalized_chain_payload(provider_path)
            if payload is not None:
                return payload, str(provider_path)
        except Exception as exc:
            last_error = exc
            continue

    if last_error is not None:
        raise last_error
    return None, None


def load_chain_payload(config: dict[str, Any]) -> tuple[dict[str, Any] | None, str, list[str], str | None]:
    errors: list[str] = []
    for source in source_order(config):
        if source == "provider":
            try:
                provider, used_path = load_provider_chain(config)
                if provider is None:
                    errors.append("provider_input_missing")
                    continue
                return provider, "provider_input_file", errors, used_path
            except Exception as exc:
                errors.append(f"provider_failed: {exc}")
                continue
        if source == "yahoo":
            try:
                live = fetch_live_chain()
                if not live:
                    errors.append("yahoo_chain_missing")
                    continue
                return live, "live_public_fetch", errors, None
            except Exception as exc:
                errors.append(f"yahoo_failed: {exc}")
                continue
    return None, "unavailable", errors, None


def derive_directional_regime(primary: dict[str, Any] | None, cross: dict[str, Any] | None, macro: dict[str, Any] | None, surface: dict[str, Any] | None) -> str:
    if surface and surface.get("event_distortion_flag"):
        return "unstable"
    trend = (primary or {}).get("trend_state", "unknown")
    cross_overall = (cross or {}).get("overall_confirmation", "unknown")
    macro_regime = (macro or {}).get("macro_regime", "unknown")
    if trend == "bullish" and cross_overall == "supportive_risk" and macro_regime not in {"risk_defensive", "restrictive_with_inflation_reacceleration"}:
        return "bullish"
    if trend == "bearish" and cross_overall == "defensive_confirmation":
        return "bearish"
    if trend in {"bullish", "bearish"}:
        return "mixed"
    return "unstable"


def structure_score(base: float, *penalties: float) -> float:
    return max(0.0, min(10.0, base - sum(penalties)))


def candidate_meta(surface: dict[str, Any] | None, chain_mode: str, config: dict[str, Any]) -> dict[str, Any]:
    return {
        "provider_mode": chain_mode,
        "source_policy": config["option_chain_source_policy"],
        "provider_input_path": config["provider_input_path"],
        "surface_regime": (surface or {}).get("surface_regime", "surface_unavailable"),
        "event_distortion_flag": bool((surface or {}).get("event_distortion_flag", False)),
    }


def build_bullish_structure(spot: float, expiry_unix: int, calls: list[dict[str, Any]], puts: list[dict[str, Any]], chain_mode: str, surface: dict[str, Any] | None, config: dict[str, Any]) -> dict[str, Any] | None:
    long_call = nearest_strike(calls, spot, None)
    long_call_strike = clean_float((long_call or {}).get("strike")) if long_call else None
    short_call = nearest_strike(calls, spot * 1.02, "above") or first_strike_above(calls, long_call_strike if long_call_strike is not None else spot)
    short_put = nearest_strike(puts, spot * 0.98, "below") or first_strike_below(puts, spot)
    short_put_strike = clean_float((short_put or {}).get("strike")) if short_put else None
    long_put = nearest_strike(puts, spot * 0.95, "below") or first_strike_below(puts, short_put_strike if short_put_strike is not None else spot)
    if not all([long_call, short_call, short_put, long_put]):
        return None

    lc_mid = row_mid(long_call)
    sc_mid = row_mid(short_call)
    sp_mid = row_mid(short_put)
    lp_mid = row_mid(long_put)
    if any(x is None for x in (lc_mid, sc_mid, sp_mid, lp_mid)):
        return None

    lc_strike = clean_float(long_call["strike"])
    sc_strike = clean_float(short_call["strike"])
    sp_strike = clean_float(short_put["strike"])
    lp_strike = clean_float(long_put["strike"])
    if None in (lc_strike, sc_strike, sp_strike, lp_strike):
        return None

    debit_call_spread = lc_mid - sc_mid
    credit_put_spread = sp_mid - lp_mid
    net_debit = debit_call_spread - credit_put_spread
    call_width = sc_strike - lc_strike
    put_width = sp_strike - lp_strike
    max_loss = max(0.0, net_debit) + max(0.0, put_width - max(0.0, credit_put_spread))
    max_gain = max(0.0, call_width - max(0.0, net_debit))
    financing_ratio = credit_put_spread / debit_call_spread if debit_call_spread > 0 else 0.0

    penalties = []
    if chain_mode == "live_public_fetch":
        penalties.append(0.7)
    if (surface or {}).get("event_distortion_flag"):
        penalties.append(2.0)

    return {
        "structure_name": "Bullish call spread financed by put credit spread",
        "family": "defined_risk_bullish_financed_convexity",
        "regime_tag": "bullish",
        "expiry": datetime.fromtimestamp(expiry_unix, tz=timezone.utc).strftime("%Y-%m-%d"),
        "long_legs": [
            {"type": "call", "action": "buy", "strike": lc_strike, "premium_est": round(lc_mid, 4)},
            {"type": "put", "action": "buy", "strike": lp_strike, "premium_est": round(lp_mid, 4)},
        ],
        "short_legs": [
            {"type": "call", "action": "sell", "strike": sc_strike, "premium_est": round(sc_mid, 4)},
            {"type": "put", "action": "sell", "strike": sp_strike, "premium_est": round(sp_mid, 4)},
        ],
        "net_premium_type": "credit" if net_debit < 0 else "debit",
        "net_debit_credit": round(abs(net_debit), 4),
        "max_gain": round(max_gain * 100.0, 2),
        "max_loss": round(max_loss * 100.0, 2),
        "break_even": round(lc_strike + max(0.0, net_debit), 4),
        "financing_ratio": round(max(0.0, financing_ratio), 4),
        "convexity_retained_score": round(structure_score(7.4, *penalties), 2),
        "theta_funding_score": round(structure_score(7.0, 0.2 if financing_ratio < 0.35 else 0.0, *penalties), 2),
        "tail_cleanliness_score": round(structure_score(6.8, 0.5 if put_width > call_width else 0.0, *penalties), 2),
        "event_risk_note": "Use extra caution if front-expiry event premium is elevated.",
        "execution_status": "candidate_only",
        "selection_confidence": round(structure_score(6.6, *penalties), 2),
        **candidate_meta(surface, chain_mode, config),
    }


def build_bearish_structure(spot: float, expiry_unix: int, calls: list[dict[str, Any]], puts: list[dict[str, Any]], chain_mode: str, surface: dict[str, Any] | None, config: dict[str, Any]) -> dict[str, Any] | None:
    long_put = nearest_strike(puts, spot, None)
    long_put_strike = clean_float((long_put or {}).get("strike")) if long_put else None
    short_put = nearest_strike(puts, spot * 0.98, "below") or first_strike_below(puts, long_put_strike if long_put_strike is not None else spot)
    short_call = nearest_strike(calls, spot * 1.02, "above") or first_strike_above(calls, spot)
    short_call_strike = clean_float((short_call or {}).get("strike")) if short_call else None
    long_call = nearest_strike(calls, spot * 1.05, "above") or first_strike_above(calls, short_call_strike if short_call_strike is not None else spot)
    if not all([long_put, short_put, short_call, long_call]):
        return None

    lp_mid = row_mid(long_put)
    sp_mid = row_mid(short_put)
    sc_mid = row_mid(short_call)
    lc_mid = row_mid(long_call)
    if any(x is None for x in (lp_mid, sp_mid, sc_mid, lc_mid)):
        return None

    lp_strike = clean_float(long_put["strike"])
    sp_strike = clean_float(short_put["strike"])
    sc_strike = clean_float(short_call["strike"])
    lc_strike = clean_float(long_call["strike"])
    if None in (lp_strike, sp_strike, sc_strike, lc_strike):
        return None

    debit_put_spread = lp_mid - sp_mid
    credit_call_spread = sc_mid - lc_mid
    net_debit = debit_put_spread - credit_call_spread
    put_width = lp_strike - sp_strike
    call_width = lc_strike - sc_strike
    max_loss = max(0.0, net_debit) + max(0.0, call_width - max(0.0, credit_call_spread))
    max_gain = max(0.0, put_width - max(0.0, net_debit))
    financing_ratio = credit_call_spread / debit_put_spread if debit_put_spread > 0 else 0.0

    penalties = []
    if chain_mode == "live_public_fetch":
        penalties.append(0.7)
    if (surface or {}).get("event_distortion_flag"):
        penalties.append(2.0)

    return {
        "structure_name": "Bearish put spread financed by call credit spread",
        "family": "defined_risk_bearish_financed_convexity",
        "regime_tag": "bearish",
        "expiry": datetime.fromtimestamp(expiry_unix, tz=timezone.utc).strftime("%Y-%m-%d"),
        "long_legs": [
            {"type": "put", "action": "buy", "strike": lp_strike, "premium_est": round(lp_mid, 4)},
            {"type": "call", "action": "buy", "strike": lc_strike, "premium_est": round(lc_mid, 4)},
        ],
        "short_legs": [
            {"type": "put", "action": "sell", "strike": sp_strike, "premium_est": round(sp_mid, 4)},
            {"type": "call", "action": "sell", "strike": sc_strike, "premium_est": round(sc_mid, 4)},
        ],
        "net_premium_type": "credit" if net_debit < 0 else "debit",
        "net_debit_credit": round(abs(net_debit), 4),
        "max_gain": round(max_gain * 100.0, 2),
        "max_loss": round(max_loss * 100.0, 2),
        "break_even": round(lp_strike - max(0.0, net_debit), 4),
        "financing_ratio": round(max(0.0, financing_ratio), 4),
        "convexity_retained_score": round(structure_score(7.4, *penalties), 2),
        "theta_funding_score": round(structure_score(7.0, 0.2 if financing_ratio < 0.35 else 0.0, *penalties), 2),
        "tail_cleanliness_score": round(structure_score(6.8, 0.5 if call_width > put_width else 0.0, *penalties), 2),
        "event_risk_note": "Use extra caution if front-expiry event premium is elevated.",
        "execution_status": "candidate_only",
        "selection_confidence": round(structure_score(6.6, *penalties), 2),
        **candidate_meta(surface, chain_mode, config),
    }


def build_range_structure(spot: float, expiry_unix: int, calls: list[dict[str, Any]], puts: list[dict[str, Any]], chain_mode: str, surface: dict[str, Any] | None, config: dict[str, Any]) -> dict[str, Any] | None:
    short_put = nearest_strike(puts, spot * 0.98, "below") or first_strike_below(puts, spot)
    short_put_strike = clean_float((short_put or {}).get("strike")) if short_put else None
    long_put = nearest_strike(puts, spot * 0.95, "below") or first_strike_below(puts, short_put_strike if short_put_strike is not None else spot)
    short_call = nearest_strike(calls, spot * 1.02, "above") or first_strike_above(calls, spot)
    short_call_strike = clean_float((short_call or {}).get("strike")) if short_call else None
    long_call = nearest_strike(calls, spot * 1.05, "above") or first_strike_above(calls, short_call_strike if short_call_strike is not None else spot)
    if not all([short_put, long_put, short_call, long_call]):
        return None

    sp_mid = row_mid(short_put)
    lp_mid = row_mid(long_put)
    sc_mid = row_mid(short_call)
    lc_mid = row_mid(long_call)
    if any(x is None for x in (sp_mid, lp_mid, sc_mid, lc_mid)):
        return None

    sp_strike = clean_float(short_put["strike"])
    lp_strike = clean_float(long_put["strike"])
    sc_strike = clean_float(short_call["strike"])
    lc_strike = clean_float(long_call["strike"])
    if None in (sp_strike, lp_strike, sc_strike, lc_strike):
        return None

    net_credit = (sp_mid - lp_mid) + (sc_mid - lc_mid)
    width = max(sp_strike - lp_strike, lc_strike - sc_strike)
    max_loss = max(0.0, width - max(0.0, net_credit))

    penalties = [1.0]
    if chain_mode == "live_public_fetch":
        penalties.append(0.7)
    if (surface or {}).get("event_distortion_flag"):
        penalties.append(2.5)

    return {
        "structure_name": "Defined-risk range premium structure",
        "family": "range_defined_risk_premium_structure",
        "regime_tag": "range",
        "expiry": datetime.fromtimestamp(expiry_unix, tz=timezone.utc).strftime("%Y-%m-%d"),
        "long_legs": [
            {"type": "put", "action": "buy", "strike": lp_strike, "premium_est": round(lp_mid, 4)},
            {"type": "call", "action": "buy", "strike": lc_strike, "premium_est": round(lc_mid, 4)},
        ],
        "short_legs": [
            {"type": "put", "action": "sell", "strike": sp_strike, "premium_est": round(sp_mid, 4)},
            {"type": "call", "action": "sell", "strike": sc_strike, "premium_est": round(sc_mid, 4)},
        ],
        "net_premium_type": "credit",
        "net_debit_credit": round(max(0.0, net_credit), 4),
        "max_gain": round(max(0.0, net_credit) * 100.0, 2),
        "max_loss": round(max_loss * 100.0, 2),
        "break_even": [round(sp_strike - max(0.0, net_credit), 4), round(sc_strike + max(0.0, net_credit), 4)],
        "financing_ratio": 0.0,
        "convexity_retained_score": round(structure_score(2.8, *penalties), 2),
        "theta_funding_score": round(structure_score(7.2, *penalties), 2),
        "tail_cleanliness_score": round(structure_score(6.4, *penalties), 2),
        "event_risk_note": "Only appropriate in low-event, low-instability conditions.",
        "execution_status": "candidate_only",
        "selection_confidence": round(structure_score(4.2, *penalties), 2),
        **candidate_meta(surface, chain_mode, config),
    }


def current_underlying_exposure(portfolio: dict[str, Any] | None) -> bool:
    if not portfolio:
        return False
    return bool(portfolio.get("underlying_exposure", {}).get("long_aex_units", 0))


def build_collar(spot: float, expiry_unix: int, calls: list[dict[str, Any]], puts: list[dict[str, Any]], chain_mode: str, surface: dict[str, Any] | None, portfolio: dict[str, Any] | None, config: dict[str, Any]) -> dict[str, Any] | None:
    if not current_underlying_exposure(portfolio):
        return None
    long_put = nearest_strike(puts, spot * 0.98, "below") or first_strike_below(puts, spot)
    short_call = nearest_strike(calls, spot * 1.03, "above") or first_strike_above(calls, spot)
    if not all([long_put, short_call]):
        return None
    lp_mid = row_mid(long_put)
    sc_mid = row_mid(short_call)
    lp_strike = clean_float(long_put["strike"])
    sc_strike = clean_float(short_call["strike"])
    if None in (lp_mid, sc_mid, lp_strike, sc_strike):
        return None

    net_cost = lp_mid - sc_mid
    financing_ratio = sc_mid / lp_mid if lp_mid > 0 else 0.0
    penalties = []
    if chain_mode == "live_public_fetch":
        penalties.append(0.7)

    return {
        "structure_name": "Protective collar on existing AEX exposure",
        "family": "collar_style_protection",
        "regime_tag": "hedge_only",
        "expiry": datetime.fromtimestamp(expiry_unix, tz=timezone.utc).strftime("%Y-%m-%d"),
        "long_legs": [{"type": "put", "action": "buy", "strike": lp_strike, "premium_est": round(lp_mid, 4)}],
        "short_legs": [{"type": "call", "action": "sell", "strike": sc_strike, "premium_est": round(sc_mid, 4)}],
        "net_premium_type": "credit" if net_cost < 0 else "debit",
        "net_debit_credit": round(abs(net_cost), 4),
        "max_gain": "underlying_capped_above_short_call",
        "max_loss": "underlying_partially_buffered_by_long_put",
        "break_even": "depends_on_existing_underlying_cost_basis",
        "financing_ratio": round(max(0.0, financing_ratio), 4),
        "convexity_retained_score": round(structure_score(5.2, *penalties), 2),
        "theta_funding_score": round(structure_score(7.4, *penalties), 2),
        "tail_cleanliness_score": round(structure_score(7.8, *penalties), 2),
        "event_risk_note": "Appropriate only if actual long AEX exposure exists in portfolio state.",
        "execution_status": "candidate_only",
        "selection_confidence": round(structure_score(6.0, *penalties), 2),
        **candidate_meta(surface, chain_mode, config),
    }


def candidate_passes_default_rules(candidate: dict[str, Any], directional: str, surface: dict[str, Any] | None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if candidate["family"] not in ALLOWED_FAMILIES:
        reasons.append("family_not_allowed")
    if candidate["selection_confidence"] < 6.0:
        reasons.append("selection_confidence_too_low")
    if isinstance(candidate.get("max_loss"), (int, float)) and float(candidate["max_loss"]) <= 0:
        reasons.append("max_loss_invalid")
    if candidate["financing_ratio"] > 1.25:
        reasons.append("financing_ratio_too_high")
    if (surface or {}).get("event_distortion_flag"):
        reasons.append("event_distortion_active")
    if directional not in {"bullish", "bearish"} and candidate["family"] != "collar_style_protection":
        reasons.append("directional_regime_not_clear")
    if candidate["family"] == "range_defined_risk_premium_structure":
        reasons.append("range_family_kept_watch_only_by_default")
    return len(reasons) == 0, reasons


def build_payload() -> dict[str, Any]:
    primary = load_json(PRIMARY_PATH)
    cross = load_json(CROSS_PATH)
    surface = load_json(SURFACE_PATH)
    macro = load_json(MACRO_PATH)
    portfolio = load_json(PORTFOLIO_PATH)
    config = load_provider_config()

    chain_payload, chain_mode, source_errors, used_provider_path = load_chain_payload(config)
    if used_provider_path:
        config = dict(config)
        config["provider_input_path"] = used_provider_path

    directional = derive_directional_regime(primary, cross, macro, surface)

    payload = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "directional_regime": directional,
        "provider_mode": chain_mode,
        "source_policy": config["option_chain_source_policy"],
        "provider_input_path": config["provider_input_path"],
        "underlying": "AEX",
        "candidates": [],
        "approved_candidates": [],
        "watch_candidates": [],
        "notes": [],
    }

    if source_errors:
        payload["notes"].append("chain source resolution notes: " + "; ".join(source_errors))

    if chain_payload is None:
        payload["notes"].append("No option-chain payload available; no strike-aware candidates could be built.")
        return payload

    spot = clean_float(chain_payload.get("spot_price"))
    expiries = chain_payload.get("expiries") or []
    if spot is None or not expiries:
        payload["notes"].append("Option-chain payload missing spot price or expiry data.")
        return payload

    front = expiries[0]
    expiry_unix = int(front.get("expiry_unix") or 0)
    calls = list(front.get("calls") or [])
    puts = list(front.get("puts") or [])
    if not expiry_unix or not calls or not puts:
        payload["notes"].append("Front expiry did not contain enough call/put rows for candidate building.")
        return payload

    builders = []
    if directional == "bullish":
        builders = [build_bullish_structure, build_collar]
    elif directional == "bearish":
        builders = [build_bearish_structure]
    else:
        builders = [build_range_structure, build_bullish_structure, build_bearish_structure, build_collar]

    for builder in builders:
        if builder is build_collar:
            candidate = builder(spot, expiry_unix, calls, puts, chain_mode, surface, portfolio, config)
        else:
            candidate = builder(spot, expiry_unix, calls, puts, chain_mode, surface, config)
        if not candidate:
            continue
        passes, reasons = candidate_passes_default_rules(candidate, directional, surface)
        candidate["default_gate_passed"] = passes
        candidate["gate_notes"] = reasons
        payload["candidates"].append(candidate)
        if passes:
            payload["approved_candidates"].append(candidate)
        else:
            payload["watch_candidates"].append(candidate)

    payload["candidates"].sort(key=lambda c: c.get("selection_confidence", 0), reverse=True)
    payload["approved_candidates"].sort(key=lambda c: c.get("selection_confidence", 0), reverse=True)
    payload["watch_candidates"].sort(key=lambda c: c.get("selection_confidence", 0), reverse=True)
    if not payload["candidates"]:
        payload["notes"].append("No complete defined-risk structures could be built from the available chain.")
    return payload


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"AEX_STRUCTURE_CANDIDATES_OK | file={OUTPUT_PATH} | mode={payload.get('provider_mode')} | policy={payload.get('source_policy')}")


if __name__ == "__main__":
    main()
