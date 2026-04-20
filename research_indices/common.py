from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from pricing_indices.run_pricing_pass import requested_close_from_today

REPORT_RE = re.compile(r"weekly_indices_review_(\d{6})(?:_(\d{2}))?\.md$")
PRICING_RE = re.compile(r"index_price_audit_(\d{4}-\d{2}-\d{2})\.json$")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def resolve_requested_close_date(output_dir: Path, state_path: Path | None = None) -> str:
    state_path = state_path or (output_dir / "index_portfolio_state.json")
    if state_path.exists():
        state = read_json(state_path)
        requested = ((state.get("pricing_basis") or {}).get("requested_close_date"))
        if requested:
            return str(requested)

    pricing_dir = output_dir / "pricing"
    if pricing_dir.exists():
        candidates: list[str] = []
        for path in pricing_dir.glob("index_price_audit_*.json"):
            match = PRICING_RE.match(path.name)
            if match:
                candidates.append(match.group(1))
        if candidates:
            candidates.sort()
            return candidates[-1]

    return requested_close_from_today(date.today())
