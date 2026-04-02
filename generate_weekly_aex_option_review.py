#!/usr/bin/env python3
"""
Generate the first Weekly AEX Option Review from the three snapshot JSON inputs.

This generator is intentionally conservative:
- it reads the primary technical snapshot
- it reads the cross-market confirmation snapshot
- it reads the option-surface snapshot
- it outputs a complete markdown review
- it outputs a machine-readable trade plan
- it defaults to NO_TRADE unless the evidence is unusually clean

The goal of v1 is a deterministic first report generator, not a full structure optimizer.
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
SURFACE_PATH = OUTPUT_DIR / "aex_option_surface_snapshot.json"

DISCLAIMER_LINE = "This report is for informational and educational purposes only; please see the disclaimer at the end."


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def today_tokens() -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%d"), now.strftime("%y%m%d")


def derive_directional_regime(primary: dict[str, Any] | None, cross: dict[str, Any] | None, surface: dict[str, Any] | None) -> str:
    if surface and surface.get("event_distortion_flag"):
        return "unstable"
    trend = (primary or {}).get("trend_state", "unknown")
    cross_overall = (cross or {}).get("overall_confirmation", "unknown")
    if trend == "bullish" and cross_overall == "supportive_risk":
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


def should_approve(primary: dict[str, Any] | None, cross: dict[str, Any] | None, surface: dict[str, Any] | None, directional: str, options_regime: str) -> bool:
    if not primary or not cross or not surface:
        return False
    if primary.get("technical_confidence") != "high":
        return False
    if directional not in {"bullish", "bearish"}:
        return False
    if options_regime not in {"long_premium_favorable", "financed_premium_favorable"}:
        return False
    if surface.get("provider_mode") == "unavailable":
        return False
    return False  # v1 intentionally stays conservative even when the setup looks clean


def build_no_trade_reason(primary: dict[str, Any] | None, cross: dict[str, Any] | None, surface: dict[str, Any] | None, directional: str, options_regime: str) -> str:
    reasons: list[str] = []
    if not primary:
        reasons.append("primary AEX technical snapshot missing")
    if not cross:
        reasons.append("cross-market confirmation snapshot missing")
    if not surface:
        reasons.append("option-surface snapshot missing")
    if surface and surface.get("provider_mode") == "unavailable":
        reasons.append("option-surface data unavailable")
    if directional == "unstable":
        reasons.append("directional regime unstable")
    if options_regime in {"surface_unavailable", "surface_unattractive", "event_distorted"}:
        reasons.append(f"options regime {options_regime}")
    if primary and primary.get("technical_confidence") != "high":
        reasons.append("technical confidence not high")
    reasons.append("v1 generator defaults to no-trade until a structure builder is added")
    return "; ".join(dict.fromkeys(reasons))


def render_report(report_date: str, primary: dict[str, Any] | None, cross: dict[str, Any] | None, surface: dict[str, Any] | None, directional: str, options_regime: str, no_trade_reason: str) -> str:
    primary_price = (primary or {}).get("reference_price")
    primary_trend = (primary or {}).get("trend_state", "unknown")
    cross_overall = (cross or {}).get("overall_confirmation", "unknown")
    provider_mode = (surface or {}).get("provider_mode", "unknown")
    implied_move = (surface or {}).get("implied_move_pct_next_expiry")
    rv20 = (((primary or {}).get("realized_vol_state") or {}).get("rv20_annualized"))
    atm_map = (surface or {}).get("atm_iv_by_expiry", {})

    top_expiry = next(iter(atm_map.items()), None)
    atm_line = f"{top_expiry[0]} ATM IV {top_expiry[1]}" if top_expiry else "no expiry IV available"

    structures_considered = [
        "overwrite_funded_hedge",
        "collar_style_protection",
        "defined_risk_bullish_financed_convexity",
        "defined_risk_bearish_financed_convexity",
        "range_defined_risk_premium_structure",
    ]

    lines = [
        f"# Weekly AEX Option Review {report_date}",
        "",
        f"> *{DISCLAIMER_LINE}*",
        "",
        "## 1. Executive summary",
        f"The current generator classifies the directional regime as **{directional}** and the options regime as **{options_regime}**.",
        f"The v1 output remains **NO_TRADE** because the burden of proof is not yet strong enough for automated structure approval. Main reason: {no_trade_reason}.",
        "",
        "## 2. Portfolio action snapshot",
        "- Primary decision: NO_TRADE",
        "- Automation level: 1",
        "- Position change: none",
        "- Financing posture: preserve optionality; do not force premium harvesting",
        "",
        "## 3. Macro / policy / geopolitical dashboard",
        f"- Cross-market confirmation: {cross_overall}",
        "- ECB / Europe-sensitive context: placeholder in v1 generator; macro snapshot generator still to be added",
        "- Geopolitical filter: not explicitly modeled in this first report generator",
        "- Interpretation: use this review as a disciplined operating baseline, not as a fully mature macro engine yet",
        "",
        "## 4. AEX composition and sector transmission map",
        "- AEX composition module is not yet fully computed in v1",
        "- Treat semiconductor concentration and Europe-sensitive cyclicality as unresolved concentration risk",
        "- Do not over-generalize from generic Europe equity behavior to AEX-specific structure approval",
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
        "- Surface interpretation: option-surface data is treated conservatively and may fall back to provider-fed input when public coverage is incomplete",
        "",
        "## 7. Approved structure family or no-trade decision",
        "**Decision: NO_TRADE**",
        "",
        f"Reason: {no_trade_reason}.",
        "",
        "## 8. Structure ranking table",
        "| Candidate family | Status | Reason |",
        "|---|---|---|",
    ]
    for fam in structures_considered:
        lines.append(f"| {fam} | reject in v1 | burden of proof not met |")
    lines += [
        "",
        "## 9. Calendar / timing gates and invalidators",
        "- Do not force a financed structure inside event-distorted or surface-unavailable conditions",
        "- Do not approve a structure while the generator still lacks a dedicated strike-selection engine",
        "- Invalidator for no-trade: upgrade only after a structure builder and richer macro snapshot are added",
        "",
        "## 10. Position changes executed this run",
        "- None",
        "",
        "## 11. Current option portfolio, premium, and cash",
        "- Portfolio state integration is not yet populated by the generator",
        "- Premium collected this cycle: not updated here",
        "- Premium spent this cycle: not updated here",
        "",
        "## 12. Carry-forward input for next run",
        "- Refresh the three snapshot JSON files",
        "- Add a dedicated macro snapshot producer",
        "- Add a structure builder with strikes, max loss, and financing metrics",
        "",
        "## 13. Disclaimer",
        DISCLAIMER_LINE,
        "",
    ]
    return "\n".join(lines)


def build_trade_plan(report_date: str, directional: str, options_regime: str, no_trade_reason: str) -> dict[str, Any]:
    return {
        "report_date": report_date,
        "approval_status": "no_trade",
        "automation_level": 1,
        "directional_regime": directional,
        "options_regime": options_regime,
        "primary_decision": "NO_TRADE",
        "no_trade_reason": no_trade_reason,
        "structures_considered": [
            "overwrite_funded_hedge",
            "collar_style_protection",
            "defined_risk_bullish_financed_convexity",
            "defined_risk_bearish_financed_convexity",
            "range_defined_risk_premium_structure",
        ],
        "approved_structures": [],
        "portfolio_overlap_assessment": "not_applicable_no_trade",
        "timing_gate_status": "pass_for_review_only_but_no_trade",
        "freshness_summary": "derived from latest available snapshot files in output_aex",
        "risk_budget_summary": "no new structure approved; risk budget preserved",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suffix", default="01", help="Two-digit daily sequence suffix")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_date, token = today_tokens()

    primary = load_json(PRIMARY_PATH)
    cross = load_json(CROSS_PATH)
    surface = load_json(SURFACE_PATH)

    directional = derive_directional_regime(primary, cross, surface)
    options_regime = derive_options_regime(surface)

    approved = should_approve(primary, cross, surface, directional, options_regime)
    if approved:
        directional = directional  # placeholder for future structure builder
    no_trade_reason = build_no_trade_reason(primary, cross, surface, directional, options_regime)

    report_md = render_report(report_date, primary, cross, surface, directional, options_regime, no_trade_reason)
    trade_plan = build_trade_plan(report_date, directional, options_regime, no_trade_reason)

    report_path = OUTPUT_DIR / f"weekly_aex_option_review_{token}_{args.suffix}.md"
    trade_plan_path = OUTPUT_DIR / f"aex_option_trade_plan_{token}_{args.suffix}.json"

    report_path.write_text(report_md, encoding="utf-8")
    trade_plan_path.write_text(json.dumps(trade_plan, indent=2), encoding="utf-8")

    print(f"AEX_WEEKLY_REVIEW_GENERATED | report={report_path.name} | trade_plan={trade_plan_path.name}")


if __name__ == "__main__":
    main()
