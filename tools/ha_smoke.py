"""Run against real Home Assistant on Linux CI, never against a user instance."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
from types import MappingProxyType
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def main() -> None:
    from aiohttp import web
    from homeassistant.components.network import async_get_adapters
    from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
    from homeassistant.core import HomeAssistant
    from homeassistant.exceptions import ServiceValidationError
    from homeassistant.helpers.storage import get_internal_store_manager
    from homeassistant.util.file import WriteError

    from custom_components.pohl_solutions_energiemanager import async_setup_entry, async_unload_entry
    from custom_components.pohl_solutions_energiemanager.config_flow import (
        PohlSolutionsConfigFlow,
        PohlSolutionsOptionsFlow,
    )
    from custom_components.pohl_solutions_energiemanager.const import BATTERY_DEFAULTS, DOMAIN
    from custom_components.pohl_solutions_energiemanager.coordinator import PohlEnergyCoordinator
    from custom_components.pohl_solutions_energiemanager.price_sources import PriceSourceLoader
    from custom_components.pohl_solutions_energiemanager.project_store import DATA_PROJECT_STORE, ProjectStore
    from custom_components.pohl_solutions_energiemanager.sensor import DESCRIPTIONS, PohlEnergySensor

    with tempfile.TemporaryDirectory() as folder:
        hass = HomeAssistant(folder)
        # HomeAssistant() alone has no ConfigEntries manager. Mirror the relevant
        # HA bootstrap prerequisites before exercising integration lifecycle and
        # persistence; retain real managers rather than a fake service container.
        hass.config_entries = ConfigEntries(hass, {})
        await get_internal_store_manager(hass).async_initialize()
        await hass.config_entries.async_initialize()
        # Normal HA bootstrap loads network before shared HTTP is used.
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
            project_flow = PohlSolutionsConfigFlow()
            project_flow.hass = hass
            form = await project_flow.async_step_user()
            assert form["type"] == "form" and form["step_id"] == "user"
            assert {key.schema for key in form["data_schema"].schema} == {"name"}
            invalid_name = await project_flow.async_step_user({"name": "   "})
            assert invalid_name["errors"] == {"name": "invalid_name"}
            project_created = await project_flow.async_step_user({"name": "  Project CI  "})
            assert project_created["type"] == "create_entry"
            assert project_created["title"] == "Project CI"
            assert project_created["data"] == {"name": "Project CI", "project_only": True}
            # Existing simulation remains available in options, never first setup.
            flow = PohlSolutionsOptionsFlow()
            flow.hass = hass
            flow.handler = entry.entry_id
            with patch.object(hass.config_entries, "async_get_known_entry", return_value=entry):
                menu = await flow.async_step_init()
                assert menu["type"] == "menu" and menu["menu_options"] == ["project", "simulation"]
                missing = await flow.async_step_simulation({})
                assert missing["errors"] == {"forecast_entity": "required_source", "soc_entity": "required_source"}
                mode_form = await flow.async_step_simulation({"forecast_entity": "sensor.pohl_test_forecast", "soc_entity": "sensor.pohl_test_soc"})
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
                assert created["data"]["project_only"] is False
                unchanged_flow = PohlSolutionsOptionsFlow()
                unchanged_flow.hass = hass
                unchanged_flow.handler = entry.entry_id
                await unchanged_flow.async_step_simulation({"forecast_entity": "sensor.pohl_test_forecast", "soc_entity": "sensor.pohl_test_soc"})
                no_details = await unchanged_flow.async_step_prices({"import_price_mode": "forecast", "export_price_mode": "forecast"})
                assert no_details["step_id"] == "battery"
                project_option = await flow.async_step_project({})
                assert project_option["data"] == {"project_only": True}
            project_entry = ConfigEntry(
                version=1, minor_version=1, domain=DOMAIN, title="Project CI",
                data=project_created["data"], options={}, source="user", unique_id=None,
                discovery_keys=MappingProxyType({}), subentries_data=(),
                state=ConfigEntryState.SETUP_IN_PROGRESS,
            )
            project_coordinator = PohlEnergyCoordinator(hass, project_entry)
            extra_coordinators.append(project_coordinator)
            project_result = await project_coordinator._async_update_data()
            assert project_result["status"] == "project_only" and not project_result["valid"]
            project_coordinator.async_set_updated_data(project_result)
            assert PohlEnergySensor(project_coordinator, project_entry, DESCRIPTIONS[0]).native_value == "project_only"

            # Run integration service lifecycle, isolating only HA platform forwarding.
            with patch.object(hass.config_entries, "async_forward_entry_setups", new=AsyncMock()), patch.object(
                hass.config_entries, "async_unload_platforms", new=AsyncMock(return_value=True),
            ):
                assert await async_setup_entry(hass, project_entry)
                try:
                    empty = await hass.services.async_call(DOMAIN, "project_status", {}, blocking=True, return_response=True)
                    assert empty["has_project"] is True
                    assert empty["summary"]["name"] == "Project CI"
                    assert all(count == 0 for count in empty["summary"]["counts"].values())
                    fixture = {
                        "format": "pohl-energy-project", "schema_version": 1,
                        "id": "ci-project", "name": "CI project", "mode": "planning_only",
                        "grids": [], "areas": [], "nodes": [], "connections": [],
                        "devices": [], "channels": [], "measurements": [], "settings": {},
                    }
                    imported = await hass.services.async_call(
                        DOMAIN, "import_project", {"project_json": json.dumps(fixture)}, blocking=True, return_response=True,
                    )
                    assert imported["has_project"] is True and imported["planning_only"] is True
                    exported = await hass.services.async_call(DOMAIN, "export_project", {}, blocking=True, return_response=True)
                    assert json.loads(exported["project_json"]) == fixture
                    await hass.data[DATA_PROJECT_STORE].async_ensure_project("Must not overwrite", "another_entry")
                    assert hass.data[DATA_PROJECT_STORE].export() == exported
                    reloaded_store = ProjectStore(hass)
                    await reloaded_store.async_load()
                    assert reloaded_store.export() == exported
                    try:
                        await hass.services.async_call(
                            DOMAIN, "import_project", {"project_json": '{"invalid":true}'}, blocking=True,
                        )
                    except ServiceValidationError:
                        pass
                    else:
                        raise AssertionError("Invalid import was accepted")
                    assert hass.data[DATA_PROJECT_STORE].export() == exported
                    altered = {**fixture, "name": "Must not become active"}
                    # HA Store itself suppresses WriteError. The integration's
                    # on-disk confirmation must still reject this candidate.
                    with patch.object(hass.data[DATA_PROJECT_STORE]._store, "_async_write_data", new=AsyncMock(side_effect=WriteError("CI simulated suppressed write failure"))):
                        try:
                            await hass.data[DATA_PROJECT_STORE].async_import(json.dumps(altered))
                        except OSError:
                            pass
                        else:
                            raise AssertionError("Suppressed Store write failure activated the project")
                    assert hass.data[DATA_PROJECT_STORE].export() == exported
                    disk_check = ProjectStore(hass)
                    await disk_check.async_load()
                    assert disk_check.export() == exported
                    # Saving must succeed before replacing active in-memory data.
                    with patch.object(hass.data[DATA_PROJECT_STORE]._store, "async_save", new=AsyncMock(side_effect=OSError("CI simulated disk failure"))):
                        try:
                            await hass.data[DATA_PROJECT_STORE].async_import(json.dumps(altered))
                        except OSError:
                            pass
                        else:
                            raise AssertionError("Disk failure was ignored")
                    assert hass.data[DATA_PROJECT_STORE].export() == exported
                finally:
                    assert await async_unload_entry(hass, project_entry)
                assert DATA_PROJECT_STORE not in hass.data
                assert not hass.services.has_service(DOMAIN, "import_project")
                assert not hass.services.has_service(DOMAIN, "export_project")
                assert not hass.services.has_service(DOMAIN, "project_status")
                assert not hass.services.has_service(DOMAIN, "replan")
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
        finally:
            for extra in extra_coordinators:
                await extra.async_shutdown()
            if coordinator is not None:
                await coordinator.async_shutdown()
            if runner is not None:
                await runner.cleanup()
            # HA owns the shared HTTP session and closes it on its close event.
            await hass.async_stop(force=True)
        print("Real HA smoke passed: project-only setup, atomic project persistence/services/unload, config flow, forecast migration, fixed/entity/HTTP prices, sensors, missing source/SOC; planning only.")


if __name__ == "__main__":
    asyncio.run(main())
