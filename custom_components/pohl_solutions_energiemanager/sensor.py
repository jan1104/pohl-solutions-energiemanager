"""Read-only sensors showing a simulated plan and its input diagnostics."""

from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, VERSION
from .coordinator import PohlEnergyCoordinator

DESCRIPTIONS = (
    SensorEntityDescription(key="status", translation_key="status", device_class=SensorDeviceClass.ENUM, options=["ready", "missing_forecast", "invalid_input", "planning_error"]),
    SensorEntityDescription(key="schedule", translation_key="schedule", icon="mdi:calendar-clock"),
    SensorEntityDescription(key="current_power", translation_key="current_power", device_class=SensorDeviceClass.POWER, native_unit_of_measurement=UnitOfPower.KILO_WATT),
    SensorEntityDescription(key="next_power", translation_key="next_power", device_class=SensorDeviceClass.POWER, native_unit_of_measurement=UnitOfPower.KILO_WATT),
    SensorEntityDescription(key="savings_eur", translation_key="savings", device_class=SensorDeviceClass.MONETARY, native_unit_of_measurement="EUR"),
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(PohlEnergySensor(coordinator, entry, description) for description in DESCRIPTIONS)


class PohlEnergySensor(CoordinatorEntity[PohlEnergyCoordinator], SensorEntity):
    """A plan is explanatory data and must not be treated as a live command."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PohlEnergyCoordinator, entry: ConfigEntry, description: SensorEntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.title, manufacturer="Pohl Solutions", model=NAME, sw_version=VERSION)

    @property
    def available(self) -> bool:
        data = self.coordinator.data or {}
        return super().available and (self.entity_description.key == "status" or bool(data.get("valid")))

    @property
    def native_value(self) -> str | float | int | None:
        data = self.coordinator.data or {}
        key = self.entity_description.key
        if key == "status":
            return data.get("status", "missing_forecast")
        if key == "schedule":
            return len(data.get("slots", []))
        if key == "savings_eur":
            return round(data[key], 4) if key in data else None
        now = datetime.now(timezone.utc)
        for row in data.get("slots", []):
            start = datetime.fromisoformat(row["start"])
            end = start + timedelta(hours=row["duration_hours"])
            if key == "current_power" and start <= now < end:
                return row["battery_power_kw"]
            if key == "next_power" and start >= now:
                return row["battery_power_kw"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        if self.entity_description.key == "status":
            return {"planning_only": True, "valid": data.get("valid", False), "error": data.get("error"), "source_entities": data.get("source_entities", {})}
        if self.entity_description.key == "schedule":
            return {key: data.get(key) for key in ("planning_only", "generated_at", "total_cost_eur", "baseline_cost_eur", "assumptions", "slots", "price_sources", "price_attribution")}
        return {"planning_only": True}
