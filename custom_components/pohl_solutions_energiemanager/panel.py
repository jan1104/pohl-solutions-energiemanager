"""Native HA sidebar panel and admin-only project configuration WebSockets."""

import asyncio
from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .base_runtime import DATA_BASE_RUNTIME
from .const import DOMAIN, VERSION
from .project_store import DATA_PROJECT_STORE, ProjectConflictError

PANEL_URL = "pohl-energiemanager"
STATIC_URL = "/pohl-energy-assets"
DATA_STATIC = f"{DOMAIN}_static_registered"
DATA_WEBSOCKETS = f"{DOMAIN}_websockets_registered"
DATA_PANEL = f"{DOMAIN}_panel_registered"


async def async_setup_panel(hass: HomeAssistant) -> None:
    """Register static routes/commands once; recreate the sidebar on reload."""
    if not hass.data.get(DATA_STATIC):
        await hass.http.async_register_static_paths([
            StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "frontend"), False),
        ])
        hass.data[DATA_STATIC] = True
    if not hass.data.get(DATA_WEBSOCKETS):
        websocket_api.async_register_command(hass, ws_project_get)
        websocket_api.async_register_command(hass, ws_project_set)
        websocket_api.async_register_command(hass, ws_project_migration_preview)
        websocket_api.async_register_command(hass, ws_project_migrate)
        websocket_api.async_register_command(hass, ws_simulate_measurement)
        websocket_api.async_register_command(hass, ws_system_get)
        hass.data[DATA_WEBSOCKETS] = True
    if not hass.data.get(DATA_PANEL):
        previous = hass.data.get(frontend.DATA_PANELS, {}).get(PANEL_URL)
        try:
            await panel_custom.async_register_panel(
                hass, PANEL_URL, "pohl-energy-manager-panel",
                sidebar_title="Energiemanager", sidebar_icon="mdi:lightning-bolt",
                module_url=f"{STATIC_URL}/pohl-panel.js?v={VERSION}",
                require_admin=True, config_panel_domain=DOMAIN,
            )
        except (Exception, asyncio.CancelledError):
            current = hass.data.get(frontend.DATA_PANELS, {}).get(PANEL_URL)
            # Only remove a newly created panel whose own component/module match.
            # Never remove a pre-existing panel that caused the name conflict.
            custom = current.config.get("_panel_custom", {}) if current and current.config else {}
            if previous is None and custom.get("name") == "pohl-energy-manager-panel" and custom.get("module_url") == f"{STATIC_URL}/pohl-panel.js?v={VERSION}":
                frontend.async_remove_panel(hass, PANEL_URL)
            raise
        hass.data[DATA_PANEL] = True


def async_remove_panel(hass: HomeAssistant) -> None:
    """Keep static routes and WS handlers; both are safe across entry reloads."""
    if hass.data.pop(DATA_PANEL, False):
        frontend.async_remove_panel(hass, PANEL_URL)


def _loaded_store(hass, connection, message_id):
    if not hass.data.get(DOMAIN) or DATA_PROJECT_STORE not in hass.data:
        connection.send_error(message_id, "not_loaded", "Der Energiemanager ist nicht geladen.")
        return None
    return hass.data[DATA_PROJECT_STORE]


@websocket_api.websocket_command({vol.Required("type"): "pohl_energy/project/get"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_project_get(hass, connection, msg):
    store = _loaded_store(hass, connection, msg["id"])
    if store is not None:
        connection.send_result(msg["id"], store.snapshot())


@websocket_api.websocket_command({vol.Required("type"): "pohl_energy/system/get"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_system_get(hass, connection, msg):
    async with hass.data.setdefault(f"{DOMAIN}_setup_lock", asyncio.Lock()):
        store = _loaded_store(hass, connection, msg["id"])
        if store is None:
            return
        runtime = hass.data.get(DATA_BASE_RUNTIME)
        if runtime is None:
            connection.send_error(msg["id"], "not_loaded", "Das Grundmodul ist nicht geladen.")
            return
        connection.send_result(msg["id"], await runtime.async_system_status())


@websocket_api.websocket_command({
    vol.Required("type"): "pohl_energy/project/set",
    vol.Required("project_json"): str,
    vol.Required("expected_revision"): str,
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_project_set(hass, connection, msg):
    # A configuration save must finish before unload swaps out its Store.
    async with hass.data.setdefault(f"{DOMAIN}_setup_lock", asyncio.Lock()):
        store = _loaded_store(hass, connection, msg["id"])
        if store is None:
            return
        try:
            await store.async_import(msg["project_json"], expected_revision=msg["expected_revision"])
        except ProjectConflictError as err:
            connection.send_error(msg["id"], "conflict", str(err))
        except ValueError as err:
            connection.send_error(msg["id"], "invalid_project", str(err))
        except OSError:
            connection.send_error(msg["id"], "storage_error", "Projekt konnte nicht dauerhaft gespeichert werden.")
        else:
            connection.send_result(msg["id"], store.snapshot())


async def _async_migration_response(hass, connection, msg, *, commit):
    async with hass.data.setdefault(f"{DOMAIN}_setup_lock", asyncio.Lock()):
        store = _loaded_store(hass, connection, msg["id"])
        if store is None:
            return
        try:
            if commit:
                result = await store.async_migrate_project(msg["expected_revision"], msg["source_revision"])
            else:
                result = await store.async_migration_preview(msg["expected_revision"])
        except ProjectConflictError as err:
            connection.send_error(msg["id"], "conflict", str(err))
        except ValueError as err:
            connection.send_error(msg["id"], "invalid_project", str(err))
        except OSError:
            connection.send_error(msg["id"], "storage_error", "Projektformat konnte nicht verarbeitet werden.")
        else:
            connection.send_result(msg["id"], result)


@websocket_api.websocket_command({
    vol.Required("type"): "pohl_energy/project/migration_preview",
    vol.Required("expected_revision"): vol.Match(r"[0-9a-f]{64}\Z"),
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_project_migration_preview(hass, connection, msg):
    await _async_migration_response(hass, connection, msg, commit=False)


@websocket_api.websocket_command({
    vol.Required("type"): "pohl_energy/project/migrate",
    vol.Required("expected_revision"): vol.Match(r"[0-9a-f]{64}\Z"),
    vol.Required("source_revision"): vol.All(int, vol.Range(min=1, max=2**53 - 1)),
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_project_migrate(hass, connection, msg):
    await _async_migration_response(hass, connection, msg, commit=True)


@websocket_api.websocket_command({
    vol.Required("type"): "pohl_energy/project/simulate_measurement",
    vol.Required("expected_revision"): vol.Match(r"[0-9a-f]{64}\Z"),
    vol.Required("measurement_id"): vol.Match(r"[a-zA-Z0-9_-]{1,80}\Z"),
    vol.Required("raw_value"): vol.Any(int, float),
    vol.Required("polarity"): vol.All(int, vol.In((-1, 1))),
})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_simulate_measurement(hass, connection, msg):
    async with hass.data.setdefault(f"{DOMAIN}_setup_lock", asyncio.Lock()):
        store = _loaded_store(hass, connection, msg["id"])
        if store is None:
            return
        try:
            result = await store.async_simulate_measurement(
                msg["expected_revision"], msg["measurement_id"], msg["raw_value"], msg["polarity"],
            )
        except ProjectConflictError as err:
            connection.send_error(msg["id"], "conflict", str(err))
        except ValueError as err:
            connection.send_error(msg["id"], "invalid_project", str(err))
        except OSError:
            connection.send_error(msg["id"], "storage_error", "Gespeichertes Projekt konnte nicht gelesen werden.")
        else:
            connection.send_result(msg["id"], result)
