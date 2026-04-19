from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .catalog import ALL_EXPOSURES, BY_EXPOSURE_ID

REPORT_RE = re.compile(r"weekly_indices_review_(\d{6})(?:_(\d{2}))?\.md$")
PLAN_RE = re.compile(r"index_recommendation_plan_(\d{6})(?:_(\d{2}))?\.json$")

GROUPS = {
    "U.S. core leadership": {"us_large_cap", "us_tech_leadership", "us_small_cap"},
    "continental Europe": {"europe_large_cap", "germany_cyclicals", "france_large_cap", "spain_large_cap", "italy_large_cap", "netherlands_large_cap"},
    "UK": {"uk_large_cap"},
    "North America ex-U.S.": {"canada_large_cap"},
    "developed Asia-Pacific": {"japan_equities", "australia_large_cap"},
    "Greater China": {"hong_kong_equities", "china_large_cap"},
    "India": {"india_large_cap"},
    "EM broad": {"em_broad"},
}

GROUP_BASE_SCORE = {
    "U.S. core leadership": 3.75,
    "continental Europe": 3.35,
    "UK": 3.10,
    "North America ex-U.S.": 3.05,
    "developed Asia-Pacific": 3.45,
    "Greater China": 3.00,
    "India": 3.25,
    "EM broad": 3.20,
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def latest_path(output_dir: Path, regex: re.Pattern[str], glob_pattern: str) -> Path | None:
    hits: list[tuple[str, int, Path]] = []
    for path in output_dir.glob(glob_pattern):
        match = regex.match(path.name)
        if match:
            hits.append((match.group(1), int(match.group(2) or "0"), path))
    if not hits:
        return None
    hits.sort(key=lambda x: (x[0], x[1]))
    return hits[-1][2]


def report_date_token(output_dir: Path) -> tuple[str, Path]:
    latest_report = latest_path(output_dir, REPORT_RE, "weekly_indices_review_*.md")
    if latest_report is None:
        raise FileNotFoundError("No weekly_indices_review_*.md file found")
    match = REPORT_RE.match(latest_report.name)
    assert match is not None
    return match.group(1), latest_report


def parse_report_board_text(report_path: Path) -> str:
    text = report_path.read_text(encoding="utf-8")
    start = text.find("## 4. Index Opportunity Board")
    if start == -1:
        return text
    end = text.find("## 5. Key Risks", start)
    return text[start:end if end != -1 else None]


def plan_for_token(output_dir: Path, token: str) -> dict[str, Any]:
    exact = output_dir / f"index_recommendation_plan_{token}.json"
    if exact.exists():
        return _read_json(exact)
    latest_plan = latest_path(output_dir, PLAN_RE, "index_recommendation_plan_*.json")
    return _read_json(latest_plan) if latest_plan else {}


def regional_group(exposure_id: str) -> str:
    for group, ids in GROUPS.items():
        if exposure_id in ids:
            return group
    return "Other"


def build_candidates(state: dict[str, Any], plan: dict[str, Any], board_text: str) -> list[dict[str, Any]]:
    positions = {p.get("exposure_id"): p for p in (state.get("positions") or [])}
    best_new = {item.get("exposure_id"): item for item in (plan.get("best_new_opportunities") or [])}
    strong_challengers = set((plan.get("continuity") or {}).get("strong_challengers_not_published") or [])
    continuity_new = set((plan.get("continuity") or {}).get("new_entries") or [])
    continuity_retained = set((plan.get("continuity") or {}).get("retained_entries") or [])

    candidates: list[dict[str, Any]] = []
    board_lower = board_text.lower()
    for exposure in ALL_EXPOSURES:
        exposure_id = exposure["exposure_id"]
        group = regional_group(exposure_id)
        score = GROUP_BASE_SCORE.get(group, 3.0)
        held = exposure_id in positions
        if held:
            score += 0.45
        if exposure_id in continuity_new:
            score += 0.20
        if exposure_id in continuity_retained:
            score += 0.15
        if exposure_id in best_new:
            score = max(score, float(best_new[exposure_id].get("score") or score))
        if exposure_id in strong_challengers:
            score += 0.10

        display_name = exposure["display_name"]
        proxy = exposure["primary_proxy"]
        publish = (display_name.lower() in board_lower) or (proxy.lower() in board_lower)

        if publish:
            reason_code = "published_on_board"
        elif exposure_id in strong_challengers:
            reason_code = "strong_challenger_not_published"
        elif exposure_id in best_new:
            reason_code = "best_new_not_on_board"
        elif held:
            reason_code = "held_but_not_board_named"
        else:
            reason_code = "below_board_cutoff"

        position = positions.get(exposure_id, {})
        candidates.append(
            {
                "exposure_id": exposure_id,
                "public_index_name": display_name,
                "benchmark_symbol": exposure["benchmark_symbol"],
                "primary_proxy": proxy,
                "alternative_proxy": exposure.get("alternative_proxy"),
                "regional_group": group,
                "region": exposure.get("region"),
                "style": exposure.get("style"),
                "currently_held": held,
                "weight_pct": position.get("weight_pct"),
                "score": round(min(score, 4.60), 2),
                "publish": publish,
                "reason_code_if_not_published": "" if publish else reason_code,
            }
        )

    candidates.sort(key=lambda item: (-float(item["score"]), item["public_index_name"]))
    return candidates


def build_coverage(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    coverage: list[dict[str, Any]] = []
    for group, ids in GROUPS.items():
        group_candidates = [c for c in candidates if c["exposure_id"] in ids]
        strongest = group_candidates[0] if group_candidates else None
        if strongest is None:
            coverage.append({
                "group": group,
                "status": "ruled_out",
                "reason_if_ruled_out": "no_candidate_available",
                "strongest_candidate": None,
            })
            continue
        status = "considered"
        if strongest["publish"]:
            status = "surfaced"
        elif strongest["reason_code_if_not_published"] in {"strong_challenger_not_published", "best_new_not_on_board"}:
            status = "near_miss"
        coverage.append(
            {
                "group": group,
                "status": status,
                "reason_if_ruled_out": "",
                "strongest_candidate": {
                    "exposure_id": strongest["exposure_id"],
                    "public_index_name": strongest["public_index_name"],
                    "primary_proxy": strongest["primary_proxy"],
                    "score": strongest["score"],
                    "publish": strongest["publish"],
                    "reason_code_if_not_published": strongest["reason_code_if_not_published"],
                },
            }
        )
    return coverage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output_indices")
    parser.add_argument("--state-path", default="output_indices/index_portfolio_state.json")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    state_path = Path(args.state_path)
    if not state_path.exists():
        raise FileNotFoundError(f"Missing state file: {state_path}")

    token, latest_report = report_date_token(output_dir)
    state = _read_json(state_path)
    plan = plan_for_token(output_dir, token)
    board_text = parse_report_board_text(latest_report)

    candidates = build_candidates(state, plan, board_text)
    coverage = build_coverage(candidates)

    ranking_payload = {
        "report_date_token": token,
        "report_file": latest_report.name,
        "regional_group_status": coverage,
        "candidates": candidates,
    }
    coverage_payload = {
        "report_date_token": token,
        "report_file": latest_report.name,
        "groups": coverage,
    }

    ranking_path = output_dir / f"index_candidate_ranking_{token}.json"
    coverage_path = output_dir / f"index_discovery_coverage_{token}.json"
    _write_json(ranking_path, ranking_payload)
    _write_json(coverage_path, coverage_payload)

    surfaced = sum(1 for row in coverage if row["status"] == "surfaced")
    near_miss = sum(1 for row in coverage if row["status"] == "near_miss")
    print(
        f"CANDIDATE_ARTIFACTS_OK | report={latest_report.name} | ranking={ranking_path.name} | "
        f"coverage={coverage_path.name} | surfaced_groups={surfaced} | near_miss_groups={near_miss}"
    )


if __name__ == "__main__":
    main()
