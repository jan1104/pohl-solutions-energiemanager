"""UI setup and editable settings for Pohl Solutions Energiemanager."""

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import BATTERY_DEFAULTS, DOMAIN, NAME, PRICE_MODES, PRICE_UNITS, SOURCE_KEYS
from .input_validation import validate_battery_settings
from .price_sources import price_config_from_values


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


def _price_mode_schema(values: dict[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Required(f"{side}_price_mode", default=values.get(f"{side}_price_mode", "forecast")):
            selector.SelectSelector(selector.SelectSelectorConfig(options=list(PRICE_MODES), translation_key="price_mode"))
        for side in ("import", "export")
    })


def _price_detail_schema(values: dict[str, Any]) -> vol.Schema:
    fields: dict[Any, Any] = {}
    for side in ("import", "export"):
        mode = values.get(f"{side}_price_mode", "forecast")
        if mode == "forecast":
            continue
        if mode == "entity":
            key = f"{side}_price_entity"
            args = {"default": values[key]} if values.get(key) else {}
            fields[vol.Required(key, **args)] = selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))
        if mode == "url":
            key = f"{side}_price_url"
            fields[vol.Required(key, default=values.get(key, ""))] = selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.URL))
        if mode in ("entity", "url", "fixed"):
            key = f"{side}_price_unit"
            fields[vol.Required(key, default=values.get(key, "eur_kwh"))] = selector.SelectSelector(selector.SelectSelectorConfig(options=list(PRICE_UNITS), translation_key="price_unit"))
        if mode == "fixed":
            key = f"{side}_fixed_price"
            fields[vol.Required(key, default=values.get(key, 0.0))] = selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any"))
        for suffix, default in (("multiplier", 1.0), ("adder_eur_kwh", 0.0)):
            key = f"{side}_price_{suffix}"
            fields[vol.Required(key, default=values.get(key, default))] = selector.NumberSelector(selector.NumberSelectorConfig(mode=selector.NumberSelectorMode.BOX, step="any"))
    return vol.Schema(fields)


def _validated_prices(values: dict[str, Any]) -> dict[str, Any]:
    for side in ("import", "export"):
        price_config_from_values(values, side)
    return {key: value for key, value in values.items() if key.startswith(("import_", "export_"))}


class PohlSolutionsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a planning instance; there are no actuator credentials."""

    VERSION = 1

    def __init__(self) -> None:
        self._sources: dict[str, Any] = {}
        self._prices: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Choose the explicit forecast and live state sources."""
        if user_input is not None:
            self._sources = user_input
            return await self.async_step_prices()
        return self.async_show_form(step_id="user", data_schema=_source_schema({}, True))

    async def async_step_prices(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._prices = user_input
            if all(user_input.get(f"{side}_price_mode") == "forecast" for side in ("import", "export")):
                self._prices = _validated_prices(self._prices)
                return await self.async_step_battery()
            return await self.async_step_price_details()
        return self.async_show_form(step_id="prices", data_schema=_price_mode_schema({}))

    async def async_step_price_details(self, user_input: dict[str, Any] | None = None):
        errors = {}
        if user_input is not None:
            try:
                self._prices = _validated_prices({**self._prices, **user_input})
            except (ValueError, KeyError):
                errors["base"] = "invalid_prices"
            else:
                return await self.async_step_battery()
        return self.async_show_form(step_id="price_details", data_schema=_price_detail_schema({**self._prices, **(user_input or {})}), errors=errors)

    async def async_step_battery(self, user_input: dict[str, Any] | None = None):
        errors = {}
        if user_input is not None:
            try:
                settings = validate_battery_settings(user_input)
            except (ValueError, KeyError):
                errors["base"] = "invalid_battery"
            else:
                return self.async_create_entry(title=self._sources[CONF_NAME], data={**self._sources, **self._prices, **settings})
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
        self._prices: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        values = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            # Empty optional selections intentionally remove earlier selections.
            self._sources = {key: user_input.get(key) for key in SOURCE_KEYS}
            return await self.async_step_prices()
        return self.async_show_form(step_id="init", data_schema=_source_schema(values))

    async def async_step_prices(self, user_input: dict[str, Any] | None = None):
        values = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            self._prices = {**values, **user_input}
            if all(user_input.get(f"{side}_price_mode") == "forecast" for side in ("import", "export")):
                self._prices = _validated_prices(self._prices)
                return await self.async_step_battery()
            return await self.async_step_price_details()
        return self.async_show_form(step_id="prices", data_schema=_price_mode_schema(values))

    async def async_step_price_details(self, user_input: dict[str, Any] | None = None):
        errors = {}
        if user_input is not None:
            try:
                self._prices = _validated_prices({**self._prices, **user_input})
            except (ValueError, KeyError):
                errors["base"] = "invalid_prices"
            else:
                return await self.async_step_battery()
        return self.async_show_form(step_id="price_details", data_schema=_price_detail_schema({**self._prices, **(user_input or {})}), errors=errors)

    async def async_step_battery(self, user_input: dict[str, Any] | None = None):
        errors = {}
        values = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            try:
                settings = validate_battery_settings(user_input)
            except (ValueError, KeyError):
                errors["base"] = "invalid_battery"
            else:
                return self.async_create_entry(title="", data={**self._sources, **self._prices, **settings})
        return self.async_show_form(step_id="battery", data_schema=_battery_schema(user_input or values), errors=errors)
