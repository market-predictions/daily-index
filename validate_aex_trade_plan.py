#!/usr/bin/env python3
"""
Validate output_aex/aex_option_trade_plan_YYMMDD.json.

This validator checks both shape and core business rules.
It does not approve trades; it only says whether the plan is internally consistent.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

PLAN_RE = re.compile(r"^aex_option_trade_plan_(\d{6})(?:_(\d{2}))?\.json$")
OUTPUT_DIR = Path("output_aex")
VALIDATION_SUFFIX = "_validation.json"

ALLOWED_APPROVAL_STATUS = {"approved", "no_trade", "watch", "rejected"}
ALLOWED_PRIMARY_DECISIONS = {"APPROVE", "NO_TRADE", "WATCH", "REJECT"}
ALLOWED_FAMILIES = {
    "overwrite_funded_hedge",
    "collar_style_protection",
    "defined_risk_bullish_financed_convexity",
    "defined_risk_bearish_financed_convexity",
    "range_defined_risk_premium_structure",
    "hedge_only",
}

REQUIRED_TOP_LEVEL = [
    "report_date",
    "approval_status",
    "automation_level",
    "directional_regime",
    "options_regime",
    "primary_decision",
    "structures_considered",
    "approved_structures",
    "portfolio_overlap_assessment",
    "timing_gate_status",
    "freshness_summary",
    "risk_budget_summary",
]

REQUIRED_STRUCTURE = [
    "structure_name",
    "family",
    "regime_tag",
    "expiry",
    "long_legs",
    "short_legs",
    "net_debit_credit",
    "max_gain",
    "max_loss",
    "break_even",
    "financing_ratio",
    "convexity_retained_score",
    "theta_funding_score",
    "tail_cleanliness_score",
    "event_risk_note",
    "execution_status",
]


def sort_key(path: Path) -> tuple[str, int]:
    match = PLAN_RE.match(path.name)
    if not match:
        return ("", -1)
    return (match.group(1), int(match.group(2) or "0"))


def latest_plan_file() -> Path:
    plans = sorted([p for p in OUTPUT_DIR.glob("aex_option_trade_plan_*.json") if PLAN_RE.match(p.name)], key=sort_key)
    if not plans:
        raise FileNotFoundError("No aex_option_trade_plan_*.json file found in output_aex/")
    return plans[-1]


def validate_plan(plan: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    missing = [k for k in REQUIRED_TOP_LEVEL if k not in plan]
    if missing:
        errors.append("Missing top-level keys: " + ", ".join(missing))
        return errors, warnings

    if plan["approval_status"] not in ALLOWED_APPROVAL_STATUS:
        errors.append(f"Invalid approval_status: {plan['approval_status']}")
    if plan["primary_decision"] not in ALLOWED_PRIMARY_DECISIONS:
        errors.append(f"Invalid primary_decision: {plan['primary_decision']}")
    if not isinstance(plan["automation_level"], int) or not (1 <= plan["automation_level"] <= 4):
        errors.append("automation_level must be an integer between 1 and 4")

    if not plan["timing_gate_status"]:
        errors.append("timing_gate_status must not be blank")
    if not plan["freshness_summary"]:
        errors.append("freshness_summary must not be blank")
    if not plan["risk_budget_summary"]:
        errors.append("risk_budget_summary must not be blank")

    approved = plan.get("approved_structures") or []
    if plan["primary_decision"] == "NO_TRADE":
        if not plan.get("no_trade_reason"):
            errors.append("NO_TRADE requires no_trade_reason")
        if approved:
            errors.append("NO_TRADE plan must not contain approved_structures")
    elif not approved:
        errors.append("Non-NO_TRADE plan must contain at least one approved structure")

    for idx, structure in enumerate(approved, start=1):
        missing_s = [k for k in REQUIRED_STRUCTURE if k not in structure]
        if missing_s:
            errors.append(f"Structure {idx} missing keys: {', '.join(missing_s)}")
            continue

        family = structure["family"]
        if family not in ALLOWED_FAMILIES:
            errors.append(f"Structure {idx} has invalid family: {family}")

        for score_key in ("convexity_retained_score", "theta_funding_score", "tail_cleanliness_score"):
            score = structure.get(score_key)
            if not isinstance(score, (int, float)) or not (0 <= float(score) <= 10):
                errors.append(f"Structure {idx} has invalid {score_key}: {score}")

        max_loss = structure.get("max_loss")
        if not isinstance(max_loss, (int, float)) or float(max_loss) < 0:
            errors.append(f"Structure {idx} has invalid max_loss: {max_loss}")

        financing_ratio = structure.get("financing_ratio")
        if not isinstance(financing_ratio, (int, float)) or float(financing_ratio) < 0:
            errors.append(f"Structure {idx} has invalid financing_ratio: {financing_ratio}")
        else:
            ratio = float(financing_ratio)
            if ratio > 1.25:
                errors.append(f"Structure {idx} financing_ratio is too high for default rules: {ratio}")
            elif ratio > 1.0:
                warnings.append(f"Structure {idx} financing_ratio > 1.0; review hidden short-vol exposure carefully")

        if family == "range_defined_risk_premium_structure" and plan.get("directional_regime") in {"unstable", "event-dominated", "unstable / event-dominated"}:
            errors.append(f"Structure {idx} uses range family in an unstable regime")

        if family == "hedge_only" and not str(structure.get("event_risk_note", "")).strip():
            warnings.append(f"Structure {idx} is hedge_only but event_risk_note is empty")

        long_legs = structure.get("long_legs") or []
        short_legs = structure.get("short_legs") or []
        if not isinstance(long_legs, list) or not isinstance(short_legs, list):
            errors.append(f"Structure {idx} long_legs and short_legs must be lists")

    return errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=None, help="Optional explicit trade plan path")
    args = parser.parse_args()

    plan_path = Path(args.path) if args.path else latest_plan_file()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    errors, warnings = validate_plan(plan)

    payload = {
        "validated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trade_plan": plan_path.name,
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
    out_path = plan_path.with_name(plan_path.stem + VALIDATION_SUFFIX)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if errors:
        print(f"AEX_TRADE_PLAN_INVALID | file={plan_path.name} | validation={out_path.name} | errors={len(errors)}")
        raise SystemExit(1)
    print(f"AEX_TRADE_PLAN_VALID | file={plan_path.name} | validation={out_path.name} | warnings={len(warnings)}")


if __name__ == "__main__":
    main()
