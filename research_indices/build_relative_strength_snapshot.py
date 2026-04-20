from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

from pricing_indices.catalog import ALL_EXPOSURES
from pricing_indices.data_sources import fetch_yahoo_history

REPORT_RE = re.compile(r"weekly_indices_review_(\d{6})(?:_(\d{2}))?\.md$")


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


def _pct_return(rows: list[dict[str, Any]], lookback: int) -> float | None:
    if len(rows) <= lookback:
        return None
    latest = float(rows[-1]["close"])
    base = float(rows[-1 - lookback]["close"])
    if base == 0:
        return None
    return (latest / base) - 1.0


def _drawdown_from_high(rows: list[dict[str, Any]], lookback: int = 120) -> float:
    sample = rows[-lookback:] if len(rows) >= lookback else rows
    high = max(float(row["close"]) for row in sample)
    latest = float(sample[-1]["close"])
    if high == 0:
        return 0.0
    return (latest / high) - 1.0


def _composite_score(r20: float | None, r60: float | None, r120: float | None, drawdown: float) -> float:
    parts = []
    if r20 is not None:
        parts.append(0.45 * r20)
    if r60 is not None:
        parts.append(0.35 * r60)
    if r120 is not None:
        parts.append(0.20 * r120)
    base = sum(parts)
    penalty = max(0.0, abs(min(drawdown, 0.0))) * 0.20
    return base - penalty


def _score_0_2(percentile: float) -> float:
    return round(max(0.0, min(2.0, percentile * 2.0)), 2)


def _fetch_history_with_fallback(exposure: dict[str, Any], requested_close_date: str | None) -> dict[str, Any]:
    attempts = [
        ("benchmark", exposure["benchmark_symbol"]),
        ("proxy", exposure["primary_proxy"]),
    ]
    last_error = None
    for source_type, symbol in attempts:
        try:
            history = fetch_yahoo_history(symbol, requested_close_date=requested_close_date, range_period="1y", interval="1d")
            history["analysis_symbol"] = symbol
            history["analysis_source_type"] = source_type
            return history
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
    raise RuntimeError(last_error or f"Unable to fetch history for {exposure['exposure_id']}")


def build_snapshot(output_dir: Path, requested_close_date: str | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for exposure in ALL_EXPOSURES:
        try:
            history = _fetch_history_with_fallback(exposure, requested_close_date=requested_close_date)
            price_rows = history["rows"]
            r20 = _pct_return(price_rows, 20)
            r60 = _pct_return(price_rows, 60)
            r120 = _pct_return(price_rows, 120)
            drawdown = _drawdown_from_high(price_rows, 120)
            composite = _composite_score(r20, r60, r120, drawdown)
            rows.append(
                {
                    "exposure_id": exposure["exposure_id"],
                    "public_index_name": exposure["display_name"],
                    "analysis_symbol": history["analysis_symbol"],
                    "analysis_source_type": history["analysis_source_type"],
                    "primary_proxy": exposure["primary_proxy"],
                    "region": exposure.get("region"),
                    "regional_group": exposure.get("region"),
                    "return_20d": round(r20, 6) if r20 is not None else None,
                    "return_60d": round(r60, 6) if r60 is not None else None,
                    "return_120d": round(r120, 6) if r120 is not None else None,
                    "drawdown_from_120d_high": round(drawdown, 6),
                    "latest_close": round(float(price_rows[-1]["close"]), 6),
                    "latest_date": price_rows[-1]["date"],
                    "composite_score_raw": round(composite, 6),
                }
            )
        except Exception as exc:  # noqa: BLE001
            rows.append(
                {
                    "exposure_id": exposure["exposure_id"],
                    "public_index_name": exposure["display_name"],
                    "analysis_symbol": None,
                    "analysis_source_type": None,
                    "primary_proxy": exposure["primary_proxy"],
                    "region": exposure.get("region"),
                    "regional_group": exposure.get("region"),
                    "return_20d": None,
                    "return_60d": None,
                    "return_120d": None,
                    "drawdown_from_120d_high": None,
                    "latest_close": None,
                    "latest_date": None,
                    "composite_score_raw": None,
                    "error": str(exc),
                }
            )

    valid_scores = [row["composite_score_raw"] for row in rows if row.get("composite_score_raw") is not None]
    valid_scores_sorted = sorted(valid_scores)
    for row in rows:
        raw = row.get("composite_score_raw")
        if raw is None or not valid_scores_sorted:
            row["percentile"] = None
            row["relative_strength_score"] = 0.0
            continue
        rank = sum(1 for value in valid_scores_sorted if value <= raw)
        percentile = rank / len(valid_scores_sorted)
        row["percentile"] = round(percentile, 4)
        row["relative_strength_score"] = _score_0_2(percentile)

    rows.sort(key=lambda row: (-(row.get("relative_strength_score") or 0.0), row["public_index_name"]))
    return {
        "requested_close_date": requested_close_date,
        "universe_size": len(rows),
        "methodology": {
            "returns": [20, 60, 120],
            "composite_formula": "0.45*r20 + 0.35*r60 + 0.20*r120 - 0.20*abs(min(drawdown_from_120d_high,0))",
            "normalized_score": "percentile mapped to 0..2",
        },
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="output_indices")
    parser.add_argument("--token", default=None)
    parser.add_argument("--requested-close-date", default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    token = args.token or latest_report_token(output_dir)
    payload = build_snapshot(output_dir, requested_close_date=args.requested_close_date)
    path = output_dir / "research" / f"index_relative_strength_snapshot_{token}.json"
    _write_json(path, payload)
    top = payload["rows"][0]["public_index_name"] if payload["rows"] else "none"
    print(f"RELATIVE_STRENGTH_SNAPSHOT_OK | token={token} | file={path.name} | top={top}")


if __name__ == "__main__":
    main()
