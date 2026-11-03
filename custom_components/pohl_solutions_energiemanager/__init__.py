"""Pohl Solutions Energiemanager: local, planning-only Home Assistant integration."""

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError

from .const import DOMAIN, SERVICE_REPLAN
from .coordinator import PohlEnergyCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up diagnostics even when forecast data has not arrived yet."""
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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload all entities and stop the coordinator's scheduled polling."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    coordinator = hass.data[DOMAIN].pop(entry.entry_id)
    await coordinator.async_shutdown()
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_REPLAN)
        hass.data.pop(DOMAIN)
    return True
