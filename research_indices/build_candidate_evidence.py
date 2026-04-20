from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from pricing_indices.catalog import ALL_EXPOSURES

REPORT_RE = re.compile(r"weekly_indices_review_(\d{6})(?:_(\d{2}))?\.md$")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def latest_report_token(output_dir: Path) -> str:
    hits: list[tuple[str, int]] = []
    for path in output_dir.glob("weekly_indices_review_*.md"):
        match = REPORT_RE.match(path.name)
        if match:
            hits.append((match.group(1), int(match.group(2) or "0")))
    if not hits:
        raise FileNotFoundError("No weekly_indices_review_*.md file found")
    hits.sort(key=lambda x: (x[0], x[1]))
    return hits[-1][0]


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
    signals = macro.get("market_signals") or {}
    score = 0.0
    reasons: list[str] = []

    if signals.get("equity_risk_appetite") == "supportive":
        score += 0.35
        reasons.append("broad equity risk appetite is supportive")
    elif signals.get("equity_risk_appetite") == "headwind":
        score -= 0.35
        reasons.append("broad equity risk appetite is a headwind")

    if exposure_id == "us_tech_leadership":
        if signals.get("growth_leadership") == "supportive":
            score += 0.55
            reasons.append("growth leadership is supportive")
        elif signals.get("growth_leadership") == "headwind":
            score -= 0.35
            reasons.append("growth leadership is fading")

    if exposure_id == "us_small_cap":
        if signals.get("breadth_confirmation") == "supportive":
            score += 0.50
            reasons.append("small-cap breadth is confirming")
        elif signals.get("breadth_confirmation") == "headwind":
            score -= 0.45
            reasons.append("small-cap breadth is weak")

    if region == "Europe" and signals.get("europe_confirmation") == "supportive":
        score += 0.45
        reasons.append("Europe confirmation is supportive")
    if region == "Japan" and signals.get("japan_confirmation") == "supportive":
        score += 0.50
        reasons.append("Japan confirmation is supportive")
    if region in {"Emerging Markets", "China", "Hong Kong", "India"} and signals.get("em_confirmation") == "supportive":
        score += 0.35
        reasons.append("EM confirmation is supportive")

    if region in {"Emerging Markets", "China", "Hong Kong", "India"}:
        if signals.get("dollar_pressure") == "supportive":
            score -= 0.40
            reasons.append("dollar pressure is a headwind")
        elif signals.get("dollar_pressure") == "headwind":
            score += 0.25
            reasons.append("dollar pressure is easing")

    if region in {"Canada", "Australia"} and signals.get("commodity_pressure") == "supportive":
        score += 0.20
        reasons.append("commodity pressure can support resource-heavy markets")
    if region == "Europe" and signals.get("commodity_pressure") == "supportive":
        score -= 0.10
        reasons.append("commodity pressure can challenge Europe")

    return round(score, 3), reasons


def _diversification_value(exposure: dict[str, Any], current_positions: dict[str, Any]) -> tuple[float, list[str]]:
    held_regions = {pos.get("region") for pos in current_positions.values()}
    held_styles = {pos.get("style") for pos in current_positions.values()}
    score = 0.0
    reasons: list[str] = []
    if exposure["exposure_id"] in current_positions:
        score += 0.10
        reasons.append("already implemented and continuity matters")
    elif exposure.get("region") not in held_regions:
        score += 0.55
        reasons.append("adds a new regional sleeve")
    else:
        score += 0.20
        reasons.append("keeps diversification within an existing region")

    if exposure.get("style") not in held_styles:
        score += 0.20
        reasons.append("adds a differentiated style bucket")

    return round(score, 3), reasons


def _fragility_penalty(exposure: dict[str, Any], macro: dict[str, Any]) -> tuple[float, list[str]]:
    region = exposure.get("region")
    exposure_id = exposure["exposure_id"]
    signals = macro.get("market_signals") or {}
    penalty = 0.0
    reasons: list[str] = []

    if exposure_id in {"us_tech_leadership", "us_small_cap"} and signals.get("duration_support") == "headwind":
        penalty += 0.25
        reasons.append("rates/duration backdrop is not supportive")
    if region in {"Emerging Markets", "China", "Hong Kong", "India"} and signals.get("dollar_pressure") == "supportive":
        penalty += 0.35
        reasons.append("dollar strength is a fragility factor")
    if region == "Europe" and signals.get("commodity_pressure") == "supportive":
        penalty += 0.10
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
        diversification_score, diversification_reasons = _diversification_value(exposure, positions)
        fragility_penalty, fragility_reasons = _fragility_penalty(exposure, macro)
        continuity_bonus = 0.0
        continuity_reasons: list[str] = []
        if exposure_id in retained:
            continuity_bonus += 0.15
            continuity_reasons.append("retained in continuity memory")
        if exposure_id in new_entries:
            continuity_bonus += 0.10
            continuity_reasons.append("new entry in continuity memory")
        if exposure_id in strong_challengers:
            continuity_bonus += 0.15
            continuity_reasons.append("already surfaced as a strong challenger")

        final_score = rs_score + regime_score + diversification_score + continuity_bonus - fragility_penalty
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
                "diversification_score": round(diversification_score, 3),
                "continuity_bonus": round(continuity_bonus, 3),
                "fragility_penalty": round(fragility_penalty, 3),
                "final_score": round(final_score, 3),
                "relative_strength_metrics": {
                    "return_20d": rs_row.get("return_20d"),
                    "return_60d": rs_row.get("return_60d"),
                    "return_120d": rs_row.get("return_120d"),
                    "drawdown_from_120d_high": rs_row.get("drawdown_from_120d_high"),
                    "analysis_symbol": rs_row.get("analysis_symbol"),
                },
                "evidence_notes": {
                    "regime_alignment": regime_reasons,
                    "diversification": diversification_reasons,
                    "continuity": continuity_reasons,
                    "fragility": fragility_reasons,
                },
            }
        )

    evidence_rows.sort(key=lambda row: (-float(row["final_score"]), row["public_index_name"]))
    return {
        "report_date_token": token,
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
