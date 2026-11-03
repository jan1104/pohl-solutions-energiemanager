"""Run against real Home Assistant on Linux CI, never against a user instance."""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
from types import MappingProxyType
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main() -> None:
    from aiohttp import web
    from homeassistant.components.network import async_get_adapters
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from custom_components.pohl_solutions_energiemanager.config_flow import (
        PohlSolutionsConfigFlow,
        PohlSolutionsOptionsFlow,
    )
    from custom_components.pohl_solutions_energiemanager.const import BATTERY_DEFAULTS, DOMAIN
    from custom_components.pohl_solutions_energiemanager.coordinator import PohlEnergyCoordinator
    from custom_components.pohl_solutions_energiemanager.price_sources import PriceSourceLoader
    from custom_components.pohl_solutions_energiemanager.sensor import DESCRIPTIONS, PohlEnergySensor

    with tempfile.TemporaryDirectory() as folder:
        hass = HomeAssistant(folder)
        # Normal HA bootstrap loads network before integrations use its shared
        # HTTP session. This standalone harness must initialize it explicitly.
        await async_get_adapters(hass)
        coordinator = None
        extra_coordinators = []
        runner = None
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
            mode_form = await flow.async_step_user({"name": "CI", "forecast_entity": "sensor.pohl_test_forecast", "soc_entity": "sensor.pohl_test_soc"})
            assert mode_form["step_id"] == "prices"
            details_form = await flow.async_step_prices({"import_price_mode": "fixed", "export_price_mode": "entity"})
            assert details_form["step_id"] == "price_details"
            battery_form = await flow.async_step_price_details({
                "import_price_unit": "ct_kwh", "import_fixed_price": 30.0,
                "import_price_multiplier": 1.0, "import_price_adder_eur_kwh": 0.0,
                "export_price_entity": "sensor.pohl_test_prices", "export_price_unit": "eur_mwh",
                "export_price_multiplier": 1.0, "export_price_adder_eur_kwh": 0.0,
            })
            assert battery_form["step_id"] == "battery"
            created = await flow.async_step_battery(BATTERY_DEFAULTS)
            assert created["type"] == "create_entry"
            assert created["data"]["import_price_mode"] == "fixed"
            unchanged_flow = PohlSolutionsConfigFlow()
            unchanged_flow.hass = hass
            await unchanged_flow.async_step_user({"name": "CI embedded", "forecast_entity": "sensor.pohl_test_forecast", "soc_entity": "sensor.pohl_test_soc"})
            no_details = await unchanged_flow.async_step_prices({"import_price_mode": "forecast", "export_price_mode": "forecast"})
            assert no_details["step_id"] == "battery"
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
            # External price sources must work without embedded price fields.
            external_rows = [{key: value for key, value in row.items() if "price" not in key} for row in rows]
            price_rows = [{"start": row["start"], "duration_hours": .25, "value": -20.0} for row in rows]
            hass.states.async_set("sensor.pohl_test_forecast", "ready", {"slots": external_rows})
            hass.states.async_set("sensor.pohl_test_prices", "ready", {"prices": price_rows})
            external_entry = ConfigEntry(
                version=1, minor_version=1, domain=DOMAIN, title="External CI test",
                data=created["data"], options={}, source="user", unique_id=None,
                discovery_keys=MappingProxyType({}), subentries_data=(),
            )
            external_coordinator = PohlEnergyCoordinator(hass, external_entry)
            extra_coordinators.append(external_coordinator)
            external_result = await external_coordinator._async_update_data()
            assert external_result["valid"], external_result
            assert external_result["slots"][0]["import_price_eur_kwh"] == .3
            assert external_result["slots"][0]["export_price_eur_kwh"] == -.02

            # Exercise real async HTTP against a temporary local JSON server.
            app = web.Application()
            week_start = datetime(2026, 11, 2, tzinfo=timezone.utc)
            week_0 = int(week_start.timestamp() * 1000)
            week_1 = int((week_start + timedelta(days=7)).timestamp() * 1000)
            boundary = week_start + timedelta(days=6, hours=23, minutes=45)
            boundary_stamp = int(boundary.timestamp() * 1000)
            blocks_requested = []

            async def prices_response(request):
                return web.json_response({"prices": price_rows})

            async def smard_index(request):
                return web.json_response({"timestamps": [week_0, week_1]})

            async def smard_block(request):
                stamp = int(request.match_info["stamp"])
                blocks_requested.append(stamp)
                series = ([[week_0, None], [boundary_stamp, 100.0]] if stamp == week_0
                          else [[week_1, 200.0], [week_1 + 900000, 300.0]])
                return web.json_response({"series": series})

            app.router.add_get("/prices", prices_response)
            app.router.add_get("/smard/index_quarterhour.json", smard_index)
            app.router.add_get("/smard/4169_DE_quarterhour_{stamp}.json", smard_block)
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "127.0.0.1", 0)
            await site.start()
            port = site._server.sockets[0].getsockname()[1]
            with patch("custom_components.pohl_solutions_energiemanager.price_sources.SMARD_BASE", f"http://127.0.0.1:{port}/smard"):
                loader = PriceSourceLoader(hass)
                periods = await loader._smard([
                    {"start": boundary, "duration_hours": .25},
                    {"start": boundary + timedelta(minutes=15), "duration_hours": .25},
                    {"start": boundary + timedelta(minutes=30), "duration_hours": .25},
                ])
                assert blocks_requested == [week_0, week_1]
                assert [period.price_eur_kwh for period in periods] == [.1, .2, .3]
            http_data = {**created["data"], "import_price_mode": "url",
                         "import_price_url": f"http://127.0.0.1:{port}/prices",
                         "import_price_unit": "eur_mwh", "export_price_mode": "fixed",
                         "export_fixed_price": 5.0, "export_price_unit": "ct_kwh"}
            http_entry = ConfigEntry(
                version=1, minor_version=1, domain=DOMAIN, title="HTTP CI test",
                data=http_data, options={}, source="user", unique_id=None,
                discovery_keys=MappingProxyType({}), subentries_data=(),
            )
            http_coordinator = PohlEnergyCoordinator(hass, http_entry)
            extra_coordinators.append(http_coordinator)
            http_result = await http_coordinator._async_update_data()
            assert http_result["valid"], http_result
            assert http_result["slots"][0]["import_price_eur_kwh"] == -.02
            assert http_result["slots"][0]["export_price_eur_kwh"] == .05
            # No stale price data or forecast fallback after a selected source fails.
            hass.states.async_set("sensor.pohl_test_prices", "unavailable")
            failed_price = await external_coordinator._async_update_data()
            assert not failed_price["valid"] and failed_price["slots"] == []
            hass.states.async_set("sensor.pohl_test_forecast", "ready", {"slots": rows})
            hass.states.async_set("sensor.pohl_test_soc", "unavailable")
            invalid = await coordinator._async_update_data()
            assert not invalid["valid"] and invalid["slots"] == []
            assert "SOC" in invalid["error"], invalid
            print("Real HA smoke passed: config flow, forecast migration, fixed/entity/HTTP prices, sensors, missing source/SOC; planning only.")
        finally:
            for extra in extra_coordinators:
                await extra.async_shutdown()
            if coordinator is not None:
                await coordinator.async_shutdown()
            if runner is not None:
                await runner.cleanup()
                await async_get_clientsession(hass).close()
            await hass.async_stop()


if __name__ == "__main__":
    asyncio.run(main())
