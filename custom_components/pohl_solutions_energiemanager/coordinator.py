"""Read HA entities, validate explicit forecasts and calculate a simulation."""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import BATTERY_DEFAULTS, EVENT_PLAN_UPDATED, NAME
from .core.models import BatteryConfig, ForecastSlot
from .core.optimizer import optimize
from .input_validation import finite_number, parse_forecast_rows, validate_battery_settings

_LOGGER = logging.getLogger(__name__)


class PohlEnergyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Planning only: this class deliberately has no device write path."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=NAME, config_entry=entry, update_interval=timedelta(minutes=5))
        self.entry = entry

    async def _async_update_data(self) -> dict[str, Any]:
        values = {**self.entry.data, **self.entry.options}
        source = self.hass.states.get(values["forecast_entity"])
        if source is None or source.state in ("unknown", "unavailable"):
            return self._invalid("missing_forecast", "Forecast source is missing or unavailable")
        try:
            now = datetime.now(timezone.utc)
            # Forecast data must carry freshness; stale source entities are not valid inputs.
            updated = getattr(source, "last_reported", source.last_updated).astimezone(timezone.utc)
            if now - updated > timedelta(hours=24):
                raise ValueError("Forecast source has not been updated within 24 hours")
            rows = parse_forecast_rows(source.attributes.get("slots"), now)
            soc_state = self.hass.states.get(values["soc_entity"])
            if soc_state is None or soc_state.state in ("unknown", "unavailable"):
                raise ValueError("Battery SOC source is missing or unavailable")
            soc_reported = getattr(soc_state, "last_reported", soc_state.last_updated)
            if now - soc_reported.astimezone(timezone.utc) > timedelta(minutes=30):
                raise ValueError("Battery SOC source is stale (older than 30 minutes)")
            soc = finite_number(soc_state.state, "SOC")
            params = validate_battery_settings({key: values.get(key, default) for key, default in BATTERY_DEFAULTS.items()})
            config = BatteryConfig(**params, initial_soc_pct=soc, terminal_soc_pct=soc)
            slots = [ForecastSlot(**row) for row in rows]
        except (ValueError, KeyError, TypeError) as err:
            return self._invalid("invalid_input", str(err))
        try:
            plan = await self.hass.async_add_executor_job(optimize, slots, config)
        except ValueError as err:
            return self._invalid("invalid_input", str(err))
        except Exception:  # Keep diagnostic entities available after an unexpected planner failure.
            _LOGGER.exception("Energy planning failed; no commands were issued")
            return self._invalid("planning_error", "Calculation failed; see Home Assistant logs")
        serialized = []
        for slot in plan.slots:
            row = asdict(slot)
            row["start"] = slot.start.isoformat()
            serialized.append(row)
        result = {
            "status": "ready", "valid": True, "planning_only": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_cost_eur": plan.total_cost_eur, "baseline_cost_eur": plan.baseline_cost_eur,
            "savings_eur": plan.savings_eur, "assumptions": plan.assumptions,
            "slots": serialized, "error": None,
            "source_entities": {key: values.get(key) for key in ("forecast_entity", "soc_entity", "grid_entity", "pv_entity", "load_entity")},
        }
        self.hass.bus.async_fire(EVENT_PLAN_UPDATED, {"entry_id": self.entry.entry_id, "planning_only": True, "generated_at": result["generated_at"]})
        return result

    @staticmethod
    def _invalid(status: str, error: str) -> dict[str, Any]:
        return {"status": status, "valid": False, "planning_only": True, "error": error, "slots": []}
