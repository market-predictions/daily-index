#!/usr/bin/env python3
"""
Build output_aex/aex_macro_snapshot.json.

Goal:
- produce a conservative macro / policy / geopolitical snapshot for the weekly AEX options workflow
- use live public sources where possible
- fail safe and label missing fields clearly
- allow a manual overlay file to enrich the snapshot without changing code

Current design:
- ECB key rates: scrape current public ECB key interest rates page
- Euro area inflation / unemployment / GDP: scrape the Eurostat Euro indicators landing page and the latest matching detail pages
- Market spillover context: read the already-built cross-market confirmation snapshot
- Optional manual overlay: input_aex/aex_macro_manual_overlay.json
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any

import requests

OUTPUT_PATH = Path("output_aex/aex_macro_snapshot.json")
CROSS_PATH = Path("output_aex/aex_cross_market_confirmation.json")
MANUAL_OVERLAY_PATH = Path("input_aex/aex_macro_manual_overlay.json")

ECB_RATES_URL = "https://data.ecb.europa.eu/key-figures/ecb-interest-rates-and-exchange-rates/key-ecb-interest-rates"
EUROSTAT_NEWS_URL = "https://ec.europa.eu/eurostat/news/euro-indicators"

USER_AGENT = "Mozilla/5.0 (compatible; DailyIndexOS/1.0)"


def fetch_text(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    return response.text


def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text)).strip()


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def parse_ecb_rates() -> dict[str, Any]:
    text = collapse_ws(fetch_text(ECB_RATES_URL))
    payload: dict[str, Any] = {
        "mro_rate_pct": None,
        "deposit_rate_pct": None,
        "marginal_lending_rate_pct": None,
        "source": ECB_RATES_URL,
        "status": "unavailable",
    }

    patterns = [
        ("mro_rate_pct", r"Main refinancing operations .*? ([0-9]+(?:\.[0-9]+)?) ?%"),
        ("marginal_lending_rate_pct", r"Marginal lending facility .*? ([0-9]+(?:\.[0-9]+)?) ?%"),
        ("deposit_rate_pct", r"Deposit facility .*? ([0-9]+(?:\.[0-9]+)?) ?%"),
    ]
    matched = 0
    for key, pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            payload[key] = float(match.group(1))
            matched += 1
    if matched:
        payload["status"] = "live_public_scrape"
    return payload


def eurostat_story_links() -> dict[str, str]:
    text = fetch_text(EUROSTAT_NEWS_URL)
    links = {}
    patterns = {
        "inflation": r'href="([^"]+)"[^>]*>[^<]*inflation[^<]*</a>',
        "unemployment": r'href="([^"]+)"[^>]*>[^<]*unemployment[^<]*</a>',
        "gdp": r'href="([^"]+)"[^>]*>[^<]*GDP[^<]*employment[^<]*</a>',
    }
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        if matches:
            href = matches[0]
            if href.startswith("/"):
                href = "https://ec.europa.eu" + href
            links[key] = href
    return links


def parse_inflation(url: str | None) -> dict[str, Any]:
    payload = {"annual_inflation_pct": None, "title": None, "source": url, "status": "unavailable"}
    if not url:
        return payload
    raw = fetch_text(url)
    text = collapse_ws(raw)
    title_match = re.search(r"<title>(.*?)</title>", raw, flags=re.IGNORECASE | re.DOTALL)
    if title_match:
        payload["title"] = collapse_ws(title_match.group(1))
    inflation_match = re.search(r"annual inflation .*? ([0-9]+(?:\.[0-9]+)?)%", text, flags=re.IGNORECASE)
    if inflation_match:
        payload["annual_inflation_pct"] = float(inflation_match.group(1))
        payload["status"] = "live_public_scrape"
    return payload


def parse_unemployment(url: str | None) -> dict[str, Any]:
    payload = {"unemployment_rate_pct": None, "title": None, "source": url, "status": "unavailable"}
    if not url:
        return payload
    raw = fetch_text(url)
    text = collapse_ws(raw)
    title_match = re.search(r"Euro area unemployment at ([0-9]+(?:\.[0-9]+)?)%", text, flags=re.IGNORECASE)
    if title_match:
        payload["unemployment_rate_pct"] = float(title_match.group(1))
        payload["status"] = "live_public_scrape"
    return payload


def parse_gdp(url: str | None) -> dict[str, Any]:
    payload = {
        "gdp_qoq_pct": None,
        "employment_qoq_pct": None,
        "source": url,
        "status": "unavailable",
    }
    if not url:
        return payload
    text = collapse_ws(fetch_text(url))
    match = re.search(
        r"GDP up by ([0-9]+(?:\.[0-9]+)?)% and employment up by ([0-9]+(?:\.[0-9]+)?)% in the euro area",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        payload["gdp_qoq_pct"] = float(match.group(1))
        payload["employment_qoq_pct"] = float(match.group(2))
        payload["status"] = "live_public_scrape"
    return payload


def infer_regime(ecb: dict[str, Any], inflation: dict[str, Any], unemployment: dict[str, Any], gdp: dict[str, Any], cross: dict[str, Any] | None, manual: dict[str, Any] | None) -> tuple[str, str, list[str]]:
    notes: list[str] = []
    cross_overall = (cross or {}).get("overall_confirmation", "unknown")
    deposit = ecb.get("deposit_rate_pct")
    inf = inflation.get("annual_inflation_pct")
    unemp = unemployment.get("unemployment_rate_pct")
    gdp_qoq = gdp.get("gdp_qoq_pct")

    if manual and manual.get("dominant_driver"):
        notes.append(f"manual dominant driver: {manual['dominant_driver']}")

    regime = "mixed_macro"
    driver = "data_incomplete"

    if inf is not None and deposit is not None and inf > 2.2 and deposit >= 2.0:
        regime = "restrictive_with_inflation_reacceleration"
        driver = "inflation_reacceleration"
    elif gdp_qoq is not None and gdp_qoq > 0.2 and unemp is not None and unemp <= 6.2 and cross_overall == "supportive_risk":
        regime = "soft_growth_supportive_risk"
        driver = "growth_stability"
    elif cross_overall == "defensive_confirmation":
        regime = "risk_defensive"
        driver = "cross_market_defensiveness"
    elif inf is not None and inf < 2.0 and deposit is not None and deposit > inf:
        regime = "disinflationary_restrictive"
        driver = "real_rates_still_positive"

    if manual and manual.get("regime_override"):
        regime = str(manual["regime_override"])
        notes.append("manual regime override applied")
    if manual and manual.get("driver_override"):
        driver = str(manual["driver_override"])
        notes.append("manual driver override applied")

    return regime, driver, notes


def build_payload() -> dict[str, Any]:
    cross = load_json(CROSS_PATH)
    manual = load_json(MANUAL_OVERLAY_PATH)

    links = eurostat_story_links()
    ecb = parse_ecb_rates()
    inflation = parse_inflation(links.get("inflation"))
    unemployment = parse_unemployment(links.get("unemployment"))
    gdp = parse_gdp(links.get("gdp"))

    regime, driver, notes = infer_regime(ecb, inflation, unemployment, gdp, cross, manual)

    payload = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "regime_horizon_days": 5,
        "macro_regime": regime,
        "dominant_driver": driver,
        "ecb": ecb,
        "inflation": inflation,
        "unemployment": unemployment,
        "growth": gdp,
        "cross_market_context": cross or {},
        "manual_overlay_used": bool(manual),
        "geopolitical_flags": list((manual or {}).get("geopolitical_flags", [])),
        "energy_flags": list((manual or {}).get("energy_flags", [])),
        "invalidators": list((manual or {}).get("invalidators", [])),
        "aex_sector_notes": dict((manual or {}).get("aex_sector_notes", {})),
        "macro_notes": notes + list((manual or {}).get("macro_notes", [])),
    }
    return payload


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"AEX_MACRO_SNAPSHOT_OK | file={OUTPUT_PATH}")


if __name__ == "__main__":
    main()
