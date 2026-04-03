#!/usr/bin/env python3
"""
Generate a Weekly AEX Option Review from the current snapshot and structure artifacts.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aex_option_chain_ingest import clean_float, load_normalized_chain_payload

OUTPUT_DIR = Path("output_aex")
PRIMARY_PATH = OUTPUT_DIR / "aex_primary_technical_snapshot.json"
CROSS_PATH = OUTPUT_DIR / "aex_cross_market_confirmation.json"
MACRO_PATH = OUTPUT_DIR / "aex_macro_snapshot.json"
SURFACE_PATH = OUTPUT_DIR / "aex_option_surface_snapshot.json"
STRUCTURES_PATH = OUTPUT_DIR / "aex_structure_candidates.json"
PORTFOLIO_PATH = OUTPUT_DIR / "aex_option_portfolio_state.json"
RISK_PATH = OUTPUT_DIR / "aex_option_risk_state.json"

DISCLAIMER_LINE = "This report is for informational and educational purposes only; please see the disclaimer at the end."


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def today_tokens() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d"), now.strftime("%y%m%d")


def derive_directional_regime(
    primary: dict[str, Any] | None,
    cross: dict[str, Any] | None,
    macro: dict[str, Any] | None,
    surface: dict[str, Any] | None,
) -> str:
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


def derive_options_regime(surface: dict[str, Any] | None) -> str:
    if not surface:
        return "surface_unavailable"
    return str(surface.get("surface_regime", "surface_unavailable"))


def derive_pricing_state(
    surface: dict[str, Any] | None,
    structures: dict[str, Any] | None,
) -> str:
    if not surface and not structures:
        return "no_pricing_available"

    provider_mode = (surface or {}).get("provider_mode")
    implied_move = (surface or {}).get("implied_move_pct_next_expiry")
    atm_values = [v for v in ((surface or {}).get("atm_iv_by_expiry") or {}).values() if v is not None]
    candidates = list((structures or {}).get("candidates") or [])

    if provider_mode == "unavailable" and implied_move is None and not atm_values and not candidates:
        return "no_pricing_available"
    if atm_values:
        return "full_surface_available"
    return "pricing_available_iv_missing"


def choose_approved_structure(
    structures: dict[str, Any] | None,
    directional: str,
    options_regime: str,
) -> tuple[dict[str, Any] | None, str]:
    if not structures:
        return None, "structure_candidates_missing"
    approved = list(structures.get("approved_candidates") or [])
    if not approved:
        return None, "no_candidates_passed_default_rules"
    top = approved[0]
    if directional not in {"bullish", "bearish"}:
        return None, "directional_regime_not_clear"
    if options_regime not in {"long_premium_favorable", "financed_premium_favorable"}:
        return None, f"options_regime_{options_regime}"
    return top, "approved"


def build_no_trade_reason(
    primary: dict[str, Any] | None,
    cross: dict[str, Any] | None,
    macro: dict[str, Any] | None,
    surface: dict[str, Any] | None,
    structures: dict[str, Any] | None,
    directional: str,
    options_regime: str,
    approval_reason: str,
) -> str:
    reasons: list[str] = []
    if not macro:
        reasons.append("macro snapshot missing")
    if not primary:
        reasons.append("primary AEX technical snapshot missing")
    if not cross:
        reasons.append("cross-market confirmation snapshot missing")
    if not surface:
        reasons.append("option-surface snapshot missing")
    if not structures:
        reasons.append("structure-candidate board missing")
    if surface and surface.get("provider_mode") == "unavailable":
        reasons.append("option-surface data unavailable")
    if directional == "unstable":
        reasons.append("directional regime unstable")
    if options_regime in {"surface_unavailable", "surface_unattractive", "event_distorted"}:
        reasons.append(f"options regime {options_regime}")
    if approval_reason != "approved":
        reasons.append(approval_reason)
    return "; ".join(dict.fromkeys(reasons))


def format_break_even(value: Any) -> str:
    if isinstance(value, list):
        return " / ".join(str(x) for x in value)
    return str(value)


def format_candidate_legs(candidate: dict[str, Any]) -> str:
    legs: list[str] = []
    for leg in candidate.get("long_legs", []):
        legs.append(f"buy {leg.get('type')} {leg.get('strike')}")
    for leg in candidate.get("short_legs", []):
        legs.append(f"sell {leg.get('type')} {leg.get('strike')}")
    return "; ".join(legs) if legs else "n/a"


def format_premium(candidate: dict[str, Any]) -> str:
    premium_type = candidate.get("net_premium_type", "premium")
    premium_value = candidate.get("net_debit_credit")
    if premium_value is None:
        return "n/a"
    return f"{premium_type} {premium_value} pts est"


def format_pct(value: Any) -> str:
    number = clean_float(value)
    if number is None:
        return "n/a"
    return f"{number * 100:.2f}%" if abs(number) <= 1 else f"{number:.2f}%"


def estimate_row_price(row: dict[str, Any]) -> float | None:
    bid = clean_float(row.get("bid"))
    ask = clean_float(row.get("ask"))
    last = clean_float(row.get("lastPrice"))
    if bid is not None and ask is not None and ask >= bid and (bid > 0 or ask > 0):
        return (bid + ask) / 2.0
    return last


def load_front_expiry_snapshot(
    surface: dict[str, Any] | None,
    structures: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    provider_path = (structures or {}).get("provider_input_path") or (surface or {}).get("provider_input_path")
    if not provider_path:
        return None, []

    path = Path(str(provider_path))
    if not path.exists():
        return None, []

    try:
        payload = load_normalized_chain_payload(path)
    except Exception:
        return None, []

    expiries = list(payload.get("expiries") or [])
    if not expiries:
        return payload, []

    front = expiries[0]
    spot = clean_float(payload.get("spot_price"))
    if spot is None:
        return payload, []

    calls_by_strike = {
        clean_float(row.get("strike")): row
        for row in (front.get("calls") or [])
        if clean_float(row.get("strike")) is not None
    }
    puts_by_strike = {
        clean_float(row.get("strike")): row
        for row in (front.get("puts") or [])
        if clean_float(row.get("strike")) is not None
    }
    strikes = sorted(set(calls_by_strike) | set(puts_by_strike), key=lambda strike: (abs(strike - spot), strike))[:4]
    rows = []
    for strike in sorted(strikes):
        rows.append(
            {
                "strike": strike,
                "call_est": estimate_row_price(calls_by_strike.get(strike, {})) if strike in calls_by_strike else None,
                "put_est": estimate_row_price(puts_by_strike.get(strike, {})) if strike in puts_by_strike else None,
            }
        )
    return payload, rows


def candidate_bias(candidate: dict[str, Any]) -> str:
    regime_tag = str(candidate.get("regime_tag", "")).lower()
    family = str(candidate.get("family", "")).lower()
    if "bull" in regime_tag or "bull" in family:
        return "Bullish"
    if "bear" in regime_tag or "bear" in family:
        return "Bearish"
    if "range" in regime_tag or "range" in family:
        return "Range"
    if "hedge" in regime_tag or "collar" in family:
        return "Hedge"
    return "Mixed"


def choose_display_candidates(
    structures: dict[str, Any] | None,
    approved_structure: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    all_candidates = list((structures or {}).get("candidates") or [])
    watch_candidates = list((structures or {}).get("watch_candidates") or [])

    if approved_structure:
        selected = [approved_structure]
        selected.extend([c for c in all_candidates if c.get("structure_name") != approved_structure.get("structure_name")][:2])
        return selected

    return (watch_candidates or all_candidates)[:3]


def render_candidate_block(candidate: dict[str, Any], approved: bool) -> list[str]:
    title = "Approved structure" if approved else "Watchlist structure"
    lines = [
        f"### {title}: {candidate['structure_name']}",
        f"- Bias: {candidate_bias(candidate)}",
        f"- Expiry: {candidate['expiry']}",
        f"- Estimated premium: {format_premium(candidate)}",
        f"- Break-even: {format_break_even(candidate.get('break_even'))}",
        f"- Max gain / max loss: {candidate.get('max_gain')} EUR / {candidate.get('max_loss')} EUR",
        f"- Legs: {format_candidate_legs(candidate)}",
    ]
    gate_notes = list(candidate.get("gate_notes") or [])
    if gate_notes:
        lines.append(f"- Approval blockers: {', '.join(gate_notes)}")
    return lines


def render_report(
    report_date: str,
    primary: dict[str, Any] | None,
    cross: dict[str, Any] | None,
    macro: dict[str, Any] | None,
    surface: dict[str, Any] | None,
    structures: dict[str, Any] | None,
    portfolio: dict[str, Any] | None,
    risk: dict[str, Any] | None,
    directional: str,
    options_regime: str,
    pricing_state: str,
    approved_structure: dict[str, Any] | None,
    no_trade_reason: str,
) -> str:
    primary_price = (primary or {}).get("reference_price")
    primary_trend = (primary or {}).get("trend_state", "unknown")
    technical_confidence = (primary or {}).get("technical_confidence", "unknown")
    cross_overall = (cross or {}).get("overall_confirmation", "unknown")
    macro_regime = (macro or {}).get("macro_regime", "unknown")
    dominant_driver = (macro or {}).get("dominant_driver", "unknown")
    provider_mode = (surface or {}).get("provider_mode", "unknown")
    implied_move = (surface or {}).get("implied_move_pct_next_expiry")
    rv20 = (((primary or {}).get("realized_vol_state") or {}).get("rv20_annualized"))
    atm_map = (surface or {}).get("atm_iv_by_expiry", {})
    top_expiry = next(iter(atm_map.items()), None)
    display_candidates = choose_display_candidates(structures, approved_structure)
    normalized_chain, strike_snapshot_rows = load_front_expiry_snapshot(surface, structures)
    chain_spot = clean_float((normalized_chain or {}).get("spot_price")) or clean_float(primary_price)
    chain_expiries = list((normalized_chain or {}).get("expiries") or [])
    target_expiry = datetime.fromtimestamp(chain_expiries[0]["expiry_unix"], tz=timezone.utc).strftime("%Y-%m-%d") if chain_expiries else (approved_structure or {}).get("expiry", "n/a")

    lines = [
        f"# Weekly AEX Option Review {report_date}",
        "",
        f"> *{DISCLAIMER_LINE}*",
        "",
        "## 1. Executive summary",
        f"- Primary status: **{'APPROVED' if approved_structure else 'NO_TRADE'}**",
        f"- Directional regime: **{directional}**",
        f"- Pricing state: **{pricing_state}**",
    ]
    if approved_structure:
        lines.append(f"- Top approved structure: **{approved_structure['structure_name']}** with {format_premium(approved_structure)} and max loss {approved_structure['max_loss']} EUR.")
    elif display_candidates:
        lines.append(f"- Top watchlist structure: **{display_candidates[0]['structure_name']}** with {format_premium(display_candidates[0])} and max loss {display_candidates[0]['max_loss']} EUR.")
    else:
        lines.append(f"- No priced structures were available. Main reason: {no_trade_reason}.")
    lines += [
        "",
        "## 2. Tradeable pricing snapshot",
        f"- Source mode: {provider_mode}",
        f"- Source path: {((structures or {}).get('provider_input_path') or (surface or {}).get('provider_input_path') or 'n/a')}",
        f"- Snapshot as of: {(surface or {}).get('as_of', 'n/a')}",
        f"- Target expiry: {target_expiry}",
        f"- Reference spot: {chain_spot if chain_spot is not None else 'n/a'}",
        f"- Options regime: {options_regime}",
        f"- Implied move next expiry: {format_pct(implied_move)}",
        f"- Front expiry IV read: {f'{top_expiry[0]} ATM IV {top_expiry[1]}' if top_expiry else 'IV unavailable from current free-source snapshot'}",
        "",
        "| Strike | Call price est | Put price est |",
        "|---:|---:|---:|",
    ]
    if strike_snapshot_rows:
        for row in strike_snapshot_rows:
            call_est = "n/a" if row["call_est"] is None else f"{row['call_est']:.2f}"
            put_est = "n/a" if row["put_est"] is None else f"{row['put_est']:.2f}"
            lines.append(f"| {row['strike']:.2f} | {call_est} | {put_est} |")
    else:
        lines.append("| n/a | n/a | n/a |")

    lines += [
        "",
        "## 3. Primary decision",
        f"- Decision: {'APPROVE' if approved_structure else 'NO_TRADE'}",
        f"- Decision reason: {'priced structure passed default rules' if approved_structure else no_trade_reason}",
        f"- Automation level: 1",
        "- Position change: none automatically; execution still requires manual confirmation.",
        "",
        "## 4. Watchlist and approved structures",
    ]
    if display_candidates:
        for candidate in display_candidates:
            lines += render_candidate_block(candidate, approved_structure is not None and candidate.get("structure_name") == approved_structure.get("structure_name"))
            lines.append("")
    else:
        lines += [
            "- No structures available from the current chain payload.",
            "",
        ]

    lines += [
        "| Structure | Bias | Premium | Break-even | Max loss EUR | Confidence | Why not approved |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for candidate in display_candidates:
        blockers = ", ".join(candidate.get("gate_notes") or []) or ("approved" if approved_structure and candidate.get("structure_name") == approved_structure.get("structure_name") else "n/a")
        lines.append(
            f"| {candidate['structure_name']} | {candidate_bias(candidate)} | {format_premium(candidate)} | {format_break_even(candidate.get('break_even'))} | {candidate.get('max_loss')} | {candidate.get('selection_confidence')} | {blockers} |"
        )

    lines += [
        "",
        "## 5. Why the top structure is not yet approved",
    ]
    if approved_structure:
        lines += [
            "- The top structure is already approved under the current default rules.",
            "- Manual execution confirmation is still required before any portfolio state change.",
        ]
    else:
        blockers = ", ".join(display_candidates[0].get("gate_notes") or []) if display_candidates else "no candidate structures were built"
        lines += [
            f"- Core no-trade reason: {no_trade_reason}",
            f"- Top structure blockers: {blockers}",
            f"- Pricing state interpretation: {pricing_state}",
            "- Free-source chain coverage remains suitable for watchlisting, not auto-approval.",
        ]

    lines += [
        "",
        "## 6. Market context appendix",
        f"- Macro regime: {macro_regime}",
        f"- Dominant driver: {dominant_driver}",
        f"- Cross-market confirmation: {cross_overall}",
        f"- Primary technical trend: {primary_trend}",
        f"- Reference price: {primary_price}",
        f"- 20d realized vol: {rv20}",
        f"- Technical confidence: {technical_confidence}",
        f"- AEX sector notes: {((macro or {}).get('aex_sector_notes') or {})}",
        "",
        "## 7. Portfolio and risk appendix",
        f"- Open structures: {len((portfolio or {}).get('open_structures', [])) if portfolio else 0}",
        f"- Cash EUR: {((portfolio or {}).get('cash_eur')) if portfolio else 0}",
        f"- Net delta / gamma / theta / vega: {((risk or {}).get('net_delta'), (risk or {}).get('net_gamma'), (risk or {}).get('net_theta'), (risk or {}).get('net_vega')) if risk else ('n/a', 'n/a', 'n/a', 'n/a')}",
        f"- Max loss total: {((risk or {}).get('max_loss_total')) if risk else 'n/a'}",
        "",
        "## 8. Source receipt appendix",
        f"- Primary technical snapshot: {(primary or {}).get('as_of', 'n/a')}",
        f"- Cross-market snapshot: {(cross or {}).get('as_of', 'n/a')}",
        f"- Macro snapshot: {(macro or {}).get('as_of', 'n/a')}",
        f"- Option surface snapshot: {(surface or {}).get('as_of', 'n/a')}",
        f"- Structure builder mode: {((structures or {}).get('provider_mode') or 'unknown')}",
        f"- Source policy: {((structures or {}).get('source_policy') or (surface or {}).get('source_policy') or 'unknown')}",
        f"- Input path used: {((structures or {}).get('provider_input_path') or (surface or {}).get('provider_input_path') or 'n/a')}",
        "- Public/free chain snapshots are acceptable for watchlist generation but should be rechecked against live broker quotes before execution.",
        "",
        "## 9. Disclaimer",
        DISCLAIMER_LINE,
        "",
    ]
    return "\n".join(lines)


def build_trade_plan(
    report_date: str,
    directional: str,
    options_regime: str,
    pricing_state: str,
    approved_structure: dict[str, Any] | None,
    no_trade_reason: str,
) -> dict[str, Any]:
    return {
        "report_date": report_date,
        "approval_status": "approved" if approved_structure else "no_trade",
        "automation_level": 1,
        "directional_regime": directional,
        "options_regime": options_regime,
        "pricing_state": pricing_state,
        "primary_decision": "APPROVE" if approved_structure else "NO_TRADE",
        "no_trade_reason": None if approved_structure else no_trade_reason,
        "structures_considered": [
            "overwrite_funded_hedge",
            "collar_style_protection",
            "defined_risk_bullish_financed_convexity",
            "defined_risk_bearish_financed_convexity",
            "range_defined_risk_premium_structure",
        ],
        "approved_structures": [approved_structure] if approved_structure else [],
        "portfolio_overlap_assessment": "manual_review_required_before_execution" if approved_structure else "not_applicable_no_trade",
        "timing_gate_status": "manual_execution_required_after_validation" if approved_structure else "pass_for_review_only_but_no_trade",
        "freshness_summary": "derived from latest available snapshot files in output_aex",
        "risk_budget_summary": "proposal only at automation level 1" if approved_structure else "no new structure approved; risk budget preserved",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suffix", default="01", help="Two-digit daily sequence suffix")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_date, token = today_tokens()

    primary = load_json(PRIMARY_PATH)
    cross = load_json(CROSS_PATH)
    macro = load_json(MACRO_PATH)
    surface = load_json(SURFACE_PATH)
    structures = load_json(STRUCTURES_PATH)
    portfolio = load_json(PORTFOLIO_PATH)
    risk = load_json(RISK_PATH)

    directional = derive_directional_regime(primary, cross, macro, surface)
    options_regime = derive_options_regime(surface)
    pricing_state = derive_pricing_state(surface, structures)
    approved_structure, approval_reason = choose_approved_structure(structures, directional, options_regime)
    no_trade_reason = build_no_trade_reason(primary, cross, macro, surface, structures, directional, options_regime, approval_reason)

    report_md = render_report(report_date, primary, cross, macro, surface, structures, portfolio, risk, directional, options_regime, pricing_state, approved_structure, no_trade_reason)
    trade_plan = build_trade_plan(report_date, directional, options_regime, pricing_state, approved_structure, no_trade_reason)

    report_path = OUTPUT_DIR / f"weekly_aex_option_review_{token}_{args.suffix}.md"
    trade_plan_path = OUTPUT_DIR / f"aex_option_trade_plan_{token}_{args.suffix}.json"

    report_path.write_text(report_md, encoding="utf-8")
    trade_plan_path.write_text(json.dumps(trade_plan, indent=2), encoding="utf-8")

    print(f"AEX_WEEKLY_REVIEW_GENERATED | report={report_path.name} | trade_plan={trade_plan_path.name}")


if __name__ == "__main__":
    main()
