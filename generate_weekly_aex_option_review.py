#!/usr/bin/env python3
"""
Generate a Weekly AEX Option Review from the current snapshot and structure artifacts.

This generator is still conservative, but it is no longer a pure placeholder:
- it reads the macro snapshot
- it reads the primary technical snapshot
- it reads the cross-market confirmation snapshot
- it reads the option-surface snapshot
- it reads the strike-aware structure-candidate board
- it reads the current portfolio / risk state when present
- it can approve one top structure if the default gates are genuinely met
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def derive_options_regime(surface: dict[str, Any] | None) -> str:
    if not surface:
        return "surface_unavailable"
    return str(surface.get("surface_regime", "surface_unavailable"))


def choose_approved_structure(structures: dict[str, Any] | None, directional: str, options_regime: str) -> tuple[dict[str, Any] | None, str]:
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

def build_no_trade_reason(primary: dict[str, Any] | None, cross: dict[str, Any] | None, macro: dict[str, Any] | None, surface: dict[str, Any] | None, structures: dict[str, Any] | None, directional: str, options_regime: str, approval_reason: str) -> str:
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


def render_report(report_date: str, primary: dict[str, Any] | None, cross: dict[str, Any] | None, macro: dict[str, Any] | None, surface: dict[str, Any] | None, structures: dict[str, Any] | None, portfolio: dict[str, Any] | None, risk: dict[str, Any] | None, directional: str, options_regime: str, approved_structure: dict[str, Any] | None, no_trade_reason: str) -> str:
    primary_price = (primary or {}).get("reference_price")
    primary_trend = (primary or {}).get("trend_state", "unknown")
    cross_overall = (cross or {}).get("overall_confirmation", "unknown")
    macro_regime = (macro or {}).get("macro_regime", "unknown")
    dominant_driver = (macro or {}).get("dominant_driver", "unknown")
    provider_mode = (surface or {}).get("provider_mode", "unknown")
    implied_move = (surface or {}).get("implied_move_pct_next_expiry")
    rv20 = (((primary or {}).get("realized_vol_state") or {}).get("rv20_annualized"))
    atm_map = (surface or {}).get("atm_iv_by_expiry", {})
    top_expiry = next(iter(atm_map.items()), None)
    atm_line = f"{top_expiry[0]} ATM IV {top_expiry[1]}" if top_expiry else "no expiry IV available"

    structures_considered = list((structures or {}).get("candidates") or [])
    approved_text = "**Decision: NO_TRADE**" if not approved_structure else f"**Decision: APPROVE {approved_structure['structure_name']}**"

    lines = [
        f"# Weekly AEX Option Review {report_date}",
        "",
        f"> *{DISCLAIMER_LINE}*",
        "",
        "## 1. Executive summary",
        f"The current generator classifies the directional regime as **{directional}** and the options regime as **{options_regime}**.",
    ]
    if approved_structure:
        lines.append(
            f"The top approved candidate is **{approved_structure['structure_name']}** in family **{approved_structure['family']}**, with estimated max loss **{approved_structure['max_loss']} EUR** and financing ratio **{approved_structure['financing_ratio']}**."
        )
    else:
        lines.append(f"The output remains **NO_TRADE** because the burden of proof is not yet met. Main reason: {no_trade_reason}.")
    lines += [
        "",
        "## 2. Portfolio action snapshot",
        f"- Primary decision: {'APPROVE' if approved_structure else 'NO_TRADE'}",
        "- Automation level: 1",
        f"- Position change: {'none (manual approval still required)' if approved_structure else 'none'}",
        "- Financing posture: preserve optionality and keep defined risk explicit",
        "",
        "## 3. Macro / policy / geopolitical dashboard",
        f"- Macro regime: {macro_regime}",
        f"- Dominant driver: {dominant_driver}",
        f"- Cross-market confirmation: {cross_overall}",
        f"- ECB deposit rate: {(((macro or {}).get('ecb') or {}).get('deposit_rate_pct'))}",
        f"- Euro area inflation: {(((macro or {}).get('inflation') or {}).get('annual_inflation_pct'))}",
        f"- Euro area unemployment: {(((macro or {}).get('unemployment') or {}).get('unemployment_rate_pct'))}",
        f"- Euro area GDP q/q: {(((macro or {}).get('growth') or {}).get('gdp_qoq_pct'))}",
        "",
        "## 4. AEX composition and sector transmission map",
        f"- AEX sector notes: {((macro or {}).get('aex_sector_notes') or {})}",
        "- Concentration warning: AEX index-level approval should still be treated cautiously when macro narratives are broad but sector leadership is narrow",
        "",
        "## 5. Technical integrity and confirmation check",
        f"- Primary technical trend: {primary_trend}",
        f"- Reference price: {primary_price}",
        f"- 20d realized vol: {rv20}",
        f"- Technical confidence: {(primary or {}).get('technical_confidence', 'unknown')}",
        "- Integrity note: the primary technical snapshot is based on the underlying, not on options",
        "",
        "## 6. Options regime and surface conditions",
        f"- Surface provider mode: {provider_mode}",
        f"- Surface regime: {options_regime}",
        f"- Front expiry read: {atm_line}",
        f"- Implied move next expiry: {implied_move}",
        "- Surface interpretation: public chain coverage is treated conservatively and provider-fed input remains preferred when available",
        "",
        "## 7. Approved structure family or no-trade decision",
        approved_text,
        "",
    ]
    if approved_structure:
        lines += [
            f"Approved family: {approved_structure['family']}",
            f"Expiry: {approved_structure['expiry']}",
            f"Long legs: {approved_structure['long_legs']}",
            f"Short legs: {approved_structure['short_legs']}",
            f"Break-even: {approved_structure['break_even']}",
            f"Max gain / max loss: {approved_structure['max_gain']} / {approved_structure['max_loss']}",
        ]
    else:
        lines += [f"Reason: {no_trade_reason}."]
    lines += [
        "",
        "## 8. Structure ranking table",
        "| Candidate family | Status | Selection confidence | Notes |",
        "|---|---|---:|---|",
    ]
    for cand in structures_considered:
        status = "approved" if approved_structure and cand["structure_name"] == approved_structure["structure_name"] else ("watch" if cand.get("default_gate_passed") else "reject")
        lines.append(f"| {cand['family']} | {status} | {cand.get('selection_confidence')} | {', '.join(cand.get('gate_notes', []))} |")
    lines += [
        "",
        "## 9. Calendar / timing gates and invalidators",
        "- Do not force a financed structure inside event-distorted conditions",
        "- Do not auto-execute approved structures at automation level 1",
        "- Keep no-trade as the default whenever structure selection depends on incomplete chain coverage",
        "",
        "## 10. Position changes executed this run",
        "- None automatically. Portfolio changes require explicit execution confirmation.",
        "",
        "## 11. Current option portfolio, premium, and cash",
        f"- Open structures: {len((portfolio or {}).get('open_structures', [])) if portfolio else 0}",
        f"- Cash EUR: {((portfolio or {}).get('cash_eur')) if portfolio else 0}",
        f"- Net delta / gamma / theta / vega: {((risk or {}).get('net_delta'), (risk or {}).get('net_gamma'), (risk or {}).get('net_theta'), (risk or {}).get('net_vega')) if risk else ('n/a', 'n/a', 'n/a', 'n/a')}",
        f"- Max loss total: {((risk or {}).get('max_loss_total')) if risk else 'n/a'}",
        "",
        "## 12. Carry-forward input for next run",
        "- Refresh macro, technical, cross-market, and option-surface snapshots",
        "- Rebuild structure candidates with the newest chain",
        "- Refresh portfolio and Greeks state after any explicit execution events",
        "",
        "## 13. Disclaimer",
        DISCLAIMER_LINE,
        "",
    ]
    return "\n".join(lines)


def build_trade_plan(report_date: str, directional: str, options_regime: str, approved_structure: dict[str, Any] | None, no_trade_reason: str) -> dict[str, Any]:
    return {
        "report_date": report_date,
        "approval_status": "approved" if approved_structure else "no_trade",
        "automation_level": 1,
        "directional_regime": directional,
        "options_regime": options_regime,
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
    approved_structure, approval_reason = choose_approved_structure(structures, directional, options_regime)
    no_trade_reason = build_no_trade_reason(primary, cross, macro, surface, structures, directional, options_regime, approval_reason)

    report_md = render_report(report_date, primary, cross, macro, surface, structures, portfolio, risk, directional, options_regime, approved_structure, no_trade_reason)
    trade_plan = build_trade_plan(report_date, directional, options_regime, approved_structure, no_trade_reason)

    report_path = OUTPUT_DIR / f"weekly_aex_option_review_{token}_{args.suffix}.md"
    trade_plan_path = OUTPUT_DIR / f"aex_option_trade_plan_{token}_{args.suffix}.json"

    report_path.write_text(report_md, encoding="utf-8")
    trade_plan_path.write_text(json.dumps(trade_plan, indent=2), encoding="utf-8")

    print(f"AEX_WEEKLY_REVIEW_GENERATED | report={report_path.name} | trade_plan={trade_plan_path.name}")


if __name__ == "__main__":
    main()
