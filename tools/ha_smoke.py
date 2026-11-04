"""Run against real Home Assistant on Linux CI, never against a user instance."""

import asyncio
from datetime import datetime, timedelta, timezone
import json
import logging
import sqlite3
from pathlib import Path
import sys
import tempfile
from types import MappingProxyType
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def sqlite_migration_checks(hass):
    """Use real HA executor and real SQLite, isolated from the integration project."""
    from threading import Event

    from custom_components.pohl_solutions_energiemanager.base_runtime import BaseRuntime
    from custom_components.pohl_solutions_energiemanager.const import DOMAIN
    from custom_components.pohl_solutions_energiemanager.core.storage import ModuleStorage
    from custom_components.pohl_solutions_energiemanager.project_store import ProjectConflictError, ProjectStore

    fixture = {"format": "pohl-energy-project", "schema_version": 1,
               "id": "migration-fixture", "name": "Legacy fixture", "mode": "planning_only",
               "grids": [], "areas": [], "nodes": [], "connections": [],
               "devices": [], "channels": [], "measurements": [], "settings": {}}
    envelope = {"version": 1, "minor_version": 1, "key": f"{DOMAIN}.project", "data": fixture}
    with tempfile.TemporaryDirectory() as isolated:
        root = Path(isolated)
        # Only the config path is isolated; persistence and HA's executor are real.
        with patch.object(hass.config, "path", side_effect=lambda *parts: str(root.joinpath(*parts))):
            legacy = root / ".storage" / f"{DOMAIN}.project"
            legacy.parent.mkdir()
            raw = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
            legacy.write_bytes(raw)
            with patch.object(ModuleStorage, "put_many", side_effect=sqlite3.OperationalError("CI disk full during migration")):
                try:
                    await ProjectStore(hass).async_load()
                except OSError:
                    pass
                else:
                    raise AssertionError("Failed migration was silently accepted")
            assert legacy.read_bytes() == raw
            first = ProjectStore(hass)
            await first.async_load()
            assert json.loads(first.export()["project_json"]) == fixture
            assert (await first.async_storage_health())["migration_status"] == "migrated_legacy"
            assert legacy.read_bytes() == raw
            other = ProjectStore(hass)
            await other.async_load()
            assert other.snapshot() == first.snapshot()
            # Existing SQLite is authoritative; a later damaged backup is not imported.
            legacy.write_bytes(b"intentionally damaged CI backup")
            reopened = ProjectStore(hass)
            await reopened.async_load()
            assert reopened.snapshot() == first.snapshot()
            changed = {**fixture, "name": "New SQLite revision"}
            old_sha = first.revision
            await first.async_import(json.dumps(changed), expected_revision=old_sha)
            try:
                await other.async_import(json.dumps(fixture), expected_revision=old_sha)
            except ProjectConflictError:
                pass
            else:
                raise AssertionError("Competing SQLite store bypassed CAS")
            assert other.snapshot() == first.snapshot()
            # Cancellation must drain the commit and update the local revision.
            started, release = Event(), Event()
            original_commit = first._sync_commit

            def delayed_commit(*args):
                started.set()
                if not release.wait(5):
                    raise OSError("CI release timeout")
                return original_commit(*args)

            cancelled_project = {**changed, "name": "Durable cancelled write"}
            with patch.object(first, "_sync_commit", side_effect=delayed_commit):
                task = asyncio.create_task(first.async_import(json.dumps(cancelled_project), expected_revision=first.revision))
                assert await hass.async_add_executor_job(started.wait, 5)
                task.cancel()
                await asyncio.sleep(0)
                assert not task.done()
                release.set()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                else:
                    raise AssertionError("Cancellation was swallowed")
            after_cancel = ProjectStore(hass)
            await after_cancel.async_load()
            assert after_cancel.snapshot() == first.snapshot()
            assert json.loads(first.export()["project_json"])["name"] == "Durable cancelled write"
            runtime = BaseRuntime(first)
            await runtime.async_start()
            assert all(m["status"] == "ready" for m in (await runtime.async_system_status())["modules"])
            with patch.object(first, "async_storage_health", new=AsyncMock(side_effect=OSError("CI database unavailable"))):
                unhealthy = await runtime.async_system_status()
                states = {m["id"]: m["status"] for m in unhealthy["modules"]}
                assert states == {"core": "ready", "storage": "failed", "project": "blocked"}
                assert unhealthy["database"]["project_persisted"] is False
            assert all(m["status"] == "ready" for m in (await runtime.async_system_status())["modules"])
            await runtime.async_stop()
    # Invalid legacy input must never become an empty successful migration.
    bad_payloads = [b"{broken", b'{"version":1,"version":1,"data":{}}',
                    json.dumps({**envelope, "version": 2}).encode(),
                    json.dumps({**envelope, "minor_version": 2}).encode(),
                    json.dumps({**envelope, "key": "foreign.project"}).encode(),
                    json.dumps({**envelope, "data": {**fixture, "settings": {"x": float("nan")}}}).encode()]
    for raw in bad_payloads:
        with tempfile.TemporaryDirectory() as isolated:
            root = Path(isolated)
            with patch.object(hass.config, "path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                legacy = root / ".storage" / f"{DOMAIN}.project"
                legacy.parent.mkdir()
                legacy.write_bytes(raw)
                store = ProjectStore(hass)
                try:
                    await store.async_load()
                except ValueError:
                    pass
                else:
                    raise AssertionError("Invalid legacy storage was silently replaced")
                assert legacy.read_bytes() == raw
                assert store.export()["project_json"] is None
    # HA's pretty indentation must not reject an otherwise valid large project.
    with tempfile.TemporaryDirectory() as isolated:
        root = Path(isolated)
        with patch.object(hass.config, "path", side_effect=lambda *parts: str(root.joinpath(*parts))):
            legacy = root / ".storage" / f"{DOMAIN}.project"
            legacy.parent.mkdir()
            large = {**fixture, "settings": {"items": ["x" * 25] * 60000}}
            pretty = json.dumps({**envelope, "data": large}, indent=2).encode()
            assert len(pretty) > 2 * 1024 * 1024 + 65536
            legacy.write_bytes(pretty)
            store = ProjectStore(hass)
            await store.async_load()
            assert json.loads(store.export()["project_json"]) == large
            assert legacy.read_bytes() == pretty


async def main() -> None:
    from aiohttp import web
    from homeassistant.auth import auth_manager_from_config
    from homeassistant.components import frontend, panel_custom
    from homeassistant.components.network import async_get_adapters
    from homeassistant.components.websocket_api.connection import ActiveConnection
    from homeassistant.components.websocket_api.http import WebSocketAdapter
    from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
    from homeassistant.core import Context, HomeAssistant
    from homeassistant.exceptions import ServiceValidationError
    from homeassistant.helpers import device_registry, entity_registry
    from homeassistant.helpers.storage import get_internal_store_manager

    from custom_components.pohl_solutions_energiemanager import async_setup_entry, async_unload_entry
    from custom_components.pohl_solutions_energiemanager.config_flow import (
        PohlSolutionsConfigFlow,
        PohlSolutionsOptionsFlow,
    )
    from custom_components.pohl_solutions_energiemanager.base_runtime import DATA_BASE_RUNTIME
    from custom_components.pohl_solutions_energiemanager.const import BATTERY_DEFAULTS, DOMAIN, VERSION
    from custom_components.pohl_solutions_energiemanager.coordinator import PohlEnergyCoordinator
    from custom_components.pohl_solutions_energiemanager.price_sources import PriceSourceLoader
    from custom_components.pohl_solutions_energiemanager.panel import PANEL_URL
    from custom_components.pohl_solutions_energiemanager.project_store import DATA_PROJECT_STORE, ProjectStore
    from custom_components.pohl_solutions_energiemanager.sensor import DESCRIPTIONS, PohlEnergySensor
    from custom_components.pohl_solutions_energiemanager.sensor import async_setup_entry as async_setup_sensors

    with tempfile.TemporaryDirectory() as folder:
        hass = HomeAssistant(folder)
        # HomeAssistant() alone has no ConfigEntries manager. Mirror the relevant
        # HA bootstrap prerequisites before exercising integration lifecycle and
        # persistence; retain real managers rather than a fake service container.
        hass.config_entries = ConfigEntries(hass, {})
        await get_internal_store_manager(hass).async_initialize()
        await hass.config_entries.async_initialize()
        await device_registry.async_load(hass)
        await entity_registry.async_load(hass)
        hass.auth = await auth_manager_from_config(hass, [], [])
        admin = await hass.auth.async_create_user("CI admin")
        non_admin = await hass.auth.async_create_user("CI non-admin")
        assert admin.is_admin and not non_admin.is_admin

        class StaticHTTPHarness:
            """Only static HTTP registration is isolated; HA panel/WS stay real."""

            def __init__(self):
                self.paths = []

            async def async_register_static_paths(self, configs):
                self.paths.extend(configs)

        hass.http = static_http = StaticHTTPHarness()

        async def ws_client(user):
            queue = asyncio.Queue()
            token = await hass.auth.async_create_refresh_token(user, client_id="https://ci.invalid")
            connection = ActiveConnection(
                WebSocketAdapter(logging.getLogger("pohl.ha_smoke.ws"), {"connid": user.id}),
                hass, queue.put_nowait, user, token,
            )

            async def request(command, **kwargs):
                connection.async_handle({"id": connection.last_id + 1, "type": command, **kwargs})
                response = await asyncio.wait_for(queue.get(), timeout=5)
                return json.loads(response) if isinstance(response, (str, bytes)) else response

            return request
        # Normal HA bootstrap loads network before shared HTTP is used.
        await async_get_adapters(hass)
        coordinator = None
        extra_coordinators = []
        runner = None
        try:
            await sqlite_migration_checks(hass)
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
            # Register the fixture with the real manager before creating legacy
            # entity-registry rows; lifecycle calls remain explicit below.
            with patch.object(hass.config_entries, "async_setup", new=AsyncMock(return_value=True)):
                await hass.config_entries.async_add(project_entry)
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
                with patch.object(hass.config_entries, "async_forward_entry_setups", new=AsyncMock(side_effect=asyncio.CancelledError)):
                    try:
                        await async_setup_entry(hass, project_entry)
                    except asyncio.CancelledError:
                        pass
                    else:
                        raise AssertionError("Setup cancellation was swallowed")
                assert DATA_PROJECT_STORE not in hass.data and DOMAIN not in hass.data
                assert PANEL_URL not in hass.data.get(frontend.DATA_PANELS, {})
                original_register_panel = panel_custom.async_register_panel

                async def partially_register_then_fail(*args, **kwargs):
                    await original_register_panel(*args, **kwargs)
                    raise RuntimeError("CI partial panel registration failure")

                with patch.object(panel_custom, "async_register_panel", new=partially_register_then_fail):
                    try:
                        await async_setup_entry(hass, project_entry)
                    except RuntimeError:
                        pass
                    else:
                        raise AssertionError("Partial panel registration failure was swallowed")
                assert DATA_PROJECT_STORE not in hass.data and DOMAIN not in hass.data
                assert PANEL_URL not in hass.data.get(frontend.DATA_PANELS, {})
                # A conflicting real registry entry forces panel registration
                # failure. Cleanup must preserve that foreign panel and remove
                # this integration's partially created runtime resources.
                frontend.async_register_built_in_panel(
                    hass, component_name="custom", frontend_url_path=PANEL_URL,
                    sidebar_title="Existing foreign panel",
                )
                try:
                    await async_setup_entry(hass, project_entry)
                except ValueError:
                    pass
                else:
                    raise AssertionError("Conflicting panel registration was accepted")
                assert frontend.DATA_PANELS in hass.data
                assert hass.data[frontend.DATA_PANELS][PANEL_URL].sidebar_title == "Existing foreign panel"
                assert DATA_PROJECT_STORE not in hass.data and DOMAIN not in hass.data
                assert not hass.services.has_service(DOMAIN, "import_project")
                admin_ws = await ws_client(admin)
                non_admin_ws = await ws_client(non_admin)
                before_loaded = await admin_ws("pohl_energy/project/get")
                assert before_loaded["error"]["code"] == "not_loaded"
                frontend.async_remove_panel(hass, PANEL_URL)
                assert await async_setup_entry(hass, project_entry)
                try:
                    panel = hass.data[frontend.DATA_PANELS][PANEL_URL]
                    assert panel.sidebar_title == "Energiemanager" and panel.require_admin is True
                    assert panel.config["_panel_custom"]["name"] == "pohl-energy-manager-panel"
                    assert panel.config["_panel_custom"]["module_url"].startswith("/pohl-energy-assets/pohl-panel.js?v=")
                    assert len(static_http.paths) == 1
                    registry = entity_registry.async_get(hass)
                    legacy_rows = {}
                    for description, disabled_by in zip(
                        DESCRIPTIONS[1:],
                        (None, entity_registry.RegistryEntryDisabler.USER,
                         entity_registry.RegistryEntryDisabler.DEVICE,
                         entity_registry.RegistryEntryDisabler.INTEGRATION),
                        strict=True,
                    ):
                        registered = registry.async_get_or_create(
                            "sensor", DOMAIN, f"{project_entry.entry_id}_{description.key}",
                            config_entry=project_entry, suggested_object_id=f"legacy_{description.key}",
                            disabled_by=disabled_by,
                        )
                        registry.async_update_entity(registered.entity_id, name=f"My {description.key}")
                        legacy_rows[description.key] = registered.entity_id
                    sensor_entities = []
                    await async_setup_sensors(hass, project_entry, lambda entities: sensor_entities.extend(entities))
                    assert len(sensor_entities) == 1 and sensor_entities[0].entity_description.key == "status"
                    assert registry.async_get(legacy_rows["schedule"]).disabled_by == entity_registry.RegistryEntryDisabler.INTEGRATION
                    assert registry.async_get(legacy_rows["current_power"]).disabled_by == entity_registry.RegistryEntryDisabler.USER
                    assert registry.async_get(legacy_rows["next_power"]).disabled_by == entity_registry.RegistryEntryDisabler.DEVICE
                    assert registry.async_get(legacy_rows["savings_eur"]).disabled_by == entity_registry.RegistryEntryDisabler.INTEGRATION
                    simulation_entry = ConfigEntry(
                        version=1, minor_version=1, domain=DOMAIN, title="Existing simulation",
                        entry_id=project_entry.entry_id, data={"project_only": False},
                        options={}, source="user", unique_id=None,
                        discovery_keys=MappingProxyType({}), subentries_data=(),
                    )
                    simulation_entities = []
                    await async_setup_sensors(hass, simulation_entry, lambda entities: simulation_entities.extend(entities))
                    assert len(simulation_entities) == len(DESCRIPTIONS)
                    assert registry.async_get(legacy_rows["schedule"]).disabled_by is None
                    assert registry.async_get(legacy_rows["savings_eur"]).disabled_by is None
                    assert registry.async_get(legacy_rows["current_power"]).disabled_by == entity_registry.RegistryEntryDisabler.USER
                    assert registry.async_get(legacy_rows["next_power"]).disabled_by == entity_registry.RegistryEntryDisabler.DEVICE
                    for key, entity_id in legacy_rows.items():
                        assert registry.async_get(entity_id).name == f"My {key}"
                        assert registry.async_get_entity_id("sensor", DOMAIN, f"{project_entry.entry_id}_{key}") == entity_id
                    await async_setup_sensors(hass, project_entry, lambda entities: list(entities))
                    assert registry.async_get(legacy_rows["schedule"]).disabled_by == entity_registry.RegistryEntryDisabler.INTEGRATION
                    for command, args in (
                        ("pohl_energy/system/get", {}),
                        ("pohl_energy/project/get", {}),
                        ("pohl_energy/project/set", {"project_json": "{}", "expected_revision": "irrelevant"}),
                    ):
                        denied = await non_admin_ws(command, **args)
                        assert denied["error"]["code"] == "unauthorized", denied
                    for service, args in (("export_project", {}), ("project_status", {}), ("import_project", {"project_json": "{}"})):
                        try:
                            await hass.services.async_call(
                                DOMAIN, service, args, blocking=True, return_response=True,
                                context=Context(user_id=non_admin.id),
                            )
                        except ServiceValidationError:
                            pass
                        else:
                            raise AssertionError(f"Non-admin accessed {service}")
                    system = (await admin_ws("pohl_energy/system/get"))["result"]
                    assert system["product_version"] == VERSION and system["planning_only"] is True
                    assert system["database"]["backend"] == "sqlite" and system["database"]["project_persisted"] is True
                    assert {module["id"] for module in system["modules"]} == {"core", "storage", "project"}
                    assert all(module["version"] == "0.1.0" for module in system["modules"])
                    assert all(module["status"] == "ready" for module in system["modules"])
                    assert DATA_BASE_RUNTIME in hass.data
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
                    snapshot = (await admin_ws("pohl_energy/project/get"))["result"]
                    assert snapshot["project_json"] == exported["project_json"]
                    assert snapshot["revision"] == exported["revision"] and snapshot["planning_only"] is True
                    changed = {**fixture, "name": "Changed through native HA panel"}
                    saved = await admin_ws(
                        "pohl_energy/project/set", project_json=json.dumps(changed), expected_revision=snapshot["revision"],
                    )
                    assert saved["success"] and saved["result"]["revision"] != snapshot["revision"]
                    stale = await admin_ws(
                        "pohl_energy/project/set", project_json=json.dumps(fixture), expected_revision=snapshot["revision"],
                    )
                    assert stale["error"]["code"] == "conflict"
                    invalid_ws = await admin_ws(
                        "pohl_energy/project/set", project_json="{}", expected_revision=saved["result"]["revision"],
                    )
                    assert invalid_ws["error"]["code"] == "invalid_project"
                    assert (await admin_ws("pohl_energy/project/get"))["result"] == saved["result"]
                    restored = await admin_ws(
                        "pohl_energy/project/set", project_json=json.dumps(fixture), expected_revision=saved["result"]["revision"],
                    )
                    assert restored["success"] and restored["result"]["revision"] == exported["revision"]
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
                    # SQLite errors must preserve the previously active project.
                    with patch.object(hass.data[DATA_PROJECT_STORE], "_sync_commit", side_effect=sqlite3.OperationalError("CI simulated database write failure")):
                        try:
                            await hass.data[DATA_PROJECT_STORE].async_import(json.dumps(altered))
                        except OSError:
                            pass
                        else:
                            raise AssertionError("SQLite write failure was ignored")
                    assert hass.data[DATA_PROJECT_STORE].export() == exported
                    disk_check = ProjectStore(hass)
                    await disk_check.async_load()
                    assert disk_check.export() == exported
                    # Read-back must confirm a successful transaction before activation.
                    with patch.object(hass.data[DATA_PROJECT_STORE], "_sync_commit", side_effect=OSError("CI simulated verification failure")):
                        try:
                            await hass.data[DATA_PROJECT_STORE].async_import(json.dumps(altered))
                        except OSError:
                            pass
                        else:
                            raise AssertionError("Verification failure was ignored")
                    assert hass.data[DATA_PROJECT_STORE].export() == exported
                    # An additional entry shares the same panel and project.
                    other_entry = ConfigEntry(
                        version=1, minor_version=1, domain=DOMAIN, title="Other CI entry",
                        data={"project_only": True}, options={}, source="user", unique_id=None,
                        discovery_keys=MappingProxyType({}), subentries_data=(),
                        state=ConfigEntryState.SETUP_IN_PROGRESS,
                    )
                    assert await async_setup_entry(hass, other_entry)
                    assert hass.data[DATA_PROJECT_STORE].export() == exported
                    assert await async_unload_entry(hass, other_entry)
                    assert PANEL_URL in hass.data[frontend.DATA_PANELS]
                finally:
                    assert await async_unload_entry(hass, project_entry)
                assert DATA_PROJECT_STORE not in hass.data
                assert DATA_BASE_RUNTIME not in hass.data
                assert not hass.services.has_service(DOMAIN, "import_project")
                assert not hass.services.has_service(DOMAIN, "export_project")
                assert not hass.services.has_service(DOMAIN, "project_status")
                assert not hass.services.has_service(DOMAIN, "replan")
                assert PANEL_URL not in hass.data[frontend.DATA_PANELS]
                unloaded_system = await admin_ws("pohl_energy/system/get")
                assert unloaded_system["error"]["code"] == "not_loaded"
                assert DATA_BASE_RUNTIME not in hass.data
                unloaded = await admin_ws("pohl_energy/project/get")
                assert unloaded["error"]["code"] == "not_loaded"
                unloaded_set = await admin_ws(
                    "pohl_energy/project/set", project_json="{}", expected_revision="unused",
                )
                assert unloaded_set["error"]["code"] == "not_loaded"
                assert await async_setup_entry(hass, project_entry)
                try:
                    assert len(static_http.paths) == 1
                    after_reload = (await admin_ws("pohl_energy/project/get"))["result"]
                    assert after_reload["project_json"] == exported["project_json"]
                    assert after_reload["revision"] == exported["revision"]
                finally:
                    assert await async_unload_entry(hass, project_entry)
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
