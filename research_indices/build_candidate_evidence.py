from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pricing_indices.catalog import ALL_EXPOSURES
from .common import latest_report_token


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _load_optional(path: Path) -> dict[str, Any]:
    return _read_json(path) if path.exists() else {}


def _continuity_sets(plan: dict[str, Any]) -> tuple[set[str], set[str], set[str]]:
    continuity = plan.get("continuity") or {}
    return (
        set(continuity.get("retained_entries") or []),
        set(continuity.get("new_entries") or []),
        set(continuity.get("strong_challengers_not_published") or []),
    )


def _regime_alignment(exposure: dict[str, Any], macro: dict[str, Any]) -> tuple[float, list[str]]:
    region = exposure.get("region")
    exposure_id = exposure["exposure_id"]
    style = str(exposure.get("style") or "").lower()
    signals = macro.get("market_signals") or {}
    score = 0.0
    reasons: list[str] = []

    if signals.get("equity_risk_appetite") == "supportive":
        score += 0.15
        reasons.append("broad equity risk appetite is supportive")
    elif signals.get("equity_risk_appetite") == "headwind":
        score -= 0.20
        reasons.append("broad equity risk appetite is a headwind")

    if exposure_id == "us_large_cap":
        if signals.get("credit_support") == "supportive":
            score += 0.20
            reasons.append("credit conditions support core U.S. equity risk")
        if signals.get("breadth_confirmation") == "supportive":
            score += 0.10
            reasons.append("breadth confirmation supports the core U.S. anchor")

    if exposure_id == "us_tech_leadership":
        if signals.get("growth_leadership") == "supportive":
            score += 0.40
            reasons.append("growth leadership is supportive")
        elif signals.get("growth_leadership") == "headwind":
            score -= 0.25
            reasons.append("growth leadership is fading")
        if signals.get("duration_support") == "supportive":
            score += 0.10
            reasons.append("duration support reduces pressure on long-duration growth")
        elif signals.get("duration_support") == "headwind":
            score -= 0.15
            reasons.append("rates remain a headwind for long-duration growth")

    if exposure_id == "us_small_cap":
        if signals.get("breadth_confirmation") == "supportive":
            score += 0.40
            reasons.append("small-cap breadth is confirming")
        elif signals.get("breadth_confirmation") == "headwind":
            score -= 0.35
            reasons.append("small-cap breadth is weak")
        if signals.get("credit_support") == "supportive":
            score += 0.10
            reasons.append("credit support helps domestic cyclicality")

    if region == "Europe":
        if signals.get("europe_confirmation") == "supportive":
            score += 0.25
            reasons.append("Europe confirmation is supportive")
        elif signals.get("europe_confirmation") == "headwind":
            score -= 0.15
            reasons.append("Europe confirmation is fading")
        if signals.get("commodity_pressure") == "supportive":
            score -= 0.15
            reasons.append("commodity pressure can challenge Europe")
        if exposure_id == "germany_cyclicals" and signals.get("breadth_confirmation") == "supportive":
            score += 0.05
            reasons.append("cyclical breadth helps Europe’s higher-beta sleeve")

    if region == "Japan":
        if signals.get("japan_confirmation") == "supportive":
            score += 0.35
            reasons.append("Japan confirmation is supportive")
        elif signals.get("japan_confirmation") == "headwind":
            score -= 0.15
            reasons.append("Japan confirmation is fading")

    if region == "Emerging Markets":
        if signals.get("em_confirmation") == "supportive":
            score += 0.30
            reasons.append("EM confirmation is supportive")
        if signals.get("dollar_pressure") == "headwind":
            score += 0.20
            reasons.append("dollar pressure is easing")
        elif signals.get("dollar_pressure") == "supportive":
            score -= 0.25
            reasons.append("dollar pressure is a headwind")

    if region in {"China", "Hong Kong", "India"}:
        if signals.get("em_confirmation") == "supportive":
            score += 0.18
            reasons.append("broader EM confirmation is supportive")
        if signals.get("dollar_pressure") == "headwind":
            score += 0.12
            reasons.append("dollar pressure is easing")
        elif signals.get("dollar_pressure") == "supportive":
            score -= 0.18
            reasons.append("dollar pressure is a headwind")

    if region in {"Canada", "Australia"}:
        if signals.get("commodity_pressure") == "supportive":
            score += 0.12
            reasons.append("commodity-linked markets can benefit from firmer resource pressure")
        if signals.get("equity_risk_appetite") == "supportive":
            score += 0.05
            reasons.append("global equity appetite helps developed resource markets")

    if region == "UK" and signals.get("equity_risk_appetite") == "supportive":
        score += 0.05
        reasons.append("risk appetite modestly supports the UK large-cap sleeve")

    return round(score, 3), reasons


def _implementation_priority(exposure: dict[str, Any], current_positions: dict[str, Any]) -> tuple[float, list[str]]:
    exposure_id = exposure["exposure_id"]
    position = current_positions.get(exposure_id)
    if not position:
        return 0.0, []

    role = str(position.get("role") or "").lower()
    score = 0.55
    reasons = ["already implemented in the live model portfolio"]

    if "core" in role:
        score += 0.25
        reasons.append("holds a core portfolio role")
    if "growth engine" in role:
        score += 0.25
        reasons.append("functions as a growth engine in the current portfolio")
    if "breadth" in role:
        score += 0.15
        reasons.append("adds funded breadth diversification")
    if "non-u.s. risk sleeve" in role:
        score += 0.10
        reasons.append("already serves as the funded non-U.S. sleeve")

    return round(score, 3), reasons


def _diversification_value(exposure: dict[str, Any], current_positions: dict[str, Any]) -> tuple[float, list[str]]:
    held_regions = {pos.get("region") for pos in current_positions.values()}
    held_styles = {pos.get("style") for pos in current_positions.values()}
    score = 0.0
    reasons: list[str] = []

    if exposure["exposure_id"] in current_positions:
        return 0.0, []

    if exposure.get("region") not in held_regions:
        score += 0.20
        reasons.append("adds a new regional sleeve")
    else:
        score += 0.08
        reasons.append("broadens opportunity within an already held region")

    if exposure.get("style") not in held_styles:
        score += 0.08
        reasons.append("adds a differentiated style bucket")

    return round(score, 3), reasons


def _fragility_penalty(exposure: dict[str, Any], macro: dict[str, Any]) -> tuple[float, list[str]]:
    region = exposure.get("region")
    exposure_id = exposure["exposure_id"]
    signals = macro.get("market_signals") or {}
    penalty = 0.0
    reasons: list[str] = []

    if exposure_id in {"us_tech_leadership", "us_small_cap"} and signals.get("duration_support") == "headwind":
        penalty += 0.20
        reasons.append("rates/duration backdrop is not supportive")
    if region in {"Emerging Markets", "China", "Hong Kong", "India"} and signals.get("dollar_pressure") == "supportive":
        penalty += 0.30
        reasons.append("dollar strength is a fragility factor")
    if region == "Europe" and signals.get("commodity_pressure") == "supportive":
        penalty += 0.15
        reasons.append("commodity pressure adds European fragility")

    return round(penalty, 3), reasons


def build_evidence(output_dir: Path, token: str) -> dict[str, Any]:
    research_dir = output_dir / "research"
    rs_path = research_dir / f"index_relative_strength_snapshot_{token}.json"
    macro_path = research_dir / f"index_macro_snapshot_{token}.json"
    state_path = output_dir / "index_portfolio_state.json"
    plan_path = output_dir / f"index_recommendation_plan_{token}.json"

    if not rs_path.exists():
        raise FileNotFoundError(f"Missing relative strength snapshot: {rs_path}")
    if not macro_path.exists():
        raise FileNotFoundError(f"Missing macro snapshot: {macro_path}")
    if not state_path.exists():
        raise FileNotFoundError(f"Missing portfolio state: {state_path}")

    rs = _read_json(rs_path)
    macro = _read_json(macro_path)
    state = _read_json(state_path)
    plan = _load_optional(plan_path)

    rs_map = {row["exposure_id"]: row for row in (rs.get("rows") or [])}
    positions = {row.get("exposure_id"): row for row in (state.get("positions") or [])}
    retained, new_entries, strong_challengers = _continuity_sets(plan)

    evidence_rows: list[dict[str, Any]] = []
    for exposure in ALL_EXPOSURES:
        exposure_id = exposure["exposure_id"]
        rs_row = rs_map.get(exposure_id, {})
        rs_score = float(rs_row.get("relative_strength_score") or 0.0)
        regime_score, regime_reasons = _regime_alignment(exposure, macro)
        implementation_priority_score, implementation_reasons = _implementation_priority(exposure, positions)
        diversification_score, diversification_reasons = _diversification_value(exposure, positions)
        fragility_penalty, fragility_reasons = _fragility_penalty(exposure, macro)
        continuity_bonus = 0.0
        continuity_reasons: list[str] = []
        if exposure_id in retained:
            continuity_bonus += 0.20
            continuity_reasons.append("retained in continuity memory")
        if exposure_id in new_entries:
            continuity_bonus += 0.15
            continuity_reasons.append("new entry in continuity memory")
        if exposure_id in strong_challengers:
            continuity_bonus += 0.08
            continuity_reasons.append("already surfaced as a strong challenger")

        board_score = rs_score + regime_score + implementation_priority_score + continuity_bonus + (0.35 * diversification_score) - fragility_penalty
        challenger_score = rs_score + regime_score + diversification_score + (0.35 * continuity_bonus) - fragility_penalty

        evidence_rows.append(
            {
                "exposure_id": exposure_id,
                "public_index_name": exposure["display_name"],
                "benchmark_symbol": exposure["benchmark_symbol"],
                "primary_proxy": exposure["primary_proxy"],
                "alternative_proxy": exposure.get("alternative_proxy"),
                "region": exposure.get("region"),
                "style": exposure.get("style"),
                "currently_held": exposure_id in positions,
                "relative_strength_score": round(rs_score, 3),
                "regime_alignment_score": round(regime_score, 3),
                "implementation_priority_score": round(implementation_priority_score, 3),
                "diversification_score": round(diversification_score, 3),
                "continuity_bonus": round(continuity_bonus, 3),
                "fragility_penalty": round(fragility_penalty, 3),
                "board_score": round(board_score, 3),
                "challenger_score": round(challenger_score, 3),
                "final_score": round(board_score, 3),
                "relative_strength_metrics": {
                    "requested_close_date": rs_row.get("requested_close_date"),
                    "selected_data_date": rs_row.get("selected_data_date"),
                    "return_20d": rs_row.get("return_20d"),
                    "return_60d": rs_row.get("return_60d"),
                    "return_120d": rs_row.get("return_120d"),
                    "drawdown_from_120d_high": rs_row.get("drawdown_from_120d_high"),
                    "analysis_symbol": rs_row.get("analysis_symbol"),
                },
                "evidence_notes": {
                    "regime_alignment": regime_reasons,
                    "implementation_priority": implementation_reasons,
                    "diversification": diversification_reasons,
                    "continuity": continuity_reasons,
                    "fragility": fragility_reasons,
                },
            }
        )

    evidence_rows.sort(key=lambda row: (-float(row["board_score"]), -float(row["challenger_score"]), row["public_index_name"]))
    return {
        "report_date_token": token,
        "requested_close_date": rs.get("requested_close_date") or macro.get("requested_close_date"),
        "macro_snapshot_file": macro_path.name,
        "relative_strength_snapshot_file": rs_path.name,
        "positions_state_file": state_path.name,
        "rows": evidence_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output_indices")
    parser.add_argument("--token", default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    token = args.token or latest_report_token(output_dir)
    payload = build_evidence(output_dir, token)
    path = output_dir / "research" / f"index_candidate_evidence_{token}.json"
    _write_json(path, payload)
    top = payload["rows"][0]["public_index_name"] if payload["rows"] else "none"
    print(f"CANDIDATE_EVIDENCE_OK | token={token} | file={path.name} | top={top}")


if __name__ == "__main__":
    main()
