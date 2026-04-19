from __future__ import annotations

import json
from datetime import date
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


def _read_url(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=20) as response:
        return response.read()


def _json_get(url: str) -> Any:
    return json.loads(_read_url(url).decode("utf-8"))


def requested_close_from_today(today: date) -> str:
    d = today
    while d.weekday() >= 5:
        d = d.fromordinal(d.toordinal() - 1)
    return d.isoformat()


def fetch_yahoo_close(symbol: str, requested_close_date: str | None = None) -> dict[str, Any]:
    encoded = quote(symbol, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        f"?interval=1d&range=3mo&includePrePost=false&events=div%2Csplits"
    )
    payload = _json_get(url)
    result = payload.get("chart", {}).get("result", [])
    if not result:
        raise RuntimeError(f"No Yahoo chart result for symbol: {symbol}")

    block = result[0]
    timestamps = block.get("timestamp") or []
    quote_block = (block.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote_block.get("close") or []
    opens = quote_block.get("open") or []
    highs = quote_block.get("high") or []
    lows = quote_block.get("low") or []
    currency = block.get("meta", {}).get("currency") or "USD"

    rows: list[dict[str, Any]] = []
    for idx, ts in enumerate(timestamps):
        if idx >= len(closes):
            continue
        close_value = closes[idx]
        if close_value is None:
            continue
        row_date = date.fromtimestamp(ts).isoformat()
        rows.append(
            {
                "date": row_date,
                "open": opens[idx] if idx < len(opens) else None,
                "high": highs[idx] if idx < len(highs) else None,
                "low": lows[idx] if idx < len(lows) else None,
                "close": close_value,
                "currency": currency,
            }
        )

    if not rows:
        raise RuntimeError(f"No usable Yahoo close rows for symbol: {symbol}")

    selected = rows[-1]
    if requested_close_date:
        eligible = [row for row in rows if row["date"] <= requested_close_date]
        if eligible:
            selected = eligible[-1]

    return {
        "symbol": symbol,
        "date": selected["date"],
        "open": selected["open"],
        "high": selected["high"],
        "low": selected["low"],
        "close": float(selected["close"]),
        "currency": selected["currency"],
        "source": "yahoo_chart",
    }


def fetch_ecb_usd_per_eur(requested_close_date: str | None = None) -> dict[str, Any]:
    xml_bytes = _read_url("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml")
    root = ET.fromstring(xml_bytes)
    ns = {"gesmes": "http://www.gesmes.org/xml/2002-08-01", "def": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}

    observations: list[dict[str, Any]] = []
    for cube in root.findall(".//def:Cube[@time]", ns):
        obs_date = cube.attrib.get("time")
        if not obs_date:
            continue
        usd_rate = None
        for child in cube.findall("def:Cube", ns):
            if child.attrib.get("currency") == "USD":
                usd_rate = child.attrib.get("rate")
                break
        if usd_rate is not None:
            observations.append({"date": obs_date, "usd_per_eur": float(usd_rate)})

    if not observations:
        raise RuntimeError("ECB EUR/USD reference data was not available")

    selected = observations[-1]
    if requested_close_date:
        eligible = [row for row in observations if row["date"] <= requested_close_date]
        if eligible:
            selected = eligible[-1]

    return {
        "date": selected["date"],
        "usd_per_eur": float(selected["usd_per_eur"]),
        "source": "ecb_reference",
    }
