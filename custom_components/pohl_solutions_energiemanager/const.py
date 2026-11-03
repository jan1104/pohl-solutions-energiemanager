"""Shared constants for the planning-only integration."""

DOMAIN = "pohl_solutions_energiemanager"
NAME = "Pohl Solutions Energiemanager"
VERSION = "0.3.0"
EVENT_PLAN_UPDATED = f"{DOMAIN}_plan_updated"
SERVICE_REPLAN = "replan"
CONF_FORECAST_ENTITY = "forecast_entity"
CONF_SOC_ENTITY = "soc_entity"
CONF_GRID_ENTITY = "grid_entity"
CONF_PV_ENTITY = "pv_entity"
CONF_LOAD_ENTITY = "load_entity"
SOURCE_KEYS = (CONF_FORECAST_ENTITY, CONF_SOC_ENTITY, CONF_GRID_ENTITY, CONF_PV_ENTITY, CONF_LOAD_ENTITY)
PRICE_MODES = ("forecast", "entity", "url", "fixed", "smard")
PRICE_UNITS = ("eur_kwh", "ct_kwh", "eur_mwh")
BATTERY_DEFAULTS = {
    "capacity_kwh": 200.704,
    "min_soc_pct": 10.0,
    "max_soc_pct": 90.0,
    "max_charge_kw": 50.0,
    "max_discharge_kw": 50.0,
    "charge_efficiency": 0.95,
    "discharge_efficiency": 0.95,
    "wear_cost_eur_per_kwh": 0.0,
    "allow_grid_charge": False,
    "allow_battery_export": False,
    "soc_step_kwh": 2.0,
}
