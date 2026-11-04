"""Pohl Solutions Energiemanager: local, planning-only Home Assistant integration."""

import asyncio
import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .base_runtime import DATA_BASE_RUNTIME, BaseRuntime
from .const import DOMAIN, SERVICE_REPLAN
from .coordinator import PohlEnergyCoordinator
from .panel import async_remove_panel, async_setup_panel
from .project_store import DATA_PROJECT_STORE, ProjectStore

PLATFORMS = [Platform.SENSOR]
DATA_SETUP_LOCK = f"{DOMAIN}_setup_lock"
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Serialize resource ownership and roll back a partially failed setup."""
    async with hass.data.setdefault(DATA_SETUP_LOCK, asyncio.Lock()):
        try:
            return await _async_setup_entry(hass, entry)
        except (Exception, asyncio.CancelledError):
            coordinator = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
            try:
                async with asyncio.timeout(10):
                    if coordinator is not None:
                        await coordinator.async_shutdown()
                        await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
            except (Exception, asyncio.CancelledError):
                _LOGGER.exception("Could not fully unload partially configured platforms")
            finally:
                if not hass.data.get(DOMAIN):
                    try:
                        await _async_remove_shared_resources(hass)
                    except Exception:
                        _LOGGER.exception("Could not fully remove partial setup resources")
            raise


async def _async_remove_shared_resources(hass: HomeAssistant) -> None:
    runtime = hass.data.pop(DATA_BASE_RUNTIME, None)
    if runtime is not None:
        await runtime.async_stop()
    async_remove_panel(hass)
    for service in (SERVICE_REPLAN, "import_project", "export_project", "project_status"):
        hass.services.async_remove(DOMAIN, service)
    hass.data.pop(DATA_PROJECT_STORE, None)
    hass.data.pop(DOMAIN, None)


async def _async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up diagnostics even when forecast data has not arrived yet."""
    if DATA_PROJECT_STORE not in hass.data:
        hass.data[DATA_PROJECT_STORE] = ProjectStore(hass)
    await hass.data[DATA_PROJECT_STORE].async_load()
    await hass.data[DATA_PROJECT_STORE].async_ensure_project(entry.title, entry.entry_id)
    if DATA_BASE_RUNTIME not in hass.data:
        runtime = BaseRuntime(hass.data[DATA_PROJECT_STORE])
        hass.data[DATA_BASE_RUNTIME] = runtime
        await runtime.async_start()
    coordinator = PohlEnergyCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await async_setup_panel(hass)

    if not hass.services.has_service(DOMAIN, SERVICE_REPLAN):
        async def async_replan(call: ServiceCall) -> None:
            selected = hass.data.get(DOMAIN, {}).get(call.data["entry_id"])
            if selected is None:
                raise ServiceValidationError("Unknown or unloaded Pohl Solutions entry_id")
            await selected.async_request_refresh()

        hass.services.async_register(DOMAIN, SERVICE_REPLAN, async_replan, schema=vol.Schema({vol.Required("entry_id"): str}))

        async def async_import_project(call: ServiceCall):
            await _async_require_service_admin(hass, call)
            async with hass.data[DATA_SETUP_LOCK]:
                store = _service_project_store(hass)
                try:
                    return await store.async_import(call.data["project_json"])
                except ValueError as err:
                    raise ServiceValidationError(str(err)) from err
                except OSError as err:
                    raise HomeAssistantError("Project was not activated because persistent storage failed") from err

        async def async_export_project(call: ServiceCall):
            await _async_require_service_admin(hass, call)
            return _service_project_store(hass).export()

        async def async_project_status(call: ServiceCall):
            await _async_require_service_admin(hass, call)
            return _service_project_store(hass).status()

        hass.services.async_register(
            DOMAIN, "import_project", async_import_project,
            schema=vol.Schema({vol.Required("project_json"): str}),
            supports_response=SupportsResponse.OPTIONAL,
        )
        for service, handler in (("export_project", async_export_project), ("project_status", async_project_status)):
            hass.services.async_register(
                DOMAIN, service, handler, schema=vol.Schema({}), supports_response=SupportsResponse.ONLY,
            )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload all entities and stop the coordinator's scheduled polling."""
    async with hass.data.setdefault(DATA_SETUP_LOCK, asyncio.Lock()):
        if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
            return False
        coordinator = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if coordinator is not None:
            await coordinator.async_shutdown()
        if not hass.data.get(DOMAIN):
            await _async_remove_shared_resources(hass)
        return True


async def _async_require_service_admin(hass: HomeAssistant, call: ServiceCall) -> None:
    """Allow trusted system calls, require admin for authenticated callers."""
    if call.context.user_id is not None:
        user = await hass.auth.async_get_user(call.context.user_id)
        if user is None or not user.is_admin:
            raise ServiceValidationError("Administratorrechte sind für die Projektverwaltung erforderlich")


def _service_project_store(hass: HomeAssistant) -> ProjectStore:
    if not hass.data.get(DOMAIN) or DATA_PROJECT_STORE not in hass.data:
        raise ServiceValidationError("Der Energiemanager ist nicht geladen")
    return hass.data[DATA_PROJECT_STORE]
