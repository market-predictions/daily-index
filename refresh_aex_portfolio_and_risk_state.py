#!/usr/bin/env python3
"""
Refresh output_aex/aex_option_portfolio_state.json and output_aex/aex_option_risk_state.json.

Key rules:
- automation level 1 means trade plans are advisory until execution is explicitly confirmed
- therefore, approved structures are NOT automatically added to the live portfolio
- this script computes risk from the existing portfolio state and records what the latest trade plan recommends
- if a structure in the portfolio has legs, Greeks are approximated with Black-Scholes using current spot / IV / rates

Optional execution feed:
- input_aex/aex_execution_events.json

Example event:
{
  "events": [
    {
      "timestamp": "2026-04-03T08:00:00Z",
      "action": "open_structure",
      "structure_name": "Bullish call spread financed by put credit spread",
      "structure": { ... full structure object ... }
    }
  ]
}
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path("output_aex")
PORTFOLIO_PATH = OUTPUT_DIR / "aex_option_portfolio_state.json"
RISK_PATH = OUTPUT_DIR / "aex_option_risk_state.json"
LEDGER_PATH = OUTPUT_DIR / "aex_trade_ledger.csv"
VALIDATION_PATH = OUTPUT_DIR / "aex_portfolio_refresh_manifest.json"

PRIMARY_PATH = OUTPUT_DIR / "aex_primary_technical_snapshot.json"
SURFACE_PATH = OUTPUT_DIR / "aex_option_surface_snapshot.json"
MACRO_PATH = OUTPUT_DIR / "aex_macro_snapshot.json"
EXECUTION_EVENTS_PATH = Path("input_aex/aex_execution_events.json")

PLAN_RE = re.compile(r"^aex_option_trade_plan_(\d{6})(?:_(\d{2}))?\.json$")


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def latest_trade_plan_path() -> Path | None:
    plans = sorted(
        [p for p in OUTPUT_DIR.glob("aex_option_trade_plan_*.json") if PLAN_RE.match(p.name)],
        key=lambda p: p.name,
    )
    return plans[-1] if plans else None


def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def option_greeks(flag: str, spot: float, strike: float, t: float, rate: float, sigma: float) -> dict[str, float]:
    sigma = max(sigma, 1e-6)
    t = max(t, 1e-6)
    if spot <= 0 or strike <= 0:
        return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    d1 = (math.log(spot / strike) + (rate + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    gamma = norm_pdf(d1) / (spot * sigma * math.sqrt(t))
    vega = spot * norm_pdf(d1) * math.sqrt(t) / 100.0

    if flag == "call":
        delta = norm_cdf(d1)
        theta = (-(spot * norm_pdf(d1) * sigma) / (2.0 * math.sqrt(t)) - rate * strike * math.exp(-rate * t) * norm_cdf(d2)) / 365.0
    else:
        delta = norm_cdf(d1) - 1.0
        theta = (-(spot * norm_pdf(d1) * sigma) / (2.0 * math.sqrt(t)) + rate * strike * math.exp(-rate * t) * norm_cdf(-d2)) / 365.0
    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega}


def initial_portfolio_state() -> dict[str, Any]:
    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_currency": "EUR",
        "cash_eur": 0.0,
        "premium_collected_cycle": 0.0,
        "premium_spent_cycle": 0.0,
        "open_structures": [],
        "expiration_ladder": {},
        "underlying_exposure": {"long_aex_units": 0},
        "last_trade_plan_observed": None,
        "last_valuation": {"date": "", "portfolio_value_eur": 0.0},
    }


def ensure_ledger() -> None:
    if not LEDGER_PATH.exists():
        LEDGER_PATH.write_text("timestamp,action,structure_name,notes\n", encoding="utf-8")


def append_ledger(timestamp: str, action: str, structure_name: str, notes: str) -> None:
    ensure_ledger()
    with LEDGER_PATH.open("a", encoding="utf-8") as fh:
        safe_notes = notes.replace(",", ";")
        fh.write(f"{timestamp},{action},{structure_name},{safe_notes}\n")


def apply_execution_events(portfolio: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    payload = load_json(EXECUTION_EVENTS_PATH)
    if not payload:
        return notes
    for event in payload.get("events", []):
        action = event.get("action")
        ts = event.get("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        if action == "open_structure" and event.get("structure"):
            portfolio.setdefault("open_structures", []).append(event["structure"])
            append_ledger(ts, "open_structure", event["structure"].get("structure_name", "unknown"), "execution_event_ingested")
            notes.append(f"opened {event['structure'].get('structure_name', 'unknown')} from execution events")
        elif action == "close_structure" and event.get("structure_name"):
            name = event["structure_name"]
            before = len(portfolio.get("open_structures", []))
            portfolio["open_structures"] = [s for s in portfolio.get("open_structures", []) if s.get("structure_name") != name]
            if len(portfolio["open_structures"]) < before:
                append_ledger(ts, "close_structure", name, "execution_event_ingested")
                notes.append(f"closed {name} from execution events")
    return notes


def compute_risk_state(portfolio: dict[str, Any], primary: dict[str, Any] | None, surface: dict[str, Any] | None, macro: dict[str, Any] | None) -> dict[str, Any]:
    spot = float((primary or {}).get("reference_price") or 0.0)
    rate_pct = (((macro or {}).get("ecb") or {}).get("deposit_rate_pct") or 0.0)
    rate = rate_pct / 100.0
    surface_map = (surface or {}).get("atm_iv_by_expiry", {})
    default_sigma = next((float(v) for v in surface_map.values() if v is not None), None)
    if default_sigma is None:
        default_sigma = (((primary or {}).get("realized_vol_state") or {}).get("rv20_annualized") or 0.18)

    totals = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    expiration_buckets: dict[str, int] = {}
    max_loss_total = 0.0
    max_gain_total = 0.0

    for structure in portfolio.get("open_structures", []):
        expiry = structure.get("expiry")
        expiration_buckets[expiry] = expiration_buckets.get(expiry, 0) + 1

        if isinstance(structure.get("max_loss"), (int, float)):
            max_loss_total += float(structure["max_loss"])
        if isinstance(structure.get("max_gain"), (int, float)):
            max_gain_total += float(structure["max_gain"])

        try:
            expiry_dt = datetime.fromisoformat(str(expiry)).replace(tzinfo=timezone.utc)
            t = max((expiry_dt - datetime.now(timezone.utc)).days / 365.0, 1 / 365.0)
        except Exception:
            t = 7 / 365.0

        for leg in structure.get("long_legs", []):
            strike = float(leg.get("strike"))
            flag = leg.get("type", "call")
            g = option_greeks(flag, spot, strike, t, rate, default_sigma)
            for k, v in g.items():
                totals[k] += v

        for leg in structure.get("short_legs", []):
            strike = float(leg.get("strike"))
            flag = leg.get("type", "call")
            g = option_greeks(flag, spot, strike, t, rate, default_sigma)
            for k, v in g.items():
                totals[k] -= v

    stress_scenarios = []
    if spot > 0:
        for pct in (-0.03, 0.03):
            stress_scenarios.append(
                {
                    "spot_move_pct": pct,
                    "spot_after_move": round(spot * (1.0 + pct), 4),
                    "delta_linear_pnl_estimate": round(totals["delta"] * spot * pct * 100.0, 2),
                }
            )

    return {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "net_delta": round(totals["delta"], 6),
        "net_gamma": round(totals["gamma"], 6),
        "net_theta": round(totals["theta"], 6),
        "net_vega": round(totals["vega"], 6),
        "premium_collected_cycle": round(float(portfolio.get("premium_collected_cycle", 0.0)), 4),
        "premium_spent_cycle": round(float(portfolio.get("premium_spent_cycle", 0.0)), 4),
        "expiration_buckets": expiration_buckets,
        "event_flags": [],
        "overlap_flags": ["none"] if len(portfolio.get("open_structures", [])) <= 1 else ["multi_structure_overlap"],
        "max_loss_total": round(max_loss_total, 2),
        "max_gain_total": round(max_gain_total, 2),
        "stress_scenarios": stress_scenarios,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    portfolio = load_json(PORTFOLIO_PATH) or initial_portfolio_state()
    primary = load_json(PRIMARY_PATH)
    surface = load_json(SURFACE_PATH)
    macro = load_json(MACRO_PATH)
    latest_plan = latest_trade_plan_path()

    notes = []
    if latest_plan:
        portfolio["last_trade_plan_observed"] = latest_plan.name
        plan = load_json(latest_plan) or {}
        if plan.get("approval_status") == "approved":
            notes.append("latest trade plan approved but not auto-applied at automation level 1")
    notes.extend(apply_execution_events(portfolio))

    portfolio["as_of"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    portfolio["expiration_ladder"] = {}
    for structure in portfolio.get("open_structures", []):
        expiry = str(structure.get("expiry", "unknown"))
        portfolio["expiration_ladder"][expiry] = portfolio["expiration_ladder"].get(expiry, 0) + 1

    risk_state = compute_risk_state(portfolio, primary, surface, macro)

    PORTFOLIO_PATH.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")
    RISK_PATH.write_text(json.dumps(risk_state, indent=2), encoding="utf-8")
    VALIDATION_PATH.write_text(
        json.dumps(
            {
                "refreshed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "portfolio_file": PORTFOLIO_PATH.name,
                "risk_file": RISK_PATH.name,
                "notes": notes,
                "latest_trade_plan": portfolio.get("last_trade_plan_observed"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"AEX_PORTFOLIO_RISK_REFRESH_OK | portfolio={PORTFOLIO_PATH.name} | risk={RISK_PATH.name}")


if __name__ == "__main__":
    main()
