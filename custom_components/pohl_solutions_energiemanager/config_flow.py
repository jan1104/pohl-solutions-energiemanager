"""UI setup and editable settings for Pohl Solutions Energiemanager."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import BATTERY_DEFAULTS, DOMAIN, NAME, SOURCE_KEYS
from .input_validation import validate_battery_settings


def _source_schema(values: dict[str, Any], include_name: bool = False) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if include_name:
        fields[vol.Required(CONF_NAME, default=values.get(CONF_NAME, NAME))] = str
    for key in SOURCE_KEYS:
        marker = vol.Required if key in ("forecast_entity", "soc_entity") else vol.Optional
        args = {"default": values[key]} if values.get(key) else {}
        fields[marker(key, **args)] = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
    return vol.Schema(fields)


def _battery_schema(values: dict[str, Any]) -> vol.Schema:
    fields = {}
    for key, default in BATTERY_DEFAULTS.items():
        value = values.get(key, default)
        if isinstance(default, bool):
            field = selector.BooleanSelector()
        else:
            field = selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any"))
        fields[vol.Required(key, default=value)] = field
    return vol.Schema(fields)


class PohlSolutionsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a planning instance; there are no actuator credentials."""

    VERSION = 1

    def __init__(self) -> None:
        self._sources: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Choose the explicit forecast and live state sources."""
        if user_input is not None:
            self._sources = user_input
            return await self.async_step_battery()
        return self.async_show_form(step_id="user", data_schema=_source_schema({}, True))

    async def async_step_battery(self, user_input: dict[str, Any] | None = None):
        errors = {}
        if user_input is not None:
            try:
                settings = validate_battery_settings(user_input)
            except (ValueError, KeyError):
                errors["base"] = "invalid_battery"
            else:
                return self.async_create_entry(title=self._sources[CONF_NAME], data={**self._sources, **settings})
        return self.async_show_form(step_id="battery", data_schema=_battery_schema(user_input or {}), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        """HA attaches config_entry; never assign the deprecated property."""
        return PohlSolutionsOptionsFlow()


class PohlSolutionsOptionsFlow(config_entries.OptionsFlowWithReload):
    """Reload the instance after its source entities or battery settings change."""

    def __init__(self) -> None:
        self._sources: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        values = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            # Empty optional selections intentionally remove earlier selections.
            self._sources = {key: user_input.get(key) for key in SOURCE_KEYS}
            return await self.async_step_battery()
        return self.async_show_form(step_id="init", data_schema=_source_schema(values))

    async def async_step_battery(self, user_input: dict[str, Any] | None = None):
        errors = {}
        values = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            try:
                settings = validate_battery_settings(user_input)
            except (ValueError, KeyError):
                errors["base"] = "invalid_battery"
            else:
                return self.async_create_entry(title="", data={**self._sources, **settings})
        return self.async_show_form(step_id="battery", data_schema=_battery_schema(user_input or values), errors=errors)
