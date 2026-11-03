"""Bounded async price fetching; no device writes or secret-bearing URLs."""

import asyncio
from bisect import bisect_right
from datetime import timedelta
import json
from typing import Any

from aiohttp import ClientError, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .pricing import normalize_prices, validate_price_config

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
SMARD_BASE = "https://www.smard.de/app/chart_data/4169/DE"


def price_config_from_values(values: dict[str, Any], side: str) -> dict[str, Any]:
    """Default old config entries to their existing embedded forecast prices."""
    mode = values.get(f"{side}_price_mode", "forecast")
    config = {
        "mode": mode,
        "entity": values.get(f"{side}_price_entity", ""),
        "url": values.get(f"{side}_price_url", ""),
        "unit": ("eur_mwh" if mode == "smard" else "eur_kwh" if mode == "forecast"
                 else values.get(f"{side}_price_unit", "eur_kwh")),
        "fixed_price": values.get(f"{side}_fixed_price", 0.0),
        "multiplier": 1.0 if mode == "forecast" else values.get(f"{side}_price_multiplier", 1.0),
        "adder_eur_kwh": 0.0 if mode == "forecast" else values.get(f"{side}_price_adder_eur_kwh", 0.0),
    }
    return validate_price_config(config)


class PriceSourceLoader:
    """One refresh-local loader deduplicates HTTP requests shared by both tariffs."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._payloads: dict[str, Any] = {}

    async def _json(self, url: str) -> Any:
        if url in self._payloads:
            return self._payloads[url]
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(url, timeout=ClientTimeout(total=15), allow_redirects=False) as response:
                if not 200 <= response.status < 300:
                    raise ValueError(f"Price source returned HTTP {response.status}")
                if response.content_length and response.content_length > MAX_RESPONSE_BYTES:
                    raise ValueError("Price response exceeds the size limit")
                body = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    body.extend(chunk)
                    if len(body) > MAX_RESPONSE_BYTES:
                        raise ValueError("Price response exceeds the size limit")
                payload = json.loads(body.decode("utf-8-sig"))
        except (ClientError, asyncio.TimeoutError, UnicodeError, json.JSONDecodeError) as err:
            # Do not expose full URLs, query strings or server bodies in diagnostics.
            raise ValueError("Price source is unavailable or did not return valid JSON") from err
        self._payloads[url] = payload
        return payload

    async def periods(self, config: dict[str, Any], rows: list[dict[str, Any]], now):
        """Return normalized external periods; forecast/fixed need no fetch."""
        mode = config["mode"]
        if mode in ("forecast", "fixed"):
            return None
        if mode == "entity":
            entity_id = config.get("entity_id") or config.get("entity")
            state = self.hass.states.get(entity_id)
            if state is None or state.state in ("unknown", "unavailable"):
                raise ValueError("Price entity is missing or unavailable")
            reported = getattr(state, "last_reported", state.last_updated)
            if now - reported > timedelta(hours=24):
                raise ValueError("Price entity is stale (older than 24 hours)")
            return normalize_prices(state.attributes.get("prices"), config["unit"])
        if mode == "url":
            return normalize_prices(await self._json(config["url"]), config["unit"])
        if mode == "smard":
            return await self._smard(rows)
        raise ValueError("Unknown price source mode")

    async def _smard(self, rows: list[dict[str, Any]]):
        """Fetch all weekly blocks intersecting the actual requested horizon."""
        index = await self._json(f"{SMARD_BASE}/index_quarterhour.json")
        timestamps = index.get("timestamps") if isinstance(index, dict) else None
        if not isinstance(timestamps, list) or not timestamps:
            raise ValueError("SMARD did not return a block index")
        if any(isinstance(t, bool) or not isinstance(t, int) or t < 0 for t in timestamps):
            raise ValueError("Invalid SMARD block timestamp")
        timestamps = sorted(set(timestamps))
        start_ms = int(rows[0]["start"].timestamp() * 1000)
        end = rows[-1]["start"] + timedelta(hours=rows[-1]["duration_hours"])
        end_ms = int(end.timestamp() * 1000)
        first = bisect_right(timestamps, start_ms) - 1
        if first < 0:
            raise ValueError("SMARD does not cover the requested start")
        selected = timestamps[first:bisect_right(timestamps, end_ms - 1)]
        if not selected or len(selected) > 4:
            raise ValueError("Unsupported SMARD horizon")
        series: dict[int, Any] = {}
        for stamp in selected:
            payload = await self._json(f"{SMARD_BASE}/4169_DE_quarterhour_{stamp}.json")
            block = payload.get("series") if isinstance(payload, dict) else None
            if not isinstance(block, list):
                raise ValueError("SMARD did not return a quarter-hour series")
            for item in block:
                if not isinstance(item, list) or len(item) != 2:
                    raise ValueError("Invalid SMARD series item")
                timestamp, value = item
                if isinstance(timestamp, bool) or not isinstance(timestamp, int):
                    raise ValueError("Invalid SMARD series timestamp")
                if timestamp in series and series[timestamp] != value:
                    raise ValueError("Conflicting SMARD prices")
                series[timestamp] = value
        # Null values remain missing. The pure pricing layer checks complete coverage.
        return normalize_prices({"series": [[t, v] for t, v in sorted(series.items())]}, "eur_mwh", smard=True)
