"""Run against real Home Assistant on Linux CI, never against a user instance."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
from types import MappingProxyType

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main() -> None:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from custom_components.pohl_solutions_energiemanager.config_flow import (
        PohlSolutionsConfigFlow,
        PohlSolutionsOptionsFlow,
    )
    from custom_components.pohl_solutions_energiemanager.const import DOMAIN
    from custom_components.pohl_solutions_energiemanager.coordinator import PohlEnergyCoordinator
    from custom_components.pohl_solutions_energiemanager.sensor import DESCRIPTIONS, PohlEnergySensor

    with tempfile.TemporaryDirectory() as folder:
        hass = HomeAssistant(folder)
        coordinator = None
        try:
            now = datetime.now(timezone.utc)
            start = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)
            rows = [{
                "start": (start + timedelta(minutes=15 * i)).isoformat(),
                "duration_hours": .25, "pv_kw": 80.0 if i < 8 else 0.0,
                "load_kw": 20.0, "import_price_eur_kwh": .3,
                "export_price_eur_kwh": .05,
            } for i in range(16)]
            hass.states.async_set("sensor.pohl_test_forecast", "ready", {"slots": rows})
            hass.states.async_set("sensor.pohl_test_soc", "50", {"unit_of_measurement": "%"})
            entry = ConfigEntry(
                version=1, minor_version=1, domain=DOMAIN, title="CI test only",
                data={"forecast_entity": "sensor.pohl_test_forecast",
                      "soc_entity": "sensor.pohl_test_soc"},
                options={}, source="user", unique_id=None,
                discovery_keys=MappingProxyType({}), subentries_data=(),
            )
            flow = PohlSolutionsConfigFlow()
            flow.hass = hass
            form = await flow.async_step_user()
            assert form["type"] == "form" and form["step_id"] == "user"
            assert issubclass(PohlSolutionsOptionsFlow, object)
            coordinator = PohlEnergyCoordinator(hass, entry)
            result = await coordinator._async_update_data()
            assert result["valid"], result
            assert result["planning_only"] is True
            assert len(result["slots"]) == 16
            coordinator.async_set_updated_data(result)
            sensors = [PohlEnergySensor(coordinator, entry, desc) for desc in DESCRIPTIONS]
            assert sensors[0].native_value == "ready"
            assert sensors[1].native_value == 16
            assert isinstance(sensors[2].native_value, (int, float))
            hass.states.async_set("sensor.pohl_test_soc", "unavailable")
            invalid = await coordinator._async_update_data()
            assert not invalid["valid"] and invalid["slots"] == []
            print("Real Home Assistant smoke passed: imports, config form, coordinator, sensors, missing input.")
        finally:
            if coordinator is not None:
                await coordinator.async_shutdown()
            await hass.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
