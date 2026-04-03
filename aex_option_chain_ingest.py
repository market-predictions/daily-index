#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DELAYED_SNAPSHOT_PATH = Path("input_aex/aex_option_chain_delayed_snapshot.json")


def clean_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def first_non_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def parse_expiry_to_unix(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            as_int = int(float(value))
        except Exception:
            return None
        return as_int if as_int > 10_000_000 else None

    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        as_int = int(text)
        return as_int if as_int > 10_000_000 else None

    normalized = re.sub(r"\s+", " ", text).strip()
    candidates = [normalized]
    titled = normalized.title()
    if titled != normalized:
        candidates.append(titled)

    for candidate in candidates:
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y"):
            try:
                dt = datetime.strptime(candidate, fmt).replace(tzinfo=timezone.utc)
                return int(dt.timestamp())
            except ValueError:
                continue
    return None


def normalize_option_row(row: dict[str, Any]) -> dict[str, Any] | None:
    strike = first_non_none(clean_float(row.get("strike")), clean_float(row.get("strike_price")))
    if strike is None:
        return None

    return {
        "strike": strike,
        "bid": first_non_none(clean_float(row.get("bid")), clean_float(row.get("best_bid"))),
        "ask": first_non_none(clean_float(row.get("ask")), clean_float(row.get("best_ask"))),
        "lastPrice": first_non_none(
            clean_float(row.get("lastPrice")),
            clean_float(row.get("last")),
            clean_float(row.get("premium")),
            clean_float(row.get("price")),
        ),
        "impliedVolatility": first_non_none(
            clean_float(row.get("impliedVolatility")),
            clean_float(row.get("implied_volatility")),
            clean_float(row.get("iv")),
            clean_float(row.get("impliedVol")),
        ),
        "openInterest": first_non_none(row.get("openInterest"), row.get("open_interest")),
        "volume": row.get("volume"),
    }


def normalize_nested_payload(payload: dict[str, Any]) -> dict[str, Any]:
    spot = first_non_none(
        clean_float(payload.get("spot_price")),
        clean_float(payload.get("spot")),
        clean_float(payload.get("underlying_price")),
        clean_float(payload.get("reference_price")),
    )
    raw_expiries = payload.get("expiries") or []
    expiries: list[dict[str, Any]] = []

    for raw_expiry in raw_expiries:
        expiry_unix = parse_expiry_to_unix(
            first_non_none(
                raw_expiry.get("expiry_unix"),
                raw_expiry.get("expiry"),
                raw_expiry.get("expiry_date"),
                raw_expiry.get("expirationDate"),
                raw_expiry.get("expiration_date"),
            )
        )
        if not expiry_unix:
            continue

        calls = [row for item in (raw_expiry.get("calls") or []) if (row := normalize_option_row(item))]
        puts = [row for item in (raw_expiry.get("puts") or []) if (row := normalize_option_row(item))]
        if not calls or not puts:
            continue

        expiries.append({
            "expiry_unix": expiry_unix,
            "calls": calls,
            "puts": puts,
        })

    expiries.sort(key=lambda item: item["expiry_unix"])
    if spot is None or not expiries:
        raise RuntimeError("Provider option-chain payload is missing usable spot_price or complete expiries.")

    return {
        "provider": payload.get("provider", "external_provider_file"),
        "spot_price": spot,
        "expiries": expiries,
    }


def normalize_flat_delayed_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    spot = first_non_none(
        clean_float(payload.get("spot_price")),
        clean_float(payload.get("spot")),
        clean_float(payload.get("underlying_price")),
        clean_float(payload.get("reference_price")),
    )
    rows = payload.get("options") or payload.get("rows") or payload.get("quotes") or []
    grouped: dict[int, dict[str, Any]] = {}

    for raw_row in rows:
        expiry_unix = parse_expiry_to_unix(
            first_non_none(
                raw_row.get("expiry_unix"),
                raw_row.get("expiry"),
                raw_row.get("expiry_date"),
                raw_row.get("expiration"),
                raw_row.get("expiration_date"),
            )
        )
        if not expiry_unix:
            continue

        option_type = str(
            first_non_none(
                raw_row.get("option_type"),
                raw_row.get("type"),
                raw_row.get("right"),
                raw_row.get("contract_type"),
            ) or ""
        ).strip().lower()
        if option_type in {"c", "call", "calls"}:
            side_key = "calls"
        elif option_type in {"p", "put", "puts"}:
            side_key = "puts"
        else:
            continue

        normalized_row = normalize_option_row(raw_row)
        if not normalized_row:
            continue

        bucket = grouped.setdefault(expiry_unix, {"expiry_unix": expiry_unix, "calls": [], "puts": []})
        bucket[side_key].append(normalized_row)

    expiries = [
        grouped[key]
        for key in sorted(grouped)
        if grouped[key]["calls"] and grouped[key]["puts"]
    ]
    if spot is None or not expiries:
        raise RuntimeError("Delayed snapshot is missing usable spot_price or complete call/put rows.")

    return {
        "provider": payload.get("provider", "manual_delayed_snapshot"),
        "spot_price": spot,
        "expiries": expiries,
    }


def normalize_chain_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise RuntimeError("Option-chain payload must be a JSON object.")

    if payload.get("expiries"):
        return normalize_nested_payload(payload)

    if payload.get("options") or payload.get("rows") or payload.get("quotes"):
        return normalize_flat_delayed_snapshot(payload)

    raise RuntimeError("Unrecognized option-chain payload schema.")


def load_normalized_chain_payload(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return normalize_chain_payload(payload)
