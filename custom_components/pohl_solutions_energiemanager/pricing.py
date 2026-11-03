"""Normalize explicit tariff sources without network access or device writes.

All public period timestamps are UTC, values are EUR/kWh. Source price is not
automatically a retail import tariff or an export remuneration contract.
"""

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
import re
from urllib.parse import urlsplit

MODES = {"forecast", "entity", "url", "fixed", "smard"}
UNIT_DIVISORS = {"eur_kwh": 1.0, "ct_kwh": 100.0, "eur_mwh": 1000.0}


@dataclass(frozen=True, slots=True)
class PricePeriod:
    start: datetime
    end: datetime
    price_eur_kwh: float


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise ValueError(f"{name} muss eine endliche Zahl sein.")
    return float(value)


def _instant(value: object, name: str) -> datetime:
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError) as err:
        raise ValueError(f"{name} benötigt einen gültigen Zeitstempel mit Zeitzone.") from err


def _unit(unit: object) -> str:
    if not isinstance(unit, str) or unit not in UNIT_DIVISORS:
        raise ValueError("Preiseinheit muss eur_kwh, ct_kwh oder eur_mwh sein.")
    return unit


def validate_price_config(config: dict) -> dict:
    """Return canonical source configuration; reject ambiguous units and values.

    An empty configuration selects forecast prices, already in EUR/kWh. SMARD
    has a known native EUR/MWh unit. Other external sources require explicit units.
    Config is copied. This function neither fetches URLs nor accesses HA entities.
    """
    if not isinstance(config, dict):
        raise ValueError("Preisquellen-Konfiguration muss ein Objekt sein.")
    mode = config.get("mode", "forecast")
    if not isinstance(mode, str) or mode not in MODES:
        raise ValueError("Unbekannte Preisquelle.")
    default_unit = "eur_mwh" if mode == "smard" else "eur_kwh"
    if mode in {"url", "entity", "fixed"} and "unit" not in config:
        raise ValueError("Für diese Preisquelle muss die Einheit ausdrücklich angegeben werden.")
    unit = _unit(config.get("unit", default_unit))
    if mode == "smard" and unit != "eur_mwh":
        raise ValueError("SMARD-Rohdaten werden in eur_mwh geliefert.")
    multiplier = _number(config.get("multiplier", 1.0), "Preisfaktor")
    adder = _number(config.get("adder_eur_kwh", 0.0), "Preisaufschlag")
    if multiplier < 0:
        raise ValueError("Preisfaktor darf nicht negativ sein.")
    entity = config.get("entity_id", config.get("entity", ""))
    url = config.get("url", "")
    if not isinstance(entity, str) or not isinstance(url, str):
        raise ValueError("Entität und URL müssen Text sein.")
    entity, url = entity.strip(), url.strip()
    if mode == "entity" and not re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", entity):
        raise ValueError("Preisquelle benötigt eine gültige Home-Assistant-Entität.")
    if mode == "url":
        try:
            parsed = urlsplit(url)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                    or parsed.username is not None or parsed.password is not None or parsed.fragment):
                raise ValueError
            _ = parsed.port  # Validate malformed or out-of-range port values.
        except ValueError as err:
            raise ValueError("Preis-URL muss eine HTTP(S)-Adresse ohne Zugangsdaten oder Fragment sein.") from err
    if mode == "fixed" and "fixed_price" not in config:
        raise ValueError("Ein fester Preis muss angegeben werden.")
    fixed = _number(config.get("fixed_price", 0.0), "Festpreis")
    return {"mode": mode, "entity_id": entity, "entity": entity, "url": url,
            "unit": unit, "fixed_price": fixed, "multiplier": multiplier,
            "adder_eur_kwh": adder}


def _validate_periods(periods: list[PricePeriod]) -> list[PricePeriod]:
    normalized = []
    for period in periods:
        if not isinstance(period, PricePeriod):
            raise ValueError("Preisdaten müssen normalisierte Preisintervalle sein.")
        start, end = _instant(period.start, "Preisbeginn"), _instant(period.end, "Preisende")
        if end <= start or end - start > timedelta(hours=24):
            raise ValueError("Preisintervalle müssen positiv und höchstens 24 Stunden lang sein.")
        normalized.append(PricePeriod(start, end, _number(period.price_eur_kwh, "Preis")))
    normalized.sort(key=lambda period: period.start)
    for previous, following in zip(normalized, normalized[1:]):
        if following.start < previous.end:
            raise ValueError("Doppelte oder überlappende Preisintervalle sind nicht erlaubt.")
    return normalized


def normalize_prices(payload: object, unit: str, smard: bool = False) -> list[PricePeriod]:
    """Parse explicit intervals or SMARD series, without filling missing prices.

    Generic JSON: [{"start": aware ISO, "end": aware ISO, "value": number}],
    alternatively duration_hours instead of end, optionally wrapped in "prices".
    Generic periods may span several quarters (e.g. an explicit hourly tariff).
    SMARD JSON: {"series": [[UTC epoch milliseconds, EUR/MWh or null], ...]}.
    Null SMARD values are absent periods, not zero-price or forward-filled values.
    """
    unit = _unit(unit)
    if smard and unit != "eur_mwh":
        raise ValueError("SMARD-Rohdaten werden in eur_mwh geliefert.")
    if isinstance(payload, dict):
        key = "series" if smard else "prices"
        if key not in payload:
            raise ValueError(f"Preisantwort benötigt das Feld {key}.")
        payload = payload[key]
    if not isinstance(payload, list):
        raise ValueError("Preisantwort muss eine Liste von Intervallen sein.")
    result = []
    seen_smard: set[datetime] = set()
    for item in payload:
        if smard:
            if not isinstance(item, (list, tuple)) or len(item) != 2:
                raise ValueError("SMARD-Datenpunkte benötigen Zeitstempel und Preis.")
            stamp = _number(item[0], "SMARD-Zeitstempel")
            if stamp != int(stamp):
                raise ValueError("SMARD-Zeitstempel muss ganze Millisekunden enthalten.")
            try:
                start = datetime.fromtimestamp(stamp / 1000, tz=timezone.utc)
            except (ValueError, OverflowError, OSError) as err:
                raise ValueError("Ungültiger SMARD-Zeitstempel.") from err
            if start.minute % 15 or start.second or start.microsecond:
                raise ValueError("SMARD-Preise müssen an Viertelstunden beginnen.")
            if start in seen_smard:
                raise ValueError("Doppelte SMARD-Zeitstempel sind nicht erlaubt.")
            seen_smard.add(start)
            if item[1] is None:
                continue
            end = start + timedelta(minutes=15)
            value = item[1]
        else:
            if not isinstance(item, dict) or "start" not in item or "value" not in item:
                raise ValueError("Preisintervalle benötigen start, value und end oder duration_hours.")
            start = _instant(item["start"], "Preisbeginn")
            if "end" in item:
                end = _instant(item["end"], "Preisende")
                if "duration_hours" in item:
                    duration = _number(item["duration_hours"], "Preisdauer")
                    if abs((end - start).total_seconds() - duration * 3600) > .001:
                        raise ValueError("Preisende und Preisdauer widersprechen sich.")
            elif "duration_hours" in item:
                duration = _number(item["duration_hours"], "Preisdauer")
                if not 0 < duration <= 24:
                    raise ValueError("Preisdauer muss positiv und höchstens 24 Stunden sein.")
                try:
                    end = start + timedelta(hours=duration)
                except OverflowError as err:
                    raise ValueError("Ungültiges Preisende.") from err
            else:
                raise ValueError("Preisintervalle benötigen end oder duration_hours.")
            value = item["value"]
        result.append(PricePeriod(start, end, _number(value, "Preis") / UNIT_DIVISORS[unit]))
    return _validate_periods(result)


def _covered_price(start: datetime, end: datetime, periods: list[PricePeriod], starts: list[datetime]) -> float:
    """Return duration-weighted price only when the entire interval is covered."""
    index = bisect_right(starts, start) - 1
    if index < 0:
        raise ValueError(f"Preisdaten fehlen ab {start.isoformat()}.")
    cursor = start
    weighted = 0.0
    while cursor < end:
        if index >= len(periods) or periods[index].start > cursor or periods[index].end <= cursor:
            raise ValueError(f"Lücke in den Preisdaten ab {cursor.isoformat()}.")
        stop = min(end, periods[index].end)
        weighted += (stop - cursor).total_seconds() * periods[index].price_eur_kwh
        cursor = stop
        index += 1
    return weighted / (end - start).total_seconds()


def apply_price_sources(
    rows: list[dict],
    import_periods: list[PricePeriod] | None,
    export_periods: list[PricePeriod] | None,
    import_config: dict,
    export_config: dict,
) -> list[dict]:
    """Copy forecast rows with independent import/export prices, never extrapolate.

    Forecast mode preserves its existing canonical EUR/kWh field unchanged.
    External and fixed sources apply unit conversion, then multiplier and the
    EUR/kWh adder exactly once. Missing prices on externally supplied sides are OK.
    Source gaps outside requested coverage are allowed. No IO is performed.
    """
    if not isinstance(rows, list):
        raise ValueError("Prognosedaten müssen eine Liste sein.")
    configs = [validate_price_config(import_config), validate_price_config(export_config)]
    sources = []
    for config, periods in zip(configs, (import_periods, export_periods)):
        normalized = _validate_periods(periods or []) if config["mode"] not in {"forecast", "fixed"} else []
        sources.append((normalized, [item.start for item in normalized]))
    result = []
    for row in rows:
        if not isinstance(row, dict) or "start" not in row:
            raise ValueError("Prognoseintervalle benötigen einen Beginn.")
        start = _instant(row["start"], "Prognosebeginn")
        duration = _number(row.get("duration_hours", .25), "Prognosedauer")
        if not 0 < duration <= 24:
            raise ValueError("Prognosedauer muss positiv und höchstens 24 Stunden sein.")
        try:
            end = start + timedelta(hours=duration)
        except OverflowError as err:
            raise ValueError("Ungültiges Prognoseende.") from err
        copied = dict(row)
        for field, config, (periods, starts) in zip(
            ("import_price_eur_kwh", "export_price_eur_kwh"), configs, sources
        ):
            if config["mode"] == "forecast":
                if field not in row:
                    raise ValueError(f"Prognose benötigt {field}, solange diese Preisquelle ausgewählt ist.")
                value = _number(row[field], field)
            else:
                if config["mode"] == "fixed":
                    value = config["fixed_price"] / UNIT_DIVISORS[config["unit"]]
                else:
                    value = _covered_price(start, end, periods, starts)
                value = value * config["multiplier"] + config["adder_eur_kwh"]
                _number(value, "Berechneter Preis")
            copied[field] = value
        result.append(copied)
    return result
