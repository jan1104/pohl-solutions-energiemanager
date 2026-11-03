"""Pohl Solutions Energiemanager: local, planning-only Home Assistant integration."""

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .const import DOMAIN, SERVICE_REPLAN
from .coordinator import PohlEnergyCoordinator
from .project_store import DATA_PROJECT_STORE, ProjectStore

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up diagnostics even when forecast data has not arrived yet."""
    if DATA_PROJECT_STORE not in hass.data:
        hass.data[DATA_PROJECT_STORE] = ProjectStore(hass)
    await hass.data[DATA_PROJECT_STORE].async_load()
    coordinator = PohlEnergyCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, SERVICE_REPLAN):
        async def async_replan(call: ServiceCall) -> None:
            selected = hass.data.get(DOMAIN, {}).get(call.data["entry_id"])
            if selected is None:
                raise ServiceValidationError("Unknown or unloaded Pohl Solutions entry_id")
            await selected.async_request_refresh()

        hass.services.async_register(DOMAIN, SERVICE_REPLAN, async_replan, schema=vol.Schema({vol.Required("entry_id"): str}))

        async def async_import_project(call: ServiceCall):
            try:
                return await hass.data[DATA_PROJECT_STORE].async_import(call.data["project_json"])
            except ValueError as err:
                raise ServiceValidationError(str(err)) from err
            except OSError as err:
                raise HomeAssistantError("Project was not activated because persistent storage failed") from err

        async def async_export_project(call: ServiceCall):
            return hass.data[DATA_PROJECT_STORE].export()

        async def async_project_status(call: ServiceCall):
            return hass.data[DATA_PROJECT_STORE].status()

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
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    coordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_shutdown()
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_REPLAN)
        for service in ("import_project", "export_project", "project_status"):
            hass.services.async_remove(DOMAIN, service)
        hass.data.pop(DATA_PROJECT_STORE, None)
        hass.data.pop(DOMAIN)
    return True
